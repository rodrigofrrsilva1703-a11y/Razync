from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
old = '.block-container { padding-top: 3.25rem; padding-bottom: 3rem; max-width: 100%; }'
new = '.block-container { padding-top: 1.15rem; padding-bottom: 2.25rem; max-width: 100%; }'
if old not in s:
    raise SystemExit('Regra global de espaçamento não encontrada')
s = s.replace(old, new, 1)
marker = '/* Main content vertical alignment v2 */'
if marker not in s:
    needle = '        .stApp > header {\n            background: transparent !important;\n        }\n'
    css = '''\n        /* Main content vertical alignment v2 */\n        main[data-testid="stMain"] .block-container {\n            padding-top: 1.15rem !important;\n        }\n\n        @media (min-width: 1000px) {\n            main[data-testid="stMain"] .block-container {\n                padding-top: .85rem !important;\n            }\n        }\n'''
    if needle in s:
        s = s.replace(needle, needle + css, 1)
p.write_text(s, encoding='utf-8')
