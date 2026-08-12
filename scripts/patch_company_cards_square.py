from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old_css = '''            .st-key-ng_card_matriz button,
            .st-key-ng_card_filial button {
                width: 100% !important;
                height: 42px !important;
                min-height: 42px !important;
                max-height: 42px !important;
                padding: 6px 12px !important;
                border-radius: 8px !important;
                border: 1px solid #12324a !important;
                background: #050b12 !important;
                box-shadow: none !important;
                transform: none !important;
                font-size: 12px !important;
                font-weight: 600 !important;
            }
'''
new_css = '''            .st-key-ng_card_matriz button,
            .st-key-ng_card_filial button {
                width: 100% !important;
                height: 52px !important;
                min-height: 52px !important;
                max-height: 52px !important;
                padding: 6px 10px !important;
                border-radius: 8px !important;
                border: 1px solid #12324a !important;
                background: #050b12 !important;
                box-shadow: none !important;
                transform: none !important;
                font-size: 12px !important;
                line-height: 1.25 !important;
                font-weight: 600 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                text-align: center !important;
                white-space: normal !important;
            }
'''
if text.count(old_css) != 1:
    raise SystemExit(f'CSS normal dos cards encontrado {text.count(old_css)} vezes.')
text = text.replace(old_css, new_css, 1)

old_active = '''            .st-key-ng_card_matriz_ativo button,
            .st-key-ng_card_filial_ativo button {
                width: 100% !important;
                height: 42px !important;
                min-height: 42px !important;
                max-height: 42px !important;
                padding: 6px 12px !important;
                border-radius: 8px !important;
                border: 1px solid #1d6f9b !important;
                background: #0b1f33 !important;
                box-shadow: none !important;
                transform: none !important;
                font-size: 12px !important;
                font-weight: 700 !important;
            }
'''
new_active = '''            .st-key-ng_card_matriz_ativo button,
            .st-key-ng_card_filial_ativo button {
                width: 100% !important;
                height: 52px !important;
                min-height: 52px !important;
                max-height: 52px !important;
                padding: 6px 10px !important;
                border-radius: 8px !important;
                border: 1px solid #1d6f9b !important;
                background: #0b1f33 !important;
                box-shadow: none !important;
                transform: none !important;
                font-size: 12px !important;
                line-height: 1.25 !important;
                font-weight: 700 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                text-align: center !important;
                white-space: normal !important;
            }
'''
if text.count(old_active) != 1:
    raise SystemExit(f'CSS ativo dos cards encontrado {text.count(old_active)} vezes.')
text = text.replace(old_active, new_active, 1)

old_cols = "        col_matriz, col_filial, col_restante = st.columns([0.14, 0.14, 0.72], gap='small')\n"
new_cols = "        col_matriz, col_filial, col_restante = st.columns([0.19, 0.19, 0.62], gap='small')\n"
if text.count(old_cols) != 1:
    raise SystemExit(f'Layout dos cards encontrado {text.count(old_cols)} vezes.')
text = text.replace(old_cols, new_cols, 1)

old_button = "            if st.button('Matriz', key=chave_card_matriz, use_container_width=True):\n"
new_button = "            if st.button('266 - Nova Geração Matriz', key=chave_card_matriz, use_container_width=True):\n"
if text.count(old_button) != 1:
    raise SystemExit(f'Botão Matriz encontrado {text.count(old_button)} vezes.')
text = text.replace(old_button, new_button, 1)

old_nome = "            '1396 - Nova Geração Filial' if chave_estabelecimento == 'filial' else 'Matriz'\n"
new_nome = "            '1396 - Nova Geração Filial' if chave_estabelecimento == 'filial' else '266 - Nova Geração Matriz'\n"
if text.count(old_nome) != 1:
    raise SystemExit(f'Nome interno visual da Matriz encontrado {text.count(old_nome)} vezes.')
text = text.replace(old_nome, new_nome, 1)

for check in [
    "st.button('266 - Nova Geração Matriz'",
    "st.button('1396 - Nova Geração Filial'",
    'height: 52px',
    "st.columns([0.19, 0.19, 0.62], gap='small')",
]:
    if check not in text:
        raise SystemExit(f'Validação falhou: {check}')

path.write_text(text, encoding='utf-8')
print('Cards Matriz/Filial alinhados, com mesmo tamanho e nomes completos.')
