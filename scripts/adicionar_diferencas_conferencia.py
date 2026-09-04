from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

old = '''                exibicao = diario.copy()\n                exibicao['DATA'] = exibicao['DATA'].dt.strftime('%d/%m/%Y')\n                exibicao = exibicao[[\n                    'DATA',\n                    'ENTRADAS PLANILHA', 'ENTRADAS EXTRATO',\n                    'SAÍDAS PLANILHA', 'SAÍDAS EXTRATO',\n                    'STATUS'\n                ]]\n                exibicao.columns = [\n                    'Data',\n                    'Entrada Planilha', 'Entrada Extrato',\n                    'Saída Planilha', 'Saída Extrato',\n                    'Status'\n                ]\n                exibicao = formatar_dataframe_moeda_br(\n                    exibicao,\n                    ['Entrada Planilha', 'Entrada Extrato',\n                     'Saída Planilha', 'Saída Extrato']\n                )\n'''

new = '''                exibicao = diario.copy()\n                exibicao['DIFERENÇA ENTRADAS'] = (\n                    pd.to_numeric(exibicao['ENTRADAS PLANILHA'], errors='coerce').fillna(0.0)\n                    - pd.to_numeric(exibicao['ENTRADAS EXTRATO'], errors='coerce').fillna(0.0)\n                ).round(2)\n                exibicao['DIFERENÇA SAÍDAS'] = (\n                    pd.to_numeric(exibicao['SAÍDAS PLANILHA'], errors='coerce').fillna(0.0)\n                    - pd.to_numeric(exibicao['SAÍDAS EXTRATO'], errors='coerce').fillna(0.0)\n                ).round(2)\n                exibicao['DATA'] = exibicao['DATA'].dt.strftime('%d/%m/%Y')\n                exibicao = exibicao[[\n                    'DATA',\n                    'ENTRADAS PLANILHA', 'ENTRADAS EXTRATO', 'DIFERENÇA ENTRADAS',\n                    'SAÍDAS PLANILHA', 'SAÍDAS EXTRATO', 'DIFERENÇA SAÍDAS',\n                    'STATUS'\n                ]]\n                exibicao.columns = [\n                    'Data',\n                    'Entrada Planilha', 'Entrada Extrato', 'Diferença Entradas',\n                    'Saída Planilha', 'Saída Extrato', 'Diferença Saídas',\n                    'Status'\n                ]\n                exibicao = formatar_dataframe_moeda_br(\n                    exibicao,\n                    ['Entrada Planilha', 'Entrada Extrato', 'Diferença Entradas',\n                     'Saída Planilha', 'Saída Extrato', 'Diferença Saídas']\n                )\n'''

count = s.count(old)
if count == 0:
    raise SystemExit('Bloco da conferência não encontrado')
s = s.replace(old, new)
p.write_text(s, encoding='utf-8')
print(f'Atualizados {count} blocos de conferência com colunas de diferença.')
