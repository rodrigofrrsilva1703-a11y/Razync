from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old = '''    if empresa_organizador is None:
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
'''

new = '''    if empresa_organizador is None:
        st.markdown("##### Empresas disponíveis")

        # Duas linhas de dois cards: mantém tamanho e espaçamento mesmo com a sidebar aberta.
        linha1_card1, linha1_gap, linha1_card2, linha1_restante = st.columns([1.0, 0.10, 1.0, 2.9])
        linha2_card1, linha2_gap, linha2_card2, linha2_restante = st.columns([1.0, 0.10, 1.0, 2.9])

        cards_empresas = [
            (linha1_card1, 'nova_geracao', 'org_empresa_card_nova', '🏢', '266 - Nova Geração', 'Organização bancária e conferência.'),
            (linha1_card2, 'autokraft_industrial', 'org_empresa_card_autokraft_industrial', '🏭', '3 - Autokraft Industrial', 'Mapas bancários e conferência.'),
            (linha2_card1, 'autokraft_projetos', 'org_empresa_card_autokraft_projetos', '📐', '178 - Autokraft Projetos', 'Mapas bancários e conferência.'),
            (linha2_card2, 'isa', 'org_empresa_card_isa', '🏢', '343 - I.S.A', 'Mapas bancários e conferência.'),
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
'''

if text.count(old) != 1:
    raise SystemExit(f'Bloco atual de cards encontrado {text.count(old)} vezes; alteração cancelada.')
text = text.replace(old, new, 1)

# Garante um respiro vertical entre as duas linhas, sem alterar o tamanho dos cards.
css_marker = '''        @media (max-width: 1150px) {'''
css_extra = '''        .st-key-org_empresa_card_autokraft_projetos,
        .st-key-org_empresa_card_isa {
            margin-top: 14px !important;
        }

'''
if css_marker not in text:
    raise SystemExit('Ponto de CSS responsivo não encontrado; alteração cancelada.')
text = text.replace(css_marker, css_extra + css_marker, 1)

path.write_text(text, encoding='utf-8')
print('Layout dos quatro cards alterado para grade 2x2 estável com sidebar aberta.')
