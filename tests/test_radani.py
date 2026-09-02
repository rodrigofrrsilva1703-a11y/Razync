import pandas as pd

from razync.radani import analisar_desmembramentos


def _extrato(valor=-33000.0, hist='SISPAG SALARIOS'):
    return pd.DataFrame([{
        'DESCRIÇÃO': 'BANCO ITAU',
        'DATA': pd.Timestamp('2026-06-15'),
        'VALOR': valor,
        'DÉBITO': '',
        'CRÉDITO': '',
        'HISTÓRICO': hist,
    }])


def test_sispag_mesmo_dia_fecha_e_desmembra():
    jaguar = pd.DataFrame([
        {'DATA': pd.Timestamp('2026-06-15'), 'HISTÓRICO': 'ALEX JIN VALE', 'VALOR': -13000.0, 'ARQUIVO': 'J', 'ABA': 'Junho'},
        {'DATA': pd.Timestamp('2026-06-15'), 'HISTÓRICO': 'BRUNO FREITAS VALE', 'VALOR': -10000.0, 'ARQUIVO': 'J', 'ABA': 'Junho'},
        {'DATA': pd.Timestamp('2026-06-15'), 'HISTÓRICO': 'EDGAR VALE', 'VALOR': -10000.0, 'ARQUIVO': 'J', 'ABA': 'Junho'},
    ])
    res = analisar_desmembramentos(_extrato(), jaguar, 'Itaú')
    assert len(res.organizado) == 3
    assert round(res.organizado['VALOR'].sum(), 2) == -33000.0
    assert set(res.organizado['HISTÓRICO']) == {'ALEX JIN VALE', 'BRUNO FREITAS VALE', 'EDGAR VALE'}
    assert res.revisoes.empty


def test_composicao_apenas_proxima_data_vai_para_revisao():
    jaguar = pd.DataFrame([
        {'DATA': pd.Timestamp('2026-06-16'), 'HISTÓRICO': 'FUNCIONARIO A VALE', 'VALOR': -20000.0, 'ARQUIVO': 'J', 'ABA': 'Junho'},
        {'DATA': pd.Timestamp('2026-06-16'), 'HISTÓRICO': 'FUNCIONARIO B VALE', 'VALOR': -13000.0, 'ARQUIVO': 'J', 'ABA': 'Junho'},
    ])
    res = analisar_desmembramentos(_extrato(), jaguar, 'Itaú')
    assert len(res.organizado) == 1
    assert res.organizado.iloc[0]['HISTÓRICO'] == 'SISPAG SALARIOS'
    assert len(res.revisoes) == 1
    assert res.revisoes.iloc[0]['STATUS'] == 'Provável - revisar'


def test_pix_identificado_nao_e_desmembrado():
    extrato = _extrato(-150.0, 'PIX ENVIADO JOSE CLAUDIO DA SILVA 032.376.444-47')
    jaguar = pd.DataFrame([
        {'DATA': pd.Timestamp('2026-06-15'), 'HISTÓRICO': 'ITEM A', 'VALOR': -100.0, 'ARQUIVO': 'J', 'ABA': 'Junho'},
        {'DATA': pd.Timestamp('2026-06-15'), 'HISTÓRICO': 'ITEM B', 'VALOR': -50.0, 'ARQUIVO': 'J', 'ABA': 'Junho'},
    ])
    res = analisar_desmembramentos(extrato, jaguar, 'Itaú')
    assert len(res.organizado) == 1
    assert res.organizado.iloc[0]['HISTÓRICO'].startswith('PIX ENVIADO')
    assert res.revisoes.empty


def test_comprovantes_sispag_tem_prioridade():
    comprovantes = pd.DataFrame([
        {'DATA': pd.Timestamp('2026-06-15'), 'HISTÓRICO': 'FUNC A VALE', 'VALOR': -20000.0, 'ARQUIVO': 'C', 'TIPO': 'VALE', 'FONTE': 'Comprovante SISPAG'},
        {'DATA': pd.Timestamp('2026-06-15'), 'HISTÓRICO': 'FUNC B VALE', 'VALOR': -13000.0, 'ARQUIVO': 'C', 'TIPO': 'VALE', 'FONTE': 'Comprovante SISPAG'},
    ])
    jaguar = pd.DataFrame([
        {'DATA': pd.Timestamp('2026-06-15'), 'HISTÓRICO': 'OUTRO A VALE', 'VALOR': -18000.0, 'ARQUIVO': 'J', 'ABA': 'Junho'},
        {'DATA': pd.Timestamp('2026-06-15'), 'HISTÓRICO': 'OUTRO B VALE', 'VALOR': -15000.0, 'ARQUIVO': 'J', 'ABA': 'Junho'},
    ])
    res = analisar_desmembramentos(_extrato(), jaguar, 'Itaú', comprovantes=comprovantes)
    assert set(res.organizado['HISTÓRICO']) == {'FUNC A VALE', 'FUNC B VALE'}
    assert set(res.detalhamentos['FONTE']) == {'Comprovante SISPAG'}
    assert res.revisoes.empty
