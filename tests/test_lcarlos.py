import io

import pandas as pd

from razync.lcarlos import processar_planilhas_lcarlos


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
    assert len(modelo) == 4
    assert modelo['VALOR'].tolist() == [60.0, 40.0, -10.0, 50.0]
    assert modelo.iloc[-1]['DATA'] == '30/07/2026'
    assert 'FORA DO MÊS' not in ' '.join(modelo['HISTÓRICO'])
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
    assert resumo['diferenca_total'] == -10
    assert resumo['grupos_com_alerta'] == 1
    assert conciliacao.iloc[0]['Situação'] == 'Diferença de valor'
    assert conciliacao.iloc[0]['Diferença'] == -10
