from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

import_anchor = 'from razync.bradesco_radani import processar_extrato_bradesco_radani\n'
import_new = '''from razync.eletro_forte import (\n    CONTAS_ELETRO_FORTE, gerar_modelo_dominio_eletro_forte, inferir_ano_recebidos,\n    processar_despesas, processar_fornecedores, processar_recebidos,\n)\n'''
if import_new not in s:
    s = s.replace(import_anchor, import_anchor + import_new)

anchor = "    if st.session_state['empresa_organizador'] == 'lcarlos':\n"
block = r'''    if st.session_state['empresa_organizador'] == 'eletro_forte':
        empresa_ef = '242 - ELETRO FORTE COMERCIAL ELETRICA LTDA'
        aba_operacoes_ef, aba_base_ef = st.tabs(['Organizar arquivos', 'Base Inteligente'])

        with aba_base_ef:
            renderizar_base_inteligente_empresa(
                'eletro_forte', empresa_ef, {'bb', 'itau_508', 'itau_509'},
                {'bb': '8', 'itau_508': '508', 'itau_509': '509'},
            )

        with aba_operacoes_ef:
            st.markdown('#### Relatórios bancários → Modelo Domínio')
            st.caption(
                'Envie Despesa, Fornecedor e/ou Recebido. O processamento é automático. '
                'BB = conta 8 · Itaú 105318 = 508 · Itaú 181537 = 509.'
            )
            col_ef1, col_ef2, col_ef3 = st.columns(3)
            with col_ef1:
                arq_despesa_ef = st.file_uploader(
                    'Planilha Despesa', type=['xls', 'xlsx'], key='ef242_despesa'
                )
            with col_ef2:
                arq_fornecedor_ef = st.file_uploader(
                    'Planilha Fornecedor', type=['xls', 'xlsx'], key='ef242_fornecedor'
                )
            with col_ef3:
                arq_recebido_ef = st.file_uploader(
                    'Planilha Recebido', type=['xls', 'xlsx'], key='ef242_recebido'
                )

            ano_inferido_ef = (
                inferir_ano_recebidos(arq_recebido_ef.getvalue())
                if arq_recebido_ef is not None else None
            )
            ano_ef = st.number_input(
                'Ano de referência', min_value=2020, max_value=2100,
                value=int(ano_inferido_ef or datetime.now().year), step=1,
                key='ef242_ano',
                help='Despesa e Fornecedor trazem apenas dia/mês; o ano é aplicado a esses relatórios.'
            )

            if any([arq_despesa_ef, arq_fornecedor_ef, arq_recebido_ef]):
                try:
                    despesas_ef = processar_despesas(
                        arq_despesa_ef.getvalue(), int(ano_ef)
                    ) if arq_despesa_ef is not None else None
                    fornecedores_ef = processar_fornecedores(
                        arq_fornecedor_ef.getvalue(), int(ano_ef)
                    ) if arq_fornecedor_ef is not None else {}
                    recebidos_ef = processar_recebidos(
                        arq_recebido_ef.getvalue(), int(ano_ef)
                    ) if arq_recebido_ef is not None else {}

                    st.markdown('#### Pré-visualização dos lançamentos')
                    tabs_nomes_ef = []
                    tabs_dfs_ef = []
                    if despesas_ef is not None and not despesas_ef.empty:
                        tabs_nomes_ef.append('Despesas')
                        tabs_dfs_ef.append(despesas_ef)
                    for conta, df_ef in fornecedores_ef.items():
                        tabs_nomes_ef.append('Fornecedor · ' + CONTAS_ELETRO_FORTE.get(conta, conta))
                        tabs_dfs_ef.append(df_ef)
                    for conta, df_ef in recebidos_ef.items():
                        tabs_nomes_ef.append('Recebido · ' + CONTAS_ELETRO_FORTE.get(conta, conta))
                        tabs_dfs_ef.append(df_ef)

                    abas_ef = st.tabs(tabs_nomes_ef)
                    for aba_ef, nome_ef, df_ef in zip(abas_ef, tabs_nomes_ef, tabs_dfs_ef):
                        with aba_ef:
                            c1, c2 = st.columns(2)
                            c1.metric('Lançamentos', len(df_ef))
                            c2.metric('Total', formatar_moeda(float(df_ef['VALOR'].sum())))
                            previa_ef = df_ef.copy()
                            previa_ef['DATA'] = pd.to_datetime(previa_ef['DATA']).dt.strftime('%d/%m/%Y')
                            st.dataframe(
                                previa_ef, use_container_width=True, hide_index=True, height=330,
                                column_config={
                                    'VALOR': st.column_config.NumberColumn('Valor', format='R$ %.2f'),
                                },
                            )
                            if 'Revisar · Conta 0' in nome_ef:
                                st.warning('Conta 0 separada para revisão manual, conforme a regra da empresa.')

                    arquivo_ef = gerar_modelo_dominio_eletro_forte(
                        despesas_ef, fornecedores_ef, recebidos_ef
                    )
                    st.download_button(
                        'Baixar Modelo Domínio — Eletro Forte', data=arquivo_ef,
                        file_name=f'ELETRO_FORTE_242_{int(ano_ef)}.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        use_container_width=True, key='ef242_download',
                    )
                except Exception as erro_ef:
                    st.error(f'Não foi possível processar os relatórios da empresa 242: {erro_ef}')

'''
if "empresa_organizador'] == 'eletro_forte'" not in s:
    s = s.replace(anchor, block + anchor)

p.write_text(s, encoding='utf-8')
