from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

s = s.replace(
    "'DATA', 'ENTRADAS PLANILHA', 'ENTRADAS EXTRATO',\n                                                    'SAÍDAS PLANILHA', 'SAÍDAS EXTRATO', 'STATUS'",
    "'DATA', 'ENTRADAS PLANILHA', 'ENTRADAS EXTRATO', 'DIF. ENTRADAS',\n                                                    'SAÍDAS PLANILHA', 'SAÍDAS EXTRATO', 'DIF. SAÍDAS', 'STATUS'",
    1
)
s = s.replace(
    "'Data', 'Entrada Planilha', 'Entrada Extrato',\n                                                    'Saída Planilha', 'Saída Extrato', 'Status'",
    "'Data', 'Entrada Planilha', 'Entrada Extrato', 'Diferença Entradas',\n                                                    'Saída Planilha', 'Saída Extrato', 'Diferença Saídas', 'Status'",
    1
)
s = s.replace(
    "['Entrada Planilha', 'Entrada Extrato', 'Saída Planilha', 'Saída Extrato']",
    "['Entrada Planilha', 'Entrada Extrato', 'Diferença Entradas', 'Saída Planilha', 'Saída Extrato', 'Diferença Saídas']",
    1
)

if "'Diferença Entradas'" not in s or "'Diferença Saídas'" not in s:
    raise SystemExit('Não foi possível incluir as diferenças na tabela da Nova Geração.')

p.write_text(s, encoding='utf-8')
print('Diferenças adicionadas na conferência da Nova Geração.')
