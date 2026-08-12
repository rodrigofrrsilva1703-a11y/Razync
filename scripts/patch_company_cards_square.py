from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old_key = "        chave_estabelecimento = st.session_state['org_estabelecimento_nova_geracao_card']\n"
new_key = """        chave_estabelecimento = st.session_state['org_estabelecimento_nova_geracao_card']
        nome_estabelecimento_nova = (
            'Filial' if chave_estabelecimento == 'filial' else 'Matriz'
        )
"""
if text.count(old_key) != 1:
    raise SystemExit(f'Chave do estabelecimento encontrada {text.count(old_key)} vezes.')
text = text.replace(old_key, new_key, 1)

old_upload = '''                f"Envie a planilha bancária da 266 - Nova Geração — {estabelecimento_nova}",
'''
new_upload = '''                f"Envie a planilha bancária da 266 - Nova Geração — {nome_estabelecimento_nova}",
'''
if text.count(old_upload) != 1:
    raise SystemExit(f'Referência antiga estabelecimento_nova encontrada {text.count(old_upload)} vezes.')
text = text.replace(old_upload, new_upload, 1)

# Garante que nenhuma referência executável à variável removida permaneça.
restos = [
    linha for linha in text.splitlines()
    if 'estabelecimento_nova' in linha and 'nome_estabelecimento_nova' not in linha
]
if restos:
    raise SystemExit('Ainda existem referências antigas a estabelecimento_nova: ' + ' | '.join(restos[:5]))

checks = [
    "nome_estabelecimento_nova = (",
    "{nome_estabelecimento_nova}",
    "org_estabelecimento_nova_geracao_card",
    "'nova_geracao_matriz'",
    "'nova_geracao_filial'",
]
for check in checks:
    if check not in text:
        raise SystemExit(f'Validação falhou: {check!r}')

path.write_text(text, encoding='utf-8')
print('NameError corrigido: upload usa o nome derivado do card Matriz/Filial.')
