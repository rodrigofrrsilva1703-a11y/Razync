from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

old = """    empresa_organizador = st.session_state['empresa_organizador']\n    empresa_catalogo_atual = EMPRESAS_POR_CHAVE.get(str(empresa_organizador))\n"""
new = """    empresa_organizador = st.session_state['empresa_organizador']\n    empresa_catalogo_atual = EMPRESAS_POR_CHAVE.get(str(empresa_organizador))\n    if empresa_catalogo_atual is None and empresa_organizador:\n        empresas_mesma_chave = [\n            empresa\n            for empresas_regime in EMPRESAS_POR_REGIME.values()\n            for empresa in empresas_regime\n            if empresa.get('chave_sistema') == empresa_organizador\n        ]\n        if empresa_organizador == 'nova_geracao' and empresas_mesma_chave:\n            estabelecimento_atual = st.session_state.get(\n                'org_estabelecimento_nova_geracao_card', 'matriz'\n            )\n            empresa_catalogo_atual = next(\n                (empresa for empresa in empresas_mesma_chave\n                 if empresa.get('estabelecimento', 'matriz') == estabelecimento_atual),\n                empresas_mesma_chave[0]\n            )\n        elif empresas_mesma_chave:\n            empresa_catalogo_atual = empresas_mesma_chave[0]\n"""
if old not in s:
    raise SystemExit('Bloco de lookup não encontrado')
s = s.replace(old, new, 1)

old_title = """            'accede_automacao': '1000 - ACCEDE AUTOMAÇÃO',\n            'accede_equipamentos': '1001 - ACCEDE EQUIPAMENTOS'\n"""
new_title = """            'accede_automacao': '1000 - ACCEDE AUTOMAÇÃO',\n            'accede_equipamentos': '1001 - ACCEDE EQUIPAMENTOS',\n            'dias_pereira': '1529 - Dias e Pereira'\n"""
if old_title not in s:
    raise SystemExit('Bloco de título não encontrado')
s = s.replace(old_title, new_title, 1)

old_placeholder = """    if empresa_catalogo_atual:\n        st.markdown(f\"### {empresa_catalogo_atual['rotulo']}\")\n        st.caption(f\"Regime tributário: {empresa_catalogo_atual['regime'].title()}\")\n        st.info(\n            \"Empresa cadastrada no Razync. As ferramentas específicas desta empresa \"\n            \"ainda não foram configuradas.\"\n        )\n"""
new_placeholder = """    if empresa_catalogo_atual and not empresa_catalogo_atual.get('chave_sistema'):\n        st.markdown(f\"### {empresa_catalogo_atual['rotulo']}\")\n        st.caption(f\"Regime tributário: {empresa_catalogo_atual['regime'].title()}\")\n        st.info(\n            \"Empresa cadastrada no Razync. As ferramentas específicas desta empresa \"\n            \"ainda não foram configuradas.\"\n        )\n"""
if old_placeholder not in s:
    raise SystemExit('Bloco de placeholder não encontrado')
s = s.replace(old_placeholder, new_placeholder, 1)

p.write_text(s, encoding='utf-8')
