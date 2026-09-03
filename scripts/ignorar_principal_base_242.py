from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

old1 = """    for nome_aba in xls.sheet_names:\n        bruto = pd.read_excel(xls, sheet_name=nome_aba, header=None, dtype=object)\n"""
new1 = """    for nome_aba in xls.sheet_names:\n        # Na empresa 242, a aba Principal é apenas a cópia preservada do relatório\n        # original. A Base Inteligente aprende somente com as abas bancárias geradas.\n        if empresa == 'eletro_forte' and normalizar_texto(nome_aba).strip() == 'principal':\n            continue\n        bruto = pd.read_excel(xls, sheet_name=nome_aba, header=None, dtype=object)\n"""
if old1 not in s:
    raise SystemExit('Bloco ler_planilha_classificada não encontrado')
s = s.replace(old1, new1, 1)

old2 = """    for ws in wb.worksheets:\n        if 'retir' in normalizar_texto(ws.title):\n            continue\n"""
new2 = """    for ws in wb.worksheets:\n        # Na 242, nunca classificar a aba Principal. Ela deve permanecer exatamente\n        # como foi recebida; somente as abas BB/Itau do Modelo Domínio são alteradas.\n        if empresa_classificacao == 'eletro_forte' and normalizar_texto(ws.title).strip() == 'principal':\n            continue\n        if 'retir' in normalizar_texto(ws.title):\n            continue\n"""
if old2 not in s:
    raise SystemExit('Bloco classificar_planilha_final não encontrado')
s = s.replace(old2, new2, 1)

old3 = """        ('Despesa', 'debito', {'0'}),\n        ('Fornecedor', 'debito', {'166', '0'}),\n        ('Recebido', 'credito', {'166', '0', '14', '16'}),\n"""
if old3 not in s:
    raise SystemExit('Configuração Base 242 não encontrada')

old4 = """            if origem == 'Despesa':\n                st.caption('Somente linhas com DÉBITO 0 serão classificadas.')\n"""
new4 = """            if origem == 'Despesa':\n                st.caption('Somente as abas bancárias serão classificadas; na Despesa, apenas linhas com DÉBITO 0. A aba Principal é preservada.')\n"""
if old4 in s:
    s = s.replace(old4, new4, 1)
else:
    # Compatibilidade com versão sem caption específica da Despesa.
    marker = """            if origem == 'Fornecedor':\n                st.caption('Somente linhas com DÉBITO 166 ou 0 serão classificadas.')\n"""
    repl = """            if origem == 'Despesa':\n                st.caption('Somente as abas bancárias serão classificadas; na Despesa, apenas linhas com DÉBITO 0. A aba Principal é preservada.')\n            elif origem == 'Fornecedor':\n                st.caption('Somente as abas bancárias serão classificadas; linhas com DÉBITO 166 ou 0. A aba Principal é preservada.')\n"""
    if marker not in s:
        raise SystemExit('Caption da Base 242 não encontrada')
    s = s.replace(marker, repl, 1)

# Ajusta as demais captions se ainda estiverem no texto antigo.
s = s.replace(
    "st.caption('Somente linhas com DÉBITO 166 ou 0 serão classificadas.')",
    "st.caption('Somente as abas bancárias serão classificadas; linhas com DÉBITO 166 ou 0. A aba Principal é preservada.')",
    1,
)
s = s.replace(
    "st.caption('Somente linhas com CRÉDITO 166, 0, 14 ou 16 serão classificadas.')",
    "st.caption('Somente as abas bancárias serão classificadas; linhas com CRÉDITO 166, 0, 14 ou 16. A aba Principal é preservada.')",
    1,
)

p.write_text(s, encoding='utf-8')
print('Aba Principal da 242 protegida da Base Inteligente')
