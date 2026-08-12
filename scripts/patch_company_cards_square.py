from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old_css = '''        /* Cards de empresas: alinhados à esquerda com espaçamento responsivo. */
        .st-key-org_empresa_card_nova,
        .st-key-org_empresa_card_autokraft_industrial,
        .st-key-org_empresa_card_autokraft_projetos,
        .st-key-org_empresa_card_isa {
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
        .st-key-org_empresa_card_autokraft_industrial,
        .st-key-org_empresa_card_autokraft_projetos,
        .st-key-org_empresa_card_isa {
            margin-left: 0 !important;
        }
        .st-key-org_empresa_card_nova button,
        .st-key-org_empresa_card_autokraft_industrial button,
        .st-key-org_empresa_card_autokraft_projetos button,
        .st-key-org_empresa_card_isa button {
            width: 218px !important;
            min-width: 218px !important;
            max-width: 218px !important;
            height: 218px !important;
            min-height: 218px !important;
            max-height: 218px !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
            padding: 16px 16px !important;
            cursor: pointer !important;
            background: #050b12 !important;
            border: 1px solid #12324a !important;
            border-radius: 8px !important;
            color: #f2f8fc !important;
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
        }
        .st-key-org_empresa_card_nova button p,
        .st-key-org_empresa_card_autokraft_industrial button p,
        .st-key-org_empresa_card_autokraft_projetos button p,
        .st-key-org_empresa_card_isa button p {
            width: 100% !important;
            max-width: 182px !important;
            white-space: pre-line !important;
            overflow-wrap: anywhere !important;
            margin: 0 auto !important;
            line-height: 1.28 !important;
        }
        .st-key-org_empresa_card_nova button strong,
        .st-key-org_empresa_card_autokraft_industrial button strong,
        .st-key-org_empresa_card_autokraft_projetos button strong,
        .st-key-org_empresa_card_isa button strong {
            display: inline-block !important;
            max-width: 178px !important;
            color: #f2f8fc !important;
            font-size: 16px !important;
            line-height: 1.2 !important;
            font-weight: 700 !important;
        }
        .st-key-org_empresa_card_nova button:hover,
        .st-key-org_empresa_card_autokraft_industrial button:hover,
        .st-key-org_empresa_card_autokraft_projetos button:hover,
        .st-key-org_empresa_card_isa button:hover {
            background: #081725 !important;
            border-color: #1d6f9b !important;
            color: #bfd1de !important;
            transform: none !important;
            box-shadow: none !important;
        }

        @media (max-width: 1150px) {
            .st-key-org_empresa_card_nova,
            .st-key-org_empresa_card_autokraft_industrial,
        .st-key-org_empresa_card_autokraft_projetos,
        .st-key-org_empresa_card_isa {
                width: 100% !important;
                min-width: 0 !important;
                max-width: 218px !important;
            }
            .st-key-org_empresa_card_nova button,
            .st-key-org_empresa_card_autokraft_industrial button,
        .st-key-org_empresa_card_autokraft_projetos button,
        .st-key-org_empresa_card_isa button {
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

new_css = '''        /* Cards de empresas: visual premium, compacto e responsivo. */
        .st-key-org_empresa_card_nova,
        .st-key-org_empresa_card_autokraft_industrial,
        .st-key-org_empresa_card_autokraft_projetos,
        .st-key-org_empresa_card_isa {
            width: 100% !important;
            min-width: 0 !important;
            max-width: 260px !important;
            display: flex !important;
            justify-content: flex-start !important;
            margin: 0 !important;
        }

        .st-key-org_empresa_card_nova button,
        .st-key-org_empresa_card_autokraft_industrial button,
        .st-key-org_empresa_card_autokraft_projetos button,
        .st-key-org_empresa_card_isa button {
            position: relative !important;
            width: 100% !important;
            min-width: 0 !important;
            max-width: 260px !important;
            height: 154px !important;
            min-height: 154px !important;
            max-height: 154px !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
            padding: 22px 20px 20px !important;
            cursor: pointer !important;
            background:
                radial-gradient(circle at top left, rgba(19, 185, 232, 0.10), transparent 42%),
                linear-gradient(145deg, #07101a 0%, #050a10 72%) !important;
            border: 1px solid rgba(40, 104, 145, 0.50) !important;
            border-top: 2px solid rgba(19, 185, 232, 0.78) !important;
            border-radius: 14px !important;
            color: #f5f9fc !important;
            display: flex !important;
            align-items: flex-end !important;
            justify-content: flex-start !important;
            text-align: left !important;
            white-space: normal !important;
            overflow-wrap: anywhere !important;
            box-shadow: none !important;
            transition:
                background 160ms ease,
                border-color 160ms ease,
                transform 160ms ease !important;
        }

        .st-key-org_empresa_card_nova button::before,
        .st-key-org_empresa_card_autokraft_industrial button::before,
        .st-key-org_empresa_card_autokraft_projetos button::before,
        .st-key-org_empresa_card_isa button::before {
            content: '' !important;
            position: absolute !important;
            top: 17px !important;
            left: 19px !important;
            width: 28px !important;
            height: 4px !important;
            border-radius: 99px !important;
            background: rgba(19, 185, 232, 0.88) !important;
        }

        .st-key-org_empresa_card_nova button p,
        .st-key-org_empresa_card_autokraft_industrial button p,
        .st-key-org_empresa_card_autokraft_projetos button p,
        .st-key-org_empresa_card_isa button p {
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            white-space: normal !important;
            overflow-wrap: anywhere !important;
            line-height: 1.24 !important;
        }

        .st-key-org_empresa_card_nova button strong,
        .st-key-org_empresa_card_autokraft_industrial button strong,
        .st-key-org_empresa_card_autokraft_projetos button strong,
        .st-key-org_empresa_card_isa button strong {
            display: block !important;
            width: 100% !important;
            color: #f5f9fc !important;
            font-size: 17px !important;
            line-height: 1.22 !important;
            font-weight: 730 !important;
            letter-spacing: -0.018em !important;
        }

        .st-key-org_empresa_card_nova button:hover,
        .st-key-org_empresa_card_autokraft_industrial button:hover,
        .st-key-org_empresa_card_autokraft_projetos button:hover,
        .st-key-org_empresa_card_isa button:hover {
            background:
                radial-gradient(circle at top left, rgba(19, 185, 232, 0.16), transparent 44%),
                linear-gradient(145deg, #091522 0%, #06101a 72%) !important;
            border-color: rgba(19, 185, 232, 0.90) !important;
            transform: translateY(-2px) !important;
            box-shadow: none !important;
        }

        @media (max-width: 1280px) {
            .st-key-org_empresa_card_nova,
            .st-key-org_empresa_card_autokraft_industrial,
            .st-key-org_empresa_card_autokraft_projetos,
            .st-key-org_empresa_card_isa,
            .st-key-org_empresa_card_nova button,
            .st-key-org_empresa_card_autokraft_industrial button,
            .st-key-org_empresa_card_autokraft_projetos button,
            .st-key-org_empresa_card_isa button {
                max-width: 230px !important;
            }
        }

        @media (max-width: 1050px) {
            .st-key-org_empresa_card_nova,
            .st-key-org_empresa_card_autokraft_industrial,
            .st-key-org_empresa_card_autokraft_projetos,
            .st-key-org_empresa_card_isa,
            .st-key-org_empresa_card_nova button,
            .st-key-org_empresa_card_autokraft_industrial button,
            .st-key-org_empresa_card_autokraft_projetos button,
            .st-key-org_empresa_card_isa button {
                max-width: 100% !important;
            }
        }
'''

if text.count(old_css) != 1:
    raise SystemExit(f'CSS antigo dos cards encontrado {text.count(old_css)} vezes.')
text = text.replace(old_css, new_css, 1)

old_cols = '''        # Uma única linha com quatro cards e gaps próprios para manter o espaçamento.
        col_emp1, gap1, col_emp2, gap2, col_emp3, gap3, col_emp4 = st.columns(
            [1.0, 0.06, 1.0, 0.06, 1.0, 0.06, 1.0], gap="small"
        )
'''
new_cols = '''        # Uma linha equilibrada com quatro cards responsivos e espaçamento consistente.
        col_emp1, col_emp2, col_emp3, col_emp4 = st.columns(
            [1, 1, 1, 1], gap="medium"
        )
'''
if text.count(old_cols) != 1:
    raise SystemExit(f'Layout antigo dos cards encontrado {text.count(old_cols)} vezes.')
text = text.replace(old_cols, new_cols, 1)

checks = [
    'height: 154px',
    'border-radius: 14px',
    'radial-gradient(circle at top left',
    'align-items: flex-end',
    'transform: translateY(-2px)',
    'st.columns(\n            [1, 1, 1, 1], gap="medium"\n        )',
]
for check in checks:
    if check not in text:
        raise SystemExit(f'Validação visual falhou: {check}')

path.write_text(text, encoding='utf-8')
print('Cards das empresas redesenhados com visual premium, compacto e responsivo.')
