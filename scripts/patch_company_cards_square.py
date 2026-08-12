from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old = '''        /* Cards de empresas: preto azulado e completamente clicáveis. */
        .st-key-org_empresa_card_nova button,
        .st-key-org_empresa_card_autokraft button {
            width: 100% !important;
            height: 132px !important;
            min-height: 132px !important;
            padding: 14px 16px !important;
'''

new = '''        /* Cards de empresas: compactos, quadrados e centralizados. */
        .st-key-org_empresa_card_nova,
        .st-key-org_empresa_card_autokraft {
            width: 168px !important;
            max-width: 168px !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }
        .st-key-org_empresa_card_nova button,
        .st-key-org_empresa_card_autokraft button {
            width: 168px !important;
            min-width: 168px !important;
            max-width: 168px !important;
            height: 168px !important;
            min-height: 168px !important;
            max-height: 168px !important;
            padding: 14px 14px !important;
'''

if text.count(old) != 1:
    raise SystemExit(f'Bloco esperado encontrado {text.count(old)} vezes; alteração cancelada.')

text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
print('Cards das empresas ajustados para 168x168 px e centralizados.')
