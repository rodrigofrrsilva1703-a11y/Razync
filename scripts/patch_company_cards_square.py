from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old_main = '''            background: linear-gradient(145deg, #05090e 0%, #07131f 56%, #0a1d2d 100%) !important;
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
'''
new_main = '''            background: #0b151e !important;
            border: 1px solid #1a3a4d !important;
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
            box-shadow: none !important;
            transition: background-color 150ms ease, border-color 150ms ease, color 150ms ease !important;
'''
if text.count(old_main) != 1:
    raise SystemExit(f'Estilo principal encontrado {text.count(old_main)} vezes; alteração cancelada.')
text = text.replace(old_main, new_main, 1)

old_hover = '''            background: linear-gradient(145deg, #071019 0%, #0a1c2c 52%, #0d2a40 100%) !important;
            border-color: #2398cf !important;
            border-left-color: #28b6e8 !important;
            color: #bfd1de !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 15px 34px rgba(0, 79, 122, 0.22) !important;
'''
new_hover = '''            background: #0f1d27 !important;
            border-color: #2586ad !important;
            color: #bfd1de !important;
            transform: none !important;
            box-shadow: none !important;
'''
if text.count(old_hover) != 1:
    raise SystemExit(f'Hover principal encontrado {text.count(old_hover)} vezes; alteração cancelada.')
text = text.replace(old_hover, new_hover, 1)

# Os cards pequenos internos do Grupo Autokraft seguem o mesmo visual flat.
small_marker = '''            overflow: hidden !important;
        }
        .st-key-org_autokraft_card_0 button p,'''
small_replacement = '''            overflow: hidden !important;
            background: #0b151e !important;
            border: 1px solid #1a3a4d !important;
            box-shadow: none !important;
            transform: none !important;
        }
        .st-key-org_autokraft_card_0 button:hover,
        .st-key-org_autokraft_card_1 button:hover,
        .st-key-org_autokraft_card_2 button:hover {
            background: #0f1d27 !important;
            border-color: #2586ad !important;
            box-shadow: none !important;
            transform: none !important;
        }
        .st-key-org_autokraft_card_0 button p,'''
if text.count(small_marker) != 1:
    raise SystemExit(f'Bloco dos cards Autokraft encontrado {text.count(small_marker)} vezes; alteração cancelada.')
text = text.replace(small_marker, small_replacement, 1)

path.write_text(text, encoding='utf-8')
print('Cards das empresas atualizados para visual flat, sem sombras e sem relevo.')
