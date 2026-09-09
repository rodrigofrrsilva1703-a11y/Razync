from pathlib import Path

import pandas as pd

from razync.valean_625 import CONTAS_VALEAN_625, processar_extrato_625


ARQUIVOS = {
    "banco_brasil": "3-Banco do Brasil -vs.pdf",
    "caixa": "5- caixa economica federal-vs.pdf",
    "sicredi": "1-Sicredi  -vs.pdf",
}


def test_contas_da_empresa_625():
    assert CONTAS_VALEAN_625 == {
        "banco_brasil": "8", "caixa": "508", "sicredi": "3999"
    }


def test_registro_modelo_define_conta_conforme_sinal(monkeypatch):
    import razync.valean_625 as valean

    monkeypatch.setattr(valean, "_texto_pdf", lambda _: (
        "02/03/2026 AMORTIZACAO CONTRATO C43430907 -1.486,28 -34.000,00\n"
        "03/03/2026 RECEBIMENTO PIX PIX_CRED 15.000,00 -19.000,00"
    ))
    df = processar_extrato_625(b"pdf", "sicredi")
    assert list(df["VALOR"]) == [-1486.28, 15000.0]
    assert list(df["DÉBITO"]) == ["", "3999"]
    assert list(df["CRÉDITO"]) == ["3999", ""]
    assert df.iloc[0]["HISTÓRICO"].startswith("Pago: ")
    assert df.iloc[1]["HISTÓRICO"].startswith("Recebido: ")


def test_datas_sao_validas_no_modelo(monkeypatch):
    import razync.valean_625 as valean

    monkeypatch.setattr(valean, "_texto_pdf", lambda _: (
        "10/04/2027 PIX RECEBIDO PIX_CRED 1.000,00 1.000,00"
    ))
    df = processar_extrato_625(b"pdf", "sicredi")
    assert pd.Timestamp(df.iloc[0]["DATA"]) == pd.Timestamp("2027-04-10")

