from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
marker = '/* Streamlit chrome cleanup v1 */'
if marker in s:
    raise SystemExit('A limpeza do Streamlit já está aplicada')

needle = '        :root {\n'
if needle not in s:
    raise SystemExit('Bloco principal de CSS não encontrado')

css = '''        /* Streamlit chrome cleanup v1 */
        #MainMenu,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        footer {
            display: none !important;
            visibility: hidden !important;
        }

        header[data-testid="stHeader"] {
            min-height: 0 !important;
            height: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
        }

        header[data-testid="stHeader"] [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapseButton"] {
            display: flex !important;
            visibility: visible !important;
        }

        .stApp > header {
            background: transparent !important;
        }

'''
s = s.replace(needle, css + needle, 1)
p.write_text(s, encoding='utf-8')
