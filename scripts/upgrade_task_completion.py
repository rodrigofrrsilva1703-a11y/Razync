from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

old = '''def salvar_status_tarefa_empresa(codigo_empresa, competencia, concluida):
    agora = datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
    registro = {
        'codigo_empresa': str(codigo_empresa),
        'competencia': competencia.isoformat(),
        'concluida': bool(concluida),
        'concluida_em': agora if concluida else None,
        'atualizado_em': agora,
    }
    requisicao_classificacao_online(
        'tarefas_empresas?on_conflict=codigo_empresa,competencia',
        metodo='POST',
        dados=[registro],
        prefer='resolution=merge-duplicates,return=minimal',
    )
    carregar_tarefas_competencia.clear()
'''
new = old + '''\n\ndef salvar_status_tarefas_empresas_em_lote(codigos_empresas, competencia, concluida):
    \"\"\"Atualiza várias empresas usando a mesma regra segura da conclusão individual.\"\"\"
    codigos = [str(codigo) for codigo in codigos_empresas if str(codigo).strip()]
    for codigo in dict.fromkeys(codigos):
        salvar_status_tarefa_empresa(codigo, competencia, concluida)
    return len(dict.fromkeys(codigos))


def registrar_conclusao_automatica_empresa(codigo_empresa, origem='Processamento concluído'):
    \"\"\"Conclui a competência atual uma única vez por resultado gerado na sessão.\"\"\"
    if not st.session_state.get('tarefas_conclusao_automatica', True):
        return False
    hoje, competencia = obter_competencia_operacional()
    chave = f\"{codigo_empresa}:{competencia.isoformat()}:{origem}\"
    ja_registradas = st.session_state.setdefault('_rz_conclusoes_automaticas', {})
    if chave in ja_registradas:
        return False
    salvar_status_tarefa_empresa(str(codigo_empresa), competencia, True)
    agora = datetime.now(ZoneInfo('America/Sao_Paulo'))
    ja_registradas[chave] = {
        'origem': origem,
        'quando': agora.strftime('%d/%m/%Y %H:%M'),
    }
    st.session_state['_rz_ultima_conclusao_automatica'] = {
        'codigo': str(codigo_empresa),
        'origem': origem,
        'quando': agora.strftime('%d/%m/%Y %H:%M'),
    }
    return True
'''
if old not in s:
    raise SystemExit('bloco salvar_status não encontrado')
s = s.replace(old, new, 1)

old = '''    with aba_painel:
        st.markdown('### Obrigações das empresas')
        f1, f2, f3 = st.columns([1.3, 1.3, 2.4])
'''
new = '''    with aba_painel:
        st.markdown('### Obrigações das empresas')
        st.toggle(
            'Concluir automaticamente quando uma ferramenta gerar resultado válido',
            value=st.session_state.get('tarefas_conclusao_automatica', True),
            key='tarefas_conclusao_automatica',
            help='A empresa só é marcada após um processamento terminar com resultado final válido. Você pode reabrir quando quiser.',
        )
        ultima_auto = st.session_state.get('_rz_ultima_conclusao_automatica')
        if ultima_auto:
            st.caption(
                f\"Última conclusão automática: empresa {ultima_auto['codigo']} · \"
                f\"{ultima_auto['origem']} · {ultima_auto['quando']}\"
            )
        f1, f2, f3 = st.columns([1.3, 1.3, 2.4])
'''
if old not in s:
    raise SystemExit('início painel tarefas não encontrado')
s = s.replace(old, new, 1)

