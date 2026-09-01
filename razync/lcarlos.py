import io
import re
import unicodedata

import pandas as pd


CONTA_SANTANDER_LCARLOS = '513'


def _normalizar(valor):
    texto = unicodedata.normalize('NFKD', str(valor or ''))
    return ''.join(c for c in texto if not unicodedata.combining(c)).casefold().strip()


def _ler_primeira_aba(arquivo_bytes):
    return pd.read_excel(io.BytesIO(arquivo_bytes), sheet_name=0, header=None)


def _data_excel(valor):
    if pd.isna(valor):
        return pd.NaT
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return pd.Timestamp('1899-12-30') + pd.to_timedelta(float(valor), unit='D')
    return pd.to_datetime(valor, dayfirst=True, errors='coerce')


def _historico_lcarlos(historico, valor):
    historico = str(historico or '').strip()
    prefixo = 'Recebido:' if float(valor) > 0 else 'Pago:'
    historico_normalizado = _normalizar(historico)
    if historico_normalizado.startswith('recebido:') or historico_normalizado.startswith('pago:'):
        return historico
    return f'{prefixo} {historico}'.strip()


def _linha_modelo(data, valor, historico):
    valor = round(float(valor), 2)
    return {
        'DATA': data.strftime('%d/%m/%Y'),
        'DÉBITO': CONTA_SANTANDER_LCARLOS if valor > 0 else '',
        'CRÉDITO': CONTA_SANTANDER_LCARLOS if valor < 0 else '',
        'VALOR': valor,
        'HISTÓRICO': _historico_lcarlos(historico, valor),
    }


