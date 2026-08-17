from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

# 1) openpyxl já é importado localmente nas rotinas que precisam dele.
linhas_openpyxl = [
    linha for linha in s.splitlines()
    if 'openpyxl' in linha and not linha.strip().startswith('import openpyxl')
    and not linha.strip().startswith('from openpyxl import')
    and "engine='openpyxl'" not in linha and 'engine="openpyxl"' not in linha
]
if not linhas_openpyxl:
    s = s.replace('import openpyxl\n', '', 1)

# 2) Cache do leitor central: evita reler PDF/OFX/Excel inteiro em cada rerun.
alvo_extrato = "def processar_extrato_unificado(file_bytes, filename):\n"
if '@st.cache_data(show_spinner=False, max_entries=12)\ndef processar_extrato_unificado' not in s:
    if alvo_extrato not in s:
        raise SystemExit('processar_extrato_unificado não encontrado')
    s = s.replace(
        alvo_extrato,
        '@st.cache_data(show_spinner=False, max_entries=12)\n' + alvo_extrato,
        1
    )

# 3) Cache curto da Base Inteligente. Mantém rede fora dos reruns repetidos.
alvo_base = "def carregar_classificacoes_online(empresa='nova_geracao'):\n"
if "@st.cache_data(show_spinner=False, ttl=120, max_entries=20)\ndef carregar_classificacoes_online" not in s:
    if alvo_base not in s:
        raise SystemExit('carregar_classificacoes_online não encontrado')
    s = s.replace(
        alvo_base,
        "@st.cache_data(show_spinner=False, ttl=120, max_entries=20)\n" + alvo_base,
        1
    )

# 4) Após DELETE, invalida o cache para não mostrar padrões apagados.
alvo_delete = """    requisicao_classificacao_online(\n        caminho,\n        metodo='DELETE',\n        prefer='return=minimal'\n    )\n    return len(existentes)\n"""
novo_delete = """    requisicao_classificacao_online(\n        caminho,\n        metodo='DELETE',\n        prefer='return=minimal'\n    )\n    carregar_classificacoes_online.clear()\n    return len(existentes)\n"""
if alvo_delete in s:
    s = s.replace(alvo_delete, novo_delete, 1)
elif 'carregar_classificacoes_online.clear()\n    return len(existentes)' not in s:
    raise SystemExit('Ponto de invalidação após DELETE não encontrado')

# 5) Após UPSERT, invalida o cache para a próxima leitura buscar a base atualizada.
alvo_save = """    for inicio in range(0, len(registros), 500):\n        requisicao_classificacao_online(\n            'classificacoes_bancarias?on_conflict=id',\n            metodo='POST',\n            dados=registros[inicio:inicio + 500],\n            prefer='resolution=merge-duplicates,return=minimal'\n        )\n    return len(registros)\n"""
novo_save = """    for inicio in range(0, len(registros), 500):\n        requisicao_classificacao_online(\n            'classificacoes_bancarias?on_conflict=id',\n            metodo='POST',\n            dados=registros[inicio:inicio + 500],\n            prefer='resolution=merge-duplicates,return=minimal'\n        )\n    carregar_classificacoes_online.clear()\n    return len(registros)\n"""
if alvo_save in s:
    s = s.replace(alvo_save, novo_save, 1)
elif 'carregar_classificacoes_online.clear()\n    return len(registros)' not in s:
    raise SystemExit('Ponto de invalidação após UPSERT não encontrado')

# 6) Cache da geração do Modelo Domínio: evita recriar o XLSX em todo rerun.
alvo_excel = 'def gerar_excel_modelo_dominio(df):\n'
if '@st.cache_data(show_spinner=False, max_entries=8)\ndef gerar_excel_modelo_dominio' not in s:
    if alvo_excel not in s:
        raise SystemExit('gerar_excel_modelo_dominio não encontrado')
    s = s.replace(
        alvo_excel,
        '@st.cache_data(show_spinner=False, max_entries=8)\n' + alvo_excel,
        1
    )

checks = [
    '@st.cache_data(show_spinner=False, max_entries=12)\ndef processar_extrato_unificado',
    "@st.cache_data(show_spinner=False, ttl=120, max_entries=20)\ndef carregar_classificacoes_online",
    'carregar_classificacoes_online.clear()',
    '@st.cache_data(show_spinner=False, max_entries=8)\ndef gerar_excel_modelo_dominio',
]
for check in checks:
    if check not in s:
        raise SystemExit(f'Validação falhou: {check}')

p.write_text(s, encoding='utf-8')
print('Performance V16 aplicada com caches seguros e invalidação da Base Inteligente.')
