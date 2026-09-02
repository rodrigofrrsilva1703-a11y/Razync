from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

old_header = '''    else:
        col_voltar, col_tit = st.columns([1.2, 8.8])
        with col_voltar:
            st.markdown(
                "<div style='height: 4px;'></div>",
                unsafe_allow_html=True,
            )
            if st.button(
                '← Empresas',
                use_container_width=True,
                key='btn_voltar_empresas_org',
            ):
                st.session_state['empresa_organizador'] = None
                st.rerun()
        with col_tit:
            st.title(titulo_pagina_organizador)
        st.caption(descricao_pagina_organizador)
        st.markdown('---')
'''

new_header = '''    else:
        if st.button(
            '← Empresas',
            key='btn_voltar_empresas_org',
            type='tertiary',
        ):
            st.session_state['empresa_organizador'] = None
            st.rerun()
        st.markdown(
            f"""
            <section class="rz-company-hero" aria-label="Área da empresa">
                <div class="rz-company-hero__eyebrow">Área operacional</div>
                <div class="rz-company-hero__title">{titulo_pagina_organizador}</div>
                <div class="rz-company-hero__copy">{descricao_pagina_organizador}</div>
            </section>
            """,
            unsafe_allow_html=True,
        )
'''

if old_header not in s:
    raise SystemExit('Cabeçalho antigo das empresas não encontrado')
s = s.replace(old_header, new_header, 1)

marker = '''    if empresa_organizador:
        regime_workspace = (
'''
if marker not in s:
    raise SystemExit('Ponto do workspace das empresas não encontrado')

css_block = r'''    if empresa_organizador:
        st.markdown(
            """
            <style>
            /* Company workspace standard v2 */
            [class*="st-key-btn_voltar_empresas_org"] {
                margin: 0 0 .38rem !important;
            }
            [class*="st-key-btn_voltar_empresas_org"] button {
                width: auto !important;
                min-height: 1.85rem !important;
                padding: .15rem .15rem !important;
                border: 0 !important;
                background: transparent !important;
                box-shadow: none !important;
                color: #8fa2b4 !important;
                font-size: .73rem !important;
            }
            .rz-company-hero {
                margin: 0 0 .68rem;
                padding: .82rem 1rem .88rem;
                border: 1px solid rgba(78, 112, 136, .28);
                border-radius: 13px;
                background: linear-gradient(135deg, rgba(15, 29, 40, .96), rgba(9, 20, 29, .96));
            }
            .rz-company-hero__eyebrow {
                margin-bottom: .25rem;
                color: #20bee9;
                font-size: .61rem;
                font-weight: 800;
                letter-spacing: .13em;
                text-transform: uppercase;
            }
            .rz-company-hero__title {
                color: #f3f7fa;
                font-size: clamp(1.28rem, 2.2vw, 1.72rem);
                font-weight: 760;
                line-height: 1.15;
                letter-spacing: -.025em;
            }
            .rz-company-hero__copy {
                max-width: 880px;
                margin-top: .28rem;
                color: #91a2b2;
                font-size: .76rem;
                line-height: 1.45;
            }
            .rz-company-workspace {
                margin: 0 0 .75rem !important;
                padding: .68rem .78rem !important;
                border-radius: 12px !important;
                background: rgba(13, 27, 38, .72) !important;
            }
            [class*="st-key-org_acao_tarefa"] {
                margin: -.28rem 0 .7rem !important;
            }
            [data-testid="stTabs"] {
                margin-top: .05rem !important;
            }
            [data-testid="stTabs"] [data-baseweb="tab-list"] {
                gap: 1.2rem !important;
                margin-bottom: .62rem !important;
            }
            [data-testid="stTabs"] button[role="tab"] {
                min-height: 2.35rem !important;
                font-size: .78rem !important;
            }
            [data-testid="stFileUploader"] {
                margin: .15rem 0 .45rem !important;
                border-radius: 12px !important;
            }
            [data-testid="stFileUploaderDropzone"] {
                min-height: 94px !important;
                padding: .72rem !important;
                border-radius: 12px !important;
                border-color: rgba(66, 105, 132, .42) !important;
                background: rgba(10, 23, 33, .58) !important;
            }
            [data-testid="stMetric"] {
                min-height: 78px !important;
                padding: .62rem .7rem !important;
                border: 1px solid rgba(73, 108, 132, .25) !important;
                border-radius: 11px !important;
                background: rgba(12, 26, 36, .68) !important;
            }
            [data-testid="stMetricLabel"] {
                font-size: .66rem !important;
            }
            [data-testid="stMetricValue"] {
                font-size: 1.18rem !important;
            }
            [data-testid="stExpander"] {
                margin: .45rem 0 !important;
                border: 1px solid rgba(73, 108, 132, .26) !important;
                border-radius: 11px !important;
                overflow: hidden !important;
                background: rgba(10, 22, 31, .5) !important;
            }
            [data-testid="stDataFrame"] {
                margin: .45rem 0 .7rem !important;
                border: 1px solid rgba(73, 108, 132, .22) !important;
                border-radius: 11px !important;
                overflow: hidden !important;
            }
            [data-testid="stAlert"] {
                margin: .42rem 0 !important;
                border-radius: 10px !important;
                font-size: .76rem !important;
            }
            h3, h4, h5 {
                margin-top: .72rem !important;
                margin-bottom: .38rem !important;
            }
            h4 {
                font-size: .98rem !important;
            }
            h5 {
                font-size: .86rem !important;
            }
            .stDownloadButton > button,
            [data-testid="stDownloadButton"] > button {
                min-height: 2.45rem !important;
                border-radius: 10px !important;
                font-size: .76rem !important;
            }
            @media (max-width: 700px) {
                .rz-company-hero { padding: .72rem .78rem; }
                .rz-company-workspace { padding: .58rem .68rem !important; }
                [data-testid="stFileUploaderDropzone"] { min-height: 82px !important; }
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        regime_workspace = (
'''

s = s.replace(marker, css_block, 1)
p.write_text(s, encoding='utf-8')
