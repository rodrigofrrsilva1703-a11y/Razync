from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

# -----------------------------------------------------------------------------
# Núcleo já aplicado: mantém idempotente.
# -----------------------------------------------------------------------------
s = s.replace(
    'from razync.companies import CONFIGURACOES_AUTOKRAFT',
    'from razync.companies import CONFIGURACOES_AUTOKRAFT, CONFIGURACOES_ACCEDE',
    1
)
s = s.replace(
    "    if 'daycoval' in texto:\n        return 'daycoval'\n    return ''",
    "    if 'daycoval' in texto:\n        return 'daycoval'\n    if 'sicredi' in texto:\n        return 'sicredi'\n    return ''",
    1
)
s = s.replace(
    "        'daycoval': 'Daycoval'\n    }.get(chave, chave)",
    "        'daycoval': 'Daycoval', 'sicredi': 'Sicredi'\n    }.get(chave, chave)",
    1
)
s = s.replace(
    "                    'fibra': 'BANCO FIBRA', 'daycoval': 'BANCO DAYCOVAL'\n                }[banco_alvo]",
    "                    'fibra': 'BANCO FIBRA', 'daycoval': 'BANCO DAYCOVAL',\n                    'sicredi': 'SICREDI'\n                }[banco_alvo]",
    1
)
s = s.replace(
    "if banco_linha not in {'itau', 'bradesco', 'fibra', 'daycoval'} or not assinatura:",
    "if banco_linha not in {'itau', 'bradesco', 'fibra', 'daycoval', 'sicredi'} or not assinatura:",
    1
)

