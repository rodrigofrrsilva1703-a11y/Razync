from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

# Amplia a base reutilizável das empresas Autokraft para incluir a classificação
# da planilha final, usando exclusivamente os padrões da empresa atual.
old_helper_end = '''        else:
            st.info("Esta empresa ainda não possui padrões aprendidos.")

# ==============================================================================
# ORGANIZADORES ESPECÍFICOS POR EMPRESA
'''
new_helper_end = '''        else:
            st.info("Esta empresa ainda não possui padrões aprendidos.")

        st.markdown("---")
        st.markdown("#### Classificar planilha final conciliada")
        st.caption(
            "Anexe somente a planilha final depois da conferência bancária. "
            "A classificação usa exclusivamente a Base Inteligente desta empresa."
        )
        planilha_final = st.file_uploader(
            "Planilha final com os saldos conferidos",
            type=['xlsx'],
            key=f"base_planilha_final_{empresa}"
        )
        if planilha_final:
            if erro_base:
                st.error("A base online precisa estar conectada antes da classificação.")
            elif not base_empresa:
                st.warning(
                    "A base desta empresa ainda não possui padrões. Importe primeiro "
                    "planilhas antigas já classificadas desta mesma empresa."
                )
            else:
                try:
                    contas_bancarias = {
                        banco: '' for banco in bancos_permitidos
                    }
                    arquivo_classificado, resumo = executar_com_loading(
                        "Analisando históricos e classificando as contas...",
                        classificar_planilha_final,
                        planilha_final.getvalue(),
                        planilha_final.name,
                        base_empresa,
                        contas_bancarias
                    )
                    m1, m2, m3 = st.columns(3)
                    m1.metric(
                        "Classificados automaticamente",
                        f"{int(resumo.get('automaticos', 0)):,}".replace(',', '.')
                    )
                    m2.metric(
                        "Por nome da empresa",
                        f"{int(resumo.get('por_nome_empresa', 0)):,}".replace(',', '.')
                    )
                    m3.metric(
                        "Padrões novos",
                        f"{int(resumo.get('padroes_novos', 0)):,}".replace(',', '.')
                    )
                    nome_saida = os.path.splitext(planilha_final.name)[0]
                    st.download_button(
                        "Baixar planilha final classificada",
                        data=arquivo_classificado,
                        file_name=f"{nome_saida}_Classificada.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"base_download_classificada_{empresa}",
                        use_container_width=True
                    )
                except Exception as erro_classificacao:
                    st.error(
                        "Não foi possível classificar a planilha final: "
                        f"{erro_classificacao}"
                    )

# ==============================================================================
# ORGANIZADORES ESPECÍFICOS POR EMPRESA
'''
if text.count(old_helper_end) != 1:
    raise SystemExit(f'Final da base reutilizável encontrado {text.count(old_helper_end)} vezes.')
text = text.replace(old_helper_end, new_helper_end, 1)

# Volta ao mesmo padrão visual da Nova Geração: duas abas reais.
old_selector = '''        ferramenta_autokraft = st.radio(
            "Ferramenta",
            ["Organizar e conferir", "Base inteligente de Débito e Crédito"],
            horizontal=True,
            key=f"ferramenta_{slug_empresa_autokraft}",
            label_visibility="collapsed"
        )

        if ferramenta_autokraft == "Base inteligente de Débito e Crédito":
            renderizar_base_inteligente_empresa(
                slug_empresa_autokraft,
                empresa_autokraft,
                {'itau', 'daycoval'}
            )
            st.stop()

        st.caption(
'''
new_selector = '''        aba_operacoes_autokraft, aba_base_autokraft = st.tabs([
            "Organizar e conferir",
            "Base inteligente de Débito e Crédito"
        ])

        with aba_base_autokraft:
            renderizar_base_inteligente_empresa(
                slug_empresa_autokraft,
                empresa_autokraft,
                {'itau', 'daycoval'}
            )

        with aba_operacoes_autokraft:
            st.caption(
'''
if text.count(old_selector) != 1:
    raise SystemExit(f'Seletor atual encontrado {text.count(old_selector)} vezes.')
text = text.replace(old_selector, new_selector, 1)

# O restante do bloco de operações precisa ficar dentro da tab. Reindenta desde
# o multiselect até imediatamente antes do bloco da Nova Geração.
start_token = '''        bancos_autokraft = st.multiselect(\n'''
end_token = '''    if st.session_state['empresa_organizador'] == 'nova_geracao':\n'''
start = text.find(start_token, text.find('with aba_operacoes_autokraft:'))
end = text.find(end_token, start)
if start == -1 or end == -1:
    raise SystemExit('Não foi possível localizar o corpo de operações Autokraft.')
bloco = text[start:end]
linhas = bloco.splitlines(True)
bloco_indentado = ''.join(('    ' + linha if linha.strip() else linha) for linha in linhas)
text = text[:start] + bloco_indentado + text[end:]

# Corrige a indentação do caption aberto pelo `with` recém-criado, caso necessário.
# A linha st.caption já está com 12 espaços; seus argumentos permanecem válidos.

path.write_text(text, encoding='utf-8')
print('Autokraft agora usa abas reais e Base Inteligente com classificação da planilha final.')
