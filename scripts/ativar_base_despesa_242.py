from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
old = """    configuracoes = [
        ('Despesa', '', set()),
        ('Fornecedor', 'debito', {'166', '0'}),
        ('Recebido', 'credito', {'166', '0', '14', '16'}),
    ]
"""
new = """    configuracoes = [
        ('Despesa', 'debito', {'0'}),
        ('Fornecedor', 'debito', {'166', '0'}),
        ('Recebido', 'credito', {'166', '0', '14', '16'}),
    ]
"""
if old not in s:
    raise SystemExit('Configuração da Base Inteligente 242 não encontrada')
s = s.replace(old, new, 1)
old_caption = """            if origem == 'Fornecedor':
                st.caption('Somente linhas com DÉBITO 166 ou 0 serão classificadas.')
            elif origem == 'Recebido':
                st.caption('Somente linhas com CRÉDITO 166, 0, 14 ou 16 serão classificadas.')
"""
new_caption = """            if origem == 'Despesa':
                st.caption('Somente linhas com DÉBITO 0 serão classificadas.')
            elif origem == 'Fornecedor':
                st.caption('Somente linhas com DÉBITO 166 ou 0 serão classificadas.')
            elif origem == 'Recebido':
                st.caption('Somente linhas com CRÉDITO 166, 0, 14 ou 16 serão classificadas.')
"""
if old_caption not in s:
    raise SystemExit('Legenda das regras da Base Inteligente 242 não encontrada')
s = s.replace(old_caption, new_caption, 1)
p.write_text(s, encoding='utf-8')

assert "('Despesa', 'debito', {'0'})" in s
assert "Somente linhas com DÉBITO 0 serão classificadas." in s
print('Base Inteligente da Despesa 242 ativada para DÉBITO 0')
