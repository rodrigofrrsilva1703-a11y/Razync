from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

# -----------------------------------------------------------------------------
# 1) Cria um ÚNICO ponto de entrada para qualquer extrato enviado pelo usuário.
#    Ele recebe bytes + nome original e encaminha para os parsers centrais.
# -----------------------------------------------------------------------------
marcador = '\ndef gerar_txt_dominio(df):\n'
if marcador not in text:
    raise SystemExit('Ponto após processar_arquivo_pdf não localizado.')

funcao_unificada = r'''
def processar_extrato_unificado(file_bytes, filename):
    """Leitor único de extratos usado por todas as ferramentas do Razync."""
    extensao = os.path.splitext(filename)[1].lower()
    if extensao == '.ofx':
        return processar_ofx(file_bytes, filename)
    if extensao in ['.csv', '.xlsx', '.xls']:
        return processar_planilha_universal(file_bytes, filename)
    if extensao != '.pdf':
        return []

    caminho_temporario = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temporario:
            temporario.write(file_bytes)
            caminho_temporario = temporario.name
        # O nome ORIGINAL é sempre passado. Isso evita que um arquivo temporário
        # faça o identificador perder banco/conta e cair no parser errado.
        return processar_arquivo_pdf(caminho_temporario, filename)
    finally:
        if caminho_temporario and os.path.exists(caminho_temporario):
            os.remove(caminho_temporario)
'''

if 'def processar_extrato_unificado(' not in text:
    text = text.replace(marcador, funcao_unificada + marcador, 1)

# -----------------------------------------------------------------------------
# 2) A Conferência passa pelo mesmo leitor único e apenas remove linhas-resumo.
# -----------------------------------------------------------------------------
inicio_conf = text.find('def processar_extrato_conferencia_empresa(file_bytes, filename):')
fim_conf = text.find('\ndef conciliar_empresa_com_extrato(', inicio_conf)
if inicio_conf < 0 or fim_conf < 0:
    raise SystemExit('Função de conferência não localizada para unificação.')

nova_conf = r'''def processar_extrato_conferencia_empresa(file_bytes, filename):
    """Lê a conferência pelo mesmo motor central usado em todo o Razync."""
    termos_saldo = [
        'saldo anterior', 'saldo aplic', 'saldo invest', 'saldo total disponivel',
        'saldo movimentacao conta', 'sdo aplic aut mais ap', 'saldo final',
        'saldo do dia', 'saldo total', 'saldo disponivel', 'saldo em conta',
    ]
    filtrados = []
    for item in processar_extrato_unificado(file_bytes, filename) or []:
        historico = normalizar_texto(texto_celula_seguro(item.get('HISTÓRICO', '')))
        if any(termo in historico for termo in termos_saldo):
            continue
        valor = limpar_valor_monetario(item.get('VALOR', 0))
        if abs(valor) < 0.005:
            continue
        filtrados.append(item)
    return filtrados
'''
text = text[:inicio_conf] + nova_conf + text[fim_conf:]

# -----------------------------------------------------------------------------
# 3) Conversor de Extratos: remove caminhos próprios de PDF/OFX/Excel.
# -----------------------------------------------------------------------------
old_converter = '''                if extensao == '.ofx':
                    lancamentos = executar_com_loading(
                        f"Lendo {arquivo.name}...", processar_ofx, file_bytes, arquivo.name
                    )
                elif extensao in ['.csv', '.xlsx', '.xls']:
                    lancamentos = executar_com_loading(
                        f"Lendo {arquivo.name}...",
                        processar_planilha_universal,
                        file_bytes,
                        arquivo.name
                    )
                elif extensao == '.pdf':
                    caminho_temp = f"temp_{arquivo.name}"
                    with open(caminho_temp, "wb") as f: f.write(file_bytes)
                    data_ini_doc, data_fim_doc = extrair_periodo_extrato(caminho_temp)
                    lancamentos = executar_com_loading(
                        f"Analisando {arquivo.name}...", processar_arquivo_pdf, caminho_temp
                    )
                    if os.path.exists(caminho_temp): os.remove(caminho_temp)
'''
new_converter = '''                if extensao == '.pdf':
                    caminho_periodo = None
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_periodo:
                            temp_periodo.write(file_bytes)
                            caminho_periodo = temp_periodo.name
                        data_ini_doc, data_fim_doc = extrair_periodo_extrato(caminho_periodo)
                    finally:
                        if caminho_periodo and os.path.exists(caminho_periodo):
                            os.remove(caminho_periodo)

                lancamentos = executar_com_loading(
                    f"Analisando {arquivo.name}...",
                    processar_extrato_unificado,
                    file_bytes,
                    arquivo.name
                )
'''
if old_converter not in text:
    raise SystemExit('Bloco antigo do Conversor não localizado.')
text = text.replace(old_converter, new_converter, 1)

# -----------------------------------------------------------------------------
# 4) Conciliação com Razão: usa exatamente o mesmo leitor único.
# -----------------------------------------------------------------------------
old_razao = '''            lancamentos_ext = []
            if ext_ext == '.ofx':
                lancamentos_ext = executar_com_loading(
                    "Lendo o extrato bancário...", processar_ofx, ext_bytes, arq_extrato.name
                )
            elif ext_ext in ['.csv', '.xlsx', '.xls']:
                lancamentos_ext = executar_com_loading(
                    "Lendo o extrato bancário...",
                    processar_planilha_universal,
                    ext_bytes,
                    arq_extrato.name
                )
            elif ext_ext == '.pdf':
                tmp_ext = f"temp_ext_conc_{arq_extrato.name}"
                with open(tmp_ext, "wb") as f: f.write(ext_bytes)
                lancamentos_ext = executar_com_loading(
                    "Analisando o extrato bancário...", processar_arquivo_pdf, tmp_ext
                )
                if os.path.exists(tmp_ext): os.remove(tmp_ext)
'''
new_razao = '''            lancamentos_ext = executar_com_loading(
                "Analisando o extrato bancário...",
                processar_extrato_unificado,
                ext_bytes,
                arq_extrato.name
            )
'''
if old_razao not in text:
    raise SystemExit('Bloco antigo da Conciliação com Razão não localizado.')
text = text.replace(old_razao, new_razao, 1)

# -----------------------------------------------------------------------------
# 5) Garantias: Itaú, Bradesco e Daycoval continuam no leitor PDF central.
# -----------------------------------------------------------------------------
checks = [
    'def processar_extrato_unificado(',
    'return processar_arquivo_pdf(caminho_temporario, filename)',
    "if banco_identificado == 'BANCO DAYCOVAL':",
    "if banco_identificado in {'BANCO ITAU', 'BANCO ITAÚ'}:",
    "if banco_identificado == 'BANCO BRADESCO':",
    'processar_pdf_itau_detalhado(',
    'processar_pdf_bradesco_mensal(',
    'processar_pdf_daycoval_detalhado(',
    'for item in processar_extrato_unificado(file_bytes, filename) or []:',
]
for check in checks:
    if check not in text:
        raise SystemExit(f'Validação da unificação falhou: {check}')

# Não pode restar nos dois fluxos principais chamada direta ao PDF por arquivo temporário.
if 'processar_arquivo_pdf, caminho_temp' in text:
    raise SystemExit('Conversor ainda possui chamada direta antiga ao leitor PDF.')
if 'processar_arquivo_pdf, tmp_ext' in text:
    raise SystemExit('Conciliação com Razão ainda possui chamada direta antiga ao leitor PDF.')

path.write_text(text, encoding='utf-8')
print('Leitor de extratos unificado em Conversor, Conferência e Conciliação com Razão.')
