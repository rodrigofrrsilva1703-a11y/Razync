from pathlib import Path

p = Path('razync/eletro_forte_francesinhas.py')
s = p.read_text(encoding='utf-8')

old = '''    padrao_linha = re.compile(
        r"^\\s*\\d{3}\\s+\\S+\\s+\\S+\\s+"
        r"(?P<pagador>.+?)\\s+\\d{4}\\s+\\d{2}/\\d{2}/\\d{2}\\s+"
        r"(?P<valor>[\\d.]+,\\d{2})\\s+L\\s+\\d{2}/\\d{2}"
        r"(?:\\s+\\d{2}\\s+[\\d.]+,\\d{2})?\\s+"
        r"(?P<credito>[\\d.]+,\\d{2})\\s*$"
    )
'''
new = '''    padrao_linha = re.compile(
        r"^\\s*\\d{3}\\s+\\S+\\s+\\S+\\s+"
        r"(?P<pagador>.+?)\\s+\\d{4}\\s+\\d{2}/\\d{2}/\\d{2}\\s+"
        r"(?P<valor>[\\d.]+,\\d{2})\\s+L\\s+(?P<data_liquidacao>\\d{2}/\\d{2})"
        r"(?:\\s+\\d{2}\\s+[\\d.]+,\\d{2})?\\s+"
        r"(?P<credito>[\\d.]+,\\d{2})\\s*$"
    )
'''
if old not in s:
    raise SystemExit('Bloco padrao_linha não encontrado')
s = s.replace(old, new, 1)

old2 = '''        valor_creditado = _valor_br(encontrado.group("credito"))
        if valor_creditado <= 0:
            continue
        registros.append({
            "DESCRIÇÃO": "BANCO ITAÚ",
            "DATA": data_emissao,
            "VALOR": valor_creditado,
'''
new2 = '''        # A coluna VALOR da francesinha é o valor nominal do título. O campo
        # final (crédito) pode vir líquido de pequenos ajustes/tarifas e, por isso,
        # não deve substituir o valor do lançamento no Modelo Domínio.
        valor_titulo = _valor_br(encontrado.group("valor"))
        if valor_titulo <= 0:
            continue

        # A data correta do lançamento é a data de liquidação indicada logo após
        # o histórico L, e não a data em que o relatório foi emitido.
        dia_mes = encontrado.group("data_liquidacao")
        ano_liquidacao = int(data_emissao.year)
        data_liquidacao = pd.to_datetime(
            f"{dia_mes}/{ano_liquidacao}", dayfirst=True, errors="raise"
        )
        # Proteção para relatórios emitidos no começo de janeiro contendo
        # liquidações dos últimos dias de dezembro do ano anterior.
        if data_liquidacao > data_emissao + pd.Timedelta(days=31):
            data_liquidacao = data_liquidacao.replace(year=ano_liquidacao - 1)

        registros.append({
            "DESCRIÇÃO": "BANCO ITAÚ",
            "DATA": data_liquidacao,
            "VALOR": valor_titulo,
'''
if old2 not in s:
    raise SystemExit('Bloco valor/data não encontrado')
s = s.replace(old2, new2, 1)

p.write_text(s, encoding='utf-8')
print('Francesinhas 242 corrigidas: valor nominal + data de liquidação')
