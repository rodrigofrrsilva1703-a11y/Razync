from pathlib import Path

p = Path('app_legacy.py')
s = p.read_text(encoding='utf-8')
old = '''        # Empresas 266 e 1396 (Nova Geração): o status do lançamento já vem no
        # campo LACTO e não deve poluir o histórico do Modelo Domínio. Mantemos
        # somente a informação útil da origem + documento e removemos também
        # eventual prefixo já gravado no próprio histórico de origem.
        historico_final = re.sub(r'\\s+', ' ', " ".join(
            parte for parte in [historico_origem, documento] if parte
        )).strip()
        historico_final = re.sub(
            r'^(?:(?:Pago|Recebido)\\s*:\\s*|(?:PAGO|RECEBIDO)\\s+)+',
            '',
            historico_final,
            flags=re.IGNORECASE,
        ).strip()
'''
new = '''        # Empresas 266 e 1396 (Nova Geração): preserva o PAGO/RECEBIDO que já
        # vem do campo LACTO, mas não adiciona o prefixo extra "Pago:"/"Recebido:".
        # Se o histórico de origem já vier com esse prefixo com dois-pontos,
        # removemos apenas ele para evitar duplicidade como "PAGO Pago: ...".
        historico_origem_limpo = re.sub(
            r'^(?:Pago|Recebido)\\s*:\\s*',
            '',
            historico_origem,
            flags=re.IGNORECASE,
        ).strip()
        historico_final = re.sub(r'\\s+', ' ', " ".join(
            parte for parte in [lacto, historico_origem_limpo, documento] if parte
        )).strip()
'''
if old not in s:
    raise SystemExit('Bloco esperado da Nova Geração não encontrado')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('Histórico 266/1396 ajustado para preservar PAGO/RECEBIDO do LACTO sem prefixo extra.')
