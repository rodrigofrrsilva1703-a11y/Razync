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
NOMES_BANCOS = {"banco_brasil": "BANCO DO BRASIL", "caixa": "CAIXA ECONÔMICA FEDERAL", "sicredi": "SICREDI"}


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
    texto = str(texto or "")
    doc = r"(?:\d{3}\.?\d{3}\.?\d{3}-?\d{2}|\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}|\d{11}|\d{14})"
    texto = re.sub(rf"(?<!\d)\d{{3}}\s+\d{{4}}\s+(?={doc}(?!\d))", " ", texto, flags=re.I)
    texto = re.sub(rf"(?<!\d)\d{{2}}/\d{{2}}\s+\d{{2}}:\d{{2}}\s+(?={doc}(?!\d))", " ", texto, flags=re.I)
    texto = re.sub(rf"\b(?:CPF|CNPJ)\b\s*[:\-]?\s*(?={doc}(?!\d))", " ", texto, flags=re.I)
    texto = re.sub(rf"(?<!\d){doc}(?!\d)", " ", texto, flags=re.I)
    texto = re.sub(r"\b(?:CPF|CNPJ)\b\s*[:\-]?", " ", texto, flags=re.I)
    return re.sub(r"\s+", " ", texto).strip(" -|;,:.")


def _limpar_rodape_url_bb_historico(texto: str) -> str:
    """Remove qualquer resíduo de URL/cabeçalho/rodapé do BB do histórico."""
    texto = re.sub(r"\s+", " ", str(texto or "")).strip()
    if not texto:
        return ""

    # Se qualquer marcador de rodapé aparecer colado ao lançamento, tudo a partir
    # dele é descartado. Isso é mais seguro do que tentar remover só o token da URL,
    # pois o PDF pode concatenar contador de página e outros textos depois dela.
    marcadores = [
        r"https?\s*:\s*//",
        r"\bwww\.",
        r"\bautoatendimento2\.bb\.com\.br",
        r"\b\d{2}/\d{2}/\d{4},\s*\d{2}:\d{2}\s+banco\s+do\s+brasil\b",
    ]
    cortes = []
    for padrao in marcadores:
        achado = re.search(padrao, texto, flags=re.I)
        if achado:
            cortes.append(achado.start())
    if cortes:
        texto = texto[:min(cortes)]

    # Remove contador de página se ainda tiver sido concatenado ao final.
    texto = re.sub(r"\s+\d+\s*/\s*\d+\s*$", " ", texto)
    return re.sub(r"\s+", " ", texto).strip(" -|;,:.")


def _registro(banco: str, data, valor: float, historico: str) -> dict:
    conta = CONTAS_VALEAN_625[banco]
    historico = re.sub(r"\s+", " ", str(historico or "MOVIMENTO BANCÁRIO")).strip()
    historico = re.sub(r"^(?:recebido|pago):\s*", "", historico, flags=re.I)
    if banco == "banco_brasil":
        historico = _limpar_rodape_url_bb_historico(historico)
    historico = _limpar_cpf_cnpj_historico(historico) or "MOVIMENTO BANCÁRIO"
    if banco == "banco_brasil":
        historico = _limpar_rodape_url_bb_historico(historico) or "MOVIMENTO BANCÁRIO"
    historico = ("Recebido: " if valor > 0 else "Pago: ") + historico
    return {"DESCRIÇÃO": NOMES_BANCOS[banco], "DATA": pd.Timestamp(data).normalize(), "VALOR": round(float(valor), 2), "DÉBITO": conta if valor > 0 else "", "CRÉDITO": conta if valor < 0 else "", "HISTÓRICO": historico}


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
                texto = pytesseract.image_to_string(imagem, lang="por", config="--psm 6 -c preserve_interword_spaces=1")
            except pytesseract.TesseractError:
                texto = pytesseract.image_to_string(imagem, config="--psm 6 -c preserve_interword_spaces=1")
            paginas.append(texto or "")
    finally:
        documento.close()
    return "\n".join(paginas)


def _eh_rodape_bb(linha: str) -> bool:
    """Impede que cabeçalho/rodapé do Internet Banking seja anexado ao movimento."""
    norm = _normalizar(linha)
    return (
        norm.startswith(("http://", "https://", "pagina ", "banco do brasil", "consultas - extrato"))
        or "autoatendimento2.bb.com.br" in norm
        or re.match(r"^\d{2}/\d{2}/\d{4},\s*\d{2}:\d{2}\b", norm) is not None
        or re.fullmatch(r"\d+/\d+", norm) is not None
    )


