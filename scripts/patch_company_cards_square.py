from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

# Na conciliação bancária a natureza é espelhada:
#   SAÍDA no extrato  <=> ENTRADA/DÉBITO no Razão
#   ENTRADA no extrato <=> SAÍDA/CRÉDITO no Razão
# Portanto NÃO se deve comparar Entrada x Entrada nem Saída x Saída.
old_calc = '''                # Sentido correto da análise: RAZÃO - EXTRATO.
                # Valor positivo = há mais no Razão do que no Extrato.
                # Valor negativo = há mais no Extrato do que no Razão.
                df_conciliacao['DIF_ENTRADAS'] = (
                    df_conciliacao['ENTRADAS_RAZAO'] - df_conciliacao['ENTRADAS_EXTRATO']
                )
                df_conciliacao['DIF_SAIDAS'] = (
                    df_conciliacao['SAIDAS_RAZAO'] - df_conciliacao['SAIDAS_EXTRATO']
                )
'''
new_calc = '''                # Natureza espelhada entre banco e contabilidade:
                # SAÍDA no extrato deve bater com ENTRADA/DÉBITO no Razão.
                # ENTRADA no extrato deve bater com SAÍDA/CRÉDITO no Razão.
                df_conciliacao['DIF_SAIDAS_EXT_ENTRADAS_RAZAO'] = (
                    df_conciliacao['ENTRADAS_RAZAO'] - df_conciliacao['SAIDAS_EXTRATO']
                )
                df_conciliacao['DIF_ENTRADAS_EXT_SAIDAS_RAZAO'] = (
                    df_conciliacao['SAIDAS_RAZAO'] - df_conciliacao['ENTRADAS_EXTRATO']
                )
'''
if text.count(old_calc) != 1:
    raise SystemExit(f'Bloco atual de diferenças encontrado {text.count(old_calc)} vezes.')
text = text.replace(old_calc, new_calc, 1)

old_status = '''                df_conciliacao['STATUS'] = df_conciliacao.apply(
                    lambda row: "✅ Batendo" if abs(row['DIF_ENTRADAS']) < 0.01 and abs(row['DIF_SAIDAS']) < 0.01 else "❌ Divergente", 
                    axis=1
                )
'''
new_status = '''                df_conciliacao['STATUS'] = df_conciliacao.apply(
                    lambda row: "✅ Batendo" if (
                        abs(row['DIF_SAIDAS_EXT_ENTRADAS_RAZAO']) < 0.01
                        and abs(row['DIF_ENTRADAS_EXT_SAIDAS_RAZAO']) < 0.01
                    ) else "❌ Divergente",
                    axis=1
                )
'''
if text.count(old_status) != 1:
    raise SystemExit(f'Bloco de status encontrado {text.count(old_status)} vezes.')
text = text.replace(old_status, new_status, 1)

old_caption = '''    st.caption(
        "Acompanhe a conferência diária comparando Entradas e Saídas. "
        "As diferenças são calculadas no sentido Razão − Extrato."
    )
'''
new_caption = '''    st.caption(
        "A conciliação considera a natureza contábil inversa: saída no extrato "
        "é comparada com entrada/débito no Razão; entrada no extrato é comparada "
        "com saída/crédito no Razão."
    )
'''
if text.count(old_caption) != 1:
    raise SystemExit(f'Legenda atual encontrada {text.count(old_caption)} vezes.')
text = text.replace(old_caption, new_caption, 1)

old_cards = '''                rc1, rc2, rc3, rc4 = st.columns(4)
                with rc1: st.markdown(f'<div class="metric-card"><div class="metric-title">Total Entradas (Extrato)</div><div class="metric-value" style="color: #3fb950;">{formatar_moeda(tot_ent_ext)}</div></div>', unsafe_allow_html=True)
                with rc2: st.markdown(f'<div class="metric-card"><div class="metric-title">Total Entradas (Razão)</div><div class="metric-value" style="color: #3fb950;">{formatar_moeda(tot_ent_raz)}</div></div>', unsafe_allow_html=True)
                with rc3: st.markdown(f'<div class="metric-card"><div class="metric-title">Total Saídas (Extrato)</div><div class="metric-value" style="color: #f85149;">{formatar_moeda(abs(tot_sai_ext))}</div></div>', unsafe_allow_html=True)
                with rc4: st.markdown(f'<div class="metric-card"><div class="metric-title">Total Saídas (Razão)</div><div class="metric-value" style="color: #f85149;">{formatar_moeda(abs(tot_sai_raz))}</div></div>', unsafe_allow_html=True)
'''
new_cards = '''                rc1, rc2, rc3, rc4 = st.columns(4)
                with rc1: st.markdown(f'<div class="metric-card"><div class="metric-title">Saídas do Extrato</div><div class="metric-value" style="color: #f85149;">{formatar_moeda(abs(tot_sai_ext))}</div></div>', unsafe_allow_html=True)
                with rc2: st.markdown(f'<div class="metric-card"><div class="metric-title">Entradas/Débitos do Razão</div><div class="metric-value" style="color: #f85149;">{formatar_moeda(tot_ent_raz)}</div></div>', unsafe_allow_html=True)
                with rc3: st.markdown(f'<div class="metric-card"><div class="metric-title">Entradas do Extrato</div><div class="metric-value" style="color: #3fb950;">{formatar_moeda(tot_ent_ext)}</div></div>', unsafe_allow_html=True)
                with rc4: st.markdown(f'<div class="metric-card"><div class="metric-title">Saídas/Créditos do Razão</div><div class="metric-value" style="color: #3fb950;">{formatar_moeda(tot_sai_raz)}</div></div>', unsafe_allow_html=True)
'''
if text.count(old_cards) != 1:
    raise SystemExit(f'Cards resumo encontrados {text.count(old_cards)} vezes.')
