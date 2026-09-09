from pathlib import Path

p = Path('app_legacy.py')
s = p.read_text(encoding='utf-8')

old = """def gerar_excel_nova_geracao(dados_por_banco, modelo_bytes=None):\n    \"\"\"Gera um único arquivo com uma aba do Modelo Domínio para cada banco.\"\"\"\n"""
new = """def gerar_excel_nova_geracao(dados_por_banco, modelo_bytes=None, prefixar_historicos=True):\n    \"\"\"Gera um único arquivo com uma aba do Modelo Domínio para cada banco.\n\n    prefixar_historicos=False é exclusivo dos fluxos em que o histórico já traz\n    PAGO/RECEBIDO da origem, como Nova Geração 266 e 1396.\n    \"\"\"\n"""
if old not in s:
    raise SystemExit('assinatura de gerar_excel_nova_geracao não encontrada')
s = s.replace(old, new, 1)

old2 = """            elif coluna == 'HISTÓRICO':\n                valor = prefixar_historico_movimento(\n                    valor, registro.get('VALOR', 0)\n                )\n"""
new2 = """            elif coluna == 'HISTÓRICO' and prefixar_historicos:\n                valor = prefixar_historico_movimento(\n                    valor, registro.get('VALOR', 0)\n                )\n"""
if old2 not in s:
    raise SystemExit('prefixação no exportador não encontrada')
s = s.replace(old2, new2, 1)

old3 = """                        dados_exportacao_por_banco,\n                        modelo_org_bytes\n                    )\n"""
new3 = """                        dados_exportacao_por_banco,\n                        modelo_org_bytes,\n                        False\n                    )\n"""
# Restrito ao bloco Nova Geração: usamos o marcador imediatamente anterior.
marker = 'renderizar_previa_bancos_padrao(\n                        dados_exportacao_por_banco,'
pos = s.find(marker)
if pos < 0:
    raise SystemExit('bloco de exportação Nova Geração não encontrado')
call_pos = s.find(old3, pos)
if call_pos < 0:
    raise SystemExit('chamada do exportador Nova Geração não encontrada')
s = s[:call_pos] + s[call_pos:].replace(old3, new3, 1)

p.write_text(s, encoding='utf-8')
print('OK: 266/1396 preservam PAGO/RECEBIDO original sem prefixo extra na exportação')
