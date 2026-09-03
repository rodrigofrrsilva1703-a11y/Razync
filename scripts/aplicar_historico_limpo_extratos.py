from pathlib import Path

# GZ 1211: limpar no ponto final do parser, mantendo BOLETOS RECEBIDOS reconhecível.
p=Path('razync/gz_1211.py'); s=p.read_text(encoding='utf-8')
imp='from razync.history_cleaning import limpar_historico_extrato\n'
if imp not in s:
    s=s.replace('from pypdf import PdfReader\n', 'from pypdf import PdfReader\n'+imp, 1)
old='''        historico_sem_prefixo = re.sub(\n            r"^(?:Pago|Recebido):\\s*", "", historico, flags=re.I\n        ).strip()\n        prefixo = "Recebido: " if valor > 0 else "Pago: "\n'''
new='''        historico_final = limpar_historico_extrato(historico, valor)\n'''
if old not in s: raise SystemExit('GZ bloco não encontrado')
s=s.replace(old,new,1).replace('"HISTÓRICO": prefixo + historico_sem_prefixo,','"HISTÓRICO": historico_final,',1)
p.write_text(s,encoding='utf-8')

# Santander empresarial: usado por empresas que recebem extrato Santander PDF.
p=Path('razync/santander_statement.py'); s=p.read_text(encoding='utf-8')
if imp not in s:
    s=s.replace('from typing import List, Dict, Any\n', 'from typing import List, Dict, Any\n\n'+imp,1)
s=s.replace('"HISTÓRICO": historico,','"HISTÓRICO": limpar_historico_extrato(historico, valor),',1)
p.write_text(s,encoding='utf-8')

# Bradesco Radani: limpeza no lançamento, sem mexer na leitura/validação dos valores.
p=Path('razync/bradesco_radani.py'); s=p.read_text(encoding='utf-8')
if imp not in s:
    s=s.replace('import pandas as pd\n', 'import pandas as pd\n\n'+imp,1)
s=s.replace('"HISTÓRICO": historico,','"HISTÓRICO": limpar_historico_extrato(historico, valor),',1)
p.write_text(s,encoding='utf-8')

# Radani: comprovantes SISPAG detalhados também recebem Pago/Recebido sem poluir nome.
p=Path('razync/radani.py'); s=p.read_text(encoding='utf-8')
if imp not in s:
    s=s.replace('from pypdf import PdfReader\n', 'from pypdf import PdfReader\n\n'+imp,1)
# Detalhes dos comprovantes são nomes reais e devem manter o texto, só com natureza.
s=s.replace('novo["HISTÓRICO"] = str(det["HISTÓRICO"])','novo["HISTÓRICO"] = limpar_historico_extrato(str(det["HISTÓRICO"]), float(det["VALOR"]))',1)
# Movimentos originais que entram na saída: limpar no append sem afetar matching anterior.
s=s.replace('saida.append(mov.to_dict())','''mov_limpo = mov.to_dict()\n        mov_limpo["HISTÓRICO"] = limpar_historico_extrato(hist, valor)\n        saida.append(mov_limpo)''')
p.write_text(s,encoding='utf-8')

# Testes existentes: nova política explícita.
p=Path('tests/test_santander_statement.py'); s=p.read_text(encoding='utf-8')
s += '''\n\ndef test_santander_historico_limpo_com_natureza():\n    texto = """Santander\\nInternet Banking Empresarial\\nSaldo do dia R$ 1,00\\n01/07/2026 Pix Enviado JOSE SILVA - R$ 10,00\\n01/07/2026 Rendimento Liquido De Contamax R$ 0,10"""\n    itens = processar_extrato_santander_empresarial_texto(texto)\n    assert itens[0]["HISTÓRICO"] == "Pago: JOSE SILVA"\n    assert itens[1]["HISTÓRICO"] == "Recebido: RENDIMENTOS"\n'''
p.write_text(s,encoding='utf-8')

p=Path('tests/test_radani.py'); s=p.read_text(encoding='utf-8')
s=s.replace("assert res.organizado.iloc[0]['HISTÓRICO'] == 'SISPAG SALARIOS'", "assert res.organizado.iloc[0]['HISTÓRICO'] == 'Pago: SISPAG SALARIOS'")
s=s.replace("assert res.organizado.iloc[0]['HISTÓRICO'].startswith('PIX ENVIADO')", "assert res.organizado.iloc[0]['HISTÓRICO'] == 'Pago: JOSE CLAUDIO'")
p.write_text(s,encoding='utf-8')
print('padronização aplicada')
