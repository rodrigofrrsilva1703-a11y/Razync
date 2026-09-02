from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
old = '''        #MainMenu,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        footer {
'''
new = '''        #MainMenu,
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        footer {
'''
if old not in s:
    raise SystemExit('Lista de ocultação do chrome não encontrada')
s = s.replace(old, new, 1)

marker = '/* Sidebar toolbar parent fix v6 */'
if marker not in s:
    needle = '        header[data-testid="stHeader"] {\n'
    css = '''        /* Sidebar toolbar parent fix v6 */\n        [data-testid="stToolbar"] {\n            display: flex !important;\n            visibility: visible !important;\n            opacity: 1 !important;\n            pointer-events: auto !important;\n            background: transparent !important;\n            box-shadow: none !important;\n            z-index: 1000000 !important;\n        }\n        [data-testid="stToolbar"] > div {\n            pointer-events: auto !important;\n        }\n\n'''
    if needle not in s:
        raise SystemExit('Header do Streamlit não encontrado')
    s = s.replace(needle, css + needle, 1)

p.write_text(s, encoding='utf-8')
# trigger
