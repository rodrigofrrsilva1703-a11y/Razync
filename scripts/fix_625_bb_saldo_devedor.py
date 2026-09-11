from pathlib import Path
p=Path('razync/valean_625.py')
s=p.read_text(encoding='utf-8')
old='''        historico = " ".join([antes] + complementos).strip()\n        if "saldo" in _normalizar(historico):\n            continue\n        registros.append(_registro("banco_brasil", data, valor, historico))\n'''
new='''        historico = " ".join([antes] + complementos).strip()\n        # Só descarta linhas que são efetivamente saldo. Complementos como\n        # "IOF Saldo Devedor Conta" pertencem a lançamentos válidos e devem ficar.\n        hist_norm = _normalizar(historico)\n        if re.fullmatch(r"(?:s ?a ?l ?d ?o|saldo anterior)(?:\\s+.*)?", hist_norm):\n            continue\n        registros.append(_registro("banco_brasil", data, valor, historico))\n'''
if old not in s:
    raise SystemExit('trecho antigo não encontrado')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
