from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

s = s.replace(
    'from razync.companies import CONFIGURACOES_AUTOKRAFT',
    'from razync.companies import CONFIGURACOES_AUTOKRAFT, CONFIGURACOES_ACCEDE',
    1
)

# Banco Sicredi passa a ser reconhecido nos fluxos de conferência/classificação.
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

# Conferência genérica: mantém Autokraft como padrão e permite Itaú + Sicredi na ACCEDE.
s = s.replace(
    "def renderizar_conferencia_autokraft(prefixo_chaves='autokraft'):\n    \"\"\"Exibe a conferência independente da planilha final do Grupo Autokraft.\"\"\"",
    "def renderizar_conferencia_autokraft(prefixo_chaves='autokraft', bancos_config=None):\n    \"\"\"Exibe a conferência independente para empresas com planilha organizada.\"\"\"",
    1
)
s = s.replace(
    "    st.caption(\n        \"Envie a planilha final organizada e os extratos do Itaú, do Daycoval \"\n        \"ou dos dois bancos. Cada banco terá seu próprio relatório diário.\"\n    )\n\n    configs = [\n        {'nome': 'Itaú', 'slug': 'itau'},\n        {'nome': 'Daycoval', 'slug': 'daycoval'}\n    ]",
    "    configs = bancos_config or [\n        {'nome': 'Itaú', 'slug': 'itau'},\n        {'nome': 'Daycoval', 'slug': 'daycoval'}\n    ]\n    nomes_bancos = [config['nome'] for config in configs]\n    st.caption(\n        \"Envie a planilha final organizada e os extratos correspondentes. \"\n        \"Cada banco terá seu próprio relatório diário.\"\n    )",
    1
)
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

# Parser estrutural do SIG ACCEDE.
marcador = "\ndef filtrar_dataframe_periodo(df, data_inicial, data_final):"
if 'def processar_planilha_accede_sig(' not in s:
    funcao = r'''
@st.cache_data(show_spinner=False, max_entries=16)
def processar_planilha_accede_sig(file_bytes, banco_nome):
    """Converte o SIG da ACCEDE por estrutura de grupos para o Modelo Domínio."""
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    registros = []
    colunas_saida = ['DESCRIÇÃO', 'DATA', 'VALOR', 'DÉBITO', 'CRÉDITO', 'HISTÓRICO']

    def valor_texto_exato(valor):
        if valor is None or pd.isna(valor):
            return ''
        if isinstance(valor, float) and valor.is_integer():
            return str(int(valor))
        return str(valor).strip()

    for nome_aba in xls.sheet_names:
        bruto = pd.read_excel(xls, sheet_name=nome_aba, header=None, dtype=object)
        if bruto.empty:
            continue
        cabecalho = None
        for idx in range(min(len(bruto), 25)):
            nomes = [normalizar_texto(texto_celula_seguro(v)).strip() for v in bruto.iloc[idx].tolist()]
            if 'data' in nomes and 'entrada' in nomes and 'saida' in nomes and ('complemento' in nomes):
                cabecalho = idx
                break
        if cabecalho is None:
            continue

        cab = [normalizar_texto(texto_celula_seguro(v)).strip() for v in bruto.iloc[cabecalho].tolist()]
        def pos(nome):
            return cab.index(nome) if nome in cab else None
        c_data, c_dc, c_comp, c_conf = pos('data'), pos('d/c'), pos('complemento'), pos('conf')
        c_ent, c_sai = pos('entrada'), pos('saida')
        if None in (c_data, c_comp, c_ent, c_sai):
            continue

        linhas = bruto.iloc[cabecalho + 1:].reset_index(drop=True)
        i = 0
        while i < len(linhas):
            linha = linhas.iloc[i]
            data = pd.to_datetime(linha.iloc[c_data], dayfirst=True, errors='coerce')
            if pd.isna(data):
                i += 1
                continue

            j = i + 1
            detalhes = []
            while j < len(linhas):
                data_prox = pd.to_datetime(linhas.iloc[j].iloc[c_data], dayfirst=True, errors='coerce')
                if not pd.isna(data_prox):
                    break
                # linha sem data só é detalhe quando possui conteúdo material
                valores_linha = [texto_celula_seguro(v) for v in linhas.iloc[j].tolist()]
                if any(v for v in valores_linha):
                    detalhes.append(linhas.iloc[j])
                j += 1

            entrada = abs(limpar_valor_monetario(linha.iloc[c_ent])) if c_ent is not None else 0.0
            saida = abs(limpar_valor_monetario(linha.iloc[c_sai])) if c_sai is not None else 0.0
            natureza = 1 if entrada else (-1 if saida else 0)
            dc = texto_celula_seguro(linha.iloc[c_dc]) if c_dc is not None else ''
            complemento = texto_celula_seguro(linha.iloc[c_comp]) if c_comp is not None else ''
            conf = valor_texto_exato(linha.iloc[c_conf]) if c_conf is not None else ''

            if detalhes:
                for det in detalhes:
                    # No SIG, detalhes são deslocados uma coluna à esquerda:
                    # [vazio, Conf/Documento, Valor, Favorecido, ...]
                    documento_conf = valor_texto_exato(det.iloc[1]) if len(det) > 1 else ''
                    valor_det = abs(limpar_valor_monetario(det.iloc[2])) if len(det) > 2 else 0.0
                    favorecido = valor_texto_exato(det.iloc[3]) if len(det) > 3 else ''
                    if valor_det == 0:
                        continue
                    historico = ' '.join(parte for parte in [favorecido, documento_conf] if parte).strip()
                    if not historico:
                        historico = documento_conf or favorecido or complemento or dc or 'MOVIMENTO BANCARIO'
                    registros.append({
                        'DESCRIÇÃO': 'BANCO ITAÚ' if normalizar_texto(banco_nome) == 'itau' else 'SICREDI',
                        'DATA': data.to_pydatetime(),
                        'VALOR': round(valor_det * (natureza or -1), 2),
                        'DÉBITO': '', 'CRÉDITO': '',
                        'HISTÓRICO': limpar_caracteres_ilegais(historico)
                    })
            else:
                valor = entrada if entrada else (-saida if saida else 0.0)
                if valor:
                    # Ordem solicitada: Complemento; Fav+Conf; Fav+Documento; Fav; Documento; Conf; descrição.
                    historico = complemento or conf or dc or 'MOVIMENTO BANCARIO'
                    registros.append({
                        'DESCRIÇÃO': 'BANCO ITAÚ' if normalizar_texto(banco_nome) == 'itau' else 'SICREDI',
                        'DATA': data.to_pydatetime(),
                        'VALOR': round(valor, 2),
                        'DÉBITO': '', 'CRÉDITO': '',
                        'HISTÓRICO': limpar_caracteres_ilegais(historico)
                    })
            i = j

    df = pd.DataFrame(registros, columns=colunas_saida)
    if df.empty:
        raise ValueError(f'Nenhum lançamento válido foi encontrado na planilha do {banco_nome}.')
    return df.sort_values('DATA', kind='stable').reset_index(drop=True)

'''
    if marcador not in s:
        raise SystemExit('Marcador para inserir parser ACCEDE não encontrado.')
    s = s.replace(marcador, '\n' + funcao + marcador, 1)

