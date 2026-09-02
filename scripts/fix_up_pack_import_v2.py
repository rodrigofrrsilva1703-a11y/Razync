from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
old = 'from razync.companies import CONFIGURACOES_AUTOKRAFT, CONFIGURACOES_ACCEDE, CONFIGURACOES_UP_PACK\n'
new = 'from razync.companies import CONFIGURACOES_AUTOKRAFT, CONFIGURACOES_ACCEDE\n'
if old not in s:
    raise SystemExit('Import atual da UP PACK não encontrado')
s = s.replace(old, new, 1)
anchor = 'from razync.up_pack import identificar_banco_up_pack, processar_planilha_up_pack\n'
config = '''\n# Configuração local da UP PACK para evitar falha de import em hot-reload do Streamlit Cloud.\nCONFIGURACOES_UP_PACK = {\n    "up_pack": {\n        "empresa": "1096 - UP PACK BRAZIL EIRELI EPP",\n        "slug": "up_pack",\n        "arquivo": "UP_PACK_Brazil",\n        "contas_bancarias": {"santander": "513", "sicredi": "510"},\n    }\n}\n'''
if 'Configuração local da UP PACK' not in s:
    if anchor not in s:
        raise SystemExit('Import do processador UP PACK não encontrado')
    s = s.replace(anchor, anchor + config, 1)
p.write_text(s, encoding='utf-8')
# trigger
