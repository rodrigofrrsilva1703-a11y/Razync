from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

anchor = "from razync.bank_validation import diagnostico_pdf_sem_lancamentos, validar_fechamento_saldo\n"
insert = anchor + "from razync.bb_statement import parece_extrato_bb_autorizavel, processar_extrato_bb_autorizavel\n"
if "from razync.bb_statement import" not in s:
    if anchor not in s:
        raise SystemExit('anchor de import não encontrado')
    s = s.replace(anchor, insert, 1)

old = """    filtrados = []\n    for item in processar_extrato_unificado(file_bytes, filename) or []:\n"""
new = """    filtrados = []\n    # O extrato BB Empresa 'Autorizável' possui linhas quebradas e pode colar\n    # movimento e saldo. Usa leitor dedicado para não perder/duplicar valores.\n    if str(filename).lower().endswith('.pdf') and parece_extrato_bb_autorizavel(file_bytes):\n        origem_extrato = processar_extrato_bb_autorizavel(file_bytes)\n    else:\n        origem_extrato = processar_extrato_unificado(file_bytes, filename) or []\n    for item in origem_extrato:\n"""
if old not in s:
    raise SystemExit('bloco da conferência não encontrado')
s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