# Títulos e descrições das novas empresas.
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

# Cards em duas linhas de três para manter tamanho consistente.
antigo_cards = '''        # Uma linha equilibrada com quatro cards responsivos e espaçamento consistente.\n        col_emp1, col_emp2, col_emp3, col_emp4 = st.columns(\n            [1, 1, 1, 1], gap="medium"\n        )\n\n        cards_empresas = [\n            (col_emp1, 'nova_geracao', 'org_empresa_card_nova', '266 - Nova Geração'),\n            (col_emp2, 'autokraft_industrial', 'org_empresa_card_autokraft_industrial', '3 - Autokraft Industrial'),\n            (col_emp3, 'autokraft_projetos', 'org_empresa_card_autokraft_projetos', '178 - Autokraft Projetos'),\n            (col_emp4, 'isa', 'org_empresa_card_isa', '343 - I.S.A'),\n        ]'''
novo_cards = '''        col_emp1, col_emp2, col_emp3 = st.columns([1, 1, 1], gap="medium")\n        col_emp4, col_emp5, col_emp6 = st.columns([1, 1, 1], gap="medium")\n\n        cards_empresas = [\n            (col_emp1, 'nova_geracao', 'org_empresa_card_nova', '266 - Nova Geração'),\n            (col_emp2, 'autokraft_industrial', 'org_empresa_card_autokraft_industrial', '3 - Autokraft Industrial'),\n            (col_emp3, 'autokraft_projetos', 'org_empresa_card_autokraft_projetos', '178 - Autokraft Projetos'),\n            (col_emp4, 'isa', 'org_empresa_card_isa', '343 - I.S.A'),\n            (col_emp5, 'accede_automacao', 'org_empresa_card_accede_automacao', '1000 - ACCEDE AUTOMAÇÃO'),\n            (col_emp6, 'accede_equipamentos', 'org_empresa_card_accede_equipamentos', '1001 - ACCEDE EQUIPAMENTOS'),\n        ]'''
if antigo_cards in s:
    s = s.replace(antigo_cards, novo_cards, 1)
