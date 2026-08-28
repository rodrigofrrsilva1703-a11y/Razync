from pathlib import Path
import re

path = Path('app.py')
text = path.read_text(encoding='utf-8')

assinatura_nova = '''    assinatura_itau = (
        (
            'LANCAMENTOS DO PERIODO' in cabecalho
            and 'RAZAO SOCIAL' in cabecalho
            and 'CNPJ/CPF' in cabecalho
            and 'VALOR (R$)' in cabecalho
            and 'SALDO (R$)' in cabecalho
            and ('LIMITE DA CONTA' in cabecalho or 'SALDO TOTAL' in cabecalho)
        )
        or (
            'LANCAMENTOS PERIODO' in cabecalho
            and 'CONTA CORRENTE' in cabecalho
            and 'AG/ORIGEM' in cabecalho
            and 'VALOR (R$)' in cabecalho
            and 'SALDO (R$)' in cabecalho
            and ('SISPAG' in cabecalho or 'APLIC AUT' in cabecalho)
        )
    )
    if assinatura_itau:
        return 'BANCO ITAU' '''

padrao_assinatura = re.compile(
    r"    assinatura_itau = \(\n.*?\n    \)\n    if assinatura_itau:\n        return 'BANCO ITAU'",
    re.S,
)
text, qtd = padrao_assinatura.subn(assinatura_nova.rstrip(), text, count=1)
if qtd != 1:
    raise SystemExit(f'Assinatura Itaú não substituída: {qtd}')