old = '''        st.dataframe(pd.DataFrame(linhas_auto), use_container_width=True, hide_index=True)

        st.markdown('#### Atualização rápida de uma empresa')
'''
new = '''        st.dataframe(pd.DataFrame(linhas_auto), use_container_width=True, hide_index=True)

        st.markdown('#### Conclusão rápida em lote')
        opcoes_lote = {
            f\"{item['Código']} - {item['Empresa']} · {item['Status']}\": item['Código']
            for item in linhas_auto
        }
        selecionadas_lote = st.multiselect(
            'Selecione uma ou mais empresas exibidas acima',
            options=list(opcoes_lote.keys()),
            key='tarefas_empresas_lote',
            placeholder='Escolher empresas para atualizar',
        )
        lote_1, lote_2 = st.columns(2)
        if lote_1.button(
            '✓ Concluir selecionadas',
            key='tarefas_concluir_lote',
            use_container_width=True,
            disabled=not selecionadas_lote,
        ):
            try:
                quantidade = salvar_status_tarefas_empresas_em_lote(
                    [opcoes_lote[item] for item in selecionadas_lote],
                    competencia_tarefas,
                    True,
                )
                st.success(f'{quantidade} empresa(s) concluída(s).')
                st.rerun()
            except Exception as erro_lote:
                st.error(f'Não foi possível concluir as selecionadas: {erro_lote}')
        if lote_2.button(
            '↺ Reabrir selecionadas',
            key='tarefas_reabrir_lote',
            use_container_width=True,
            disabled=not selecionadas_lote,
        ):
            try:
                quantidade = salvar_status_tarefas_empresas_em_lote(
                    [opcoes_lote[item] for item in selecionadas_lote],
                    competencia_tarefas,
                    False,
                )
                st.success(f'{quantidade} empresa(s) reaberta(s).')
                st.rerun()
            except Exception as erro_lote:
                st.error(f'Não foi possível reabrir as selecionadas: {erro_lote}')

        st.markdown('#### Atualização rápida de uma empresa')
'''
if old not in s:
    raise SystemExit('ponto lote não encontrado')
s = s.replace(old, new, 1)

old = '''                    arquivo_excel_lcarlos = gerar_excel_modelo_dominio(
                        df_modelo_lcarlos
                    )
                    col_download_excel, col_download_txt = st.columns(2)
'''
new = '''                    arquivo_excel_lcarlos = gerar_excel_modelo_dominio(
                        df_modelo_lcarlos
                    )
                    try:
                        if registrar_conclusao_automatica_empresa(
                            '285', 'Organizador · L. Carlos Gomes'
                        ):
                            st.success('✓ Tarefa da empresa 285 concluída automaticamente nesta competência.')
                    except Exception as erro_auto_tarefa:
                        st.caption(f'A tarefa não foi atualizada automaticamente: {erro_auto_tarefa}')
                    col_download_excel, col_download_txt = st.columns(2)
'''
if old not in s:
    raise SystemExit('ponto lcarlos não encontrado')
s = s.replace(old, new, 1)

old = '''                    arquivo_final = executar_com_loading(
                        "Gerando a planilha final...",
                        gerar_excel_nova_geracao,
                        dados_exportacao_por_banco,
                        modelo_org_bytes
                    )

                    total_entradas = df_org.loc[df_org['VALOR'] > 0, 'VALOR'].sum()
'''
new = '''                    arquivo_final = executar_com_loading(
                        "Gerando a planilha final...",
                        gerar_excel_nova_geracao,
                        dados_exportacao_por_banco,
                        modelo_org_bytes
                    )
                    try:
                        if registrar_conclusao_automatica_empresa(
                            '266', f'Organizador · Nova Geração {nome_estabelecimento_nova}'
                        ):
                            st.success('✓ Tarefa da empresa 266 concluída automaticamente nesta competência.')
                    except Exception as erro_auto_tarefa:
                        st.caption(f'A tarefa não foi atualizada automaticamente: {erro_auto_tarefa}')

                    total_entradas = df_org.loc[df_org['VALOR'] > 0, 'VALOR'].sum()
'''
if old not in s:
    raise SystemExit('ponto nova geração não encontrado')
s = s.replace(old, new, 1)

# teste estático simples para proteger a integração
pt = Path('tests/test_task_completion_integration.py')
pt.write_text('''from pathlib import Path\n\n\ndef test_central_tem_conclusao_em_lote_e_automatica():\n    app = Path("app.py").read_text(encoding="utf-8")\n    assert "salvar_status_tarefas_empresas_em_lote" in app\n    assert "registrar_conclusao_automatica_empresa" in app\n    assert "Concluir selecionadas" in app\n    assert "Reabrir selecionadas" in app\n    assert "tarefas_conclusao_automatica" in app\n    assert "Organizador · L. Carlos Gomes" in app\n    assert "Organizador · Nova Geração" in app\n''', encoding='utf-8')

p.write_text(s, encoding='utf-8')
