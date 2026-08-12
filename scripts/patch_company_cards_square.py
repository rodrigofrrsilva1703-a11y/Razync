from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

# Adiciona um parser específico para o extrato detalhado Itaú mostrado pelo usuário.
# Esse formato tem uma coluna de Valor apenas nos movimentos reais; linhas de saldo
# (inclusive SALDO APLIC. AUT.) devem ser totalmente ignoradas.
marker = '''def processar_pdf_daycoval_detalhado(reader, banco_identificado):
'''
helper = r'''def processar_pdf_itau_detalhado(reader, banco_identificado):
    """Lê o extrato detalhado Itaú Empresas e ignora linhas que são apenas saldos."""
    textos = [(pagina.extract_text() or '') for pagina in reader.pages]
    texto_total = '\n'.join(textos)
    texto_norm = normalizar_texto(texto_total)
    if banco_identificado != 'BANCO ITAÚ' and 'itau' not in texto_norm:
        return []
    if 'lancamentos do periodo' not in texto_norm or 'razao social' not in texto_norm:
        return []

    linhas = [re.sub(r'\s+', ' ', linha).strip() for linha in texto_total.splitlines() if linha.strip()]
    padrao_data = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(.*)$')
    blocos = []
    atual = None
    for linha in linhas:
        m = padrao_data.match(linha)
        if m:
            if atual:
                blocos.append(atual)
            atual = [m.group(1), m.group(2)]
        elif atual:
            # Complementos de razão social podem quebrar em várias linhas.
            atual[1] += ' ' + linha
    if atual:
        blocos.append(atual)

    termos_saldo = [
        'saldo anterior',
        'saldo aplic',
        'saldo aplic. aut',
        'saldo total disponivel dia',
        'saldo movimentacao conta',
        'sdo aplic aut mais ap',
        'saldo total',
        'limite da conta',
        'utilizado',
        'disponivel',
    ]
    padrao_valor = re.compile(r'(?<!\d)([-+]?\s*\d{1,3}(?:\.\d{3})*,\d{2})(?!\d)')
    lancamentos = []
    vistos = set()

    for data_str, conteudo in blocos:
        conteudo_norm = normalizar_texto(conteudo)
        if any(termo in conteudo_norm for termo in termos_saldo):
            continue
        if conteudo_norm.startswith(('aviso', 'atualizado em')):
            continue

        valores = list(padrao_valor.finditer(conteudo))
        if not valores:
            continue

        # Neste layout, o movimento real aparece como o último valor monetário do bloco.
        # Linhas de saldo já foram excluídas acima.
        valor_match = valores[-1]
        valor = limpar_valor_monetario(valor_match.group(1))
        if valor == 0:
            continue

        historico = (conteudo[:valor_match.start()] + ' ' + conteudo[valor_match.end():]).strip()
        historico = re.sub(r'\s+', ' ', historico).strip(' -|')
        if not historico:
            historico = 'MOVIMENTO BANCARIO'

        chave = (data_str, round(valor, 2), historico)
        if chave in vistos:
            continue
        vistos.add(chave)
        lancamentos.append({
            'DESCRIÇÃO': banco_identificado or 'BANCO ITAÚ',
            'DATA': data_str,
            'VALOR': valor,
            'DÉBITO': '',
            'CRÉDITO': '',
            'HISTÓRICO': limpar_caracteres_ilegais(historico)
        })

    return lancamentos

'''
if marker not in text:
    raise SystemExit('Marcador do parser Daycoval não encontrado.')
text = text.replace(marker, helper + marker, 1)

# Executa o parser Itaú específico antes do analisador estrutural universal.
old = '''        if banco_identificado == 'BANCO DAYCOVAL':
            lancamentos_daycoval = processar_pdf_daycoval_detalhado(
                reader, banco_identificado
            )
            if lancamentos_daycoval:
                return lancamentos_daycoval

        # Primeiro tenta o analisador estrutural único, independente do banco.
'''
new = '''        if banco_identificado == 'BANCO DAYCOVAL':
            lancamentos_daycoval = processar_pdf_daycoval_detalhado(
                reader, banco_identificado
            )
            if lancamentos_daycoval:
                return lancamentos_daycoval

        if banco_identificado == 'BANCO ITAÚ':
            lancamentos_itau = processar_pdf_itau_detalhado(
                reader, banco_identificado
            )
            if lancamentos_itau:
                return lancamentos_itau

        # Primeiro tenta o analisador estrutural único, independente do banco.
'''
if text.count(old) != 1:
    raise SystemExit(f'Ponto de entrada do PDF encontrado {text.count(old)} vezes.')
text = text.replace(old, new, 1)

# Validações do comportamento pedido.
checks = [
    'def processar_pdf_itau_detalhado',
    "'saldo aplic'",
    "'saldo total disponivel dia'",
    "'saldo movimentacao conta'",
    "'sdo aplic aut mais ap'",
    "lancamentos_itau = processar_pdf_itau_detalhado",
]
for check in checks:
    if check not in text:
        raise SystemExit(f'Validação falhou: não encontrei {check!r}.')

path.write_text(text, encoding='utf-8')
print('Extrato detalhado Itaú suportado; saldos de aplicação e demais linhas de saldo são ignorados.')
