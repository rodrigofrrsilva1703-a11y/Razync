from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
old = '# Deploy sync 2026-09-09: históricos Nova Geração 266/1396 preservam PAGO/RECEBIDO original sem prefixo extra.'
new = '# Deploy sync 2026-09-14: Caixa 625 suporta extrato #PESSOAL multilinha e SIATR antigo.'
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    s = new + '\n' + s
p.write_text(s, encoding='utf-8')
