from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

old = '''                dias_batendo = int((diario['STATUS'] == '✅ Batendo').sum())
                dias_divergentes = int((diario['STATUS'] == '❌ Divergente').sum())
                te = float(diario['ENTRADAS EXTRATO'].sum())
                tp = float(diario['ENTRADAS PLANILHA'].sum())
                se = float(diario['SAÍDAS EXTRATO'].sum())
                sp = float(diario['SAÍDAS PLANILHA'].sum())

                st.markdown("##### Resumo da conferência")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Entradas — Extrato", formatar_moeda(te))
                c2.metric("Entradas — Planilha", formatar_moeda(tp))
                c3.metric("Saídas — Extrato", formatar_moeda(se))
                c4.metric("Saídas — Planilha", formatar_moeda(sp))
                d1, d2, d3, d4 = st.columns(4)
                d1.metric("Diferença Entradas", formatar_moeda(tp - te))
                d2.metric("Diferença Saídas", formatar_moeda(sp - se))
                d3.metric("Dias batendo", dias_batendo)
                d4.metric("Dias divergentes", dias_divergentes)

                if dias_divergentes == 0:
                    st.success("Entradas e saídas estão batendo em todos os dias.")
                else:
                    st.warning("Há divergências. Confira Entradas e Saídas separadamente.")

                exibicao = diario.copy()
                exibicao['DATA'] = exibicao['DATA'].dt.strftime('%d/%m/%Y')
                exibicao = exibicao[['DATA','ENTRADAS EXTRATO','ENTRADAS PLANILHA','DIF. ENTRADAS','STATUS ENTRADAS','SAÍDAS EXTRATO','SAÍDAS PLANILHA','DIF. SAÍDAS','STATUS SAÍDAS','STATUS']]
                exibicao = formatar_dataframe_moeda_br(exibicao, ['ENTRADAS EXTRATO','ENTRADAS PLANILHA','DIF. ENTRADAS','SAÍDAS EXTRATO','SAÍDAS PLANILHA','DIF. SAÍDAS'])
                st.dataframe(exibicao, use_container_width=True, height=390)
'''

new = '''                dias_batendo = int((diario['STATUS'] == '✅ Batendo').sum())
                dias_divergentes = int((diario['STATUS'] == '❌ Divergente').sum())
                te = float(diario['ENTRADAS EXTRATO'].sum())
                tp = float(diario['ENTRADAS PLANILHA'].sum())
                se = float(diario['SAÍDAS EXTRATO'].sum())
                sp = float(diario['SAÍDAS PLANILHA'].sum())
                dif_ent = round(tp - te, 2)
                dif_sai = round(sp - se, 2)

                st.markdown("##### Conferência por natureza")
                bloco_entradas, bloco_saidas = st.columns(2, gap='large')

                with bloco_entradas:
                    st.markdown("**Entradas**")
                    ent1, ent2, ent3 = st.columns(3)
                    ent1.metric("Extrato", formatar_moeda(te))
                    ent2.metric("Planilha", formatar_moeda(tp))
                    ent3.metric("Diferença", formatar_moeda(dif_ent))
                    if abs(dif_ent) < 0.01:
                        st.success("Entradas batendo")
                    else:
                        st.error("Entradas divergentes")

                with bloco_saidas:
                    st.markdown("**Saídas**")
                    sai1, sai2, sai3 = st.columns(3)
                    sai1.metric("Extrato", formatar_moeda(se))
                    sai2.metric("Planilha", formatar_moeda(sp))
                    sai3.metric("Diferença", formatar_moeda(dif_sai))
                    if abs(dif_sai) < 0.01:
                        st.success("Saídas batendo")
                    else:
                        st.error("Saídas divergentes")

                st.markdown("##### Conferência diária")
                resumo1, resumo2 = st.columns(2)
                resumo1.metric("Dias batendo", dias_batendo)
                resumo2.metric("Dias divergentes", dias_divergentes)

                exibicao = diario.copy()
                exibicao['DATA'] = exibicao['DATA'].dt.strftime('%d/%m/%Y')
                exibicao = exibicao[[
                    'DATA',
                    'DIF. ENTRADAS', 'STATUS ENTRADAS',
                    'DIF. SAÍDAS', 'STATUS SAÍDAS',
                    'STATUS'
                ]]
                exibicao.columns = [
                    'Data',
                    'Dif. Entradas', 'Entradas',
                    'Dif. Saídas', 'Saídas',
                    'Status do dia'
                ]
                exibicao = formatar_dataframe_moeda_br(
                    exibicao, ['Dif. Entradas', 'Dif. Saídas']
                )
                st.dataframe(exibicao, use_container_width=True, height=340)

                with st.expander("Ver valores detalhados por dia", expanded=False):
                    detalhes = diario.copy()
                    detalhes['DATA'] = detalhes['DATA'].dt.strftime('%d/%m/%Y')
                    detalhes = detalhes[[
                        'DATA',
                        'ENTRADAS EXTRATO', 'ENTRADAS PLANILHA', 'DIF. ENTRADAS',
                        'SAÍDAS EXTRATO', 'SAÍDAS PLANILHA', 'DIF. SAÍDAS'
                    ]]
                    detalhes.columns = [
                        'Data',
                        'Entradas Extrato', 'Entradas Planilha', 'Dif. Entradas',
                        'Saídas Extrato', 'Saídas Planilha', 'Dif. Saídas'
                    ]
                    detalhes = formatar_dataframe_moeda_br(
                        detalhes,
                        ['Entradas Extrato', 'Entradas Planilha', 'Dif. Entradas',
                         'Saídas Extrato', 'Saídas Planilha', 'Dif. Saídas']
                    )
                    st.dataframe(detalhes, use_container_width=True, height=320)
'''

if s.count(old) != 1:
    raise SystemExit(f'Bloco visual atual encontrado {s.count(old)} vezes.')
s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('Relatório da conferência simplificado e reorganizado.')
