from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')
marker = '# Sidebar refinement v2\n'
insert = '''# Sidebar spacing refinement v3\nst.markdown("""\n<style>\n/* Desce levemente o bloco de navegação lateral sem alterar a estrutura. */\nsection[data-testid="stSidebar"] .rz-nav-label {\n    margin-top: 1.15rem !important;\n}\nsection[data-testid="stSidebar"] .rz-nav-title-gap {\n    height: 0.82rem !important;\n}\nsection[data-testid="stSidebar"] [class*="st-key-sb_"]:first-of-type {\n    margin-top: 0.3rem !important;\n}\n</style>\n""", unsafe_allow_html=True)\n\n'''
if 'Sidebar spacing refinement v3' not in text:
    if marker not in text:
        raise SystemExit('Marcador da sidebar não encontrado')
    text = text.replace(marker, insert + marker, 1)
    path.write_text(text, encoding='utf-8')
