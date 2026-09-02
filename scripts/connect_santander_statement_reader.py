from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

anchor_import = 'from razync.up_pack import identificar_banco_up_pack, processar_planilha_up_pack\n'
new_import = (
    'from razync.santander_statement import ('
    'parece_extrato_santander_empresarial, '
    'processar_extrato_santander_empresarial_texto)\n'
)
if new_import not in s:
    if anchor_import not in s:
        raise SystemExit('Import anchor not found')
    s = s.replace(anchor_import, anchor_import + new_import, 1)

anchor = '''        nome_para_identificacao = filename_original or os.path.basename(caminho_pdf)\n        banco_identificado = identificar_banco_inteligente(texto_completo, nome_para_identificacao)\n\n'''
insert = '''        nome_para_identificacao = filename_original or os.path.basename(caminho_pdf)\n        banco_identificado = identificar_banco_inteligente(texto_completo, nome_para_identificacao)\n\n        # Santander Empresarial: formato Data / Histórico / Valor.\n        # É processado antes do parser universal porque o próprio PDF informa\n        # o sinal com "- R$" nas saídas e sem hífen nas entradas.\n        if parece_extrato_santander_empresarial(texto_completo):\n            lancamentos_santander = processar_extrato_santander_empresarial_texto(\n                texto_completo,\n                banco='BANCO SANTANDER',\n            )\n            if lancamentos_santander:\n                return lancamentos_santander\n\n'''
if 'lancamentos_santander = processar_extrato_santander_empresarial_texto' not in s:
    if anchor not in s:
        raise SystemExit('PDF parser anchor not found')
    s = s.replace(anchor, insert, 1)

p.write_text(s, encoding='utf-8')
# trigger
