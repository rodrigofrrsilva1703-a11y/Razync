from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

anchor_ak = '''                        else:\n                            arquivo_final_autokraft = gerar_excel_nova_geracao(\n                                dados_filtrados_autokraft\n                            )\n'''
repl_ak = '''                        else:\n                            renderizar_previa_bancos_padrao(\n                                dados_filtrados_autokraft,\n                                ordem=['Itaú', 'Daycoval'],\n                            )\n                            arquivo_final_autokraft = gerar_excel_nova_geracao(\n                                dados_filtrados_autokraft\n                            )\n'''
if "renderizar_previa_bancos_padrao(\n                                dados_filtrados_autokraft" not in text:
    if anchor_ak not in text:
        raise SystemExit('Âncora Autokraft não encontrada')
    text = text.replace(anchor_ak, repl_ak, 1)

anchor_ng = '''                    arquivo_final = executar_com_loading(\n                        "Gerando a planilha final...",\n                        gerar_excel_nova_geracao,\n                        dados_exportacao_por_banco,\n                        modelo_org_bytes\n                    )\n'''
repl_ng = '''                    renderizar_previa_bancos_padrao(\n                        dados_exportacao_por_banco,\n                        ordem=[config['nome'] for config in configs_selecionadas],\n                    )\n                    arquivo_final = executar_com_loading(\n                        "Gerando a planilha final...",\n                        gerar_excel_nova_geracao,\n                        dados_exportacao_por_banco,\n                        modelo_org_bytes\n                    )\n'''
if "renderizar_previa_bancos_padrao(\n                        dados_exportacao_por_banco" not in text:
    if anchor_ng not in text:
        raise SystemExit('Âncora Nova Geração não encontrada')
    text = text.replace(anchor_ng, repl_ng, 1)

path.write_text(text, encoding='utf-8')
print('Pré-visualizações de Autokraft e Nova Geração completadas.')
