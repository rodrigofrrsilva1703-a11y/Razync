from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old_checks = [
    "if banco_identificado != 'BANCO ITAÚ' and 'itau' not in texto_norm:",
    "'DESCRIÇÃO': banco_identificado or 'BANCO ITAÚ',",
    "if banco_identificado == 'BANCO ITAÚ':",
]
for check in old_checks:
    if check not in text:
        raise SystemExit(f'Ponto antigo não encontrado: {check!r}')

text = text.replace(
    "if banco_identificado != 'BANCO ITAÚ' and 'itau' not in texto_norm:",
    "if banco_identificado not in {'BANCO ITAU', 'BANCO ITAÚ'} and 'itau' not in texto_norm:",
    1
)
text = text.replace(
    "'DESCRIÇÃO': banco_identificado or 'BANCO ITAÚ',",
    "'DESCRIÇÃO': banco_identificado or 'BANCO ITAU',",
    1
)
text = text.replace(
    "if banco_identificado == 'BANCO ITAÚ':",
    "if banco_identificado in {'BANCO ITAU', 'BANCO ITAÚ'}:",
    1
)

checks = [
    "if banco_identificado in {'BANCO ITAU', 'BANCO ITAÚ'}:",
    "if banco_identificado not in {'BANCO ITAU', 'BANCO ITAÚ'}",
    "'saldo aplic'",
    "'saldo total disponivel dia'",
    "'saldo movimentacao conta'",
    "'sdo aplic aut mais ap'",
]
for check in checks:
    if check not in text:
        raise SystemExit(f'Validação falhou: {check!r}')

path.write_text(text, encoding='utf-8')
print('Parser Itaú detalhado agora é acionado pelo identificador real BANCO ITAU.')
