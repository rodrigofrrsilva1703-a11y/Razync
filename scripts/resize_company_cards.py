from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

replacements = {
    '            height: 156px !important;\n': '            height: 132px !important;\n',
    '            min-height: 156px !important;\n': '            min-height: 132px !important;\n',
    '            padding: 20px 22px !important;\n': '            padding: 14px 16px !important;\n',
    '            border-radius: 10px !important;\n': '            border-radius: 7px !important;\n',
    '            font-size: 12px !important;\n': '            font-size: 11px !important;\n',
    '            font-size: 18px !important;\n': '            font-size: 16px !important;\n',
}

for old, new in replacements.items():
    count = text.count(old)
    if count < 1:
        raise SystemExit(f'Trecho esperado não encontrado: {old!r}')
    # altera somente a primeira ocorrência pertinente aos cards de empresa
    card_start = text.index('/* Cards de empresas: preto azulado e completamente clicáveis. */')
    before = text[:card_start]
    after = text[card_start:]
    if old not in after:
        raise SystemExit(f'Trecho não encontrado no bloco dos cards: {old!r}')
    after = after.replace(old, new, 1)
    text = before + after

path.write_text(text, encoding='utf-8')
print('Cards das empresas ajustados com segurança.')