# -----------------------------------------------------------------------------
# Parser estrutural das planilhas SIG ACCEDE.
# -----------------------------------------------------------------------------
if 'def processar_planilha_accede_sig(' not in s:
    marcador = '\ndef filtrar_dataframe_periodo(df, data_inicial, data_final):'
    if marcador not in s:
        raise SystemExit('Marcador do parser ACCEDE não encontrado.')

    funcao = r'''
@st.cache_data(show_spinner=False, max_entries=16)
def processar_planilha_accede_sig(file_bytes, banco_nome):
    """
    Converte planilhas SIG da ACCEDE para o Modelo Domínio.

    Regra estrutural: uma linha com DATA inicia o lançamento/grupo. Todas as linhas
    seguintes sem DATA pertencem a esse grupo até surgir uma nova DATA. Quando há
    detalhamento com valor individual, o total da linha principal não é duplicado.
    """
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    colunas_saida = ['DESCRIÇÃO', 'DATA', 'VALOR', 'DÉBITO', 'CRÉDITO', 'HISTÓRICO']
    registros = []

    def texto_exato(valor):
        if valor is None or pd.isna(valor):
            return ''
        if isinstance(valor, float) and valor.is_integer():
            return str(int(valor))
        return limpar_caracteres_ilegais(str(valor)).strip()

    for nome_aba in xls.sheet_names:
        bruto = pd.read_excel(xls, sheet_name=nome_aba, header=None, dtype=object)
        if bruto.empty:
            continue

        idx_header = None
        nomes_header = None
        for idx in range(min(len(bruto), 30)):
            nomes = [normalizar_texto(texto_celula_seguro(v)).strip() for v in bruto.iloc[idx].tolist()]
            if all(nome in nomes for nome in ['data', 'complemento', 'entrada', 'saida']):
                idx_header = idx
                nomes_header = nomes
                break
        if idx_header is None:
            continue

        def coluna(nome):
            return nomes_header.index(nome) if nome in nomes_header else None

        c_data = coluna('data')
        c_dc = coluna('d/c')
        c_comp = coluna('complemento')
        c_conf = coluna('conf')
        c_ent = coluna('entrada')
        c_sai = coluna('saida')
        linhas = bruto.iloc[idx_header + 1:].reset_index(drop=True)
        i = 0

        while i < len(linhas):
            principal = linhas.iloc[i]
            data = pd.to_datetime(principal.iloc[c_data], dayfirst=True, errors='coerce')
            if pd.isna(data):
                i += 1
                continue

            j = i + 1
            detalhes = []
            while j < len(linhas):
                proxima_data = pd.to_datetime(linhas.iloc[j].iloc[c_data], dayfirst=True, errors='coerce')
                if not pd.isna(proxima_data):
                    break
                valores_linha = [texto_celula_seguro(v) for v in linhas.iloc[j].tolist()]
                if any(valores_linha):
                    detalhes.append(linhas.iloc[j])
                j += 1

            entrada = abs(limpar_valor_monetario(principal.iloc[c_ent])) if c_ent is not None else 0.0
            saida = abs(limpar_valor_monetario(principal.iloc[c_sai])) if c_sai is not None else 0.0
            sinal_grupo = 1 if entrada else (-1 if saida else 0)
            dc_principal = texto_exato(principal.iloc[c_dc]) if c_dc is not None else ''
            complemento = texto_exato(principal.iloc[c_comp]) if c_comp is not None else ''
            conf_principal = texto_exato(principal.iloc[c_conf]) if c_conf is not None else ''
            descricao_banco = 'BANCO ITAÚ' if normalizar_texto(banco_nome) == 'itau' else 'SICREDI'

            detalhes_validos = []
            for detalhe in detalhes:
                # Nos SIGs ACCEDE os detalhes aparecem deslocados para a esquerda:
                # [vazio/data, Conf/Documento, Valor, Favorecido/Descrição, ...].
                conf_doc = texto_exato(detalhe.iloc[1]) if len(detalhe) > 1 else ''
                valor_individual = abs(limpar_valor_monetario(detalhe.iloc[2])) if len(detalhe) > 2 else 0.0
                favorecido = texto_exato(detalhe.iloc[3]) if len(detalhe) > 3 else ''
                if valor_individual:
                    detalhes_validos.append((conf_doc, valor_individual, favorecido))

            if detalhes_validos:
                for conf_doc, valor_individual, favorecido in detalhes_validos:
                    historico = ' '.join(parte for parte in [favorecido, conf_doc] if parte).strip()
                    if not historico:
                        historico = complemento or conf_principal or dc_principal or 'MOVIMENTO BANCARIO'
                    registros.append({
                        'DESCRIÇÃO': descricao_banco,
                        'DATA': data.to_pydatetime(),
                        'VALOR': round(valor_individual * (sinal_grupo or -1), 2),
                        'DÉBITO': '',
                        'CRÉDITO': '',
                        'HISTÓRICO': historico
                    })
            else:
                valor = entrada if entrada else (-saida if saida else 0.0)
                if valor:
                    historico = complemento or conf_principal or dc_principal or 'MOVIMENTO BANCARIO'
                    registros.append({
                        'DESCRIÇÃO': descricao_banco,
                        'DATA': data.to_pydatetime(),
                        'VALOR': round(valor, 2),
                        'DÉBITO': '',
                        'CRÉDITO': '',
                        'HISTÓRICO': historico
                    })
            i = j

    df = pd.DataFrame(registros, columns=colunas_saida)
    if df.empty:
        raise ValueError(f'Nenhum lançamento válido foi encontrado na planilha SIG do {banco_nome}.')
    return df.sort_values('DATA', kind='stable').reset_index(drop=True)

'''
    s = s.replace(marcador, '\n' + funcao + marcador, 1)

# -----------------------------------------------------------------------------
# Conferência reutilizável: Autokraft continua Itaú/Daycoval; ACCEDE usa Itaú/Sicredi.
# -----------------------------------------------------------------------------
s = s.replace(
    "def renderizar_conferencia_autokraft(prefixo_chaves='autokraft'):",
    "def renderizar_conferencia_autokraft(prefixo_chaves='autokraft', bancos_config=None):",
    1
)

