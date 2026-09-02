"""Leitor dedicado do extrato Bradesco da empresa 968 - Radani.

O PDF do Bradesco pode ser rasterizado. Para evitar erros silenciosos do OCR, o
leitor combina uma leitura textual com uma leitura numérica focada nas colunas
de crédito, débito e saldo. Os totais impressos no próprio extrato são usados
como validação, nunca para inventar lançamentos.
"""
from __future__ import annotations

from io import BytesIO
import re
import unicodedata

import pandas as pd


def _norm(txt) -> str:
    txt = "" if txt is None else str(txt)
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", txt).strip().upper()


def _moeda(txt):
    if txt is None:
        return None
    s = (
        str(txt).strip().replace("O", "0").replace("o", "0")
        .replace("I", "1").replace("l", "1")
        .replace("“", "").replace("”", "").replace("—", "-")
    )
    m = re.search(r"-?\d{1,3}(?:\.\d{3})*,\d{2}", s)
    if not m:
        return None
    try:
        return float(m.group(0).replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _agrupar_linhas(partes, tolerancia=10):
    """Agrupa tokens numéricos pela coordenada Y, preservando o OCR focado."""
    saida = []
    for item in sorted(partes, key=lambda x: x["y"]):
        if saida and abs(item["y"] - saida[-1]["y"]) <= tolerancia:
            for chave, valor in item.items():
                if chave in {"y", "prioridade"} or valor in (None, ""):
                    continue
                pchave = f"_p_{chave}"
                if chave not in saida[-1] or item.get("prioridade", 0) > saida[-1].get(pchave, -1):
                    saida[-1][chave] = valor
                    saida[-1][pchave] = item.get("prioridade", 0)
            saida[-1]["y"] = (saida[-1]["y"] + item["y"]) / 2
        else:
            novo = dict(item)
            for chave in ("saldo", "debito", "credito"):
                if chave in novo:
                    novo[f"_p_{chave}"] = novo.get("prioridade", 0)
            saida.append(novo)
    return saida


def _data_da_linha(texto, ano_referencia=None):
    m = re.search(r"(\d{2})\D?(\d{2})\D?(\d{4})", texto or "")
    if not m:
        digitos = re.sub(r"\D", "", texto or "")
        if len(digitos) >= 8:
            m = re.match(r"(\d{2})(\d{2})(\d{4})", digitos[:8])
    if not m:
        return None
    try:
        dia, mes, ano = map(int, m.groups())
    except Exception:
        return None
    if not (1 <= dia <= 31 and 1 <= mes <= 12):
        return None
    if ano_referencia and not (ano_referencia - 1 <= ano <= ano_referencia + 1):
        ano = ano_referencia
    try:
        return pd.Timestamp(year=ano, month=mes, day=dia)
    except Exception:
        return None


def processar_extrato_bradesco_radani(conteudo: bytes):
    """Retorna (lançamentos, diagnóstico) para o PDF Bradesco da Radani."""
    import fitz
    import pytesseract
    from PIL import Image, ImageOps

    documento = fitz.open(stream=conteudo, filetype="pdf")
    lancamentos = []
    totais_impressos = []
    data_atual = None
    saldo_atual = None
    ano_ref = None

    for numero_pagina, pagina in enumerate(documento, start=1):
        escala = 2.5
        pix = pagina.get_pixmap(matrix=fitz.Matrix(escala, escala), alpha=False)
        imagem = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        imagem = ImageOps.autocontrast(ImageOps.grayscale(imagem))
        largura, altura = imagem.size

        geral = pytesseract.image_to_data(
            imagem,
            lang="por",
            config="--psm 6 -c preserve_interword_spaces=1",
            output_type=pytesseract.Output.DATAFRAME,
        )
        geral = geral.dropna(subset=["text"]).copy()
        geral["text"] = geral["text"].astype(str)
        geral["cx"] = geral["left"] + geral["width"] / 2
        geral["cy"] = geral["top"] + geral["height"] / 2

        texto_pagina = " ".join(geral["text"].tolist())
        anos = re.findall(r"20\d{2}", texto_pagina)
        if anos and ano_ref is None:
            candidatos = [int(a) for a in anos if 2024 <= int(a) <= 2035]
            if candidatos:
                ano_ref = max(set(candidatos), key=candidatos.count)

        corte = altura
        for _, token in geral.iterrows():
            if _norm(token["text"]).startswith("SALDOS"):
                perto = " ".join(
                    geral[
                        (geral["cy"].sub(token["cy"]).abs() < 24)
                        & (geral["cx"] < largura * 0.62)
                    ]["text"]
                )
                if "SALDOS INVEST" in _norm(perto):
                    corte = min(corte, float(token["cy"]) - 10)

        x_crop = int(largura * 0.43)
        imagem_numeros = imagem.crop((x_crop, 0, largura, int(min(corte, altura * 0.84))))
        numeros = pytesseract.image_to_data(
            imagem_numeros,
            lang="por",
            config="--psm 6 -c tessedit_char_whitelist=0123456789.,-",
            output_type=pytesseract.Output.DATAFRAME,
        )
        numeros = numeros.dropna(subset=["text"]).copy()
        numeros["text"] = numeros["text"].astype(str)
        numeros["cx"] = numeros["left"] + numeros["width"] / 2 + x_crop
        numeros["cy"] = numeros["top"] + numeros["height"] / 2

        partes = []

        def adicionar_tokens(df, prioridade):
            for _, token in df[df["cy"] < corte].iterrows():
                valor = _moeda(token["text"])
                if valor is None:
                    continue
                x = float(token["cx"])
                y = float(token["cy"])
                tipo = None
                if x > largura * 0.87:
                    tipo = "saldo"
                elif x > largura * 0.72:
                    tipo = "debito"
                elif x > largura * 0.58:
                    tipo = "credito"
                if tipo:
                    partes.append({"y": y, tipo: valor, "prioridade": prioridade})

        # OCR numérico focado sempre vence a leitura textual quando ambos existem.
        adicionar_tokens(numeros, 2)
        adicionar_tokens(geral, 1)

        for item in _agrupar_linhas(partes):
            y = item["y"]
            if y < altura * 0.12 or y >= corte:
                continue

            faixa = geral[(geral["cy"] >= y - 22) & (geral["cy"] <= y + 22)]
            texto_esquerda = " ".join(
                faixa[faixa["cx"] < largura * 0.17].sort_values(["top", "left"])["text"]
            )
            data_linha = _data_da_linha(texto_esquerda, ano_ref)
            if data_linha is not None:
                data_atual = data_linha

            historico = " ".join(
                faixa[
                    (faixa["cx"] >= largura * 0.16)
                    & (faixa["cx"] < largura * 0.56)
                ].sort_values(["top", "left"])["text"]
            )
            historico = re.sub(r"\s+", " ", historico).strip(" |—-")
            hist_norm = _norm(historico)
            hist_compacto = hist_norm.replace(" ", "")

            saldo = item.get("saldo")
            credito = item.get("credito")
            debito = item.get("debito")

            # Linhas Total têm crédito e débito simultâneos. Servem apenas para validar.
            if credito is not None and debito is not None:
                totais_impressos.append({
                    "pagina": numero_pagina,
                    "credito": abs(float(credito)),
                    "debito": -abs(float(debito)),
                    "saldo": float(saldo) if saldo is not None else None,
                })
                continue

            if "SALDOANTERIOR" in hist_compacto:
                if saldo is not None:
                    saldo_atual = float(saldo)
                continue
            if hist_norm.startswith("TOTAL"):
                continue
            if "SALDOINVEST" in hist_compacto:
                continue
            if data_atual is None:
                continue

            valor_impresso = None
            if credito is not None:
                valor_impresso = abs(float(credito))
            elif debito is not None:
                valor_impresso = -abs(float(debito))

            valor = None
            mesma_data = bool(
                lancamentos
                and pd.Timestamp(lancamentos[-1]["DATA"]).normalize() == data_atual.normalize()
            )

            # O valor da coluna Crédito/Débito é a fonte principal. O saldo só recupera
            # valor ausente quando estamos na mesma data, evitando saltos do Invest Fácil.
            if valor_impresso is not None:
                valor = round(valor_impresso, 2)
                if saldo is not None:
                    saldo_atual = float(saldo)
                elif saldo_atual is not None:
                    saldo_atual = round(saldo_atual + valor, 2)
            elif saldo is not None and saldo_atual is not None and mesma_data:
                valor = round(float(saldo) - saldo_atual, 2)
                saldo_atual = float(saldo)
            elif saldo is not None:
                saldo_atual = float(saldo)
                continue

            if valor is None or abs(valor) < 0.005:
                continue
            if not historico or hist_norm.startswith(("AGENCIA", "EXTRATO DE", "TOTAL")):
                continue

            lancamentos.append({
                "DESCRIÇÃO": "BANCO BRADESCO",
                "DATA": data_atual.to_pydatetime(),
                "VALOR": round(valor, 2),
                "DÉBITO": "",
                "CRÉDITO": "",
                "HISTÓRICO": historico,
            })

    # Evita duplicidade causada por uma mesma linha reconhecida pelos dois OCRs.
    unicos = []
    vistos = set()
    for item in lancamentos:
        chave = (
            pd.Timestamp(item["DATA"]),
            round(float(item["VALOR"]), 2),
            _norm(item["HISTÓRICO"]),
        )
        if chave in vistos:
            continue
        vistos.add(chave)
        unicos.append(item)

    total_creditos = round(sum(x["VALOR"] for x in unicos if x["VALOR"] > 0), 2)
    total_debitos = round(sum(x["VALOR"] for x in unicos if x["VALOR"] < 0), 2)
    esperado_creditos = round(sum(x["credito"] for x in totais_impressos), 2)
    esperado_debitos = round(sum(x["debito"] for x in totais_impressos), 2)
    diferenca_creditos = round(total_creditos - esperado_creditos, 2)
    diferenca_debitos = round(total_debitos - esperado_debitos, 2)

    diagnostico = {
        "lancamentos": len(unicos),
        "creditos_lidos": total_creditos,
        "debitos_lidos": total_debitos,
        "creditos_extrato": esperado_creditos,
        "debitos_extrato": esperado_debitos,
        "diferenca_creditos": diferenca_creditos,
        "diferenca_debitos": diferenca_debitos,
        "totais_encontrados": len(totais_impressos),
        "ok": (
            bool(totais_impressos)
            and abs(diferenca_creditos) <= 0.02
            and abs(diferenca_debitos) <= 0.02
        ),
    }
    return unicos, diagnostico
