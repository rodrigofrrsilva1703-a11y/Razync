from pathlib import Path

import pandas as pd

from razync.dias_pereira_1530 import (
    CONTA_ITAU_1530,
    processar_extrato_itau_xls_1530,
)


ARQUIVO_REAL = Path(
    "/workspace/scratch/5e34a0486359/upload/Extrato_0775-984586-07-2026 BAHIA.xls"
)


def test_le_extrato_itau_xls_real_quando_disponivel():
    if not ARQUIVO_REAL.exists():
        return
    resultado = processar_extrato_itau_xls_1530(ARQUIVO_REAL.read_bytes())

    assert not resultado.empty
    assert not resultado["HISTÓRICO"].str.contains("SALDO", case=False).any()
    assert set(resultado.loc[resultado["VALOR"] > 0, "DÉBITO"]) == {CONTA_ITAU_1530}
    assert set(resultado.loc[resultado["VALOR"] < 0, "CRÉDITO"]) == {CONTA_ITAU_1530}
    assert resultado["DATA"].min() == pd.Timestamp("2026-07-02")
    assert resultado["DATA"].max() == pd.Timestamp("2026-07-31")


def test_empresa_1530_tem_todas_as_ferramentas():
    app = Path("app.py").read_text(encoding="utf-8")
    catalogo = Path("razync/company_catalog.py").read_text(encoding="utf-8")

    assert '"codigo": 1530' in catalogo
    assert '"chave_sistema": "dias_pereira_1530"' in catalogo
    assert '"1530": "dias_pereira_1530"' in app
    assert 'type=["xls", "xlsx", "pdf"]' in app
    assert '"Baixar Modelo Domínio · Itaú 508"' in app
    assert '"dias_pereira_1530", empresa, {"itau"}, {"itau": "508"}' in app
    assert '"banco": "itau_1530", "conta": "508"' in app
