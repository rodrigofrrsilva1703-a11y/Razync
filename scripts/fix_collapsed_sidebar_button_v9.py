from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
old = '''        /* Razync sidebar-only chrome v7 */
        [data-testid="stToolbar"] {
            display: none !important;
            visibility: hidden !important;
        }
'''
new = '''        /* Razync sidebar-only chrome v9 */
        [data-testid="stToolbar"] {
            display: flex !important;
            visibility: hidden !important;
            opacity: 1 !important;
            pointer-events: none !important;
            background: transparent !important;
            box-shadow: none !important;
        }
        [data-testid="stToolbar"] [data-testid="stSidebarCollapsedControl"],
        [data-testid="stToolbar"] [data-testid="stSidebarCollapsedControl"] * {
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
        }
'''
if old not in s:
    raise SystemExit('Bloco toolbar v7 não encontrado')
s = s.replace(old, new, 1)

# Garante que o controle recolhido fique acima do header/toolbar e nunca herde ocultação.
needle = '''        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapseButton"] {
'''
if needle not in s:
    raise SystemExit('Bloco de controles laterais não encontrado')
insert = '''        [data-testid="stSidebarCollapsedControl"] {
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            display: flex !important;
            z-index: 2147483000 !important;
        }
'''
s = s.replace(needle, insert + needle, 1)

p.write_text(s, encoding='utf-8')
