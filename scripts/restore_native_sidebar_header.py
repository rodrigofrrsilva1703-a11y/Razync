from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
old = '''        header[data-testid="stHeader"] {
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
new = '''        header[data-testid="stHeader"] {
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
if old not in s:
    raise SystemExit('Bloco customizado atual do header não encontrado')
s = s.replace(old, new, 1)
# Mantém o conteúdo visualmente alto mesmo com o header nativo restaurado.
marker = '/* Global top spacing v4 */'
if marker in s and '/* Native sidebar header restore v5 */' not in s:
    s = s.replace(marker, marker + '''\n        /* Native sidebar header restore v5 */\n        main[data-testid="stMain"] .block-container,\n        .stMainBlockContainer {\n            transform: translateY(-2.7rem);\n            padding-bottom: 0 !important;\n        }\n        @media (max-width: 900px) {\n            main[data-testid="stMain"] .block-container,\n            .stMainBlockContainer { transform: translateY(-1.8rem); }\n        }\n''', 1)
p.write_text(s, encoding='utf-8')
