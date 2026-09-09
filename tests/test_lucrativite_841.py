from pathlib import Path

import pandas as pd

from razync.lucrativite_841 import processar_extrato_inter_841


def test_processa_extrato_inter_real():
    caminho = Path('/workspace/scratch/864557ed301e/upload/EXTRATO BANCO INTER - JUNHO 2026.xlsx')
    if not caminho.exists():
        return
    df = processar_extrato_inter_841(caminho.read_bytes())
    assert len(df) == 28
    assert set(df['DESCRIÇÃO']) == {'BANCO INTER'}
    assert set(df.loc[df['VALOR'] > 0, 'DÉBITO']) == {'506'}
    assert set(df.loc[df['VALOR'] < 0, 'CRÉDITO']) == {'506'}
    assert df.loc[df['VALOR'] > 0, 'HISTÓRICO'].str.startswith('Recebido: ').all()
    assert df.loc[df['VALOR'] < 0, 'HISTÓRICO'].str.startswith('Pago: ').all()
    assert pd.Timestamp('2026-06-03') == df['DATA'].min()


def test_filtra_periodo_inter_real():
    caminho = Path('/workspace/scratch/864557ed301e/upload/EXTRATO BANCO INTER - JUNHO 2026.xlsx')
    if not caminho.exists():
        return
    df = processar_extrato_inter_841(
        caminho.read_bytes(), pd.Timestamp('2026-06-10'), pd.Timestamp('2026-06-18')
    )
    assert df['DATA'].min() >= pd.Timestamp('2026-06-10')
    assert df['DATA'].max() <= pd.Timestamp('2026-06-18')
