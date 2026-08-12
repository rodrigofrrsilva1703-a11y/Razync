from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

# Altera somente o nome exibido da Filial. A chave interna continua separada
# como nova_geracao_filial para preservar a Base Inteligente independente.
old = '''        labels_estabelecimento = {
            'matriz': 'Matriz',
            'filial': 'Filial',
        }
'''
new = '''        labels_estabelecimento = {
            'matriz': 'Matriz',
            'filial': '1396 - Nova Geração',
        }
'''
if old in text:
    text = text.replace(old, new, 1)
else:
    # Compatibilidade caso o bloco esteja escrito de outra forma: troca apenas
    # o rótulo da filial no seletor, sem tocar nas chaves da base.
    alvo = "'filial': 'Filial'"
    if text.count(alvo) != 1:
        raise SystemExit(f'Rótulo da Filial encontrado {text.count(alvo)} vezes.')
    text = text.replace(alvo, "'filial': '1396 - Nova Geração'", 1)

if "'nova_geracao_filial'" not in text:
    raise SystemExit('A chave independente da Base Inteligente da Filial não foi preservada.')
if '1396 - Nova Geração' not in text:
    raise SystemExit('Novo nome da Filial não foi aplicado.')

path.write_text(text, encoding='utf-8')
print('Filial renomeada visualmente para 1396 - Nova Geração, mantendo sua base independente.')
