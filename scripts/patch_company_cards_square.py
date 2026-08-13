from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

old = '''                st.markdown("##### Conferência diária")
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
'''

new = '''                st.markdown("##### Conferência diária")
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
                    ['Entrada Planilha', 'Entrada Extrato', 'Saída Planilha', 'Saída Extrato']
                )
                st.dataframe(exibicao, use_container_width=True, height=340)
'''

if s.count(old) != 1:
    raise SystemExit(f'Bloco da tabela diária encontrado {s.count(old)} vezes.')
s = s.replace(old, new, 1)

checks = [
    "'Entrada Planilha', 'Entrada Extrato'",
    "'Saída Planilha', 'Saída Extrato'",
    "'Status'"
]
for check in checks:
    if check not in s:
        raise SystemExit(f'Validação falhou: {check}')

p.write_text(s, encoding='utf-8')
print('Tabela da conferência ajustada para Planilha x Extrato e status final.')