text = text.replace(old_cards, new_cards, 1)

old_table = '''                df_exibicao = df_conciliacao[['DATA_EXIBICAO', 'ENTRADAS_EXTRATO', 'ENTRADAS_RAZAO', 'DIF_ENTRADAS', 'SAIDAS_EXTRATO', 'SAIDAS_RAZAO', 'DIF_SAIDAS', 'STATUS']].copy()
                df_exibicao.columns = ['Data', 'Entradas Ext. (R$)', 'Entradas Razão (R$)', 'Dif. Entradas (R$)', 'Saídas Ext. (R$)', 'Saídas Razão (R$)', 'Dif. Saídas (R$)', 'Status']
                colunas_monetarias_conciliacao = [
                    'Entradas Ext. (R$)', 'Entradas Razão (R$)', 'Dif. Entradas (R$)',
                    'Saídas Ext. (R$)', 'Saídas Razão (R$)', 'Dif. Saídas (R$)'
                ]
'''
new_table = '''                df_exibicao = df_conciliacao[[
                    'DATA_EXIBICAO',
                    'SAIDAS_EXTRATO', 'ENTRADAS_RAZAO', 'DIF_SAIDAS_EXT_ENTRADAS_RAZAO',
                    'ENTRADAS_EXTRATO', 'SAIDAS_RAZAO', 'DIF_ENTRADAS_EXT_SAIDAS_RAZAO',
                    'STATUS'
                ]].copy()
                df_exibicao.columns = [
                    'Data',
                    'Saídas Extrato (R$)', 'Entradas/Débitos Razão (R$)', 'Dif. Saída Ext. x Entrada Razão (R$)',
                    'Entradas Extrato (R$)', 'Saídas/Créditos Razão (R$)', 'Dif. Entrada Ext. x Saída Razão (R$)',
                    'Status'
                ]
                colunas_monetarias_conciliacao = [
                    'Saídas Extrato (R$)', 'Entradas/Débitos Razão (R$)',
                    'Dif. Saída Ext. x Entrada Razão (R$)',
                    'Entradas Extrato (R$)', 'Saídas/Créditos Razão (R$)',
                    'Dif. Entrada Ext. x Saída Razão (R$)'
                ]
'''
if text.count(old_table) != 1:
    raise SystemExit(f'Tabela de exibição encontrada {text.count(old_table)} vezes.')
text = text.replace(old_table, new_table, 1)

old_excel_loop = '''                    for col in ['Entradas Ext. (R$)', 'Entradas Razão (R$)', 'Dif. Entradas (R$)', 'Saídas Ext. (R$)', 'Saídas Razão (R$)', 'Dif. Saídas (R$)']:
                        df_exib_excel[col] = df_exib_excel[col].apply(formatar_moeda)
'''
new_excel_loop = '''                    for col in colunas_monetarias_conciliacao:
                        df_exib_excel[col] = df_exib_excel[col].apply(formatar_moeda)
'''
if text.count(old_excel_loop) != 1:
    raise SystemExit(f'Formatação Excel encontrada {text.count(old_excel_loop)} vezes.')
text = text.replace(old_excel_loop, new_excel_loop, 1)

old_div = '''                        df_div_export = df_divergencias[['DATA_EXIBICAO', 'ENTRADAS_EXTRATO', 'ENTRADAS_RAZAO', 'DIF_ENTRADAS', 'SAIDAS_EXTRATO', 'SAIDAS_RAZAO', 'DIF_SAIDAS']].copy()
                        df_div_export.columns = ['Data', 'Entradas Extrato', 'Entradas Razao', 'Diferenca Entradas', 'Saidas Extrato', 'Saidas Razao', 'Diferenca Saidas']
'''
new_div = '''                        df_div_export = df_divergencias[[
                            'DATA_EXIBICAO',
                            'SAIDAS_EXTRATO', 'ENTRADAS_RAZAO', 'DIF_SAIDAS_EXT_ENTRADAS_RAZAO',
                            'ENTRADAS_EXTRATO', 'SAIDAS_RAZAO', 'DIF_ENTRADAS_EXT_SAIDAS_RAZAO'
                        ]].copy()
                        df_div_export.columns = [
                            'Data',
                            'Saidas Extrato', 'Entradas Debitos Razao', 'Diferenca Saida Ext x Entrada Razao',
                            'Entradas Extrato', 'Saidas Creditos Razao', 'Diferenca Entrada Ext x Saida Razao'
                        ]
'''
if text.count(old_div) != 1:
    raise SystemExit(f'Exportação de divergências encontrada {text.count(old_div)} vezes.')
text = text.replace(old_div, new_div, 1)

checks = [
    "df_conciliacao['ENTRADAS_RAZAO'] - df_conciliacao['SAIDAS_EXTRATO']",
    "df_conciliacao['SAIDAS_RAZAO'] - df_conciliacao['ENTRADAS_EXTRATO']",
    'Saídas Extrato (R$)',
    'Entradas/Débitos Razão (R$)',
    'Entradas Extrato (R$)',
    'Saídas/Créditos Razão (R$)',
]
for check in checks:
    if check not in text:
        raise SystemExit(f'Validação falhou: {check}')

# Garante que a tela não continue usando a comparação antiga lado-a-lado.
bloco_inicio = text.find("elif st.session_state['pagina_ativa'] == 'razao':")
bloco_razao = text[bloco_inicio:]
for antigo in ["DIF_ENTRADAS']", "DIF_SAIDAS']"]:
    if antigo in bloco_razao:
        raise SystemExit(f'Referência antiga ainda presente na tela Razão: {antigo}')

path.write_text(text, encoding='utf-8')
print('Conciliação corrigida: saída do extrato x entrada/débito do Razão e vice-versa.')