def processar_planilhas_lcarlos(jaguar_bytes, entradas_bytes):
    jaguar = _ler_primeira_aba(jaguar_bytes)
    cabecalho = None
    for indice, linha in jaguar.iterrows():
        nomes = [_normalizar(v) for v in linha.tolist()]
        if 'data' in nomes and any('valor' in nome for nome in nomes):
            cabecalho = indice
            break
    if cabecalho is None:
        raise ValueError('Cabeçalho da planilha Jaguar não foi localizado.')

    nomes = [_normalizar(v) for v in jaguar.iloc[cabecalho].tolist()]
    col_data = nomes.index('data')
    col_descricao = next(
        (i for i, nome in enumerate(nomes) if 'cliente ou fornecedor' in nome),
        1,
    )
    col_valor = next(i for i, nome in enumerate(nomes) if nome.startswith('valor'))

    movimentos = []
    for ordem, (_, linha) in enumerate(jaguar.iloc[cabecalho + 1:].iterrows()):
        data = _data_excel(linha.iloc[col_data])
        descricao = str(linha.iloc[col_descricao] or '').strip()
        valor = pd.to_numeric(linha.iloc[col_valor], errors='coerce')
        if pd.isna(data) or pd.isna(valor) or not descricao:
            continue
        if _normalizar(descricao) == 'saldo':
            continue
        movimentos.append({
            'data': data.normalize(),
            'descricao': descricao,
            'valor': round(float(valor), 2),
            'ordem': ordem,
        })
    if not movimentos:
        raise ValueError('Nenhum movimento válido foi localizado na planilha Jaguar.')

    meses = pd.Series([(m['data'].year, m['data'].month) for m in movimentos])
    ano_periodo, mes_periodo = meses.value_counts().index[0]
    movimentos = [
        m for m in movimentos
        if m['data'].year == ano_periodo and m['data'].month == mes_periodo
    ]
    inicio_periodo = pd.Timestamp(ano_periodo, mes_periodo, 1)
    fim_periodo = inicio_periodo + pd.offsets.MonthEnd(0)

    entradas = _ler_primeira_aba(entradas_bytes)
    grupos = {}
    data_atual = pd.NaT
    for _, linha in entradas.iloc[2:].iterrows():
        bruto_data = linha.iloc[0] if len(linha) > 0 else None
        if pd.notna(bruto_data) and str(bruto_data).strip() not in {'', '.'}:
            candidata = _data_excel(bruto_data)
            if not pd.isna(candidata):
                data_atual = candidata.normalize()
        valor = pd.to_numeric(linha.iloc[1] if len(linha) > 1 else None, errors='coerce')
        historico = str(linha.iloc[2] if len(linha) > 2 and pd.notna(linha.iloc[2]) else '').strip()
        cliente = str(linha.iloc[3] if len(linha) > 3 and pd.notna(linha.iloc[3]) else '').strip()
        if pd.isna(data_atual) or pd.isna(valor) or not historico:
            continue
        historico_norm = _normalizar(historico)
        if 'total' in historico_norm or historico_norm.startswith('entrou'):
            continue
        if not (inicio_periodo <= data_atual <= fim_periodo):
            continue
        grupos.setdefault(data_atual, []).append({
            'valor': round(float(valor), 2),
            'historico': ' '.join(parte for parte in [cliente, historico] if parte).strip(),
        })

    grupos_info = [
        {
            'data': data,
            'detalhes': detalhes,
            'total': round(sum(item['valor'] for item in detalhes), 2),
            'usado': False,
        }
        for data, detalhes in sorted(grupos.items())
    ]

    linhas_modelo = []
    conciliacao = []
    for movimento in movimentos:
        descricao_norm = _normalizar(movimento['descricao'])
        if 'recebimento vendas nf' not in descricao_norm:
            linhas_modelo.append(
                _linha_modelo(
                    movimento['data'],
                    movimento['valor'],
                    movimento['descricao'],
                )
            )
            continue

        disponiveis = [grupo for grupo in grupos_info if not grupo['usado']]
        exatos = [
            grupo for grupo in disponiveis
            if abs(grupo['total'] - movimento['valor']) <= 0.01
        ]
        grupo = None
        if exatos:
            grupo = min(
                exatos,
                key=lambda item: (
                    item['data'] != movimento['data'],
                    abs((item['data'] - movimento['data']).days),
                ),
            )
        else:
            grupo = next(
                (item for item in disponiveis if item['data'] == movimento['data']),
                None,
            )

        if grupo is None:
            linhas_modelo.append(
                _linha_modelo(
                    movimento['data'],
                    movimento['valor'],
                    movimento['descricao'],
                )
            )
            conciliacao.append({
                'Data Jaguar': movimento['data'].strftime('%d/%m/%Y'),
                'Data Entradas': '',
                'Total Jaguar': movimento['valor'],
                'Total detalhado': 0.0,
                'Diferença': -movimento['valor'],
                'Situação': 'Sem detalhamento',
            })
            continue

        grupo['usado'] = True
        diferenca = round(grupo['total'] - movimento['valor'], 2)
        data_ajustada = grupo['data'] != movimento['data']
        situacao = 'Conciliado'
        if abs(diferenca) > 0.01:
            situacao = 'Diferença de valor'
        elif data_ajustada:
            situacao = 'Data ajustada pela Jaguar'

        for detalhe in grupo['detalhes']:
            linhas_modelo.append(
                _linha_modelo(
                    movimento['data'],
                    detalhe['valor'],
                    detalhe['historico'],
                )
            )
        conciliacao.append({
            'Data Jaguar': movimento['data'].strftime('%d/%m/%Y'),
            'Data Entradas': grupo['data'].strftime('%d/%m/%Y'),
            'Total Jaguar': movimento['valor'],
            'Total detalhado': grupo['total'],
            'Diferença': diferenca,
            'Situação': situacao,
        })

    grupos_nao_usados = [grupo for grupo in grupos_info if not grupo['usado']]
    for grupo in grupos_nao_usados:
        conciliacao.append({
            'Data Jaguar': '',
            'Data Entradas': grupo['data'].strftime('%d/%m/%Y'),
            'Total Jaguar': 0.0,
            'Total detalhado': grupo['total'],
            'Diferença': grupo['total'],
            'Situação': 'Sem correspondente na Jaguar',
        })

    df_modelo = pd.DataFrame(linhas_modelo)
    df_conciliacao = pd.DataFrame(conciliacao)
    total_jaguar = round(sum(m['valor'] for m in movimentos), 2)
    total_modelo = round(float(df_modelo['VALOR'].sum()), 2)
    resumo = {
        'periodo': inicio_periodo.strftime('%m/%Y'),
        'inicio': inicio_periodo.date(),
        'fim': fim_periodo.date(),
        'total_jaguar': total_jaguar,
        'total_modelo': total_modelo,
        'diferenca_total': round(total_modelo - total_jaguar, 2),
        'lancamentos_jaguar': len(movimentos),
        'lancamentos_modelo': len(df_modelo),
        'grupos_com_alerta': int((df_conciliacao['Situação'] != 'Conciliado').sum()),
        'banco': 'Santander',
        'conta_bancaria': CONTA_SANTANDER_LCARLOS,
    }
    return df_modelo, df_conciliacao, resumo
