"""Extrato Itaú da empresa 88 - H & W Serviços Médicos."""

from __future__ import annotations

import re

import pandas as pd

from razync.vgv_1402 import _ocr_paginas


CONTA_ITAU_HW88 = "508"
COLUNAS_MODELO = ["DESCRIÇÃO", "DATA", "VALOR", "DÉBITO", "CRÉDITO", "HISTÓRICO"]
_DATA = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")
_VALOR = re.compile(r"^-?\s*\d{1,3}(?:\.\d{3})*,\d{2}$")
_DOCUMENTO = re.compile(
    r"\b(?:\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2})\b"
)


def _moeda(texto) -> float:
    valor = str(texto or "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(valor)
    except ValueError:
        return 0.0


def _limpar_historico(texto: str, valor: float) -> str:
    texto = _DOCUMENTO.sub(" ", str(texto or ""))
    texto = re.sub(r"\s+", " ", texto).strip(" -|—_")
    texto = re.sub(r"^(?:Pago|Recebido):\s*", "", texto, flags=re.I)
    if re.search(r"RENDIMENTOS?\s+REND", texto, flags=re.I):
        texto = "RENDIMENTOS"
    return ("Recebido: " if valor > 0 else "Pago: ") + texto


def processar_tokens_pagina(largura: float, dados: pd.DataFrame) -> list[dict]:
    """Reconstrói a tabela usando as posições das colunas do extrato Itaú."""
    if dados is None or dados.empty:
        return []
    df = dados.dropna(subset=["text"]).copy()
    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"] != ""]
    df["left"] = pd.to_numeric(df["left"], errors="coerce")
    df["top"] = pd.to_numeric(df["top"], errors="coerce")
    df["width"] = pd.to_numeric(df["width"], errors="coerce").fillna(0)
    df["height"] = pd.to_numeric(df["height"], errors="coerce").fillna(0)
    df = df.dropna(subset=["left", "top"])
    df["cx"] = df["left"] + df["width"] / 2
    df["cy"] = df["top"] + df["height"] / 2

    datas = []
    for indice, item in df.iterrows():
        achado = _DATA.search(item["text"])
        if achado and item["cx"] < largura * 0.22:
            datas.append((indice, achado.group(0), float(item["cy"])))
    datas.sort(key=lambda item: item[2])

    registros = []
    for posicao, (_, data_texto, centro_y) in enumerate(datas):
        anterior = datas[posicao - 1][2] if posicao else centro_y - 70
        seguinte = datas[posicao + 1][2] if posicao + 1 < len(datas) else centro_y + 70
        limite_superior = (anterior + centro_y) / 2
        limite_inferior = (centro_y + seguinte) / 2
        faixa = df[(df["cy"] >= limite_superior) & (df["cy"] < limite_inferior)].copy()

        valores = faixa[
            (faixa["cx"] >= largura * 0.76)
            & (faixa["cx"] < largura * 0.91)
            & faixa["text"].str.match(_VALOR)
        ].sort_values(["cy", "left"])
        if valores.empty:
            continue
        valor = round(_moeda(valores.iloc[-1]["text"]), 2)
        if abs(valor) < 0.005:
            continue

        historico_partes = faixa[
            (faixa["cx"] >= largura * 0.13)
            & (faixa["cx"] < largura * 0.76)
            & ~faixa["text"].str.contains(_DATA)
            & ~faixa["text"].str.match(_VALOR)
        ].sort_values(["cy", "left"])["text"].tolist()
        historico_bruto = " ".join(historico_partes)
        if "SALDO TOTAL" in historico_bruto.upper():
            continue
        historico = _limpar_historico(historico_bruto, valor)
        if historico in {"Pago: ", "Recebido: "}:
            continue
        data = pd.to_datetime(data_texto, dayfirst=True, errors="coerce")
        if pd.isna(data):
            continue
        registros.append({
            "DESCRIÇÃO": "BANCO ITAÚ",
            "DATA": data.normalize(),
            "VALOR": valor,
            "DÉBITO": CONTA_ITAU_HW88 if valor > 0 else "",
            "CRÉDITO": CONTA_ITAU_HW88 if valor < 0 else "",
            "HISTÓRICO": historico,
        })
    return registros


def processar_extrato_hw88(
    conteudo: bytes, data_inicial=None, data_final=None
) -> pd.DataFrame:
    registros = []
    for largura, dados in _ocr_paginas(conteudo):
        registros.extend(processar_tokens_pagina(largura, dados))
    if not registros:
        raise ValueError("Nenhum lançamento foi reconhecido no extrato Itaú da empresa 88.")
    df = pd.DataFrame(registros, columns=COLUNAS_MODELO)
    if data_inicial is not None:
        df = df[df["DATA"] >= pd.Timestamp(data_inicial)]
    if data_final is not None:
        df = df[df["DATA"] <= pd.Timestamp(data_final)]
    if df.empty:
        raise ValueError("O extrato não possui lançamentos no período informado.")
    return df.sort_values(["DATA"], kind="stable").reset_index(drop=True)
