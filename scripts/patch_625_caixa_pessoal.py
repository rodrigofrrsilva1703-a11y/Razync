from pathlib import Path

path = Path('razync/valean_625.py')
text = path.read_text(encoding='utf-8')
start = text.index('def processar_caixa_625(conteudo: bytes) -> pd.DataFrame:')
end = text.index('\n\ndef _finalizar(', start)

new_func = r'''def processar_caixa_625(conteudo: bytes) -> pd.DataFrame:
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
'''

path.write_text(text[:start] + new_func + text[end:], encoding='utf-8')
