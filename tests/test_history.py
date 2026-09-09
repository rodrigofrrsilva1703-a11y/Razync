import pandas as pd

from razync.history import (
    padronizar_historicos_modelo,
    prefixar_historico_movimento,
)


def test_prefixa_pago_e_recebido_conforme_sinal():
    assert prefixar_historico_movimento("PIX FORNECEDOR", -125.50) == "Pago: PIX FORNECEDOR"
    assert prefixar_historico_movimento("PIX CLIENTE", 250) == "Recebido: PIX CLIENTE"


def test_nao_duplica_e_corrige_prefixo_incompativel():
    assert prefixar_historico_movimento("Pago: ENERGIA", -80) == "Pago: ENERGIA"
    assert prefixar_historico_movimento("Recebido: CLIENTE", 80) == "Recebido: CLIENTE"
    assert prefixar_historico_movimento("Recebido: ESTORNO", -80) == "Pago: ESTORNO"
    assert prefixar_historico_movimento("Pago: DEVOLUÇÃO", 80) == "Recebido: DEVOLUÇÃO"


def test_valor_zero_preserva_historico():
    assert prefixar_historico_movimento("SALDO", 0) == "SALDO"


def test_padroniza_dataframe_sem_alterar_original():
    original = pd.DataFrame({
        "VALOR": [-10.0, 20.0],
        "HISTÓRICO": ["TARIFA", "PIX"],
    })
    resultado = padronizar_historicos_modelo(original)
    assert original["HISTÓRICO"].tolist() == ["TARIFA", "PIX"]
    assert resultado["HISTÓRICO"].tolist() == [
        "Pago: TARIFA",
        "Recebido: PIX",
    ]
