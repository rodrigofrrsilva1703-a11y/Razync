from pathlib import Path

path = Path('razync/valean_625.py')
text = path.read_text(encoding='utf-8')
old = '        or re.match(r"^\\d{2}/\\d{2}/\\d{4},?\\s+\\d{2}:\\d{2}\\s+banco do brasil", norm) is not None\n'
new = '        # Cabeçalho/rodapé impresso pelo BB: data, vírgula e hora. O nome do banco\n        # pode sair quebrado no PDF (ex.: "Banc o do Bras il"), então a vírgula\n        # após a data é o sinal confiável para nunca abrir um novo lançamento.\n        or re.match(r"^\\d{2}/\\d{2}/\\d{4},\\s*\\d{2}:\\d{2}\\b", norm) is not None\n'
if old not in text:
    raise SystemExit('Trecho esperado não encontrado')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
