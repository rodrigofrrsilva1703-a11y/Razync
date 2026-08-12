from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old_css = '''        /* Cards de empresas: levemente maiores e alinhados à esquerda. */
        .st-key-org_empresa_card_nova,
        .st-key-org_empresa_card_autokraft {
            width: 224px !important;
            min-width: 224px !important;
            max-width: 224px !important;
            display: flex !important;
            justify-content: flex-start !important;
            margin: 0 !important;
        }
        .st-key-org_empresa_card_nova {
            margin-right: 10px !important;
        }
        .st-key-org_empresa_card_autokraft {
            margin-left: 0 !important;
        }
        .st-key-org_empresa_card_nova button,
        .st-key-org_empresa_card_autokraft button {
            width: 224px !important;
            min-width: 224px !important;
            max-width: 224px !important;
            height: 224px !important;
            min-height: 224px !important;
            max-height: 224px !important;
'''

new_css = '''        /* Cards de empresas: alinhados à esquerda com espaçamento responsivo. */
        .st-key-org_empresa_card_nova,
        .st-key-org_empresa_card_autokraft {
            width: 218px !important;
            min-width: 218px !important;
            max-width: 218px !important;
            display: flex !important;
            justify-content: flex-start !important;
            margin: 0 !important;
        }
        .st-key-org_empresa_card_nova {
            margin-right: 18px !important;
        }
        .st-key-org_empresa_card_autokraft {
            margin-left: 0 !important;
        }
        .st-key-org_empresa_card_nova button,
        .st-key-org_empresa_card_autokraft button {
            width: 218px !important;
            min-width: 218px !important;
            max-width: 218px !important;
            height: 218px !important;
            min-height: 218px !important;
            max-height: 218px !important;
'''

if text.count(old_css) != 1:
    raise SystemExit(f'CSS atual encontrado {text.count(old_css)} vezes; alteração cancelada.')
text = text.replace(old_css, new_css, 1)
text = text.replace('max-width: 188px !important;', 'max-width: 182px !important;', 1)
text = text.replace('max-width: 184px !important;', 'max-width: 178px !important;', 1)

old_cols = '''        col_emp1, col_emp2, _espaco_empresas = st.columns([1, 1, 4])
'''
new_cols = '''        col_emp1, col_gap_empresas, col_emp2, _espaco_empresas = st.columns([1.15, 0.10, 1.15, 3.60])
'''
if text.count(old_cols) != 1:
    raise SystemExit(f'Layout atual encontrado {text.count(old_cols)} vezes; alteração cancelada.')
text = text.replace(old_cols, new_cols, 1)

# Fallback para larguras menores: mantém os cards contidos nas colunas quando a sidebar reduz a área útil.
css_marker = '''        [data-testid="stFileUploaderDropzone"] {'''
responsive_css = '''        @media (max-width: 1150px) {
            .st-key-org_empresa_card_nova,
            .st-key-org_empresa_card_autokraft {
                width: 100% !important;
                min-width: 0 !important;
                max-width: 218px !important;
            }
            .st-key-org_empresa_card_nova button,
            .st-key-org_empresa_card_autokraft button {
                width: 100% !important;
                min-width: 0 !important;
                max-width: 218px !important;
                aspect-ratio: 1 / 1 !important;
                height: auto !important;
                min-height: 190px !important;
                max-height: 218px !important;
            }
        }

'''
if css_marker not in text:
    raise SystemExit('Ponto para CSS responsivo não encontrado; alteração cancelada.')
text = text.replace(css_marker, responsive_css + css_marker, 1)

path.write_text(text, encoding='utf-8')
print('Espaçamento dos cards corrigido para sidebar aberta e larguras menores.')
