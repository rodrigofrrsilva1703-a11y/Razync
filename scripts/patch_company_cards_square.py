from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

# 1) Adiciona exclusão explícita por empresa no Supabase.
marker = '''def salvar_classificacoes_online(registros, empresa='nova_geracao'):\n'''
helper = '''def apagar_classificacoes_online(empresa):\n    """Remove todos os padrões de uma empresa específica da base online."""\n    if not empresa:\n        return 0\n    existentes = carregar_classificacoes_online(empresa)\n    if not existentes:\n        return 0\n    caminho = (\n        'classificacoes_bancarias?empresa=eq.'\n        + urllib.parse.quote(empresa)\n    )\n    requisicao_classificacao_online(\n        caminho,\n        metodo='DELETE',\n        prefer='return=minimal'\n    )\n    return len(existentes)\n\n'''
if marker not in text:
    raise SystemExit('Função salvar_classificacoes_online não encontrada.')
text = text.replace(marker, helper + marker, 1)

# 2) A Nova Geração deixa de usar a chave compartilhada e passa a usar uma chave por estabelecimento.
old_after_radio = '''        chave_estabelecimento = normalizar_texto(estabelecimento_nova)\n        if chave_estabelecimento == 'filial':\n'''
new_after_radio = '''        chave_estabelecimento = normalizar_texto(estabelecimento_nova)\n        empresa_base_nova = (\n            'nova_geracao_filial'\n            if chave_estabelecimento == 'filial'\n            else 'nova_geracao_matriz'\n        )\n        nome_base_nova = (\n            '266 - Nova Geração Filial'\n            if chave_estabelecimento == 'filial'\n            else '266 - Nova Geração Matriz'\n        )\n        if chave_estabelecimento == 'filial':\n'''
if text.count(old_after_radio) != 1:
    raise SystemExit(f'Bloco após seleção Matriz/Filial encontrado {text.count(old_after_radio)} vezes.')
text = text.replace(old_after_radio, new_after_radio, 1)

# 3) Carrega somente a base da área selecionada.
old_load = "                base_classificacoes = carregar_classificacoes_online('nova_geracao')\n"
new_load = "                base_classificacoes = carregar_classificacoes_online(empresa_base_nova)\n"
if text.count(old_load) != 1:
    raise SystemExit(f'Carregamento compartilhado encontrado {text.count(old_load)} vezes.')
text = text.replace(old_load, new_load, 1)

# 4) Limpa automaticamente a base antiga compartilhada uma única vez.
# A limpeza só roda quando ela ainda contém registros; depois fica inócua.
old_before_tabs = '''        aba_operacoes, aba_base_inteligente = st.tabs([\n            "Organizar e conferir",\n            "Base inteligente de Débito e Crédito"\n        ])\n'''
new_before_tabs = '''        # Migração: a antiga base compartilhada não deve mais alimentar Matriz ou Filial.\n        # Com a service role já configurada, ela é apagada automaticamente na primeira\n        # abertura após esta atualização. As duas novas bases começam vazias.\n        if url_base_classificacao and chave_base_classificacao:\n            try:\n                if not st.session_state.get('_nova_geracao_base_legada_verificada'):\n                    apagar_classificacoes_online('nova_geracao')\n                    st.session_state['_nova_geracao_base_legada_verificada'] = True\n            except Exception as erro_limpeza_legada:\n                st.session_state['_nova_geracao_erro_limpeza_legada'] = str(\n                    erro_limpeza_legada\n                )\n\n        aba_operacoes, aba_base_inteligente = st.tabs([\n            "Organizar e conferir",\n            "Base inteligente de Débito e Crédito"\n        ])\n'''
if text.count(old_before_tabs) != 1:
    raise SystemExit(f'Bloco de tabs Nova Geração encontrado {text.count(old_before_tabs)} vezes.')
text = text.replace(old_before_tabs, new_before_tabs, 1)

