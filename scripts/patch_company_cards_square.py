from pathlib import Path
import re

p = Path('app.py')
s = p.read_text(encoding='utf-8')

pat = re.compile(
    r'(?ms)^\s{48}with st\.expander\(\n\s+"O que significam os valores acumulados\?"\n\s+\):.*?^\s{48}st\.dataframe\(\n\s+exibicao_diaria,\n\s+use_container_width=True,\n\s+height=360\n\s+\)\n'
)

novo = '''                                                exibicao_diaria = diario[[
                                                    'DATA', 'ENTRADAS PLANILHA', 'ENTRADAS EXTRATO',
                                                    'SAÍDAS PLANILHA', 'SAÍDAS EXTRATO', 'STATUS'
                                                ]].copy()
                                                exibicao_diaria['DATA'] = exibicao_diaria['DATA'].dt.strftime('%d/%m/%Y')
                                                exibicao_diaria.columns = [
                                                    'Data', 'Entrada Planilha', 'Entrada Extrato',
                                                    'Saída Planilha', 'Saída Extrato', 'Status'
                                                ]
                                                exibicao_diaria = formatar_dataframe_moeda_br(
                                                    exibicao_diaria,
                                                    ['Entrada Planilha', 'Entrada Extrato', 'Saída Planilha', 'Saída Extrato']
                                                )
                                                st.dataframe(
                                                    exibicao_diaria,
                                                    use_container_width=True,
                                                    height=390,
                                                    hide_index=True
                                                )
'''

s, n = pat.subn(novo, s, count=1)
if n != 1:
    raise SystemExit(f'Conferência antiga da Nova Geração encontrada {n} vezes.')
if 'O que significam os valores acumulados?' in s:
    raise SystemExit('Relatório antigo ainda presente.')

p.write_text(s, encoding='utf-8')
print('Conferência da Nova Geração corrigida.')
