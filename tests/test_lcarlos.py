import io

import pandas as pd

from razync.lcarlos import CONTA_SANTANDER_LCARLOS, processar_planilhas_lcarlos


def arquivo_excel(linhas):
    saida = io.BytesIO()
    pd.DataFrame(linhas).to_excel(saida, index=False, header=False)
    return saida.getvalue()


def test_substitui_recebimentos_e_usa_data_da_jaguar():
    jaguar = arquivo_excel([
        ['', 'Banco Santander', '', '', '', ''],
        ['', '', '', '', '', ''],
        ['Data', 'Cliente ou Fornecedor (Razão Social ou Nome Fantasia)', '', '', 'Valor (R$)', 'Saldo (R$)'],
        ['', '', '', '', '', ''],
        [pd.Timestamp('2026-06-30'), 'SALDO', '', '', '', 1000],
        [pd.Timestamp('2026-07-02'), 'RECEBIMENTO VENDAS NF', '', '', 100, 1100],
        [pd.Timestamp('2026-07-02'), 'PAGAMENTO TESTE', '', '', -10, 1090],
        [pd.Timestamp('2026-07-30'), 'RECEBIMENTO VENDAS NF', '', '', 50, 1140],
    ])
    entradas = arquivo_excel([
        ['RECEBIMENTOS', 'LCARLOS', 'JULHO', ''],
        ['', '', '', ''],
        [pd.Timestamp('2026-07-02'), 60, 'BOLETO NF 1', 'CLIENTE A'],
        ['', 40, 'BOLETO NF 2', 'CLIENTE B'],
        ['', '', 'TOTAL 100', ''],
        [pd.Timestamp('2026-07-29'), 50, 'BOLETO NF 3', 'CLIENTE C'],
        ['', '', 'TOTAL 50', ''],
        [pd.Timestamp('2026-08-01'), 20, 'BOLETO NF 4', 'FORA DO MÊS'],
    ])

    modelo, conciliacao, resumo = processar_planilhas_lcarlos(jaguar, entradas)

    assert resumo['periodo'] == '07/2026'
    assert resumo['diferenca_total'] == 0
    assert resumo['banco'] == 'Santander'
    assert resumo['conta_bancaria'] == CONTA_SANTANDER_LCARLOS == '513'
    assert len(modelo) == 4
    assert modelo['VALOR'].tolist() == [60.0, 40.0, -10.0, 50.0]
    assert modelo.iloc[-1]['DATA'] == '30/07/2026'
    assert 'FORA DO MÊS' not in ' '.join(modelo['HISTÓRICO'])
    assert modelo['HISTÓRICO'].tolist() == [
        'Recebido: CLIENTE A BOLETO NF 1',
        'Recebido: CLIENTE B BOLETO NF 2',
        'Pago: PAGAMENTO TESTE',
        'Recebido: CLIENTE C BOLETO NF 3',
    ]
    assert modelo['DÉBITO'].tolist() == ['513', '513', '', '513']
    assert modelo['CRÉDITO'].tolist() == ['', '', '513', '']
    assert 'Data ajustada pela Jaguar' in conciliacao['Situação'].tolist()


def test_permite_diferenca_e_informa_conferencia():
    jaguar = arquivo_excel([
        ['', 'Banco Santander', '', '', '', ''],
        ['', '', '', '', '', ''],
        ['Data', 'Cliente ou Fornecedor (Razão Social ou Nome Fantasia)', '', '', 'Valor (R$)', 'Saldo (R$)'],
        ['', '', '', '', '', ''],
        [pd.Timestamp('2026-07-16'), 'RECEBIMENTO VENDAS NF', '', '', 100, 100],
    ])
    entradas = arquivo_excel([
        ['RECEBIMENTOS', 'LCARLOS', 'JULHO', ''],
        ['', '', '', ''],
        [pd.Timestamp('2026-07-16'), 90, 'BOLETO NF 1', 'CLIENTE A'],
        ['', '', 'TOTAL 90', ''],
    ])

    modelo, conciliacao, resumo = processar_planilhas_lcarlos(jaguar, entradas)

    assert modelo['VALOR'].sum() == 90
    assert modelo.iloc[0]['HISTÓRICO'] == 'Recebido: CLIENTE A BOLETO NF 1'
    assert modelo.iloc[0]['DÉBITO'] == '513'
    assert modelo.iloc[0]['CRÉDITO'] == ''
    assert resumo['diferenca_total'] == -10
    assert resumo['grupos_com_alerta'] == 1
    assert conciliacao.iloc[0]['Situação'] == 'Diferença de valor'
    assert conciliacao.iloc[0]['Diferença'] == -10


def test_funciona_em_outro_periodo_sem_regra_fixa_de_julho():
    jaguar = arquivo_excel([
        ['Data', 'Cliente ou Fornecedor (Razão Social ou Nome Fantasia)', '', '', 'Valor (R$)', 'Saldo (R$)'],
        [pd.Timestamp('2026-08-05'), 'RECEBIMENTO VENDAS NF', '', '', 75, 75],
        [pd.Timestamp('2026-08-06'), 'TARIFA BANCARIA', '', '', -5, 70],
    ])
    entradas = arquivo_excel([
        ['RECEBIMENTOS', 'LCARLOS', 'AGOSTO', ''],
        ['', '', '', ''],
        [pd.Timestamp('2026-08-05'), 75, 'NF 123', 'CLIENTE AGOSTO'],
    ])

    modelo, _, resumo = processar_planilhas_lcarlos(jaguar, entradas)

    assert resumo['periodo'] == '08/2026'
    assert modelo['VALOR'].tolist() == [75.0, -5.0]
    assert modelo['HISTÓRICO'].tolist() == [
        'Recebido: CLIENTE AGOSTO NF 123',
        'Pago: TARIFA BANCARIA',
    ]
    assert modelo['DÉBITO'].tolist() == ['513', '']
    assert modelo['CRÉDITO'].tolist() == ['', '513']
