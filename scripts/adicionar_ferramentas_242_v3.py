from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

old = "aba_operacoes_ef, aba_base_ef = st.tabs(['Organizar arquivos', 'Base Inteligente'])"
new = "aba_operacoes_ef, aba_base_ef, aba_conferencia_ef = st.tabs(['Organizar arquivos', 'Base Inteligente', 'Conferência com Extrato'])"
if old not in s:
    raise SystemExit('tabs 242 não localizadas')
s = s.replace(old, new, 1)

old = """            if any([arq_despesa_ef, arq_fornecedor_ef, arq_recebido_ef]):
                try:
                    despesas_ef = processar_despesas(
                        arq_despesa_ef.getvalue(), int(ano_ef)
                    ) if arq_despesa_ef is not None else None
"""
new = """            despesas_ef, fornecedores_ef, recebidos_ef = {}, {}, {}
            if any([arq_despesa_ef, arq_fornecedor_ef, arq_recebido_ef]):
                try:
                    despesas_ef = processar_despesas(
                        arq_despesa_ef.getvalue(), int(ano_ef)
                    ) if arq_despesa_ef is not None else {}
"""
if old not in s:
    raise SystemExit('inicialização 242 não localizada')
s = s.replace(old, new, 1)

needle = "\n    if st.session_state['empresa_organizador'] == 'lcarlos':\n"
if needle not in s:
    raise SystemExit('ponto de inserção não localizado')

