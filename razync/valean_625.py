"""Leitores bancários da empresa 625 - Valean.

Converte extratos PDF do Banco do Brasil, Caixa e Sicredi para o padrão
do Modelo Domínio. A Caixa usa OCR apenas quando o PDF não possui texto.
"""

from __future__ import annotations

import io
import re
import unicodedata

import pandas as pd
from pypdf import PdfReader

COLUNAS_MODELO = ["DESCRIÇÃO", "DATA", "VALOR", "DÉBITO", "CRÉDITO", "HISTÓRICO"]
CONTAS_VALEAN_625 = {"banco_brasil": "8", "caixa": "504", "sicredi": "3999"}
NOMES_BANCOS = {
    "banco_brasil": "BANCO DO BRASIL",
    "caixa": "CAIXA ECONÔMICA FEDERAL",
    "sicredi": "SICREDI",
}


def _normalizar(valor) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", texto).strip().casefold()


def _valor_br(token: str, natureza: str = "") -> float:
    texto = str(token or "").replace("R$", "").replace(" ", "").strip()
    sinal = -1 if texto.startswith("-") or str(natureza).upper() == "D" else 1
    texto = texto.lstrip("+-").replace(".", "").replace(",", ".")
    return round(sinal * float(texto), 2)


def _limpar_cpf_cnpj_historico(texto: str) -> str:
    """Remove CPF/CNPJ dos históricos da empresa 625.

    Trata os formatos reais observados nos extratos BB e Sicredi, inclusive
    documentos sem máscara no meio da descrição. Preserva números que não têm
    11 ou 14 dígitos, como nomes empresariais do tipo ``63.006.516 EDIMARCO``.
    """
    texto = str(texto or "")
    doc = (
        r"(?:\d{3}\.?\d{3}\.?\d{3}-?\d{2}"
        r"|\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}"
        r"|\d{11}|\d{14})"
    )

    # Banco do Brasil: algumas linhas trazem banco/agência antes do CNPJ.
    texto = re.sub(
        rf"(?<!\d)\d{{3}}\s+\d{{4}}\s+(?={doc}(?!\d))",
        " ", texto, flags=re.I,
    )
    # Banco do Brasil: PIX pode trazer data/hora auxiliar antes do CPF/CNPJ.
    texto = re.sub(
        rf"(?<!\d)\d{{2}}/\d{{2}}\s+\d{{2}}:\d{{2}}\s+(?={doc}(?!\d))",
        " ", texto, flags=re.I,
    )
    # Remove rótulos e documentos com/sem máscara.
    texto = re.sub(
        rf"\b(?:CPF|CNPJ)\b\s*[:\-]?\s*(?={doc}(?!\d))",
        " ", texto, flags=re.I,
    )
    texto = re.sub(rf"(?<!\d){doc}(?!\d)", " ", texto, flags=re.I)
    texto = re.sub(r"\b(?:CPF|CNPJ)\b\s*[:\-]?", " ", texto, flags=re.I)
    return re.sub(r"\s+", " ", texto).strip(" -|;,:.")


def _registro(banco: str, data, valor: float, historico: str) -> dict:
    conta = CONTAS_VALEAN_625[banco]
    historico = re.sub(r"\s+", " ", str(historico or "MOVIMENTO BANCÁRIO")).strip()
    historico = re.sub(r"^(?:recebido|pago):\s*", "", historico, flags=re.I)
    historico = _limpar_cpf_cnpj_historico(historico) or "MOVIMENTO BANCÁRIO"
    historico = ("Recebido: " if valor > 0 else "Pago: ") + historico
    return {
        "DESCRIÇÃO": NOMES_BANCOS[banco],
        "DATA": pd.Timestamp(data).normalize(),
        "VALOR": round(float(valor), 2),
        "DÉBITO": conta if valor > 0 else "",
        "CRÉDITO": conta if valor < 0 else "",
        "HISTÓRICO": historico,
    }


def _texto_pdf(conteudo: bytes) -> str:
    leitor = PdfReader(io.BytesIO(conteudo), strict=False)
    textos = []
    for pagina in leitor.pages:
        try:
            textos.append(pagina.extract_text(extraction_mode="layout") or "")
        except TypeError:
            textos.append(pagina.extract_text() or "")
    return "\n".join(textos)


def _texto_ocr_caixa(conteudo: bytes) -> str:
    try:
        import fitz
        import pytesseract
        from PIL import Image, ImageOps
    except ImportError as erro:
        raise ValueError("O leitor OCR necessário para o extrato Caixa não está instalado.") from erro

    documento = fitz.open(stream=conteudo, filetype="pdf")
    paginas = []
    try:
        for pagina in documento:
            pix = pagina.get_pixmap(matrix=fitz.Matrix(3.2, 3.2), alpha=False)
            imagem = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            imagem = ImageOps.autocontrast(ImageOps.grayscale(imagem))
            try:
                texto = pytesseract.image_to_string(
                    imagem, lang="por", config="--psm 6 -c preserve_interword_spaces=1"
                )
            except pytesseract.TesseractError:
                texto = pytesseract.image_to_string(
                    imagem, config="--psm 6 -c preserve_interword_spaces=1"
                )
            paginas.append(texto or "")
    finally:
        documento.close()
    return "\n".join(paginas)


