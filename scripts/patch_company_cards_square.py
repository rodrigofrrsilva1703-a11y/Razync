from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

# Adiciona um parser específico para o extrato mensal do Bradesco. Esse layout
# possui uma segunda seção chamada "Últimos Lançamentos" depois de uma linha
# "Total"; nela pode estar o último dia do mês (como 30/04), que não pode ser
# descartado. A leitura percorre o PDF inteiro e usa sempre o penúltimo valor
# monetário como movimento e o último como saldo acumulado.
marcador = '\ndef processar_extrato_conferencia_empresa(file_bytes, filename):\n'
if marcador not in text:
    raise SystemExit('Função de conferência não localizada.')

parser_bradesco = r'''
def processar_pdf_bradesco_mensal(reader, banco='BANCO BRADESCO'):
    """Lê o extrato mensal/por período do Bradesco, inclusive Últimos Lançamentos."""
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
                # Não encerra a leitura: o Bradesco pode trazer o último dia do
                # mês logo depois, na seção "Últimos Lançamentos".
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
                # Continuação no começo de página: mantém a data da página anterior.
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
                    r'\s+', ' ', ' '.join(partes_historico + ([trecho_historico] if trecho_historico else []))
                ).strip()
                partes_historico = []

                hist_norm = normalizar_texto(historico)
                if not historico or hist_norm.startswith(('saldo ', 'total ')):
                    continue
                if abs(valor) < 0.005:
                    continue

                try:
                    data = datetime.strptime(data_atual, '%d/%m/%Y')
                except ValueError:
                    continue

                lancamentos.append({
                    'DESCRIÇÃO': banco,
                    'DATA': data,
                    'VALOR': valor,
                    'DÉBITO': '',
                    'CRÉDITO': '',
                    'HISTÓRICO': historico,
                })
            else:
                partes_historico.append(linha)
                if len(partes_historico) > 6:
                    partes_historico = partes_historico[-6:]

    return lancamentos
'''

if 'def processar_pdf_bradesco_mensal(' not in text:
    text = text.replace(marcador, parser_bradesco + marcador, 1)

old = """            if banco in {'BANCO ITAU', 'BANCO ITAÚ'}:
                lancamentos = processar_pdf_itau_detalhado(reader, banco)
            else:
                lancamentos = processar_arquivo_pdf(caminho_temporario, filename)
"""
new = """            if banco in {'BANCO ITAU', 'BANCO ITAÚ'}:
                lancamentos = processar_pdf_itau_detalhado(reader, banco)
            elif banco == 'BANCO BRADESCO':
                lancamentos = processar_pdf_bradesco_mensal(reader, banco)
            else:
                lancamentos = processar_arquivo_pdf(caminho_temporario, filename)
"""
if old not in text:
    raise SystemExit('Bloco de seleção do parser PDF não localizado.')
text = text.replace(old, new, 1)

checks = [
    'def processar_pdf_bradesco_mensal(',
    "elif banco == 'BANCO BRADESCO':",
    'processar_pdf_bradesco_mensal(reader, banco)',
    "normalizada.startswith('ultimos lancamentos')",
    "normalizada.startswith('total ')",
    'moedas[-2]',
]
for check in checks:
    if check not in text:
        raise SystemExit(f'Validação Bradesco falhou: {check}')

path.write_text(text, encoding='utf-8')
print('Parser Bradesco ajustado para preservar o último dia do mês após a seção Total.')
