from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

old_reader = "        reader = PdfReader(caminho_pdf, strict=False)\n        texto_completo = \"\""
new_reader = "        reader = PdfReader(caminho_pdf, strict=False)\n        # O pypdf converte o caminho em BytesIO e perde reader.stream.name.\n        # Guardamos explicitamente o arquivo temporário para o fallback OCR.\n        reader._razync_source_path = caminho_pdf\n        texto_completo = \"\""
if old_reader not in s:
    raise SystemExit('Ponto de criação do PdfReader não encontrado.')
s = s.replace(old_reader, new_reader, 1)

old_path = "            caminho_pdf = getattr(getattr(reader, 'stream', None), 'name', None)"
new_path = "            caminho_pdf = (\n                getattr(reader, '_razync_source_path', None)\n                or getattr(getattr(reader, 'stream', None), 'name', None)\n            )"
if old_path not in s:
    raise SystemExit('Ponto de resolução do caminho OCR não encontrado.')
s = s.replace(old_path, new_path, 1)

for check in [
    "reader._razync_source_path = caminho_pdf",
    "getattr(reader, '_razync_source_path', None)",
    "fitz.Matrix(4.0, 4.0)",
    "lang='por'",
]:
    assert check in s, check

p.write_text(s, encoding='utf-8')
print('Caminho do PDF preservado para OCR Bradesco.')