nova_funcao = r'''def processar_pdf_itau_detalhado(reader, banco_identificado):
    """Lê os formatos detalhados do Itaú Empresas sem importar linhas de saldo."""
    textos = [(pagina.extract_text() or '') for pagina in reader.pages]
    texto_total = '\n'.join(textos)
    texto_norm = normalizar_texto(texto_total)

    assinatura_moderno = (
        'lancamentos do periodo' in texto_norm
        and 'razao social' in texto_norm
        and 'valor (r$)' in texto_norm
        and 'saldo (r$)' in texto_norm
    )
    assinatura_abreviado = (
        'lancamentos periodo' in texto_norm
        and 'conta corrente' in texto_norm
        and 'ag/origem' in texto_norm
        and 'valor (r$)' in texto_norm
        and 'saldo (r$)' in texto_norm
        and ('sispag' in texto_norm or 'aplic aut' in texto_norm)
    )
    if (
        banco_identificado not in {'BANCO ITAU', 'BANCO ITAÚ'}
        and 'itau' not in texto_norm
        and not assinatura_moderno
        and not assinatura_abreviado
    ):
        return []

    termos_saldo = [
        'saldo anterior', 'saldo aplic', 'saldo aplic. aut',
        'saldo total disponivel dia', 'saldo movimentacao conta',
        'sdo aplic aut mais ap', 'saldo em conta corrente',
        'saldo da conta corrente', 'saldo disponivel sem investimentos',
        'saldo em aplicacao automatica', 'valor total em aplicacoes automaticas',
        'saldo total disponivel', 'saldo total', 'limite da conta',
        'total disponivel para uso', 'utilizado', 'disponivel',
    ]
    padrao_valor = re.compile(r'(?<!\d)([-+]?\s*\d{1,3}(?:\.\d{3})*,\d{2})(?!\d)')

    # Formato Itaú Empresas em que o PDF extrai datas como "02 / mar" e,
    # frequentemente, cola a data DEPOIS do valor: "-1.621,0002 / mar".
    # O período declarado no cabeçalho define o ano e também impede que a seção
    # de lançamentos futuros (por exemplo, abril em um extrato de março) seja lida.
    periodo_match = re.search(
        r'lancamentos\s+periodo\s*:\s*(\d{2}/\d{2}/\d{4})\s+ate\s+(\d{2}/\d{2}/\d{4})',
        texto_norm,
        re.IGNORECASE,
    )
    if assinatura_abreviado and periodo_match:
        try:
            periodo_inicio = datetime.strptime(periodo_match.group(1), '%d/%m/%Y').date()
            periodo_fim = datetime.strptime(periodo_match.group(2), '%d/%m/%Y').date()
        except ValueError:
            periodo_inicio = periodo_fim = None

        if periodo_inicio and periodo_fim:
            meses = {
                'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4,
                'mai': 5, 'jun': 6, 'jul': 7, 'ago': 8,
                'set': 9, 'out': 10, 'nov': 11, 'dez': 12,
            }
            moeda = r'[-+]?\d{1,3}(?:\.\d{3})*,\d{2}'
            padrao_data_sufixo = re.compile(
                rf'^(?P<hist>.+?)\s+(?P<valor>{moeda})(?P<dia>\d{{2}})\s*/\s*(?P<mes>[A-Za-zÀ-ÿ#]+)$'
            )
            padrao_data_prefixo = re.compile(
                rf'^(?P<dia>\d{{2}})\s*/\s*(?P<mes>[A-Za-zÀ-ÿ#]+)\s+(?P<hist>.+?)\s+(?P<valor>{moeda})$'
            )

            def resolver_data_curta(dia_raw, mes_raw):
                mes_norm = normalizar_texto(str(mes_raw)).replace('#', '')[:3]
                numero_mes = meses.get(mes_norm)
                if not numero_mes:
                    return None
                for ano in sorted({periodo_inicio.year, periodo_fim.year}):
                    try:
                        candidato = datetime(ano, numero_mes, int(dia_raw)).date()
                    except ValueError:
                        continue
                    if periodo_inicio <= candidato <= periodo_fim:
                        return candidato
                return None

            lancamentos_abreviados = []
            for texto_pagina in textos:
                for linha_bruta in texto_pagina.splitlines():
                    linha = re.sub(r'\s+', ' ', linha_bruta).strip()
                    if not linha:
                        continue
                    correspondencia = padrao_data_sufixo.match(linha)
                    if correspondencia is None:
                        correspondencia = padrao_data_prefixo.match(linha)
                    if correspondencia is None:
                        continue

                    data_lancamento = resolver_data_curta(
                        correspondencia.group('dia'), correspondencia.group('mes')
                    )
                    if data_lancamento is None:
                        continue

                    historico = re.sub(r'\s+', ' ', correspondencia.group('hist')).strip(' -|')
                    historico_norm = normalizar_texto(historico)
                    if not historico or any(termo in historico_norm for termo in termos_saldo):
                        continue

                    valor = limpar_valor_monetario(correspondencia.group('valor'))
                    if abs(valor) < 0.005:
                        continue

                    lancamentos_abreviados.append({
                        'DESCRIÇÃO': banco_identificado if banco_identificado in {'BANCO ITAU', 'BANCO ITAÚ'} else 'BANCO ITAU',
                        'DATA': data_lancamento.strftime('%d/%m/%Y'),
                        'VALOR': valor,
                        'DÉBITO': '',
                        'CRÉDITO': '',
                        'HISTÓRICO': limpar_caracteres_ilegais(historico),
                    })

            if lancamentos_abreviados:
                return lancamentos_abreviados

    # Formato detalhado atual, com datas completas no início da linha.
    linhas_por_pagina = [
        [re.sub(r'\s+', ' ', linha).strip() for linha in texto.splitlines() if linha.strip()]
        for texto in textos
    ]
    padrao_data = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(.*)$')
    blocos = []
    atual = None

    for linhas_pagina in linhas_por_pagina:
        for linha in linhas_pagina:
            m = padrao_data.match(linha)
            if m:
                # Na quebra de página o Itaú pode repetir a mesma data para
                # continuar um lançamento cujo valor ficou na página seguinte.
                atual_sem_valor = bool(atual) and not padrao_valor.search(atual[1])
                if atual_sem_valor and atual[0] == m.group(1):
                    atual[1] += ' ' + m.group(2)
                    continue
                if atual:
                    blocos.append(atual)
                atual = [m.group(1), m.group(2)]
            elif atual:
                atual[1] += ' ' + linha
    if atual:
        blocos.append(atual)

    lancamentos = []
    for data_str, conteudo in blocos:
        conteudo_norm = normalizar_texto(conteudo)
        if any(termo in conteudo_norm for termo in termos_saldo):
            continue
        if conteudo_norm.startswith(('aviso', 'atualizado em')):
            continue

        valores = list(padrao_valor.finditer(conteudo))
        if not valores:
            continue

        valor_match = valores[-1]
        valor = limpar_valor_monetario(valor_match.group(1))
        if abs(valor) < 0.005:
            continue

        historico = (conteudo[:valor_match.start()] + ' ' + conteudo[valor_match.end():]).strip()
        historico = re.sub(r'\s+', ' ', historico).strip(' -|')
        if not historico:
            historico = 'MOVIMENTO BANCARIO'

        lancamentos.append({
            'DESCRIÇÃO': banco_identificado or 'BANCO ITAU',
            'DATA': data_str,
            'VALOR': valor,
            'DÉBITO': '',
            'CRÉDITO': '',
            'HISTÓRICO': limpar_caracteres_ilegais(historico),
        })

    return lancamentos
'''

inicio = text.index('def processar_pdf_itau_detalhado(')
fim = text.index('\ndef processar_pdf_daycoval_detalhado', inicio)
text = text[:inicio] + nova_funcao.rstrip() + '\n' + text[fim:]
path.write_text(text, encoding='utf-8')
