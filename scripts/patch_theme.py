from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

old = '''if st.session_state["tema_razync"] == "Claro":
    st.markdown("""<style>
    :root{--hc-bg:#f5f7fa;--hc-surface:#ffffff;--hc-surface-hover:#eef4f8;--hc-border:#d6e0e8;--hc-border-strong:#bac8d3;--hc-text:#17212b;--hc-muted:#5f7180;--hc-accent:#0784b8;--hc-accent-soft:rgba(7,132,184,.10)}
    .stApp,[data-testid=stAppViewContainer],[data-testid=stMain]{background:#f5f7fa!important;color:#17212b!important}
    section[data-testid=stSidebar]{background:#fff!important;border-right:1px solid #d6e0e8!important}
    h1,h2,h3,h4,h5,h6{color:#17212b!important}
    .stButton>button,[data-testid=stFileUploaderDropzone],[data-testid=stMetric],.metric-card,.aviso-banner{background:#fff!important;border-color:#d6e0e8!important;color:#17212b!important}
    [data-testid=stCaptionContainer]{background:rgba(7,132,184,.065)!important;border-left-color:#0784b8!important}
    [data-testid=stCaptionContainer] p{color:#405766!important}
    input,textarea{background:#fff!important;color:#17212b!important}
    </style>""", unsafe_allow_html=True)
'''

