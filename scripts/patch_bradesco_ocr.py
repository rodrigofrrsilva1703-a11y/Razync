from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

old = """    for pagina in reader.pages:\n        texto = pagina.extract_text() or ''\n        for linha_bruta in texto.splitlines():"""
new = """    textos_paginas = [pagina.extract_text() or '' for pagina in reader.pages]\n\n    # Alguns extratos do Bradesco Net Empresa são PDFs rasterizados, sem qualquer\n    # camada de texto. Nesses casos usamos OCR apenas como fallback, mantendo o\n    # caminho rápido do pypdf para os PDFs normais.\n    if not any(texto.strip() for texto in textos_paginas):\n        try:\n            import fitz\n            import pytesseract\n            from PIL import Image\n\n            caminho_pdf = getattr(getattr(reader, 'stream', None), 'name', None)\n            if caminho_pdf and os.path.exists(caminho_pdf):\n                documento_ocr = fitz.open(caminho_pdf)\n                textos_paginas = []\n                for pagina_ocr in documento_ocr:\n                    pix = pagina_ocr.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)\n                    imagem = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)\n                    texto_ocr = pytesseract.image_to_string(\n                        imagem,\n                        config='--psm 6 -c preserve_interword_spaces=1'\n                    )\n                    textos_paginas.append(texto_ocr or '')\n                documento_ocr.close()\n        except Exception:\n            textos_paginas = textos_paginas or []\n\n    for texto in textos_paginas:\n        for linha_bruta in texto.splitlines():"""

if old not in s:
    if 'textos_paginas = [pagina.extract_text() or' in s:
        print('Fallback OCR Bradesco já aplicado.')
        raise SystemExit(0)
    raise SystemExit('Trecho do leitor Bradesco não encontrado.')

s = s.replace(old, new, 1)

checks = [
    "import pytesseract",
    "import fitz",
    "preserve_interword_spaces=1",
    "if not any(texto.strip() for texto in textos_paginas)",
]
for check in checks:
    if check not in s:
        raise SystemExit(f'Check OCR ausente: {check}')

p.write_text(s, encoding='utf-8')
print('Fallback OCR Bradesco aplicado.')
