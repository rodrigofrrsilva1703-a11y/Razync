from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')
start = text.index("if st.session_state['pagina_ativa'] == 'home':")
end = text.index("# ==============================================================================\n# CENTRAL DE TAREFAS E PRAZOS", start)

new_home = r'''if st.session_state['pagina_ativa'] == 'home':
    # Resumo operacional real da competência atual para a Home.
    hoje_home, competencia_home = obter_competencia_operacional()
    try:
        status_empresas_home = carregar_tarefas_competencia(competencia_home.isoformat())
    except Exception:
        status_empresas_home = {}

    prioridades_home = [
        calcular_prioridade_empresa(
            empresa, status_empresas_home, hoje_home, competencia_home
        )
        for empresa in EMPRESAS
    ]
    total_empresas_home = len(EMPRESAS)
    vencendo_hoje_home = sum(
        1 for prioridade in prioridades_home
        if not prioridade['concluida'] and prioridade.get('dias_restantes') == 0
    )
    atrasadas_home = sum(
        1 for prioridade in prioridades_home
        if not prioridade['concluida'] and prioridade['status'] == 'Atrasada'
    )
    concluidas_home = sum(1 for prioridade in prioridades_home if prioridade['concluida'])
    progresso_home = round((concluidas_home / total_empresas_home) * 100) if total_empresas_home else 0

    st.markdown(
        f"""
        <style>
        /* Home compacta v4 — ocupa melhor a primeira dobra da tela. */
        .stMainBlockContainer {{
            padding-top: 1.65rem !important;
            padding-bottom: 1.2rem !important;
            max-width: 1180px !important;
        }}
        .rz-home-shell {{ margin-top: 0 !important; }}
        .rz-dashboard-intro {{
            padding: .1rem 0 .55rem !important;
            margin: 0 0 .65rem !important;
            border: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
        }}
        .rz-home-eyebrow {{
            font-size: .68rem !important;
            letter-spacing: .14em !important;
            margin-bottom: .35rem !important;
        }}
        .rz-home-title {{
            font-size: clamp(2rem, 3.6vw, 3.15rem) !important;
            line-height: 1.02 !important;
            margin: 0 !important;
            letter-spacing: -.045em !important;
        }}
        .rz-home-copy {{
            margin-top: .55rem !important;
            max-width: 780px !important;
            font-size: .88rem !important;
            line-height: 1.45 !important;
        }}
        .rz-home-metrics {{
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: .65rem;
            margin: .85rem 0 1.05rem;
        }}
        .rz-home-metric {{
            min-height: 112px;
            padding: .9rem .95rem;
            border: 1px solid rgba(110,145,166,.20);
            border-radius: 14px;
            background: linear-gradient(145deg, rgba(14,28,40,.96), rgba(10,21,31,.96));
            box-shadow: 0 7px 20px rgba(0,0,0,.10);
        }}
        .rz-home-metric__label {{
            color: #91a5b6;
            font-size: .64rem;
            font-weight: 760;
            letter-spacing: .08em;
            text-transform: uppercase;
        }}
        .rz-home-metric__value {{
            margin-top: .3rem;
            color: #f4f8fb;
            font-size: 1.72rem;
            font-weight: 780;
            line-height: 1;
        }}
        .rz-home-metric__sub {{
            margin-top: .42rem;
            color: #7890a3;
            font-size: .72rem;
        }}
        .rz-home-progress-track {{
            height: 5px;
            margin-top: .55rem;
            overflow: hidden;
            border-radius: 999px;
            background: rgba(116,143,162,.18);
        }}
        .rz-home-progress-track > i {{
            display: block;
            width: {progresso_home}%;
            height: 100%;
            border-radius: inherit;
            background: linear-gradient(90deg, #13b9e8, #1e8fff);
        }}
        .rz-dashboard-grid-title {{
            margin: .15rem 0 .55rem !important;
            font-size: .68rem !important;
            letter-spacing: .12em !important;
        }}
        div[class*="st-key-home_action_"] {{ margin-bottom: .55rem !important; }}
        div[class*="st-key-home_action_"] button {{
            min-height: 78px !important;
            padding: .8rem 1rem !important;
            border-radius: 14px !important;
            text-align: left !important;
        }}
        div[class*="st-key-home_action_"] button p {{
            font-size: .79rem !important;
            line-height: 1.35 !important;
        }}
        div[class*="st-key-home_action_"] button strong {{
            display: block;
            margin-bottom: .16rem;
            color: #f4f8fb !important;
            font-size: .92rem !important;
        }}
        .rz-overview-panel {{
            min-height: 246px !important;
            padding: 1rem 1.05rem !important;
            border-radius: 14px !important;
        }}
        .rz-overview-title {{ font-size: 1rem !important; margin-top: .28rem !important; }}
        .rz-overview-copy {{ font-size: .74rem !important; margin: .4rem 0 .65rem !important; }}
        .rz-overview-row {{ padding: .52rem 0 !important; gap: .55rem !important; }}
        .rz-overview-row strong {{ font-size: .72rem !important; }}
        .rz-overview-row span {{ font-size: .66rem !important; line-height: 1.35 !important; }}
        .rz-home-tip {{
            margin-top: .55rem;
            padding: .72rem .9rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            border: 1px solid rgba(110,145,166,.18);
            border-radius: 12px;
            background: rgba(13,27,39,.76);
        }}
        .rz-home-tip strong {{ color: #eaf3f8; font-size: .76rem; }}
        .rz-home-tip span {{ color: #7890a3; font-size: .7rem; }}
        @media (max-width: 1050px) {{
            .rz-home-metrics {{ grid-template-columns: repeat(3, 1fr); }}
        }}
        @media (max-width: 760px) {{
            .stMainBlockContainer {{ padding-top: 1rem !important; }}
            .rz-home-metrics {{ grid-template-columns: repeat(2, 1fr); }}
            .rz-home-title {{ font-size: 2rem !important; }}
        }}
        </style>
        <div class="rz-home-shell">
            <section class="rz-dashboard-intro" aria-labelledby="rz-home-title">
                <div class="rz-home-eyebrow">Central operacional</div>
                <div class="rz-home-title" id="rz-home-title">Vamos organizar seu dia.</div>
                <div class="rz-home-copy">
                    Centralize suas rotinas contábeis em um só lugar e acesse rapidamente cada ferramenta da operação.
                </div>
            </section>
            <section class="rz-home-metrics" aria-label="Resumo operacional">
                <div class="rz-home-metric">
                    <div class="rz-home-metric__label">Empresas</div>
                    <div class="rz-home-metric__value">{total_empresas_home}</div>
                    <div class="rz-home-metric__sub">Cadastradas</div>
                </div>
                <div class="rz-home-metric">
                    <div class="rz-home-metric__label">Vencendo hoje</div>
                    <div class="rz-home-metric__value">{vencendo_hoje_home}</div>
                    <div class="rz-home-metric__sub">Empresas</div>
                </div>
                <div class="rz-home-metric">
                    <div class="rz-home-metric__label">Atrasadas</div>
                    <div class="rz-home-metric__value">{atrasadas_home}</div>
                    <div class="rz-home-metric__sub">Exigem atenção</div>
                </div>
                <div class="rz-home-metric">
                    <div class="rz-home-metric__label">Concluídas</div>
                    <div class="rz-home-metric__value">{concluidas_home}</div>
                    <div class="rz-home-metric__sub">Competência atual</div>
                </div>
                <div class="rz-home-metric">
                    <div class="rz-home-metric__label">Progresso</div>
                    <div class="rz-home-metric__value">{progresso_home}%</div>
                    <div class="rz-home-progress-track"><i></i></div>
                    <div class="rz-home-metric__sub">{concluidas_home} de {total_empresas_home}</div>
                </div>
            </section>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_acoes, col_visao = st.columns([1.45, 0.75], gap="large")
    with col_acoes:
        st.markdown('<div class="rz-dashboard-grid-title">Ações rápidas</div>', unsafe_allow_html=True)
        st.button(
            "**Organizador de Planilhas**\nFluxos específicos, empresas e Base Inteligente.",
            key="home_action_organizador",
            use_container_width=True,
            on_click=mudar_pagina,
            args=('organizador',),
        )
        st.button(
            "**Conversor de Extratos**\nPDF, OFX, CSV e Excel para o padrão Domínio.",
            key="home_action_extratos",
            use_container_width=True,
            on_click=mudar_pagina,
            args=('extratos',),
        )
        st.button(
            "**Conciliação com Razão**\nConferência diária e identificação de divergências.",
            key="home_action_razao",
            use_container_width=True,
            on_click=mudar_pagina,
            args=('razao',),
        )

    with col_visao:
        st.markdown('<div class="rz-dashboard-grid-title">Visão do ambiente</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <section class="rz-overview-panel" aria-label="Recursos do Razync">
                <div class="rz-overview-kicker">Razync</div>
                <div class="rz-overview-title">Operação centralizada</div>
                <div class="rz-overview-copy">Ferramentas bancárias e contábeis reunidas em um único fluxo de trabalho.</div>
                <div class="rz-overview-row">
                    <i class="rz-overview-dot"></i>
                    <div><strong>{total_empresas_home} empresas cadastradas</strong>
                    <span>Áreas individuais preparadas para regras específicas.</span></div>
                </div>
                <div class="rz-overview-row">
                    <i class="rz-overview-dot"></i>
                    <div><strong>Arquivos bancários</strong>
                    <span>PDF, OFX, CSV, XLSX e XLS suportados.</span></div>
                </div>
                <div class="rz-overview-row">
                    <i class="rz-overview-dot"></i>
                    <div><strong>Saída para a Domínio</strong>
                    <span>Modelo, classificação e conferência preservados.</span></div>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="rz-home-tip">
            <div><strong>Dica rápida</strong><br><span>Use a navegação lateral para acessar ferramentas e a Central de Tarefas.</span></div>
            <span>Ambiente operacional Razync</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

'''

text = text[:start] + new_home + text[end:]
path.write_text(text, encoding='utf-8')
