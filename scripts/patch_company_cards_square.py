from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old = '''        /* Cards de empresas: quadrados, alinhados e com conteúdo contido. */
        .st-key-org_empresa_card_nova,
        .st-key-org_empresa_card_autokraft {
            width: 184px !important;
            min-width: 184px !important;
            max-width: 184px !important;
            margin: 0 auto !important;
            display: flex !important;
            justify-content: center !important;
        }
        .st-key-org_empresa_card_nova button,
        .st-key-org_empresa_card_autokraft button {
            width: 184px !important;
            min-width: 184px !important;
            max-width: 184px !important;
            height: 184px !important;
            min-height: 184px !important;
            max-height: 184px !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
            padding: 12px 13px !important;
'''

new = '''        /* Cards de empresas: maiores, próximos e alinhados ao centro. */
        .st-key-org_empresa_card_nova,
        .st-key-org_empresa_card_autokraft {
            width: 210px !important;
            min-width: 210px !important;
            max-width: 210px !important;
            display: flex !important;
            justify-content: center !important;
        }
        .st-key-org_empresa_card_nova {
            margin-left: auto !important;
            margin-right: 24px !important;
        }
        .st-key-org_empresa_card_autokraft {
            margin-left: 24px !important;
            margin-right: auto !important;
        }
        .st-key-org_empresa_card_nova button,
        .st-key-org_empresa_card_autokraft button {
            width: 210px !important;
            min-width: 210px !important;
            max-width: 210px !important;
            height: 210px !important;
            min-height: 210px !important;
            max-height: 210px !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
            padding: 16px 16px !important;
'''

if text.count(old) != 1:
    raise SystemExit(f'Bloco dos cards encontrado {text.count(old)} vezes; alteração cancelada.')

text = text.replace(old, new, 1)
text = text.replace('max-width: 154px !important;', 'max-width: 176px !important;', 1)
text = text.replace('max-width: 150px !important;', 'max-width: 172px !important;', 1)
text = text.replace('font-size: 15px !important;', 'font-size: 16px !important;', 1)

path.write_text(text, encoding='utf-8')
print('Cards aumentados para 210x210 px e aproximados do centro.')
