from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

s = s.replace('import streamlit.components.v1 as components\n', '')

old = '''_pesquisa_empresa_instantanea = components.declare_component(\n    "razync_company_search",\n    path=os.path.join(\n        os.path.dirname(__file__),\n        "components",\n        "company_search",\n    ),\n)\n'''
new = '''def _pesquisa_empresa_instantanea(value="", placeholder="Pesquisar empresa", key=None, default=None, **kwargs):\n    """Busca de empresas usando widget nativo do Streamlit.\n\n    Evita o iframe/componente customizado que podia causar NotFoundError/removeChild\n    durante reruns rápidos no Streamlit Cloud.\n    """\n    if value is None:\n        value = default or ""\n    return st.text_input(\n        "Pesquisar empresa",\n        value=str(value or ""),\n        placeholder=placeholder or "Pesquisar empresa",\n        key=key or "razync_company_search_native",\n        label_visibility="collapsed",\n    )\n'''
if old not in s:
    raise SystemExit('Bloco do componente customizado não encontrado em app.py')
s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('Busca de empresas migrada para widget nativo do Streamlit.')
