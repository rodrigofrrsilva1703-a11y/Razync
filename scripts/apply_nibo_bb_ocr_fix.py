from pathlib import Path

path = Path('razync/nibo.py')
text = path.read_text(encoding='utf-8')
old = '''    elif "." in bruto:\n        partes = bruto.split(".")\n        if len(partes[-1]) == 2:\n            normalizado = "".join(partes[:-1]) + "." + partes[-1]\n        elif len(partes[-1]) == 3:\n            normalizado = "".join(partes)\n        else:\n            normalizado = bruto.replace(".", "")\n'''
new = '''    elif "." in bruto:\n        # OCR do Nibo pode perder a vírgula decimal em valores com milhar.\n        # Ex.: "20.115,83" pode chegar como "20.11583". Nesse formato,\n        # os dois últimos dígitos continuam sendo os centavos.\n        sinal = "-" if bruto.startswith("-") else ""\n        corpo = bruto.lstrip("-")\n        if re.fullmatch(r"\\d{1,3}(?:\\.\\d{3})+\\d{2}", corpo):\n            inteiro = corpo[:-2].replace(".", "")\n            normalizado = f"{sinal}{inteiro}.{corpo[-2:]}"\n        else:\n            partes = bruto.split(".")\n            if len(partes[-1]) == 2:\n                normalizado = "".join(partes[:-1]) + "." + partes[-1]\n            elif len(partes[-1]) == 3:\n                normalizado = "".join(partes)\n            else:\n                normalizado = bruto.replace(".", "")\n'''
if old not in text:
    raise SystemExit('Trecho esperado de _valor_br não encontrado')
path.write_text(text.replace(old, new, 1), encoding='utf-8')

test_path = Path('tests/test_nibo.py')
test_path.write_text('''from razync.nibo import _valor_br\n\n\ndef test_valor_br_corrige_virgula_perdida_pelo_ocr():\n    assert _valor_br("20.11583") == 20115.83\n    assert _valor_br("(20.11583)") == -20115.83\n\n\ndef test_valor_br_preserva_formatos_normais():\n    assert _valor_br("61.722,68") == 61722.68\n    assert _valor_br("(41.271,20)") == -41271.20\n    assert _valor_br("123.45") == 123.45\n''', encoding='utf-8')
