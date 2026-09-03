from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')
old = '''                    # Cada relatório da 242 gera seu próprio Modelo Domínio.
                    # A ordem original das linhas é preservada e as colunas permanecem
                    # exatamente em DATA, DÉBITO, CRÉDITO, VALOR e HISTÓRICO.
                    mime_excel_ef = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    if despesas_ef is not None and not despesas_ef.empty:
                        arquivo_despesa_ef = gerar_modelo_dominio_eletro_forte(
                            despesas_ef, {}, {}
                        )
                        download_despesa_ef.download_button(
                            'Baixar Despesa · Modelo Domínio',
                            data=arquivo_despesa_ef,
                            file_name=f'ELETRO_FORTE_242_DESPESA_{int(ano_ef)}.xlsx',
                            mime=mime_excel_ef,
                            use_container_width=True,
                            key='ef242_download_despesa',
                        )
                    if fornecedores_ef:
                        arquivo_fornecedor_ef = gerar_modelo_dominio_eletro_forte(
                            None, fornecedores_ef, {}
                        )
                        download_fornecedor_ef.download_button(
                            'Baixar Fornecedor · Modelo Domínio',
                            data=arquivo_fornecedor_ef,
                            file_name=f'ELETRO_FORTE_242_FORNECEDOR_{int(ano_ef)}.xlsx',
                            mime=mime_excel_ef,
                            use_container_width=True,
                            key='ef242_download_fornecedor',
                        )
                    if recebidos_ef:
                        arquivo_recebido_ef = gerar_modelo_dominio_eletro_forte(
                            None, {}, recebidos_ef
                        )
                        download_recebido_ef.download_button(
                            'Baixar Recebido · Modelo Domínio',
                            data=arquivo_recebido_ef,
                            file_name=f'ELETRO_FORTE_242_RECEBIDO_{int(ano_ef)}.xlsx',
                            mime=mime_excel_ef,
                            use_container_width=True,
                            key='ef242_download_recebido',
                        )
'''
new = '''                    # Cada relatório da 242 gera seu próprio arquivo final.
                    # A primeira aba preserva o relatório original e as abas seguintes
                    # são cópias do Modelo Domínio real existente no Razync.
                    mime_excel_ef = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    modelo_bytes_ef = None
                    for caminho_modelo_ef in [
                        'Modelo dominio.xlsx', 'Modelo dominio(6).xlsx',
                        'Modelo Dominio.xlsx', 'modelo_dominio.xlsx'
                    ]:
                        if os.path.exists(caminho_modelo_ef):
                            with open(caminho_modelo_ef, 'rb') as arq_modelo_ef:
                                modelo_bytes_ef = arq_modelo_ef.read()
                            break
                    if not modelo_bytes_ef:
                        raise FileNotFoundError('Modelo Domínio não encontrado no sistema.')

                    if despesas_ef is not None and not despesas_ef.empty:
                        arquivo_despesa_ef = gerar_modelo_dominio_eletro_forte(
                            arq_despesa_ef.getvalue(), arq_despesa_ef.name,
                            modelo_bytes_ef, despesas_ef, {}, {}
                        )
                        download_despesa_ef.download_button(
                            'Baixar Despesa · Modelo Domínio',
                            data=arquivo_despesa_ef,
                            file_name=f'ELETRO_FORTE_242_DESPESA_{int(ano_ef)}.xlsx',
                            mime=mime_excel_ef,
                            use_container_width=True,
                            key='ef242_download_despesa',
                        )
                    if fornecedores_ef:
                        arquivo_fornecedor_ef = gerar_modelo_dominio_eletro_forte(
                            arq_fornecedor_ef.getvalue(), arq_fornecedor_ef.name,
                            modelo_bytes_ef, None, fornecedores_ef, {}
                        )
                        download_fornecedor_ef.download_button(
                            'Baixar Fornecedor · Modelo Domínio',
                            data=arquivo_fornecedor_ef,
                            file_name=f'ELETRO_FORTE_242_FORNECEDOR_{int(ano_ef)}.xlsx',
                            mime=mime_excel_ef,
                            use_container_width=True,
                            key='ef242_download_fornecedor',
                        )
                    if recebidos_ef:
                        arquivo_recebido_ef = gerar_modelo_dominio_eletro_forte(
                            arq_recebido_ef.getvalue(), arq_recebido_ef.name,
                            modelo_bytes_ef, None, {}, recebidos_ef
                        )
                        download_recebido_ef.download_button(
                            'Baixar Recebido · Modelo Domínio',
                            data=arquivo_recebido_ef,
                            file_name=f'ELETRO_FORTE_242_RECEBIDO_{int(ano_ef)}.xlsx',
                            mime=mime_excel_ef,
                            use_container_width=True,
                            key='ef242_download_recebido',
                        )
'''
if old not in text:
    raise SystemExit('Bloco antigo da 242 não encontrado')
text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
