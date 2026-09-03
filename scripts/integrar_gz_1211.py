from pathlib import Path
import re

# 1) Ativa a empresa 1211 já existente no catálogo, sem duplicá-la.
p = Path('razync/company_catalog.py')
s = p.read_text(encoding='utf-8')
old = '{"codigo": 1211, "nome": "GZ IMPORTADORA E EXPORTADORA LTDA EPP (ANTIGA BODY-UP)", "regime": "LUCRO PRESUMIDO"}'
new = '{"codigo": 1211, "nome": "GZ IMPORTADORA E EXPORTADORA LTDA EPP (ANTIGA BODY-UP)", "regime": "LUCRO PRESUMIDO", "chave_sistema": "gz_1211"}'
if old not in s:
    raise SystemExit('Cadastro 1211 não localizado no catálogo.')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')

# 2) Integra processador e interface.
p = Path('app.py')
s = p.read_text(encoding='utf-8')
import_anchor = '''from razync.eletro_forte import (\n    CONTAS_ELETRO_FORTE, gerar_modelo_dominio_eletro_forte, inferir_ano_recebidos,\n    processar_despesas, processar_fornecedores, processar_recebidos,\n)\n'''
import_new = import_anchor + '''from razync.gz_1211 import (\n    CONTA_ITAU_GZ, gerar_modelo_dominio_gz, processar_gz,\n)\n'''
if 'from razync.gz_1211 import' not in s:
    if import_anchor not in s:
        raise SystemExit('Âncora de imports não localizada.')
    s = s.replace(import_anchor, import_new, 1)

# Descrição da área.
desc_anchor = "        'lcarlos': (\n"
desc_gz = '''        'gz_1211': (\n            'Converta o extrato Itaú da 1211 - GZ, desmembre os boletos recebidos '\n            'e confira os totais antes da classificação.'\n        ),\n'''
if "'gz_1211': (" not in s:
    if desc_anchor not in s:
        raise SystemExit('Âncora de descrição não localizada.')
    s = s.replace(desc_anchor, desc_gz + desc_anchor, 1)

# Bloco operacional inserido antes da empresa 242.
anchor = "    if st.session_state['empresa_organizador'] == 'eletro_forte':\n"
if anchor not in s:
    raise SystemExit('Âncora da empresa 242 não localizada.')

