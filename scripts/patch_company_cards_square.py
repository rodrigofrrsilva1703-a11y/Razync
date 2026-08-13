from pathlib import Path
import re

p = Path('app.py')
s = p.read_text(encoding='utf-8')

padrao = re.compile(
    r"def processar_pdf_bradesco_mensal\(reader, banco='BANCO BRADESCO'\):.*?\n(?=def processar_extrato_conferencia_empresa)",
    re.S,
)

novo = '''def processar_pdf_bradesco_mensal(reader, banco='BANCO BRADESCO'):
    """Lê extratos PDF mensais do Bradesco validando cada movimento pelo saldo."""
    lancamentos = []
    data_atual = None
    partes_historico = []
    ultimo_saldo = None
    dentro_saldos_invest = False

    regex_data = re.compile(r'^(\\d{2}/\\d{2}/\\d{4})\\s*(.*)$')
    regex_moeda = re.compile(r'-?\\d{1,3}(?:\\.\\d{3})*,\\d{2}')
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
            linha = re.sub(r'\\s+', ' ', linha_bruta).strip()
            if not linha:
                continue

            normalizada = normalizar_texto(linha)

            if normalizada.startswith('saldos invest facil'):
                dentro_saldos_invest = True
                partes_historico = []
                continue
            if normalizada.startswith('ultimos lancamentos'):
                dentro_saldos_invest = False
                partes_historico = []
                continue
            if normalizada.startswith(('data lancamento', 'data lançamento')):
                dentro_saldos_invest = False
                partes_historico = []
                continue
            if dentro_saldos_invest:
                continue
            if normalizada.startswith(ignorar_prefixos):
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
                moedas_saldo = regex_moeda.findall(linha)
                if moedas_saldo:
                    ultimo_saldo = limpar_valor_monetario(moedas_saldo[-1])
                partes_historico = []
                continue

            if not data_atual:
                continue

            moedas = regex_moeda.findall(linha)
            if len(moedas) >= 2:
                valor_txt = moedas[-2]
                saldo_txt = moedas[-1]
                valor_impresso = limpar_valor_monetario(valor_txt)
                saldo_atual = limpar_valor_monetario(saldo_txt)
                valor = valor_impresso
                if ultimo_saldo is not None:
                    variacao = round(saldo_atual - ultimo_saldo, 2)
                    if abs(abs(variacao) - abs(valor_impresso)) <= 0.02:
                        valor = variacao

                inicio_valor = linha.rfind(valor_txt)
                trecho_historico = linha[:inicio_valor].strip()
                historico = re.sub(
                    r'\\s+', ' ',
                    ' '.join(partes_historico + ([trecho_historico] if trecho_historico else []))
                ).strip()
                partes_historico = []
                ultimo_saldo = saldo_atual

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
                    'VALOR': round(valor, 2),
                    'DÉBITO': '',
                    'CRÉDITO': '',
                    'HISTÓRICO': historico,
                })
            else:
                partes_historico.append(linha)
                if len(partes_historico) > 8:
                    partes_historico = partes_historico[-8:]

    return lancamentos

'''

s, n = padrao.subn(lambda _m: novo, s, count=1)
if n != 1:
    raise SystemExit(f'Leitor Bradesco encontrado {n} vezes.')

checks = [
    'variacao = round(saldo_atual - ultimo_saldo, 2)',
    "normalizada.startswith('saldo anterior')",
    "normalizada.startswith('ultimos lancamentos')",
    "'VALOR': round(valor, 2)",
]
for check in checks:
    if check not in s:
        raise SystemExit(f'Validação Bradesco falhou: {check}')

p.write_text(s, encoding='utf-8')
print('Leitor PDF Bradesco reforçado com validação pela variação do saldo.')
