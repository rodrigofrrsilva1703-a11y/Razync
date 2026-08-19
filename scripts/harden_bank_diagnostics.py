from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

# Importa o pequeno módulo testável de validação bancária.
import_marker = 'from razync.security import proteger_acesso\n'
import_line = (
    'from razync.bank_validation import diagnostico_pdf_sem_lancamentos, validar_fechamento_saldo\n'
)
if import_line not in s:
    if import_marker not in s:
        raise SystemExit('Import de segurança não encontrado.')
    s = s.replace(import_marker, import_marker + import_line, 1)

# -----------------------------------------------------------------------------
# Bradesco: diagnóstico explícito do OCR + conferência matemática de saldo.
# -----------------------------------------------------------------------------
start = s.index("def processar_pdf_bradesco_mensal(")
end = s.index('\ndef ', start + 5)
br = s[start:end]

if 'saldo_abertura = None' not in br:
    br = br.replace(
        '    dentro_saldos_invest = False\n    modo_ocr = False\n',
        '    dentro_saldos_invest = False\n    modo_ocr = False\n'
        '    saldo_abertura = None\n    indice_saldo_abertura = 0\n    erro_ocr = \'\'\n',
        1,
    )

path_marker = """            caminho_pdf = (
                getattr(reader, '_razync_source_path', None)
                or getattr(getattr(reader, 'stream', None), 'name', None)
            )
            if caminho_pdf and os.path.exists(caminho_pdf):"""
path_repl = """            caminho_pdf = (
                getattr(reader, '_razync_source_path', None)
                or getattr(getattr(reader, 'stream', None), 'name', None)
            )
            if not caminho_pdf or not os.path.exists(caminho_pdf):
                erro_ocr = 'Arquivo temporário do PDF não ficou disponível para o OCR.'
                reader._razync_ocr_error = erro_ocr
            if caminho_pdf and os.path.exists(caminho_pdf):"""
if 'Arquivo temporário do PDF não ficou disponível para o OCR.' not in br:
    if path_marker not in br:
        raise SystemExit('Resolução do caminho OCR não encontrada.')
    br = br.replace(path_marker, path_repl, 1)

exception_marker = """                documento_ocr.close()
        except Exception:
            textos_paginas = textos_paginas or []

    for texto in textos_paginas:"""
exception_repl = """                documento_ocr.close()
        except Exception as erro:
            erro_ocr = str(erro)
            reader._razync_ocr_error = erro_ocr
            textos_paginas = textos_paginas or []

    reader._razync_ocr_executado = modo_ocr
    for texto in textos_paginas:"""
if 'except Exception as erro:' not in br:
    if exception_marker not in br:
        raise SystemExit('Bloco de exceção OCR não encontrado.')
    br = br.replace(exception_marker, exception_repl, 1)

saldo_marker = """            if 'saldo anterior' in normalizada:
                moedas_saldo = regex_moeda.findall(linha)
                if moedas_saldo:
                    ultimo_saldo = limpar_valor_monetario(moedas_saldo[-1])
                partes_historico = []
                continue"""
saldo_repl = """            if 'saldo anterior' in normalizada:
                moedas_saldo = regex_moeda.findall(linha)
                if moedas_saldo:
                    ultimo_saldo = limpar_valor_monetario(moedas_saldo[-1])
                    saldo_abertura = ultimo_saldo
                    indice_saldo_abertura = len(lancamentos)
                partes_historico = []
                continue"""
if 'indice_saldo_abertura = len(lancamentos)' not in br:
    if saldo_marker not in br:
        raise SystemExit('Tratamento de saldo anterior não encontrado.')
    br = br.replace(saldo_marker, saldo_repl, 1)

return_marker = '\n    return lancamentos\n'
return_repl = """
    if saldo_abertura is not None and ultimo_saldo is not None:
        movimentos_validacao = [
            item.get('VALOR', 0.0) for item in lancamentos[indice_saldo_abertura:]
        ]
        reader._razync_balance_check = validar_fechamento_saldo(
            saldo_abertura, ultimo_saldo, movimentos_validacao
        )
    reader._razync_ocr_executado = modo_ocr
    if erro_ocr:
        reader._razync_ocr_error = erro_ocr
    return lancamentos
"""
if '_razync_balance_check = validar_fechamento_saldo' not in br:
    if return_marker not in br:
        raise SystemExit('Retorno do leitor Bradesco não encontrado.')
    br = br.replace(return_marker, return_repl, 1)

