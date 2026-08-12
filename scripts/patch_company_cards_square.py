from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old = '''        st.markdown("<div class='ng-area-label'>Área da empresa</div>", unsafe_allow_html=True)
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

new = '''        st.markdown("<div class='ng-area-label'>Área da empresa</div>", unsafe_allow_html=True)
        if 'org_estabelecimento_nova_geracao_card' not in st.session_state:
            st.session_state['org_estabelecimento_nova_geracao_card'] = 'matriz'

        st.markdown(
            """
            <style>
            .ng-area-label {
                font-size: 12px;
                opacity: .72;
                margin: 0 0 5px 1px;
            }
            .st-key-ng_card_matriz button,
            .st-key-ng_card_filial button {
                width: 100% !important;
                height: 42px !important;
                min-height: 42px !important;
                max-height: 42px !important;
                padding: 6px 12px !important;
                border-radius: 8px !important;
                border: 1px solid #12324a !important;
                background: #050b12 !important;
                box-shadow: none !important;
                transform: none !important;
                font-size: 12px !important;
                font-weight: 600 !important;
            }
            .st-key-ng_card_matriz button:hover,
            .st-key-ng_card_filial button:hover {
                background: #081725 !important;
                border-color: #1d6f9b !important;
                box-shadow: none !important;
                transform: none !important;
            }
            .st-key-ng_card_matriz_ativo button,
            .st-key-ng_card_filial_ativo button {
                width: 100% !important;
                height: 42px !important;
                min-height: 42px !important;
                max-height: 42px !important;
                padding: 6px 12px !important;
                border-radius: 8px !important;
                border: 1px solid #1d6f9b !important;
                background: #0b1f33 !important;
                box-shadow: none !important;
                transform: none !important;
                font-size: 12px !important;
                font-weight: 700 !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        col_matriz, col_filial, col_restante = st.columns([0.14, 0.14, 0.72], gap='small')
        selecionado_ng = st.session_state['org_estabelecimento_nova_geracao_card']

        with col_matriz:
            chave_card_matriz = 'ng_card_matriz_ativo' if selecionado_ng == 'matriz' else 'ng_card_matriz'
            if st.button('Matriz', key=chave_card_matriz, use_container_width=True):
                st.session_state['org_estabelecimento_nova_geracao_card'] = 'matriz'
                st.rerun()

        with col_filial:
            chave_card_filial = 'ng_card_filial_ativo' if selecionado_ng == 'filial' else 'ng_card_filial'
            if st.button('Filial', key=chave_card_filial, use_container_width=True):
                st.session_state['org_estabelecimento_nova_geracao_card'] = 'filial'
                st.rerun()

        chave_estabelecimento = st.session_state['org_estabelecimento_nova_geracao_card']
'''

if text.count(old) != 1:
    raise SystemExit(f'Bloco antigo Matriz/Filial encontrado {text.count(old)} vezes.')
text = text.replace(old, new, 1)

checks = [
    "org_estabelecimento_nova_geracao_card",
    "st.button('Matriz'",
    "st.button('Filial'",
    "height: 42px",
    "st.columns([0.14, 0.14, 0.72]",
    "'nova_geracao_matriz'",
    "'nova_geracao_filial'",
]
for check in checks:
    if check not in text:
        raise SystemExit(f'Validação falhou: {check!r}')

path.write_text(text, encoding='utf-8')
print('Matriz/Filial agora usam dois botões-card reais, compactos e independentes do CSS do radio.')
