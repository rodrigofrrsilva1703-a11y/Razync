from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

if 'def processar_pdf_fibra_extrato' not in s:
    marcador = "def processar_arquivo_pdf(caminho_pdf, filename_original=None):"
    if marcador not in s:
        raise SystemExit('Ponto de inserção do parser Fibra não encontrado.')

    funcao = r'''def processar_pdf_fibra_extrato(reader, banco_identificado='BANCO FIBRA'):
    """Lê o extrato de C/C do Banco Fibra sem depender do layout posicional do PDF."""
    texto_total = '\n'.join((pagina.extract_text() or '') for pagina in reader.pages)
    texto_norm = normalizar_texto(texto_total)
    if banco_identificado != 'BANCO FIBRA' and 'banco fibra' not in texto_norm:
        return []
    if 'extrato de c/c para simples conferencia' not in texto_norm:
        return []

    linhas = [re.sub(r'\s+', ' ', linha.replace('\x00', '')).strip()
              for linha in texto_total.splitlines() if linha.strip()]
    regex_data = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(.*)$')
    regex_valor = re.compile(r'R\$\s*([\d.]+,\d{2})|(?<!\d)([\d.]+,\d{2})(?!\d)')

    blocos = []
    atual = None
    for linha in linhas:
        norm = normalizar_texto(linha)
        if norm.startswith(('posicao em:', 'saldo atual:', '= disponivel:', 'saldo liquido:',
                            'lancamentos futuros:', 'tarifas pendentes:', 'previsao encargos:',
                            '= saldo provisionado:', 'fim de relatorio')):
            if atual:
                blocos.append(atual)
                atual = None
            break
        if norm.startswith('saldo '):
            if atual:
                blocos.append(atual)
                atual = None
            continue
        if norm.startswith(('pagina ', 'sujeito a alteracoes')):
            continue

        m = regex_data.match(linha)
        if m:
            if atual:
                blocos.append(atual)
            atual = {'data': m.group(1), 'linhas': [m.group(2)]}
        elif atual:
            atual['linhas'].append(linha)
    if atual:
        blocos.append(atual)

    lancamentos = []
    for bloco in blocos:
        conteudo = ' '.join(bloco['linhas'])
        norm = normalizar_texto(conteudo)
        if any(t in norm for t in ['saldo anterior', 'saldo atual', 'saldo provisionado']):
            continue

        valores = []
        for m in regex_valor.finditer(conteudo):
            token = m.group(1) or m.group(2)
            if token:
                valores.append((m, token))
        if not valores:
            continue

        # O extrato Fibra possui um único valor de movimento por lançamento.
        # O saldo aparece em linhas separadas iniciadas por SALDO e já foi removido.
        m_valor, token_valor = valores[-1]
        valor_abs = abs(limpar_valor_monetario(token_valor))
        if valor_abs < 0.005:
            continue

        hist = re.sub(r'\s+', ' ', (conteudo[:m_valor.start()] + ' ' + conteudo[m_valor.end():])).strip()
        hist_norm = normalizar_texto(hist)

        # Natureza explícita do formato Fibra. Essas regras vêm antes da heurística
        # universal porque o PDF textual não preserva as posições Débito/Crédito.
        if any(t in hist_norm for t in [
            'ted emitido', 'tarifa', 'debito', 'pix enviado', 'pagamento',
            'saque', 'transferencia enviada', 'ted enviado', 'doc emitido'
        ]):
            valor = -valor_abs
        elif any(t in hist_norm for t in [
            'ted recebido', 'pix recebido', 'credito', 'deposito',
            'transferencia recebida', 'recebimento'
        ]):
            valor = valor_abs
        else:
            valor = interpretar_sinal_inteligente(hist, valor_abs)

        try:
            data = datetime.strptime(bloco['data'], '%d/%m/%Y')
        except ValueError:
            continue

        lancamentos.append({
            'DESCRIÇÃO': banco_identificado or 'BANCO FIBRA',
            'DATA': data,
            'VALOR': round(valor, 2),
            'DÉBITO': '',
            'CRÉDITO': '',
            'HISTÓRICO': limpar_caracteres_ilegais(hist or 'MOVIMENTO BANCARIO')
        })

    return lancamentos

'''
    s = s.replace(marcador, funcao + marcador, 1)

chamada = """        if banco_identificado == 'BANCO BRADESCO':
            lancamentos_bradesco = processar_pdf_bradesco_mensal(
                reader, banco_identificado
            )
            if lancamentos_bradesco:
                return lancamentos_bradesco

"""
novo = chamada + """        if banco_identificado == 'BANCO FIBRA':
            lancamentos_fibra = processar_pdf_fibra_extrato(
                reader, banco_identificado
            )
            if lancamentos_fibra:
                return lancamentos_fibra

"""
if "lancamentos_fibra = processar_pdf_fibra_extrato" not in s:
    if chamada not in s:
        raise SystemExit('Bloco Bradesco para inserir chamada Fibra não encontrado.')
    s = s.replace(chamada, novo, 1)

checks = [
    'def processar_pdf_fibra_extrato',
    "'ted emitido'",
    "'ted recebido'",
    'lancamentos_fibra = processar_pdf_fibra_extrato',
]
for check in checks:
    if check not in s:
        raise SystemExit(f'Validação do patch Fibra falhou: {check}')

p.write_text(s, encoding='utf-8')
print('Parser dedicado do Banco Fibra aplicado ao leitor central.')
