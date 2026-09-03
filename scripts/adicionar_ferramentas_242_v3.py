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

old = """                    if despesas_ef is not None and not despesas_ef.empty:
                        tabs_nomes_ef.append('Despesas')
                        tabs_dfs_ef.append(despesas_ef)
"""
new = """                    for conta, df_ef in despesas_ef.items():
                        tabs_nomes_ef.append('Despesa · ' + CONTAS_ELETRO_FORTE.get(conta, conta))
                        tabs_dfs_ef.append(df_ef)
"""
if old not in s:
    raise SystemExit('prévia despesa não localizada')
s = s.replace(old, new, 1)

old = "if despesas_ef is not None and not despesas_ef.empty:"
if old not in s:
    raise SystemExit('condição download despesa não localizada')
s = s.replace(old, "if despesas_ef:", 1)

needle = "\n    if st.session_state['empresa_organizador'] == 'lcarlos':\n"
if needle not in s:
    raise SystemExit('ponto de inserção da conferência 242 não localizado')

bloco = r'''
        with aba_conferencia_ef:
            st.markdown('#### Conferência com Extrato')
            st.caption(
                'A conferência é feita por conta, sem misturar os dois Itaús. '
                'Despesa e Fornecedor são tratados como saídas; Recebido como entrada. '
                'A conta 0 permanece somente para revisão manual.'
            )

            dados_conferencia_ef = {'8': [], '508': [], '509': []}
            origens_conferencia_ef = [
                ('Despesa', despesas_ef, -1),
                ('Fornecedor', fornecedores_ef, -1),
                ('Recebido', recebidos_ef, 1),
            ]
            for origem_ef, grupos_ef, sinal_ef in origens_conferencia_ef:
                for conta_ef, df_origem_ef in (grupos_ef or {}).items():
                    if conta_ef not in dados_conferencia_ef or df_origem_ef.empty:
                        continue
                    df_conf_origem_ef = df_origem_ef.copy()
                    df_conf_origem_ef['DATA'] = pd.to_datetime(
                        df_conf_origem_ef['DATA'], dayfirst=True, errors='coerce'
                    )
                    df_conf_origem_ef['VALOR'] = pd.to_numeric(
                        df_conf_origem_ef['VALOR'], errors='coerce'
                    ).fillna(0.0).abs() * sinal_ef
                    df_conf_origem_ef['ORIGEM'] = origem_ef
                    dados_conferencia_ef[conta_ef].append(df_conf_origem_ef)

            configs_conferencia_ef = [
                ('8', 'Banco do Brasil · Conta 8'),
                ('508', 'Itaú · 105318 · Conta 508'),
                ('509', 'Itaú · 181537 · Conta 509'),
            ]
            abas_conferencia_ef = st.tabs([rotulo for _, rotulo in configs_conferencia_ef])

            for aba_conf_ef, (conta_conf_ef, rotulo_conf_ef) in zip(
                abas_conferencia_ef, configs_conferencia_ef
            ):
                with aba_conf_ef:
                    partes_planilha_ef = dados_conferencia_ef.get(conta_conf_ef, [])
                    if not partes_planilha_ef:
                        st.info(
                            f'Nenhum lançamento da conta {conta_conf_ef} foi identificado nas '
                            'planilhas atualmente anexadas em Organizar arquivos.'
                        )
                        continue

                    df_planilha_conf_ef = pd.concat(
                        partes_planilha_ef, ignore_index=True
                    ).dropna(subset=['DATA'])
                    if df_planilha_conf_ef.empty:
                        st.info('Não há datas válidas nesta conta para conferência.')
                        continue

                    data_ini_conf_ef = df_planilha_conf_ef['DATA'].min().normalize()
                    data_fim_conf_ef = df_planilha_conf_ef['DATA'].max().normalize()
                    st.caption(
                        f"Período das planilhas: {data_ini_conf_ef.strftime('%d/%m/%Y')} a "
                        f"{data_fim_conf_ef.strftime('%d/%m/%Y')}"
                    )

                    extrato_conf_ef = st.file_uploader(
                        f'Extrato — {rotulo_conf_ef}',
                        type=['pdf', 'ofx', 'csv', 'xlsx', 'xls'],
                        key=f'ef242_extrato_conferencia_{conta_conf_ef}',
                        help='Envie somente o extrato desta conta. Os dois Itaús são conferidos separadamente.',
                    )
                    if extrato_conf_ef is None:
                        st.info('Envie o extrato desta conta para iniciar a conferência.')
                        continue

                    try:
                        lancamentos_extrato_ef = executar_com_loading(
                            f'Lendo o extrato da conta {conta_conf_ef}...',
                            processar_extrato_conferencia_empresa,
                            extrato_conf_ef.getvalue(),
                            extrato_conf_ef.name,
                        )
                        df_extrato_conf_ef = pd.DataFrame(lancamentos_extrato_ef or [])
                        if df_extrato_conf_ef.empty:
                            st.warning('Nenhum lançamento foi reconhecido neste extrato.')
                            continue
                        df_extrato_conf_ef['DATA'] = pd.to_datetime(
                            df_extrato_conf_ef['DATA'], dayfirst=True, errors='coerce'
                        )
                        df_extrato_conf_ef['VALOR'] = pd.to_numeric(
                            df_extrato_conf_ef['VALOR'], errors='coerce'
                        ).fillna(0.0)
                        df_extrato_conf_ef = df_extrato_conf_ef[
                            df_extrato_conf_ef['DATA'].between(
                                data_ini_conf_ef, data_fim_conf_ef, inclusive='both'
                            )
                        ].dropna(subset=['DATA'])
                        if df_extrato_conf_ef.empty:
                            st.warning('O extrato não possui lançamentos dentro do período das planilhas.')
                            continue

                        datas_conf_ef = sorted(set(
                            df_planilha_conf_ef['DATA'].dt.normalize().tolist()
                        ) | set(
                            df_extrato_conf_ef['DATA'].dt.normalize().tolist()
                        ))
                        linhas_conf_ef = []
                        for data_conf_ef in datas_conf_ef:
                            plan_dia_ef = df_planilha_conf_ef[
                                df_planilha_conf_ef['DATA'].dt.normalize().eq(data_conf_ef)
                            ]
                            ext_dia_ef = df_extrato_conf_ef[
                                df_extrato_conf_ef['DATA'].dt.normalize().eq(data_conf_ef)
                            ]
                            ent_plan_ef = float(plan_dia_ef.loc[plan_dia_ef['VALOR'] > 0, 'VALOR'].sum())
                            sai_plan_ef = float(abs(plan_dia_ef.loc[plan_dia_ef['VALOR'] < 0, 'VALOR'].sum()))
                            ent_ext_ef = float(ext_dia_ef.loc[ext_dia_ef['VALOR'] > 0, 'VALOR'].sum())
                            sai_ext_ef = float(abs(ext_dia_ef.loc[ext_dia_ef['VALOR'] < 0, 'VALOR'].sum()))
                            dif_ent_ef = round(ent_plan_ef - ent_ext_ef, 2)
                            dif_sai_ef = round(sai_plan_ef - sai_ext_ef, 2)
                            bate_ef = abs(dif_ent_ef) <= 0.02 and abs(dif_sai_ef) <= 0.02
                            linhas_conf_ef.append({
                                'Data': data_conf_ef.strftime('%d/%m/%Y'),
                                'Entrada Planilha': ent_plan_ef,
                                'Entrada Extrato': ent_ext_ef,
                                'Dif. Entradas': dif_ent_ef,
                                'Saída Planilha': sai_plan_ef,
                                'Saída Extrato': sai_ext_ef,
                                'Dif. Saídas': dif_sai_ef,
                                'Status': '✅ Batendo' if bate_ef else '❌ Divergente',
                            })

                        diario_conf_ef = pd.DataFrame(linhas_conf_ef)
                        qtd_batendo_ef = int((diario_conf_ef['Status'] == '✅ Batendo').sum())
                        qtd_div_ef = int((diario_conf_ef['Status'] == '❌ Divergente').sum())
                        mc1_ef, mc2_ef = st.columns(2)
                        mc1_ef.metric('Dias batendo', qtd_batendo_ef)
                        mc2_ef.metric('Dias divergentes', qtd_div_ef)

                        st.dataframe(
                            diario_conf_ef,
                            use_container_width=True,
                            hide_index=True,
                            height=min(420, 38 + max(1, min(len(diario_conf_ef), 10)) * 35),
                            column_config={
                                'Entrada Planilha': st.column_config.NumberColumn(format='R$ %.2f'),
                                'Entrada Extrato': st.column_config.NumberColumn(format='R$ %.2f'),
                                'Dif. Entradas': st.column_config.NumberColumn(format='R$ %.2f'),
                                'Saída Planilha': st.column_config.NumberColumn(format='R$ %.2f'),
                                'Saída Extrato': st.column_config.NumberColumn(format='R$ %.2f'),
                                'Dif. Saídas': st.column_config.NumberColumn(format='R$ %.2f'),
                            },
                        )
                        if qtd_div_ef == 0:
                            st.success('Conferência concluída: todos os dias estão batendo.')
                        else:
                            st.warning(
                                f'{qtd_div_ef} dia(s) possuem diferença entre as planilhas e o extrato.'
                            )
                    except Exception as erro_conf_ef:
                        st.error(f'Não foi possível conferir a conta {conta_conf_ef}: {erro_conf_ef}')
'''

s = s.replace(needle, '\n' + bloco + needle, 1)
p.write_text(s, encoding='utf-8')
# gatilho v2
