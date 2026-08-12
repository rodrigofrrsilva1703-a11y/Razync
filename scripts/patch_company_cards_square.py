from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old = '''    with col_tit:
        st.title({
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
        empresa_organizador,
        'Selecione uma empresa para abrir sua área de trabalho exclusiva.'
    ))
'''
new = '''    estabelecimento_ng_atual = st.session_state.get(
        'org_estabelecimento_nova_geracao_card', 'matriz'
    )
    titulo_nova_geracao_atual = (
        '1396 - Nova Geração'
        if estabelecimento_ng_atual == 'filial'
        else '266 - Nova Geração'
    )

    with col_tit:
        st.title({
            'nova_geracao': titulo_nova_geracao_atual,
            'autokraft_industrial': '3 - Autokraft Industrial',
            'autokraft_projetos': '178 - Autokraft Projetos',
            'isa': '343 - I.S.A'
        }.get(empresa_organizador, 'Organizador de Planilhas'))
    st.caption({
        'nova_geracao': f'Organize, confira e classifique os movimentos da {titulo_nova_geracao_atual}.',
        'autokraft_industrial': 'Organize os mapas diários e confira os extratos da 3 - Autokraft Industrial.',
        'autokraft_projetos': 'Organize os mapas diários e confira os extratos da 178 - Autokraft Projetos.',
        'isa': 'Organize os mapas diários e confira os extratos da 343 - I.S.A.'
    }.get(
        empresa_organizador,
        'Selecione uma empresa para abrir sua área de trabalho exclusiva.'
    ))
'''

if text.count(old) != 1:
    raise SystemExit(f'Bloco do título principal encontrado {text.count(old)} vezes.')
text = text.replace(old, new, 1)

if "titulo_nova_geracao_atual" not in text:
    raise SystemExit('Título dinâmico não foi criado.')
if "'1396 - Nova Geração'" not in text:
    raise SystemExit('Título da filial não foi preservado.')
if "'nova_geracao_filial'" not in text:
    raise SystemExit('Base independente da filial não foi preservada.')

path.write_text(text, encoding='utf-8')
print('Título principal agora acompanha Matriz/Filial da Nova Geração.')
