from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from razync.accede_1000 import (
    aplicar_regras_accede_1000,
    identificar_conta_folha_accede_1000,
)


def test_identifica_codigos_e_erros_claros_da_accede_1000():
    casos = {
        "ADTO JOAO": "25",
        "ADT0 MARIA": "25",
        "ADIANTAMENTO DE SALARIO": "25",
        "PGTO FUNCIONARIOS": "187",
        "PGT0 FOLHA": "187",
        "PAGTO SALARIO": "187",
        "PAGAMENTO DE SALARIO": "187",
        "REEM DESPESAS": "668",
        "REEN VIAGEM": "668",
        "REMEBOLSO FUNCIONARIO": "668",
        "REEMBOLSO": "668",
        "Pago: FUNCIONARIO PGTO2026-06": "187",
        "Pago: FUNCIONARIO PAGTO2026-07": "187",
        "Pago: FUNCIONARIO ADTO26-07": "25",
        "Pago: FUNCIONARIO REEM2026-07": "668",
        "Pago: FUNCIONARIO REEMB2026-06": "668",
    }
    for historico, conta in casos.items():
        assert identificar_conta_folha_accede_1000(historico) == conta


def test_nao_classifica_palavras_ambiguas():
    for historico in ["PAGO FORNECEDOR", "AUTO PECAS", "REDE VISA", "PIX CLIENTE"]:
        assert identificar_conta_folha_accede_1000(historico) == ""


def test_aplica_contrapartidas_e_conta_itau_sem_sobrescrever():
    original = pd.DataFrame([
        {"VALOR": -100, "DÉBITO": "", "CRÉDITO": "", "HISTÓRICO": "ADTO ANA"},
        {"VALOR": -200, "DÉBITO": "", "CRÉDITO": "", "HISTÓRICO": "PGTO JOSE"},
        {"VALOR": -300, "DÉBITO": "", "CRÉDITO": "", "HISTÓRICO": "REEM VIAGEM"},
        {"VALOR": 400, "DÉBITO": "", "CRÉDITO": "", "HISTÓRICO": "RECEBIMENTO"},
        {"VALOR": -500, "DÉBITO": "999", "CRÉDITO": "777", "HISTÓRICO": "PGTO"},
    ])
    resultado = aplicar_regras_accede_1000(original, "508")
    assert resultado["DÉBITO"].tolist() == ["25", "187", "668", "508", "999"]
    assert resultado["CRÉDITO"].tolist() == ["508", "508", "508", "", "777"]


def test_regra_tambem_usa_conta_sicredi_da_empresa_1000():
    df = pd.DataFrame([
        {"VALOR": -50, "DÉBITO": "", "CRÉDITO": "", "HISTÓRICO": "PGT0"},
    ])
    resultado = aplicar_regras_accede_1000(df, "505")
    assert resultado.iloc[0]["DÉBITO"] == "187"
    assert resultado.iloc[0]["CRÉDITO"] == "505"


def test_aplica_formatos_reais_da_planilha_accede():
    df = pd.DataFrame([
        {"VALOR": -108.20, "DÉBITO": "", "CRÉDITO": "508", "HISTÓRICO": "Pago: DAVID BENNER VIEIRA DA SILVA PGTO2026-06"},
        {"VALOR": -4666.08, "DÉBITO": "", "CRÉDITO": "508", "HISTÓRICO": "Pago: GABRIEL PEREIRA RUSIG REEM2026-06"},
        {"VALOR": -525.00, "DÉBITO": "", "CRÉDITO": "508", "HISTÓRICO": "Pago: JOSE LUCAS DA SILVA SOARES ADTO26-07"},
    ])
    resultado = aplicar_regras_accede_1000(df, "508")
    assert resultado["DÉBITO"].tolist() == ["187", "668", "25"]
    assert resultado["CRÉDITO"].tolist() == ["508", "508", "508"]
