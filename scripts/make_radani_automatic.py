from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old = """            pode_processar_radani = bool(arquivos_ativos_radani)\n            if not pode_processar_radani:\n                st.info('Envie pelo menos um extrato PDF para liberar o processamento.')\n\n            processar_radani = st.button(\n                'Processar 968',\n                type='primary',\n                use_container_width=True,\n                disabled=not pode_processar_radani,\n                key='radani_processar_arquivos',\n            )\n\n            if processar_radani:\n"""
new = """            pode_processar_radani = bool(arquivos_ativos_radani)\n            if not pode_processar_radani:\n                st.info('Envie pelo menos um extrato PDF. O processamento começa automaticamente após o upload.')\n\n            resultado_anterior_radani = st.session_state.get('radani_resultado_processado')\n            precisa_processar_radani = bool(\n                pode_processar_radani\n                and (\n                    not resultado_anterior_radani\n                    or resultado_anterior_radani.get('assinatura') != assinatura_radani\n                )\n            )\n\n            if precisa_processar_radani:\n"""
if old not in text:
    raise SystemExit('Bloco manual da Radani não encontrado; nada alterado.')
text = text.replace(old, new, 1)

old_stale = """            elif resultado_radani:\n                st.caption(\n                    'Os arquivos selecionados mudaram. Clique em Processar 968 para gerar um novo resultado.'\n                )\n\n"""
if old_stale not in text:
    raise SystemExit('Mensagem antiga de processamento manual não encontrada.')
text = text.replace(old_stale, '', 1)

if "'Processar 968'" in text or "radani_processar_arquivos" in text:
    raise SystemExit('Ainda existe gatilho manual Processar 968 no app.py.')

path.write_text(text, encoding='utf-8')
print('Radani alterada para processamento automático.')
