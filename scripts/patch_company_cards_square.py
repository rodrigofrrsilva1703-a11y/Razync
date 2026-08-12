from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old = """            if banco_linha not in {'itau', 'bradesco', 'fibra'}:\n                resumo['banco_nao_identificado'] += 1\n                continue\n"""
new = """            if banco_linha not in contas_bancarias:\n                resumo['banco_nao_identificado'] += 1\n                continue\n"""

if text.count(old) != 1:
    raise SystemExit(
        f'Filtro antigo de bancos encontrado {text.count(old)} vezes; alteração cancelada.'
    )
text = text.replace(old, new, 1)

# Validações estáticas específicas do comportamento pedido.
checks = [
    "'contas_bancarias': {'itau': '508', 'daycoval': '2283'}",
    "'contas_bancarias': {'itau': '508', 'daycoval': '505'}",
    "'contas_bancarias': {'itau': '508', 'daycoval': '506'}",
    "if banco_linha not in contas_bancarias:",
    "identificar_chave_banco_empresa",
]
for check in checks:
    if check not in text:
        raise SystemExit(f'Validação falhou: não encontrei {check!r}.')

path.write_text(text, encoding='utf-8')
print('Classificação corrigida para aceitar os bancos configurados por empresa, incluindo Daycoval.')