bloco = r'''
        with aba_conferencia_ef:
            st.markdown('#### Conferência com Extrato')
            st.caption(
                'Conferência independente por conta. Despesa e Fornecedor entram como saídas; '
                'Recebido entra como entrada. A conta 0 fica somente para revisão manual.'
            )

            dados_conferencia_ef = {'8': [], '508': [], '509': []}
            for origem_ef, grupos_ef, sinal_ef in [
                ('Despesa', despesas_ef, -1),
                ('Fornecedor', fornecedores_ef, -1),
                ('Recebido', recebidos_ef, 1),
            ]:
                for conta_ef, df_origem_ef in (grupos_ef or {}).items():
                    if conta_ef not in dados_conferencia_ef or df_origem_ef.empty:
                        continue
                    df_temp_ef = df_origem_ef.copy()
                    df_temp_ef['DATA'] = pd.to_datetime(df_temp_ef['DATA'], dayfirst=True, errors='coerce')
                    df_temp_ef['VALOR'] = pd.to_numeric(df_temp_ef['VALOR'], errors='coerce').fillna(0.0).abs() * sinal_ef
                    df_temp_ef['ORIGEM'] = origem_ef
                    dados_conferencia_ef[conta_ef].append(df_temp_ef)

            configs_conf_ef = [
                ('8', 'Banco do Brasil · Conta 8'),
                ('508', 'Itaú · 105318 · Conta 508'),
                ('509', 'Itaú · 181537 · Conta 509'),
            ]
            abas_conf_ef = st.tabs([rotulo for _, rotulo in configs_conf_ef])
            for aba_conf_ef, (conta_conf_ef, rotulo_conf_ef) in zip(abas_conf_ef, configs_conf_ef):
                with aba_conf_ef:
                    partes_ef = dados_conferencia_ef.get(conta_conf_ef, [])
                    if not partes_ef:
                        st.info(f'Nenhum lançamento da conta {conta_conf_ef} nas planilhas anexadas.')
                        continue
                    df_plan_ef = pd.concat(partes_ef, ignore_index=True).dropna(subset=['DATA'])
                    if df_plan_ef.empty:
                        st.info('Não há datas válidas para conferência nesta conta.')
                        continue
                    inicio_ef = df_plan_ef['DATA'].min().normalize()
                    fim_ef = df_plan_ef['DATA'].max().normalize()
                    st.caption(f"Período: {inicio_ef.strftime('%d/%m/%Y')} a {fim_ef.strftime('%d/%m/%Y')}")

                    extrato_ef = st.file_uploader(
                        f'Extrato — {rotulo_conf_ef}',
                        type=['pdf', 'ofx', 'csv', 'xlsx', 'xls'],
                        key=f'ef242_extrato_conferencia_{conta_conf_ef}',
                        help='Envie somente o extrato desta conta. Os dois Itaús são conferidos separadamente.',
                    )
                    if extrato_ef is None:
                        st.info('Envie o extrato desta conta para iniciar a conferência.')
                        continue
                    try:
                        movs_ef = executar_com_loading(
                            f'Lendo o extrato da conta {conta_conf_ef}...',
                            processar_extrato_conferencia_empresa,
                            extrato_ef.getvalue(), extrato_ef.name,
                        )
                        df_ext_ef = pd.DataFrame(movs_ef or [])
                        if df_ext_ef.empty:
                            st.warning('Nenhum lançamento foi reconhecido neste extrato.')
                            continue
                        df_ext_ef['DATA'] = pd.to_datetime(df_ext_ef['DATA'], dayfirst=True, errors='coerce')
                        df_ext_ef['VALOR'] = pd.to_numeric(df_ext_ef['VALOR'], errors='coerce').fillna(0.0)
                        df_ext_ef = df_ext_ef[df_ext_ef['DATA'].between(inicio_ef, fim_ef, inclusive='both')].dropna(subset=['DATA'])
                        if df_ext_ef.empty:
                            st.warning('O extrato não possui lançamentos dentro do período das planilhas.')
                            continue

                        datas_ef = sorted(set(df_plan_ef['DATA'].dt.normalize()) | set(df_ext_ef['DATA'].dt.normalize()))
                        linhas_ef = []
                        for data_ef in datas_ef:
                            p_ef = df_plan_ef[df_plan_ef['DATA'].dt.normalize().eq(data_ef)]
                            e_ef = df_ext_ef[df_ext_ef['DATA'].dt.normalize().eq(data_ef)]
                            ep = float(p_ef.loc[p_ef['VALOR'] > 0, 'VALOR'].sum())
                            sp = float(abs(p_ef.loc[p_ef['VALOR'] < 0, 'VALOR'].sum()))
                            ee = float(e_ef.loc[e_ef['VALOR'] > 0, 'VALOR'].sum())
                            se = float(abs(e_ef.loc[e_ef['VALOR'] < 0, 'VALOR'].sum()))
                            de, ds = round(ep - ee, 2), round(sp - se, 2)
                            bate = abs(de) <= 0.02 and abs(ds) <= 0.02
                            linhas_ef.append({
                                'Data': data_ef.strftime('%d/%m/%Y'),
                                'Entrada Planilha': ep, 'Entrada Extrato': ee, 'Dif. Entradas': de,
                                'Saída Planilha': sp, 'Saída Extrato': se, 'Dif. Saídas': ds,
                                'Status': '✅ Batendo' if bate else '❌ Divergente',
                            })
                        diario_ef = pd.DataFrame(linhas_ef)
                        batendo_ef = int((diario_ef['Status'] == '✅ Batendo').sum())
                        divergentes_ef = int((diario_ef['Status'] == '❌ Divergente').sum())
                        c1_ef, c2_ef = st.columns(2)
                        c1_ef.metric('Dias batendo', batendo_ef)
                        c2_ef.metric('Dias divergentes', divergentes_ef)
                        st.dataframe(
                            diario_ef, use_container_width=True, hide_index=True,
                            height=min(420, 38 + max(1, min(len(diario_ef), 10)) * 35),
                            column_config={
                                'Entrada Planilha': st.column_config.NumberColumn(format='R$ %.2f'),
                                'Entrada Extrato': st.column_config.NumberColumn(format='R$ %.2f'),
                                'Dif. Entradas': st.column_config.NumberColumn(format='R$ %.2f'),
                                'Saída Planilha': st.column_config.NumberColumn(format='R$ %.2f'),
                                'Saída Extrato': st.column_config.NumberColumn(format='R$ %.2f'),
                                'Dif. Saídas': st.column_config.NumberColumn(format='R$ %.2f'),
                            },
                        )
                        if divergentes_ef == 0:
                            st.success('Conferência concluída: todos os dias estão batendo.')
                        else:
                            st.warning(f'{divergentes_ef} dia(s) possuem diferença entre planilhas e extrato.')
                    except Exception as erro_conf_ef:
                        st.error(f'Não foi possível conferir a conta {conta_conf_ef}: {erro_conf_ef}')
'''

s = s.replace(needle, '\n' + bloco + needle, 1)
p.write_text(s, encoding='utf-8')
# gatilho v3
