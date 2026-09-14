from pathlib import Path

p = Path('app_legacy.py')
texto = p.read_text(encoding='utf-8')
old = "if empresa == 'valean_625':\n                    bancos_validos = {'banco_brasil', 'caixa', 'sicredi'}"
new = "if empresa in {'valean_625', 'valean_626'}:\n                    bancos_validos = {'banco_brasil', 'caixa', 'sicredi'}"
if old not in texto:
    raise SystemExit('Trecho da Base Inteligente Valean não encontrado')
texto = texto.replace(old, new, 1)
p.write_text(texto, encoding='utf-8')
