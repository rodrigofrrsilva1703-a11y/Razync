from razync.santander_statement import (
    parece_extrato_santander_empresarial,
    processar_extrato_santander_empresarial_texto,
)


def test_santander_empresarial_usa_sinal_do_pdf_e_ignora_saldo():
    texto = """
    Santander
    Internet Banking Empresarial
    UP PACK BRASIL LTDA Agência: 0643 Conta: 130048131
    30/07/2026 Saldo do dia Cc + ContaMax principal R$ 70.133,85
    30/07/2026 Pagamento De Boleto Outros Bancos CARDUM PALACE HOTEL LTDA - R$ 476,00
    30/07/2026 Ted Enviada 058.672.068-58 - R$ 64.000,00
    30/07/2026 Ted Recebida 06649712000112 R$ 134.000,00
    24/07/2026 Rendimento Liquido De Contamax 7000 RENDIMENTO LIQUIDO DE CONTAMAX R$ 0,10
    24/07/2026 Pix Enviado Wendell Carvalho - R$ 948,28
    """

    assert parece_extrato_santander_empresarial(texto)
    lancamentos = processar_extrato_santander_empresarial_texto(texto)

    assert len(lancamentos) == 5
    assert [item["VALOR"] for item in lancamentos] == [-476.00, -64000.00, 134000.00, 0.10, -948.28]
    assert all("SALDO DO DIA" not in item["HISTÓRICO"].upper() for item in lancamentos)
    assert lancamentos[0]["DATA"] == "30/07/2026"
    assert lancamentos[0]["DESCRIÇÃO"] == "BANCO SANTANDER"
