from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

marcador = '\ndef processar_extrato_conferencia_empresa(file_bytes, filename):\n'
if marcador not in text:
    raise SystemExit('Função de conferência não localizada.')

parser_bradesco = r'''
def processar_pdf_bradesco_mensal(reader, banco='BANCO BRADESCO'):
    """Lê extrato mensal/por período Bradesco, inclusive Últimos Lançamentos."""
    lancamentos = []
    data_atual = None
    partes_historico = []
    dentro_saldos_invest = False

    regex_data = re.compile(r'^(\d{2}/\d{2}/\d{4})\s*(.*)$')
    regex_moeda = re.compile(r'-?\d{1,3}(?:\.\d{3})*,\d{2}')
    ignorar_prefixos = (
        'extrato de:', 'agência | conta', 'agencia | conta', 'data lançamento',
        'data lancamento', 'folha ', 'extrato mensal / por período',
        'extrato mensal / por periodo', 'nova geração comercial',
        'nova geracao comercial', 'nome do usuário:', 'nome do usuario:',
        'data da operação:', 'data da operacao:', 'os dados acima têm como base',
        'os dados acima tem como base',
    )

    for pagina in reader.pages:
        texto = pagina.extract_text() or ''
        for linha_bruta in texto.splitlines():
            linha = re.sub(r'\s+', ' ', linha_bruta).strip()
            if not linha:
                continue

            normalizada = normalizar_texto(linha)
            if normalizada.startswith('saldos invest facil'):
                dentro_saldos_invest = True
                partes_historico = []
                continue
            if dentro_saldos_invest:
                continue
            if normalizada.startswith(ignorar_prefixos):
                continue
            if normalizada.startswith('ultimos lancamentos'):
                partes_historico = []
                continue
            if normalizada.startswith('total '):
                partes_historico = []
                continue

            match_data = regex_data.match(linha)
            if match_data:
                data_atual = match_data.group(1)
                linha = match_data.group(2).strip()
                normalizada = normalizar_texto(linha)
                if not linha:
                    continue
                if normalizada.startswith('saldo anterior'):
                    partes_historico = []
                    continue

            if not data_atual:
                continue
            if normalizada.startswith('saldo anterior'):
                partes_historico = []
                continue

            moedas = regex_moeda.findall(linha)
            if len(moedas) >= 2:
                valor_txt = moedas[-2]
                valor = limpar_valor_monetario(valor_txt)
                inicio_valor = linha.rfind(valor_txt)
                trecho_historico = linha[:inicio_valor].strip()
                historico = re.sub(
                    r'\s+', ' ',
                    ' '.join(partes_historico + ([trecho_historico] if trecho_historico else []))
                ).strip()
                partes_historico = []

                hist_norm = normalizar_texto(historico)
                if not historico or hist_norm.startswith(('saldo ', 'total ')):
                    continue
                if abs(valor) < 0.005:
                    continue
                try:
                    datetime.strptime(data_atual, '%d/%m/%Y')
                except ValueError:
                    continue

                lancamentos.append({
                    'DESCRIÇÃO': banco,
                    'DATA': data_atual,
                    'VALOR': valor,
                    'DÉBITO': '',
                    'CRÉDITO': '',
                    'HISTÓRICO': limpar_caracteres_ilegais(historico),
                })
            else:
                partes_historico.append(linha)
                if len(partes_historico) > 6:
                    partes_historico = partes_historico[-6:]

    return lancamentos
'''

if 'def processar_pdf_bradesco_mensal(' not in text:
    text = text.replace(marcador, parser_bradesco + marcador, 1)

old_central = '''        if banco_identificado in {'BANCO ITAU', 'BANCO ITAÚ'}:
            lancamentos_itau = processar_pdf_itau_detalhado(
                reader, banco_identificado
            )
            if lancamentos_itau:
                return lancamentos_itau

        # Primeiro tenta o analisador estrutural único, independente do banco.
'''
new_central = '''        if banco_identificado in {'BANCO ITAU', 'BANCO ITAÚ'}:
            lancamentos_itau = processar_pdf_itau_detalhado(
                reader, banco_identificado
            )
            if lancamentos_itau:
                return lancamentos_itau

        if banco_identificado == 'BANCO BRADESCO':
            lancamentos_bradesco = processar_pdf_bradesco_mensal(
                reader, banco_identificado
            )
            if lancamentos_bradesco:
                return lancamentos_bradesco

        # Primeiro tenta o analisador estrutural único, independente do banco.
'''
if old_central in text:
    text = text.replace(old_central, new_central, 1)
elif new_central not in text:
    raise SystemExit('Ponto central de seleção dos parsers PDF não foi localizado.')

old_conf = '''            if banco in {'BANCO ITAU', 'BANCO ITAÚ'}:
                lancamentos = processar_pdf_itau_detalhado(reader, banco)
            else:
                lancamentos = processar_arquivo_pdf(caminho_temporario, filename)
'''
new_conf = '''            if banco in {'BANCO ITAU', 'BANCO ITAÚ'}:
                lancamentos = processar_pdf_itau_detalhado(reader, banco)
            elif banco == 'BANCO BRADESCO':
                lancamentos = processar_pdf_bradesco_mensal(reader, banco)
            else:
                lancamentos = processar_arquivo_pdf(caminho_temporario, filename)
'''
if old_conf in text:
    text = text.replace(old_conf, new_conf, 1)

checks = [
    'def processar_pdf_itau_detalhado(',
    'def processar_pdf_daycoval_detalhado(',
    'def processar_pdf_bradesco_mensal(',
    "if banco_identificado == 'BANCO DAYCOVAL':",
    "if banco_identificado in {'BANCO ITAU', 'BANCO ITAÚ'}:",
    "if banco_identificado == 'BANCO BRADESCO':",
    'lancamentos_bradesco = processar_pdf_bradesco_mensal(',
    'reader, banco_identificado',
    "normalizada.startswith('ultimos lancamentos')",
    "normalizada.startswith('total ')",
    'moedas[-2]',
]
for check in checks:
    if check not in text:
        raise SystemExit(f'Validação dos leitores centrais falhou: {check}')

path.write_text(text, encoding='utf-8')
print('Correções Itaú/Bradesco centralizadas no leitor PDF usado por todas as ferramentas.')
