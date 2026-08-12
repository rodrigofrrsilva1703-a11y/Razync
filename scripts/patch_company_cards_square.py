from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old = '''    if empresa_organizador is None:
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
'''

new = '''    if empresa_organizador is None:
        st.markdown("##### Empresas disponíveis")

        # Uma única linha com quatro cards e gaps próprios para manter o espaçamento.
        col_emp1, gap1, col_emp2, gap2, col_emp3, gap3, col_emp4 = st.columns(
            [1.0, 0.06, 1.0, 0.06, 1.0, 0.06, 1.0], gap="small"
        )

        cards_empresas = [
            (col_emp1, 'nova_geracao', 'org_empresa_card_nova', '🏢', '266 - Nova Geração', 'Organização bancária e conferência.'),
            (col_emp2, 'autokraft_industrial', 'org_empresa_card_autokraft_industrial', '🏭', '3 - Autokraft Industrial', 'Mapas bancários e conferência.'),
            (col_emp3, 'autokraft_projetos', 'org_empresa_card_autokraft_projetos', '📐', '178 - Autokraft Projetos', 'Mapas bancários e conferência.'),
            (col_emp4, 'isa', 'org_empresa_card_isa', '🏢', '343 - I.S.A', 'Mapas bancários e conferência.'),
        ]
'''

if text.count(old) != 1:
    raise SystemExit(f'Bloco 2x2 atual encontrado {text.count(old)} vezes; alteração cancelada.')
text = text.replace(old, new, 1)

# Remove o espaçamento vertical que existia apenas para a segunda linha do layout 2x2.
vertical_gap = '''        .st-key-org_empresa_card_autokraft_projetos,
        .st-key-org_empresa_card_isa {
            margin-top: 14px !important;
        }

'''
if text.count(vertical_gap) != 1:
    raise SystemExit(f'Regra de espaçamento vertical encontrada {text.count(vertical_gap)} vezes; alteração cancelada.')
text = text.replace(vertical_gap, '', 1)

# Com quatro cards na mesma linha, deixa cada card usar a largura disponível da coluna
# quando a sidebar estiver aberta, preservando o limite máximo no desktop.
old_media = '''                max-width: 218px !important;
'''
# Não altera globalmente: o CSS existente já reduz width para 100% no breakpoint.

path.write_text(text, encoding='utf-8')
print('Cards das empresas alterados de 2x2 para 1x4 com espaçamento próprio.')