# 5) Atualiza textos e chaves da UI para deixar claro que as bases são independentes.
old_caption = '''            st.caption(\n                "Importe planilhas já classificadas. Pode enviar arquivos separados, uma planilha "\n                "com vários bancos ou arquivos ZIP. Reimportar o mesmo conteúdo não cria duplicidades. "\n                "A base de fornecedores é compartilhada entre Matriz e Filial, portanto as planilhas "\n                "antigas da Matriz não precisam ser enviadas novamente."\n            )\n'''
new_caption = '''            st.caption(\n                f"Base exclusiva de {nome_base_nova}. Matriz e Filial não compartilham mais "\n                "nenhum padrão. Envie apenas planilhas antigas já classificadas desta área."\n            )\n            if st.session_state.get('_nova_geracao_erro_limpeza_legada'):\n                st.warning(\n                    "A separação das bases já está ativa, mas a base antiga compartilhada "\n                    "não pôde ser apagada automaticamente: "\n                    + st.session_state['_nova_geracao_erro_limpeza_legada']\n                )\n'''
if text.count(old_caption) != 1:
    raise SystemExit(f'Caption compartilhada encontrada {text.count(old_caption)} vezes.')
text = text.replace(old_caption, new_caption, 1)

# 6) Inputs e ações passam a ser independentes por Matriz/Filial.
text = text.replace(
    "key='org_base_classificada_nova'",
    "key=f'org_base_classificada_nova_{chave_estabelecimento}'",
    1
)
text = text.replace(
    "key='org_senha_base_classificada_nova'",
    "key=f'org_senha_base_classificada_nova_{chave_estabelecimento}'",
    1
)
text = text.replace(
    "key='org_importar_base_classificada_nova'",
    "key=f'org_importar_base_classificada_nova_{chave_estabelecimento}'",
    1
)

# 7) Importação e gravação recebem explicitamente a base selecionada.
old_import = '''                            importar_arquivos_classificados,\n                            arquivos_aprendizado\n'''
new_import = '''                            importar_arquivos_classificados,\n                            arquivos_aprendizado,\n                            empresa_base_nova\n'''
if text.count(old_import) != 1:
    raise SystemExit(f'Chamada de importação Nova Geração encontrada {text.count(old_import)} vezes.')
text = text.replace(old_import, new_import, 1)

old_save = '''                            salvar_classificacoes_online,\n                            novos_registros\n'''
new_save = '''                            salvar_classificacoes_online,\n                            novos_registros,\n                            empresa_base_nova\n'''
if text.count(old_save) != 1:
    raise SystemExit(f'Chamada de salvamento Nova Geração encontrada {text.count(old_save)} vezes.')
text = text.replace(old_save, new_save, 1)

# 8) Mensagens deixam claro qual base está em uso e que ambas começam vazias.
text = text.replace(
    'f"Base online conectada: {len(base_classificacoes)} padrões disponíveis."',
    'f"{nome_base_nova}: {len(base_classificacoes)} padrões disponíveis."',
    1
)
text = text.replace(
    'f"Base atualizada com {quantidade_salva} padrões de classificação."',
    'f"{nome_base_nova} atualizada com {quantidade_salva} padrões de classificação."',
    1
)

# Validações estáticas para impedir regressão para a base compartilhada.
checks = [
    "'nova_geracao_matriz'",
    "'nova_geracao_filial'",
    "carregar_classificacoes_online(empresa_base_nova)",
    "importar_arquivos_classificados,\n                            arquivos_aprendizado,\n                            empresa_base_nova",
    "salvar_classificacoes_online,\n                            novos_registros,\n                            empresa_base_nova",
    "apagar_classificacoes_online('nova_geracao')",
]
for check in checks:
    if check not in text:
        raise SystemExit(f'Validação falhou: não encontrei {check!r}.')

path.write_text(text, encoding='utf-8')
print('Nova Geração separada em bases independentes de Matriz e Filial; base compartilhada legada será zerada.')
