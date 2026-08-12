from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old = '''        estabelecimento_nova = st.radio(
            "Área da empresa",
            ["Matriz", "Filial"],
            horizontal=True,
            key="org_estabelecimento_nova_geracao",
            help="Escolha a empresa antes de organizar ou classificar a planilha final."
        )
        chave_estabelecimento = normalizar_texto(estabelecimento_nova)
'''
new = '''        st.markdown("<div class='ng-area-label'>Área da empresa</div>", unsafe_allow_html=True)
        st.markdown(
            """
            <style>
            div[data-testid="stRadio"]:has(input[name="org_estabelecimento_nova_geracao"]) > label {
                display: none !important;
            }
            div[data-testid="stRadio"]:has(input[name="org_estabelecimento_nova_geracao"]) [role="radiogroup"] {
                gap: 8px !important;
                flex-wrap: nowrap !important;
            }
            div[data-testid="stRadio"]:has(input[name="org_estabelecimento_nova_geracao"]) label[data-baseweb="radio"] {
                min-height: 34px !important;
                padding: 5px 12px !important;
                margin: 0 !important;
                border: 1px solid rgba(59,130,246,.34) !important;
                border-radius: 8px !important;
                background: linear-gradient(135deg, #080d16 0%, #0a1628 100%) !important;
                box-shadow: none !important;
                cursor: pointer !important;
                transition: border-color .15s ease, background .15s ease !important;
            }
            div[data-testid="stRadio"]:has(input[name="org_estabelecimento_nova_geracao"]) label[data-baseweb="radio"]:has(input:checked) {
                border-color: #2563eb !important;
                background: linear-gradient(135deg, #0b1424 0%, #0d2344 100%) !important;
            }
            div[data-testid="stRadio"]:has(input[name="org_estabelecimento_nova_geracao"]) label[data-baseweb="radio"] > div:first-child {
                display: none !important;
            }
            div[data-testid="stRadio"]:has(input[name="org_estabelecimento_nova_geracao"]) label[data-baseweb="radio"] p {
                font-size: 12px !important;
                line-height: 18px !important;
                font-weight: 600 !important;
                margin: 0 !important;
            }
            .ng-area-label {
                font-size: 12px;
                opacity: .72;
                margin: 0 0 5px 1px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        estabelecimento_nova = st.radio(
            "Área da empresa",
            ["Matriz", "Filial"],
            horizontal=True,
            key="org_estabelecimento_nova_geracao",
            label_visibility="collapsed",
            help="Escolha a empresa antes de organizar ou classificar a planilha final."
        )
        chave_estabelecimento = normalizar_texto(estabelecimento_nova)
'''
if text.count(old) != 1:
    raise SystemExit(f'Seletor Matriz/Filial encontrado {text.count(old)} vezes.')
text = text.replace(old, new, 1)

checks = [
    'ng-area-label',
    'min-height: 34px',
    'padding: 5px 12px',
    'box-shadow: none',
    'label_visibility="collapsed"',
    "['nova_geracao_matriz'" if False else "'nova_geracao_matriz'",
    "'nova_geracao_filial'",
]
for check in checks:
    if check not in text:
        raise SystemExit(f'Validação falhou: {check!r}')

path.write_text(text, encoding='utf-8')
print('Seletor Matriz/Filial convertido em dois cards compactos, sem sombra e no visual preto/azul.')
