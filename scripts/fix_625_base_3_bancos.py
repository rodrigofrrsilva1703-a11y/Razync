from pathlib import Path

p = Path('app_legacy.py')
text = p.read_text(encoding='utf-8')
old = """                bancos_validos = {\n                    'itau', 'bradesco', 'fibra', 'daycoval', 'sicredi',\n                    'santander', 'btg'\n                }\n"""
new = """                if empresa == 'valean_625':\n                    bancos_validos = {'banco_brasil', 'caixa', 'sicredi'}\n                else:\n                    bancos_validos = {\n                        'itau', 'bradesco', 'fibra', 'daycoval', 'sicredi',\n                        'santander', 'btg'\n                    }\n"""
if old not in text:
    raise SystemExit('Trecho alvo não encontrado')
text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8')
