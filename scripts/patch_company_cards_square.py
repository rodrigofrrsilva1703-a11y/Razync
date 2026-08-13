from pathlib import Path
import re

p = Path('app.py')
s = p.read_text(encoding='utf-8')

padrao = re.compile(
    r'(?m)^(?P<i>\s*)st\.dataframe\(diario,\s*use_container_width=True(?:,\s*height=\d+)?\)\s*$'
)

def substituir(m):
    i = m.group('i')
    return f'''{i}tabela = diario[[
{i}    'DATA', 'ENTRADAS PLANILHA', 'ENTRADAS EXTRATO',
{i}    'SAÍDAS PLANILHA', 'SAÍDAS EXTRATO', 'STATUS'
{i}]].copy()
{i}tabela['DATA'] = pd.to_datetime(tabela['DATA'], errors='coerce').dt.strftime('%d/%m/%Y')
{i}tabela.columns = [
{i}    'Data', 'Entrada Planilha', 'Entrada Extrato',
{i}    'Saída Planilha', 'Saída Extrato', 'Status'
{i}]
{i}tabela = formatar_dataframe_moeda_br(
{i}    tabela,
{i}    ['Entrada Planilha', 'Entrada Extrato', 'Saída Planilha', 'Saída Extrato']
{i})
{i}st.dataframe(tabela, use_container_width=True, height=390, hide_index=True)'''

s, quantidade = padrao.subn(substituir, s)

# Se a tabela principal já foi montada como `exibicao`, garante que o índice fique oculto.
s = s.replace(
    'st.dataframe(exibicao, use_container_width=True, height=390)',
    'st.dataframe(exibicao, use_container_width=True, height=390, hide_index=True)'
)

if quantidade == 0 and 'Entrada Planilha' not in s:
    raise SystemExit('Tabela da conferência não encontrada.')

p.write_text(s, encoding='utf-8')
print(f'Tabelas brutas corrigidas: {quantidade}')
