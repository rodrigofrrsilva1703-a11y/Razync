"""Leitores bancários da empresa 626 - Valean Assessoria.

Bancos configurados:
- Banco do Brasil -> conta Domínio 8
- Sicredi -> conta Domínio 1155

Aceita PDFs nativos e, no Banco do Brasil, usa OCR como fallback quando o
extrato vier escaneado. Também consolida vários períodos em um único quadro.
"""

from __future__ import annotations

import io
import hashlib
import re
import unicodedata
from typing import Iterable

import pandas as pd
from pypdf import PdfReader

COLUNAS_MODELO = ["DESCRIÇÃO", "DATA", "VALOR", "DÉBITO", "CRÉDITO", "HISTÓRICO"]
CONTAS_VALEAN_626 = {"banco_brasil": "8", "sicredi": "1155"}
NOMES_BANCOS = {"banco_brasil": "BANCO DO BRASIL", "sicredi": "SICREDI"}
PROCESSADOR_VALEAN_626_VERSAO = "2026-09-15-sicredi-movimentos-v8"


def _normalizar(valor) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", texto).strip().casefold()


def _valor_br(token: str, natureza: str = "") -> float:
    texto = str(token or "").replace("R$", "").replace(" ", "").strip()
    sinal = -1 if texto.startswith("-") or str(natureza).upper() == "D" else 1
    # O OCR pode trocar o separador de milhar de ponto para vírgula
    # (ex.: -2,000,00). Como os extratos sempre trazem duas casas decimais,
    # usa os dois últimos dígitos como centavos e ignora os separadores.
    digitos = re.sub(r"\D", "", texto.lstrip("+-"))
    if len(digitos) < 3:
        raise ValueError(f"Valor monetário inválido: {token}")
    return round(sinal * (int(digitos) / 100), 2)


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
    saldo_inicial_extrato = None
    data_saldo_inicial = pd.NaT
    saldo_extrato = None
    data_saldo_extrato = pd.NaT
    saldo_corrente = None
    for bloco in blocos:
        primeira = bloco[0]
        data = pd.to_datetime(primeira[:10], dayfirst=True, errors="coerce")
        valores = list(moeda.finditer(primeira))
        if pd.isna(data) or not valores:
            continue

        movimento = valores[0]
        valor = _valor_br(movimento.group(1), movimento.group(2))
        antes_bruto = primeira[10:movimento.start()]

        # O BB imprime o saldo da conta como um valor adicional na mesma linha
        # de alguns movimentos (especialmente no fechamento do dia/período).
        # Guardamos sempre o saldo da data mais recente para exibir o saldo real
        # do extrato, sem transformar esse valor em lançamento contábil.
        if len(valores) >= 2:
            saldo_match = valores[-1]
            saldo_candidato = _valor_br(saldo_match.group(1), saldo_match.group(2))
            if pd.isna(data_saldo_extrato) or data >= data_saldo_extrato:
                saldo_extrato = saldo_candidato
                data_saldo_extrato = data
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
            if "saldo anterior" in antes_saldo and valores:
                saldo_match = valores[-1]
                saldo_inicial_extrato = _valor_br(
                    saldo_match.group(1), saldo_match.group(2)
                )
                data_saldo_inicial = data
                saldo_corrente = saldo_inicial_extrato
            # Em alguns layouts a linha 999/SALDO contém apenas o saldo final.
            # Capturamos esse valor, mas a linha continua fora do Modelo Domínio.
            if valores:
                saldo_match = valores[-1]
                saldo_candidato = _valor_br(saldo_match.group(1), saldo_match.group(2))
                if pd.isna(data_saldo_extrato) or data >= data_saldo_extrato:
                    saldo_extrato = saldo_candidato
                    data_saldo_extrato = data
            continue

        # Remove agência/lote e Documento, mantendo apenas o histórico textual.
        antes = re.sub(r"^\s*(?:[=\d]+\s+){2,8}", "", antes_bruto).strip()
        antes = re.sub(r"\s+\d[\d./-]{2,}\s*$", "", antes).strip()

        # Segunda barreira contra o saldo final do BB. O OCR pode distorcer o
        # código 999 ou inserir espaços/pontuação em S A L D O; por isso, depois
        # de retirar os campos estruturais, reduzimos o texto a letras e testamos
        # o conteúdo sem depender do código numérico reconhecido.
        antes_so_letras = re.sub(r"[^a-z]", "", _normalizar(antes))
        bruto_so_letras = re.sub(r"[^a-z]", "", _normalizar(antes_bruto))
        if antes_so_letras in {"saldo", "saldoanterior"} or bruto_so_letras.endswith("saldo"):
            continue

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

        # Confere os centavos pelo saldo acumulado impresso pelo BB. O saldo não
        # aparece em todas as linhas, mas, quando aparece, permite corrigir uma
        # pequena oscilação do OCR sem criar ou excluir qualquer lançamento.
        saldo_linha = None
        if len(valores) >= 2:
            ultimo = valores[-1]
            saldo_linha = _valor_br(ultimo.group(1), ultimo.group(2))
        if saldo_corrente is not None:
            saldo_previsto = round(float(saldo_corrente) + float(valor), 2)
            if saldo_linha is not None:
                ajuste_ocr = round(float(saldo_linha) - saldo_previsto, 2)
                if 0 < abs(ajuste_ocr) <= 1.00:
                    valor = round(float(valor) + ajuste_ocr, 2)
                saldo_corrente = float(saldo_linha)
            else:
                saldo_corrente = round(float(saldo_corrente) + float(valor), 2)
        registros.append(_registro("banco_brasil", data, valor, historico))

    resultado = _finalizar(registros, "Banco do Brasil")
    if saldo_inicial_extrato is not None:
        resultado.attrs["saldo_inicial_extrato"] = round(
            float(saldo_inicial_extrato), 2
        )
        resultado.attrs["data_saldo_inicial_extrato"] = pd.Timestamp(
            data_saldo_inicial
        )
    if saldo_extrato is not None:
        resultado.attrs["saldo_extrato"] = round(float(saldo_extrato), 2)
        resultado.attrs["data_saldo_extrato"] = pd.Timestamp(data_saldo_extrato)
    return resultado


