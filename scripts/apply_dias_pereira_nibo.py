from pathlib import Path

catalogo = Path('razync/company_catalog.py')
texto = catalogo.read_text(encoding='utf-8')
antigo = '{"codigo": 1529, "nome": "DIAS E PEREIRA SOCIEDADE DE ADVOGADOS", "regime": "LUCRO PRESUMIDO"},'
novo = '{"codigo": 1529, "nome": "DIAS E PEREIRA SOCIEDADE DE ADVOGADOS", "regime": "LUCRO PRESUMIDO", "chave_sistema": "dias_pereira"},'
if antigo not in texto and novo not in texto:
    raise SystemExit('Linha da empresa 1529 não encontrada no catálogo')
texto = texto.replace(antigo, novo)
catalogo.write_text(texto, encoding='utf-8')

app = Path('app.py')
texto = app.read_text(encoding='utf-8')

import_base = 'from razync.company_catalog import EMPRESAS_POR_REGIME, EMPRESAS_POR_CHAVE\n'
import_nibo = 'from razync.nibo import processar_extrato_nibo_pdf\n'
if import_nibo not in texto:
    if import_base not in texto:
        raise SystemExit('Import do catálogo não encontrado')
    texto = texto.replace(import_base, import_base + import_nibo, 1)

caption_existente = "        'accede_equipamentos': 'Organize as planilhas SIG e confira Itaú e Sicredi da 1001 - ACCEDE EQUIPAMENTOS.'\n"
caption_nibo = "        'dias_pereira': 'Converta o relatório visual do Nibo da 1529 - Dias e Pereira diretamente para o Modelo Domínio.'\n"
if caption_nibo not in texto:
    if caption_existente not in texto:
        raise SystemExit('Bloco de captions das empresas não encontrado')
    texto = texto.replace(caption_existente, caption_existente.rstrip('\n') + ',\n' + caption_nibo, 1)

marcador = "# --- Ferramenta exclusiva 1529: Nibo -> Modelo Dominio ---"
if marcador not in texto:
    bloco = r'''

    # --- Ferramenta exclusiva 1529: Nibo -> Modelo Dominio ---
    if st.session_state['empresa_organizador'] == 'dias_pereira':
        st.markdown('### Nibo → Modelo Domínio')
        st.caption(
            'Envie o PDF de Contas & Extratos exportado pelo Nibo. '
            'O Razync lê a tabela visual, organiza os movimentos e preenche o Modelo Domínio.'
        )

        arquivo_nibo = st.file_uploader(
            'Extrato Nibo em PDF',
            type=['pdf'],
            key='dias_pereira_extrato_nibo_pdf',
            help='Use o relatório mensal de Contas & Extratos do Nibo.'
        )

        if arquivo_nibo is not None:
            try:
                with st.spinner('Lendo e organizando o relatório Nibo...'):
                    df_nibo = processar_extrato_nibo_pdf(arquivo_nibo.getvalue())

                df_export_nibo = df_nibo[
                    ['DESCRIÇÃO', 'DATA', 'VALOR', 'DÉBITO', 'CRÉDITO', 'HISTÓRICO']
                ].copy()
                datas_nibo = pd.to_datetime(df_export_nibo['DATA'], dayfirst=True, errors='coerce')
                entradas_nibo = df_export_nibo.loc[df_export_nibo['VALOR'] > 0, 'VALOR'].sum()
                saidas_nibo = abs(df_export_nibo.loc[df_export_nibo['VALOR'] < 0, 'VALOR'].sum())

                col_nibo_1, col_nibo_2, col_nibo_3 = st.columns(3)
                col_nibo_1.metric('Lançamentos', f'{len(df_export_nibo):,}'.replace(',', '.'))
                col_nibo_2.metric('Entradas', f'R$ {entradas_nibo:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'))
                col_nibo_3.metric('Saídas', f'R$ {saidas_nibo:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'))

                st.success('Relatório Nibo organizado com sucesso.')
                st.dataframe(
                    df_export_nibo[['DATA', 'VALOR', 'HISTÓRICO']],
                    use_container_width=True,
                    hide_index=True
                )

                excel_nibo = gerar_excel_modelo_dominio(df_export_nibo)
                datas_validas = datas_nibo.dropna()
                if not datas_validas.empty:
                    nome_nibo = f"1529_Dias_Pereira_Nibo_{datas_validas.min().strftime('%m_%Y')}.xlsx"
                else:
                    nome_nibo = '1529_Dias_Pereira_Nibo_Modelo_Dominio.xlsx'

                st.download_button(
                    'Baixar Modelo Domínio',
                    data=excel_nibo,
                    file_name=nome_nibo,
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    use_container_width=True,
                    key='dias_pereira_download_modelo_dominio'
                )
            except Exception as erro_nibo:
                st.error(f'Não foi possível processar o relatório Nibo: {erro_nibo}')
'''
    texto = texto.rstrip() + bloco + '\n'

app.write_text(texto, encoding='utf-8')
