from pathlib import Path
# Trigger: usar exatamente as mesmas abas nativas das demais empresas.

path = Path('app.py')
text = path.read_text(encoding='utf-8')

start_marker = "        # Navegação visual padronizada com as demais empresas, mantendo execução\n"
organizer_marker = "        else:\n            st.caption(\n                'O extrato define o período e os totais oficiais. Somente os comprovantes de salários do Itaú '\n"
start = text.find(start_marker)
end = text.find(organizer_marker, start)
if start == -1 or end == -1:
    raise SystemExit('Bloco de navegação customizada da Radani não encontrado')

replacement = '''        aba_operacoes_radani, aba_base_radani = st.tabs([\n            'Organizar arquivos',\n            'Base Inteligente'\n        ])\n\n        with aba_base_radani:\n            renderizar_base_inteligente_empresa(\n                slug_radani,\n                empresa_radani,\n                {'itau', 'bradesco'},\n                config_radani['contas_bancarias']\n            )\n\n        with aba_operacoes_radani:\n            st.caption(\n                'O extrato define o período e os totais oficiais. Somente os comprovantes de salários do Itaú '\n'''
text = text[:start] + replacement + text[end + len(organizer_marker):]

old_conf = '''            st.markdown(f'#### Conferência — {empresa_radani}')\n            abrir_conferencia_radani = st.checkbox(\n                'Abrir Conferência com o extrato',\n                value=False,\n                key='radani_abrir_conferencia',\n                help='A conferência fica dentro do Organizador como nas demais empresas, mas só carrega quando aberta para preservar a performance.'\n            )\n            if abrir_conferencia_radani:\n                renderizar_conferencia_autokraft(\n                    slug_radani,\n                    bancos_config=[\n                        {'nome': 'Itaú', 'slug': 'itau'},\n                        {'nome': 'Bradesco', 'slug': 'bradesco'},\n                    ]\n                )\n'''
new_conf = '''            st.markdown(f'#### Conferência — {empresa_radani}')\n            renderizar_conferencia_autokraft(\n                slug_radani,\n                bancos_config=[\n                    {'nome': 'Itaú', 'slug': 'itau'},\n                    {'nome': 'Bradesco', 'slug': 'bradesco'},\n                ]\n            )\n'''
if old_conf not in text:
    raise SystemExit('Bloco especial de conferência da Radani não encontrado')
text = text.replace(old_conf, new_conf, 1)

if "radani_modo_ferramenta" in text:
    raise SystemExit('Navegação customizada ainda presente')
if "aba_operacoes_radani, aba_base_radani = st.tabs" not in text:
    raise SystemExit('Abas nativas não foram criadas')

path.write_text(text, encoding='utf-8')
