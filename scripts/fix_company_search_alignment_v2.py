from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old = '''            [class*="st-key-org_linha_empresa_"] [data-testid="stColumn"] {
                display: flex;
                align-items: center;
                min-height: 2.25rem;
            }
            [class*="st-key-org_linha_empresa_"] [data-testid="stColumn"] > div {
                width: 100%;
            }
'''
new = '''            [class*="st-key-org_linha_empresa_"] [data-testid="stColumn"] {
                display: flex !important;
                align-items: center !important;
                min-height: 2.55rem !important;
            }
            [class*="st-key-org_linha_empresa_"] [data-testid="stColumn"] > div {
                width: 100%;
            }
            [class*="st-key-org_linha_empresa_"] [data-testid="stMarkdown"] {
                display: flex !important;
                align-items: center !important;
                min-height: 2rem !important;
            }
            [class*="st-key-org_linha_empresa_"] [data-testid="stMarkdownContainer"] {
                display: flex !important;
                align-items: center !important;
                min-height: 2rem !important;
                width: 100%;
            }
'''
if old not in text:
    raise SystemExit('Bloco estrutural da pesquisa não encontrado.')
text = text.replace(old, new, 1)

text = text.replace('''                font-size: 0.76rem !important;\n                line-height: 1.35 !important;\n''', '''                font-size: 0.82rem !important;\n                line-height: 1.35 !important;\n''', 1)

old = '''            [class*="st-key-org_linha_empresa_"] button {
                width: auto !important;
                min-height: 1.9rem !important;
                padding: 0.12rem 0 !important;
                justify-content: flex-start !important;
                text-align: left !important;
                border: 0 !important;
                background: transparent !important;
                box-shadow: none !important;
            }
'''
new = '''            [class*="st-key-org_linha_empresa_"] button {
                width: 100% !important;
                min-height: 2rem !important;
                height: auto !important;
                padding: 0 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: flex-start !important;
                text-align: left !important;
                border: 0 !important;
                background: transparent !important;
                box-shadow: none !important;
            }
'''
if old not in text:
    raise SystemExit('Botão da empresa não encontrado.')
text = text.replace(old, new, 1)

old = '''            [class*="st-key-org_linha_empresa_"] button p {
                color: #e7edf2 !important;
                font-size: 0.76rem !important;
                font-weight: 600 !important;
                line-height: 1.35 !important;
                text-align: left !important;
                text-decoration: none !important;
            }
'''
new = '''            [class*="st-key-org_linha_empresa_"] button p {
                color: #e7edf2 !important;
                font-size: 0.82rem !important;
                font-weight: 600 !important;
                line-height: 1.35 !important;
                text-align: left !important;
                text-decoration: none !important;
            }
'''
if old not in text:
    raise SystemExit('Texto do nome da empresa não encontrado.')
text = text.replace(old, new, 1)

old = '''            .rz-company-code {
                display: inline-flex;
                align-items: center;
                min-height: 1.9rem;
                color: #7f91a1;
                font-size: 0.76rem;
                font-weight: 600;
                line-height: 1.35;
            }
'''
new = '''            .rz-company-code {
                display: inline-flex !important;
                align-items: center !important;
                min-height: 2rem !important;
                color: #7f91a1;
                font-size: 0.82rem !important;
                font-weight: 600 !important;
                line-height: 1.35 !important;
            }
'''
if old not in text:
    raise SystemExit('Código da empresa não encontrado.')
text = text.replace(old, new, 1)

path.write_text(text, encoding='utf-8')
print('Pesquisa: código e nome uniformizados e centralizados.')