s = s[:start] + br + s[end:]

# -----------------------------------------------------------------------------
# Motor central: guarda diagnóstico/fechamento sem expor traceback.
# -----------------------------------------------------------------------------
start = s.index('def processar_arquivo_pdf(')
end = s.index('\ndef ', start + 5)
pdf = s[start:end]

bradesco_marker = """        if banco_identificado == 'BANCO BRADESCO':
            lancamentos_bradesco = processar_pdf_bradesco_mensal(
                reader, banco_identificado
            )
            if lancamentos_bradesco:
                return lancamentos_bradesco
"""
bradesco_repl = """        if banco_identificado == 'BANCO BRADESCO':
            lancamentos_bradesco = processar_pdf_bradesco_mensal(
                reader, banco_identificado
            )
            fechamento_bradesco = getattr(reader, '_razync_balance_check', None)
            if fechamento_bradesco:
                st.session_state['ultimo_fechamento_extrato'] = fechamento_bradesco
            if lancamentos_bradesco:
                return lancamentos_bradesco
            if not texto_completo.strip():
                st.session_state['ultimo_erro_extrato'] = diagnostico_pdf_sem_lancamentos(
                    banco_identificado,
                    True,
                    bool(getattr(reader, '_razync_ocr_executado', False)),
                    str(getattr(reader, '_razync_ocr_error', '') or '')
                )
"""
if "st.session_state['ultimo_erro_extrato'] = diagnostico_pdf_sem_lancamentos" not in pdf:
    if bradesco_marker not in pdf:
        raise SystemExit('Rota Bradesco do motor central não encontrada.')
    pdf = pdf.replace(bradesco_marker, bradesco_repl, 1)

s = s[:start] + pdf + s[end:]

# Limpa diagnóstico anterior ao iniciar um PDF novo.
start = s.index('def processar_extrato_unificado(')
end = s.index('\ndef ', start + 5)
unificado = s[start:end]
if "st.session_state.pop('ultimo_erro_extrato', None)" not in unificado:
    unificado = unificado.replace(
        "    if extensao != '.pdf':\n        return []\n\n    caminho_temporario = None",
        "    if extensao != '.pdf':\n        return []\n\n"
        "    st.session_state.pop('ultimo_erro_extrato', None)\n"
        "    st.session_state.pop('ultimo_fechamento_extrato', None)\n"
        "    caminho_temporario = None",
        1,
    )
s = s[:start] + unificado + s[end:]

# Conferência: transforma a falha silenciosa do OCR em mensagem útil e avisa saldo divergente.
start = s.index('def processar_extrato_conferencia_empresa(')
end = s.index('\ndef ', start + 5)
conf = s[start:end]
if "ultimo_fechamento_extrato" not in conf:
    conf = conf.replace(
        '    return filtrados\n',
        "    fechamento = st.session_state.get('ultimo_fechamento_extrato')\n"
        "    if fechamento and fechamento.get('disponivel') and fechamento.get('ok') is False:\n"
        "        st.warning(\n"
        "            'O extrato foi lido, mas o fechamento matemático do saldo apresentou '\n"
        "            f\"diferença de {formatar_moeda(abs(fechamento.get('diferenca', 0)))}. \"\n"
        "            'Revise os lançamentos antes de concluir a conciliação.'\n"
        "        )\n"
        "    if not filtrados:\n"
        "        erro_leitura = st.session_state.get('ultimo_erro_extrato', '')\n"
        "        if erro_leitura:\n"
        "            raise ValueError(erro_leitura)\n"
        "    return filtrados\n",
        1,
    )
s = s[:start] + conf + s[end:]

checks = [
    'from razync.bank_validation import diagnostico_pdf_sem_lancamentos, validar_fechamento_saldo',
    "reader._razync_ocr_executado = modo_ocr",
    "reader._razync_ocr_error = erro_ocr",
    "reader._razync_balance_check = validar_fechamento_saldo",
    "st.session_state['ultimo_erro_extrato'] = diagnostico_pdf_sem_lancamentos",
    "st.session_state.pop('ultimo_erro_extrato', None)",
    "fechamento.get('ok') is False",
]
for check in checks:
    if check not in s:
        raise SystemExit(f'Check de hardening ausente: {check}')

p.write_text(s, encoding='utf-8')
print('Diagnóstico de OCR e validação de saldo incorporados ao app.')
