from pathlib import Path
p=Path('razync/valean_625.py')
s=p.read_text(encoding='utf-8')
old='''        movimento = valores[0]\n        valor = _valor_br(movimento.group(1), movimento.group(2))\n        antes = primeira[10:movimento.start()]\n'''
new='''        movimento = valores[0]\n        valor = _valor_br(movimento.group(1), movimento.group(2))\n        antes_bruto = primeira[10:movimento.start()]\n        antes_bruto_norm = _normalizar(antes_bruto)\n        # Filtra saldo anterior e saldos diarios diretamente no trecho bruto do BB,\n        # antes de remover codigos/documento. Isso evita falsos negativos causados\n        # pelos codigos 0000/00000/000 ou 999 antes de SALDO/S A L D O.\n        if re.search(r"\\bsaldo anterior\\b", antes_bruto_norm):\n            continue\n        if re.search(r"(?:^|\\s)s\\s*a\\s*l\\s*d\\s*o\\s*$", antes_bruto_norm):\n            continue\n        antes = antes_bruto\n'''
if old not in s: raise SystemExit('trecho inicial BB não encontrado')
s=s.replace(old,new,1)
# remove bloco antigo de filtro tardio para não duplicar lógica
start='''        # Descarta os saldos contábeis exibidos pelo BB (saldo anterior e saldos\n        # diários), mas preserva lançamentos reais cujo complemento menciona saldo,\n        # como "Cobrança de I.O.F. ... IOF Saldo Devedor Conta".\n        hist_norm = _normalizar(historico)\n        antes_norm = _normalizar(antes)\n        eh_saldo_bb = (\n            re.fullmatch(r"s ?a ?l ?d ?o(?: anterior)?", antes_norm or "") is not None\n            or re.fullmatch(r"saldo anterior", antes_norm or "") is not None\n            or (not antes_norm and re.fullmatch(r"s ?a ?l ?d ?o(?: anterior)?", hist_norm or "") is not None)\n        )\n        if eh_saldo_bb:\n            continue\n'''
s=s.replace(start,'',1)
p.write_text(s,encoding='utf-8')
