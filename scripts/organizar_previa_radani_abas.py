from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')
old = """                previa_bancos_radani = resultado_radani.get('previa_bancos', {})
                if previa_bancos_radani:
                    st.markdown('#### Pré-visualização por banco')
                    for nome_banco_previa in ['Itaú', 'Bradesco']:
                        previa_banco = previa_bancos_radani.get(nome_banco_previa)
                        if not previa_banco:
                            continue
                        st.markdown(f'##### {nome_banco_previa}')
                        card_ent, card_sai, card_saldo = st.columns(3)
                        card_ent.metric(
                            'Entradas',
                            formatar_moeda(previa_banco['entradas'])
                        )
                        card_sai.metric(
                            'Saídas',
                            formatar_moeda(previa_banco['saidas'])
                        )
                        card_saldo.metric(
                            'Saldo',
                            formatar_moeda(previa_banco['saldo'])
                        )

                        df_previa_banco = previa_banco['lancamentos'].copy()
                        df_previa_banco['DATA'] = pd.to_datetime(
                            df_previa_banco['DATA'], errors='coerce'
                        ).dt.strftime('%d/%m/%Y')
                        st.dataframe(
                            df_previa_banco,
                            use_container_width=True,
                            hide_index=True,
                            height=min(360, 38 + max(1, min(len(df_previa_banco), 8)) * 35),
                            column_config={
                                'DATA': st.column_config.TextColumn('Data', width='small'),
                                'HISTÓRICO': st.column_config.TextColumn('Histórico', width='large'),
                                'VALOR': st.column_config.NumberColumn(
                                    'Valor', format='R$ %.2f'
                                ),
                            },
                        )
"""
new = """                previa_bancos_radani = resultado_radani.get('previa_bancos', {})
                if previa_bancos_radani:
                    st.markdown('#### Pré-visualização dos lançamentos')
                    nomes_bancos_previa = [
                        nome for nome in ['Itaú', 'Bradesco']
                        if previa_bancos_radani.get(nome)
                    ]
                    abas_bancos_previa = st.tabs(nomes_bancos_previa)
                    for aba_banco_previa, nome_banco_previa in zip(
                        abas_bancos_previa, nomes_bancos_previa
                    ):
                        with aba_banco_previa:
                            previa_banco = previa_bancos_radani[nome_banco_previa]
                            card_ent, card_sai, card_saldo = st.columns(3)
                            card_ent.metric(
                                'Entradas',
                                formatar_moeda(previa_banco['entradas'])
                            )
                            card_sai.metric(
                                'Saídas',
                                formatar_moeda(previa_banco['saidas'])
                            )
                            card_saldo.metric(
                                'Saldo',
                                formatar_moeda(previa_banco['saldo'])
                            )

                            df_previa_banco = previa_banco['lancamentos'].copy()
                            df_previa_banco['DATA'] = pd.to_datetime(
                                df_previa_banco['DATA'], errors='coerce'
                            ).dt.strftime('%d/%m/%Y')
                            st.dataframe(
                                df_previa_banco,
                                use_container_width=True,
                                hide_index=True,
                                height=min(360, 38 + max(1, min(len(df_previa_banco), 8)) * 35),
                                column_config={
                                    'DATA': st.column_config.TextColumn('Data', width='small'),
                                    'HISTÓRICO': st.column_config.TextColumn('Histórico', width='large'),
                                    'VALOR': st.column_config.NumberColumn(
                                        'Valor', format='R$ %.2f'
                                    ),
                                },
                            )
"""
if old not in text:
    raise SystemExit('Bloco de prévia da Radani não encontrado')
text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
