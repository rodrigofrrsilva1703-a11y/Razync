import pandas as pd

from razync.hw_88 import processar_tokens_pagina


def _token(text, left, top, width=70, height=18):
    return {"text": text, "left": left, "top": top, "width": width, "height": height}


def test_processa_movimentos_e_ignora_saldo_sem_documentos_no_historico():
    dados = pd.DataFrame([
        _token("31/07/2026", 30, 100),
        _token("SALDO TOTAL DISPONIVEL DIA", 180, 100, 260),
        _token("3.292,55", 930, 100),
        _token("31/07/2026", 30, 140),
        _token("BOLETO PAGO SAMEDIL", 180, 140, 220),
        _token("SAMEDIL SERVICOS MEDICOS", 480, 140, 220),
        _token("31.466.949/0001-05", 680, 140, 130),
        _token("-2.051,45", 820, 140),
        _token("23/07/2026", 30, 180),
        _token("RECEBIMENTOS REDE DOR", 180, 180, 220),
        _token("29.360,03", 820, 180),
    ])
    resultado = processar_tokens_pagina(1000, dados)
    assert len(resultado) == 2
    assert resultado[0]["VALOR"] == -2051.45
    assert resultado[0]["CRÉDITO"] == "508"
    assert resultado[0]["DÉBITO"] == ""
    assert resultado[0]["HISTÓRICO"].startswith("Pago: ")
    assert "31.466" not in resultado[0]["HISTÓRICO"]
    assert resultado[1]["VALOR"] == 29360.03
    assert resultado[1]["DÉBITO"] == "508"
    assert resultado[1]["HISTÓRICO"].startswith("Recebido: ")
