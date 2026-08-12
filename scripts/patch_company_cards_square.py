from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

# Mantém o visual flat já aprovado, mudando somente a paleta para preto com azul escuro.
replacements = [
    ('background: #0b151e !important;', 'background: #050b12 !important;'),
    ('border: 1px solid #1a3a4d !important;', 'border: 1px solid #12324a !important;'),
    ('background: #0f1d27 !important;', 'background: #081725 !important;'),
    ('border-color: #2586ad !important;', 'border-color: #1d6f9b !important;'),
]

for old, new in replacements:
    count = text.count(old)
    if count < 2:
        raise SystemExit(f'Esperava pelo menos 2 ocorrências de {old!r}, encontrei {count}; alteração cancelada.')
    text = text.replace(old, new)

path.write_text(text, encoding='utf-8')
print('Cards atualizados para preto com azul escuro, mantendo visual flat e sem sombras.')
