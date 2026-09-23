import pandas as pd

from razync import conferencia_fiscal
from razync.conferencia_fiscal import conferir_fiscal_contabil


def test_pagamento_extra_nao_impede_conferencia_fiscal():
    acumuladores = pd.DataFrame([{
        "CONTA": "2221", "TIPO": "ENTRADAS", "ACUMULADOR": "3000",
        "DESCRIÇÃO": "Consultoria", "VALOR_FISCAL": 1294.0,
    }])
    razao = pd.DataFrame([
        {"CONTA": "2221", "DATA": pd.Timestamp("2026-07-28"), "LOTE": "1", "HISTÓRICO": "SERVIÇOS DE TERCEIROS CF NF 1300", "CONTRAPARTIDA": "2693", "DÉBITO": 1294.0, "CRÉDITO": 0.0},
        {"CONTA": "2221", "DATA": pd.Timestamp("2026-07-31"), "LOTE": "2", "HISTÓRICO": "Pago: fornecedor NF 1300", "CONTRAPARTIDA": "508", "DÉBITO": 1294.0, "CRÉDITO": 0.0},
    ])
    resumo, detalhes = conferir_fiscal_contabil(acumuladores, razao)
    assert resumo.iloc[0]["SITUAÇÃO"] == "CONFERE COM ALERTAS"
    assert resumo.iloc[0]["CONTÁBIL COMPATÍVEL"] == 1294.0
    assert resumo.iloc[0]["TOTAL DA CONTA"] == 2588.0
    assert (detalhes["CLASSIFICAÇÃO"] == "ALERTA - NÃO FISCAL").sum() == 1


def test_relatorio_individual_nao_confunde_empresa_com_filial(monkeypatch):
    acumuladores = pd.DataFrame([{
        "CONTA": "2221", "TIPO": "ENTRADAS", "ACUMULADOR": "3000",
        "DESCRIÇÃO": "Serviços", "VALOR_FISCAL": 100.0,
    }])
    razao = pd.DataFrame([{
        "CONTA": "2221", "FILIAL": "1", "DATA": pd.Timestamp("2026-03-31"),
        "LOTE": "1", "HISTÓRICO": "SERVIÇOS CF NF 1",
        "CONTRAPARTIDA": "1", "DÉBITO": 100.0, "CRÉDITO": 0.0,
    }])
    leituras = iter([
        (acumuladores, {"inicio": pd.Timestamp("2026-03-01"), "fim": pd.Timestamp("2026-03-31")}),
        (razao, {"inicio": pd.Timestamp("2026-03-01"), "fim": pd.Timestamp("2026-03-31")}),
    ])
    monkeypatch.setattr(conferencia_fiscal, "ler_acumuladores", lambda *_: next(leituras))
    monkeypatch.setattr(conferencia_fiscal, "ler_razao", lambda *_: next(leituras))

    resultado = conferencia_fiscal.processar_conferencia(
        b"acumuladores", "acumuladores.xlsx", b"razao", "razao.xlsx",
        filial_alvo="1532",
    )

    assert resultado["filial_aplicada"] == "1"
    assert resultado["resumo"].iloc[0]["SITUAÇÃO"] == "CONFERE"
