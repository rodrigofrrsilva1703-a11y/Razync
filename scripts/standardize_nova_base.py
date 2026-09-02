from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
start = "        with aba_base_inteligente:\n            if erro_base_classificacoes:"
end = "\n        with aba_operacoes:"
idx = s.find(start)
if idx == -1:
    raise SystemExit('Bloco antigo da Base Inteligente da Nova Geração não encontrado')
end_idx = s.find(end, idx)
if end_idx == -1:
    raise SystemExit('Fim do bloco da Base Inteligente da Nova Geração não encontrado')
new = '''        with aba_base_inteligente:\n            renderizar_base_inteligente_empresa(\n                empresa_base_nova,\n                nome_base_nova,\n                set(contas_dominio_estabelecimento.keys()),\n                contas_dominio_estabelecimento,\n            )\n'''
s = s[:idx] + new + s[end_idx:]
p.write_text(s, encoding='utf-8')

# trigger apply workflow
