from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

# Padroniza os históricos gerados na organização das três empresas Autokraft.
# Entradas (VALOR positivo) recebem "Recebido:" e saídas (VALOR negativo) recebem "Pago:".
old_credito = '''                    registros[banco_atual].append({
                        'DESCRIÇÃO': f'BANCO {banco_atual.upper()}',
                        'DATA': data_aba.to_pydatetime(),
                        'VALOR': valor_credito,
                        'DÉBITO': '',
                        'CRÉDITO': '',
                        'HISTÓRICO': limpar_caracteres_ilegais(historico_credito).strip()
                    })
'''
new_credito = '''                    historico_credito_final = limpar_caracteres_ilegais(
                        historico_credito
                    ).strip()
                    registros[banco_atual].append({
                        'DESCRIÇÃO': f'BANCO {banco_atual.upper()}',
                        'DATA': data_aba.to_pydatetime(),
                        'VALOR': valor_credito,
                        'DÉBITO': '',
                        'CRÉDITO': '',
                        'HISTÓRICO': f'Recebido: {historico_credito_final}'
                    })
'''
if text.count(old_credito) != 1:
    raise SystemExit(f'Bloco de créditos Autokraft encontrado {text.count(old_credito)} vezes.')
text = text.replace(old_credito, new_credito, 1)

old_debito = '''                    registros[banco_atual].append({
                        'DESCRIÇÃO': f'BANCO {banco_atual.upper()}',
                        'DATA': data_aba.to_pydatetime(),
                        'VALOR': -valor_debito,
                        'DÉBITO': '',
                        'CRÉDITO': '',
                        'HISTÓRICO': limpar_caracteres_ilegais(historico_debito).strip()
                    })
'''
new_debito = '''                    historico_debito_final = limpar_caracteres_ilegais(
                        historico_debito
                    ).strip()
                    registros[banco_atual].append({
                        'DESCRIÇÃO': f'BANCO {banco_atual.upper()}',
                        'DATA': data_aba.to_pydatetime(),
                        'VALOR': -valor_debito,
                        'DÉBITO': '',
                        'CRÉDITO': '',
                        'HISTÓRICO': f'Pago: {historico_debito_final}'
                    })
'''
if text.count(old_debito) != 1:
    raise SystemExit(f'Bloco de débitos Autokraft encontrado {text.count(old_debito)} vezes.')
text = text.replace(old_debito, new_debito, 1)

# Validações estáticas do novo padrão.
checks = [
    "'HISTÓRICO': f'Recebido: {historico_credito_final}'",
    "'HISTÓRICO': f'Pago: {historico_debito_final}'",
    "'VALOR': valor_credito",
    "'VALOR': -valor_debito",
]
for check in checks:
    if check not in text:
        raise SystemExit(f'Validação falhou: não encontrei {check!r}.')

path.write_text(text, encoding='utf-8')
print('Históricos Autokraft padronizados: Recebido para positivos e Pago para negativos.')
