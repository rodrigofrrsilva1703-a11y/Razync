from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old_import = 'from razync.radani import analisar_desmembramentos, consolidar_comprovantes_sispag\n'
new_import = old_import + 'from razync.bradesco_radani import processar_extrato_bradesco_radani\n'
if new_import not in text:
    if old_import not in text:
        raise SystemExit('Import da Radani não encontrado')
    text = text.replace(old_import, new_import, 1)

marker = '''@st.cache_data(show_spinner=False, ttl=1800, max_entries=8)\ndef _radani_cache_comprovantes'''
cache_fn = '''@st.cache_data(show_spinner=False, ttl=1800, max_entries=8)\ndef _radani_cache_bradesco_pdf(conteudo: bytes):\n    return processar_extrato_bradesco_radani(conteudo)\n\n\n'''
if cache_fn not in text:
    idx = text.find(marker)
    if idx == -1:
        raise SystemExit('Ponto de cache da Radani não encontrado')
    text = text[:idx] + cache_fn + text[idx:]

old_call = '''                            movs_radani = _radani_cache_extrato_pdf(\n                                arquivo_extrato_radani.getvalue(),\n                                arquivo_extrato_radani.name,\n                            )\n                            df_extrato_radani = pd.DataFrame(movs_radani or [])\n'''
new_call = '''                            diagnostico_bradesco_radani = None\n                            if nome_banco_radani == 'Bradesco':\n                                movs_radani, diagnostico_bradesco_radani = _radani_cache_bradesco_pdf(\n                                    arquivo_extrato_radani.getvalue()\n                                )\n                            else:\n                                movs_radani = _radani_cache_extrato_pdf(\n                                    arquivo_extrato_radani.getvalue(),\n                                    arquivo_extrato_radani.name,\n                                )\n                            df_extrato_radani = pd.DataFrame(movs_radani or [])\n'''
if old_call not in text:
    raise SystemExit('Chamada do extrato Radani não encontrada')
text = text.replace(old_call, new_call, 1)

needle = '''                            if df_extrato_radani.empty:\n                                st.warning(\n                                    f'Nenhum lançamento foi reconhecido no extrato do {nome_banco_radani}.'\n                                )\n                                continue\n'''
insert = needle + '''                            if diagnostico_bradesco_radani and not diagnostico_bradesco_radani.get('ok'):\n                                st.warning(\n                                    'Bradesco: a leitura não fechou com os totais impressos no extrato. '\n                                    f"Diferença em créditos: {formatar_moeda(abs(diagnostico_bradesco_radani.get('diferenca_creditos', 0)))} · "\n                                    f"Diferença em débitos: {formatar_moeda(abs(diagnostico_bradesco_radani.get('diferenca_debitos', 0)))}. "\n                                    'Os lançamentos reconhecidos serão exibidos, mas revise o extrato antes de concluir.'\n                                )\n'''
if insert not in text:
    if needle not in text:
        raise SystemExit('Bloco de dataframe vazio não encontrado')
    text = text.replace(needle, insert, 1)

path.write_text(text, encoding='utf-8')
