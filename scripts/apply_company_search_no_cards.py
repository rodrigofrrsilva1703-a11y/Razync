from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')
old_result = """                    if st.button(\n                        f\"{empresa_catalogo['codigo']} · {empresa_catalogo['nome']}\",\n                        type='tertiary',\n                        use_container_width=True,\n                        key=f\"org_resultado_empresa_{empresa_catalogo['codigo']}\"\n                    ):"""
new_result = """                    if st.button(\n                        f\"{empresa_catalogo['codigo']} · {empresa_catalogo['nome']}\",\n                        type='tertiary',\n                        use_container_width=False,\n                        key=f\"org_resultado_empresa_{empresa_catalogo['codigo']}\"\n                    ):"""
old_active = """                if st.button(\n                    f\"{empresa_catalogo['codigo']} · {empresa_catalogo['nome']}\",\n                    type='tertiary',\n                    use_container_width=True,\n                    key=f\"org_empresa_ativa_{empresa_catalogo['codigo']}\"\n                ):"""
new_active = """                if st.button(\n                    f\"{empresa_catalogo['codigo']} · {empresa_catalogo['nome']}\",\n                    type='tertiary',\n                    use_container_width=False,\n                    key=f\"org_empresa_ativa_{empresa_catalogo['codigo']}\"\n                ):"""
if old_result not in text:
    raise SystemExit('Bloco de resultados não encontrado')
if old_active not in text:
    raise SystemExit('Bloco de empresas ativas não encontrado')
text = text.replace(old_result, new_result, 1).replace(old_active, new_active, 1)
path.write_text(text, encoding='utf-8')
