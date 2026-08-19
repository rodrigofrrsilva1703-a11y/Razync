from pathlib import Path
import re

p = Path('app.py')
s = p.read_text(encoding='utf-8')

padrao = re.compile(
    r"def processar_pdf_bradesco_mensal\(reader, banco='BANCO BRADESCO'\):.*?\n    return lancamentos\n",
    re.S,
)

novo = r'''def processar_pdf_bradesco_mensal(reader, banco='BANCO BRADESCO'):
    """Lê extratos mensais Bradesco, inclusive PDFs rasterizados via OCR."""
    lancamentos = []
    data_atual = None
    partes_historico = []
    ultimo_saldo = None
    dentro_saldos_invest = False
    modo_ocr = False

    regex_data = re.compile(r'^(\d{2}/\d{2}/\d{4})\s*[|—-]?\s*(.*)$')
    regex_moeda = re.compile(r'-?\d{1,3}(?:\.\d{3})*,\d{2}')
    ignorar_prefixos = (
        'extrato de:', 'agência | conta', 'agencia | conta', 'data lançamento',
        'data lancamento', 'folha ', 'extrato mensal / por período',
        'extrato mensal / por periodo', 'nome do usuário:', 'nome do usuario:',
        'data da operação:', 'data da operacao:', 'os dados acima têm como base',
        'os dados acima tem como base',
    )

    textos_paginas = [pagina.extract_text() or '' for pagina in reader.pages]

    # PDF-imagem: OCR somente quando não existe qualquer camada de texto.
    if not any(texto.strip() for texto in textos_paginas):
        modo_ocr = True
        try:
            import fitz
            import pytesseract
            from PIL import Image, ImageOps

            caminho_pdf = getattr(getattr(reader, 'stream', None), 'name', None)
            if caminho_pdf and os.path.exists(caminho_pdf):
                documento_ocr = fitz.open(caminho_pdf)
                textos_paginas = []
                for pagina_ocr in documento_ocr:
                    pix = pagina_ocr.get_pixmap(
                        matrix=fitz.Matrix(4.0, 4.0), alpha=False
                    )
                    imagem = Image.frombytes(
                        'RGB', [pix.width, pix.height], pix.samples
                    )
                    imagem = ImageOps.autocontrast(ImageOps.grayscale(imagem))
                    texto_ocr = pytesseract.image_to_string(
                        imagem,
                        lang='por',
                        config='--psm 6 -c preserve_interword_spaces=1'
                    )
                    textos_paginas.append(texto_ocr or '')
                documento_ocr.close()
        except Exception:
            textos_paginas = textos_paginas or []

    for texto in textos_paginas:
        for linha_bruta in texto.splitlines():
            linha = re.sub(r'\s+', ' ', linha_bruta).strip()
            if not linha:
                continue

            normalizada = normalizar_texto(linha)

            if normalizada.startswith('saldos invest facil'):
                dentro_saldos_invest = True
                partes_historico = []
                continue
            if normalizada.startswith('ultimos lancamentos'):
                dentro_saldos_invest = False
                partes_historico = []
                ultimo_saldo = None
                continue
            if normalizada.startswith(('data lancamento', 'data lançamento')):
                dentro_saldos_invest = False
                partes_historico = []
                continue
            if dentro_saldos_invest:
                continue
            if normalizada.startswith(ignorar_prefixos):
                continue
            if normalizada.startswith('nova geracao comercial') and 'cnpj:' in normalizada:
                continue
            if normalizada.startswith('total '):
                partes_historico = []
                continue

            match_data = regex_data.match(linha)
            if match_data:
                data_atual = match_data.group(1)
                linha = match_data.group(2).strip()
                normalizada = normalizar_texto(linha)
                if not linha:
                    continue

            if 'saldo anterior' in normalizada:
                moedas_saldo = regex_moeda.findall(linha)
                if moedas_saldo:
                    ultimo_saldo = limpar_valor_monetario(moedas_saldo[-1])
                partes_historico = []
                continue

            if not data_atual:
                continue

            moedas = regex_moeda.findall(linha)
            if len(moedas) >= 2:
                valor_txt = moedas[-2]
                saldo_txt = moedas[-1]
                valor_impresso = limpar_valor_monetario(valor_txt)
                saldo_lido = limpar_valor_monetario(saldo_txt)
                valor = valor_impresso

                if ultimo_saldo is not None:
                    variacao = round(saldo_lido - ultimo_saldo, 2)
                    if modo_ocr:
                        # OCR pode perder o sinal do débito ou errar um dígito do saldo.
                        # A direção do saldo define o sinal; a magnitude impressa continua
                        # sendo usada quando a leitura do saldo não fecha exatamente.
                        sinal = -1 if variacao < 0 else 1
                        if abs(abs(variacao) - abs(valor_impresso)) <= max(
                            0.05, abs(valor_impresso) * 0.01
                        ):
                            valor = variacao
                            ultimo_saldo = saldo_lido
                        else:
                            valor = sinal * abs(valor_impresso)
                            ultimo_saldo = round(ultimo_saldo + valor, 2)
                    else:
                        if abs(abs(variacao) - abs(valor_impresso)) <= 0.02:
                            valor = variacao
                        ultimo_saldo = saldo_lido
                else:
                    ultimo_saldo = saldo_lido

                inicio_valor = linha.rfind(valor_txt)
                trecho_historico = linha[:inicio_valor].strip()
                historico = re.sub(
                    r'\s+', ' ',
                    ' '.join(
                        partes_historico
                        + ([trecho_historico] if trecho_historico else [])
                    )
                ).strip(' |—-')
                partes_historico = []

                hist_norm = normalizar_texto(historico)
                if not historico or hist_norm.startswith(('saldo ', 'total ')):
                    continue
                if abs(valor) < 0.005:
                    continue

                try:
                    data = datetime.strptime(data_atual, '%d/%m/%Y')
                except ValueError:
                    continue

                lancamentos.append({
                    'DESCRIÇÃO': banco,
                    'DATA': data,
                    'VALOR': round(valor, 2),
                    'DÉBITO': '',
                    'CRÉDITO': '',
                    'HISTÓRICO': historico,
                })
            else:
                partes_historico.append(linha)
                if len(partes_historico) > 8:
                    partes_historico = partes_historico[-8:]

    return lancamentos
'''

s, n = padrao.subn(lambda _m: novo, s, count=1)
if n != 1:
    raise SystemExit(f'Leitor Bradesco encontrado {n} vezes.')

for check in [
    "modo_ocr = True",
    "fitz.Matrix(4.0, 4.0)",
    "lang='por'",
    "ImageOps.autocontrast",
    "sinal = -1 if variacao < 0 else 1",
    "if 'saldo anterior' in normalizada",
]:
    if check not in s:
        raise SystemExit(f'Check OCR ausente: {check}')

p.write_text(s, encoding='utf-8')
print('Parser Bradesco com fallback OCR robusto aplicado.')
