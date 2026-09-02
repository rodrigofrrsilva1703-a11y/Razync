from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
start = s.index('    st.markdown(\n        f"""\n        <div class="rz-company-loading-overlay"', s.index("_empresa_loading = st.session_state.get('_rz_empresa_loading')"))
end_marker = "    # Mantém o diretório sob o overlay e só troca a empresa depois da transição.\n"
end = s.index(end_marker, start)
new = '''    st.markdown(
        f"""
        <div class="rz-company-loading-overlay" role="status" aria-live="polite">
            <div class="rz-company-loading-shell">
                <div class="rz-company-loading-brand">R</div>
                <div class="rz-company-loading-kicker">Acessando empresa</div>
                <div class="rz-company-loading-name">{_codigo_loading} · {_nome_loading}</div>
                <div class="rz-company-loading-status">
                    <span class="rz-company-loading-spinner" aria-hidden="true"></span>
                    <span>Preparando ambiente</span>
                </div>
            </div>
        </div>
        <style>
        .rz-company-loading-overlay {{
            position: fixed;
            inset: 0;
            z-index: 999999;
            display: grid;
            place-items: center;
            padding: 1.25rem;
            background: #091017;
            overflow: hidden;
        }}
        .rz-company-loading-overlay::before {{
            content: "";
            position: absolute;
            width: 440px;
            height: 440px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(25,189,232,.08) 0%, rgba(25,189,232,0) 68%);
            pointer-events: none;
        }}
        .rz-company-loading-shell {{
            position: relative;
            z-index: 1;
            width: min(90vw, 390px);
            text-align: center;
            animation: rz-company-enter .18s ease-out both;
        }}
        .rz-company-loading-brand {{
            width: 42px;
            height: 42px;
            margin: 0 auto 1rem;
            display: grid;
            place-items: center;
            border: 1px solid rgba(25,189,232,.32);
            border-radius: 12px;
            background: rgba(17,31,41,.82);
            color: #55d4f3;
            font-size: 1rem;
            font-weight: 800;
            letter-spacing: -.03em;
            box-shadow: 0 10px 30px rgba(0,0,0,.18);
        }}
        .rz-company-loading-kicker {{
            color: #55d4f3;
            font-size: .66rem;
            font-weight: 760;
            letter-spacing: .14em;
            text-transform: uppercase;
            margin-bottom: .45rem;
        }}
        .rz-company-loading-name {{
            color: #f3f7fa;
            font-size: 1.08rem;
            line-height: 1.35;
            font-weight: 700;
            letter-spacing: -.018em;
        }}
        .rz-company-loading-status {{
            margin-top: .95rem;
            display: inline-flex;
            align-items: center;
            gap: .48rem;
            color: #8296a6;
            font-size: .76rem;
        }}
        .rz-company-loading-spinner {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            border: 2px solid rgba(130,150,166,.24);
            border-top-color: #2fc6eb;
            animation: rz-company-spin .62s linear infinite;
        }}
        @keyframes rz-company-spin {{
            to {{ transform: rotate(360deg); }}
        }}
        @keyframes rz-company-enter {{
            from {{ opacity: 0; transform: translateY(5px) scale(.99); }}
            to {{ opacity: 1; transform: translateY(0) scale(1); }}
        }}
        @media (prefers-reduced-motion: reduce) {{
            .rz-company-loading-shell,
            .rz-company-loading-spinner {{ animation: none !important; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
'''
s = s[:start] + new + s[end:]
s = s.replace('    time.sleep(0.55)\n', '    time.sleep(0.30)\n', 1)
p.write_text(s, encoding='utf-8')
# trigger