antigo_inicio_conf = '''    st.caption(\n        "Envie a planilha final organizada e os extratos do Itaú, do Daycoval "\n        "ou dos dois bancos. Cada banco terá seu próprio relatório diário."\n    )\n\n    configs = [\n        {'nome': 'Itaú', 'slug': 'itau'},\n        {'nome': 'Daycoval', 'slug': 'daycoval'}\n    ]'''
novo_inicio_conf = '''    configs = bancos_config or [\n        {'nome': 'Itaú', 'slug': 'itau'},\n        {'nome': 'Daycoval', 'slug': 'daycoval'}\n    ]\n    nomes_bancos = [config['nome'] for config in configs]\n    st.caption(\n        "Envie a planilha final organizada e os extratos correspondentes. "\n        "Cada banco terá seu próprio relatório diário."\n    )'''
if antigo_inicio_conf in s:
    s = s.replace(antigo_inicio_conf, novo_inicio_conf, 1)

s = s.replace(
    "        bancos_escolhidos = ['Itaú', 'Daycoval']\n        st.caption(\"Serão apresentados relatórios separados para Itaú e Daycoval.\")",
    "        bancos_escolhidos = nomes_bancos\n        st.caption(\"Serão apresentados relatórios separados para os bancos selecionados.\")",
    1
)
s = s.replace(
    "            ['Itaú', 'Daycoval'],\n            default=['Itaú'],",
    "            nomes_bancos,\n            default=[nomes_bancos[0]],",
    1
)

# -----------------------------------------------------------------------------
# Títulos e textos das duas empresas.
# -----------------------------------------------------------------------------
s = s.replace(
    "            'isa': '343 - I.S.A'\n        }.get(empresa_organizador, 'Organizador de Planilhas'))",
    "            'isa': '343 - I.S.A',\n            'accede_automacao': '1000 - ACCEDE AUTOMAÇÃO',\n            'accede_equipamentos': '1001 - ACCEDE EQUIPAMENTOS'\n        }.get(empresa_organizador, 'Organizador de Planilhas'))",
    1
)
s = s.replace(
    "        'isa': 'Organize os mapas diários e confira os extratos da 343 - I.S.A.'\n    }.get(",
    "        'isa': 'Organize os mapas diários e confira os extratos da 343 - I.S.A.',\n        'accede_automacao': 'Organize as planilhas SIG e confira Itaú e Sicredi da 1000 - ACCEDE AUTOMAÇÃO.',\n        'accede_equipamentos': 'Organize as planilhas SIG e confira Itaú e Sicredi da 1001 - ACCEDE EQUIPAMENTOS.'\n    }.get(",
    1
)

# -----------------------------------------------------------------------------
# Cards: 6 empresas em duas linhas de três.
# -----------------------------------------------------------------------------
if "'accede_automacao', 'org_empresa_card_accede_automacao'" not in s:
    inicio = s.find('        # Uma linha equilibrada com quatro cards responsivos e espaçamento consistente.')
    fim = s.find('        for coluna_card, chave_empresa, chave_card, titulo_card in cards_empresas:', inicio)
    if inicio < 0 or fim < 0:
        raise SystemExit('Bloco dos cards de empresas não encontrado.')
    cards = '''        col_emp1, col_emp2, col_emp3 = st.columns([1, 1, 1], gap="medium")\n        col_emp4, col_emp5, col_emp6 = st.columns([1, 1, 1], gap="medium")\n\n        cards_empresas = [\n            (col_emp1, 'nova_geracao', 'org_empresa_card_nova', '266 - Nova Geração'),\n            (col_emp2, 'autokraft_industrial', 'org_empresa_card_autokraft_industrial', '3 - Autokraft Industrial'),\n            (col_emp3, 'autokraft_projetos', 'org_empresa_card_autokraft_projetos', '178 - Autokraft Projetos'),\n            (col_emp4, 'isa', 'org_empresa_card_isa', '343 - I.S.A'),\n            (col_emp5, 'accede_automacao', 'org_empresa_card_accede_automacao', '1000 - ACCEDE AUTOMAÇÃO'),\n            (col_emp6, 'accede_equipamentos', 'org_empresa_card_accede_equipamentos', '1001 - ACCEDE EQUIPAMENTOS'),\n        ]\n'''
    s = s[:inicio] + cards + s[fim:]

