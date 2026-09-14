from pathlib import Path

mod = Path('razync/valean_626.py')
text = mod.read_text(encoding='utf-8')

old = '''    moeda = re.compile(r"(\\d{1,3}(?:\\.\\d{3})*,\\d{2})\\s*([CD])", re.I)
    registros = []
    for bloco in blocos:
'''
new = '''    moeda = re.compile(r"(\\d{1,3}(?:\\.\\d{3})*,\\d{2})\\s*([CD])", re.I)
    registros = []
    saldo_extrato = None
    data_saldo_extrato = pd.NaT
    for bloco in blocos:
'''
if old not in text:
    raise SystemExit('marcador registros BB não encontrado')
text = text.replace(old, new, 1)

old = '''        movimento = valores[0]
        valor = _valor_br(movimento.group(1), movimento.group(2))
        antes_bruto = primeira[10:movimento.start()]
'''
new = '''        movimento = valores[0]
        valor = _valor_br(movimento.group(1), movimento.group(2))
        antes_bruto = primeira[10:movimento.start()]

        # O BB imprime o saldo da conta como um valor adicional na mesma linha
        # de alguns movimentos (especialmente no fechamento do dia/período).
        # Guardamos sempre o saldo da data mais recente para exibir o saldo real
        # do extrato, sem transformar esse valor em lançamento contábil.
        if len(valores) >= 2:
            saldo_match = valores[-1]
            saldo_candidato = _valor_br(saldo_match.group(1), saldo_match.group(2))
            if pd.isna(data_saldo_extrato) or data >= data_saldo_extrato:
                saldo_extrato = saldo_candidato
                data_saldo_extrato = data
'''
if old not in text:
    raise SystemExit('marcador movimento BB não encontrado')
text = text.replace(old, new, 1)

old = '''        if tem_saldo:
            continue
'''
new = '''        if tem_saldo:
            # Em alguns layouts a linha 999/SALDO contém apenas o saldo final.
            # Capturamos esse valor, mas a linha continua fora do Modelo Domínio.
            if valores:
                saldo_match = valores[-1]
                saldo_candidato = _valor_br(saldo_match.group(1), saldo_match.group(2))
                if pd.isna(data_saldo_extrato) or data >= data_saldo_extrato:
                    saldo_extrato = saldo_candidato
                    data_saldo_extrato = data
            continue
'''
if old not in text:
    raise SystemExit('marcador tem_saldo não encontrado')
text = text.replace(old, new, 1)

old = '''    return _finalizar(registros, "Banco do Brasil")
'''
new = '''    resultado = _finalizar(registros, "Banco do Brasil")
    if saldo_extrato is not None:
        resultado.attrs["saldo_extrato"] = round(float(saldo_extrato), 2)
        resultado.attrs["data_saldo_extrato"] = pd.Timestamp(data_saldo_extrato)
    return resultado
'''
if old not in text:
    raise SystemExit('retorno BB não encontrado')
text = text.replace(old, new, 1)

old = '''    resultado = pd.concat(quadros, ignore_index=True)
    resultado = resultado.drop_duplicates(subset=["DATA", "VALOR", "HISTÓRICO"], keep="first")
    return resultado.sort_values("DATA", kind="stable").reset_index(drop=True)
'''
new = '''    # Preserva o saldo real do extrato mais recente quando vários períodos são
    # processados juntos. Esse saldo é apenas informativo e não vira lançamento.
    saldos = []
    for quadro in quadros:
        saldo = quadro.attrs.get("saldo_extrato")
        data_saldo = quadro.attrs.get("data_saldo_extrato")
        if saldo is not None and data_saldo is not None:
            saldos.append((pd.Timestamp(data_saldo), float(saldo)))

    resultado = pd.concat(quadros, ignore_index=True)
    resultado = resultado.drop_duplicates(subset=["DATA", "VALOR", "HISTÓRICO"], keep="first")
    resultado = resultado.sort_values("DATA", kind="stable").reset_index(drop=True)
    if saldos:
        data_saldo, saldo = max(saldos, key=lambda item: item[0])
        resultado.attrs["saldo_extrato"] = round(saldo, 2)
        resultado.attrs["data_saldo_extrato"] = data_saldo
    return resultado
'''
if old not in text:
    raise SystemExit('consolidação 626 não encontrada')
text = text.replace(old, new, 1)
mod.write_text(text, encoding='utf-8')

legacy = Path('app_legacy.py')
text = legacy.read_text(encoding='utf-8')
old = '''            saldo = entradas - saidas

            card_ent, card_sai, card_saldo = st.columns(3)
'''
new = '''            saldo_calculado = entradas - saidas
            # Alguns parsers bancários preservam o saldo final oficial do extrato
            # em DataFrame.attrs. Quando disponível, ele é mais correto que apenas
            # Entradas - Saídas, pois considera o saldo inicial do período.
            try:
                saldo = float(df_banco.attrs.get('saldo_extrato', saldo_calculado))
            except (TypeError, ValueError):
                saldo = saldo_calculado

            card_ent, card_sai, card_saldo = st.columns(3)
'''
if old not in text:
    raise SystemExit('helper de prévia não encontrado')
text = text.replace(old, new, 1)
legacy.write_text(text, encoding='utf-8')

# valida sintaxe
compile(mod.read_text(encoding='utf-8'), str(mod), 'exec')
compile(legacy.read_text(encoding='utf-8'), str(legacy), 'exec')
