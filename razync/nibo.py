"""Leitura do relatório visual de Contas & Extratos exportado pelo Nibo.

O PDF do Nibo usado pela empresa 1529 é composto principalmente por imagens.
Este módulo usa OCR por página e a posição das colunas da tabela para reconstruir
Data, Nome, Descrição, Ref., Identif., Entrada e Saída sem interferir nos parsers
bancários do Razync.
"""

from __future__ import annotations

import io
import re
from datetime import datetime

import fitz
import pandas as pd
import pytesseract
from PIL import Image


_RE_DATA = re.compile(r"\b(\d{2}/\d{2}/\d{2})\b")


def _valor_br(texto: str):
    texto = str(texto or "").strip().replace("R$", "").replace(" ", "")
    texto = texto.replace("O", "0").replace("o", "0")
    match = re.search(r"\(?-?[\d\.,]+\)?", texto)
    if not match:
        return None

    bruto = match.group(0)
    negativo = bruto.startswith("(") and bruto.endswith(")")
    bruto = bruto.strip("()")

    if "," in bruto:
        normalizado = bruto.replace(".", "").replace(",", ".")
    elif "." in bruto:
        # OCR do Nibo pode perder a vírgula decimal em valores com milhar.
        # Ex.: "20.115,83" pode chegar como "20.11583". Nesse formato,
        # os dois últimos dígitos continuam sendo os centavos.
        sinal = "-" if bruto.startswith("-") else ""
        corpo = bruto.lstrip("-")
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+\d{2}", corpo):
            inteiro = corpo[:-2].replace(".", "")
            normalizado = f"{sinal}{inteiro}.{corpo[-2:]}"
        else:
            partes = bruto.split(".")
            if len(partes[-1]) == 2:
                normalizado = "".join(partes[:-1]) + "." + partes[-1]
            elif len(partes[-1]) == 3:
                normalizado = "".join(partes)
            else:
                normalizado = bruto.replace(".", "")
    else:
        digitos = re.sub(r"\D", "", bruto)
        if not digitos:
            return None
        normalizado = digitos[:-2] + "." + digitos[-2:] if len(digitos) >= 3 else digitos

    try:
        valor = float(normalizado)
    except ValueError:
        return None
    return -valor if negativo else valor


def _texto_segmento(segmento: pd.DataFrame, largura: int, inicio: float, fim: float) -> str:
    dados = segmento[(segmento["cx"] / largura >= inicio) & (segmento["cx"] / largura < fim)].copy()
    if dados.empty:
        return ""

    dados = dados.sort_values(["cy", "left"])
    linhas = []
    for _, palavra in dados.iterrows():
        centro = float(palavra["cy"])
        destino = None
        for linha in linhas:
            if abs(centro - linha["cy"]) <= 10:
                destino = linha
                break
        if destino is None:
            destino = {"cy": centro, "palavras": []}
            linhas.append(destino)
        destino["palavras"].append((float(palavra["left"]), str(palavra["text"])))
        destino["cy"] = sum(p[0] * 0 + centro for p in destino["palavras"]) / len(destino["palavras"])

    textos = []
    for linha in sorted(linhas, key=lambda item: item["cy"]):
        textos.append(" ".join(texto for _, texto in sorted(linha["palavras"], key=lambda item: item[0])))
    return re.sub(r"\s+", " ", " ".join(textos)).strip()


def _limpar_nome(texto: str) -> str:
    texto = re.sub(r"\s+", " ", str(texto or "")).strip()
    texto = re.sub(r"^(?:\[[^\]]{1,3}\]|[QO]{1,3})\s+", "", texto, flags=re.IGNORECASE)
    return texto.strip(" -|")


def _historico(nome: str, descricao: str, referencia: str = "", identificacao: str = "") -> str:
    """Monta somente Nome + Descrição; Ref. e Identif. não vão para o Domínio."""
    nome = _limpar_nome(nome)
    descricao = re.sub(r"\s+", " ", str(descricao or "")).strip()
    principal = " - ".join(parte for parte in (nome, descricao) if parte)
    return principal or "MOVIMENTO NIBO"