def processar_sicredi_626(conteudo: bytes) -> pd.DataFrame:
    texto = _texto_pdf(conteudo)
    if len(re.sub(r"\s+", "", texto)) < 80:
        texto = _texto_ocr(conteudo)

    moeda = re.compile(r"-?\d{1,3}(?:[.,]\d{3})*[.,]\d{2}")
    saldo_inicial_extrato = None
    for linha_saldo in texto.splitlines():
        if _normalizar(linha_saldo).startswith("saldo"):
            valores_saldo = moeda.findall(linha_saldo)
            if valores_saldo:
                saldo_inicial_extrato = _valor_br(valores_saldo[-1])
                break
    registros = []
    saldo_extrato = None
    data_saldo_extrato = pd.NaT
    saldo_corrente = saldo_inicial_extrato
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
        saldo_linha = _valor_br(valores[-1].group())
        # No Sicredi cada movimento traz o saldo resultante. Porém o OCR pode
        # perder somente o sinal negativo do saldo; nesse caso uma substituição
        # cega criaria lançamentos enormes. O valor impresso continua sendo a
        # fonte principal. A variação do saldo só corrige valor ausente ou uma
        # pequena diferença coerente de mesmo sinal e magnitude.
        if saldo_corrente is not None:
            variacao_saldo = round(float(saldo_linha) - float(saldo_corrente), 2)
            mesmo_sinal = (
                valor == 0
                or (valor > 0 and variacao_saldo > 0)
                or (valor < 0 and variacao_saldo < 0)
            )
            tolerancia = max(1.00, abs(float(valor)) * 0.01)
            magnitude_coerente = abs(variacao_saldo - float(valor)) <= tolerancia
            if abs(float(valor)) < 0.005 or (mesmo_sinal and magnitude_coerente):
                valor = variacao_saldo
        saldo_corrente = saldo_linha
        saldo_extrato = saldo_linha
        data_saldo_extrato = data
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

    resultado = _finalizar(registros, "Sicredi")
    if saldo_inicial_extrato is not None:
        primeira_data = pd.to_datetime(resultado["DATA"], errors="coerce").min()
        resultado.attrs["saldo_inicial_extrato"] = round(
            float(saldo_inicial_extrato), 2
        )
        resultado.attrs["data_saldo_inicial_extrato"] = primeira_data - pd.Timedelta(days=1)
    if saldo_extrato is not None and not pd.isna(data_saldo_extrato):
        resultado.attrs["saldo_extrato"] = round(float(saldo_extrato), 2)
        resultado.attrs["data_saldo_extrato"] = pd.Timestamp(data_saldo_extrato)
    if saldo_inicial_extrato is not None and saldo_extrato is not None:
        movimento_lido = round(float(resultado["VALOR"].sum()), 2)
        movimento_saldos = round(
            float(saldo_extrato) - float(saldo_inicial_extrato), 2
        )
        diferenca = round(movimento_lido - movimento_saldos, 2)
        resultado.attrs["diferenca_validacao_saldo"] = diferenca
        if abs(diferenca) > 0.02:
            # O saldo acumulado é apenas uma conferência auxiliar. Em PDFs
            # escaneados o OCR pode perder o sinal desse campo, mesmo lendo
            # corretamente o valor do movimento. Os cards e a planilha usam os
            # movimentos; por isso a divergência vira aviso e não elimina o mês.
            resultado.attrs["aviso_saldo_impresso"] = (
                "O saldo acumulado impresso teve leitura divergente em "
                f"R$ {abs(diferenca):,.2f}; os lançamentos foram mantidos."
            )
    return resultado


