from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

# 1) Persistência: consulta e salva sempre dentro da empresa atual.
text = text.replace(
'''def salvar_classificacoes_online(registros):
    if not registros:
        return 0
    existentes = {item['id']: item for item in carregar_classificacoes_online()}
''',
'''def salvar_classificacoes_online(registros, empresa='nova_geracao'):
    if not registros:
        return 0
    existentes = {
        item['id']: item for item in carregar_classificacoes_online(empresa)
    }
''', 1)

# 2) Importação: IDs e coluna empresa deixam de ser fixos na Nova Geração.
text = text.replace(
'''def ler_planilha_classificada(file_bytes, filename):
    """Lê planilha com um ou vários bancos e extrai Débito/Crédito já revisados."""
''',
'''def ler_planilha_classificada(file_bytes, filename, empresa='nova_geracao'):
    """Lê planilha revisada e cria padrões exclusivos da empresa informada."""
''', 1)
text = text.replace(
'''                f"nova_geracao|{banco_linha}|{assinatura}|{debito}|{credito}".encode('utf-8')
''',
'''                f"{empresa}|{banco_linha}|{assinatura}|{debito}|{credito}".encode('utf-8')
''', 1)
text = text.replace("                'empresa': 'nova_geracao',\n", "                'empresa': empresa,\n", 1)
text = text.replace(
'''def importar_arquivos_classificados(arquivos):
    """Aceita XLSX individual, vários XLSX ou ZIP contendo planilhas."""
''',
'''def importar_arquivos_classificados(arquivos, empresa='nova_geracao'):
    """Aceita XLSX/ZIP e mantém o aprendizado isolado por empresa."""
''', 1)
text = text.replace(
'''                    registros.extend(ler_planilha_classificada(
                        pacote.read(membro), os.path.basename(membro.filename)
                    ))
''',
'''                    registros.extend(ler_planilha_classificada(
                        pacote.read(membro), os.path.basename(membro.filename), empresa
                    ))
''', 1)
text = text.replace(
'''            registros.extend(ler_planilha_classificada(conteudo, nome))
''',
'''            registros.extend(ler_planilha_classificada(conteudo, nome, empresa))
''', 1)

# 3) Bancos: Autokraft usa Itaú/Daycoval; Nova Geração mantém Itaú/Bradesco/Fibra.
text = text.replace(
'''            if banco_linha not in {'itau', 'bradesco', 'fibra'} or not assinatura:
                continue
''',
'''            if banco_linha not in {'itau', 'bradesco', 'fibra', 'daycoval'} or not assinatura:
                continue
''', 1)

# 4) UI reutilizável da Base Inteligente para qualquer empresa.
marker = '''# ==============================================================================\n# ORGANIZADORES ESPECÍFICOS POR EMPRESA\n# ==============================================================================\n'''
helper = r'''def renderizar_base_inteligente_empresa(empresa, nome_empresa, bancos_permitidos):
    """Base de Débito/Crédito isolada por empresa usando a mesma tabela Supabase."""
    url_base, chave_base, senha_admin = obter_config_classificacao_online()
    base = []
    erro_base = ''
    if url_base and chave_base:
        try:
            base = carregar_classificacoes_online(empresa)
        except Exception as erro:
            erro_base = str(erro)

    st.markdown(f"#### Base inteligente — {nome_empresa}")
    st.caption(
        "O aprendizado desta área é exclusivo desta empresa. Padrões de outras "
        "empresas não são usados aqui. Envie planilhas já revisadas, com DÉBITO e "
        "CRÉDITO preenchidos, para ensinar novos lançamentos."
    )
    if erro_base:
        st.warning(f"Não foi possível carregar a base online: {erro_base}")
    elif not url_base or not chave_base:
        st.warning("A conexão com a base online ainda não está configurada.")
    else:
        base_empresa = [item for item in base if item.get('banco') in bancos_permitidos]
        c1, c2 = st.columns(2)
        c1.metric("Padrões desta empresa", len(base_empresa))
        c2.metric(
            "Bancos com aprendizado",
            len({item.get('banco') for item in base_empresa if item.get('banco')})
        )

        arquivos_base = st.file_uploader(
            "Planilhas já classificadas",
            type=['xlsx', 'xls', 'zip'],
            accept_multiple_files=True,
            key=f"base_upload_{empresa}",
            help="Use somente arquivos revisados desta empresa."
        )
        senha_digitada = st.text_input(
            "Senha administrativa para gravar aprendizado",
            type="password",
            key=f"base_senha_{empresa}"
        ) if senha_admin else ''

        pode_gravar = bool(arquivos_base) and (
            not senha_admin or hmac.compare_digest(str(senha_digitada), str(senha_admin))
        )
        if arquivos_base and senha_admin and senha_digitada and not pode_gravar:
            st.error("Senha administrativa inválida.")

        if st.button(
            "Aprender com planilhas revisadas",
            key=f"base_aprender_{empresa}",
            disabled=not pode_gravar,
            use_container_width=True
        ):
            try:
                registros = importar_arquivos_classificados(arquivos_base, empresa)
                registros = [r for r in registros if r.get('banco') in bancos_permitidos]
                if not registros:
                    st.warning("Nenhum padrão válido foi encontrado para os bancos desta empresa.")
                else:
                    quantidade = salvar_classificacoes_online(registros, empresa)
                    st.success(f"{quantidade} padrões da {nome_empresa} foram gravados/atualizados.")
                    st.rerun()
            except Exception as erro:
                st.error(f"Não foi possível atualizar a base: {erro}")

        if base_empresa:
            linhas = []
            for item in base_empresa:
                linhas.append({
                    'Banco': nome_banco_por_chave(item.get('banco', '')),
                    'Débito': item.get('debito', ''),
                    'Crédito': item.get('credito', ''),
                    'Ocorrências': item.get('ocorrencias', 0),
                    'Períodos': len(item.get('periodos') or []),
                    'Exemplo': item.get('exemplo_historico', '')
                })
            st.dataframe(pd.DataFrame(linhas), use_container_width=True, height=300)
        else:
            st.info("Esta empresa ainda não possui padrões aprendidos.")

'''
if marker not in text:
    raise SystemExit('Marcador dos organizadores não encontrado.')
