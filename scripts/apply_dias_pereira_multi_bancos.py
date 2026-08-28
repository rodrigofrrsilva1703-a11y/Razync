from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')
start = text.index("            banco_nibo_rotulo = st.selectbox(")
end_marker = "                except Exception as erro_nibo:\n                    st.error(f'Não foi possível processar o relatório Nibo: {erro_nibo}')\n"
end = text.index(end_marker, start) + len(end_marker)

new = '''            bancos_nibo_selecionados = st.multiselect(
                'Bancos deste processamento Nibo',
                list(bancos_dias_pereira.keys()),
                default=[list(bancos_dias_pereira.keys())[0]],
                key='dias_pereira_bancos_nibo',
                help='Você pode selecionar Itaú, Banco do Brasil ou os dois bancos ao mesmo tempo.'
            )

            arquivos_nibo_por_banco = {}
            if not bancos_nibo_selecionados:
                st.info('Selecione pelo menos um banco para continuar.')
            else:
                st.caption(
                    'Envie um PDF para cada banco selecionado. Quando os dois forem enviados, '
                    'o Razync gera um único Modelo Domínio consolidado.'
                )
                for banco_nibo_rotulo in bancos_nibo_selecionados:
                    config_banco_nibo = bancos_dias_pereira[banco_nibo_rotulo]
                    arquivo_nibo = st.file_uploader(
                        f"Extrato Nibo em PDF — {banco_nibo_rotulo}",
                        type=['pdf'],
                        key=f"dias_pereira_extrato_nibo_{config_banco_nibo['slug']}",
                        help='Use o relatório mensal de Contas & Extratos do Nibo.'
                    )
                    if arquivo_nibo is not None:
                        arquivos_nibo_por_banco[banco_nibo_rotulo] = arquivo_nibo

            todos_arquivos_nibo_enviados = (
                bool(bancos_nibo_selecionados)
                and len(arquivos_nibo_por_banco) == len(bancos_nibo_selecionados)
            )

            if todos_arquivos_nibo_enviados:
                try:
                    quadros_nibo = []
                    configs_nibo_processados = []
                    with st.spinner('Lendo e organizando os relatórios Nibo...'):
                        for banco_nibo_rotulo in bancos_nibo_selecionados:
                            config_banco_nibo = bancos_dias_pereira[banco_nibo_rotulo]
                            arquivo_nibo = arquivos_nibo_por_banco[banco_nibo_rotulo]
                            df_nibo = processar_extrato_nibo_pdf(arquivo_nibo.getvalue())
                            df_banco_nibo = df_nibo[
                                ['DESCRIÇÃO', 'DATA', 'VALOR', 'DÉBITO', 'CRÉDITO', 'HISTÓRICO']
                            ].copy()
                            df_banco_nibo['DESCRIÇÃO'] = config_banco_nibo['descricao']
                            quadros_nibo.append(df_banco_nibo)
                            configs_nibo_processados.append(config_banco_nibo)

                    df_export_nibo = pd.concat(quadros_nibo, ignore_index=True)
                    df_export_nibo['_DATA_ORDEM'] = pd.to_datetime(
                        df_export_nibo['DATA'], dayfirst=True, errors='coerce'
                    )
                    df_export_nibo = (
                        df_export_nibo
                        .sort_values(['_DATA_ORDEM', 'DESCRIÇÃO'], kind='stable')
                        .drop(columns=['_DATA_ORDEM'])
                        .reset_index(drop=True)
                    )
                    datas_nibo = pd.to_datetime(
                        df_export_nibo['DATA'], dayfirst=True, errors='coerce'
                    )
                    entradas_nibo = df_export_nibo.loc[
                        df_export_nibo['VALOR'] > 0, 'VALOR'
                    ].sum()
                    saidas_nibo = abs(df_export_nibo.loc[
                        df_export_nibo['VALOR'] < 0, 'VALOR'
                    ].sum())

                    col_nibo_1, col_nibo_2, col_nibo_3 = st.columns(3)
                    col_nibo_1.metric(
                        'Lançamentos', f'{len(df_export_nibo):,}'.replace(',', '.')
                    )
                    col_nibo_2.metric(
                        'Entradas',
                        f'R$ {entradas_nibo:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
                    )
                    col_nibo_3.metric(
                        'Saídas',
                        f'R$ {saidas_nibo:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
                    )

                    st.success('Relatório(s) Nibo organizado(s) com sucesso.')
                    st.dataframe(
                        df_export_nibo[['DESCRIÇÃO', 'DATA', 'VALOR', 'HISTÓRICO']],
                        use_container_width=True,
                        hide_index=True
                    )

                    excel_nibo = gerar_excel_modelo_dominio(df_export_nibo)
                    datas_validas = datas_nibo.dropna()
                    bancos_nome_arquivo = '_'.join(
                        config['arquivo'] for config in configs_nibo_processados
                    )
                    if not datas_validas.empty:
                        nome_nibo = (
                            f"1529_Dias_Pereira_{bancos_nome_arquivo}_"
                            f"{datas_validas.min().strftime('%m_%Y')}.xlsx"
                        )
                    else:
                        nome_nibo = (
                            f"1529_Dias_Pereira_{bancos_nome_arquivo}_Modelo_Dominio.xlsx"
                        )

                    arquivo_saida_nibo = excel_nibo
                    resumo_nibo = {}
                    try:
                        base_dias_pereira = carregar_classificacoes_online('dias_pereira')
                        bancos_slugs_nibo = {
                            config['slug'] for config in configs_nibo_processados
                        }
                        base_bancos_nibo = [
                            item for item in base_dias_pereira
                            if item.get('banco') in bancos_slugs_nibo
                        ]
                        arquivo_saida_nibo, resumo_nibo = classificar_planilha_final(
                            excel_nibo,
                            nome_nibo,
                            base_bancos_nibo,
                            contas_dias_pereira
                        )
                    except Exception as erro_base_nibo:
                        st.info(
                            'O Modelo Domínio foi gerado normalmente, mas a Base Inteligente '
                            f'não pôde ser aplicada agora: {erro_base_nibo}'
                        )

                    if resumo_nibo:
                        c_auto_1, c_auto_2 = st.columns(2)
                        c_auto_1.metric(
                            'Classificados automaticamente',
                            f"{int(resumo_nibo.get('automaticos', 0)):,}".replace(',', '.')
                        )
                        c_auto_2.metric(
                            'Pendentes de contrapartida',
                            f"{int(resumo_nibo.get('somente_banco', 0)):,}".replace(',', '.')
                        )

                    st.download_button(
                        'Baixar Modelo Domínio',
                        data=arquivo_saida_nibo,
                        file_name=nome_nibo,
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        use_container_width=True,
                        key='dias_pereira_download_modelo_dominio'
                    )
                except Exception as erro_nibo:
                    st.error(f'Não foi possível processar o(s) relatório(s) Nibo: {erro_nibo}')
'''

text = text[:start] + new + text[end:]
path.write_text(text, encoding='utf-8')
