from pathlib import Path

# 1) Configuração da empresa
p = Path('razync/companies.py')
s = p.read_text(encoding='utf-8')
if 'CONFIGURACOES_UP_PACK' not in s:
    s += '''\n\nCONFIGURACOES_UP_PACK = {\n    "up_pack": {\n        "empresa": "1096 - UP PACK BRAZIL EIRELI EPP",\n        "slug": "up_pack",\n        "arquivo": "UP_PACK_Brazil",\n        "contas_bancarias": {"santander": "513", "sicredi": "510"},\n    }\n}\n'''
    p.write_text(s, encoding='utf-8')

# 2) Ativa a empresa no catálogo
p = Path('razync/company_catalog.py')
s = p.read_text(encoding='utf-8')
old = '{"codigo": 1096, "nome": "UP PACK BRAZIL EIRELI EPP", "regime": "LUCRO PRESUMIDO"},'
new = '{"codigo": 1096, "nome": "UP PACK BRAZIL EIRELI EPP", "regime": "LUCRO PRESUMIDO", "chave_sistema": "up_pack"},'
if old in s:
    s = s.replace(old, new, 1)
elif '"codigo": 1096' in s and '"chave_sistema": "up_pack"' not in s:
    raise SystemExit('Linha da empresa 1096 encontrada em formato inesperado')
p.write_text(s, encoding='utf-8')

# 3) Integração no app
p = Path('app.py')
s = p.read_text(encoding='utf-8')
old_import = 'from razync.companies import CONFIGURACOES_AUTOKRAFT, CONFIGURACOES_ACCEDE\n'
new_import = 'from razync.companies import CONFIGURACOES_AUTOKRAFT, CONFIGURACOES_ACCEDE, CONFIGURACOES_UP_PACK\n'
if old_import in s:
    s = s.replace(old_import, new_import, 1)
if 'from razync.up_pack import identificar_banco_up_pack, processar_planilha_up_pack\n' not in s:
    anchor = 'from razync.lcarlos import processar_planilhas_lcarlos\n'
    s = s.replace(anchor, anchor + 'from razync.up_pack import identificar_banco_up_pack, processar_planilha_up_pack\n', 1)

marker = "    if st.session_state['empresa_organizador'] == 'nova_geracao':\n"
if "empresa_organizador'] == 'up_pack'" not in s:
    if marker not in s:
        raise SystemExit('Ponto de inserção antes da Nova Geração não encontrado')
    bloco = '''    if st.session_state['empresa_organizador'] == 'up_pack':\n        config_up_pack = CONFIGURACOES_UP_PACK['up_pack']\n        empresa_up_pack = config_up_pack['empresa']\n        slug_up_pack = config_up_pack['slug']\n\n        aba_operacoes_up, aba_base_up = st.tabs([\n            'Organizar arquivos',\n            'Base Inteligente'\n        ])\n\n        with aba_base_up:\n            renderizar_base_inteligente_empresa(\n                slug_up_pack,\n                empresa_up_pack,\n                {'santander', 'sicredi'},\n                config_up_pack['contas_bancarias']\n            )\n\n        with aba_operacoes_up:\n            st.caption(\n                'Envie as planilhas SIG da UP PACK. O Razync identifica Santander e Sicredi '\n                'pelo nome do arquivo e desmembra automaticamente os grupos de pagamento.'\n            )\n            arquivos_up_pack = st.file_uploader(\n                'Planilhas SIG — Santander e/ou Sicredi',\n                type=['xlsx', 'xls'],\n                accept_multiple_files=True,\n                key='up_pack_sig_bancos'\n            )\n\n            dados_up_pack = {}\n            avisos_up_pack = []\n            try:\n                for arquivo_up in arquivos_up_pack or []:\n                    banco_up = identificar_banco_up_pack(\n                        arquivo_up.getvalue(), arquivo_up.name\n                    )\n                    if banco_up is None:\n                        avisos_up_pack.append(\n                            f'Não foi possível identificar o banco de {arquivo_up.name}. '\n                            'Mantenha Santander ou Sicredi no nome do arquivo.'\n                        )\n                        continue\n                    nome_banco_up = 'Santander' if banco_up == 'santander' else 'Sicredi'\n                    dados_up_pack[nome_banco_up] = {\n                        'principal': executar_com_loading(\n                            f'Organizando a planilha SIG do {nome_banco_up}...',\n                            processar_planilha_up_pack,\n                            arquivo_up.getvalue(),\n                            banco_up\n                        ),\n                        'retirados': pd.DataFrame()\n                    }\n\n                for aviso_up in avisos_up_pack:\n                    st.warning(aviso_up)\n\n                if dados_up_pack:\n                    df_up_pack = pd.concat(\n                        [dados['principal'] for dados in dados_up_pack.values()],\n                        ignore_index=True\n                    ).sort_values(['DATA', 'DESCRIÇÃO'], kind='stable').reset_index(drop=True)\n\n                    if df_up_pack.empty:\n                        st.warning('Nenhum lançamento bancário foi encontrado nas planilhas enviadas.')\n                    else:\n                        datas_up_pack = pd.to_datetime(\n                            df_up_pack['DATA'], errors='coerce'\n                        ).dropna().dt.date\n                        data_min_up = min(datas_up_pack)\n                        data_max_up = max(datas_up_pack)\n\n                        met_up1, met_up2, met_up3 = st.columns(3)\n                        met_up1.metric('Lançamentos', len(df_up_pack))\n                        met_up2.metric(\n                            'Entradas',\n                            formatar_moeda(df_up_pack.loc[df_up_pack['VALOR'] > 0, 'VALOR'].sum())\n                        )\n                        met_up3.metric(\n                            'Saídas',\n                            formatar_moeda(abs(df_up_pack.loc[df_up_pack['VALOR'] < 0, 'VALOR'].sum()))\n                        )\n                        st.caption(\n                            f'Período identificado: {data_min_up.strftime("%d/%m/%Y")} a '\n                            f'{data_max_up.strftime("%d/%m/%Y")} · '\n                            'Santander conta 513 · Sicredi conta 510.'\n                        )\n\n                        modelo_bytes_up = None\n                        for caminho_modelo in ['Modelo dominio.xlsx', 'Modelo dominio(6).xlsx']:\n                            if os.path.exists(caminho_modelo):\n                                with open(caminho_modelo, 'rb') as modelo_arquivo:\n                                    modelo_bytes_up = modelo_arquivo.read()\n                                break\n                        arquivo_final_up = gerar_excel_nova_geracao(\n                            dados_up_pack, modelo_bytes_up\n                        )\n                        st.download_button(\n                            'Baixar planilha no Modelo Domínio',\n                            data=arquivo_final_up,\n                            file_name=(\n                                f"{config_up_pack['arquivo']}_"\n                                f"{data_min_up.strftime('%d%m%Y')}_a_"\n                                f"{data_max_up.strftime('%d%m%Y')}.xlsx"\n                            ),\n                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',\n                            use_container_width=True,\n                            key='up_pack_download_modelo'\n                        )\n            except Exception as erro_up_pack:\n                st.error(f'Não foi possível processar as planilhas da UP PACK: {erro_up_pack}')\n\n            st.markdown(f'#### Conferência — {empresa_up_pack}')\n            renderizar_conferencia_autokraft(\n                slug_up_pack,\n                bancos_config=[\n                    {'nome': 'Santander', 'slug': 'santander'},\n                    {'nome': 'Sicredi', 'slug': 'sicredi'}\n                ]\n            )\n\n'''
    s = s.replace(marker, bloco + marker, 1)

p.write_text(s, encoding='utf-8')
# trigger 2
