import pandas as pd

from razync import gz_1211


def test_gz_le_boletos_em_linha_unica():
    texto = (
        "CLIENTE TESTE LTDA 10/07/2026 10/07/2026 "
        "1.234,56 157 DOCUMENTO Liquidado"
    )
    boletos = gz_1211._extrair_boletos_texto_gz(texto)

    assert len(boletos) == 1
    assert boletos[0].pagador == "CLIENTE TESTE LTDA"
    assert boletos[0].valor == 1234.56
    assert boletos[0].status == "Liquidado"


def test_gz_le_boleto_quebrado_em_duas_linhas():
    texto = (
        "CLIENTE QUEBRA LINHA LTDA 11/07/2026\n"
        "11/07/2026 500,00 157 DOCUMENTO Liquidado"
    )
    boletos = gz_1211._extrair_boletos_texto_gz(texto)

    assert len(boletos) == 1
    assert boletos[0].pagador == "CLIENTE QUEBRA LINHA LTDA"
    assert boletos[0].valor == 500.0


def test_gz_gera_modelo_mesmo_quando_auxiliar_nao_e_lido(monkeypatch):
    extrato = pd.DataFrame([
        {
            "DESCRIÇÃO": "BANCO ITAÚ",
            "DATA": pd.Timestamp("2026-07-10"),
            "VALOR": 4083.19,
            "DÉBITO": "508",
            "CRÉDITO": "",
            "HISTÓRICO": "Recebido: BOLETOS RECEBIDOS",
        },
        {
            "DESCRIÇÃO": "BANCO ITAÚ",
            "DATA": pd.Timestamp("2026-07-10"),
            "VALOR": -100.0,
            "DÉBITO": "",
            "CRÉDITO": "508",
            "HISTÓRICO": "Pago: TESTE",
        },
    ])

    monkeypatch.setattr(gz_1211, "ler_extrato_itau_gz", lambda _: extrato.copy())
    monkeypatch.setattr(
        gz_1211,
        "ler_saldos_extrato_itau_gz",
        lambda _: {"saldo_inicial": None, "saldo_final_informado": None},
    )

    def falhar(_):
        raise ValueError("layout auxiliar diferente")

    monkeypatch.setattr(gz_1211, "ler_boletos_liquidados_gz", falhar)

    saida, diag, _, resumo = gz_1211.processar_gz(b"extrato", b"auxiliar")

    assert len(saida) == 2
    assert saida.iloc[0]["VALOR"] == 4083.19
    assert diag.iloc[0]["STATUS"] == "Sem detalhamento"
    assert "layout auxiliar diferente" in resumo["aviso_boletos"]
