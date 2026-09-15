import pandas as pd
import pytest

from razync import valean_626


def _quadro(linhas, inicial, final):
    df = pd.DataFrame(linhas, columns=valean_626.COLUNAS_MODELO)
    df.attrs["saldo_inicial_extrato"] = 100.0
    df.attrs["data_saldo_inicial_extrato"] = pd.Timestamp(inicial)
    df.attrs["saldo_extrato"] = 100.0
    df.attrs["data_saldo_extrato"] = pd.Timestamp(final)
    return df


def test_multiplos_remove_somente_sobreposicao_entre_periodos(monkeypatch):
    primeiro = _quadro([
        ["BB", pd.Timestamp("2026-01-31"), 10.0, "", "", "Devolução"],
    ], "2025-12-31", "2026-01-31")
    segundo = _quadro([
        ["BB", pd.Timestamp("2026-01-31"), 10.0, "", "", "Devolução repetida"],
        ["BB", pd.Timestamp("2026-02-02"), -20.0, "", "", "PIX igual"],
        ["BB", pd.Timestamp("2026-02-02"), -20.0, "", "", "PIX igual"],
    ], "2026-01-31", "2026-02-28")
    mapa = {b"jan": primeiro, b"fev": segundo}
    monkeypatch.setattr(
        valean_626, "processar_extrato_626", lambda conteudo, banco: mapa[conteudo]
    )

    resultado = valean_626.processar_multiplos_626(
        [b"fev", b"jan"], "banco_brasil"
    )

    assert resultado["VALOR"].tolist() == [10.0, -20.0, -20.0]
    assert resultado.attrs["linhas_sobrepostas_ignoradas"] == 1


def test_sicredi_nao_transforma_saldo_sem_sinal_em_movimento(monkeypatch):
    texto = """
SALDO -12.534,21
13/03/2026 PAGAMENTO PIX WILSON PIX_DEB -2.377,31 14.911,52
13/03/2026 PAGAMENTO PIX BRUNO PIX_DEB -2.240,00 -17.151,52
"""
    monkeypatch.setattr(valean_626, "_texto_pdf", lambda _: texto)

    resultado = valean_626.processar_sicredi_626(b"pdf")

    assert resultado["VALOR"].tolist() == [-2377.31, -2240.0]


def test_multiplos_nao_entrega_resultado_parcial(monkeypatch):
    valido = _quadro([
        ["SICREDI", pd.Timestamp("2026-01-02"), 100.0, "1155", "", "PIX"],
    ], "2026-01-01", "2026-01-31")

    def processar(conteudo, banco):
        if conteudo == b"marco_ilegivel":
            raise ValueError("OCR indisponível")
        return valido

    monkeypatch.setattr(valean_626, "processar_extrato_626", processar)

    with pytest.raises(ValueError, match="nem todos os extratos foram lidos"):
        valean_626.processar_multiplos_626(
            [b"janeiro", b"marco_ilegivel"], "sicredi"
        )


def test_sicredi_mantem_movimentos_quando_saldo_impresso_diverge(monkeypatch):
    texto = """
SALDO -1.000,00
02/04/2026 PAGAMENTO PIX CLIENTE COM HISTORICO SUFICIENTE PARA LEITURA PIX_DEB -100,00 15.302,44
"""
    monkeypatch.setattr(valean_626, "_texto_pdf", lambda _: texto)

    resultado = valean_626.processar_sicredi_626(b"pdf")

    assert resultado["VALOR"].tolist() == [-100.0]
    assert "aviso_saldo_impresso" in resultado.attrs
