from pathlib import Path

app_path = Path('app.py')
app = app_path.read_text(encoding='utf-8')

# Cache específico da 968: evita reler PDFs/Excel em cada rerun do Streamlit.
cache_anchor = "# Configuração da página Web\nst.set_page_config(\n"
cache_code = r'''# Cache de processamento pesado da empresa 968 - Radani.
# Os arquivos são imutáveis durante o processamento e o cache é limitado para
# não reter meses antigos indefinidamente no Streamlit Cloud.
@st.cache_data(show_spinner=False, ttl=1800, max_entries=12)
def _radani_cache_extrato_pdf(conteudo: bytes, nome_arquivo: str):
    caminho = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(conteudo)
            caminho = tmp.name
        return processar_arquivo_pdf(caminho, nome_arquivo)
    finally:
        if caminho and os.path.exists(caminho):
            os.unlink(caminho)


@st.cache_data(show_spinner=False, ttl=1800, max_entries=8)
def _radani_cache_jaguares(arquivos_tuple, inicio_iso: str, fim_iso: str):
    return consolidar_jaguares(
        list(arquivos_tuple),
        pd.Timestamp(inicio_iso),
        pd.Timestamp(fim_iso),
    )


@st.cache_data(show_spinner=False, ttl=1800, max_entries=8)
def _radani_cache_comprovantes(arquivos_tuple, inicio_iso: str, fim_iso: str):
    return consolidar_comprovantes_sispag(
        list(arquivos_tuple),
        pd.Timestamp(inicio_iso),
        pd.Timestamp(fim_iso),
    )


'''
if '_radani_cache_extrato_pdf' not in app:
    if cache_anchor not in app:
        raise SystemExit('Âncora para cache da Radani não encontrada')
    app = app.replace(cache_anchor, cache_code + cache_anchor, 1)

inicio = "    if st.session_state['empresa_organizador'] == 'radani':\n"
fim = "    if st.session_state['empresa_organizador'] == 'up_pack':\n"
if inicio not in app or fim not in app:
    raise SystemExit('Bloco da Radani não encontrado')
antes, resto = app.split(inicio, 1)
bloco_antigo, depois = resto.split(fim, 1)

