from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

# 1) Identificação bancária específica da 242 no aprendizado.
needle = "def ler_planilha_classificada(file_bytes, filename, empresa='nova_geracao'):\n"
helper = '''def identificar_banco_classificacao_eletro_forte(nome_aba='', descricao='', debito='', credito=''):
    """Distingue BB 8, Itaú 508 e Itaú 509 na empresa 242."""
    valores = {
        texto_celula_seguro(debito),
        texto_celula_seguro(credito),
    }
    if '509' in valores:
        return 'itau_509'
    if '508' in valores:
        return 'itau_508'
    if '8' in valores:
        return 'bb'

    texto = normalizar_texto(f"{nome_aba} {descricao}")
    if '509' in texto or '181537' in texto:
        return 'itau_509'
    if '508' in texto or '105318' in texto:
        return 'itau_508'
    if 'bb' in texto or 'banco do brasil' in texto:
        return 'bb'
    return ''


'''
if helper.strip() not in s:
    if needle not in s:
        raise SystemExit('ler_planilha_classificada não localizado')
    s = s.replace(needle, helper + needle, 1)

old = '''            banco_linha = (
                identificar_chave_banco_empresa(linha[col_descricao])
                if col_descricao is not None else ''
            ) or banco_aba or banco_arquivo
            assinatura = criar_assinatura_classificacao(historico)
            if banco_linha not in {'itau', 'bradesco', 'fibra', 'daycoval', 'sicredi', 'santander'} or not assinatura:
                continue
'''
new = '''            descricao_linha = linha[col_descricao] if col_descricao is not None else ''
            if empresa == 'eletro_forte':
                banco_linha = identificar_banco_classificacao_eletro_forte(
                    nome_aba, descricao_linha, debito, credito
                )
                bancos_validos = {'bb', 'itau_508', 'itau_509'}
            else:
                banco_linha = (
                    identificar_chave_banco_empresa(descricao_linha)
                    if col_descricao is not None else ''
                ) or banco_aba or banco_arquivo
                bancos_validos = {'itau', 'bradesco', 'fibra', 'daycoval', 'sicredi', 'santander'}
            assinatura = criar_assinatura_classificacao(historico)
            if banco_linha not in bancos_validos or not assinatura:
                continue
'''
if old not in s:
    raise SystemExit('bloco de aprendizado bancário não localizado')
s = s.replace(old, new, 1)

# 2) Classificador geral recebe uma regra opcional, usada somente pela 242.
old_sig = '''def classificar_planilha_final(
    file_bytes, filename, base_classificacoes, contas_bancarias=None
):
'''
new_sig = '''def classificar_planilha_final(
    file_bytes, filename, base_classificacoes, contas_bancarias=None,
    empresa_classificacao='', coluna_substituir='', valores_substituiveis=None
):
'''
if old_sig not in s:
    raise SystemExit('assinatura classificar_planilha_final não localizada')
s = s.replace(old_sig, new_sig, 1)

# Resumo com métricas específicas.
old_resumo = "        'abas_processadas': 0,\n    }"
new_resumo = "        'abas_processadas': 0,\n        'elegiveis_regra': 0,\n        'preservados_regra': 0,\n    }"
pos_class = s.index('def classificar_planilha_final(')
pos_res = s.find(old_resumo, pos_class)
if pos_res == -1:
    raise SystemExit('resumo do classificador não localizado')
s = s[:pos_res] + s[pos_res:].replace(old_resumo, new_resumo, 1)

old_full = '''            debito_atual = texto_celula_seguro(ws.cell(numero_linha, col_debito).value)
            credito_atual = texto_celula_seguro(ws.cell(numero_linha, col_credito).value)
            if debito_atual and credito_atual:
                resumo['ja_preenchidos'] += 1
                continue
            linha_estava_parcial = bool(debito_atual or credito_atual)
'''
new_full = '''            debito_atual = texto_celula_seguro(ws.cell(numero_linha, col_debito).value)
            credito_atual = texto_celula_seguro(ws.cell(numero_linha, col_credito).value)

            # Na 242, algumas contas são placeholders e precisam ser substituídas
            # pela Base Inteligente. Todo valor fora da lista é preservado.
            coluna_regra = normalizar_texto(coluna_substituir or '').strip()
            valores_regra = {
                texto_celula_seguro(v) for v in (valores_substituiveis or [])
            }
            if coluna_regra in {'debito', 'credito'}:
                atual_regra = debito_atual if coluna_regra == 'debito' else credito_atual
                if atual_regra not in valores_regra:
                    resumo['preservados_regra'] += 1
                    resumo['ja_preenchidos'] += 1
                    continue
                resumo['elegiveis_regra'] += 1
                if coluna_regra == 'debito':
                    ws.cell(numero_linha, col_debito).value = None
                    debito_atual = ''
                else:
                    ws.cell(numero_linha, col_credito).value = None
                    credito_atual = ''
            elif debito_atual and credito_atual:
                resumo['ja_preenchidos'] += 1
                continue
            linha_estava_parcial = bool(debito_atual or credito_atual)
'''
pos_full = s.find(old_full, pos_class)
if pos_full == -1:
    raise SystemExit('bloco débito/crédito do classificador não localizado')
