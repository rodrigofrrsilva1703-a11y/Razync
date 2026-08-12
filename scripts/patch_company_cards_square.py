from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old_titles = '''        st.title({
            'nova_geracao': '266 - Nova Geração',
            'autokraft': 'Grupo Autokraft'
        }.get(empresa_organizador, 'Organizador de Planilhas'))
    st.caption({
        'nova_geracao': 'Organize, confira e classifique os movimentos da 266 - Nova Geração.',
        'autokraft': 'Organize os mapas diários e confira os extratos do Grupo Autokraft.'
    }.get(
'''
new_titles = '''        st.title({
            'nova_geracao': '266 - Nova Geração',
            'autokraft_industrial': '3 - Autokraft Industrial',
            'autokraft_projetos': '178 - Autokraft Projetos',
            'isa': '343 - I.S.A'
        }.get(empresa_organizador, 'Organizador de Planilhas'))
    st.caption({
        'nova_geracao': 'Organize, confira e classifique os movimentos da 266 - Nova Geração.',
        'autokraft_industrial': 'Organize os mapas diários e confira os extratos da 3 - Autokraft Industrial.',
        'autokraft_projetos': 'Organize os mapas diários e confira os extratos da 178 - Autokraft Projetos.',
        'isa': 'Organize os mapas diários e confira os extratos da 343 - I.S.A.'
    }.get(
'''
if text.count(old_titles) != 1:
    raise SystemExit(f'Bloco de títulos encontrado {text.count(old_titles)} vezes; alteração cancelada.')
text = text.replace(old_titles, new_titles, 1)

old_cards = '''    if empresa_organizador is None:
        st.markdown("##### Empresas disponíveis")
        col_emp1, col_gap_empresas, col_emp2, _espaco_empresas = st.columns([1.15, 0.10, 1.15, 3.60])
        with col_emp1:
            if st.button(
                "🏢\\n\\n**266 - Nova Geração**\\n\\n"
                "Organização bancária e conferência.",
                use_container_width=True,
                key="org_empresa_card_nova"
            ):
                st.session_state['empresa_organizador'] = 'nova_geracao'
                st.rerun()
        with col_emp2:
            if st.button(
                "🏭\\n\\n**Grupo Autokraft**\\n\\n"
                "Mapas bancários e conferência.",
                use_container_width=True,
                key="org_empresa_card_autokraft"
            ):
                st.session_state['empresa_organizador'] = 'autokraft'
                st.rerun()

    if st.session_state['empresa_organizador'] == 'autokraft':
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

        configuracao_empresa_autokraft = {
            "3 - Autokraft Industrial": {
                "slug": "autokraft_industrial",
                "arquivo": "Autokraft_Industrial"
            },
            "178 - Autokraft Projetos": {
                "slug": "autokraft_projetos",
                "arquivo": "Autokraft_Projetos"
            },
            "343 - I.S.A": {
                "slug": "isa",
                "arquivo": "ISA"
            }
        }[empresa_autokraft]
'''
new_cards = '''    if empresa_organizador is None:
        st.markdown("##### Empresas disponíveis")
        col_emp1, col_gap1, col_emp2, col_gap2, col_emp3, col_gap3, col_emp4, _espaco_empresas = st.columns(
            [1.08, 0.08, 1.08, 0.08, 1.08, 0.08, 1.08, 2.52]
        )
        cards_empresas = [
            (col_emp1, 'nova_geracao', 'org_empresa_card_nova', '🏢', '266 - Nova Geração', 'Organização bancária e conferência.'),
            (col_emp2, 'autokraft_industrial', 'org_empresa_card_autokraft_industrial', '🏭', '3 - Autokraft Industrial', 'Mapas bancários e conferência.'),
            (col_emp3, 'autokraft_projetos', 'org_empresa_card_autokraft_projetos', '📐', '178 - Autokraft Projetos', 'Mapas bancários e conferência.'),
            (col_emp4, 'isa', 'org_empresa_card_isa', '🏢', '343 - I.S.A', 'Mapas bancários e conferência.'),
        ]
        for coluna_card, chave_empresa, chave_card, icone, titulo_card, descricao_card in cards_empresas:
            with coluna_card:
                if st.button(
                    f"{icone}\\n\\n**{titulo_card}**\\n\\n{descricao_card}",
                    use_container_width=True,
                    key=chave_card
                ):
                    st.session_state['empresa_organizador'] = chave_empresa
                    st.rerun()

    if st.session_state['empresa_organizador'] in {
        'autokraft_industrial', 'autokraft_projetos', 'isa'
    }:
        configuracoes_autokraft_por_area = {
            'autokraft_industrial': {
                'empresa': '3 - Autokraft Industrial',
                'slug': 'autokraft_industrial',
                'arquivo': 'Autokraft_Industrial'
            },
            'autokraft_projetos': {
                'empresa': '178 - Autokraft Projetos',
                'slug': 'autokraft_projetos',
                'arquivo': 'Autokraft_Projetos'
            },
            'isa': {
                'empresa': '343 - I.S.A',
                'slug': 'isa',
                'arquivo': 'ISA'
            }
        }
        configuracao_empresa_autokraft = configuracoes_autokraft_por_area[
            st.session_state['empresa_organizador']
        ]
        empresa_autokraft = configuracao_empresa_autokraft['empresa']
'''
if text.count(old_cards) != 1:
    raise SystemExit(f'Bloco de cards/Autokraft encontrado {text.count(old_cards)} vezes; alteração cancelada.')
