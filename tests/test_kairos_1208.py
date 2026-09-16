from pathlib import Path

import pandas as pd

from razync.kairos_1208 import COLUNAS_MODELO, CONTAS, detalhar_com_contas_pagas


def test_contas_e_layout_1208():
    assert CONTAS == {"itau": "508", "safra": "512", "bradesco": "9"}
    assert COLUNAS_MODELO == ["DESCRIÇÃO", "DATA", "VALOR", "DÉBITO", "CRÉDITO", "HISTÓRICO"]


def test_detalhamento_preserva_total():
    base = pd.DataFrame([{
        "DESCRIÇÃO": "BANCO ITAÚ", "DATA": pd.Timestamp("2026-01-05"),
        "VALOR": -300.0, "DÉBITO": "", "CRÉDITO": "508",
        "HISTÓRICO": "Pago: PAGAMENTOS A FORNECEDORES SISPAG",
    }])
    detalhes = pd.DataFrame([
        {"DATA": pd.Timestamp("2026-01-05"), "VALOR": 100.0, "HISTÓRICO": "Fornecedor A"},
        {"DATA": pd.Timestamp("2026-01-05"), "VALOR": 200.0, "HISTÓRICO": "Fornecedor B"},
    ])
    saida, aplicados = detalhar_com_contas_pagas({"itau": base}, detalhes)
    assert round(saida["itau"]["VALOR"].sum(), 2) == -300.0
    assert len(saida["itau"]) == 2
    assert len(aplicados) == 1


def test_integracao_esta_ligada_no_app():
    raiz = Path(__file__).resolve().parents[1]
    app = (raiz / "app.py").read_text(encoding="utf-8")
    catalogo = (raiz / "razync" / "company_catalog.py").read_text(encoding="utf-8")
    assert '"1208": "kairos_1208"' in app
    assert '"chave_sistema": "kairos_1208"' in catalogo