s = s[:pos_full] + s[pos_full:].replace(old_full, new_full, 1)

old_bank = '''            banco_linha = (
                identificar_chave_banco_empresa(ws.cell(numero_linha, col_descricao).value)
                if col_descricao is not None else ''
            ) or banco_aba
            if banco_linha not in contas_bancarias:
                resumo['banco_nao_identificado'] += 1
                continue
'''
new_bank = '''            descricao_linha = (
                ws.cell(numero_linha, col_descricao).value
                if col_descricao is not None else ''
            )
            if empresa_classificacao == 'eletro_forte':
                banco_linha = identificar_banco_classificacao_eletro_forte(
                    ws.title, descricao_linha, debito_atual, credito_atual
                )
            else:
                banco_linha = (
                    identificar_chave_banco_empresa(descricao_linha)
                    if col_descricao is not None else ''
                ) or banco_aba
            if banco_linha not in contas_bancarias:
                resumo['banco_nao_identificado'] += 1
                continue
'''
pos_bank = s.find(old_bank, pos_class)
if pos_bank == -1:
    raise SystemExit('identificação bancária do classificador não localizada')
s = s[:pos_bank] + s[pos_bank:].replace(old_bank, new_bank, 1)

# 3) Renderer próprio da Base Inteligente da 242.
marker = '# ==============================================================================\n# ORGANIZADORES ESPECÍFICOS POR EMPRESA\n# ==============================================================================\n'
if marker not in s:
    raise SystemExit('marcador dos organizadores não localizado')

