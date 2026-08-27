from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

old_detect = """    for conta, banco in contas_nova_geracao:\n        if conta in digitos_cabecalho:\n            return banco\n    if '58.616.418' in str(texto_conteudo)[:6000]: return 'BANCO FIBRA'\n    if re.search(r'\\b0?341\\b', cabecalho): return 'BANCO ITAU'\n    return \"BANCO CONTA CORRENTE\"\n"""
new_detect = """    for conta, banco in contas_nova_geracao:\n        if conta in digitos_cabecalho:\n            return banco\n\n    # Itaú Empresas: em alguns PDFs o logotipo é imagem e a palavra \"Itaú\"\n    # não existe na camada de texto. Identificamos então pela assinatura estrutural\n    # exclusiva do extrato detalhado, sem depender do nome do arquivo.\n    assinatura_itau = (\n        'LANCAMENTOS DO PERIODO' in cabecalho\n        and 'RAZAO SOCIAL' in cabecalho\n        and 'CNPJ/CPF' in cabecalho\n        and 'VALOR (R$)' in cabecalho\n        and 'SALDO (R$)' in cabecalho\n        and ('LIMITE DA CONTA' in cabecalho or 'SALDO TOTAL' in cabecalho)\n    )\n    if assinatura_itau:\n        return 'BANCO ITAU'\n\n    if '58.616.418' in str(texto_conteudo)[:6000]: return 'BANCO FIBRA'\n    if re.search(r'\\b0?341\\b', cabecalho): return 'BANCO ITAU'\n    return \"BANCO CONTA CORRENTE\"\n"""
if old_detect not in s:
    raise SystemExit('bloco de identificação não encontrado')
s = s.replace(old_detect, new_detect, 1)

start = s.index('def processar_pdf_itau_detalhado(reader, banco_identificado):')
end = s.index('\ndef processar_pdf_daycoval_detalhado(reader, banco_identificado):', start)
new_func = r'''def processar_pdf_itau_detalhado(reader, banco_identificado):
    """Lê o extrato detalhado Itaú Empresas e ignora linhas que são apenas saldos."""
    textos = [(pagina.extract_text() or '') for pagina in reader.pages]
    texto_total = '\n'.join(textos)
    texto_norm = normalizar_texto(texto_total)
    if banco_identificado not in {'BANCO ITAU', 'BANCO ITAÚ'} and 'itau' not in texto_norm:
        return []
    if 'lancamentos do periodo' not in texto_norm or 'razao social' not in texto_norm:
        return []

    padrao_data = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(.*)$')
    padrao_valor = re.compile(r'(?<!\d)([-+]?\s*\d{1,3}(?:\.\d{3})*,\d{2})(?!\d)')
    blocos = []
    atual = None

    # Processa página a página. Alguns extratos Itaú repetem a data na primeira
    # linha da página seguinte quando um lançamento foi quebrado na virada de página.
    # Se o bloco anterior ainda não tem valor monetário e a data é a mesma, tratamos
    # a nova linha como continuação, preservando histórico e valor do mesmo movimento.
    for texto_pagina in textos:
        linhas_pagina = [
            re.sub(r'\s+', ' ', linha).strip()
            for linha in texto_pagina.splitlines()
            if linha.strip()
        ]
        for linha in linhas_pagina:
            m = padrao_data.match(linha)
            if m:
                data_nova, conteudo_novo = m.group(1), m.group(2)
                if (
                    atual
                    and atual[0] == data_nova
                    and not padrao_valor.search(atual[1])
                ):
                    atual[1] += ' ' + conteudo_novo
                    continue
                if atual:
                    blocos.append(atual)
                atual = [data_nova, conteudo_novo]
            elif atual:
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
        'saldo em conta corrente',
        'saldo disponivel',
        'saldo final',
        'saldo do dia',
        'saldo total',
        'limite da conta',
        'utilizado',
        'disponivel',
    ]
    lancamentos = []

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

        lancamentos.append({
            'DESCRIÇÃO': banco_identificado or 'BANCO ITAU',
            'DATA': data_str,
            'VALOR': valor,
            'DÉBITO': '',
            'CRÉDITO': '',
            'HISTÓRICO': limpar_caracteres_ilegais(historico)
        })

    return lancamentos
'''
s = s[:start] + new_func + s[end:]
p.write_text(s, encoding='utf-8')
