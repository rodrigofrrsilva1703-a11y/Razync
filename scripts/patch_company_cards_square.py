from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

# O primeiro patch criou as tabs, mas apenas o caption ficou dentro da aba de operações.
# Em Streamlit, tudo que deve pertencer à tab precisa executar dentro do `with` correspondente.
# Para evitar reindentar centenas de linhas e reduzir risco, usamos um seletor de ferramenta
# exclusivo por empresa: somente a área escolhida é renderizada.
old = '''        aba_operacoes_autokraft, aba_base_autokraft = st.tabs([
            "Organizar e conferir",
            "Base inteligente de Débito e Crédito"
        ])
        with aba_operacoes_autokraft:
            st.caption(
                f"Ferramentas ativas para {empresa_autokraft}. O sistema lê automaticamente "
                "cada aba diária, ignora saldos e totais e separa os lançamentos por banco."
            )
        bancos_autokraft = st.multiselect(
'''
new = '''        ferramenta_autokraft = st.radio(
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
            f"Ferramentas ativas para {empresa_autokraft}. O sistema lê automaticamente "
            "cada aba diária, ignora saldos e totais e separa os lançamentos por banco."
        )
        bancos_autokraft = st.multiselect(
'''
if text.count(old) != 1:
    raise SystemExit(f'Bloco de tabs Autokraft encontrado {text.count(old)} vezes; alteração cancelada.')
text = text.replace(old, new, 1)

old_end = '''        with aba_base_autokraft:
            renderizar_base_inteligente_empresa(
                slug_empresa_autokraft,
                empresa_autokraft,
                {'itau', 'daycoval'}
            )

    if st.session_state['empresa_organizador'] == 'nova_geracao':
'''
new_end = '''    if st.session_state['empresa_organizador'] == 'nova_geracao':
'''
if text.count(old_end) != 1:
    raise SystemExit(f'Bloco final da antiga tab encontrado {text.count(old_end)} vezes; alteração cancelada.')
text = text.replace(old_end, new_end, 1)

path.write_text(text, encoding='utf-8')
print('Ferramentas Autokraft separadas: apenas a ferramenta selecionada é renderizada.')
