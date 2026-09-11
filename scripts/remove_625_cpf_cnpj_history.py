from pathlib import Path

p = Path('razync/valean_625.py')
s = p.read_text(encoding='utf-8')

old = '''def _registro(banco: str, data, valor: float, historico: str) -> dict:\n    conta = CONTAS_VALEAN_625[banco]\n    historico = re.sub(r"\\s+", " ", str(historico or "MOVIMENTO BANCÁRIO")).strip()\n    historico = re.sub(r"^(?:recebido|pago):\\s*", "", historico, flags=re.I)\n    historico = ("Recebido: " if valor > 0 else "Pago: ") + historico\n'''
new = '''def _limpar_cpf_cnpj_historico(texto: str) -> str:\n    texto = str(texto or "")\n    # Remove CPF/CNPJ com ou sem rótulo e com ou sem pontuação.\n    padroes = [\n        r"\\b(?:CPF|CNPJ)\\s*[:\\-]?\\s*(?:\\d{3}\\.?\\d{3}\\.?\\d{3}-?\\d{2}|\\d{2}\\.?\\d{3}\\.?\\d{3}/?\\d{4}-?\\d{2}|\\d{11}|\\d{14})\\b",\n        r"(?<!\\d)(?:\\d{3}\\.?\\d{3}\\.?\\d{3}-?\\d{2}|\\d{2}\\.?\\d{3}\\.?\\d{3}/?\\d{4}-?\\d{2})(?!\\d)",\n    ]\n    for padrao in padroes:\n        texto = re.sub(padrao, " ", texto, flags=re.I)\n    texto = re.sub(r"\\b(?:CPF|CNPJ)\\b\\s*[:\\-]?", " ", texto, flags=re.I)\n    return re.sub(r"\\s+", " ", texto).strip(" -|;,:.")\n\n\ndef _registro(banco: str, data, valor: float, historico: str) -> dict:\n    conta = CONTAS_VALEAN_625[banco]\n    historico = re.sub(r"\\s+", " ", str(historico or "MOVIMENTO BANCÁRIO")).strip()\n    historico = re.sub(r"^(?:recebido|pago):\\s*", "", historico, flags=re.I)\n    historico = _limpar_cpf_cnpj_historico(historico) or "MOVIMENTO BANCÁRIO"\n    historico = ("Recebido: " if valor > 0 else "Pago: ") + historico\n'''

if old not in s:
    raise SystemExit('bloco _registro não encontrado')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
