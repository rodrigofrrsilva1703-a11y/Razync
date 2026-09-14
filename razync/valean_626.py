"""Leitores bancários da empresa 626 - Valean Assessoria.

Bancos configurados:
- Banco do Brasil -> conta Domínio 8
- Sicredi -> conta Domínio 1155

Aceita PDFs nativos e, no Banco do Brasil, usa OCR como fallback quando o
extrato vier escaneado. Também consolida vários períodos em um único quadro.
"""

from __future__ import annotations

import io
import re
import unicodedata
from typing import Iterable

import pandas as pd
from pypdf import PdfReader

COLUNAS_MODELO = ["DESCRIÇÃO", "DATA", "VALOR", "DÉBITO", "CRÉDITO", "HISTÓRICO"]
CONTAS_VALEAN_626 = {"banco_brasil": "8", "sicredi": "1155"}
NOMES_BANCOS = {"banco_brasil": "BANCO DO BRASIL", "sicredi": "SICREDI"}


def _normalizar(valor) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", texto).strip().casefold()


def _valor_br(token: str, natureza: str = "") -> float:
    texto = str(token or "").replace("R$", "").replace(" ", "").strip()
    sinal = -1 if texto.startswith("-") or str(natureza).upper() == "D" else 1
    texto = texto.lstrip("+-").replace(".", "").replace(",", ".")
    return round(sinal * float(texto), 2)


def _limpar_documentos_pessoais(texto: str) -> str:
    texto = str(texto or "")
    doc = (
        r"(?:\d{3}\.?\d{3}\.?\d{3}-?\d{2}"
        r"|\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}"
        r"|\d{11}|\d{14})"
    )
    texto = re.sub(rf"\b(?:CPF|CNPJ)\b\s*[:\-]?\s*(?={doc}(?!\d))", " ", texto, flags=re.I)
    texto = re.sub(rf"(?<!\d){doc}(?!\d)", " ", texto, flags=re.I)
    texto = re.sub(r"\b(?:CPF|CNPJ)\b\s*[:\-]?", " ", texto, flags=re.I)
    return re.sub(r"\s+", " ", texto).strip(" -|;,:.")


def _registro(banco: str, data, valor: float, historico: str) -> dict:
    conta = CONTAS_VALEAN_626[banco]
    hist = re.sub(r"\s+", " ", str(historico or "MOVIMENTO BANCÁRIO")).strip()
    hist = re.sub(r"^(?:recebido|pago):\s*", "", hist, flags=re.I)
    hist = _limpar_documentos_pessoais(hist) or "MOVIMENTO BANCÁRIO"
    hist = ("Recebido: " if valor > 0 else "Pago: ") + hist
    return {
        "DESCRIÇÃO": NOMES_BANCOS[banco],
        "DATA": pd.Timestamp(data).normalize(),
        "VALOR": round(float(valor), 2),
        "DÉBITO": conta if valor > 0 else "",
        "CRÉDITO": conta if valor < 0 else "",
        "HISTÓRICO": hist,
    }


def _texto_pdf(conteudo: bytes) -> str:
    leitor = PdfReader(io.BytesIO(conteudo), strict=False)
    partes = []
    for pagina in leitor.pages:
        try:
            partes.append(pagina.extract_text(extraction_mode="layout") or "")
        except TypeError:
            partes.append(pagina.extract_text() or "")
    return "\n".join(partes)


def _texto_ocr(conteudo: bytes) -> str:
    try:
        import fitz
        import pytesseract
        from PIL import Image, ImageOps
    except ImportError as erro:
        raise ValueError("O OCR necessário para ler o PDF escaneado não está instalado.") from erro

    documento = fitz.open(stream=conteudo, filetype="pdf")
    paginas = []
    try:
        for pagina in documento:
            pix = pagina.get_pixmap(matrix=fitz.Matrix(2.8, 2.8), alpha=False)
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


def _eh_ruido_bb(linha: str) -> bool:
    norm = _normalizar(linha)
    return (
        not norm
        or norm.startswith((
            "consultas - extrato", "cliente - conta atual", "agencia", "conta corrente",
            "periodo do extrato", "lancamentos", "dt. balancete", "limite ouro",
            "taxa lim", "custo efetivo", "data vencimento", "informacoes complementares",
            "valor total devido", "valor liberado", "despesas vinculadas", "tributos",
            "tarifa", "transforme vendas", "com o aqs", "cartao sem iof",
            "transacao efetuada", "servico de atendimento", "para deficientes"
        ))
        or "autoatendimento" in norm
        or norm.startswith(("http://", "https://", "www."))
    )