text = text.replace(marker, helper + marker, 1)

# 5) Cada Autokraft recebe sua própria aba, sem compartilhar base.
old_autokraft_start = '''        st.caption(
            f"Ferramentas ativas para {empresa_autokraft}. O sistema lê automaticamente "
            "cada aba diária, ignora saldos e totais e separa os lançamentos por banco."
        )
        bancos_autokraft = st.multiselect(
'''
new_autokraft_start = '''        aba_operacoes_autokraft, aba_base_autokraft = st.tabs([
            "Organizar e conferir",
            "Base inteligente de Débito e Crédito"
        ])
        with aba_operacoes_autokraft:
            st.caption(
                f"Ferramentas ativas para {empresa_autokraft}. O sistema lê automaticamente "
                "cada aba diária, ignora saldos e totais e separa os lançamentos por banco."
            )
        bancos_autokraft = st.multiselect(
'''
if old_autokraft_start not in text:
    raise SystemExit('Início da área Autokraft não encontrado.')
text = text.replace(old_autokraft_start, new_autokraft_start, 1)

# A aba de base fica após a conferência; as chaves são exclusivas pelo slug.
old_conf = '''        st.markdown(f"#### Conferência — {empresa_autokraft}")
        renderizar_conferencia_autokraft(slug_empresa_autokraft)

    if st.session_state['empresa_organizador'] == 'nova_geracao':
'''
new_conf = '''        st.markdown(f"#### Conferência — {empresa_autokraft}")
        renderizar_conferencia_autokraft(slug_empresa_autokraft)

        with aba_base_autokraft:
            renderizar_base_inteligente_empresa(
                slug_empresa_autokraft,
                empresa_autokraft,
                {'itau', 'daycoval'}
            )

    if st.session_state['empresa_organizador'] == 'nova_geracao':
'''
if old_conf not in text:
    raise SystemExit('Final da área Autokraft não encontrado.')
text = text.replace(old_conf, new_conf, 1)

# 6) Corrige chamadas da Nova Geração para deixá-las explicitamente isoladas.
text = text.replace('base_classificacoes = carregar_classificacoes_online()\n', "base_classificacoes = carregar_classificacoes_online('nova_geracao')\n", 1)
text = text.replace('registros_importados = importar_arquivos_classificados(arquivos_base)\n', "registros_importados = importar_arquivos_classificados(arquivos_base, 'nova_geracao')\n", 1)
text = text.replace('salvar_classificacoes_online(registros_importados)\n', "salvar_classificacoes_online(registros_importados, 'nova_geracao')\n", 1)

path.write_text(text, encoding='utf-8')
print('Bases inteligentes individuais adicionadas para as três empresas Autokraft.')
