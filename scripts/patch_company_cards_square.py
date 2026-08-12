from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

# 1) A Base Inteligente reutilizável recebe agora as contas bancárias corretas
# da empresa atual, exatamente como a Nova Geração já faz.
old_sig = '''def renderizar_base_inteligente_empresa(empresa, nome_empresa, bancos_permitidos):
'''
new_sig = '''def renderizar_base_inteligente_empresa(
    empresa, nome_empresa, bancos_permitidos, contas_bancarias
):
'''
if text.count(old_sig) != 1:
    raise SystemExit(f'Assinatura da base encontrada {text.count(old_sig)} vezes.')
text = text.replace(old_sig, new_sig, 1)

# Remove o mapa vazio temporário: a função passa a usar as contas recebidas.
old_empty_map = '''                    contas_bancarias = {
                        banco: '' for banco in bancos_permitidos
                    }
                    arquivo_classificado, resumo = executar_com_loading(
'''
new_empty_map = '''                    arquivo_classificado, resumo = executar_com_loading(
'''
if text.count(old_empty_map) != 1:
    raise SystemExit(f'Mapa bancário temporário encontrado {text.count(old_empty_map)} vezes.')
text = text.replace(old_empty_map, new_empty_map, 1)

# 2) Grava as contas específicas em cada configuração de empresa.
replacements = {
'''            'autokraft_industrial': {
                'empresa': '3 - Autokraft Industrial',
                'slug': 'autokraft_industrial',
                'arquivo': 'Autokraft_Industrial'
            },
''': '''            'autokraft_industrial': {
                'empresa': '3 - Autokraft Industrial',
                'slug': 'autokraft_industrial',
                'arquivo': 'Autokraft_Industrial',
                'contas_bancarias': {'itau': '508', 'daycoval': '2283'}
            },
''',
'''            'autokraft_projetos': {
                'empresa': '178 - Autokraft Projetos',
                'slug': 'autokraft_projetos',
                'arquivo': 'Autokraft_Projetos'
            },
''': '''            'autokraft_projetos': {
                'empresa': '178 - Autokraft Projetos',
                'slug': 'autokraft_projetos',
                'arquivo': 'Autokraft_Projetos',
                'contas_bancarias': {'itau': '508', 'daycoval': '505'}
            },
''',
'''            'isa': {
                'empresa': '343 - I.S.A',
                'slug': 'isa',
                'arquivo': 'ISA'
            }
''': '''            'isa': {
                'empresa': '343 - I.S.A',
                'slug': 'isa',
                'arquivo': 'ISA',
                'contas_bancarias': {'itau': '508', 'daycoval': '506'}
            }
'''
}
for old, new in replacements.items():
    if text.count(old) != 1:
        raise SystemExit(f'Configuração esperada encontrada {text.count(old)} vezes.')
    text = text.replace(old, new, 1)

# 3) Entrega o mapa correto para a classificação da planilha final.
old_call = '''            renderizar_base_inteligente_empresa(
                slug_empresa_autokraft,
                empresa_autokraft,
                {'itau', 'daycoval'}
            )
'''
new_call = '''            renderizar_base_inteligente_empresa(
                slug_empresa_autokraft,
                empresa_autokraft,
                {'itau', 'daycoval'},
                configuracao_empresa_autokraft['contas_bancarias']
            )
'''
if text.count(old_call) != 1:
    raise SystemExit(f'Chamada da base encontrada {text.count(old_call)} vezes.')
text = text.replace(old_call, new_call, 1)

# 4) Mostra para o usuário quais contas serão usadas, reduzindo risco de classificação
# com empresa errada sem perceber.
old_caption = '''    st.caption(
        "O aprendizado desta área é exclusivo desta empresa. Padrões de outras "
        "empresas não são usados aqui. Envie planilhas já revisadas, com DÉBITO e "
        "CRÉDITO preenchidos, para ensinar novos lançamentos."
    )
'''
new_caption = '''    st.caption(
        "O aprendizado desta área é exclusivo desta empresa. Padrões de outras "
        "empresas não são usados aqui. Envie planilhas já revisadas, com DÉBITO e "
        "CRÉDITO preenchidos, para ensinar novos lançamentos."
    )
    st.caption(
        "Contas bancárias automáticas: "
        + " | ".join(
            f"{nome_banco_por_chave(banco)} {conta}"
            for banco, conta in contas_bancarias.items()
        )
    )
'''
if text.count(old_caption) != 1:
    raise SystemExit(f'Caption da base encontrado {text.count(old_caption)} vezes.')
text = text.replace(old_caption, new_caption, 1)

path.write_text(text, encoding='utf-8')
print('Contas bancárias configuradas por empresa para classificação automática.')
