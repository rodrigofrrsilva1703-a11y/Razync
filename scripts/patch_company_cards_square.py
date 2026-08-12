from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

inicio = text.find('def processar_pdf_itau_detalhado(')
fim = text.find('\ndef processar_pdf_daycoval_detalhado(', inicio)
if inicio < 0 or fim < 0:
    raise SystemExit('Parser específico do Itaú não localizado.')

bloco = text[inicio:fim]

# O Itaú pode ter lançamentos realmente idênticos no mesmo dia (mesma data,
# valor e histórico). Não podemos deduplicar por conteúdo, pois isso altera o
# total diário e faz a conferência divergir do saldo oficial do PDF.
bloco_novo = bloco.replace('    vistos = set()\n', '')
bloco_novo = bloco_novo.replace(
    '''        chave = (data_str, round(valor, 2), historico)\n        if chave in vistos:\n            continue\n        vistos.add(chave)\n''',
    ''
)

if bloco_novo == bloco:
    raise SystemExit('A deduplicação antiga do parser Itaú não foi encontrada.')
if 'vistos' in bloco_novo:
    raise SystemExit('Ainda existe deduplicação por conteúdo dentro do parser Itaú.')

text = text[:inicio] + bloco_novo + text[fim:]

# Mantém as proteções já existentes contra linhas que são apenas saldos.
for termo in [
    "'saldo anterior'",
    "'saldo aplic'",
    "'saldo total disponivel dia'",
    "'saldo movimentacao conta'",
    "'sdo aplic aut mais ap'",
]:
    if termo not in bloco_novo:
        raise SystemExit(f'Proteção de saldo foi perdida: {termo}')

# Confirma que a conferência continua forçando o parser específico do Itaú.
if 'processar_pdf_itau_detalhado(reader, banco)' not in text:
    raise SystemExit('A conferência deixou de usar o parser específico do Itaú.')

path.write_text(text, encoding='utf-8')
print('Parser Itaú preserva lançamentos repetidos legítimos e continua ignorando linhas de saldo.')
