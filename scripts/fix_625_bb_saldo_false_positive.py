from pathlib import Path
p=Path('razync/valean_625.py')
s=p.read_text(encoding='utf-8')
old='''        historico = " ".join([antes] + complementos).strip()\n        if "saldo" in _normalizar(historico):\n            continue\n        registros.append(_registro("banco_brasil", data, valor, historico))\n'''
new='''        historico = " ".join([antes] + complementos).strip()\n        # Não descarte um lançamento só porque um complemento contém a palavra\n        # "saldo" (ex.: "IOF Saldo Devedor Conta"). Somente a descrição principal\n        # da própria linha bancária pode caracterizar uma linha de saldo.\n        principal_bb = re.sub(r"[^a-z]", "", _normalizar(antes))\n        if principal_bb in {"saldo", "saldoanterior"} or principal_bb.endswith("saldo"):\n            continue\n        registros.append(_registro("banco_brasil", data, valor, historico))\n'''
if old not in s:
    raise SystemExit('trecho alvo não encontrado')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