text = text.replace(old_cards, new_cards, 1)

# Ajusta o acesso ao slug/arquivo, agora presentes diretamente no dicionário selecionado.
old_slug = '''        slug_empresa_autokraft = configuracao_empresa_autokraft["slug"]
'''
if text.count(old_slug) != 1:
    raise SystemExit(f'Linha de slug encontrada {text.count(old_slug)} vezes; alteração cancelada.')

# CSS: aplica o mesmo visual dos cards principais aos 4 cards, sem depender do antigo card Grupo Autokraft.
text = text.replace(
    '.st-key-org_empresa_card_autokraft {',
    '.st-key-org_empresa_card_autokraft_industrial,\n        .st-key-org_empresa_card_autokraft_projetos,\n        .st-key-org_empresa_card_isa {',
)
text = text.replace(
    '.st-key-org_empresa_card_autokraft button',
    '.st-key-org_empresa_card_autokraft_industrial button,\n        .st-key-org_empresa_card_autokraft_projetos button,\n        .st-key-org_empresa_card_isa button',
)
text = text.replace(
    '.st-key-org_empresa_card_autokraft button p',
    '.st-key-org_empresa_card_autokraft_industrial button p,\n        .st-key-org_empresa_card_autokraft_projetos button p,\n        .st-key-org_empresa_card_isa button p',
)
text = text.replace(
    '.st-key-org_empresa_card_autokraft button strong',
    '.st-key-org_empresa_card_autokraft_industrial button strong,\n        .st-key-org_empresa_card_autokraft_projetos button strong,\n        .st-key-org_empresa_card_isa button strong',
)
text = text.replace(
    '.st-key-org_empresa_card_autokraft button:hover',
    '.st-key-org_empresa_card_autokraft_industrial button:hover,\n        .st-key-org_empresa_card_autokraft_projetos button:hover,\n        .st-key-org_empresa_card_isa button:hover',
)

# Remove regras específicas do card antigo que não existe mais.
text = text.replace('        .st-key-org_empresa_card_autokraft {\n            margin-left: 0 !important;\n        }\n', '')

path.write_text(text, encoding='utf-8')
print('Grupo Autokraft separado em três cards independentes, cada um abrindo sua própria área.')
