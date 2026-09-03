from pathlib import Path

# catálogo
p=Path('razync/company_catalog.py'); s=p.read_text(encoding='utf-8')
old='''{"codigo": 969, "nome": "ENGEKRAFT AUTOMAÇÃO LTDA - EPP", "regime": "LUCRO PRESUMIDO"}'''
new='''{"codigo": 969, "nome": "ENGEKRAFT AUTOMAÇÃO LTDA - EPP", "regime": "LUCRO PRESUMIDO", "chave_sistema": "engekraft_969"}'''
if old not in s: raise SystemExit('catálogo 969 não encontrado')
s=s.replace(old,new,1); p.write_text(s,encoding='utf-8')

# app imports
p=Path('app.py'); s=p.read_text(encoding='utf-8')
anchor='''from razync.gz_1211 import (\n    CONTA_ITAU_GZ, gerar_modelo_dominio_gz, processar_gz,\n)\n'''
insert=anchor+'''from razync.engekraft_969 import (\n    CONTA_ITAU_969, gerar_modelo_dominio_engekraft_969, processar_extrato_engekraft_969,\n)\n'''
if anchor not in s: raise SystemExit('âncora import não encontrada')
s=s.replace(anchor,insert,1)

# inserir workspace antes da GZ
anchor2="    if st.session_state['empresa_organizador'] == 'gz_1211':\n"
workspace='''    if st.session_state['empresa_organizador'] == 'engekraft_969':\n        empresa_969 = '969 - ENGEKRAFT AUTOMAÇÃO LTDA - EPP'\n        aba_operacoes_969, aba_base_969 = st.tabs([\n            'Organizar arquivos', 'Base Inteligente'\n        ])\n\n        with aba_operacoes_969:\n            st.markdown('#### Extrato Itaú → Modelo Domínio')\n            st.caption(\n                'Itaú = conta 508. Valores negativos recebem Pago: e valores positivos '
                'recebem Recebido: no histórico. O processamento é automático.'\n            )\n            extrato_969 = st.file_uploader(\n                'Extrato Itaú', type=['pdf'], key='engekraft969_extrato'\n            )\n            if extrato_969 is not None:\n                try:\n                    df_969 = executar_com_loading(\n                        'Lendo extrato Itaú e montando o Modelo Domínio...',\n                        processar_extrato_engekraft_969, extrato_969.getvalue()\n                    )\n                    renderizar_previa_bancos_padrao(\n                        {'Itaú · Conta 508': df_969},\n                        titulo='Pré-visualização do Modelo Domínio',\n                    )\n                    modelo_bytes_969 = None\n                    for caminho_modelo_969 in [\n                        'Modelo dominio.xlsx', 'Modelo dominio(6).xlsx',\n                        'Modelo Dominio.xlsx', 'modelo_dominio.xlsx'\n                    ]:\n                        if os.path.exists(caminho_modelo_969):\n                            with open(caminho_modelo_969, 'rb') as modelo_969:\n                                modelo_bytes_969 = modelo_969.read()\n                            break\n                    if not modelo_bytes_969:\n                        raise FileNotFoundError('Modelo Domínio não encontrado no sistema.')\n                    excel_969 = gerar_modelo_dominio_engekraft_969(df_969, modelo_bytes_969)\n                    datas_969 = pd.to_datetime(df_969['DATA'], errors='coerce').dropna()\n                    periodo_969 = datas_969.min().strftime('%m_%Y') if not datas_969.empty else 'periodo'\n                    st.download_button(\n                        'Baixar Engekraft · Modelo Domínio', data=excel_969,\n                        file_name=f'ENGEKRAFT_969_ITAU_{periodo_969}.xlsx',\n                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',\n                        use_container_width=True, key='engekraft969_download_modelo'\n                    )\n                except Exception as erro_969:\n                    st.error(f'Não foi possível processar a empresa 969 - Engekraft: {erro_969}')\n\n            st.markdown(f'#### Conferência — {empresa_969}')\n            renderizar_conferencia_autokraft(\n                'engekraft969', bancos_config=[{'nome': 'Itaú', 'slug': 'itau'}]\n            )\n\n        with aba_base_969:\n            renderizar_base_inteligente_empresa(\n                'engekraft_969', empresa_969, {'itau'}, {'itau': CONTA_ITAU_969}\n            )\n\n'''
if anchor2 not in s: raise SystemExit('âncora workspace não encontrada')
s=s.replace(anchor2,workspace+anchor2,1); p.write_text(s,encoding='utf-8')

assert '"chave_sistema": "engekraft_969"' in Path('razync/company_catalog.py').read_text(encoding='utf-8')
t=Path('app.py').read_text(encoding='utf-8')
assert "empresa_organizador'] == 'engekraft_969'" in t
assert "renderizar_conferencia_autokraft(\n                'engekraft969'" in t
print('969 integrada')