def processar_bb_625(conteudo: bytes) -> pd.DataFrame:
    texto = _texto_pdf(conteudo)
    blocos = []
    atual = []
    for linha in texto.splitlines():
        linha = re.sub(r"\s+", " ", linha).strip()
        if not linha:
            continue
        if _eh_rodape_bb(linha):
            continue
        if re.match(r"^\d{2}/\d{2}/\d{4}\b", linha):
            if atual:
                blocos.append(atual)
            atual = [linha]
        elif atual:
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
        antes_bruto = primeira[10:movimento.start()]
        antes_bruto_norm = _normalizar(antes_bruto)
        if re.search(r"\bsaldo anterior\b", antes_bruto_norm):
            continue
        if re.search(r"(?:^|\s)s\s*a\s*l\s*d\s*o\s*$", antes_bruto_norm):
            continue
        antes = re.sub(r"^\s*\d{4}\s+\d{5,8}\s*", "", antes_bruto)
        antes = re.sub(r"\s+(?:\d[\d./-]{2,})\s*$", "", antes).strip()
        antes = _limpar_rodape_url_bb_historico(antes)

        complementos = []
        for comp in bloco[1:]:
            if _eh_rodape_bb(comp):
                continue
            norm = _normalizar(comp)
            if norm.startswith(("cliente", "agencia", "conta corrente", "periodo", "lancamentos", "dt.")):
                continue
            comp_limpo = _limpar_rodape_url_bb_historico(comp)
            comp_limpo = _limpar_cpf_cnpj_historico(comp_limpo)
            comp_limpo = re.sub(r"^\d{2}/\d{2}\s+\d{2}:\d{2}\s*", "", comp_limpo).strip()
            comp_limpo = _limpar_rodape_url_bb_historico(comp_limpo)
            if comp_limpo:
                complementos.append(comp_limpo)
        historico = " ".join([antes] + complementos).strip()
        historico = _limpar_rodape_url_bb_historico(historico)
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
    """Lê os dois layouts de extrato Caixa usados pela Valean 625.

    Suporta o SIATR antigo, com o lançamento em uma única linha, e o layout
    ``Extrato #PESSOAL``, no qual data, hora e detalhamento podem ocupar linhas
    diferentes. Saldo, SALDO DIA, número do documento e identificadores
    técnicos não viram histórico.
    """
    texto = _texto_pdf(conteudo)
    if not texto.strip():
        texto = _texto_ocr_caixa(conteudo)

    # Layout novo da Caixa (#PESSOAL). O extract_text(layout) preserva as
    # colunas, permitindo distinguir VALOR do movimento e SALDO da conta.
    if 'Descrição/Detalhamento' in texto or 'Descricao/Detalhamento' in texto or '#PESSOAL' in texto:
        valor_pat = r"\d{1,3}(?:\.\d{3})*,\d{2}"
        linha_mov = re.compile(
            rf"^\s*(\d{{2}}/\d{{2}}/\d{{4}})\s+(\d+)\s+(.*?)\s+"
            rf"({valor_pat})\s*([CD])\s+({valor_pat})\s*([CD])\s*$",
            flags=re.I,
        )
        linhas = texto.splitlines()
        registros = []
        vistos = set()

        def _util_descricao_caixa(linha: str) -> str:
            original = str(linha or '').strip()
            if not original:
                return ''
            norm = _normalizar(original)
            if (
                'saldo dia' in norm
                or norm.startswith(('extrato', '#pessoal', 'cliente:', 'conta:', 'data:', 'saldo proprio',
                                    'saldo bloqueado', 'limite contratado', 'saldo:', '*650',
                                    'movimentacoes desde', 'data/hora', 'nr. doc.'))
                or re.match(r'^\d{1,2} de [a-z]+ de \d{4}', norm)
            ):
                return ''
            # Hora sozinha ou hora antes de um complemento.
            original = re.sub(r'^\d{2}:\d{2}:\d{2}\s*', '', original).strip()
            if not original:
                return ''
            # Identificador EndToEnd do PIX e outros códigos técnicos longos.
            original = re.sub(r'\bE\d{20,}\b', ' ', original, flags=re.I)
            original = re.sub(r'\s+', ' ', original).strip()
            if not original or re.fullmatch(r'\d+', original):
                return ''
            return original

        for i, linha in enumerate(linhas):
            achado = linha_mov.match(linha)
            if not achado:
                continue
            data_txt, _documento, descricao, mov_txt, natureza = achado.group(1, 2, 3, 4, 5)
            data = pd.to_datetime(data_txt, dayfirst=True, errors='coerce')
            valor = _valor_br(mov_txt, natureza)
            if pd.isna(data) or abs(valor) < 0.005:
                continue

            partes = []
            # Alguns lançamentos (PIX) trazem o tipo da operação na linha
            # imediatamente anterior à linha que contém data/valor.
            if i > 0:
                prefixo = _util_descricao_caixa(linhas[i - 1])
                if prefixo and not linha_mov.match(linhas[i - 1]):
                    partes.append(prefixo)

            partes.append(descricao.strip())

            # Captura complementos úteis posteriores até o próximo lançamento,
            # SALDO DIA ou cabeçalho de uma nova seção/página.
            j = i + 1
            while j < len(linhas):
                prox = linhas[j]
                if linha_mov.match(prox):
                    break
                prox_norm = _normalizar(prox)
                if 'saldo dia' in prox_norm:
                    break
                if (
                    re.match(r'^\d{1,2} de [a-z]+ de \d{4}', prox_norm)
                    or prox_norm.startswith(('data/hora', 'extrato', '#pessoal', 'cliente:', 'conta:',
                                             'saldo proprio', 'saldo bloqueado', 'limite contratado',
                                             'movimentacoes desde'))
                ):
                    break
                util = _util_descricao_caixa(prox)
                if util:
                    partes.append(util)
                j += 1

            historico = ' '.join(p for p in partes if p).strip()
            historico = re.sub(r'\bE\d{20,}\b', ' ', historico, flags=re.I)
            historico = _limpar_cpf_cnpj_historico(historico)
            historico = re.sub(r'\s+', ' ', historico).strip()
            if not historico or 'saldo dia' in _normalizar(historico):
                continue

            chave = (data_txt, round(valor, 2), _normalizar(historico))
            if chave in vistos:
                continue
            vistos.add(chave)
            registros.append(_registro('caixa', data, valor, historico))

        if registros:
            return _finalizar(registros, 'Caixa')

    # Layout SIATR antigo: uma linha contém data, documento, descrição,
    # valor do movimento e saldo. O segundo valor continua sendo ignorado.
    padrao = re.compile(
        r"^_?\s*(\d{2}/\d{2}/(?:\d{2}|\d{4}))\s+"
        r"(\d{6,})\s+(.+?)\s+"
        r"(\d{1,3}(?:\.\d{3})*,\d{2})\s*([CD])"
        r"(?:\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s*([CD]))?\s*$",
        flags=re.I,
    )
    registros = []
    vistos = set()
    for linha in texto.splitlines():
        linha = re.sub(r"\s+", " ", linha).strip()
        achado = padrao.match(linha)
        if not achado:
            continue
        data_txt, _documento, historico, mov_txt, natureza = achado.group(1, 2, 3, 4, 5)
        hist_norm = _normalizar(historico)
        chave = (data_txt, _documento, hist_norm, mov_txt, natureza.upper())
        if chave in vistos:
            continue
        vistos.add(chave)
        if 'saldo dia' in hist_norm or re.fullmatch(r'saldo(?: do)? dia', hist_norm):
            continue
        data = pd.to_datetime(data_txt, dayfirst=True, errors='coerce')
        valor = _valor_br(mov_txt, natureza)
        if pd.isna(data) or abs(valor) < 0.005:
            continue
        registros.append(_registro('caixa', data, valor, historico))
    return _finalizar(registros, 'Caixa')


def _finalizar(registros: list[dict], banco: str) -> pd.DataFrame:
    if not registros:
        raise ValueError(f"Nenhum lançamento válido foi encontrado no extrato {banco}.")
    return pd.DataFrame(registros, columns=COLUNAS_MODELO).sort_values("DATA", kind="stable").reset_index(drop=True)


def processar_extrato_625(conteudo: bytes, banco: str) -> pd.DataFrame:
    leitores = {"banco_brasil": processar_bb_625, "caixa": processar_caixa_625, "sicredi": processar_sicredi_625}
    if banco not in leitores:
        raise ValueError(f"Banco não configurado para a empresa 625: {banco}")
    return leitores[banco](conteudo)
