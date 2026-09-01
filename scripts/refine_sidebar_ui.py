from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old_icon = 'section[data-testid="stSidebar"] .st-key-sb_tarefas button::before { content: "✓"; }'
new_icon = 'section[data-testid="stSidebar"] .st-key-sb_tarefas button::before { content: "☷"; }'
if old_icon in text:
    text = text.replace(old_icon, new_icon, 1)

marker = '# ==============================================================================\n# CONTROLE DE ESTADO DE NAVEGAÇÃO\n# =============================================================================='
if marker not in text:
    raise SystemExit('Marcador de navegação não encontrado.')

css = r'''
# Sidebar refinement v2
st.markdown("""
<style>
/* Sidebar Razync — navegação profissional e alinhada */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b1117 0%, #0d141b 100%) !important;
    border-right: 1px solid rgba(126, 151, 173, 0.18) !important;
}
section[data-testid="stSidebar"] > div {
    padding-top: 0.75rem !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding-left: 0.72rem !important;
    padding-right: 0.72rem !important;
}

/* Espaçamento consistente entre os itens de navegação. */
section[data-testid="stSidebar"] [class*="st-key-sb_"] {
    margin: 0 0 0.36rem 0 !important;
}
section[data-testid="stSidebar"] [class*="st-key-sb_"] .stButton,
section[data-testid="stSidebar"] [class*="st-key-sb_"] [data-testid="stButton"] {
    margin: 0 !important;
}

/* Um único sistema visual para todos os botões da sidebar. */
section[data-testid="stSidebar"] [class*="st-key-sb_"] button {
    position: relative !important;
    width: 100% !important;
    height: 46px !important;
    min-height: 46px !important;
    max-height: 46px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    gap: 0 !important;
    box-sizing: border-box !important;
    padding: 0 0.82rem 0 3.15rem !important;
    margin: 0 !important;
    border-radius: 10px !important;
    border: 1px solid transparent !important;
    background: transparent !important;
    color: #aebdca !important;
    box-shadow: none !important;
    text-align: left !important;
    font-size: 0.84rem !important;
    font-weight: 560 !important;
    line-height: 1 !important;
    transition: background 140ms ease, border-color 140ms ease, color 140ms ease, transform 140ms ease !important;
}
section[data-testid="stSidebar"] [class*="st-key-sb_"] button > div,
section[data-testid="stSidebar"] [class*="st-key-sb_"] button [data-testid="stMarkdownContainer"] {
    width: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    margin: 0 !important;
    padding: 0 !important;
}
section[data-testid="stSidebar"] [class*="st-key-sb_"] button p {
    width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    color: inherit !important;
    font-size: 0.84rem !important;
    font-weight: inherit !important;
    line-height: 1 !important;
    text-align: left !important;
    white-space: nowrap !important;
}

/* Área fixa dos ícones: todos começam e terminam no mesmo lugar. */
section[data-testid="stSidebar"] [class*="st-key-sb_"] button::before {
    position: absolute !important;
    left: 0.72rem !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    width: 1.72rem !important;
    height: 1.72rem !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin: 0 !important;
    border-radius: 7px !important;
    border: 1px solid rgba(126, 151, 173, 0.13) !important;
    background: rgba(255,255,255,0.018) !important;
    color: #8194a5 !important;
    font-size: 0.88rem !important;
    font-weight: 700 !important;
    line-height: 1 !important;
}

section[data-testid="stSidebar"] [class*="st-key-sb_"] button:hover {
    background: rgba(19, 185, 232, 0.075) !important;
    border-color: rgba(19, 185, 232, 0.18) !important;
    color: #ecf6fb !important;
    transform: translateX(2px) !important;
}
section[data-testid="stSidebar"] [class*="st-key-sb_"] button:hover::before {
    color: #35c5e9 !important;
    border-color: rgba(19, 185, 232, 0.28) !important;
    background: rgba(19, 185, 232, 0.08) !important;
}

/* Estado ativo — discreto, claro e alinhado. */
section[data-testid="stSidebar"] [class*="st-key-sb_"] button[kind="primary"],
section[data-testid="stSidebar"] [class*="st-key-sb_"] button[data-testid="baseButton-primary"] {
    background: linear-gradient(90deg, rgba(19,185,232,.13), rgba(19,185,232,.055)) !important;
    border-color: rgba(19,185,232,.30) !important;
    color: #f4fbff !important;
    font-weight: 650 !important;
}
section[data-testid="stSidebar"] [class*="st-key-sb_"] button[kind="primary"]::after,
section[data-testid="stSidebar"] [class*="st-key-sb_"] button[data-testid="baseButton-primary"]::after {
    content: '' !important;
    position: absolute !important;
    left: -0.01rem !important;
    top: 9px !important;
    bottom: 9px !important;
    width: 3px !important;
    border-radius: 0 99px 99px 0 !important;
    background: #13b9e8 !important;
}
section[data-testid="stSidebar"] [class*="st-key-sb_"] button[kind="primary"]::before,
section[data-testid="stSidebar"] [class*="st-key-sb_"] button[data-testid="baseButton-primary"]::before {
    color: #42c9eb !important;
    background: rgba(19,185,232,.11) !important;
    border-color: rgba(19,185,232,.30) !important;
}

/* Marca/cabeçalho da sidebar também recebe uma grade mais limpa. */
section[data-testid="stSidebar"] .hc-brand-title {
    margin: 0.35rem 0 0.12rem !important;
    font-size: 1.42rem !important;
    line-height: 1.2 !important;
}
section[data-testid="stSidebar"] .hc-brand-subtitle {
    margin: 0 0 0.9rem !important;
    font-size: 0.72rem !important;
    line-height: 1.45 !important;
    color: #748797 !important;
}

@media (max-width: 900px) {
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        padding-left: 0.6rem !important;
        padding-right: 0.6rem !important;
    }
    section[data-testid="stSidebar"] [class*="st-key-sb_"] button {
        height: 44px !important;
        min-height: 44px !important;
        max-height: 44px !important;
    }
}
</style>
""", unsafe_allow_html=True)

'''

if 'Sidebar refinement v2' not in text:
    text = text.replace(marker, css + marker, 1)

path.write_text(text, encoding='utf-8')
print('Sidebar profissional aplicada.')
