from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

if 'import time\n' not in text:
    text = text.replace('import tempfile\n', 'import tempfile\nimport time\n', 1)

old = '''        def _abrir_empresa_catalogo(empresa_catalogo):
            chave_destino = empresa_catalogo.get(
                'chave_sistema', empresa_catalogo['chave']
            )
            if chave_destino == 'nova_geracao':
                st.session_state['org_estabelecimento_nova_geracao_card'] = (
                    empresa_catalogo.get('estabelecimento', 'matriz')
                )
            st.session_state['empresa_organizador'] = chave_destino
            st.rerun()
'''
new = '''        def _abrir_empresa_catalogo(empresa_catalogo):
            chave_destino = empresa_catalogo.get(
                'chave_sistema', empresa_catalogo['chave']
            )
            if chave_destino == 'nova_geracao':
                st.session_state['org_estabelecimento_nova_geracao_card'] = (
                    empresa_catalogo.get('estabelecimento', 'matriz')
                )
            st.session_state['_rz_empresa_loading'] = {
                'codigo': str(empresa_catalogo.get('codigo', '')),
                'nome': str(empresa_catalogo.get('nome', 'Empresa')),
            }
            st.session_state['empresa_organizador'] = chave_destino
            st.rerun()
'''
if old not in text:
    raise SystemExit('Função de abertura de empresa não encontrada')
text = text.replace(old, new, 1)

marker = '''# TELA 1: MENU PRINCIPAL (HOME)
# ==============================================================================
'''
loading = '''# Transição curta ao abrir uma empresa: mascara o rerun do Streamlit sem atrasar a navegação normal.
_empresa_loading = st.session_state.pop('_rz_empresa_loading', None)
if _empresa_loading:
    _codigo_loading = _empresa_loading.get('codigo', '')
    _nome_loading = _empresa_loading.get('nome', 'Empresa')
    st.markdown(
        f"""
        <div class="rz-company-loading-overlay" role="status" aria-live="polite">
            <div class="rz-company-loading-card">
                <div class="rz-company-loading-mark"><span></span><span></span><span></span></div>
                <div class="rz-company-loading-kicker">Abrindo empresa</div>
                <div class="rz-company-loading-name">{_codigo_loading} · {_nome_loading}</div>
                <div class="rz-company-loading-copy">Preparando ferramentas e ambiente operacional…</div>
                <div class="rz-company-loading-track"><i></i></div>
            </div>
        </div>
        <style>
        .rz-company-loading-overlay {{
            position: fixed;
            inset: 0;
            z-index: 999999;
            display: grid;
            place-items: center;
            padding: 1.5rem;
            background: rgba(5, 12, 18, .965);
            backdrop-filter: blur(5px);
        }}
        .rz-company-loading-card {{
            width: min(92vw, 460px);
            padding: 1.6rem 1.7rem 1.5rem;
            border: 1px solid rgba(25,189,232,.26);
            border-radius: 18px;
            background: #0b1721;
            box-shadow: 0 20px 55px rgba(0,0,0,.28);
        }}
        .rz-company-loading-mark {{
            display: flex;
            gap: 5px;
            margin-bottom: 1.2rem;
        }}
        .rz-company-loading-mark span {{
            width: 7px;
            height: 7px;
            border-radius: 999px;
            background: #19bde8;
            animation: rz-company-pulse .85s ease-in-out infinite alternate;
        }}
        .rz-company-loading-mark span:nth-child(2) {{ animation-delay: .12s; opacity: .72; }}
        .rz-company-loading-mark span:nth-child(3) {{ animation-delay: .24s; opacity: .45; }}
        .rz-company-loading-kicker {{
            color: #38c8ec;
            font-size: .68rem;
            font-weight: 760;
            letter-spacing: .13em;
            text-transform: uppercase;
            margin-bottom: .42rem;
        }}
        .rz-company-loading-name {{
            color: #f4f8fb;
            font-size: 1.15rem;
            line-height: 1.3;
            font-weight: 720;
            letter-spacing: -.02em;
        }}
        .rz-company-loading-copy {{
            margin-top: .45rem;
            color: #8397a8;
            font-size: .82rem;
        }}
        .rz-company-loading-track {{
            position: relative;
            height: 3px;
            margin-top: 1.3rem;
            overflow: hidden;
            border-radius: 99px;
            background: rgba(111,145,166,.15);
        }}
        .rz-company-loading-track i {{
            position: absolute;
            inset: 0 auto 0 0;
            width: 38%;
            border-radius: inherit;
            background: linear-gradient(90deg, transparent, #19bde8, #62d9f4, transparent);
            animation: rz-company-loading 1s ease-in-out infinite;
        }}
        @keyframes rz-company-loading {{
            from {{ transform: translateX(-110%); }}
            to {{ transform: translateX(290%); }}
        }}
        @keyframes rz-company-pulse {{
            from {{ transform: translateY(0); opacity: .35; }}
            to {{ transform: translateY(-3px); opacity: 1; }}
        }}
        @media (prefers-reduced-motion: reduce) {{
            .rz-company-loading-mark span,
            .rz-company-loading-track i {{ animation: none !important; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    # Janela mínima apenas para a transição chegar ao navegador antes do rerun final.
    time.sleep(0.16)
    st.rerun()

'''
if marker not in text:
    raise SystemExit('Ponto de inserção da transição não encontrado')
if 'rz-company-loading-overlay' not in text:
    text = text.replace(marker, loading + marker, 1)

path.write_text(text, encoding='utf-8')
