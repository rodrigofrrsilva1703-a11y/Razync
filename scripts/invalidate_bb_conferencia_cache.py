from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
old="""def processar_extrato_conferencia_empresa(file_bytes, filename):\n    \"\"\"Lê a conferência pelo mesmo motor central usado em todo o Razync.\"\"\"\n    termos_saldo = [\n"""
new="""def processar_extrato_conferencia_empresa(file_bytes, filename):\n    \"\"\"Lê a conferência pelo mesmo motor central usado em todo o Razync.\"\"\"\n    # Versão do parser para invalidar resultados antigos do cache quando a regra\n    # de leitura do BB Autorizável mudar.\n    _parser_conferencia_version = 'bb-rende-facil-v2'\n    termos_saldo = [\n"""
if old not in s:
    raise SystemExit('função de conferência não encontrada')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
