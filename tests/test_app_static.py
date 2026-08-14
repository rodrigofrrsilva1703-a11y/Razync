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
        "def processar_mapa_autokraft",
        "def processar_nova_geracao_banco",
        "def conciliar_empresa_com_extrato",
        "def renderizar_base_inteligente_empresa",
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
    ]
    for empresa in empresas:
        assert empresa in texto
    for banco in ["Itaú", "Bradesco", "Fibra", "Daycoval"]:
        assert banco in texto


def test_erros_nao_expoem_traceback():
    texto = APP.read_text(encoding="utf-8")
    assert "traceback.format_exc()" not in texto
    assert "st.exception(" not in texto