# Faz os novos cards herdarem exatamente o mesmo visual dos atuais.
s = s.replace(
    '.st-key-org_empresa_card_isa {',
    '.st-key-org_empresa_card_isa,\n        .st-key-org_empresa_card_accede_automacao,\n        .st-key-org_empresa_card_accede_equipamentos {',
)
s = s.replace(
    '.st-key-org_empresa_card_isa button {',
    '.st-key-org_empresa_card_isa button,\n        .st-key-org_empresa_card_accede_automacao button,\n        .st-key-org_empresa_card_accede_equipamentos button {',
)
s = s.replace(
    '.st-key-org_empresa_card_isa button::before {',
    '.st-key-org_empresa_card_isa button::before,\n        .st-key-org_empresa_card_accede_automacao button::before,\n        .st-key-org_empresa_card_accede_equipamentos button::before {',
)
s = s.replace(
    '.st-key-org_empresa_card_isa button p {',
    '.st-key-org_empresa_card_isa button p,\n        .st-key-org_empresa_card_accede_automacao button p,\n        .st-key-org_empresa_card_accede_equipamentos button p {',
)
s = s.replace(
    '.st-key-org_empresa_card_isa button strong {',
    '.st-key-org_empresa_card_isa button strong,\n        .st-key-org_empresa_card_accede_automacao button strong,\n        .st-key-org_empresa_card_accede_equipamentos button strong {',
)
s = s.replace(
    '.st-key-org_empresa_card_isa button:hover {',
    '.st-key-org_empresa_card_isa button:hover,\n        .st-key-org_empresa_card_accede_automacao button:hover,\n        .st-key-org_empresa_card_accede_equipamentos button:hover {',
)

