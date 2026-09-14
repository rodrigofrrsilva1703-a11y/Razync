from pathlib import Path

path = Path('razync/valean_626.py')
text = path.read_text(encoding='utf-8')
old = '''        # Remove agência/lote e Documento, mantendo apenas o histórico textual.\n        antes = re.sub(r"^\\s*(?:[=\\d]+\\s+){2,5}", "", antes_bruto).strip()\n        antes = re.sub(r"\\s+\\d[\\d./-]{2,}\\s*$", "", antes).strip()\n\n        complementos = []\n'''
new = '''        # Remove agência/lote e Documento, mantendo apenas o histórico textual.\n        antes = re.sub(r"^\\s*(?:[=\\d]+\\s+){2,8}", "", antes_bruto).strip()\n        antes = re.sub(r"\\s+\\d[\\d./-]{2,}\\s*$", "", antes).strip()\n\n        # Segunda barreira contra o saldo final do BB. O OCR pode distorcer o\n        # código 999 ou inserir espaços/pontuação em S A L D O; por isso, depois\n        # de retirar os campos estruturais, reduzimos o texto a letras e testamos\n        # o conteúdo sem depender do código numérico reconhecido.\n        antes_so_letras = re.sub(r"[^a-z]", "", _normalizar(antes))\n        bruto_so_letras = re.sub(r"[^a-z]", "", _normalizar(antes_bruto))\n        if antes_so_letras in {"saldo", "saldoanterior"} or bruto_so_letras.endswith("saldo"):\n            continue\n\n        complementos = []\n'''
if old not in text:
    raise SystemExit('Trecho alvo não encontrado')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