renderer = r'''def renderizar_base_inteligente_eletro_forte():
    empresa = 'eletro_forte'
    nome_empresa = '242 - ELETRO FORTE COMERCIAL ELETRICA LTDA'
    bancos_permitidos = {'bb', 'itau_508', 'itau_509'}
    contas_bancarias = {'bb': '8', 'itau_508': '508', 'itau_509': '509'}

    url_base, chave_base, senha_admin = obter_config_classificacao_online()
    base = []
    erro_base = ''
    if url_base and chave_base:
        try:
            base = carregar_classificacoes_online(empresa)
        except Exception as erro:
            erro_base = str(erro)

    st.markdown(f'#### Base inteligente — {nome_empresa}')
    st.caption(
        'O aprendizado é exclusivo da empresa 242 e mantém BB 8, Itaú 508 e Itaú 509 '
        'separados. A classificação também é separada por origem: Despesa, Fornecedor e Recebido.'
    )
    st.caption(
        'Fornecedor: somente DÉBITO 166 ou 0 é substituído. '
        'Recebido: somente CRÉDITO 166, 0, 14 ou 16 é substituído. '
        'Demais contas preenchidas são preservadas.'
    )

    if erro_base:
        st.warning(f'Não foi possível carregar a base online: {erro_base}')
        return
    if not url_base or not chave_base:
        st.warning('A conexão com a base online ainda não está configurada.')
        return

    base_empresa = [item for item in base if item.get('banco') in bancos_permitidos]
    c1, c2 = st.columns(2)
    c1.metric('Padrões desta empresa', len(base_empresa))
    c2.metric('Contas com aprendizado', len({item.get('banco') for item in base_empresa if item.get('banco')}))

    st.markdown('##### Ensinar a Base Inteligente')
    arquivos_base = st.file_uploader(
        'Planilhas já classificadas da 242',
        type=['xlsx', 'xls', 'zip'],
        accept_multiple_files=True,
        key='base_upload_eletro_forte',
        help='Use somente arquivos revisados da empresa 242.'
    )
    senha_digitada = st.text_input(
        'Senha administrativa para gravar aprendizado',
        type='password',
        key='base_senha_eletro_forte'
    ) if senha_admin else ''
    pode_gravar = bool(arquivos_base) and (
        not senha_admin or hmac.compare_digest(str(senha_digitada), str(senha_admin))
    )
    if arquivos_base and senha_admin and senha_digitada and not pode_gravar:
        st.error('Senha administrativa inválida.')
    if st.button(
        'Aprender com planilhas revisadas',
        key='base_aprender_eletro_forte',
        disabled=not pode_gravar,
        use_container_width=True
    ):
        try:
            registros = importar_arquivos_classificados(arquivos_base, empresa)
            registros = [r for r in registros if r.get('banco') in bancos_permitidos]
            if not registros:
                st.warning('Nenhum padrão válido da 242 foi encontrado.')
            else:
                quantidade = salvar_classificacoes_online(registros, empresa)
                st.success(f'{quantidade} padrões da empresa 242 foram gravados/atualizados.')
                st.rerun()
        except Exception as erro:
            st.error(f'Não foi possível atualizar a base: {erro}')

    if not base_empresa:
        st.info('A empresa 242 ainda não possui padrões aprendidos.')

    st.markdown('---')
    st.markdown('#### Classificar por planilha')
    abas = st.tabs(['Despesa', 'Fornecedor', 'Recebido'])
    configuracoes = [
        ('Despesa', '', set()),
        ('Fornecedor', 'debito', {'166', '0'}),
        ('Recebido', 'credito', {'166', '0', '14', '16'}),
    ]

    for aba, (origem, coluna_regra, valores_regra) in zip(abas, configuracoes):
        with aba:
            if origem == 'Fornecedor':
                st.caption('Somente linhas com DÉBITO 166 ou 0 serão classificadas.')
            elif origem == 'Recebido':
                st.caption('Somente linhas com CRÉDITO 166, 0, 14 ou 16 serão classificadas.')
            else:
                st.caption('Classificação exclusiva da planilha de Despesa; nenhuma regra adicional foi definida para substituir contas já preenchidas.')

            planilha_final = st.file_uploader(
                f'Planilha {origem} para classificar',
                type=['xlsx'],
                key=f'base_242_classificar_{origem.lower()}'
            )
            if not planilha_final:
                continue
            if not base_empresa:
                st.warning('A Base Inteligente da 242 ainda não possui padrões aprendidos.')
                continue

            try:
                arquivo_classificado, resumo = executar_com_loading(
                    f'Classificando {origem}...',
                    classificar_planilha_final,
                    planilha_final.getvalue(),
                    planilha_final.name,
                    base_empresa,
                    contas_bancarias,
                    'eletro_forte',
                    coluna_regra,
                    valores_regra,
                )
                m1, m2, m3 = st.columns(3)
                m1.metric('Classificados automaticamente', int(resumo.get('automaticos', 0)))
                m2.metric('Linhas elegíveis pela regra', int(resumo.get('elegiveis_regra', 0)))
                m3.metric('Contas preservadas', int(resumo.get('preservados_regra', 0)))

                renderizar_revisao_inteligente(
                    arquivo_classificado,
                    planilha_final.getvalue(),
                    planilha_final.name,
                    empresa,
                    contas_bancarias,
                    senha_admin,
                    f'base_revisao_242_{origem.lower()}'
                )
            except Exception as erro_classificacao:
                st.error(f'Não foi possível classificar a planilha {origem}: {erro_classificacao}')


'''
if 'def renderizar_base_inteligente_eletro_forte()' not in s:
    s = s.replace(marker, renderer + marker, 1)

# 4) 242 usa o renderer próprio.
old_call = '''        with aba_base_ef:
            renderizar_base_inteligente_empresa(
                'eletro_forte', empresa_ef, {'bb', 'itau_508', 'itau_509'},
                {'bb': '8', 'itau_508': '508', 'itau_509': '509'},
            )
'''
new_call = '''        with aba_base_ef:
            renderizar_base_inteligente_eletro_forte()
'''
if old_call not in s:
    raise SystemExit('chamada da Base Inteligente 242 não localizada')
s = s.replace(old_call, new_call, 1)

p.write_text(s, encoding='utf-8')
