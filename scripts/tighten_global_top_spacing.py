from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

# Remove the old Organizer-only compensation so all pages share one predictable rule.
old = '''                <style>\n                /* Organizer directory vertical fix v3 */\n                main[data-testid="stMain"] .block-container {\n                    padding-top: 0 !important;\n                    margin-top: -5.25rem !important;\n                }\n                @media (max-width: 900px) {\n                    main[data-testid="stMain"] .block-container {\n                        margin-top: -2.25rem !important;\n                    }\n                }\n                </style>\n'''
s = s.replace(old, '')

marker = '/* Global top spacing v4 */'
if marker in s:
    raise SystemExit('Ajuste global já aplicado')

needle = '        /* Main content vertical alignment v2 */\n'
if needle not in s:
    raise SystemExit('Bloco de alinhamento global não encontrado')

css = '''        /* Global top spacing v4 */\n        main[data-testid="stMain"] {\n            padding-top: 0 !important;\n        }\n        main[data-testid="stMain"] .block-container,\n        .stMainBlockContainer {\n            padding-top: .30rem !important;\n            padding-bottom: 1.2rem !important;\n            margin-top: 0 !important;\n        }\n        section[data-testid="stSidebar"] > div,\n        section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {\n            padding-top: .45rem !important;\n        }\n        [class*="st-key-btn_voltar_home_org"],\n        [class*="st-key-btn_voltar_empresas_org"] {\n            margin-top: 0 !important;\n        }\n        .rz-dashboard-intro,\n        .rz-company-hero,\n        .rz-page-header,\n        .rz-directory-eyebrow {\n            margin-top: 0 !important;\n        }\n        h1:first-of-type, h2:first-of-type {\n            margin-top: 0 !important;\n            padding-top: 0 !important;\n        }\n        @media (max-width: 900px) {\n            main[data-testid="stMain"] .block-container,\n            .stMainBlockContainer {\n                padding-top: .55rem !important;\n            }\n        }\n\n'''
s = s.replace(needle, css + needle, 1)

# Make the previous global rule consistent instead of fighting the new rule.
s = s.replace('padding-top: 1.15rem !important;', 'padding-top: .30rem !important;', 1)
s = s.replace('padding-top: .85rem !important;', 'padding-top: .30rem !important;', 1)
s = s.replace('.block-container { padding-top: 1.15rem;', '.block-container { padding-top: .30rem;', 1)

p.write_text(s, encoding='utf-8')
