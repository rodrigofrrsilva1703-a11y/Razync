"""Montagem bancária específica da Eletro Forte Filial 1408."""
from __future__ import annotations

from collections import defaultdict
import re
import unicodedata

import pandas as pd

from razync.eletro_forte import COLUNAS_MODELO, processar_recebidos


CONTA_ITAU_1408 = "512"


def _texto_normalizado(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    return texto.encode("ascii", "ignore").decode().upper()


def _eh_recebimento_cartao(valor: str) -> bool:
    texto = _texto_normalizado(valor)
    return "RECEBIMENTO REDE" in texto or any(
        bandeira in texto for bandeira in ("REDE VISA", "REDE MAST", "REDE ELO")
    )


def _remover_cpf_cnpj(valor: str) -> str:
    texto = str(valor or "")
    texto = re.sub(
        r"(?<!\d)(?:\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}|"
        r"\d{3}\.?\d{3}\.?\d{3}-?\d{2})(?!\d)",
        "",
        texto,
    )
    texto = re.sub(r"\b(?:CNPJ|CPF)(?:/CPF)?\s*[:\-]?\s*", "", texto, flags=re.I)
    return re.sub(r"\s{2,}", " ", texto).strip(" -|")


def _chave(data, valor) -> tuple[pd.Timestamp, int]:
    return pd.Timestamp(data).normalize(), int(round(float(valor) * 100))


def montar_modelo_1408(
    lancamentos_extrato,
    conteudo_recebidos: bytes | None = None,
    ano_referencia: int | None = None,
    francesinhas: pd.DataFrame | None = None,
):
    """Usa o extrato como base e detalha recebimentos e francesinhas."""
    modelo = pd.DataFrame(lancamentos_extrato).copy()
    if modelo.empty or not {"DATA", "VALOR"}.issubset(modelo.columns):
        raise ValueError("Nenhum movimento válido foi encontrado no extrato Itaú.")

    modelo["DATA"] = pd.to_datetime(modelo["DATA"], dayfirst=True, errors="coerce")
    modelo["VALOR"] = pd.to_numeric(modelo["VALOR"], errors="coerce")
    modelo = modelo.dropna(subset=["DATA", "VALOR"]).reset_index(drop=True)
    if modelo.empty:
        raise ValueError("O extrato Itaú não contém datas e valores válidos.")
    modelo["DESCRIÇÃO"] = "BANCO ITAÚ"
    modelo["DÉBITO"] = modelo["VALOR"].map(lambda v: CONTA_ITAU_1408 if v > 0 else "")
    modelo["CRÉDITO"] = modelo["VALOR"].map(lambda v: CONTA_ITAU_1408 if v < 0 else "")
    if "HISTÓRICO" not in modelo:
        modelo["HISTÓRICO"] = "MOVIMENTO ITAÚ"

    detalhes = defaultdict(list)
    if conteudo_recebidos:
        ano = int(ano_referencia or modelo["DATA"].dt.year.mode().iloc[0])
        grupos = processar_recebidos(conteudo_recebidos, ano, CONTA_ITAU_1408)
        recebido = grupos.get(CONTA_ITAU_1408, pd.DataFrame())
        for indice, linha in recebido.iterrows():
            detalhes[_chave(linha["DATA"], linha["VALOR"])].append((indice, linha))

    usados_recebidos = set()
    historicos_substituidos = 0
    for indice, linha in modelo.loc[modelo["VALOR"] > 0].iterrows():
        if _eh_recebimento_cartao(linha.get("HISTÓRICO", "")):
            continue
        candidatos = detalhes.get(_chave(linha["DATA"], linha["VALOR"]), [])
        candidato = next((item for item in candidatos if item[0] not in usados_recebidos), None)
        if candidato:
            usados_recebidos.add(candidato[0])
            modelo.at[indice, "HISTÓRICO"] = candidato[1]["HISTÓRICO"]
            historicos_substituidos += 1

    linhas_francesinhas = []
    indices_remover = []
    grupos_francesinhas = 0
    if francesinhas is not None and not francesinhas.empty:
        for data, grupo in francesinhas.groupby(pd.to_datetime(francesinhas["DATA"]).dt.normalize()):
            total = round(float(grupo["VALOR"].sum()), 2)
            candidatos = modelo.loc[
                (modelo["DATA"].dt.normalize() == data)
                & (modelo["VALOR"].round(2) == total)
                & modelo["HISTÓRICO"].astype(str).str.contains("BOLETO RECEBIDO", case=False, na=False)
            ]
            if candidatos.empty:
                continue
            indices_remover.append(candidatos.index[0])
            linhas_francesinhas.append(grupo[COLUNAS_MODELO].copy())
            grupos_francesinhas += 1

    if indices_remover:
        modelo = modelo.drop(index=indices_remover)
    if linhas_francesinhas:
        modelo = pd.concat([modelo[COLUNAS_MODELO], *linhas_francesinhas], ignore_index=True)

    historico = modelo["HISTÓRICO"].fillna("").astype(str).map(_remover_cpf_cnpj)
    modelo["HISTÓRICO"] = [
        texto if texto.lower().startswith(("pago: ", "recebido: "))
        else ("Recebido: " if valor > 0 else "Pago: ") + texto
        for texto, valor in zip(historico, modelo["VALOR"])
    ]
    modelo = modelo[COLUNAS_MODELO].sort_values(["DATA"], kind="stable").reset_index(drop=True)
    resumo = {
        "movimentos_extrato": len(lancamentos_extrato),
        "historicos_substituidos": historicos_substituidos,
        "grupos_francesinhas": grupos_francesinhas,
        "linhas_finais": len(modelo),
    }
    return modelo, resumo
