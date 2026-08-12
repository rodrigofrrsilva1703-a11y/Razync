from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old_css = '''        /* Cards de empresas: compactos, quadrados e centralizados. */
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
            cursor: pointer !important;
            background: linear-gradient(145deg, #05090e 0%, #07131f 56%, #0a1d2d 100%) !important;
            border: 1px solid #17364f !important;
            border-left: 3px solid #147eaf !important;
            border-radius: 7px !important;
            color: #91a9bb !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
            white-space: pre-line !important;
            line-height: 1.55 !important;
            font-size: 11px !important;
            font-weight: 400 !important;
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.24) !important;
            transition: transform 160ms ease, border-color 160ms ease,
                        background 180ms ease, box-shadow 180ms ease !important;
        }
        .st-key-org_empresa_card_nova button p,
        .st-key-org_empresa_card_autokraft button p {
            white-space: pre-line !important;
            margin: 0 !important;
        }
        .st-key-org_empresa_card_nova button strong,
        .st-key-org_empresa_card_autokraft button strong {
            color: #f2f8fc !important;
            font-size: 16px !important;
            line-height: 1.3 !important;
            font-weight: 700 !important;
        }
'''

new_css = '''        /* Cards de empresas: quadrados, alinhados e com conteúdo contido. */
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
            cursor: pointer !important;
            background: linear-gradient(145deg, #05090e 0%, #07131f 56%, #0a1d2d 100%) !important;
            border: 1px solid #17364f !important;
            border-left: 3px solid #147eaf !important;
            border-radius: 8px !important;
            color: #91a9bb !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
            white-space: normal !important;
            overflow-wrap: anywhere !important;
            line-height: 1.28 !important;
            font-size: 10.5px !important;
            font-weight: 400 !important;
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.24) !important;
            transition: transform 160ms ease, border-color 160ms ease,
                        background 180ms ease, box-shadow 180ms ease !important;
        }
        .st-key-org_empresa_card_nova button p,
        .st-key-org_empresa_card_autokraft button p {
            width: 100% !important;
            max-width: 154px !important;
            white-space: pre-line !important;
            overflow-wrap: anywhere !important;
            margin: 0 auto !important;
            line-height: 1.28 !important;
        }
        .st-key-org_empresa_card_nova button strong,
        .st-key-org_empresa_card_autokraft button strong {
            display: inline-block !important;
            max-width: 150px !important;
            color: #f2f8fc !important;
            font-size: 15px !important;
            line-height: 1.2 !important;
            font-weight: 700 !important;
        }
'''

if text.count(old_css) != 1:
    raise SystemExit(f'CSS esperado encontrado {text.count(old_css)} vezes; alteração cancelada.')
text = text.replace(old_css, new_css, 1)

old_nova = '''                "🏢\\n\\n**266 - Nova Geração**\\n\\n"
                "Organização, conferência e classificação dos movimentos bancários.",'''
new_nova = '''                "🏢\\n\\n**266 - Nova Geração**\\n\\n"
                "Organização bancária e conferência.",'''
if text.count(old_nova) != 1:
    raise SystemExit(f'Texto do card Nova Geração encontrado {text.count(old_nova)} vezes; alteração cancelada.')
text = text.replace(old_nova, new_nova, 1)

old_autokraft = '''                "🏭\\n\\n**Grupo Autokraft**\\n\\n"
                "Mapas diários e conferência dos bancos Itaú e Daycoval.",'''
new_autokraft = '''                "🏭\\n\\n**Grupo Autokraft**\\n\\n"
                "Mapas bancários e conferência.",'''
if text.count(old_autokraft) != 1:
    raise SystemExit(f'Texto do card Autokraft encontrado {text.count(old_autokraft)} vezes; alteração cancelada.')
text = text.replace(old_autokraft, new_autokraft, 1)

path.write_text(text, encoding='utf-8')
print('Cards ajustados para 184x184 px, alinhados e com textos contidos.')
