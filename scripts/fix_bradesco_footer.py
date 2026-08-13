from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

antigo = "        'extrato mensal / por periodo', 'nova geração comercial',\n        'nova geracao comercial', 'nome do usuário:', 'nome do usuario:',"
novo = "        'extrato mensal / por periodo', 'nome do usuário:', 'nome do usuario:',"
if antigo not in s:
    raise SystemExit('Prefixos antigos do Bradesco não encontrados.')
s = s.replace(antigo, novo, 1)

alvo = "            if normalizada.startswith(ignorar_prefixos):\n                continue\n            if normalizada.startswith('total '):"
substituto = "            if normalizada.startswith(ignorar_prefixos):\n                continue\n            # O nome da empresa pode ser um lançamento real. Só ignora o rodapé com CNPJ.\n            if normalizada.startswith('nova geracao comercial') and 'cnpj:' in normalizada:\n                continue\n            if normalizada.startswith('total '):"
if alvo not in s:
    raise SystemExit('Ponto de filtro do Bradesco não encontrado.')
s = s.replace(alvo, substituto, 1)

p.write_text(s, encoding='utf-8')
print('Filtro de rodapé Bradesco corrigido sem descartar lançamentos reais.')
