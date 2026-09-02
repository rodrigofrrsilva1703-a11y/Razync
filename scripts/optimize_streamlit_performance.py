from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old_batch = '''def salvar_status_tarefas_empresas_em_lote(codigos_empresas, competencia, concluida):
    """Atualiza várias empresas usando a mesma regra segura da conclusão individual."""
    codigos = [str(codigo) for codigo in codigos_empresas if str(codigo).strip()]
    for codigo in dict.fromkeys(codigos):
        salvar_status_tarefa_empresa(codigo, competencia, concluida)
    return len(dict.fromkeys(codigos))
'''
new_batch = '''def salvar_status_tarefas_empresas_em_lote(codigos_empresas, competencia, concluida):
    """Atualiza várias empresas em uma única chamada ao Supabase."""
    codigos = list(dict.fromkeys(
        str(codigo).strip() for codigo in codigos_empresas if str(codigo).strip()
    ))
    if not codigos:
        return 0
    agora = datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
    registros = [
        {
            'codigo_empresa': codigo,
            'competencia': competencia.isoformat(),
            'concluida': bool(concluida),
            'concluida_em': agora if concluida else None,
            'atualizado_em': agora,
        }
        for codigo in codigos
    ]
    requisicao_classificacao_online(
        'tarefas_empresas?on_conflict=codigo_empresa,competencia',
        metodo='POST',
        dados=registros,
        prefer='resolution=merge-duplicates,return=minimal',
    )
    carregar_tarefas_competencia.clear()
    return len(codigos)
'''
if old_batch not in text:
    raise SystemExit('Bloco de atualização em lote não encontrado')
text = text.replace(old_batch, new_batch, 1)

text = text.replace(
    '@st.cache_data(show_spinner=False, ttl=20)\ndef carregar_tarefas_competencia',
    '@st.cache_data(show_spinner=False, ttl=60, max_entries=12)\ndef carregar_tarefas_competencia',
    1,
)
text = text.replace(
    '@st.cache_data(show_spinner=False, ttl=15)\ndef carregar_tarefas_central',
    '@st.cache_data(show_spinner=False, ttl=45, max_entries=4)\ndef carregar_tarefas_central',
    1,
)

marker = '''def gerar_txt_dominio(df):'''
if marker not in text:
    raise SystemExit('Marcador para helper de modelo não encontrado')
helper = '''@st.cache_data(show_spinner=False, max_entries=2)\ndef carregar_modelo_dominio_base():\n    """Lê o arquivo-base uma vez e reutiliza entre reruns do Streamlit."""\n    colunas = ['DESCRIÇÃO', 'DATA', 'VALOR', 'DÉBITO', 'CRÉDITO', 'HISTÓRICO']\n    caminho = "Modelo dominio.xlsx"\n    if not os.path.exists(caminho):\n        return pd.DataFrame(columns=colunas)\n    try:\n        df = pd.read_excel(caminho)\n    except Exception:\n        return pd.DataFrame(columns=colunas)\n    if 'DESCRIÇÃO' not in df.columns:\n        return pd.DataFrame(columns=colunas)\n    return df\n\n\n'''
if 'def carregar_modelo_dominio_base()' not in text:
    text = text.replace(marker, helper + marker, 1)

old_model = '''            colunas_dominio = ['DESCRIÇÃO', 'DATA', 'VALOR', 'DÉBITO', 'CRÉDITO', 'HISTÓRICO']
            df_modelo = pd.read_excel("Modelo dominio.xlsx") if os.path.exists("Modelo dominio.xlsx") else pd.DataFrame(columns=colunas_dominio)
            if 'DESCRIÇÃO' not in df_modelo.columns: df_modelo = pd.DataFrame(columns=colunas_dominio)
'''
new_model = '''            colunas_dominio = ['DESCRIÇÃO', 'DATA', 'VALOR', 'DÉBITO', 'CRÉDITO', 'HISTÓRICO']
            df_modelo = carregar_modelo_dominio_base()
'''
if old_model not in text:
    raise SystemExit('Leitura direta do Modelo Domínio não encontrada')
text = text.replace(old_model, new_model, 1)

perf_css = '''\n# ==============================================================================
# PERFORMANCE VISUAL V1
# ==============================================================================
st.markdown("""
<style>
/* Menos trabalho de pintura/composição sem alterar a identidade visual. */
.stApp {
    background: linear-gradient(180deg, var(--rz-bg) 0%, var(--rz-bg-soft) 100%) !important;
}
.rz-page-header,
.rz-dashboard-intro,
.rz-overview-panel,
.metric-card,
[data-testid="stMetric"],
[data-testid="stFileUploaderDropzone"] {
    box-shadow: 0 8px 24px rgba(0,0,0,.11) !important;
}
.rz-page-header,
.rz-dashboard-intro,
.rz-overview-panel,
[data-testid="stFileUploaderDropzone"] {
    background: var(--rz-panel) !important;
}
.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] > button,
[data-testid="stFileUploaderDropzone"] {
    transition-duration: .10s !important;
}
.stButton > button:hover,
.stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    transform: none !important;
}
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        scroll-behavior: auto !important;
        transition: none !important;
        animation: none !important;
    }
}
</style>
""", unsafe_allow_html=True)
\n'''
route_marker = '# ==============================================================================\n# CONTROLE DE ESTADO DE NAVEGAÇÃO'
if route_marker not in text:
    raise SystemExit('Marcador de navegação não encontrado')
if '# PERFORMANCE VISUAL V1' not in text:
    text = text.replace(route_marker, perf_css + route_marker, 1)

path.write_text(text, encoding='utf-8')
