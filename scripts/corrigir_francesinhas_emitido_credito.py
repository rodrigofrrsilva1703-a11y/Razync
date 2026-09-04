from pathlib import Path

# 1) Francesinha: DATA = Emitido em; VALOR = Crédito/Débito.
p = Path('razync/eletro_forte_francesinhas.py')
s = p.read_text(encoding='utf-8')
old = '''        # A coluna VALOR da francesinha é o valor nominal do título. O campo\n        # final (crédito) pode vir líquido de pequenos ajustes/tarifas e, por isso,\n        # não deve substituir o valor do lançamento no Modelo Domínio.\n        valor_titulo = _valor_br(encontrado.group("valor"))\n        if valor_titulo <= 0:\n            continue\n\n        # A data correta do lançamento é a data de liquidação indicada logo após\n        # o histórico L, e não a data em que o relatório foi emitido.\n        dia_mes = encontrado.group("data_liquidacao")\n        ano_liquidacao = int(data_emissao.year)\n        data_liquidacao = pd.to_datetime(\n            f"{dia_mes}/{ano_liquidacao}", dayfirst=True, errors="raise"\n        )\n        # Proteção para relatórios emitidos no começo de janeiro contendo\n        # liquidações dos últimos dias de dezembro do ano anterior.\n        if data_liquidacao > data_emissao + pd.Timedelta(days=31):\n            data_liquidacao = data_liquidacao.replace(year=ano_liquidacao - 1)\n\n        registros.append({\n            "DESCRIÇÃO": "BANCO ITAÚ",\n            "DATA": data_liquidacao,\n            "VALOR": valor_titulo,\n'''
new = '''        # Regra da empresa 242: o lançamento usa o valor efetivamente\n        # creditado pelo Itaú (coluna Crédito/Débito), inclusive quando houver\n        # desconto no título. Ex.: 3.478,06 - 2.773,80 = 704,26.\n        valor_creditado = _valor_br(encontrado.group("credito"))\n        if valor_creditado <= 0:\n            continue\n\n        # A data contábil definida para as francesinhas da 242 é a data\n        # "Emitido em" do relatório, não o Dia/mês da liquidação.\n        registros.append({\n            "DESCRIÇÃO": "BANCO ITAÚ",\n            "DATA": data_emissao,\n            "VALOR": valor_creditado,\n'''
if old not in s:
    raise SystemExit('Bloco da francesinha não encontrado')
s = s.replace(old, new, 1)
s = s.replace('"""Extrai apenas liquidações L e usa a data de emissão do relatório."""', '"""Extrai liquidações L usando Emitido em e Crédito/Débito."""', 1)
p.write_text(s, encoding='utf-8')

# 2) Correção dos recebidos: tolera 1 centavo e corrige também o valor.
p = Path('razync/eletro_forte.py')
s = p.read_text(encoding='utf-8')
s = s.replace('''                valor_linha = round(float(linha.get("VALOR", 0) or 0), 2)\n                if valor_linha != valor_correto:\n                    continue\n''', '''                valor_linha = round(float(linha.get("VALOR", 0) or 0), 2)\n                # Alguns relatórios recebidos podem vir com diferença de 1 centavo\n                # em relação à francesinha. A francesinha é a fonte de verdade.\n                if abs(valor_linha - valor_correto) > 0.01:\n                    continue\n''', 1)
s = s.replace('''                grupo.at[indice, "DATA"] = data_correta\n                usados.add((conta, indice))\n''', '''                grupo.at[indice, "DATA"] = data_correta\n                grupo.at[indice, "VALOR"] = valor_correto\n                usados.add((conta, indice))\n''', 1)
s = s.replace('''    """Corrige somente a data de recebimentos conciliados com liquidações L."""''', '''    """Corrige data e, quando necessário, até 1 centavo pelo valor da francesinha."""''', 1)
p.write_text(s, encoding='utf-8')

print('correção final das francesinhas 242 aplicada')
