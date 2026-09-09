from pathlib import Path

p = Path('app_legacy.py')
s = p.read_text(encoding='utf-8')

old = '''        historico_origem = texto_celula_seguro(historico_valor_original)\n        documento = texto_celula_seguro(linha[col_doc])\n        historico_final = re.sub(r'\\s+', ' ', " ".join(\n            parte for parte in [lacto, historico_origem, documento] if parte\n        )).strip()\n'''
new = '''        historico_origem = texto_celula_seguro(historico_valor_original)\n        documento = texto_celula_seguro(linha[col_doc])\n\n        # Empresas 266 e 1396 (Nova Geração): o status do lançamento já vem no\n        # campo LACTO e não deve poluir o histórico do Modelo Domínio. Mantemos\n        # somente a informação útil da origem + documento e removemos também\n        # eventual prefixo já gravado no próprio histórico de origem.\n        historico_final = re.sub(r'\\s+', ' ', " ".join(\n            parte for parte in [historico_origem, documento] if parte\n        )).strip()\n        historico_final = re.sub(\n            r'^(?:(?:Pago|Recebido)\\s*:\\s*|(?:PAGO|RECEBIDO)\\s+)+',\n            '',\n            historico_final,\n            flags=re.IGNORECASE,\n        ).strip()\n'''

if old not in s:
    raise SystemExit('Bloco de histórico da Nova Geração não encontrado.')

s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('Prefixos removidos somente do fluxo Nova Geração 266/1396.')
