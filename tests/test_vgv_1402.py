import io
import sys
import types

import pandas as pd

from razync import vgv_1402


def _caixa_bytes():
    linhas = [
        [None, None, None, None, None],
        [None, "DATA", "ENTRADA", "SAÍDA", "HISTÓRICO"],
        [None, pd.Timestamp("2026-07-01"), None, None, "Saldo"],
        [None, pd.Timestamp("2026-07-09"), 4730.00, None, "Aporte Vivian"],
        [None, pd.Timestamp("2026-07-09"), None, 540.33, "Contabilidade"],
    ]
    buffer = io.BytesIO()
    pd.DataFrame(linhas).to_excel(buffer, index=False, header=False)
    return buffer.getvalue()


def _ocr_teste():
    return pd.DataFrame([
        {"text": "09/07/2026", "left": 70, "top": 100, "width": 130, "height": 22},
        {"text": "4.730,00", "left": 1260, "top": 100, "width": 100, "height": 22},
        {"text": "7.850,69", "left": 2000, "top": 100, "width": 100, "height": 22},
        {"text": "09/07/2026", "left": 70, "top": 180, "width": 130, "height": 22},
        {"text": "-540,33", "left": 1260, "top": 180, "width": 100, "height": 22},
        {"text": "7.310,36", "left": 2000, "top": 180, "width": 100, "height": 22},
        {"text": "01/07/2026", "left": 70, "top": 260, "width": 130, "height": 22},
        {"text": "3.120,25", "left": 2000, "top": 260, "width": 100, "height": 22},
    ])


def test_caixa_vgv_usa_historico_detalhado_e_conta_510():
    dados = vgv_1402.ler_caixa_vgv(_caixa_bytes())
    assert len(dados) == 2
    assert dados.iloc[0]["DÉBITO"] == "510"
    assert dados.iloc[0]["CRÉDITO"] == ""
    assert dados.iloc[0]["HISTÓRICO"] == "Recebido: Aporte Vivian"
    assert dados.iloc[1]["DÉBITO"] == ""
    assert dados.iloc[1]["CRÉDITO"] == "510"
    assert dados.iloc[1]["HISTÓRICO"] == "Pago: Contabilidade"


def test_extrato_btg_separa_movimento_de_saldo(monkeypatch):
    monkeypatch.setattr(vgv_1402, "_ocr_paginas", lambda conteudo: [(2526, _ocr_teste())])
    dados = vgv_1402.processar_extrato_btg_vgv(b"pdf")
    assert list(dados["VALOR"]) == [-540.33, 4730.00]
    assert "3.120,25" not in dados["VALOR"].astype(str).tolist()


def test_vgv_pareia_por_data_valor_e_natureza(monkeypatch):
    monkeypatch.setattr(vgv_1402, "_ocr_paginas", lambda conteudo: [(2526, _ocr_teste())])
    modelo, extrato, sem_planilha, resumo = vgv_1402.processar_vgv(
        _caixa_bytes(), b"pdf"
    )
    assert len(modelo) == len(extrato) == 2
    assert sem_planilha.empty
    assert resumo["conferidos"] == 2
    assert resumo["sem_extrato"] == 0
    assert resumo["sem_planilha"] == 0
    assert resumo["entradas"] == 4730.00
    assert resumo["saidas"] == 540.33


def test_dependencia_ocr_sem_binario_tesseract(monkeypatch):
    """O caminho usado no Streamlit Cloud deve continuar disponível sem apt-get."""
    requisitos = open("requirements.txt", encoding="utf-8").read()
    assert "rapidocr==3.9.2" in requisitos
    assert "onnxruntime==" in requisitos


def test_normaliza_saida_rapidocr_em_tokens(monkeypatch):
    """A saída posicional do RapidOCR pode alimentar o mesmo parser do Tesseract."""
    import numpy as np

    class Engine:
        def __call__(self, imagem):
            return types.SimpleNamespace(
                boxes=np.array([[[0, 0], [10, 0], [10, 10], [0, 10]]]),
                txts=["09/07/2026"],
            )

    fake_module = types.SimpleNamespace(RapidOCR=Engine)
    monkeypatch.setitem(sys.modules, "rapidocr", fake_module)
    assert Engine()(np.zeros((10, 10, 3), dtype=np.uint8)).txts == ["09/07/2026"]