bloco = r'''    if st.session_state['empresa_organizador'] == 'gz_1211':
        empresa_gz = '1211 - GZ IMPORTADORA E EXPORTADORA LTDA EPP'
        aba_operacoes_gz, aba_base_gz, aba_conferencia_gz = st.tabs([
            'Organizar arquivos', 'Base Inteligente', 'Conferência com Extrato'
        ])

        with aba_operacoes_gz:
            st.markdown('#### Extrato Itaú + Boletos liquidados → Modelo Domínio')
            st.caption(
                'Itaú = conta 508. Os lançamentos BOLETOS RECEBIDOS são substituídos '
                'pelos boletos individuais liquidados. O histórico fica como '
                'Recebido: NOME DO PAGADOR.'
            )
            col_extrato_gz, col_boletos_gz = st.columns(2)
            with col_extrato_gz:
                extrato_gz = st.file_uploader(
                    '1º · Extrato Itaú', type=['pdf'], key='gz1211_extrato',
                    help='Extrato principal da conta Itaú 0099343-5 / conta Domínio 508.'
                )
            with col_boletos_gz:
                boletos_gz = st.file_uploader(
                    '2º · Boletos baixados e liquidados', type=['pdf'], key='gz1211_boletos',
                    help='Relatório auxiliar usado para identificar os BOLETOS RECEBIDOS.'
                )

            if extrato_gz is not None and boletos_gz is not None:
                chave_gz = hashlib.sha256(
                    extrato_gz.getvalue() + b'|' + boletos_gz.getvalue()
                ).hexdigest()
                try:
                    resultado_gz = executar_com_loading(
                        'Lendo extrato, identificando boletos e conferindo os totais...',
                        processar_gz,
                        extrato_gz.getvalue(), boletos_gz.getvalue()
                    )
                    df_gz, diag_gz, nao_usados_gz, resumo_gz = resultado_gz
                    st.session_state['_gz1211_resultado'] = {
                        'chave': chave_gz,
                        'df': df_gz,
                        'diag': diag_gz,
                        'nao_usados': nao_usados_gz,
                        'resumo': resumo_gz,
                    }

                    renderizar_previa_bancos_padrao(
                        {'Itaú · Conta 508': df_gz},
                        titulo='Pré-visualização do Modelo Domínio',
                    )

                    m1_gz, m2_gz, m3_gz = st.columns(3)
                    m1_gz.metric('Totais de boletos', int(resumo_gz.get('agregados', 0)))
                    m2_gz.metric('Batendo', int(resumo_gz.get('agregados_batendo', 0)))
                    m3_gz.metric('Divergentes', int(resumo_gz.get('agregados_divergentes', 0)))

                    if int(resumo_gz.get('agregados_divergentes', 0)):
                        st.warning(
                            'Há BOLETOS RECEBIDOS que não fecharam com o relatório auxiliar. '
                            'Nesses casos o lançamento agregado do extrato foi preservado.'
                        )
                    if int(resumo_gz.get('boletos_nao_usados', 0)):
                        st.warning(
                            f"{int(resumo_gz.get('boletos_nao_usados', 0))} boleto(s) liquidado(s) "
                            'do período não foram vinculados a um total do extrato.'
                        )

                    modelo_bytes_gz = None
                    for caminho_modelo_gz in [
                        'Modelo dominio.xlsx', 'Modelo dominio(6).xlsx',
                        'Modelo Dominio.xlsx', 'modelo_dominio.xlsx'
                    ]:
                        if os.path.exists(caminho_modelo_gz):
                            with open(caminho_modelo_gz, 'rb') as modelo_gz:
                                modelo_bytes_gz = modelo_gz.read()
                            break
                    if not modelo_bytes_gz:
                        raise FileNotFoundError('Modelo Domínio não encontrado no sistema.')

                    excel_gz = gerar_modelo_dominio_gz(df_gz, modelo_bytes_gz)
                    periodo_gz = pd.to_datetime(resumo_gz['periodo_inicio']).strftime('%m_%Y')
                    st.download_button(
                        'Baixar GZ · Modelo Domínio',
                        data=excel_gz,
                        file_name=f'GZ_1211_ITAU_{periodo_gz}.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        use_container_width=True,
                        key='gz1211_download_modelo',
                    )
                except Exception as erro_gz:
                    st.error(f'Não foi possível processar a empresa 1211 - GZ: {erro_gz}')
            elif extrato_gz is not None or boletos_gz is not None:
                st.info('Envie os dois PDFs para montar e conferir o arquivo da GZ.')

        with aba_base_gz:
            renderizar_base_inteligente_empresa(
                'gz_1211', empresa_gz, {'itau'}, {'itau': CONTA_ITAU_GZ}
            )

        with aba_conferencia_gz:
            st.markdown('#### Conferência com Extrato')
            st.caption(
                'Confere cada total BOLETOS RECEBIDOS contra os boletos liquidados ainda '
                'não utilizados e também valida o total financeiro do arquivo final.'
            )
            resultado_salvo_gz = st.session_state.get('_gz1211_resultado')
            chave_atual_gz = None
            if extrato_gz is not None and boletos_gz is not None:
                chave_atual_gz = hashlib.sha256(
                    extrato_gz.getvalue() + b'|' + boletos_gz.getvalue()
                ).hexdigest()
            if not resultado_salvo_gz or resultado_salvo_gz.get('chave') != chave_atual_gz:
                st.info('Envie e processe os dois PDFs em Organizar arquivos para visualizar a conferência.')
            else:
                diag_conf_gz = resultado_salvo_gz['diag'].copy()
                nao_usados_conf_gz = resultado_salvo_gz['nao_usados'].copy()
                resumo_conf_gz = resultado_salvo_gz['resumo']
                total_ext_gz = float(resumo_conf_gz.get('total_extrato', 0.0))
                total_mod_gz = float(resumo_conf_gz.get('total_modelo', 0.0))
                dif_total_gz = round(total_mod_gz - total_ext_gz, 2)

                c1_gz, c2_gz, c3_gz = st.columns(3)
                c1_gz.metric('Total líquido extrato', formatar_moeda(total_ext_gz))
                c2_gz.metric('Total líquido Modelo', formatar_moeda(total_mod_gz))
                c3_gz.metric('Diferença', formatar_moeda(dif_total_gz))
                if abs(dif_total_gz) <= 0.02:
                    st.success('O total financeiro do Modelo Domínio está preservado em relação ao extrato.')
                else:
                    st.error('O total financeiro do Modelo Domínio não está fechando com o extrato.')

                if not diag_conf_gz.empty:
                    previa_diag_gz = diag_conf_gz.copy()
                    previa_diag_gz['DATA_EXTRATO'] = pd.to_datetime(
                        previa_diag_gz['DATA_EXTRATO']
                    ).dt.strftime('%d/%m/%Y')
                    st.markdown('##### Conferência dos BOLETOS RECEBIDOS')
                    st.dataframe(
                        previa_diag_gz, use_container_width=True, hide_index=True,
                        column_config={
                            'TOTAL_EXTRATO': st.column_config.NumberColumn(format='R$ %.2f'),
                            'TOTAL_BOLETOS': st.column_config.NumberColumn(format='R$ %.2f'),
                            'DIFERENÇA': st.column_config.NumberColumn(format='R$ %.2f'),
                        },
                    )
                if not nao_usados_conf_gz.empty:
                    st.markdown('##### Boletos liquidados sem vínculo')
                    previa_nao_usados_gz = nao_usados_conf_gz.copy()
                    previa_nao_usados_gz['DATA'] = pd.to_datetime(
                        previa_nao_usados_gz['DATA']
                    ).dt.strftime('%d/%m/%Y')
                    st.dataframe(
                        previa_nao_usados_gz, use_container_width=True, hide_index=True,
                        column_config={'VALOR': st.column_config.NumberColumn(format='R$ %.2f')},
                    )

'''
if "empresa_organizador'] == 'gz_1211'" not in s:
    s = s.replace(anchor, bloco + anchor, 1)

p.write_text(s, encoding='utf-8')
