from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

old = '''        if empresa_autokraft != "3 - Autokraft Industrial":
            st.info(
                "Esta empresa já foi incluída na seleção. A conversão será liberada "
                "depois da validação da Autokraft Industrial."
            )
        else:
            st.caption(
                "O sistema lê automaticamente cada aba diária, ignora saldos e totais "
                "e separa os lançamentos por banco."
            )
            bancos_autokraft = st.multiselect(
                "Bancos para organizar",
                ["Itaú", "Daycoval"],
                default=["Itaú", "Daycoval"],
                key="org_bancos_autokraft"
            )
            arquivo_autokraft = st.file_uploader(
                "Envie o mapa bancário da Autokraft Industrial",
                type=['xlsx', 'xls'],
                key="upload_mapa_autokraft_industrial",
                help="O arquivo pode conter todas as abas diárias do mês."
            )

            if arquivo_autokraft is not None:
                try:
                    dados_autokraft, abas_autokraft = processar_mapa_autokraft(
                        arquivo_autokraft.getvalue(), arquivo_autokraft.name
                    )
                    datas_disponiveis = []
                    for dados_banco in dados_autokraft.values():
                        df_banco = dados_banco['principal']
                        if not df_banco.empty:
                            datas_disponiveis.extend(
                                pd.to_datetime(df_banco['DATA'], errors='coerce').dropna().dt.date.tolist()
                            )
                    if not datas_disponiveis:
                        raise ValueError("Nenhuma data válida foi localizada nas abas diárias.")

                    data_min_autokraft = min(datas_disponiveis)
                    data_max_autokraft = max(datas_disponiveis)
                    col_data_ak1, col_data_ak2 = st.columns(2)
                    with col_data_ak1:
                        data_ini_autokraft = st.date_input(
                            "Data inicial",
                            value=data_min_autokraft,
                            min_value=data_min_autokraft,
                            max_value=data_max_autokraft,
                            format="DD/MM/YYYY",
                            key="data_ini_autokraft"
                        )
                    with col_data_ak2:
                        data_fim_autokraft = st.date_input(
                            "Data final",
                            value=data_max_autokraft,
                            min_value=data_min_autokraft,
                            max_value=data_max_autokraft,
                            format="DD/MM/YYYY",
                            key="data_fim_autokraft"
                        )

                    if data_ini_autokraft > data_fim_autokraft:
                        st.warning("A data inicial deve ser anterior ou igual à data final.")
                    elif not bancos_autokraft:
                        st.warning("Selecione pelo menos um banco para gerar a planilha.")
                    else:
                        dados_filtrados_autokraft = {}
                        for nome_banco in bancos_autokraft:
                            df_filtrado = filtrar_dataframe_periodo(
                                dados_autokraft[nome_banco]['principal'],
                                data_ini_autokraft,
                                data_fim_autokraft
                            )
                            dados_filtrados_autokraft[nome_banco] = {
                                'principal': df_filtrado,
                                'retirados': pd.DataFrame()
                            }

                        df_resumo_autokraft = pd.concat(
                            [dados['principal'] for dados in dados_filtrados_autokraft.values()],
                            ignore_index=True
                        )
                        total_autokraft = len(df_resumo_autokraft)
                        entradas_autokraft = df_resumo_autokraft.loc[
                            df_resumo_autokraft['VALOR'] > 0, 'VALOR'
                        ].sum() if not df_resumo_autokraft.empty else 0
                        saidas_autokraft = abs(df_resumo_autokraft.loc[
                            df_resumo_autokraft['VALOR'] < 0, 'VALOR'
                        ].sum()) if not df_resumo_autokraft.empty else 0

                        met_ak1, met_ak2, met_ak3 = st.columns(3)
                        with met_ak1:
                            st.metric("Lançamentos", total_autokraft)
                        with met_ak2:
                            st.metric("Entradas", formatar_moeda(entradas_autokraft))
                        with met_ak3:
                            st.metric("Saídas", formatar_moeda(saidas_autokraft))

                        st.caption(
                            f"{len(abas_autokraft)} abas diárias reconhecidas, de "
                            f"{data_min_autokraft.strftime('%d/%m/%Y')} a "
                            f"{data_max_autokraft.strftime('%d/%m/%Y')}."
                        )
                        if df_resumo_autokraft.empty:
                            st.warning("Não há lançamentos para os bancos e período escolhidos.")
                        else:
                            arquivo_final_autokraft = gerar_excel_nova_geracao(
                                dados_filtrados_autokraft
                            )
                            st.download_button(
                                "Baixar planilha no Modelo Domínio",
                                data=arquivo_final_autokraft,
                                file_name=(
                                    "Autokraft_Industrial_"
                                    f"{data_ini_autokraft.strftime('%d%m%Y')}_a_"
                                    f"{data_fim_autokraft.strftime('%d%m%Y')}.xlsx"
                                ),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                key="download_autokraft_industrial"
                            )
                except Exception as erro_autokraft:
                    st.error(f"Não foi possível processar o mapa Autokraft: {erro_autokraft}")

            renderizar_conferencia_autokraft()
'''

