from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

# 1) Dá mais destaque visual aos textos explicativos (st.caption) sem alterar o conteúdo.
anchor = '''        .stTextInput { margin-top: -2px; }
'''
caption_css = '''        /* Textos explicativos das ferramentas: mais visíveis e fáceis de localizar. */
        [data-testid="stCaptionContainer"] {
            margin: 8px 0 14px !important;
            padding: 10px 13px !important;
            border-left: 3px solid rgba(19, 185, 232, 0.78) !important;
            border-radius: 6px !important;
            background: rgba(19, 185, 232, 0.065) !important;
        }
        [data-testid="stCaptionContainer"] p {
            color: #c8d7e2 !important;
            font-size: 13.5px !important;
            line-height: 1.55 !important;
            font-weight: 500 !important;
            margin: 0 !important;
        }

        .stTextInput { margin-top: -2px; }
'''
if caption_css not in text:
    if text.count(anchor) != 1:
        raise SystemExit(f'Âncora do CSS encontrada {text.count(anchor)} vezes.')
    text = text.replace(anchor, caption_css, 1)

# 2) Cards das empresas ficam somente com o nome, sem ícone e sem descrição.
old_cards = '''        cards_empresas = [
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
new_cards = '''        cards_empresas = [
            (col_emp1, 'nova_geracao', 'org_empresa_card_nova', '266 - Nova Geração'),
            (col_emp2, 'autokraft_industrial', 'org_empresa_card_autokraft_industrial', '3 - Autokraft Industrial'),
            (col_emp3, 'autokraft_projetos', 'org_empresa_card_autokraft_projetos', '178 - Autokraft Projetos'),
            (col_emp4, 'isa', 'org_empresa_card_isa', '343 - I.S.A'),
        ]
        for coluna_card, chave_empresa, chave_card, titulo_card in cards_empresas:
            with coluna_card:
                if st.button(
                    f"**{titulo_card}**",
                    use_container_width=True,
                    key=chave_card
                ):
                    st.session_state['empresa_organizador'] = chave_empresa
                    st.rerun()
'''
if old_cards in text:
    text = text.replace(old_cards, new_cards, 1)
elif new_cards not in text:
    raise SystemExit('Bloco dos cards das empresas não foi localizado.')

# 3) Como agora há apenas nomes, deixa a tipografia do card mais forte e limpa.
old_font = '''            color: #91a9bb !important;
            display: flex !important;
'''
new_font = '''            color: #f2f8fc !important;
            display: flex !important;
'''
if old_font in text:
    text = text.replace(old_font, new_font, 1)

checks = [
    '[data-testid="stCaptionContainer"]',
    "(col_emp1, 'nova_geracao', 'org_empresa_card_nova', '266 - Nova Geração')",
    'f"**{titulo_card}**"',
]
for check in checks:
    if check not in text:
        raise SystemExit(f'Validação falhou: {check!r}')

for removed in ['Organização bancária e conferência.', 'Mapas bancários e conferência.']:
    # Esses textos não devem mais aparecer dentro da definição dos cards.
    bloco_inicio = text.find('        cards_empresas = [')
    bloco_fim = text.find("    if st.session_state['empresa_organizador']", bloco_inicio)
    if removed in text[bloco_inicio:bloco_fim]:
        raise SystemExit(f'Texto antigo ainda presente nos cards: {removed}')

path.write_text(text, encoding='utf-8')
print('Explicações destacadas e cards das empresas reduzidos aos nomes.')
