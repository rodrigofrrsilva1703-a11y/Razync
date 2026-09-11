from pathlib import Path
p=Path('razync/valean_625.py')
s=p.read_text(encoding='utf-8')
old='''        # Só descarta linhas que são efetivamente saldo. Complementos como\n        # "IOF Saldo Devedor Conta" pertencem a lançamentos válidos e devem ficar.\n        hist_norm = _normalizar(historico)\n        if re.fullmatch(r"(?:s ?a ?l ?d ?o|saldo anterior)(?:\\s+.*)?", hist_norm):\n            continue\n        registros.append(_registro("banco_brasil", data, valor, historico))\n'''
new='''        # Descarta os saldos contábeis exibidos pelo BB (saldo anterior e saldos\n        # diários), mas preserva lançamentos reais cujo complemento menciona saldo,\n        # como "Cobrança de I.O.F. ... IOF Saldo Devedor Conta".\n        hist_norm = _normalizar(historico)\n        antes_norm = _normalizar(antes)\n        eh_saldo_bb = (\n            re.fullmatch(r"s ?a ?l ?d ?o(?: anterior)?", antes_norm or "") is not None\n            or re.fullmatch(r"saldo anterior", antes_norm or "") is not None\n            or (not antes_norm and re.fullmatch(r"s ?a ?l ?d ?o(?: anterior)?", hist_norm or "") is not None)\n        )\n        if eh_saldo_bb:\n            continue\n        registros.append(_registro("banco_brasil", data, valor, historico))\n'''
if old not in s: raise SystemExit('trecho esperado não encontrado')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
