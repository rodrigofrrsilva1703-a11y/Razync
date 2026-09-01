from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old_sort = '''                empresas_encontradas.sort(\n                    key=lambda empresa: (\n                        prioridades_empresas[str(empresa['codigo'])]['ordem'],\n                        prioridades_empresas[str(empresa['codigo'])]['vencimento'],\n                        int(empresa['codigo']),\n                    )\n                )\n                st.markdown(\n                    '<div class="rz-company-section">Resultados por prioridade</div>',\n                    unsafe_allow_html=True,\n                )\n'''
new_sort = '''                def _relevancia_busca_empresa(empresa):\n                    codigo = str(empresa['codigo'])\n                    nome = _normalizar_busca_empresa(empresa['nome'])\n                    termo = termo_normalizado\n                    if termo == codigo:\n                        return (0, int(codigo))\n                    if termo == nome:\n                        return (1, int(codigo))\n                    if codigo.startswith(termo):\n                        return (2, int(codigo))\n                    if nome.startswith(termo):\n                        return (3, int(codigo))\n                    return (4, int(codigo))\n\n                # A busca serve para acessar ferramentas. O status da tarefa mensal\n                # não pode esconder nem rebaixar uma empresa concluída.\n                empresas_encontradas.sort(key=_relevancia_busca_empresa)\n                st.markdown(\n                    '<div class="rz-company-section">Resultados da pesquisa</div>',\n                    unsafe_allow_html=True,\n                )\n'''

if old_sort not in text:
    raise SystemExit('Bloco de ordenação da pesquisa não encontrado.')
text = text.replace(old_sort, new_sort, 1)

# O app contém apenas um bloco ativo dessa busca; se houver cópia idêntica adicional,
# corrige também para evitar regressão em versões duplicadas do trecho.
if old_sort in text:
    text = text.replace(old_sort, new_sort, 1)

path.write_text(text, encoding='utf-8')
print('Busca desacoplada do status de conclusão das tarefas.')
