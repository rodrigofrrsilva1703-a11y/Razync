from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
start = s.index('        /* Razync sidebar-only chrome v9 */')
end = s.index('        .stApp > header', start)
old = s[start:end]
new = '''        /* Sidebar restaurada ao comportamento anterior v10 */
        [data-testid="stToolbar"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            background: transparent !important;
            box-shadow: none !important;
            z-index: 1000000 !important;
        }
        [data-testid="stToolbar"] > div {
            pointer-events: auto !important;
        }

        header[data-testid="stHeader"] {
            background: transparent !important;
            box-shadow: none !important;
        }

        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapseButton"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            z-index: 1000001 !important;
        }

'''
if 'Botão lateral Razync v8' not in old:
    raise SystemExit('Customização atual da sidebar não encontrada')
s = s[:start] + new + s[end:]
p.write_text(s, encoding='utf-8')
# trigger
