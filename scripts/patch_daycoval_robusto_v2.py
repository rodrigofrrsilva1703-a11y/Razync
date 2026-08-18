from pathlib import Path
import re

p = Path('app.py')
s = p.read_text(encoding='utf-8')

inicio = s.find('def processar_pdf_daycoval_detalhado(')
fim = s.find('\ndef processar_pdf_fibra_extrato(', inicio)
if inicio < 0 or fim < 0:
    raise SystemExit('Função Daycoval não localizada para substituição.')

novo = r'''def processar_pdf_daycoval_detalhado(reader, banco_identificado):
    """
    Lê extratos detalhados Dayconnect/Daycoval antigos e recentes.

    Alguns PDFs preservam o texto normalmente; outros inserem espaços entre
    letras, datas e valores (ex.: ``01/ 05 T A R I F A ... - R $  7 , 3 7``).
    O parser normaliza essa fragmentação, preserva lançamentos repetidos reais,
    respeita o período declarado no extrato e usa o modo layout somente como
    fallback quando a extração textual simples não produz lançamentos.
    """
    textos_simples = [(pagina.extract_text() or '') for pagina in reader.pages]
    texto_identificacao = normalizar_texto('\n'.join(textos_simples[:2]))
    if (
        banco_identificado != 'BANCO DAYCOVAL'
        and 'daycoval' not in texto_identificacao
        and 'dayconnect' not in texto_identificacao
    ):
        return []

    padrao_data_inicio = re.compile(
        r'^\s*(\d)\s*(\d)\s*/\s*(\d)\s*(\d)\s+(.*)$'
    )
    padrao_data_completa = re.compile(
        r'(\d)\s*(\d)\s*/\s*(\d)\s*(\d)\s*/\s*(2)\s*(0)\s*(\d)\s*(\d)'
    )
    padrao_moeda = re.compile(
        r'([+-]?\s*R\s*\$\s*[+-]?\s*\d[\d\s.]*,\s*\d\s*\d)',
        re.IGNORECASE
    )

    def desfragmentar_linha(linha):
        texto = str(linha or '').replace('\xa0', ' ')
        tokens = texto.split()
        alfabeticos = [
            token for token in tokens
            if any(caractere.isalpha() for caractere in token)
        ]
        unitarios = [
            token for token in alfabeticos
            if len(re.sub(r'[^A-Za-zÀ-ÿ]', '', token)) == 1
        ]
        fragmentado = bool(alfabeticos) and (
            len(unitarios) / len(alfabeticos) >= 0.45
        )
        if fragmentado:
            # Remove somente ESPAÇO SIMPLES entre letras. Espaços duplos do PDF
            # continuam separando palavras e são colapsados apenas ao final.
            texto = re.sub(
                r'(?<=[A-Za-zÀ-ÿ]) (?=[A-Za-zÀ-ÿ])', '', texto
            )
        return re.sub(r'\s+', ' ', texto).strip()

    def converter_moeda(valor_raw):
        texto = re.sub(r'\s+', '', str(valor_raw).upper()).replace('R$', '')
        sinal = -1.0 if texto.startswith('-') else 1.0
        texto = texto.lstrip('+-').replace('.', '').replace(',', '.')
        try:
            return sinal * float(texto)
        except (TypeError, ValueError):
            return 0.0

    def extrair_data_match(match):
        dia = match.group(1) + match.group(2)
        mes = match.group(3) + match.group(4)
        ano = '20' + match.group(7) + match.group(8)
        try:
            return datetime.strptime(
                f'{dia}/{mes}/{ano}', '%d/%m/%Y'
            ).date()
        except ValueError:
            return None

    def localizar_periodo(texto_total):
        linhas = texto_total.splitlines()
        for indice, linha in enumerate(linhas):
            normalizada = normalizar_texto(desfragmentar_linha(linha))
            if 'periodo' not in normalizada:
                continue
            janela = ' '.join(linhas[indice:indice + 4])
            datas = list(padrao_data_completa.finditer(janela))
            if len(datas) >= 2:
                data_inicial = extrair_data_match(datas[0])
                data_final = extrair_data_match(datas[1])
                if data_inicial and data_final and data_inicial <= data_final:
                    return data_inicial, data_final
        return None

    def processar_fonte(texto_total):
        periodo = localizar_periodo(texto_total)
        if periodo:
            ano_referencia = periodo[0].year
        else:
            data_completa = padrao_data_completa.search(texto_total)
            data_referencia = extrair_data_match(data_completa) if data_completa else None
            ano_referencia = data_referencia.year if data_referencia else datetime.now().year

        blocos = []
        atual = None
        prefixos_fim = (
            'impressao realizada', 'central de atendimento',
            'horario de atendimento', 'sac daycoval',
            'central para deficientes', 'ouvidoria:', 'os saldos acima',
            'saldo anterior', 'extrato detalhado', 'conta corrente',
            'saldo disponivel', 'titular', 'periodo', 'agencia', 'conta ',
            'saldo atual', 'limite ', 'saldo bloqueado', 'valor bloqueado',
            'provisao de encargos', 'lancamentos futuros'
        )

        for linha_bruta in texto_total.splitlines():
            correspondencia = padrao_data_inicio.match(linha_bruta)
            if correspondencia:
                if atual:
                    blocos.append(atual)
                atual = {
                    'dia': correspondencia.group(1) + correspondencia.group(2),
                    'mes': correspondencia.group(3) + correspondencia.group(4),
                    'linhas': [correspondencia.group(5)]
                }
                continue

            if atual:
                linha_normalizada = normalizar_texto(
                    desfragmentar_linha(linha_bruta)
                )
                if (
                    any(linha_normalizada.startswith(prefixo) for prefixo in prefixos_fim)
                    or ('feira' in linha_normalizada and 'saldo:' in linha_normalizada)
                ):
                    blocos.append(atual)
                    atual = None
                    continue
                atual['linhas'].append(linha_bruta)

        if atual:
            blocos.append(atual)

        lancamentos = []
        for bloco in blocos:
            conteudo = ' '.join(bloco['linhas'])
            moedas = list(padrao_moeda.finditer(conteudo))
            if not moedas:
                continue

            # O primeiro valor monetário pertence ao lançamento. Isso evita que
            # um "Saldo Anterior" posterior contamine o último movimento da página.
            moeda = moedas[0]
            valor = converter_moeda(moeda.group(1))
            if abs(valor) < 0.005:
                continue

            historico = desfragmentar_linha(
                conteudo[:moeda.start()]
            ).strip(' -|')
            if not historico:
                continue
            historico_normalizado = normalizar_texto(historico)
            if historico_normalizado.startswith('saldo ') or 'saldo:' in historico_normalizado:
                continue

            try:
                data_lancamento = datetime(
                    ano_referencia,
                    int(bloco['mes']),
                    int(bloco['dia'])
                ).date()
            except ValueError:
                continue

            # Extratos emitidos no início do mês seguinte podem exibir um movimento
            # posterior ao período solicitado. Para conciliação, prevalece o período
            # declarado pelo próprio banco.
            if periodo and not (periodo[0] <= data_lancamento <= periodo[1]):
                continue

            lancamentos.append({
                'DESCRIÇÃO': banco_identificado or 'BANCO DAYCOVAL',
                'DATA': data_lancamento.strftime('%d/%m/%Y'),
                'VALOR': round(valor, 2),
                'DÉBITO': '',
                'CRÉDITO': '',
                'HISTÓRICO': limpar_caracteres_ilegais(historico)
            })

        return lancamentos

    # Prioriza a extração simples: é a mais fiel nos modelos recentes e nos PDFs
    # antigos com texto fragmentado. O layout fica como fallback real, não é somado,
    # portanto lançamentos legítimos repetidos no mesmo dia/valor são preservados.
    texto_simples_total = '\n'.join(textos_simples)
    lancamentos_simples = processar_fonte(texto_simples_total)
    if lancamentos_simples:
        return lancamentos_simples

    textos_layout = []
    for pagina, texto_simples in zip(reader.pages, textos_simples):
        try:
            texto_layout = pagina.extract_text(extraction_mode='layout') or texto_simples
        except (TypeError, ValueError):
            texto_layout = texto_simples
        textos_layout.append(texto_layout)

    return processar_fonte('\n'.join(textos_layout))
'''

s = s[:inicio] + novo + s[fim:]

checks = [
    'def processar_pdf_daycoval_detalhado(reader, banco_identificado):',
    'def desfragmentar_linha(linha):',
    'lancamentos_simples = processar_fonte(texto_simples_total)',
    "if periodo and not (periodo[0] <= data_lancamento <= periodo[1]):",
    "return processar_fonte('\\n'.join(textos_layout))",
]
for check in checks:
    if check not in s:
        raise SystemExit(f'Validação estrutural falhou: {check}')

p.write_text(s, encoding='utf-8')
print('Parser Daycoval robusto V2 aplicado.')
