"""Banco Inter da empresa 841 - Lucrativite."""

from __future__ import annotations

import io
import re

import pandas as pd


CONTA_INTER_841 = "506"
COLUNAS_MODELO = ["DESCRIÇÃO", "DATA", "VALOR", "DÉBITO", "CRÉDITO", "HISTÓRICO"]


def _normalizar(texto) -> str:
    texto = str(texto or "")
    # Alguns arquivos exportados pelo Inter chegam com UTF-8 interpretado como latin-1.
    if "Ã" in texto or "Â" in texto:
        try:
            texto = texto.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return re.sub(r"\s+", " ", texto).strip()


def _mapa_cabecalho(valores) -> dict[str, int]:
    mapa = {}
    for indice, valor in enumerate(valores):
        nome = _normalizar(valor).lower()
        nome = (nome.replace("ç", "c").replace("ã", "a").replace("á", "a")
                .replace("é", "e").replace("í", "i").replace("ó", "o")
                .replace("ú", "u"))
        if "data" in nome and "lanc" in nome:
            mapa["data"] = indice
        elif "descri" in nome:
            mapa["historico"] = indice
        elif nome == "valor" or nome.startswith("valor "):
            mapa["valor"] = indice
    return mapa


def processar_extrato_inter_841(
    conteudo: bytes, data_inicial=None, data_final=None
) -> pd.DataFrame:
    """Transforma a exportação XLS/XLSX do Banco Inter no Modelo Domínio."""
    xls = pd.ExcelFile(io.BytesIO(conteudo))
    registros = []
    for aba in xls.sheet_names:
        bruto = pd.read_excel(xls, sheet_name=aba, header=None, dtype=object)
        cabecalho = None
        mapa = None
        for indice in range(min(len(bruto), 30)):
            candidato = _mapa_cabecalho(bruto.iloc[indice].tolist())
            if all(chave in candidato for chave in ("data", "historico", "valor")):
                cabecalho, mapa = indice, candidato
                break
        if cabecalho is None:
            continue

        for _, linha in bruto.iloc[cabecalho + 1:].iterrows():
            data = pd.to_datetime(linha.iloc[mapa["data"]], dayfirst=True, errors="coerce")
            valor = pd.to_numeric(linha.iloc[mapa["valor"]], errors="coerce")
            historico = _normalizar(linha.iloc[mapa["historico"]])
            if pd.isna(data) or pd.isna(valor) or abs(float(valor)) < 0.005 or not historico:
                continue
            valor = round(float(valor), 2)
            historico = re.sub(r"^(?:Pago|Recebido):\s*", "", historico, flags=re.I)
            registros.append({
                "DESCRIÇÃO": "BANCO INTER",
                "DATA": data.normalize(),
                "VALOR": valor,
                "DÉBITO": CONTA_INTER_841 if valor > 0 else "",
                "CRÉDITO": CONTA_INTER_841 if valor < 0 else "",
                "HISTÓRICO": ("Recebido: " if valor > 0 else "Pago: ") + historico,
            })

    if not registros:
        raise ValueError("Nenhum lançamento foi reconhecido no extrato Banco Inter.")
    df = pd.DataFrame(registros, columns=COLUNAS_MODELO)
    if data_inicial is not None:
        df = df[df["DATA"] >= pd.Timestamp(data_inicial)]
    if data_final is not None:
        df = df[df["DATA"] <= pd.Timestamp(data_final)]
    if df.empty:
        raise ValueError("O extrato não possui lançamentos no período informado.")
    return df.sort_values("DATA", kind="stable").reset_index(drop=True)
