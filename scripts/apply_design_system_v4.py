from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

marker = '# CONTROLE DE ESTADO DE NAVEGAÇÃO'
tag = '/* Razync Design System v4 */'
if tag not in text:
    css = r'''
# ==============================================================================
# DESIGN SYSTEM VISUAL V4
# ==============================================================================
st.markdown("""
<style>
/* Razync Design System v4 */
:root {
    --rz-bg: #071019;
    --rz-bg-soft: #0a131d;
    --rz-panel: rgba(12, 23, 34, 0.92);
    --rz-panel-2: rgba(15, 29, 41, 0.88);
    --rz-panel-hover: rgba(18, 39, 54, 0.96);
    --rz-line: rgba(117, 151, 176, 0.18);
    --rz-line-strong: rgba(19, 185, 232, 0.38);
    --rz-text: #f4f8fb;
    --rz-muted: #8fa2b2;
    --rz-muted-2: #6f8495;
    --rz-accent: #19bde8;
    --rz-accent-2: #45d0f1;
    --rz-success: #55c98b;
    --rz-warning: #e4b15f;
    --rz-danger: #ef7272;
    --rz-radius-sm: 10px;
    --rz-radius: 14px;
    --rz-radius-lg: 18px;
    --rz-shadow: 0 18px 44px rgba(0,0,0,.20);
}

html[data-theme="light"] {
    --rz-bg: #f4f7f9;
    --rz-bg-soft: #eef3f6;
    --rz-panel: rgba(255,255,255,.94);
    --rz-panel-2: rgba(248,251,253,.96);
    --rz-panel-hover: rgba(240,247,251,.98);
    --rz-line: rgba(41,72,92,.14);
    --rz-line-strong: rgba(0,132,178,.34);
    --rz-text: #13222d;
    --rz-muted: #5e7180;
    --rz-muted-2: #7b8d9a;
    --rz-shadow: 0 18px 44px rgba(22,49,66,.08);
}

.stApp {
    background:
        radial-gradient(circle at 28% 0%, rgba(25,189,232,.075), transparent 31%),
        linear-gradient(180deg, var(--rz-bg) 0%, var(--rz-bg-soft) 100%) !important;
    color: var(--rz-text) !important;
}

.block-container {
    max-width: 1500px !important;
    padding-top: 2rem !important;
    padding-bottom: 4rem !important;
    padding-left: clamp(1.25rem, 2.7vw, 3rem) !important;
    padding-right: clamp(1.25rem, 2.7vw, 3rem) !important;
}

h1, h2, h3, h4, h5, h6 {
    color: var(--rz-text) !important;
    letter-spacing: -.025em !important;
}

p, label, .stCaption, [data-testid="stCaptionContainer"] {
    color: var(--rz-muted);
}

/* Cabeçalhos de página */
.rz-page-header,
.rz-dashboard-intro {
    position: relative !important;
    border: 1px solid var(--rz-line) !important;
    border-radius: var(--rz-radius-lg) !important;
    background:
        radial-gradient(circle at 0 0, rgba(25,189,232,.11), transparent 38%),
        linear-gradient(145deg, var(--rz-panel), rgba(8,18,27,.72)) !important;
    box-shadow: var(--rz-shadow) !important;
    padding: 1.35rem 1.5rem 1.45rem !important;
    overflow: hidden !important;
    margin-bottom: 1.45rem !important;
}
.rz-page-header::after,
.rz-dashboard-intro::after {
    content: '';
    position: absolute;
    left: 1.5rem;
    bottom: 0;
    width: 54px;
    height: 2px;
    border-radius: 999px;
    background: linear-gradient(90deg, var(--rz-accent), transparent);
}
.rz-page-kicker,
.rz-home-eyebrow,
.rz-dashboard-grid-title,
.rz-company-section {
    color: var(--rz-accent) !important;
    text-transform: uppercase !important;
    letter-spacing: .13em !important;
    font-size: .69rem !important;
    font-weight: 760 !important;
}
.rz-page-title,
.rz-dashboard-intro .rz-home-title {
    color: var(--rz-text) !important;
    font-size: clamp(2rem, 3.7vw, 3.15rem) !important;
    line-height: 1.04 !important;
    font-weight: 780 !important;
    letter-spacing: -.045em !important;
}
.rz-page-description,
.rz-home-copy {
    color: var(--rz-muted) !important;
    max-width: 760px !important;
    font-size: .96rem !important;
    line-height: 1.65 !important;
}

/* Botões */
.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] > button {
    min-height: 42px !important;
    border-radius: var(--rz-radius-sm) !important;
    border: 1px solid var(--rz-line) !important;
    background: linear-gradient(180deg, rgba(255,255,255,.018), rgba(255,255,255,0)), var(--rz-panel-2) !important;
    color: var(--rz-text) !important;
    box-shadow: none !important;
    font-weight: 620 !important;
    transition: transform .16s ease, border-color .16s ease, background .16s ease !important;
}
.stButton > button:hover,
.stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    transform: translateY(-1px) !important;
    border-color: var(--rz-line-strong) !important;
    background: var(--rz-panel-hover) !important;
    color: var(--rz-text) !important;
}
.stButton > button[kind="primary"],
[data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #0d91bd, #13b9e8) !important;
    border-color: rgba(86,212,245,.72) !important;
    color: #03131a !important;
    font-weight: 760 !important;
}

/* Inputs, selects e datas */
[data-baseweb="input"] > div,
[data-baseweb="select"] > div,
[data-testid="stDateInput"] [data-baseweb="input"] > div,
.stTextArea textarea {
    min-height: 44px !important;
    border-radius: var(--rz-radius-sm) !important;
    border-color: var(--rz-line) !important;
    background: var(--rz-panel) !important;
    color: var(--rz-text) !important;
    box-shadow: none !important;
}
[data-baseweb="input"] > div:focus-within,
[data-baseweb="select"] > div:focus-within,
.stTextArea textarea:focus {
    border-color: var(--rz-accent) !important;
    box-shadow: 0 0 0 3px rgba(25,189,232,.09) !important;
}

/* Upload de arquivos */
[data-testid="stFileUploaderDropzone"] {
    min-height: 132px !important;
    border-radius: var(--rz-radius) !important;
    border: 1px dashed rgba(25,189,232,.38) !important;
    background:
        radial-gradient(circle at 14% 0%, rgba(25,189,232,.08), transparent 42%),
        var(--rz-panel) !important;
    transition: border-color .16s ease, background .16s ease !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: rgba(25,189,232,.72) !important;
    background: var(--rz-panel-hover) !important;
}
[data-testid="stFileUploaderFile"] {
    border: 1px solid var(--rz-line) !important;
    border-radius: 10px !important;
    background: var(--rz-panel-2) !important;
}

/* Métricas nativas e métricas antigas */
[data-testid="stMetric"] {
    min-height: 112px !important;
    padding: 1rem 1.05rem !important;
    border: 1px solid var(--rz-line) !important;
    border-radius: var(--rz-radius) !important;
    background: var(--rz-panel) !important;
    box-shadow: 0 12px 28px rgba(0,0,0,.10) !important;
}
[data-testid="stMetricLabel"] { color: var(--rz-muted) !important; }
[data-testid="stMetricValue"] { color: var(--rz-text) !important; letter-spacing: -.035em !important; }
.metric-card {
    min-height: 108px !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    padding: 1rem 1.05rem !important;
    border-radius: var(--rz-radius) !important;
    border: 1px solid var(--rz-line) !important;
    background: var(--rz-panel) !important;
    box-shadow: 0 12px 28px rgba(0,0,0,.10) !important;
}
.metric-title { color: var(--rz-muted) !important; font-size: .68rem !important; letter-spacing: .08em !important; }
.metric-value { color: var(--rz-text) !important; font-size: 1.22rem !important; letter-spacing: -.025em !important; }

/* Alertas */
[data-testid="stAlert"] {
    border-radius: var(--rz-radius) !important;
    border: 1px solid var(--rz-line) !important;
    background: var(--rz-panel) !important;
}

/* Tabs */
[data-baseweb="tab-list"] {
    gap: .35rem !important;
    padding: .34rem !important;
    border: 1px solid var(--rz-line) !important;
    border-radius: 12px !important;
    background: rgba(9,19,28,.54) !important;
}
[data-baseweb="tab"] {
    min-height: 39px !important;
    border-radius: 9px !important;
    padding-left: .95rem !important;
    padding-right: .95rem !important;
    color: var(--rz-muted) !important;
}
[data-baseweb="tab"][aria-selected="true"] {
    color: var(--rz-text) !important;
    background: var(--rz-panel-hover) !important;
}
[data-baseweb="tab-highlight"] { background-color: var(--rz-accent) !important; }

/* Dataframes */
[data-testid="stDataFrame"] {
    overflow: hidden !important;
    border: 1px solid var(--rz-line) !important;
    border-radius: var(--rz-radius) !important;
    background: var(--rz-panel) !important;
}

/* Expanders */
[data-testid="stExpander"] {
    border: 1px solid var(--rz-line) !important;
    border-radius: var(--rz-radius) !important;
    background: var(--rz-panel) !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] summary:hover { background: rgba(25,189,232,.035) !important; }

/* Separadores */
hr { border-color: var(--rz-line) !important; opacity: 1 !important; }

/* Sidebar premium */
section[data-testid="stSidebar"] {
    background:
        radial-gradient(circle at 15% 0%, rgba(25,189,232,.10), transparent 24%),
        linear-gradient(180deg, #09121b 0%, #0a1219 100%) !important;
    border-right: 1px solid var(--rz-line) !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding-top: 1.3rem !important;
}
section[data-testid="stSidebar"] .stButton {
    margin: .24rem 0 !important;
}
section[data-testid="stSidebar"] .stButton > button {
    min-height: 46px !important;
    border-radius: 11px !important;
    border: 1px solid transparent !important;
    background: transparent !important;
    color: #a9bac7 !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    transform: none !important;
    background: rgba(25,189,232,.075) !important;
    border-color: rgba(25,189,232,.20) !important;
    color: #edf8fb !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(90deg, rgba(25,189,232,.16), rgba(25,189,232,.055)) !important;
    border-color: rgba(25,189,232,.30) !important;
    color: #eafaff !important;
}
.hc-brand-title { font-size: 1.78rem !important; letter-spacing: -.05em !important; }
.hc-brand-subtitle { font-size: .72rem !important; letter-spacing: .08em !important; text-transform: uppercase !important; }

/* Home */
[class*="st-key-home_action_"] button {
    min-height: 94px !important;
    height: 94px !important;
    border-radius: var(--rz-radius) !important;
    padding: 1rem 1.15rem 1rem 4rem !important;
    border: 1px solid var(--rz-line) !important;
    background: var(--rz-panel) !important;
    box-shadow: 0 13px 28px rgba(0,0,0,.12) !important;
}
[class*="st-key-home_action_"] button:hover {
    border-color: var(--rz-line-strong) !important;
    background: var(--rz-panel-hover) !important;
}
.rz-overview-panel {
    border-radius: var(--rz-radius-lg) !important;
    border: 1px solid var(--rz-line) !important;
    background: var(--rz-panel) !important;
    box-shadow: var(--rz-shadow) !important;
}

/* Pesquisa e área de empresas */
[class*="st-key-org_resultados_nativos"],
[class*="st-key-org_acesso_rapido"],
.rz-company-workspace {
    border-radius: var(--rz-radius) !important;
}
[class*="st-key-org_linha_empresa_"] {
    border-bottom: 1px solid rgba(117,151,176,.10) !important;
    transition: background .14s ease !important;
}
[class*="st-key-org_linha_empresa_"]:hover {
    background: rgba(25,189,232,.035) !important;
}
.rz-task-status {
    border-radius: 999px !important;
    padding: .28rem .56rem !important;
    font-size: .68rem !important;
    font-weight: 720 !important;
}

/* Central de tarefas */
.rz-task-hero {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1rem;
    padding: 1.3rem 1.4rem;
    margin-bottom: 1.15rem;
    border: 1px solid var(--rz-line);
    border-radius: var(--rz-radius-lg);
    background:
        radial-gradient(circle at 0 0, rgba(25,189,232,.10), transparent 38%),
        var(--rz-panel);
    box-shadow: var(--rz-shadow);
}
.rz-task-hero__eyebrow {
    color: var(--rz-accent);
    text-transform: uppercase;
    letter-spacing: .13em;
    font-size: .68rem;
    font-weight: 760;
}
.rz-task-hero__title {
    color: var(--rz-text);
    font-size: clamp(1.85rem, 3vw, 2.6rem);
    font-weight: 780;
    letter-spacing: -.045em;
    line-height: 1.06;
    margin-top: .26rem;
}
.rz-task-hero__copy {
    color: var(--rz-muted);
    max-width: 720px;
    font-size: .9rem;
    line-height: 1.55;
    margin-top: .45rem;
}
.rz-task-hero__badge {
    flex: 0 0 auto;
    padding: .44rem .7rem;
    border-radius: 999px;
    border: 1px solid rgba(25,189,232,.26);
    background: rgba(25,189,232,.08);
    color: #9ce7f7;
    font-size: .72rem;
    font-weight: 700;
    white-space: nowrap;
}

/* Forms */
[data-testid="stForm"] {
    padding: 1rem 1.05rem 1.05rem !important;
    border: 1px solid var(--rz-line) !important;
    border-radius: var(--rz-radius) !important;
    background: var(--rz-panel) !important;
}

/* Progress */
[data-testid="stProgress"] > div > div > div > div {
    background: linear-gradient(90deg, #0d91bd, #22c8ef) !important;
}

@media (max-width: 900px) {
    .block-container { padding-top: 1.15rem !important; }
    .rz-page-header, .rz-dashboard-intro, .rz-task-hero { border-radius: 14px !important; padding: 1rem 1.05rem !important; }
    .rz-task-hero { align-items: flex-start; flex-direction: column; }
    [class*="st-key-home_action_"] button { height: auto !important; min-height: 88px !important; }
}
</style>
""", unsafe_allow_html=True)

'''
    if marker not in text:
        raise SystemExit('Marcador de navegação não encontrado')
    text = text.replace(marker, css + marker, 1)

old_header = '''    st.markdown("## Central de Tarefas e Prazos")
    st.caption(
        "Controle operacional das obrigações das empresas e das suas tarefas manuais, "
        "com prioridade, prazo, atraso e progresso em um só lugar."
    )'''
new_header = '''    st.markdown(
        """
        <section class="rz-task-hero">
            <div>
                <div class="rz-task-hero__eyebrow">Central operacional</div>
                <div class="rz-task-hero__title">Tarefas e Prazos</div>
                <div class="rz-task-hero__copy">
                    Acompanhe obrigações, prioridades e conclusões das empresas em uma visão única,
                    com atualização rápida e automações do fluxo operacional.
                </div>
            </div>
            <div class="rz-task-hero__badge">Competência atual</div>
        </section>
        """,
        unsafe_allow_html=True,
    )'''
if old_header in text:
    text = text.replace(old_header, new_header, 1)

path.write_text(text, encoding='utf-8')
