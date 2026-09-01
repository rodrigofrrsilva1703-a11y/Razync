from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old = '''            [class*="st-key-org_linha_empresa_"] [data-testid="stHorizontalBlock"] {
                align-items: center;
            }
            [class*="st-key-org_linha_empresa_"] p {
                margin: 0 !important;
            }
            [class*="st-key-org_linha_empresa_"] [data-testid="stMarkdownContainer"] p {
                color: #7f91a1;
                font-size: 0.73rem;
            }
'''
new = '''            [class*="st-key-org_linha_empresa_"] [data-testid="stHorizontalBlock"] {
                align-items: center;
            }
            [class*="st-key-org_linha_empresa_"] [data-testid="stColumn"] {
                display: flex;
                align-items: center;
                min-height: 2.25rem;
            }
            [class*="st-key-org_linha_empresa_"] [data-testid="stColumn"] > div {
                width: 100%;
            }
            [class*="st-key-org_linha_empresa_"] p {
                margin: 0 !important;
            }
            [class*="st-key-org_linha_empresa_"] [data-testid="stMarkdownContainer"] p {
                color: #7f91a1;
                font-size: 0.76rem !important;
                line-height: 1.35 !important;
            }
'''
if old not in text:
    raise SystemExit('Bloco CSS da linha de pesquisa não encontrado.')
text = text.replace(old, new, 1)

old = '''            [class*="st-key-org_linha_empresa_"] button p {
                color: #e7edf2 !important;
                font-size: 0.78rem !important;
                font-weight: 560 !important;
                text-align: left !important;
                text-decoration: none !important;
            }
'''
new = '''            [class*="st-key-org_linha_empresa_"] button p {
                color: #e7edf2 !important;
                font-size: 0.76rem !important;
                font-weight: 600 !important;
                line-height: 1.35 !important;
                text-align: left !important;
                text-decoration: none !important;
            }
'''
if old not in text:
    raise SystemExit('Estilo do nome da empresa não encontrado.')
text = text.replace(old, new, 1)

old = '''            .rz-company-code {
                color: #7f91a1;
                font-size: 0.73rem;
                font-weight: 650;
            }
'''
new = '''            .rz-company-code {
                display: inline-flex;
                align-items: center;
                min-height: 1.9rem;
                color: #7f91a1;
                font-size: 0.76rem;
                font-weight: 600;
                line-height: 1.35;
            }
'''
if old not in text:
    raise SystemExit('Estilo do código da empresa não encontrado.')
text = text.replace(old, new, 1)

path.write_text(text, encoding='utf-8')
print('Alinhamento da pesquisa de empresas corrigido.')
