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
    assert "'Período dos lançamentos'" in texto
    assert "key='ef242_periodo'" in texto
    assert "key='ef242_ano'" not in texto
    assert "Nenhum lançamento foi encontrado no período selecionado." in texto
