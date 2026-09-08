import pandas as pd

from razync.eletro_forte_filial_1408 import montar_modelo_1408


def test_monta_extrato_substitui_recebido_e_desmembra_francesinha(monkeypatch):
    extrato = [
        {"DATA": "04/08/2026", "VALOR": 80.63, "HISTÓRICO": "PIX RECEBIDO"},
        {"DATA": "04/08/2026", "VALOR": 1170.75, "HISTÓRICO": "BOLETO RECEBIDO 04/08S"},
        {"DATA": "04/08/2026", "VALOR": -24.56, "HISTÓRICO": "TAR COBRANCA"},
    ]
    recebidos = pd.DataFrame([{
        "DESCRIÇÃO": "BANCO ITAÚ", "DATA": pd.Timestamp("2026-08-04"),
        "VALOR": 80.63, "DÉBITO": "512", "CRÉDITO": "",
        "HISTÓRICO": "Recebido: NA025200 - CONSUMIDOR",
    }])
    monkeypatch.setattr(
        "razync.eletro_forte_filial_1408.processar_recebidos",
        lambda *args: {"512": recebidos},
    )
    francesinhas = pd.DataFrame([
        {"DESCRIÇÃO": "BANCO ITAÚ", "DATA": pd.Timestamp("2026-08-04"),
         "VALOR": 200.00, "DÉBITO": "512", "CRÉDITO": "", "HISTÓRICO": "Recebido: Cliente A"},
        {"DESCRIÇÃO": "BANCO ITAÚ", "DATA": pd.Timestamp("2026-08-04"),
         "VALOR": 970.75, "DÉBITO": "512", "CRÉDITO": "", "HISTÓRICO": "Recebido: Cliente B"},
    ])

    modelo, resumo = montar_modelo_1408(extrato, b"xls", 2026, francesinhas)
    assert len(modelo) == 4
    assert "Recebido: NA025200 - CONSUMIDOR" in modelo["HISTÓRICO"].tolist()
    assert "Pago: TAR COBRANCA" in modelo["HISTÓRICO"].tolist()
    assert 1170.75 not in modelo["VALOR"].tolist()
    assert resumo["historicos_substituidos"] == 1
    assert resumo["grupos_francesinhas"] == 1
    assert set(modelo.loc[modelo["VALOR"] > 0, "DÉBITO"]) == {"512"}