def processar_extrato_nibo_pdf(file_bytes: bytes) -> pd.DataFrame:
    """Converte o PDF visual do Nibo em lançamentos prontos para o Modelo Domínio."""
    documento = fitz.open(stream=file_bytes, filetype="pdf")
    lancamentos = []
    data_atual = None

    for numero_pagina, pagina in enumerate(documento, start=1):
        pix = pagina.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
        imagem = Image.open(io.BytesIO(pix.tobytes("png")))
        largura, altura = imagem.size

        dados = pytesseract.image_to_data(
            imagem,
            lang="por",
            config="--psm 4",
            output_type=pytesseract.Output.DATAFRAME,
        )
        dados = dados.dropna(subset=["text"])
        dados = dados[dados["conf"] >= 15].copy()
        if dados.empty:
            continue

        dados["text"] = dados["text"].astype(str)
        dados["cx"] = dados["left"] + dados["width"] / 2
        dados["cy"] = dados["top"] + dados["height"] / 2

        cabecalhos = dados[dados["text"].str.contains(r"Entrada|Sa[ií]da", case=False, regex=True)]
        y_cabecalho = float(cabecalhos["cy"].min()) if not cabecalhos.empty else altura * 0.07

        ancoras = []
        for _, palavra in dados.iterrows():
            x = float(palavra["cx"]) / largura
            if not (0.755 <= x <= 0.885):
                continue
            if float(palavra["cy"]) <= y_cabecalho + 20:
                continue
            if not any(caractere.isdigit() for caractere in str(palavra["text"])):
                continue
            valor = _valor_br(palavra["text"])
            if valor is None:
                continue
            ancoras.append({
                "cy": float(palavra["cy"]),
                "tipo": "entrada" if x < 0.825 else "saida",
                "valor": abs(float(valor)),
            })

        ancoras.sort(key=lambda item: item["cy"])
        unicas = []
        for ancora in ancoras:
            if unicas and abs(ancora["cy"] - unicas[-1]["cy"]) < 12:
                continue
            unicas.append(ancora)
        ancoras = unicas

        for indice, ancora in enumerate(ancoras):
            cy = ancora["cy"]
            superior = (ancoras[indice - 1]["cy"] + cy) / 2 if indice else max(y_cabecalho + 15, cy - 65)
            inferior = (cy + ancoras[indice + 1]["cy"]) / 2 if indice + 1 < len(ancoras) else cy + 65
            segmento = dados[(dados["cy"] >= superior) & (dados["cy"] < inferior)]

            datas = []
            coluna_data = segmento[(segmento["cx"] / largura >= 0.055) & (segmento["cx"] / largura < 0.13)]
            for _, palavra in coluna_data.iterrows():
                match_data = _RE_DATA.search(str(palavra["text"]))
                if match_data:
                    datas.append((abs(float(palavra["cy"]) - cy), match_data.group(1)))
            if datas:
                data_atual = min(datas, key=lambda item: item[0])[1]
            if not data_atual:
                continue

            nome = _texto_segmento(segmento, largura, 0.13, 0.385)
            descricao = _texto_segmento(segmento, largura, 0.385, 0.615)
            referencia = _texto_segmento(segmento, largura, 0.615, 0.70)
            identificacao = _texto_segmento(segmento, largura, 0.70, 0.755)

            valor = round(ancora["valor"] if ancora["tipo"] == "entrada" else -ancora["valor"], 2)
            if valor == 0:
                continue

            data_formatada = datetime.strptime(data_atual, "%d/%m/%y").strftime("%d/%m/%Y")
            historico_base = _historico(nome, descricao, referencia, identificacao)
            prefixo_historico = "Pago:" if valor < 0 else "Recebido:"
            lancamentos.append({
                "DESCRIÇÃO": "NIBO",
                "DATA": data_formatada,
                "VALOR": valor,
                "DÉBITO": "",
                "CRÉDITO": "",
                "HISTÓRICO": f"{prefixo_historico} {historico_base}",
                "PÁGINA": numero_pagina,
            })

    if not lancamentos:
        raise ValueError("Nenhum lançamento foi identificado no relatório Nibo.")

    df = pd.DataFrame(lancamentos)
    return df
