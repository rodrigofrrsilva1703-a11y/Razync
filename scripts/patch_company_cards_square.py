from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

inicio = s.find('                st.markdown("##### Conferência por natureza")')
fim = s.find('    except Exception as erro:\n        st.error(f"Não foi possível realizar a conferência: {erro}")', inicio)

if inicio < 0 or fim < 0:
    raise SystemExit('Bloco visual da conferência não encontrado.')

novo = '''                st.markdown("##### Conferência diária")
                resumo1, resumo2 = st.columns(2)
                resumo1.metric("Dias batendo", dias_batendo)
                resumo2.metric("Dias divergentes", dias_divergentes)

                exibicao = diario.copy()
                exibicao['DATA'] = exibicao['DATA'].dt.strftime('%d/%m/%Y')
                exibicao = exibicao[[
                    'DATA',
                    'ENTRADAS PLANILHA', 'ENTRADAS EXTRATO',
                    'SAÍDAS PLANILHA', 'SAÍDAS EXTRATO',
                    'STATUS'
                ]]
                exibicao.columns = [
                    'Data',
                    'Entrada Planilha', 'Entrada Extrato',
                    'Saída Planilha', 'Saída Extrato',
                    'Status'
                ]
                exibicao = formatar_dataframe_moeda_br(
                    exibicao,
                    ['Entrada Planilha', 'Entrada Extrato',
                     'Saída Planilha', 'Saída Extrato']
                )
                st.dataframe(exibicao, use_container_width=True, height=390)

                if dias_divergentes == 0:
                    st.success("✅ Entradas e saídas estão batendo em todos os dias.")
                else:
                    st.warning("❌ Existem dias com divergência entre a planilha e o extrato.")
'''

s = s[:inicio] + novo + s[fim:]

for check in [
    "'Entrada Planilha', 'Entrada Extrato'",
    "'Saída Planilha', 'Saída Extrato'",
    "'Status'",
]:
    if check not in s:
        raise SystemExit(f'Validação falhou: {check}')

if 'Conferência por natureza' in s[inicio:fim]:
    raise SystemExit('Bloco antigo ainda permaneceu.')
if 'Ver valores detalhados por dia' in s[inicio:fim]:
    raise SystemExit('Expander antigo ainda permaneceu.')

p.write_text(s, encoding='utf-8')
print('Conferência bancária simplificada para Planilha x Extrato com status final.')
