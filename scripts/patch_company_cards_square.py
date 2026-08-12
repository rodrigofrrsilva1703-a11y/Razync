from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old = '''        [data-testid="stCaptionContainer"] p {
            color: #c8d7e2 !important;
            font-size: 13.5px !important;
            line-height: 1.55 !important;
            font-weight: 500 !important;
            margin: 0 !important;
        }
'''
new = '''        [data-testid="stCaptionContainer"] p {
            color: #d6e4ee !important;
            font-size: 16px !important;
            line-height: 1.6 !important;
            font-weight: 550 !important;
            margin: 0 !important;
        }
'''
if text.count(old) != 1:
    raise SystemExit(f'Estilo atual dos textos explicativos encontrado {text.count(old)} vezes.')
text = text.replace(old, new, 1)

path.write_text(text, encoding='utf-8')
print('Textos explicativos aumentados para 16px com contraste reforçado.')
