from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

replacements = [
    (
        'def renderizar_conferencia_autokraft():\n',
        "def renderizar_conferencia_autokraft(prefixo_chaves='autokraft'):\n"
    ),
    (
        '        key="autokraft_conferir_todos"\n',
        '        key=f"{prefixo_chaves}_conferir_todos"\n'
    ),
    (
        '            key="autokraft_bancos_conferencia"\n',
        '            key=f"{prefixo_chaves}_bancos_conferencia"\n'
    ),
    (
        '            key="autokraft_planilha_final_conferencia",\n',
        '            key=f"{prefixo_chaves}_planilha_final_conferencia",\n'
    ),
    (
        '                "autokraft_extratos_conferencia_"\n',
        '                f"{prefixo_chaves}_extratos_conferencia_"\n'
    ),
    (
        '            key="autokraft_periodo_conferencia"\n',
        '            key=f"{prefixo_chaves}_periodo_conferencia"\n'
    ),
    (
        '        renderizar_conferencia_autokraft()\n',
        '        renderizar_conferencia_autokraft(slug_empresa_autokraft)\n'
    ),
]

for old, new in replacements:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'Esperava 1 ocorrência de {old!r}, encontrei {count}.')
    text = text.replace(old, new, 1)

state_block = '''        # Evita reaproveitar uploads e seleções de conferência de outra empresa.\n        if st.session_state.get('_autokraft_empresa_ativa') != slug_empresa_autokraft:\n            for chave_estado in [\n                'autokraft_conferir_todos', 'autokraft_bancos_conferencia',\n                'autokraft_planilha_final_conferencia', 'autokraft_extrato_itau',\n                'autokraft_extrato_daycoval'\n            ]:\n                st.session_state.pop(chave_estado, None)\n            st.session_state['_autokraft_empresa_ativa'] = slug_empresa_autokraft\n\n'''
if text.count(state_block) != 1:
    raise SystemExit('Bloco antigo de limpeza de estado não encontrado exatamente uma vez.')
text = text.replace(state_block, '', 1)

path.write_text(text, encoding='utf-8')
print('Conferência Autokraft isolada por empresa.')
