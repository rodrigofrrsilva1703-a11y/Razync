from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

# ----------------------------------------------------------------------------
# A natureza do lançamento bancário deve vir SEMPRE do sinal do VALOR:
#   valor < 0  => pago / saída  => conta do banco no CRÉDITO
#   valor > 0  => recebido      => conta do banco no DÉBITO
# O texto do histórico não pode inverter essa decisão.
# ----------------------------------------------------------------------------
old_base = '''        assinatura = item.get('assinatura', '')
        natureza = assinatura.split('|', 1)[0] if assinatura else ''
        debito_item = texto_celula_seguro(item.get('debito'))
        credito_item = texto_celula_seguro(item.get('credito'))
        conta_banco_item = texto_celula_seguro(contas_bancarias.get(banco, ''))

        if natureza == 'pago':
            contrapartida = debito_item
        elif natureza == 'recebido':
            contrapartida = credito_item
        elif banco in contas_bancarias and conta_banco_item:
            # Planilhas Autokraft aprendidas não trazem PAGO/RECEBIDO no histórico.
            # Se a conta do banco está no crédito, é uma saída; se está no débito, é entrada.
            if credito_item == conta_banco_item and debito_item:
                natureza = 'pago'
                contrapartida = debito_item
            elif debito_item == conta_banco_item and credito_item:
                natureza = 'recebido'
                contrapartida = credito_item
            else:
                contrapartida = ''
        else:
            contrapartida = ''
'''
new_base = '''        assinatura = item.get('assinatura', '')
        debito_item = texto_celula_seguro(item.get('debito'))
        credito_item = texto_celula_seguro(item.get('credito'))
        conta_banco_item = texto_celula_seguro(contas_bancarias.get(banco, ''))

        # Para padrões já aprendidos, a posição REAL da conta bancária é mais
        # confiável que palavras como "pago" ou "recebido" presentes no histórico.
        if banco in contas_bancarias and conta_banco_item:
            if credito_item == conta_banco_item and debito_item:
                natureza = 'pago'
                contrapartida = debito_item
            elif debito_item == conta_banco_item and credito_item:
                natureza = 'recebido'
                contrapartida = credito_item
            else:
                natureza = assinatura.split('|', 1)[0] if assinatura else ''
                contrapartida = ''
        else:
            natureza = assinatura.split('|', 1)[0] if assinatura else ''
            contrapartida = ''

        # Normaliza também a assinatura existente para a natureza real inferida
        # pela posição da conta do banco. Isso reaproveita a base antiga sem zerar.
        if assinatura and natureza in {'pago', 'recebido'}:
            partes_assinatura = assinatura.split('|', 1)
            sufixo_assinatura = partes_assinatura[1] if len(partes_assinatura) > 1 else ''
            assinatura = (
                f"{natureza}|{sufixo_assinatura}" if sufixo_assinatura else natureza
            )
'''
if text.count(old_base) != 1:
    raise SystemExit(f'Bloco de interpretação da base encontrado {text.count(old_base)} vezes.')
text = text.replace(old_base, new_base, 1)

old_class = '''            assinatura = criar_assinatura_classificacao(historico)
            natureza = assinatura.split('|', 1)[0] if assinatura else ''

            # Fallback essencial para as planilhas Autokraft: nelas o histórico
            # costuma ser apenas a descrição original, enquanto o sinal do VALOR
            # informa com segurança se foi entrada ou saída.
            if natureza not in {'pago', 'recebido'} and col_valor is not None:
                valor_linha = limpar_valor_monetario(
                    ws.cell(numero_linha, col_valor).value
                )
                if valor_linha < 0:
                    natureza = 'pago'
                elif valor_linha > 0:
                    natureza = 'recebido'
'''
new_class = '''            assinatura = criar_assinatura_classificacao(historico)

            # REGRA PRINCIPAL: o sinal do VALOR decide a natureza.
            # Nunca usamos uma palavra perdida no histórico para decidir se o banco
            # entra no débito ou no crédito.
            valor_linha = (
                limpar_valor_monetario(ws.cell(numero_linha, col_valor).value)
                if col_valor is not None else 0.0
            )
            if valor_linha < 0:
                natureza = 'pago'
            elif valor_linha > 0:
                natureza = 'recebido'
            else:
                natureza = assinatura.split('|', 1)[0] if assinatura else ''

            # A assinatura usada para procurar a contrapartida também recebe a
            # natureza definida pelo sinal, evitando que "pago" dentro do histórico
            # faça um recebimento buscar padrões de pagamento (e vice-versa).
            if assinatura and natureza in {'pago', 'recebido'}:
                partes_assinatura = assinatura.split('|', 1)
                sufixo_assinatura = partes_assinatura[1] if len(partes_assinatura) > 1 else ''
                assinatura = (
                    f"{natureza}|{sufixo_assinatura}" if sufixo_assinatura else natureza
                )
'''
if text.count(old_class) != 1:
    raise SystemExit(f'Bloco principal de natureza encontrado {text.count(old_class)} vezes.')
text = text.replace(old_class, new_class, 1)

old_review = '''            assinatura = criar_assinatura_classificacao(historico)
            natureza = assinatura.split('|', 1)[0] if assinatura else ''
            valor = 0.0
            if col_valor is not None:
                valor = limpar_valor_monetario(ws.cell(numero_linha, col_valor).value)
            if natureza not in {'pago', 'recebido'}:
                if valor < 0:
                    natureza = 'pago'
                elif valor > 0:
                    natureza = 'recebido'
'''
new_review = '''            assinatura = criar_assinatura_classificacao(historico)
            valor = 0.0
            if col_valor is not None:
                valor = limpar_valor_monetario(ws.cell(numero_linha, col_valor).value)

            # A Revisão Inteligente segue exatamente a mesma regra da classificação.
            if valor < 0:
                natureza = 'pago'
            elif valor > 0:
                natureza = 'recebido'
            else:
                natureza = assinatura.split('|', 1)[0] if assinatura else ''
'''
if text.count(old_review) != 1:
    raise SystemExit(f'Bloco de natureza da revisão encontrado {text.count(old_review)} vezes.')
text = text.replace(old_review, new_review, 1)

checks = [
    "if valor_linha < 0:\n                natureza = 'pago'",
    "elif valor_linha > 0:\n                natureza = 'recebido'",
    "if credito_item == conta_banco_item and debito_item:",
    "if valor < 0:\n                natureza = 'pago'",
    "f\"{natureza}|{sufixo_assinatura}\"",
]
for check in checks:
    if check not in text:
        raise SystemExit(f'Validação falhou: {check}')

path.write_text(text, encoding='utf-8')
print('Contas bancárias passam a ser classificadas pelo sinal do valor, não por palavras do histórico.')
