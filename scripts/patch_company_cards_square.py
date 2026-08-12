from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old = '''    if st.session_state['empresa_organizador'] == 'autokraft':
        empresa_autokraft = st.selectbox(
            "Empresa",
            [
                "3 - Autokraft Industrial",
                "178 - Autokraft Projetos",
                "343 - I.S.A"
            ],
            key="org_empresa_autokraft"
        )

        configuracao_empresa_autokraft = {'''

new = '''    if st.session_state['empresa_organizador'] == 'autokraft':
        empresas_autokraft = [
            ("3 - Autokraft Industrial", "3", "Autokraft Industrial", "🏭"),
            ("178 - Autokraft Projetos", "178", "Autokraft Projetos", "📐"),
            ("343 - I.S.A", "343", "I.S.A", "🏢"),
        ]
        if st.session_state.get("org_empresa_autokraft") not in [item[0] for item in empresas_autokraft]:
            st.session_state["org_empresa_autokraft"] = empresas_autokraft[0][0]

        st.markdown("##### Selecione a empresa")
        colunas_empresas_autokraft = st.columns([1, 1, 1, 3])
        for indice, (nome_empresa, numero_empresa, nome_curto, icone) in enumerate(empresas_autokraft):
            selecionada = st.session_state["org_empresa_autokraft"] == nome_empresa
            with colunas_empresas_autokraft[indice]:
                if st.button(
                    f"{icone}  **{numero_empresa}**\\n{nome_curto}" + ("\\n✓ Selecionada" if selecionada else ""),
                    key=f"org_autokraft_card_{indice}",
                    use_container_width=True,
                    type="primary" if selecionada else "secondary"
                ):
                    st.session_state["org_empresa_autokraft"] = nome_empresa
                    st.rerun()

        empresa_autokraft = st.session_state["org_empresa_autokraft"]

        configuracao_empresa_autokraft = {'''

if text.count(old) != 1:
    raise SystemExit(f'Seleção Autokraft encontrada {text.count(old)} vezes; alteração cancelada.')
text = text.replace(old, new, 1)

css_marker = '''        /* Cards de empresas: maiores, próximos e alinhados ao centro. */'''
css = '''        /* Cards pequenos para selecionar as empresas dentro do Grupo Autokraft. */
        .st-key-org_autokraft_card_0 button,
        .st-key-org_autokraft_card_1 button,
        .st-key-org_autokraft_card_2 button {
            min-height: 88px !important;
            height: 88px !important;
            padding: 8px 10px !important;
            border-radius: 8px !important;
            white-space: pre-line !important;
            line-height: 1.18 !important;
            font-size: 11px !important;
            text-align: center !important;
            overflow: hidden !important;
        }
        .st-key-org_autokraft_card_0 button p,
        .st-key-org_autokraft_card_1 button p,
        .st-key-org_autokraft_card_2 button p {
            white-space: pre-line !important;
            margin: 0 !important;
            line-height: 1.18 !important;
        }

'''
if css_marker not in text:
    raise SystemExit('Ponto de CSS dos cards não encontrado; alteração cancelada.')
text = text.replace(css_marker, css + css_marker, 1)

path.write_text(text, encoding='utf-8')
print('Lista Autokraft substituída por três cards pequenos lado a lado.')
