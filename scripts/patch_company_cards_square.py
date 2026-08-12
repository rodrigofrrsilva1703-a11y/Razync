from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

replacements = {
    "if st.button('Filial', key=chave_card_filial, use_container_width=True):":
        "if st.button('1396 - Nova Geração', key=chave_card_filial, use_container_width=True):",
    "'Filial' if chave_estabelecimento == 'filial' else 'Matriz'":
        "'1396 - Nova Geração' if chave_estabelecimento == 'filial' else 'Matriz'",
    "'266 - Nova Geração Filial'\n            if chave_estabelecimento == 'filial'":
        "'1396 - Nova Geração'\n            if chave_estabelecimento == 'filial'",
    '"Filial selecionada — Itaú 98002-6 usa a conta 515 e "':
        '"1396 - Nova Geração selecionada — Itaú 98002-6 usa a conta 515 e "',
}

for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f'Trecho esperado não encontrado: {old}')
    text = text.replace(old, new, 1)

# Preserva a separação técnica da Base Inteligente.
if "'nova_geracao_filial'" not in text:
    raise SystemExit('A chave nova_geracao_filial foi perdida.')
if "st.button('1396 - Nova Geração'" not in text:
    raise SystemExit('O card da filial não recebeu o novo nome.')

path.write_text(text, encoding='utf-8')
print('Filial exibida como 1396 - Nova Geração em toda a área, mantendo base separada.')