# -----------------------------------------------------------------------------
# Área de trabalho ACCEDE com Base Inteligente + organização + conferência.
# -----------------------------------------------------------------------------
marcador_ng = "\n    if st.session_state['empresa_organizador'] == 'nova_geracao':"
if "if st.session_state['empresa_organizador'] in {'accede_automacao', 'accede_equipamentos'}:" not in s:
    if marcador_ng not in s:
        raise SystemExit('Marcador Nova Geração não encontrado.')
    bloco = r'''
    if st.session_state['empresa_organizador'] in {'accede_automacao', 'accede_equipamentos'}:
        chave_accede = st.session_state['empresa_organizador']
        config_accede = CONFIGURACOES_ACCEDE[chave_accede]
        empresa_accede = config_accede['empresa']
        slug_accede = config_accede['slug']

        aba_operacoes_accede, aba_base_accede = st.tabs([
            'Organizar e conferir',
            'Base inteligente de Débito e Crédito'
        ])

        with aba_base_accede:
            renderizar_base_inteligente_empresa(
                slug_accede,
                empresa_accede,
                {'itau', 'sicredi'},
                config_accede['contas_bancarias']
            )

        with aba_operacoes_accede:
            st.caption(
                'Envie as planilhas SIG do Itaú e/ou Sicredi. Linhas sem DATA abaixo '
                'de um lançamento são tratadas como detalhamento do mesmo grupo.'
            )
            col_itau_accede, col_sicredi_accede = st.columns(2)
            with col_itau_accede:
                arquivo_itau_accede = st.file_uploader(
                    'Planilha SIG — Itaú',
                    type=['xlsx', 'xls'],
                    key=f'{slug_accede}_sig_itau'
                )
            with col_sicredi_accede:
                arquivo_sicredi_accede = st.file_uploader(
                    'Planilha SIG — Sicredi',
                    type=['xlsx', 'xls'],
                    key=f'{slug_accede}_sig_sicredi'
                )

            dados_accede = {}
            try:
                if arquivo_itau_accede is not None:
                    dados_accede['Itaú'] = {
                        'principal': executar_com_loading(
                            'Organizando a planilha SIG do Itaú...',
                            processar_planilha_accede_sig,
                            arquivo_itau_accede.getvalue(),
                            'Itaú'
                        ),
                        'retirados': pd.DataFrame()
                    }
                if arquivo_sicredi_accede is not None:
                    dados_accede['Sicredi'] = {
                        'principal': executar_com_loading(
                            'Organizando a planilha SIG do Sicredi...',
                            processar_planilha_accede_sig,
                            arquivo_sicredi_accede.getvalue(),
                            'Sicredi'
                        ),
                        'retirados': pd.DataFrame()
                    }

                if dados_accede:
                    df_accede = pd.concat(
                        [dados['principal'] for dados in dados_accede.values()],
                        ignore_index=True
                    ).sort_values(['DATA', 'DESCRIÇÃO'], kind='stable').reset_index(drop=True)
                    datas_accede = pd.to_datetime(df_accede['DATA'], errors='coerce').dropna().dt.date
                    data_min_accede = min(datas_accede)
                    data_max_accede = max(datas_accede)

                    met_ac1, met_ac2, met_ac3 = st.columns(3)
                    met_ac1.metric('Lançamentos', len(df_accede))
                    met_ac2.metric(
                        'Entradas',
                        formatar_moeda(df_accede.loc[df_accede['VALOR'] > 0, 'VALOR'].sum())
                    )
                    met_ac3.metric(
                        'Saídas',
                        formatar_moeda(abs(df_accede.loc[df_accede['VALOR'] < 0, 'VALOR'].sum()))
                    )
                    st.caption(
                        f'Período identificado: {data_min_accede.strftime("%d/%m/%Y")} a '
                        f'{data_max_accede.strftime("%d/%m/%Y")}.'
                    )

                    modelo_bytes_accede = None
                    for caminho_modelo in ['Modelo dominio.xlsx', 'Modelo dominio(6).xlsx']:
                        if os.path.exists(caminho_modelo):
                            with open(caminho_modelo, 'rb') as modelo_arquivo:
                                modelo_bytes_accede = modelo_arquivo.read()
                            break
                    arquivo_final_accede = gerar_excel_nova_geracao(
                        dados_accede, modelo_bytes_accede
                    )
                    st.download_button(
                        'Baixar planilha no Modelo Domínio',
                        data=arquivo_final_accede,
                        file_name=(
                            f"{config_accede['arquivo']}_"
                            f"{data_min_accede.strftime('%d%m%Y')}_a_"
                            f"{data_max_accede.strftime('%d%m%Y')}.xlsx"
                        ),
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        use_container_width=True,
                        key=f'{slug_accede}_download_modelo'
                    )
            except Exception as erro_accede:
                st.error(f'Não foi possível processar as planilhas da ACCEDE: {erro_accede}')

            st.markdown(f'#### Conferência — {empresa_accede}')
            renderizar_conferencia_autokraft(
                slug_accede,
                bancos_config=[
                    {'nome': 'Itaú', 'slug': 'itau'},
                    {'nome': 'Sicredi', 'slug': 'sicredi'}
                ]
            )
'''
    s = s.replace(marcador_ng, '\n' + bloco + marcador_ng, 1)

# Validações mínimas para impedir commit parcial.
checks = [
    'CONFIGURACOES_AUTOKRAFT, CONFIGURACOES_ACCEDE',
    'def processar_planilha_accede_sig(file_bytes, banco_nome):',
    "return 'sicredi'",
    "'accede_automacao': '1000 - ACCEDE AUTOMAÇÃO'",
    "'accede_equipamentos': '1001 - ACCEDE EQUIPAMENTOS'",
    "'org_empresa_card_accede_automacao'",
    "'org_empresa_card_accede_equipamentos'",
    "renderizar_base_inteligente_empresa(\n                slug_accede,",
    "{'nome': 'Sicredi', 'slug': 'sicredi'}",
]
for check in checks:
    if check not in s:
        raise SystemExit(f'Validação ACCEDE ausente: {check}')

p.write_text(s, encoding='utf-8')
print('Integração completa ACCEDE preparada no app.py.')
