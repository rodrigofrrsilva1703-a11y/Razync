from pathlib import Path
import re

p = Path('app.py')
s = p.read_text(encoding='utf-8')

padrao_calc = re.compile(
    r"    total_modelo = df_modelo\.groupby\('DATA'\)\['VALOR'\]\.sum\(\)\.rename\('TOTAL PLANILHA'\).*?"
    r"    diario\['STATUS'\] = diario\['DIFERENÇA DO DIA'\]\.apply\(\n"
    r"        lambda valor: '✅ Batendo' if abs\(valor\) < 0\.01 else '❌ Divergente'\n"
    r"    \)\n",
    re.S,
)
novo_calc = '''    def resumo_diario_por_natureza(df, prefixo):
        temp = df[['DATA', 'VALOR']].copy()
        temp[f'ENTRADAS {prefixo}'] = temp['VALOR'].where(temp['VALOR'] > 0, 0.0)
        temp[f'SAÍDAS {prefixo}'] = -temp['VALOR'].where(temp['VALOR'] < 0, 0.0)
        return temp.groupby('DATA', as_index=False)[[f'ENTRADAS {prefixo}', f'SAÍDAS {prefixo}']].sum()

    ext_dia = resumo_diario_por_natureza(df_extrato_comparavel, 'EXTRATO')
    plan_dia = resumo_diario_por_natureza(df_modelo, 'PLANILHA')
    diario = pd.merge(ext_dia, plan_dia, on='DATA', how='outer').fillna(0.0).sort_values('DATA')
    diario['DIF. ENTRADAS'] = (diario['ENTRADAS PLANILHA'] - diario['ENTRADAS EXTRATO']).round(2)
    diario['DIF. SAÍDAS'] = (diario['SAÍDAS PLANILHA'] - diario['SAÍDAS EXTRATO']).round(2)
    diario['STATUS ENTRADAS'] = diario['DIF. ENTRADAS'].apply(lambda v: '✅ Batendo' if abs(v) < 0.01 else '❌ Divergente')
    diario['STATUS SAÍDAS'] = diario['DIF. SAÍDAS'].apply(lambda v: '✅ Batendo' if abs(v) < 0.01 else '❌ Divergente')
    diario['STATUS'] = diario.apply(lambda r: '✅ Batendo' if abs(r['DIF. ENTRADAS']) < 0.01 and abs(r['DIF. SAÍDAS']) < 0.01 else '❌ Divergente', axis=1)
'''
s, n1 = padrao_calc.subn(novo_calc, s, count=1)
if n1 != 1:
    raise SystemExit('Bloco de cálculo da conferência não encontrado.')

inicio = s.find("                dias_batendo = int((diario['STATUS'] == '✅ Batendo').sum())")
fim = s.find("    except Exception as erro:\n        st.error(f\"Não foi possível realizar a conferência: {erro}\")", inicio)
if inicio < 0 or fim < 0:
    raise SystemExit('Bloco visual da conferência não encontrado.')

novo_visual = '''                dias_batendo = int((diario['STATUS'] == '✅ Batendo').sum())
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
s = s[:inicio] + novo_visual + s[fim:]

p.write_text(s, encoding='utf-8')
print('Conferência com entradas e saídas separadas.')
