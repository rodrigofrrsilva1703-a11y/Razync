from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old_name = '1396 - Nova Geração'
new_name = '1396 - Nova Geração Filial'

count = text.count(old_name)
if count < 1:
    raise SystemExit('Nome atual da filial não encontrado.')
text = text.replace(old_name, new_name)

# Não altera nenhuma chave técnica da base; somente textos visuais.
if "'nova_geracao_filial'" not in text:
    raise SystemExit('A chave independente nova_geracao_filial não foi preservada.')
if new_name not in text:
    raise SystemExit('Novo nome visual da filial não foi aplicado.')

path.write_text(text, encoding='utf-8')
print(f'Nome visual da filial atualizado em {count} ocorrência(s) para {new_name}.')