else:
    raise SystemExit('Bloco de cards não encontrado.')

# Área completa das duas ACCEDE, antes do bloco Nova Geração.
marcador_ng = "\n    if st.session_state['empresa_organizador'] == 'nova_geracao':"
if "if st.session_state['empresa_organizador'] in {'accede_automacao', 'accede_equipamentos'}:" not in s:
    bloco = r'''
    if st.session_state['empresa_organizador'] in {'accede_automacao', 'accede_equipamentos'}:
        chave_accede = st.session_state['empresa_organizador']
        config_accede = CONFIGURACOES_ACCEDE[chave_accede]
        empresa_accede = config_accede['empresa']
        slug_accede = config_accede['slug']

        aba_operacoes_accede, aba_base_accede = st.tabs([
            'Organizar e conferir', 'Base inteligente de Débito e Crédito'
        ])
        with aba_base_accede:
            renderizar_base_inteligente_empresa(
                slug_accede, empresa_accede, {'itau', 'sicredi'},
                config_accede['contas_bancarias']
            )

        with aba_operacoes_accede:
            st.caption(
                'Envie as planilhas SIG do Itaú e/ou Sicredi. Grupos com linhas sem DATA '
                'são expandidos integralmente e o total do grupo não é duplicado.'
            )
            col_itau_ac, col_sicredi_ac = st.columns(2)
            with col_itau_ac:
                arq_itau_ac = st.file_uploader(
                    'Planilha SIG — Itaú', type=['xlsx', 'xls'],
                    key=f'{slug_accede}_sig_itau'
                )
            with col_sicredi_ac:
                arq_sicredi_ac = st.file_uploader(
                    'Planilha SIG — Sicredi', type=['xlsx', 'xls'],
                    key=f'{slug_accede}_sig_sicredi'
                )

            dados_accede = {}
            try:
                if arq_itau_ac is not None:
                    dados_accede['Itaú'] = {
                        'principal': processar_planilha_accede_sig(arq_itau_ac.getvalue(), 'Itaú'),
                        'retirados': pd.DataFrame()
                    }
                if arq_sicredi_ac is not None:
                    dados_accede['Sicredi'] = {
                        'principal': processar_planilha_accede_sig(arq_sicredi_ac.getvalue(), 'Sicredi'),
                        'retirados': pd.DataFrame()
                    }

                if dados_accede:
                    df_accede = pd.concat(
                        [item['principal'] for item in dados_accede.values()], ignore_index=True
                    ).sort_values('DATA', kind='stable').reset_index(drop=True)
                    datas_accede = pd.to_datetime(df_accede['DATA'], errors='coerce').dropna().dt.date
                    dmin, dmax = datas_accede.min(), datas_accede.max()
                    ac1, ac2, ac3 = st.columns(3)
                    ac1.metric('Lançamentos', len(df_accede))
                    ac2.metric('Entradas', formatar_moeda(df_accede.loc[df_accede['VALOR'] > 0, 'VALOR'].sum()))
                    ac3.metric('Saídas', formatar_moeda(abs(df_accede.loc[df_accede['VALOR'] < 0, 'VALOR'].sum())))
                    st.caption(f'Período identificado: {dmin.strftime("%d/%m/%Y")} a {dmax.strftime("%d/%m/%Y")}.')

                    arquivo_accede = gerar_excel_nova_geracao(dados_accede)
                    st.download_button(
                        'Baixar planilha no Modelo Domínio', data=arquivo_accede,
                        file_name=f"{config_accede['arquivo']}_{dmin.strftime('%m%Y')}.xlsx",
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        use_container_width=True, key=f'{slug_accede}_download_modelo'
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
    if marcador_ng not in s:
        raise SystemExit('Marcador Nova Geração não encontrado.')
    s = s.replace(marcador_ng, '\n' + bloco + marcador_ng, 1)

checks = [
    'CONFIGURACOES_AUTOKRAFT, CONFIGURACOES_ACCEDE',
    'def processar_planilha_accede_sig(file_bytes, banco_nome):',
    "'accede_automacao': '1000 - ACCEDE AUTOMAÇÃO'",
    "'accede_equipamentos': '1001 - ACCEDE EQUIPAMENTOS'",
    "{'nome': 'Sicredi', 'slug': 'sicredi'}",
    "renderizar_base_inteligente_empresa(\n                slug_accede, empresa_accede, {'itau', 'sicredi'}",
]
for check in checks:
    if check not in s:
        raise SystemExit(f'Check ausente: {check}')

p.write_text(s, encoding='utf-8')
print('Empresas ACCEDE e parser SIG adicionados ao Razync.')