def _finalizar(registros: list[dict], banco: str) -> pd.DataFrame:
    if not registros:
        raise ValueError(f"Nenhum lançamento válido foi encontrado no extrato {banco}.")
    df = pd.DataFrame(registros, columns=COLUNAS_MODELO)
    # Não elimina linhas iguais: um extrato pode conter duas transações legítimas
    # com a mesma data, valor e favorecido (por exemplo, PIX repetidos).
    return df.sort_values("DATA", kind="stable").reset_index(drop=True)


def processar_extrato_626(conteudo: bytes, banco: str) -> pd.DataFrame:
    leitores = {"banco_brasil": processar_bb_626, "sicredi": processar_sicredi_626}
    if banco not in leitores:
        raise ValueError(f"Banco não configurado para a empresa 626: {banco}")
    return leitores[banco](conteudo)


def processar_multiplos_626(arquivos: Iterable[bytes], banco: str) -> pd.DataFrame:
    quadros = []
    erros = []
    arquivos_vistos = set()
    for indice, conteudo in enumerate(arquivos, start=1):
        assinatura = hashlib.sha256(conteudo).hexdigest()
        if assinatura in arquivos_vistos:
            continue
        arquivos_vistos.add(assinatura)
        try:
            quadros.append(processar_extrato_626(conteudo, banco))
        except Exception as erro:
            erros.append(f"arquivo {indice}: {erro}")
    # Nunca entrega uma consolidação parcial. Antes, se um PDF (como o Sicredi
    # escaneado de março) falhasse, os demais eram somados e os cards pareciam
    # válidos, porém entradas e saídas ficavam incompletas.
    if erros:
        detalhe = "; ".join(erros)
        raise ValueError(
            f"A consolidação de {banco} foi interrompida porque nem todos os "
            f"extratos foram lidos: {detalhe}"
        )
    if not quadros:
        detalhe = "; ".join(erros) if erros else "nenhum arquivo recebido"
        raise ValueError(f"Nenhum período pôde ser processado para {banco}: {detalhe}")

    # Alguns extratos mensais do BB repetem no início do arquivo seguinte
    # movimentos que já participaram do fechamento anterior (principalmente
    # devoluções de juros registradas na data de corte). Ordena os períodos e
    # mantém, em cada novo arquivo, somente datas posteriores ao último saldo
    # final já coberto. A limpeza ocorre entre arquivos, nunca dentro do mesmo
    # extrato, preservando PIX e outros lançamentos legítimos repetidos.
    def chave_periodo(quadro):
        data_inicial = quadro.attrs.get("data_saldo_inicial_extrato")
        if data_inicial is not None:
            return pd.Timestamp(data_inicial)
        datas = pd.to_datetime(quadro.get("DATA"), errors="coerce").dropna()
        return datas.min() if not datas.empty else pd.Timestamp.max

    quadros = sorted(quadros, key=chave_periodo)
    quadros_sem_sobreposicao = []
    ultima_data_coberta = None
    linhas_sobrepostas = 0
    for quadro in quadros:
        atual = quadro.copy()
        atributos = dict(quadro.attrs)
        if ultima_data_coberta is not None:
            datas = pd.to_datetime(atual["DATA"], errors="coerce")
            mascara_sobreposta = datas <= ultima_data_coberta
            linhas_sobrepostas += int(mascara_sobreposta.sum())
            atual = atual.loc[~mascara_sobreposta].copy()
        atual.attrs.update(atributos)
        if not atual.empty:
            quadros_sem_sobreposicao.append(atual)
        data_final = atributos.get("data_saldo_extrato")
        if data_final is not None:
            data_final = pd.Timestamp(data_final)
            if ultima_data_coberta is None or data_final > ultima_data_coberta:
                ultima_data_coberta = data_final

    if quadros_sem_sobreposicao:
        quadros = quadros_sem_sobreposicao
    # Preserva o saldo real do extrato mais recente quando vários períodos são
    # processados juntos. Esse saldo é apenas informativo e não vira lançamento.
    saldos = []
    saldos_iniciais = []
    avisos_saldo = []
    for quadro in quadros:
        aviso_saldo = quadro.attrs.get("aviso_saldo_impresso")
        if aviso_saldo:
            avisos_saldo.append(str(aviso_saldo))
        saldo_inicial = quadro.attrs.get("saldo_inicial_extrato")
        data_saldo_inicial = quadro.attrs.get("data_saldo_inicial_extrato")
        if saldo_inicial is not None and data_saldo_inicial is not None:
            saldos_iniciais.append(
                (pd.Timestamp(data_saldo_inicial), float(saldo_inicial))
            )
        saldo = quadro.attrs.get("saldo_extrato")
        data_saldo = quadro.attrs.get("data_saldo_extrato")
        if saldo is not None and data_saldo is not None:
            saldos.append((pd.Timestamp(data_saldo), float(saldo)))

    resultado = pd.concat(quadros, ignore_index=True)
    resultado = resultado.sort_values("DATA", kind="stable").reset_index(drop=True)
    if saldos_iniciais:
        data_saldo_inicial, saldo_inicial = min(
            saldos_iniciais, key=lambda item: item[0]
        )
        resultado.attrs["saldo_inicial_extrato"] = round(saldo_inicial, 2)
        resultado.attrs["data_saldo_inicial_extrato"] = data_saldo_inicial
    if saldos:
        data_saldo, saldo = max(saldos, key=lambda item: item[0])
        resultado.attrs["saldo_extrato"] = round(saldo, 2)
        resultado.attrs["data_saldo_extrato"] = data_saldo
    resultado.attrs["linhas_sobrepostas_ignoradas"] = linhas_sobrepostas
    resultado.attrs["arquivos_processados"] = len(quadros)
    resultado.attrs["avisos_saldo_impresso"] = avisos_saldo
    return resultado
