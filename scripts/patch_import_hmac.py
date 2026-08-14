from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

if 'import hmac\n' not in s:
    alvo = 'import hashlib\n'
    if alvo not in s:
        raise SystemExit('Import hashlib não encontrado.')
    s = s.replace(alvo, alvo + 'import hmac\n', 1)

if 'import hmac\n' not in s:
    raise SystemExit('Falha ao adicionar import hmac.')

p.write_text(s, encoding='utf-8')
print('import hmac adicionado ao app.py')
