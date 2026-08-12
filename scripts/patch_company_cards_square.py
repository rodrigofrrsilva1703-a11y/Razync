from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old = '''def processar_extrato_conferencia_empresa(file_bytes, filename):
    """Lê o extrato usado na conferência com os mesmos motores do conversor."""
    extensao = os.path.splitext(filename)[1].lower()
    if extensao == '.ofx':
        return processar_ofx(file_bytes, filename)
    if extensao in ['.csv', '.xlsx', '.xls']:
        return processar_planilha_universal(file_bytes, filename)
    if extensao == '.pdf':
        caminho_temporario = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temporario:
                temporario.write(file_bytes)
                caminho_temporario = temporario.name
            return processar_arquivo_pdf(caminho_temporario, filename)
        finally:
            if caminho_temporario and os.path.exists(caminho_temporario):
                os.remove(caminho_temporario)
    return []
'''
new = '''def processar_extrato_conferencia_empresa(file_bytes, filename):
    """Lê o extrato usado na conferência sem transformar linhas de saldo em movimento."""
    extensao = os.path.splitext(filename)[1].lower()

    def remover_linhas_de_saldo(lancamentos):
        termos_saldo = [
            'saldo anterior',
            'saldo aplic',
            'saldo total disponivel',
            'saldo movimentacao conta',
            'sdo aplic aut mais ap',
            'saldo final',
            'saldo do dia',
            'saldo total',
            'saldo disponivel',
            'saldo em conta',
        ]
        filtrados = []
        for item in lancamentos or []:
            historico = normalizar_texto(texto_celula_seguro(item.get('HISTÓRICO', '')))
            if any(termo in historico for termo in termos_saldo):
                continue
            valor = limpar_valor_monetario(item.get('VALOR', 0))
            if abs(valor) < 0.005:
                continue
            filtrados.append(item)
        return filtrados

    if extensao == '.ofx':
        return remover_linhas_de_saldo(processar_ofx(file_bytes, filename))
    if extensao in ['.csv', '.xlsx', '.xls']:
        return remover_linhas_de_saldo(processar_planilha_universal(file_bytes, filename))
    if extensao == '.pdf':
        caminho_temporario = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temporario:
                temporario.write(file_bytes)
                caminho_temporario = temporario.name

            # Para PDF Itaú detalhado, força o parser específico também na conferência.
            # Assim os saldos de aplicação, saldo anterior, saldo disponível e saldo
            # de movimentação nunca entram no total comparado com a planilha.
            reader = PdfReader(caminho_temporario, strict=False)
            texto_amostra = '\\n'.join((pagina.extract_text() or '') for pagina in reader.pages[:2])
            banco = identificar_banco_inteligente(texto_amostra, filename)
            if banco in {'BANCO ITAU', 'BANCO ITAÚ'}:
                lancamentos = processar_pdf_itau_detalhado(reader, banco)
            else:
                lancamentos = processar_arquivo_pdf(caminho_temporario, filename)
            return remover_linhas_de_saldo(lancamentos)
        finally:
            if caminho_temporario and os.path.exists(caminho_temporario):
                os.remove(caminho_temporario)
    return []
'''

if text.count(old) != 1:
    raise SystemExit(f'Função de conferência encontrada {text.count(old)} vezes.')
text = text.replace(old, new, 1)

for termo in [
    "'saldo aplic'",
    "'saldo movimentacao conta'",
    "'sdo aplic aut mais ap'",
    'processar_pdf_itau_detalhado(reader, banco)',
    "texto_amostra = '\\n'.join",
]:
    if termo not in text:
        raise SystemExit(f'Validação da correção falhou: {termo}')

path.write_text(text, encoding='utf-8')
print('Conferência Itaú corrigida: parser específico e linhas de saldo removidas.')
