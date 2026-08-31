from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

old_itau = "'slug': 'itau', 'descricao': 'BANCO ITAÚ', 'arquivo': 'Itau'"
new_itau = "'slug': 'itau', 'descricao': 'BANCO ITAÚ', 'arquivo': 'Itau', 'aba': 'Itaú'"
old_bb = "'slug': 'banco_brasil', 'descricao': 'BANCO DO BRASIL', 'arquivo': 'Banco_do_Brasil'"
new_bb = "'slug': 'banco_brasil', 'descricao': 'BANCO DO BRASIL', 'arquivo': 'Banco_do_Brasil', 'aba': 'Banco do Brasil'"

assert old_itau in s, 'config Itaú não encontrada'
assert old_bb in s, 'config BB não encontrada'
s = s.replace(old_itau, new_itau, 1)
s = s.replace(old_bb, new_bb, 1)

count_nome = s.count("config_banco_nibo['nome']")
assert count_nome == 2, f'esperadas 2 referências a nome, encontradas {count_nome}'
s = s.replace("config_banco_nibo['nome']", "config_banco_nibo['aba']")

p.write_text(s, encoding='utf-8')
