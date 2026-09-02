"""Processamento das planilhas SIG da empresa 1096 - UP PACK BRAZIL."""

from __future__ import annotations

import io
import os
import re
from typing import Optional

import pandas as pd

COLUNAS_DOMINIO = ["DESCRIÇÃO", "DATA", "VALOR", "DÉBITO", "CRÉDITO", "HISTÓRICO"]


def _texto(valor) -> str:
    if pd.isna(valor):
        return ""
    return re.sub(r"\s+", " ", str(valor)).strip()


def _moeda(valor) -> float:
    if valor is None or pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if not texto:
        return 0.0
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except (TypeError, ValueError):
        return 0.0


def _ler_sig(file_bytes: bytes) -> pd.DataFrame:
    bruto = pd.read_excel(io.BytesIO(file_bytes), header=None)
    cabecalho = None
    for idx, row in bruto.iterrows():
        valores = {_texto(v).casefold() for v in row.tolist() if _texto(v)}
        if "data" in valores and "entrada" in valores and ("saída" in valores or "saida" in valores):
            cabecalho = idx
            break
    if cabecalho is None:
        raise ValueError("Cabeçalho SIG não identificado. Esperado: Data, Entrada e Saída.")

    nomes = []
    for pos, valor in enumerate(bruto.iloc[cabecalho].tolist()):
        nome = _texto(valor)
        nomes.append(nome if nome else f"COL_{pos}")
    df = bruto.iloc[cabecalho + 1 :].copy()
    df.columns = nomes
    return df


def identificar_banco_up_pack(file_bytes: bytes, filename: str = "") -> Optional[str]:
    """Identifica Santander/Sicredi sem confundir transferências entre contas."""
    nome = os.path.basename(filename or "").casefold()
    if "santander" in nome:
        return "santander"
    if "sicredi" in nome:
        return "sicredi"

    # O layout SIG enviado não traz o nome do banco no cabeçalho. Como uma planilha
    # pode citar o outro banco em Conta Vinculada, não inferimos por transferências.
    return None


def processar_planilha_up_pack(file_bytes: bytes, banco: str) -> pd.DataFrame:
    banco_slug = str(banco or "").strip().casefold()
    if banco_slug not in {"santander", "sicredi"}:
        raise ValueError("Banco inválido para a UP PACK. Use Santander ou Sicredi.")

    df = _ler_sig(file_bytes)
    obrigatorias = {"Data", "D/C", "Complemento", "Conf", "Entrada", "Saída"}
    faltantes = [col for col in obrigatorias if col not in df.columns]
    if faltantes:
        raise ValueError("Colunas SIG ausentes: " + ", ".join(faltantes))

    banco_nome = "Santander" if banco_slug == "santander" else "Sicredi"
    linhas = []
    data_grupo = None
    grupo_pagamento_diversos = False

    for _, row in df.iterrows():
        data_raw = row.get("Data")
        data = pd.to_datetime(data_raw, dayfirst=True, errors="coerce")

        if pd.notna(data):
            data_grupo = data
            dc = _texto(row.get("D/C"))
            complemento = _texto(row.get("Complemento"))
            entrada = abs(_moeda(row.get("Entrada")))
            saida = abs(_moeda(row.get("Saída")))

            grupo_pagamento_diversos = (
                "PAGAMENTO CONTAS DIV" in complemento.upper()
                and saida > 0
            )
            if grupo_pagamento_diversos:
                # É somente o total. Os títulos aparecem nas linhas sem DATA seguintes.
                continue

            valor = entrada if entrada > 0 else (-saida if saida > 0 else 0.0)
            if abs(valor) < 0.005:
                continue

            historico = complemento or dc or "MOVIMENTO BANCARIO"
            linhas.append(
                {
                    "DESCRIÇÃO": banco_nome,
                    "DATA": data.strftime("%d/%m/%Y"),
                    "VALOR": round(valor, 2),
                    "DÉBITO": "",
                    "CRÉDITO": "",
                    "HISTÓRICO": historico,
                }
            )
            continue

        # Linhas sem DATA imediatamente após PAGAMENTO CONTAS DIV. representam
        # títulos individuais: D/C = referência, Complemento = valor, Conf = favorecido.
        if grupo_pagamento_diversos and data_grupo is not None:
            referencia = _texto(row.get("D/C"))
            favorecido = _texto(row.get("Conf"))
            valor_titulo = abs(_moeda(row.get("Complemento")))
            if valor_titulo < 0.005:
                continue
            historico = " ".join(parte for parte in (favorecido, referencia) if parte).strip()
            if not historico:
                historico = "PAGAMENTO TITULO"
            linhas.append(
                {
                    "DESCRIÇÃO": banco_nome,
                    "DATA": data_grupo.strftime("%d/%m/%Y"),
                    "VALOR": round(-valor_titulo, 2),
                    "DÉBITO": "",
                    "CRÉDITO": "",
                    "HISTÓRICO": historico,
                }
            )

    resultado = pd.DataFrame(linhas, columns=COLUNAS_DOMINIO)
    if resultado.empty:
        return resultado
    resultado["DATA"] = pd.to_datetime(resultado["DATA"], dayfirst=True, errors="coerce")
    resultado = resultado.dropna(subset=["DATA"]).reset_index(drop=True)
    return resultado