new = '''        configuracao_empresa_autokraft = {
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
        slug_empresa_autokraft = configuracao_empresa_autokraft["slug"]

        # Evita reaproveitar uploads e seleções de conferência de outra empresa.
        if st.session_state.get('_autokraft_empresa_ativa') != slug_empresa_autokraft:
            for chave_estado in [
                'autokraft_conferir_todos', 'autokraft_bancos_conferencia',
                'autokraft_planilha_final_conferencia', 'autokraft_extrato_itau',
                'autokraft_extrato_daycoval'
            ]:
                st.session_state.pop(chave_estado, None)
            st.session_state['_autokraft_empresa_ativa'] = slug_empresa_autokraft

        st.caption(
            f"Ferramentas ativas para {empresa_autokraft}. O sistema lê automaticamente "
            "cada aba diária, ignora saldos e totais e separa os lançamentos por banco."
        )
        bancos_autokraft = st.multiselect(
            "Bancos para organizar",
            ["Itaú", "Daycoval"],
            default=["Itaú", "Daycoval"],
            key=f"org_bancos_{slug_empresa_autokraft}"
        )
        arquivo_autokraft = st.file_uploader(
            f"Envie o mapa bancário da {empresa_autokraft}",
            type=['xlsx', 'xls'],
            key=f"upload_mapa_{slug_empresa_autokraft}",
            help="O arquivo pode conter todas as abas diárias do mês."
        )

        if arquivo_autokraft is not None:
            try:
                dados_autokraft, abas_autokraft = processar_mapa_autokraft(
                    arquivo_autokraft.getvalue(), arquivo_autokraft.name
                )
                datas_disponiveis = []
                for dados_banco in dados_autokraft.values():
                    df_banco = dados_banco['principal']
                    if not df_banco.empty:
                        datas_disponiveis.extend(
                            pd.to_datetime(df_banco['DATA'], errors='coerce').dropna().dt.date.tolist()
                        )
                if not datas_disponiveis:
                    raise ValueError("Nenhuma data válida foi localizada nas abas diárias.")

                data_min_autokraft = min(datas_disponiveis)
                data_max_autokraft = max(datas_disponiveis)
                col_data_ak1, col_data_ak2 = st.columns(2)
                with col_data_ak1:
                    data_ini_autokraft = st.date_input(
                        "Data inicial",
                        value=data_min_autokraft,
                        min_value=data_min_autokraft,
                        max_value=data_max_autokraft,
                        format="DD/MM/YYYY",
                        key=f"data_ini_{slug_empresa_autokraft}"
                    )
                with col_data_ak2:
                    data_fim_autokraft = st.date_input(
                        "Data final",
                        value=data_max_autokraft,
                        min_value=data_min_autokraft,
                        max_value=data_max_autokraft,
                        format="DD/MM/YYYY",
                        key=f"data_fim_{slug_empresa_autokraft}"
                    )

                if data_ini_autokraft > data_fim_autokraft:
                    st.warning("A data inicial deve ser anterior ou igual à data final.")
                elif not bancos_autokraft:
                    st.warning("Selecione pelo menos um banco para gerar a planilha.")
                else:
                    dados_filtrados_autokraft = {}
                    for nome_banco in bancos_autokraft:
                        df_filtrado = filtrar_dataframe_periodo(
                            dados_autokraft[nome_banco]['principal'],
                            data_ini_autokraft,
                            data_fim_autokraft
                        )
                        dados_filtrados_autokraft[nome_banco] = {
                            'principal': df_filtrado,
                            'retirados': pd.DataFrame()
                        }

                    df_resumo_autokraft = pd.concat(
                        [dados['principal'] for dados in dados_filtrados_autokraft.values()],
                        ignore_index=True
                    )
                    total_autokraft = len(df_resumo_autokraft)
                    entradas_autokraft = df_resumo_autokraft.loc[
                        df_resumo_autokraft['VALOR'] > 0, 'VALOR'
                    ].sum() if not df_resumo_autokraft.empty else 0
                    saidas_autokraft = abs(df_resumo_autokraft.loc[
                        df_resumo_autokraft['VALOR'] < 0, 'VALOR'
                    ].sum()) if not df_resumo_autokraft.empty else 0

                    met_ak1, met_ak2, met_ak3 = st.columns(3)
                    with met_ak1:
                        st.metric("Lançamentos", total_autokraft)
                    with met_ak2:
                        st.metric("Entradas", formatar_moeda(entradas_autokraft))
                    with met_ak3:
                        st.metric("Saídas", formatar_moeda(saidas_autokraft))

                    st.caption(
                        f"{len(abas_autokraft)} abas diárias reconhecidas, de "
                        f"{data_min_autokraft.strftime('%d/%m/%Y')} a "
                        f"{data_max_autokraft.strftime('%d/%m/%Y')}."
                    )
                    if df_resumo_autokraft.empty:
                        st.warning("Não há lançamentos para os bancos e período escolhidos.")
                    else:
                        arquivo_final_autokraft = gerar_excel_nova_geracao(
                            dados_filtrados_autokraft
                        )
                        st.download_button(
                            "Baixar planilha no Modelo Domínio",
                            data=arquivo_final_autokraft,
                            file_name=(
                                f"{configuracao_empresa_autokraft['arquivo']}_"
                                f"{data_ini_autokraft.strftime('%d%m%Y')}_a_"
                                f"{data_fim_autokraft.strftime('%d%m%Y')}.xlsx"
                            ),
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            key=f"download_{slug_empresa_autokraft}"
                        )
            except Exception as erro_autokraft:
                st.error(
                    f"Não foi possível processar o mapa de {empresa_autokraft}: "
                    f"{erro_autokraft}"
                )

        st.markdown(f"#### Conferência — {empresa_autokraft}")
        renderizar_conferencia_autokraft()
'''

if old not in text:
    raise SystemExit("Bloco Autokraft esperado não foi encontrado; patch não aplicado.")

path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("app.py atualizado com ferramentas para todas as empresas Autokraft.")
