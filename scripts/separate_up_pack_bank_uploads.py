from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
old = '''            arquivos_up_pack = st.file_uploader(
                'Planilhas SIG — Santander e/ou Sicredi',
                type=['xlsx', 'xls'],
                accept_multiple_files=True,
                key='up_pack_sig_bancos'
            )

            dados_up_pack = {}
            avisos_up_pack = []
            try:
                for arquivo_up in arquivos_up_pack or []:
                    banco_up = identificar_banco_up_pack(
                        arquivo_up.getvalue(), arquivo_up.name
                    )
                    if banco_up is None:
                        avisos_up_pack.append(
                            f'Não foi possível identificar o banco de {arquivo_up.name}. '
                            'Mantenha Santander ou Sicredi no nome do arquivo.'
                        )
                        continue
                    nome_banco_up = 'Santander' if banco_up == 'santander' else 'Sicredi'
                    dados_up_pack[nome_banco_up] = {
                        'principal': executar_com_loading(
                            f'Organizando a planilha SIG do {nome_banco_up}...',
                            processar_planilha_up_pack,
                            arquivo_up.getvalue(),
                            banco_up
                        ),
                        'retirados': pd.DataFrame()
                    }
'''
new = '''            bancos_up_selecionados = st.multiselect(
                'Bancos para organizar',
                options=['Santander', 'Sicredi'],
                default=['Santander', 'Sicredi'],
                key='up_pack_bancos_selecionados'
            )

            col_up_santander, col_up_sicredi = st.columns(2)
            with col_up_santander:
                arquivo_up_santander = st.file_uploader(
                    'Planilha SIG — Santander',
                    type=['xlsx', 'xls'],
                    key='up_pack_sig_santander',
                    disabled='Santander' not in bancos_up_selecionados
                )
                st.caption('Conta Domínio: 513')

            with col_up_sicredi:
                arquivo_up_sicredi = st.file_uploader(
                    'Planilha SIG — Sicredi',
                    type=['xlsx', 'xls'],
                    key='up_pack_sig_sicredi',
                    disabled='Sicredi' not in bancos_up_selecionados
                )
                st.caption('Conta Domínio: 510')

            dados_up_pack = {}
            avisos_up_pack = []
            try:
                arquivos_por_banco_up = {
                    'Santander': ('santander', arquivo_up_santander),
                    'Sicredi': ('sicredi', arquivo_up_sicredi),
                }
                for nome_banco_up in bancos_up_selecionados:
                    banco_up, arquivo_up = arquivos_por_banco_up[nome_banco_up]
                    if arquivo_up is None:
                        continue

                    banco_detectado_up = identificar_banco_up_pack(
                        arquivo_up.getvalue(), arquivo_up.name
                    )
                    if banco_detectado_up and banco_detectado_up != banco_up:
                        avisos_up_pack.append(
                            f'O arquivo {arquivo_up.name} parece ser do banco '
                            f'{"Santander" if banco_detectado_up == "santander" else "Sicredi"}, '
                            f'mas foi enviado no campo {nome_banco_up}. Confira antes de continuar.'
                        )

                    dados_up_pack[nome_banco_up] = {
                        'principal': executar_com_loading(
                            f'Organizando a planilha SIG do {nome_banco_up}...',
                            processar_planilha_up_pack,
                            arquivo_up.getvalue(),
                            banco_up
                        ),
                        'retirados': pd.DataFrame()
                    }
'''
if old not in s:
    raise SystemExit('Bloco atual de upload da UP PACK não encontrado')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
# trigger
