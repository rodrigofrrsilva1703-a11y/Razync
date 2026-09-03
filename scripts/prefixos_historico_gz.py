from pathlib import Path
p=Path('razync/gz_1211.py')
s=p.read_text(encoding='utf-8')
old='''        registros.append({\n            "DESCRIÇÃO": "BANCO ITAÚ",\n            "DATA": data,\n            "VALOR": round(valor, 2),\n            "DÉBITO": CONTA_ITAU_GZ if valor > 0 else "",\n            "CRÉDITO": CONTA_ITAU_GZ if valor < 0 else "",\n            "HISTÓRICO": historico,\n        })'''
new='''        historico_sem_prefixo = re.sub(\n            r"^(?:Pago|Recebido):\\s*", "", historico, flags=re.I\n        ).strip()\n        prefixo = "Recebido: " if valor > 0 else "Pago: "\n        registros.append({\n            "DESCRIÇÃO": "BANCO ITAÚ",\n            "DATA": data,\n            "VALOR": round(valor, 2),\n            "DÉBITO": CONTA_ITAU_GZ if valor > 0 else "",\n            "CRÉDITO": CONTA_ITAU_GZ if valor < 0 else "",\n            "HISTÓRICO": prefixo + historico_sem_prefixo,\n        })'''
if old not in s: raise SystemExit('bloco alvo não encontrado')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
t=p.read_text(encoding='utf-8')
assert 'prefixo = "Recebido: " if valor > 0 else "Pago: "' in t
assert '"HISTÓRICO": f"Recebido: {boleto.pagador}"' in t
print('prefixos GZ aplicados')
