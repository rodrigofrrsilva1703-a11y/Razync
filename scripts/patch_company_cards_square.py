from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

# 1) Ao montar a base de classificação, registros Autokraft podem ter assinatura
# com natureza "outro" porque o histórico do mapa não contém PAGO/RECEBIDO.
# Nesses casos, inferimos a natureza pela conta bancária já preenchida na base.
old_base = '''        natureza = assinatura.split('|', 1)[0] if assinatura else ''
        if natureza == 'pago':
            contrapartida = texto_celula_seguro(item.get('debito'))
        elif natureza == 'recebido':
            contrapartida = texto_celula_seguro(item.get('credito'))
        else:
            contrapartida = ''
        if banco not in contas_bancarias or not assinatura or not contrapartida:
            continue
'''
new_base = '''        natureza = assinatura.split('|', 1)[0] if assinatura else ''
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
        if banco not in contas_bancarias or not assinatura or not contrapartida:
            continue
'''
if text.count(old_base) != 1:
    raise SystemExit(f'Bloco de leitura da base encontrado {text.count(old_base)} vezes.')
text = text.replace(old_base, new_base, 1)

# 2) A planilha final Autokraft possui VALOR positivo/negativo, mas o histórico
# pode não conter PAGO/RECEBIDO. Usa o sinal do VALOR como fallback para decidir
# em qual coluna entra a conta bancária.
old_cols = '''        col_hist = mapa_colunas['historico']
        col_debito = mapa_colunas['debito']
        col_credito = mapa_colunas['credito']
        col_descricao = mapa_colunas.get('descricao')
'''
new_cols = '''        col_hist = mapa_colunas['historico']
        col_debito = mapa_colunas['debito']
        col_credito = mapa_colunas['credito']
        col_valor = mapa_colunas.get('valor')
        col_descricao = mapa_colunas.get('descricao')
'''
if text.count(old_cols) != 1:
    raise SystemExit(f'Bloco de colunas encontrado {text.count(old_cols)} vezes.')
text = text.replace(old_cols, new_cols, 1)

old_nature = '''            assinatura = criar_assinatura_classificacao(historico)
            natureza = assinatura.split('|', 1)[0] if assinatura else ''
            conta_banco = contas_bancarias[banco_linha]
            if natureza == 'pago':
'''
new_nature = '''            assinatura = criar_assinatura_classificacao(historico)
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

            conta_banco = contas_bancarias[banco_linha]
            if natureza == 'pago':
'''
if text.count(old_nature) != 1:
    raise SystemExit(f'Bloco de natureza encontrado {text.count(old_nature)} vezes.')
text = text.replace(old_nature, new_nature, 1)

# 3) A assinatura armazenada na base Autokraft pode começar com "outro|".
# Para busca exata, tentamos também a mesma assinatura sem exigir a natureza textual,
# porque a direção já foi inferida pelo valor/conta bancária.
old_candidates = '''            candidatos = candidatos_por_banco.get(banco_linha, {}).get(assinatura, set())
            conta_segura = mapas_seguros.get(banco_linha, {}).get(assinatura)
'''
new_candidates = '''            candidatos_banco = candidatos_por_banco.get(banco_linha, {})
            mapas_banco = mapas_seguros.get(banco_linha, {})
            candidatos = candidatos_banco.get(assinatura, set())
            conta_segura = mapas_banco.get(assinatura)

            # Quando a base foi aprendida a partir de histórico cru da Autokraft,
            # a assinatura fica "outro|...". Mantemos o restante da assinatura e
            # localizamos esse padrão também.
            if not candidatos and assinatura:
                partes_assinatura = assinatura.split('|', 1)
                sufixo_assinatura = partes_assinatura[1] if len(partes_assinatura) > 1 else ''
                assinatura_outro = f"outro|{sufixo_assinatura}" if sufixo_assinatura else assinatura
                candidatos = candidatos_banco.get(assinatura_outro, set())
                conta_segura = mapas_banco.get(assinatura_outro)
'''
if text.count(old_candidates) != 1:
    raise SystemExit(f'Bloco de candidatos encontrado {text.count(old_candidates)} vezes.')
text = text.replace(old_candidates, new_candidates, 1)

# Validações específicas para o comportamento solicitado.
checks = [
    "'contas_bancarias': {'itau': '508', 'daycoval': '2283'}",
    "'contas_bancarias': {'itau': '508', 'daycoval': '505'}",
    "'contas_bancarias': {'itau': '508', 'daycoval': '506'}",
    "col_valor = mapa_colunas.get('valor')",
    "if valor_linha < 0:",
    "natureza = 'pago'",
    "natureza = 'recebido'",
    "if credito_item == conta_banco_item",
    "if banco_linha not in contas_bancarias:",
]
for check in checks:
    if check not in text:
        raise SystemExit(f'Validação falhou: não encontrei {check!r}.')

path.write_text(text, encoding='utf-8')
print('Classificação Autokraft corrigida: conta bancária pelo sinal do VALOR e base inteligente pela conta conhecida.')