new = '''if st.session_state["tema_razync"] == "Claro":
    st.markdown("""<style>
    :root {
        --hc-bg: #f4f7fb;
        --hc-surface: #ffffff;
        --hc-surface-hover: #f0f5f9;
        --hc-border: #d7e1e9;
        --hc-border-strong: #b9c8d4;
        --hc-text: #17212b;
        --hc-muted: #607181;
        --hc-accent: #0784b8;
        --hc-accent-soft: rgba(7,132,184,.09);
    }

    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        background: #f4f7fb !important;
        color: #17212b !important;
    }
    .block-container { background: transparent !important; }

    section[data-testid="stSidebar"] {
        background: #eef3f7 !important;
        border-right: 1px solid #d4dfe8 !important;
    }
    section[data-testid="stSidebar"] * { color: #23313d; }
    section[data-testid="stSidebar"] .stButton > button {
        color: #314250 !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #e2edf4 !important;
        border-color: #a8c7d9 !important;
    }

    h1,h2,h3,h4,h5,h6,
    .hc-brand-title,
    .metric-value,
    .hc-review-title {
        color: #17212b !important;
    }
    p, label, .stMarkdown, .stText, [data-testid="stWidgetLabel"] {
        color: #344552;
    }
    .hc-brand-subtitle,
    .metric-title,
    .hc-review-text { color: #657685 !important; }

    .stButton > button {
        background: #ffffff !important;
        color: #253746 !important;
        border-color: #cfdbe4 !important;
        box-shadow: 0 1px 2px rgba(31, 49, 64, .04) !important;
    }
    .stButton > button:hover {
        background: #f3f8fb !important;
        color: #102532 !important;
        border-color: #63a9c8 !important;
        box-shadow: 0 3px 10px rgba(37, 77, 99, .08) !important;
    }

    [data-testid="stCaptionContainer"] {
        background: #edf7fb !important;
        border-left-color: #0784b8 !important;
    }
    [data-testid="stCaptionContainer"] p {
        color: #3c5666 !important;
    }

    [data-testid="stFileUploaderDropzone"],
    [data-testid="stMetric"],
    .metric-card,
    .aviso-banner,
    .hc-review-box,
    [data-testid="stExpander"] {
        background: #ffffff !important;
        border-color: #d5e0e8 !important;
        color: #17212b !important;
        box-shadow: 0 1px 3px rgba(31, 49, 64, .035) !important;
    }
    [data-testid="stFileUploaderDropzone"]:hover {
        background: #f5fafc !important;
        border-color: #70b2cf !important;
    }

    input, textarea,
    [data-baseweb="select"] > div,
    [data-baseweb="input"] > div {
        background: #ffffff !important;
        color: #17212b !important;
        border-color: #cad7e1 !important;
    }
    input::placeholder, textarea::placeholder { color: #8797a4 !important; }

    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        border-bottom-color: #d5e0e8 !important;
    }
    [data-testid="stTabs"] button[role="tab"] {
        color: #617382 !important;
        background: transparent !important;
    }
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        color: #075f84 !important;
        background: #eaf5fa !important;
        border-bottom-color: #0784b8 !important;
    }

    [data-testid="stDataFrame"],
    [data-testid="stTable"] {
        background: #ffffff !important;
        border-color: #d5e0e8 !important;
    }

    .hc-step-badge {
        background: #edf6fa !important;
        border-color: #b8d6e4 !important;
        color: #28566b !important;
    }

    .st-key-org_empresa_card_nova button,
    .st-key-org_empresa_card_autokraft_industrial button,
    .st-key-org_empresa_card_autokraft_projetos button,
    .st-key-org_empresa_card_isa button {
        background: linear-gradient(145deg, #ffffff 0%, #f3f8fb 100%) !important;
        border-color: #bfd5e1 !important;
        border-top-color: #0784b8 !important;
        color: #17212b !important;
        box-shadow: 0 4px 14px rgba(38, 74, 95, .06) !important;
    }
    .st-key-org_empresa_card_nova button strong,
    .st-key-org_empresa_card_autokraft_industrial button strong,
    .st-key-org_empresa_card_autokraft_projetos button strong,
    .st-key-org_empresa_card_isa button strong {
        color: #17212b !important;
    }
    .st-key-org_empresa_card_nova button:hover,
    .st-key-org_empresa_card_autokraft_industrial button:hover,
    .st-key-org_empresa_card_autokraft_projetos button:hover,
    .st-key-org_empresa_card_isa button:hover {
        background: linear-gradient(145deg, #ffffff 0%, #eaf5fa 100%) !important;
        border-color: #5ea7c7 !important;
        box-shadow: 0 7px 18px rgba(38, 74, 95, .09) !important;
    }

    .st-key-ng_card_matriz button,
    .st-key-ng_card_filial button,
    .st-key-ng_card_matriz_ativo button,
    .st-key-ng_card_filial_ativo button {
        background: #ffffff !important;
        color: #263b49 !important;
        border-color: #c6d7e2 !important;
    }
    .st-key-ng_card_matriz_ativo button,
    .st-key-ng_card_filial_ativo button {
        background: #e9f5fb !important;
        border-color: #208bb7 !important;
        color: #164f68 !important;
    }

    [data-testid="stSpinner"] {
        background: linear-gradient(90deg, #edf7fb, #ffffff 45%) !important;
        border-color: #d2e0e8 !important;
        box-shadow: none !important;
    }
    [data-testid="stSpinner"] p { color: #405766 !important; }

    .alerta-dominio {
        background: #fff2f3 !important;
        border-left-color: #d94755 !important;
    }
    .alerta-dominio h4 { color: #a92c38 !important; }
    .alerta-dominio p { color: #62474b !important; }
    </style>""", unsafe_allow_html=True)
'''

if s.count(old) != 1:
    raise SystemExit(f'Bloco atual do tema claro encontrado {s.count(old)} vezes.')
s = s.replace(old, new, 1)

for check in [
    '--hc-bg: #f4f7fb',
    'section[data-testid="stSidebar"]',
    '.st-key-org_empresa_card_nova button',
    '.st-key-ng_card_matriz_ativo button',
    '[data-testid="stTabs"] button[role="tab"][aria-selected="true"]',
]:
    if check not in s:
        raise SystemExit(f'Validação do tema claro falhou: {check}')

p.write_text(s, encoding='utf-8')
print('Modo claro refinado com contraste, componentes e cards específicos.')