def processar_bb_626(conteudo: bytes) -> pd.DataFrame:
    texto = _texto_pdf(conteudo)
    # Os extratos BB enviados para a 626 podem ser imagens. Se não houver texto
    # bancário útil, aplica OCR automaticamente.
    if len(re.sub(r"\s+", "", texto)) < 80 or "pagamento" not in _normalizar(texto):
        texto = _texto_ocr(conteudo)

    blocos: list[list[str]] = []
    atual: list[str] = []
    for bruto in texto.splitlines():
        linha = re.sub(r"\s+", " ", bruto).strip()
        if not linha or _eh_ruido_bb(linha):
            continue
        if re.match(r"^\d{2}/\d{2}/\d{4}\b", linha):
            if atual:
                blocos.append(atual)
            atual = [linha]
        elif atual:
            atual.append(linha)
    if atual:
        blocos.append(atual)

    moeda = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2})\s*([CD])", re.I)
    registros = []
    for bloco in blocos:
        primeira = bloco[0]
        data = pd.to_datetime(primeira[:10], dayfirst=True, errors="coerce")
        valores = list(moeda.finditer(primeira))
        if pd.isna(data) or not valores:
            continue

        movimento = valores[0]
        valor = _valor_br(movimento.group(1), movimento.group(2))
        antes_bruto = primeira[10:movimento.start()]
        antes_norm = _normalizar(antes_bruto)
        # O BB usa o código estrutural 999 para a linha de saldo final.
        # Essa linha nunca representa movimento e não pode ir ao Modelo Domínio.
        antes_saldo = re.sub(r"\s+", " ", antes_norm).strip()
        tem_saldo = (
            "saldo anterior" in antes_saldo
            or re.search(r"(?:^|\s)s\s*a\s*l\s*d\s*o\s*$", antes_saldo) is not None
            or re.search(r"(?:^|\s)999(?:\s+|.*?\s+)s\s*a\s*l\s*d\s*o(?:\s|$)", antes_saldo) is not None
            or re.search(r"(?:^|\s)999\s+saldo(?:\s|$)", antes_saldo) is not None
        )
        if tem_saldo:
            continue

        # Remove agência/lote e Documento, mantendo apenas o histórico textual.
        antes = re.sub(r"^\s*(?:[=\d]+\s+){2,5}", "", antes_bruto).strip()
        antes = re.sub(r"\s+\d[\d./-]{2,}\s*$", "", antes).strip()

        complementos = []
        for comp in bloco[1:]:
            if _eh_ruido_bb(comp):
                continue
            norm = _normalizar(comp)
            if norm.startswith(("tar. agrupadas", "cobranca referente")):
                # Informação operacional do banco; não identifica favorecido.
                continue
            limpo = re.sub(r"^\d{2}/\d{2}\s+\d{2}:\d{2}\s*", "", comp).strip()
            # TED do BB costuma trazer banco/agência + CNPJ antes do nome.
            limpo = re.sub(r"^\d{3}\s+\d{4}\s+", "", limpo).strip()
            limpo = _limpar_documentos_pessoais(limpo)
            if limpo:
                complementos.append(limpo)

        historico = " ".join([antes] + complementos).strip()
        if not historico:
            historico = "MOVIMENTO BANCÁRIO"
        registros.append(_registro("banco_brasil", data, valor, historico))

    return _finalizar(registros, "Banco do Brasil")


def processar_sicredi_626(conteudo: bytes) -> pd.DataFrame:
    texto = _texto_pdf(conteudo)
    if len(re.sub(r"\s+", "", texto)) < 80:
        texto = _texto_ocr(conteudo)

    moeda = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2}")
    registros = []
    for bruto in texto.splitlines():
        linha = re.sub(r"\s+", " ", bruto).strip()
        data_match = re.match(r"^(\d{2}/\d{2}/\d{4})\s+", linha)
        if not data_match:
            continue
        valores = list(moeda.finditer(linha))
        if len(valores) < 2:
            continue

        data = pd.to_datetime(data_match.group(1), dayfirst=True, errors="coerce")
        movimento = valores[-2]
        valor = _valor_br(movimento.group())
        historico = linha[data_match.end():movimento.start()].strip()
        hist_norm = _normalizar(historico)
        if pd.isna(data) or abs(valor) < 0.005 or hist_norm == "saldo" or "saldo dia" in hist_norm:
            continue

        # Remove a coluna Documento quando aparece ao fim do trecho textual.
        historico = re.sub(
            r"\s+(?:PIX_(?:DEB|CRED)|Iof\.[A-Za-z.]+|ENC\d+|CX\d+|DAS)\s*$",
            "", historico, flags=re.I,
        ).strip()
        historico = _limpar_documentos_pessoais(historico)
        registros.append(_registro("sicredi", data, valor, historico))

    return _finalizar(registros, "Sicredi")


def _finalizar(registros: list[dict], banco: str) -> pd.DataFrame:
    if not registros:
        raise ValueError(f"Nenhum lançamento válido foi encontrado no extrato {banco}.")
    df = pd.DataFrame(registros, columns=COLUNAS_MODELO)
    df = df.drop_duplicates(subset=["DATA", "VALOR", "HISTÓRICO"], keep="first")
    return df.sort_values("DATA", kind="stable").reset_index(drop=True)


def processar_extrato_626(conteudo: bytes, banco: str) -> pd.DataFrame:
    leitores = {"banco_brasil": processar_bb_626, "sicredi": processar_sicredi_626}
    if banco not in leitores:
        raise ValueError(f"Banco não configurado para a empresa 626: {banco}")
    return leitores[banco](conteudo)


def processar_multiplos_626(arquivos: Iterable[bytes], banco: str) -> pd.DataFrame:
    quadros = []
    erros = []
    for indice, conteudo in enumerate(arquivos, start=1):
        try:
            quadros.append(processar_extrato_626(conteudo, banco))
        except Exception as erro:
            erros.append(f"arquivo {indice}: {erro}")
    if not quadros:
        detalhe = "; ".join(erros) if erros else "nenhum arquivo recebido"
        raise ValueError(f"Nenhum período pôde ser processado para {banco}: {detalhe}")
    resultado = pd.concat(quadros, ignore_index=True)
    resultado = resultado.drop_duplicates(subset=["DATA", "VALOR", "HISTÓRICO"], keep="first")
    return resultado.sort_values("DATA", kind="stable").reset_index(drop=True)