bloco_novo = r'''    if st.session_state['empresa_organizador'] == 'radani':
        config_radani = CONFIGURACOES_RADANI['radani']
        empresa_radani = config_radani['empresa']
        slug_radani = config_radani['slug']

        # Diferente de st.tabs: somente a ferramenta escolhida é executada.
        # Isso evita chamadas ao Supabase e à conferência enquanto o usuário
        # está apenas organizando os arquivos da 968.
        modo_radani = st.radio(
            'Ferramenta da 968',
            ['Organizar arquivos', 'Base Inteligente', 'Conferência com extrato'],
            horizontal=True,
            label_visibility='collapsed',
            key='radani_modo_ferramenta',
        )

        if modo_radani == 'Base Inteligente':
            st.caption('Base exclusiva da 968 · Itaú conta 508 · Bradesco conta 9.')
            renderizar_base_inteligente_empresa(
                slug_radani,
                empresa_radani,
                {'itau', 'bradesco'},
                config_radani['contas_bancarias']
            )

        elif modo_radani == 'Conferência com extrato':
            st.caption(
                'A conferência é carregada somente quando esta ferramenta está aberta, '
                'sem pesar no organizador da 968.'
            )
            renderizar_conferencia_autokraft(
                slug_radani,
                bancos_config=[
                    {'nome': 'Itaú', 'slug': 'itau'},
                    {'nome': 'Bradesco', 'slug': 'bradesco'},
                ]
            )

        else:
            st.caption(
                'O extrato define o período e os totais oficiais. Jaguar e comprovantes '
                'são analisados somente quando você clicar em Processar 968.'
            )
            bancos_radani = st.multiselect(
                'Bancos para organizar',
                ['Itaú', 'Bradesco'],
                default=['Itaú', 'Bradesco'],
                key='radani_bancos_selecionados'
            )

            col_radani_itau, col_radani_bradesco = st.columns(2)
            with col_radani_itau:
                extrato_radani_itau = st.file_uploader(
                    'Extrato — Itaú',
                    type=['pdf'],
                    key='radani_extrato_itau',
                    disabled='Itaú' not in bancos_radani
                )
                st.caption('Conta Domínio: 508')
            with col_radani_bradesco:
                extrato_radani_bradesco = st.file_uploader(
                    'Extrato — Bradesco',
                    type=['pdf'],
                    key='radani_extrato_bradesco',
                    disabled='Bradesco' not in bancos_radani
                )
                st.caption('Conta Domínio: 9')

            col_jaguar_radani, col_comp_radani = st.columns(2)
            with col_jaguar_radani:
                jaguares_radani = st.file_uploader(
                    'Planilhas auxiliares Jaguar',
                    type=['xlsx', 'xls'],
                    accept_multiple_files=True,
                    key='radani_jaguares',
                    help='Pode enviar Jaguar anual e lançamentos diversos. Só o período do extrato será utilizado.'
                )
            with col_comp_radani:
                comprovantes_sispag_radani = st.file_uploader(
                    'Comprovantes de salários / SISPAG',
                    type=['pdf'],
                    accept_multiple_files=True,
                    key='radani_comprovantes_sispag',
                    help='Opcional. Quando o total fecha, os comprovantes têm prioridade sobre a Jaguar.'
                )

            extratos_radani = {
                'Itaú': extrato_radani_itau,
                'Bradesco': extrato_radani_bradesco,
            }
            arquivos_ativos_radani = [
                (nome, extratos_radani.get(nome))
                for nome in bancos_radani
                if extratos_radani.get(nome) is not None
            ]

            # Assinatura barata e determinística para saber se o resultado salvo
            # ainda corresponde exatamente aos arquivos atualmente selecionados.
            assinatura_radani = hashlib.sha256()
            assinatura_radani.update('|'.join(sorted(bancos_radani)).encode('utf-8'))
            for nome_banco, arq in arquivos_ativos_radani:
                assinatura_radani.update(nome_banco.encode('utf-8'))
                assinatura_radani.update(arq.name.encode('utf-8', errors='ignore'))
                assinatura_radani.update(arq.getvalue())
            for arq in (jaguares_radani or []):
                assinatura_radani.update(arq.name.encode('utf-8', errors='ignore'))
                assinatura_radani.update(arq.getvalue())
            for arq in (comprovantes_sispag_radani or []):
                assinatura_radani.update(arq.name.encode('utf-8', errors='ignore'))
                assinatura_radani.update(arq.getvalue())
            assinatura_radani = assinatura_radani.hexdigest()

            pode_processar_radani = bool(arquivos_ativos_radani)
            if not pode_processar_radani:
                st.info('Envie pelo menos um extrato PDF para liberar o processamento.')

            processar_radani = st.button(
                'Processar 968',
                type='primary',
                use_container_width=True,
                disabled=not pode_processar_radani,
                key='radani_processar_arquivos',
            )

            if processar_radani:
                try:
                    dados_radani = {}
                    revisoes_radani = []
                    detalhes_radani = []
                    arquivos_jaguar_tuple = tuple(
                        (arq.name, arq.getvalue()) for arq in (jaguares_radani or [])
                    )
                    arquivos_comprovantes_tuple = tuple(
                        (arq.name, arq.getvalue()) for arq in (comprovantes_sispag_radani or [])
                    )

                    with st.spinner('Analisando a 968...'):
                        for nome_banco_radani, arquivo_extrato_radani in arquivos_ativos_radani:
                            movs_radani = _radani_cache_extrato_pdf(
                                arquivo_extrato_radani.getvalue(),
                                arquivo_extrato_radani.name,
                            )
                            df_extrato_radani = pd.DataFrame(movs_radani or [])
                            if df_extrato_radani.empty:
                                st.warning(
                                    f'Nenhum lançamento foi reconhecido no extrato do {nome_banco_radani}.'
                                )
                                continue
                            df_extrato_radani['DATA'] = pd.to_datetime(
                                df_extrato_radani['DATA'], dayfirst=True, errors='coerce'
                            )
                            df_extrato_radani = df_extrato_radani.dropna(subset=['DATA']).copy()
                            if df_extrato_radani.empty:
                                continue

                            inicio_radani = df_extrato_radani['DATA'].min().normalize()
                            fim_radani = df_extrato_radani['DATA'].max().normalize()
                            inicio_iso = inicio_radani.isoformat()
                            fim_iso = fim_radani.isoformat()

                            jaguar_periodo_radani = (
                                _radani_cache_jaguares(
                                    arquivos_jaguar_tuple, inicio_iso, fim_iso
                                )
                                if arquivos_jaguar_tuple
                                else pd.DataFrame()
                            )
                            comprovantes_periodo_radani = (
                                _radani_cache_comprovantes(
                                    arquivos_comprovantes_tuple, inicio_iso, fim_iso
                                )
                                if arquivos_comprovantes_tuple and nome_banco_radani == 'Itaú'
                                else pd.DataFrame()
                            )

                            analise_radani = analisar_desmembramentos(
                                df_extrato_radani,
                                jaguar_periodo_radani,
                                nome_banco_radani,
                                comprovantes_periodo_radani,
                            )
                            dados_radani[nome_banco_radani] = {
                                'principal': analise_radani.organizado,
                                'retirados': pd.DataFrame(),
                            }
                            if not analise_radani.revisoes.empty:
                                revisoes_radani.append(analise_radani.revisoes)
                            if not analise_radani.detalhamentos.empty:
                                detalhes_radani.append(analise_radani.detalhamentos)

                    if not dados_radani:
                        raise ValueError('Nenhum banco gerou lançamentos válidos.')

                    df_radani_total = pd.concat(
                        [d['principal'] for d in dados_radani.values()],
                        ignore_index=True
                    )
                    datas_radani = pd.to_datetime(
                        df_radani_total['DATA'], errors='coerce'
                    ).dropna()
                    if datas_radani.empty:
                        raise ValueError('Nenhuma data válida foi encontrada após a análise.')

                    modelo_bytes_radani = None
                    for caminho_modelo_radani in [
                        'Modelo dominio.xlsx', 'Modelo dominio(6).xlsx',
                        'Modelo Dominio.xlsx', 'modelo_dominio.xlsx'
                    ]:
                        if os.path.exists(caminho_modelo_radani):
                            with open(caminho_modelo_radani, 'rb') as arq_modelo_radani:
                                modelo_bytes_radani = arq_modelo_radani.read()
                            break
                    arquivo_final_radani = gerar_excel_nova_geracao(
                        dados_radani, modelo_bytes_radani
                    )

                    st.session_state['radani_resultado_processado'] = {
                        'assinatura': assinatura_radani,
                        'arquivo_final': arquivo_final_radani,
                        'total': int(len(df_radani_total)),
                        'entradas': float(df_radani_total.loc[df_radani_total['VALOR'] > 0, 'VALOR'].sum()),
                        'saidas': float(abs(df_radani_total.loc[df_radani_total['VALOR'] < 0, 'VALOR'].sum())),
                        'inicio': datas_radani.min(),
                        'fim': datas_radani.max(),
                        'detalhes': pd.concat(detalhes_radani, ignore_index=True) if detalhes_radani else pd.DataFrame(),
                        'revisoes': pd.concat(revisoes_radani, ignore_index=True) if revisoes_radani else pd.DataFrame(),
                    }
                except Exception as erro_radani:
                    st.session_state.pop('radani_resultado_processado', None)
                    st.error(f'Não foi possível processar os arquivos da empresa 968: {erro_radani}')

            resultado_radani = st.session_state.get('radani_resultado_processado')
            if resultado_radani and resultado_radani.get('assinatura') == assinatura_radani:
                m1_radani, m2_radani, m3_radani, m4_radani = st.columns(4)
                m1_radani.metric('Lançamentos finais', resultado_radani['total'])
                m2_radani.metric('Entradas', formatar_moeda(resultado_radani['entradas']))
                m3_radani.metric('Saídas', formatar_moeda(resultado_radani['saidas']))
                m4_radani.metric(
                    'Período',
                    f"{resultado_radani['inicio'].strftime('%d/%m')} a {resultado_radani['fim'].strftime('%d/%m')}"
                )

                df_detalhes_radani = resultado_radani['detalhes']
                df_revisoes_radani = resultado_radani['revisoes']
                if not df_detalhes_radani.empty:
                    qtd_grupos = int(df_detalhes_radani['HISTÓRICO BANCO'].nunique())
                    st.success(
                        f'{qtd_grupos} lançamento(s) consolidado(s) foram desmembrados com fechamento exato.'
                    )
                    if st.checkbox(
                        'Ver desmembramentos identificados',
                        value=False,
                        key='radani_ver_detalhes',
                    ):
                        st.dataframe(
                            df_detalhes_radani,
                            use_container_width=True,
                            hide_index=True,
                            height=330,
                        )

                if not df_revisoes_radani.empty:
                    st.warning(
                        f'{len(df_revisoes_radani)} lançamento(s) ficaram para revisão. '
                        'Correspondências ambíguas não são alteradas automaticamente.'
                    )
                    if st.checkbox(
                        'Ver lançamentos para revisão',
                        value=False,
                        key='radani_ver_revisoes',
                    ):
                        st.dataframe(
                            df_revisoes_radani,
                            use_container_width=True,
                            hide_index=True,
                            height=330,
                        )

                st.download_button(
                    'Baixar planilha no Modelo Domínio',
                    data=resultado_radani['arquivo_final'],
                    file_name=(
                        f"RADANI_968_{resultado_radani['inicio'].strftime('%m_%Y')}_Modelo_Dominio.xlsx"
                    ),
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    use_container_width=True,
                    key='radani_download_modelo'
                )
            elif resultado_radani:
                st.caption(
                    'Os arquivos selecionados mudaram. Clique em Processar 968 para gerar um novo resultado.'
                )

'''

app = antes + bloco_novo + fim + depois
app_path.write_text(app, encoding='utf-8')
