import pandas as pd

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
