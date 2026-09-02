import io

import pandas as pd

from razync.up_pack import identificar_banco_up_pack, processar_planilha_up_pack


def _xlsx(linhas):
    buffer = io.BytesIO()
    pd.DataFrame(linhas).to_excel(buffer, index=False, header=False)
    return buffer.getvalue()


def test_identificacao_por_nome_do_arquivo():
    assert identificar_banco_up_pack(b"x", "072026 Conciliação SIG - Santander.xlsx") == "santander"
    assert identificar_banco_up_pack(b"x", "072026 Conciliação SIG - Sicredi.xlsx") == "sicredi"
    assert identificar_banco_up_pack(b"x", "movimento.xlsx") is None


def test_santander_desmembra_pagamento_contas_diversas():
    arquivo = _xlsx([
        ["Filial: UP PACK - TECHNOLOGY AND CONSULTING"],
        ["Data", "D/C", "Complemento", "Conf", "Entrada", "Saída", "Saldo", "Conta Vinculada"],
        ["03/07/2026", "PAGTO TITULO", "PAGAMENTO CONTAS DIV.", "X", 0, 2477.73, 17960.52, None],
        [None, "JAGUAR2026-06", 810.50, "JAGUAR SERVICOS CONTABEIS LTDA", None, "2.1.3.01", "FORNECEDORES", None],
        [None, "2026-06", 763.80, "FELIPE KIRSANOFF RIZZO", None, "2.1.3.01", "FORNECEDORES", None],
        [None, "2026-06", 903.43, "ANDREA PROIETTI", None, "2.1.3.01", "FORNECEDORES", None],
        ["03/07/2026", "RENDIMENTO AUTOMATICO", "RENDIMENTO AUTOMATICO", None, 0.14, 0, 17960.66, None],
    ])

    df = processar_planilha_up_pack(arquivo, "santander")
    assert len(df) == 4
    assert df["VALOR"].tolist() == [-810.50, -763.80, -903.43, 0.14]
    assert df.iloc[0]["HISTÓRICO"] == "JAGUAR SERVICOS CONTABEIS LTDA JAGUAR2026-06"
    assert df.iloc[1]["DATA"].strftime("%d/%m/%Y") == "03/07/2026"
    assert not df["HISTÓRICO"].str.contains("PAGAMENTO CONTAS DIV", case=False).any()


def test_sicredi_processa_movimentos_normais():
    arquivo = _xlsx([
        ["Filial: UP PACK - TECHNOLOGY AND CONSULTING"],
        ["Data", "D/C", "Complemento", "Conf", "Entrada", "Saída", "Saldo", "Conta Vinculada"],
        ["13/07/2026", "TRANSFERÊNCIA (E)", "TRANSFERENCIA ENTRE CONTAS", None, 400, 0, 410.38, "SANTANDER"],
        ["22/07/2026", "PAGTO TITULO", "Doc.084574/01 - CARDUM PALACE HOTEL LTDA", "X", 0, 238, 172.38, None],
    ])

    df = processar_planilha_up_pack(arquivo, "sicredi")
    assert len(df) == 2
    assert df["VALOR"].tolist() == [400.0, -238.0]
    assert df.iloc[0]["HISTÓRICO"] == "TRANSFERENCIA ENTRE CONTAS"
    assert df.iloc[1]["HISTÓRICO"].startswith("Doc.084574/01")
