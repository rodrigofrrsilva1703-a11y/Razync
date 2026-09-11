from pathlib import Path

p = Path('razync/valean_625.py')
s = p.read_text(encoding='utf-8')
old = '''        antes = primeira[10:movimento.start()]\n        antes = re.sub(r"^\\s*\\d{4}\\s+\\d{5,8}\\s*", "", antes)\n        antes = re.sub(r"\\s+\\d[\\d.]{2,}$", "", antes).strip()\n'''
new = '''        antes = primeira[10:movimento.start()]\n        # BB Autorizável: após a data vêm Nº do documento e lote antes do histórico.\n        # Esses campos são estruturais do extrato e nunca devem compor o HISTÓRICO.\n        antes = re.sub(r"^\\s*\\d{4}\\s+\\d{5,8}\\s*", "", antes)\n        # Remove também a coluna Documento quando ela aparece no fim do trecho\n        # anterior ao valor (numérica, com pontos ou barras), preservando o texto.\n        antes = re.sub(r"\\s+(?:\\d[\\d./-]{2,})\\s*$", "", antes).strip()\n'''
if old not in s:
    raise SystemExit('trecho BB esperado não encontrado')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
