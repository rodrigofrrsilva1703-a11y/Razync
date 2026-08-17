from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

antigo = """    lancamentos = []
    chaves_vistas = set()
    for texto_pagina in textos_layout:
        for linha in texto_pagina.splitlines():
"""
novo = """    lancamentos = []
    chaves_vistas = set()

    # Alguns PDFs recentes do Dayconnect perdem as datas DD/MM quando extraídos
    # em modo layout. O texto simples preserva corretamente data, histórico e sinal.
    # Processamos primeiro o texto simples e mantemos o layout como fallback para
    # os formatos antigos; a deduplicação abaixo impede lançamentos repetidos.
    fontes_texto = textos_simples + textos_layout
    for texto_pagina in fontes_texto:
        for linha in texto_pagina.splitlines():
"""
if antigo not in s:
    raise SystemExit('Bloco Daycoval esperado não encontrado.')
s = s.replace(antigo, novo, 1)

checks = [
    'fontes_texto = textos_simples + textos_layout',
    'for texto_pagina in fontes_texto:',
    'chaves_vistas = set()',
]
for check in checks:
    if check not in s:
        raise SystemExit(f'Validação falhou: {check}')

p.write_text(s, encoding='utf-8')
print('Parser Daycoval atualizado: texto simples primeiro, layout como fallback.')
