from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old_state = """                    st.session_state['radani_resultado_processado'] = {
                        'assinatura': assinatura_radani,
                        'arquivo_final': arquivo_final_radani,
                        'total': int(len(df_radani_total)),
                        'entradas': float(df_radani_total.loc[df_radani_total['VALOR'] > 0, 'VALOR'].sum()),
                        'saidas': float(abs(df_radani_total.loc[df_radani_total['VALOR'] < 0, 'VALOR'].sum())),
                        'inicio': datas_radani.min(),
                        'fim': datas_radani.max(),
                        'detalhes': pd.concat(detalhes_radani, ignore_index=True) if detalhes_radani else pd.DataFrame(),
                        'revisoes': pd.concat(revisoes_radani, ignore_index=True) if revisoes_radani else pd.DataFrame(),
                    }
"""
new_state = """                    previa_bancos_radani = {}
                    for nome_banco_previa, dados_banco_previa in dados_radani.items():
                        df_banco_previa = dados_banco_previa['principal'].copy()
                        df_banco_previa['VALOR'] = pd.to_numeric(
                            df_banco_previa['VALOR'], errors='coerce'
                        ).fillna(0.0)
                        entradas_banco_previa = float(
                            df_banco_previa.loc[df_banco_previa['VALOR'] > 0, 'VALOR'].sum()
                        )
                        saidas_banco_previa = float(abs(
                            df_banco_previa.loc[df_banco_previa['VALOR'] < 0, 'VALOR'].sum()
                        ))
                        previa_bancos_radani[nome_banco_previa] = {
                            'entradas': entradas_banco_previa,
                            'saidas': saidas_banco_previa,
                            'saldo': entradas_banco_previa - saidas_banco_previa,
                            'lancamentos': df_banco_previa[
                                ['DATA', 'HISTÓRICO', 'VALOR']
                            ].copy(),
                        }

                    st.session_state['radani_resultado_processado'] = {
                        'assinatura': assinatura_radani,
                        'arquivo_final': arquivo_final_radani,
                        'total': int(len(df_radani_total)),
                        'entradas': float(df_radani_total.loc[df_radani_total['VALOR'] > 0, 'VALOR'].sum()),
                        'saidas': float(abs(df_radani_total.loc[df_radani_total['VALOR'] < 0, 'VALOR'].sum())),
                        'inicio': datas_radani.min(),
                        'fim': datas_radani.max(),
                        'previa_bancos': previa_bancos_radani,
                        'detalhes': pd.concat(detalhes_radani, ignore_index=True) if detalhes_radani else pd.DataFrame(),
                        'revisoes': pd.concat(revisoes_radani, ignore_index=True) if revisoes_radani else pd.DataFrame(),
                    }
"""
if old_state not in text:
    raise SystemExit('Bloco de session_state da Radani não encontrado')
text = text.replace(old_state, new_state, 1)

marker = """                df_detalhes_radani = resultado_radani['detalhes']
                df_revisoes_radani = resultado_radani['revisoes']
"""
insert = """                previa_bancos_radani = resultado_radani.get('previa_bancos', {})
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

                df_detalhes_radani = resultado_radani['detalhes']
                df_revisoes_radani = resultado_radani['revisoes']
"""
if marker not in text:
    raise SystemExit('Ponto de inserção da prévia não encontrado')
text = text.replace(marker, insert, 1)

path.write_text(text, encoding='utf-8')
