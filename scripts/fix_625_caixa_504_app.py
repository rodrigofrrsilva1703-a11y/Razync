from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
s=s.replace('Caixa · Conta 508', 'Caixa · Conta 504')
s=s.replace('"conta": "508"', '"conta": "504"')
s=s.replace('Caixa · conta 508', 'Caixa · conta 504')
p.write_text(s, encoding='utf-8')
assert 'Caixa · Conta 508' not in s
assert 'Caixa · conta 508' not in s
print('OK Caixa 625 = 504 no app')
