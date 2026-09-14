from pathlib import Path

path = Path('razync/valean_626.py')
text = path.read_text(encoding='utf-8')
old = '''        antes_bruto = primeira[10:movimento.start()]\n        antes_norm = _normalizar(antes_bruto)\n        if "saldo anterior" in antes_norm or re.search(r"(?:^|\\s)s\\s*a\\s*l\\s*d\\s*o\\s*$", antes_norm):\n            continue\n'''
new = '''        antes_bruto = primeira[10:movimento.start()]\n        antes_norm = _normalizar(antes_bruto)\n        # O BB usa o código estrutural 999 para a linha de saldo final.\n        # Essa linha nunca representa movimento e não pode ir ao Modelo Domínio.\n        antes_saldo = re.sub(r"\\s+", " ", antes_norm).strip()\n        tem_saldo = (\n            "saldo anterior" in antes_saldo\n            or re.search(r"(?:^|\\s)s\\s*a\\s*l\\s*d\\s*o\\s*$", antes_saldo) is not None\n            or re.search(r"(?:^|\\s)999(?:\\s+|.*?\\s+)s\\s*a\\s*l\\s*d\\s*o(?:\\s|$)", antes_saldo) is not None\n            or re.search(r"(?:^|\\s)999\\s+saldo(?:\\s|$)", antes_saldo) is not None\n        )\n        if tem_saldo:\n            continue\n'''
if old not in text:
    raise SystemExit('Trecho alvo não encontrado')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