def processar_bb_625(conteudo: bytes) -> pd.DataFrame:
    texto = _texto_pdf(conteudo)
    blocos = []
    atual = []
    for linha in texto.splitlines():
        linha = re.sub(r"\s+", " ", linha).strip()
        if re.match(r"^\d{2}/\d{2}/\d{4}", linha):
            if atual:
                blocos.append(atual)
            atual = [linha]
        elif atual and linha and not linha.lower().startswith(("https://", "pagina ")):
            atual.append(linha)
    if atual:
        blocos.append(atual)

    registros = []
    moeda = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2})\s*([CD])", re.I)
    for bloco in blocos:
        primeira = bloco[0]
        data = pd.to_datetime(primeira[:10], dayfirst=True, errors="coerce")
        valores = list(moeda.finditer(primeira))
        if pd.isna(data) or not valores:
            continue
        movimento = valores[0]
        valor = _valor_br(movimento.group(1), movimento.group(2))
        antes = primeira[10:movimento.start()]
        antes = re.sub(r"^\s*\d{4}\s+\d{5,8}\s*", "", antes)
        antes = re.sub(r"\s+\d[\d.]{2,}$", "", antes).strip()
        complementos = [x for x in bloco[1:] if not _normalizar(x).startswith(
            ("cliente", "agencia", "conta corrente", "periodo", "lancamentos", "dt.")
        )]
        historico = " ".join([antes] + complementos).strip()
        if "saldo" in _normalizar(historico):
            continue
        registros.append(_registro("banco_brasil", data, valor, historico))
    return _finalizar(registros, "Banco do Brasil")


def processar_sicredi_625(conteudo: bytes) -> pd.DataFrame:
    texto = _texto_pdf(conteudo)
    moeda = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2}")
    registros = []
    for linha in texto.splitlines():
        linha = re.sub(r"\s+", " ", linha).strip()
        data_match = re.match(r"^(\d{2}/\d{2}/\d{4})", linha)
        valores = list(moeda.finditer(linha))
        if not data_match or len(valores) < 2:
            continue
        data = pd.to_datetime(data_match.group(1), dayfirst=True, errors="coerce")
        movimento = valores[-2]
        historico = linha[10:movimento.start()].strip()
        historico = re.sub(r"\s+[A-Za-z][A-Za-z0-9._-]{2,}\s*$", "", historico)
        valor = _valor_br(movimento.group())
        if pd.isna(data) or abs(valor) < 0.005 or "saldo" in _normalizar(historico):
            continue
        registros.append(_registro("sicredi", data, valor, historico))
    return _finalizar(registros, "Sicredi")


def processar_caixa_625(conteudo: bytes) -> pd.DataFrame:
    texto = _texto_pdf(conteudo)
    if not texto.strip():
        texto = _texto_ocr_caixa(conteudo)

    padrao = re.compile(
        r"^(\d{2}/\d{2}/\d{4})\s+(?:\d{2}/\d{2}\s+\d{2}:\d{2}\s+)?"
        r"(?:\d{6,}\s+)?(.+?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s*([CD])"
        r"(?:\s+\d{1,3}(?:\.\d{3})*,\d{2}\s*[CD])?\s*$",
        flags=re.I,
    )
    registros = []
    for linha in texto.splitlines():
        linha = re.sub(r"\s+", " ", linha).strip()
        achado = padrao.match(linha)
        if not achado:
            continue
        data = pd.to_datetime(achado.group(1), dayfirst=True, errors="coerce")
        historico = achado.group(2).strip(" -|")
        valor = _valor_br(achado.group(3), achado.group(4))
        if pd.isna(data) or abs(valor) < 0.005 or "saldo" in _normalizar(historico):
            continue
        registros.append(_registro("caixa", data, valor, historico))
    return _finalizar(registros, "Caixa")


def _finalizar(registros: list[dict], banco: str) -> pd.DataFrame:
    if not registros:
        raise ValueError(f"Nenhum lançamento válido foi encontrado no extrato {banco}.")
    return pd.DataFrame(registros, columns=COLUNAS_MODELO).sort_values(
        "DATA", kind="stable"
    ).reset_index(drop=True)


def processar_extrato_625(conteudo: bytes, banco: str) -> pd.DataFrame:
    leitores = {
        "banco_brasil": processar_bb_625,
        "caixa": processar_caixa_625,
        "sicredi": processar_sicredi_625,
    }
    if banco not in leitores:
        raise ValueError(f"Banco não configurado para a empresa 625: {banco}")
    return leitores[banco](conteudo)
