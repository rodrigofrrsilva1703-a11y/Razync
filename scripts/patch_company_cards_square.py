from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

fixes = {
'''        .st-key-org_empresa_card_nova button p,
        .st-key-org_empresa_card_autokraft_industrial button,
        .st-key-org_empresa_card_autokraft_projetos button,
        .st-key-org_empresa_card_isa button p {''':
'''        .st-key-org_empresa_card_nova button p,
        .st-key-org_empresa_card_autokraft_industrial button p,
        .st-key-org_empresa_card_autokraft_projetos button p,
        .st-key-org_empresa_card_isa button p {''',
'''        .st-key-org_empresa_card_nova button strong,
        .st-key-org_empresa_card_autokraft_industrial button,
        .st-key-org_empresa_card_autokraft_projetos button,
        .st-key-org_empresa_card_isa button strong {''':
'''        .st-key-org_empresa_card_nova button strong,
        .st-key-org_empresa_card_autokraft_industrial button strong,
        .st-key-org_empresa_card_autokraft_projetos button strong,
        .st-key-org_empresa_card_isa button strong {''',
'''        .st-key-org_empresa_card_nova button:hover,
        .st-key-org_empresa_card_autokraft_industrial button,
        .st-key-org_empresa_card_autokraft_projetos button,
        .st-key-org_empresa_card_isa button:hover {''':
'''        .st-key-org_empresa_card_nova button:hover,
        .st-key-org_empresa_card_autokraft_industrial button:hover,
        .st-key-org_empresa_card_autokraft_projetos button:hover,
        .st-key-org_empresa_card_isa button:hover {''',
}

for old, new in fixes.items():
    if text.count(old) != 1:
        raise SystemExit(f'Seletores esperados encontrados {text.count(old)} vezes; alteração cancelada.')
    text = text.replace(old, new, 1)

path.write_text(text, encoding='utf-8')
print('Seletores CSS dos quatro cards corrigidos e isolados.')
