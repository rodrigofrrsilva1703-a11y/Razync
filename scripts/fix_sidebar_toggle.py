from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
old = '''        header[data-testid="stHeader"] {
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
'''
new = '''        header[data-testid="stHeader"] {
            min-height: 2.4rem !important;
            height: 2.4rem !important;
            background: transparent !important;
            box-shadow: none !important;
            pointer-events: none !important;
        }

        header[data-testid="stHeader"] [data-testid="stSidebarCollapsedControl"],
        header[data-testid="stHeader"] [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapseButton"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            position: relative !important;
            z-index: 1000001 !important;
        }
'''
if old not in s:
    raise SystemExit('Bloco do header/sidebar não encontrado')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
# trigger
