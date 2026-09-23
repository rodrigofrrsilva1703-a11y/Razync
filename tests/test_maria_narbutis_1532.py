import pandas as pd

from razync import engekraft_969 as leitor_itau


def test_extrato_1532_converte_linhas_quebradas(monkeypatch):
    texto = """Agência 0644 Conta 0097731-6 CNPJ 59.124.979/0001-52 MARIA A D P NARB SOC UNIP LTDA
01/03/2026 SALDO ANTERIOR 1.000,00
02/03/2026 BOLETO PAGO AMIL ASSISTE AMIL ASSISTENCIA ME 29.309.127/0001-79 -100,00
02/03/2026 RENDIMENTOS REND PAGO APLIC
AUT MAIS 0,50
02/03/2026 SALDO TOTAL DISPONÍVEL DIA 900,50
12/03/2026 PIX ENVIADO MARIA APARECIDA DIAS PEREIRA
NARBUTIS 767.710.328-68 -200,00
"""
    monkeypatch.setattr(leitor_itau, "_texto_pdf", lambda _: texto)

    resultado = leitor_itau.processar_extrato_itau_modelo(
        b"pdf",
        "508",
        ("MARIA A D P NARB", "0097731-6"),
        "empresa 1532 - Maria Narbutis",
    )

    assert len(resultado) == 3
    assert resultado["VALOR"].tolist() == [-100.0, 0.5, -200.0]
    assert resultado["HISTÓRICO"].tolist() == [
        "Pago: AMIL ASSISTENCIA ME",
        "Recebido: RENDIMENTOS",
        "Pago: MARIA APARECIDA DIAS PEREIRA NARBUTIS",
    ]
    assert resultado.loc[resultado["VALOR"] > 0, "DÉBITO"].eq("508").all()
    assert resultado.loc[resultado["VALOR"] < 0, "CRÉDITO"].eq("508").all()
    assert pd.api.types.is_datetime64_any_dtype(resultado["DATA"])
