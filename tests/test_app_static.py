from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"


def test_app_tem_sintaxe_valida():
    ast.parse(APP.read_text(encoding="utf-8"))


def test_funcoes_criticas_permanecem():
    texto = APP.read_text(encoding="utf-8")
    obrigatorias = [
        "def processar_pdf_daycoval_detalhado",
        "def processar_pdf_itau_detalhado",
        "def processar_pdf_bradesco_mensal",
        "def processar_pdf_fibra_extrato",
        "def processar_mapa_autokraft",
        "def processar_planilha_accede_sig",
        "def processar_nova_geracao_banco",
        "def conciliar_empresa_com_extrato",
        "def renderizar_base_inteligente_empresa",
        "def processar_extrato_unificado",
    ]
    for funcao in obrigatorias:
        assert funcao in texto


def test_empresas_e_bancos_permanecem():
    texto = APP.read_text(encoding="utf-8")
    empresas = [
        "266 - Nova Geração",
        "1396 - Nova Geração Filial",
        "3 - Autokraft Industrial",
        "178 - Autokraft Projetos",
        "343 - I.S.A",
        "1000 - ACCEDE AUTOMAÇÃO",
        "1001 - ACCEDE EQUIPAMENTOS",
    ]
    for empresa in empresas:
        assert empresa in texto
    for banco in ["Itaú", "Bradesco", "Fibra", "Daycoval", "Sicredi"]:
        assert banco in texto


def test_ocr_bradesco_preserva_caminho_real():
    texto = APP.read_text(encoding="utf-8")
    assert "reader._razync_source_path = caminho_pdf" in texto
    assert "getattr(reader, '_razync_source_path', None)" in texto
    assert "fitz.Matrix(4.0, 4.0)" in texto
    assert "lang='por'" in texto


def test_nao_existem_aplicadores_temporarios():
    temporarios = [
        ROOT / '.github/workflows/apply-accede-after-validation.yml',
        ROOT / '.github/workflows/apply-accede-empresas.yml',
        ROOT / 'scripts/patch_accede_empresas.py',
        ROOT / 'scripts/cleanup_accede_import.py',
        ROOT / 'scripts/patch_bradesco_ocr.py',
    ]
    for caminho in temporarios:
        assert not caminho.exists(), str(caminho)


def test_erros_nao_expoem_traceback():
    texto = APP.read_text(encoding="utf-8")
    assert "traceback.format_exc()" not in texto
    assert "st.exception(" not in texto


def test_empresa_242_usa_periodo_em_vez_de_ano_manual():
    texto = APP.read_text(encoding="utf-8")
    assert "Período dos lançamentos" in texto
    assert "key=f'{prefixo_ef}_data_inicial'" in texto
    assert "key=f'{prefixo_ef}_data_final'" in texto
    assert "placeholder='DD/MM/AAAA'" in texto
    assert "key='ef242_periodo'" not in texto
    assert "key='ef242_ano'" not in texto
    assert "Nenhum lançamento foi encontrado no período selecionado." in texto


def test_conferencia_242_usa_consolidado_separado_por_conta():
    texto = APP.read_text(encoding="utf-8")
    assert "rotulo_planilha='Planilha consolidada'" in texto
    assert "'slug': 'bb_8'" in texto
    assert "'slug': 'itau_508'" in texto
    assert "'slug': 'itau_509'" in texto
    assert "ler_planilha_organizada_conferencia(file_bytes, banco_alvo, conta_alvo=None)" in texto


def test_empresa_242_reutiliza_processamentos_pesados_entre_interacoes():
    texto = APP.read_text(encoding="utf-8")
    caches_242 = [
        "_ef242_processar_despesas",
        "_ef242_processar_fornecedores",
        "_ef242_processar_recebidos",
        "_ef242_processar_francesinhas",
        "_ef242_corrigir_datas",
        "_ef242_gerar_modelo",
        "_ef242_gerar_consolidado",
    ]
    for cache in caches_242:
        assert texto.count(cache) >= 2

    for funcao in [
        "classificar_planilha_final",
        "ler_planilha_organizada_conferencia",
        "processar_extrato_conferencia_empresa",
        "conciliar_empresa_com_extrato",
    ]:
        posicao = texto.index(f"def {funcao}")
        trecho_anterior = texto[max(0, posicao - 100):posicao]
        assert "@st.cache_data" in trecho_anterior


def test_detector_prioriza_bb_e_contas_itau_da_242():
    texto = APP.read_text(encoding="utf-8")
    assert "['105318', '181537']" in texto
    assert "EXTRATO DE CONTA CORRENTE - AUTORIZAVEL" in texto
    assert "CLIENTE - CONTA ATUAL" in texto
    assert "return 'BANCO DO BRASIL'" in texto


def test_base_242_classifica_planilha_consolidada_em_uma_etapa():
    texto = APP.read_text(encoding="utf-8")
    assert "'Consolidada', 'Despesa', 'Fornecedor', 'Recebido', 'Francesinhas'" in texto
    assert "modo_consolidado_eletro_forte=False" in texto
    assert "if modo_consolidado_eletro_forte:" in texto
    assert "valores_regra = {'0', '166'}" in texto
    assert "valores_regra = {'', '0', '14', '16', '166'}" in texto


def test_empresa_1408_reutiliza_fluxo_242_com_itau_512_e_base_isolada():
    texto = APP.read_text(encoding="utf-8")
    catalogo = (ROOT / "razync" / "company_catalog.py").read_text(encoding="utf-8")
    assert '"codigo": 1408' in catalogo
    assert '"chave_sistema": "eletro_forte_filial"' in catalogo
    assert "chave_base_ef = 'eletro_forte_filial_1408'" in texto


def test_base_1408_tem_perfil_consolidado_e_regras_proprias():
    texto = Path('app.py').read_text(encoding='utf-8')
    assert "perfil_1408 = empresa == 'eletro_forte_filial_1408'" in texto
    assert "abas = st.tabs(['Modelo Domínio consolidado'])" in texto
    assert "{'itau_512'} if empresa == 'eletro_forte_filial_1408'" in texto
    assert "{'', '0'} if empresa_classificacao == 'eletro_forte_filial_1408'" in texto
    assert "{'itau_512': '512'}" in texto
    assert "conta_unica_ef = '512'" in texto
    assert "'slug': 'itau_512'" in texto
    assert "'conta': '512'" in texto
    assert "classificar_planilha_final," in texto
    assert "                    empresa,\n                    coluna_regra," in texto


def test_empresa_1402_tem_btg_510_base_e_conferencia():
    texto = APP.read_text(encoding="utf-8")
    catalogo = (ROOT / "razync" / "company_catalog.py").read_text(encoding="utf-8")
    assert '"codigo": 1402' in catalogo
    assert '"chave_sistema": "vgv_1402"' in catalogo
    assert "contas_vgv = {'btg': '510'}" in texto
    assert "renderizar_base_inteligente_empresa(\n                'vgv_1402'" in texto
    assert "'nome': 'BTG · Conta 510'" in texto
    assert "processar_extrato_btg_vgv" in texto


def test_pesquisa_nao_usa_componente_customizado_que_quebra_rerun():
    texto = APP.read_text(encoding="utf-8")
    assert "components.declare_component" not in texto
    assert "streamlit.components" not in texto
    assert "return st.text_input(" in texto
    assert not (ROOT / 'components' / 'company_search' / 'index.html').exists()
