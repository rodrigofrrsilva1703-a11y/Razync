from pathlib import Path
import re

path = Path('app.py')
text = path.read_text(encoding='utf-8')

helper = r'''

def renderizar_previa_bancos_padrao(dados_bancos, titulo='Pré-visualização por banco', ordem=None):
    """Renderiza o padrão visual de prévia bancária usado pelas empresas do Razync."""
    if not dados_bancos:
        return

    itens = []
    nomes = list(dados_bancos.keys())
    if ordem:
        nomes = [nome for nome in ordem if nome in dados_bancos] + [
            nome for nome in nomes if nome not in ordem
        ]

    for nome_banco in nomes:
        dados_banco = dados_bancos.get(nome_banco)
        if isinstance(dados_banco, dict) and 'principal' in dados_banco:
            df_banco = dados_banco.get('principal')
        elif isinstance(dados_banco, dict) and 'lancamentos' in dados_banco:
            df_banco = dados_banco.get('lancamentos')
        elif isinstance(dados_banco, pd.DataFrame):
            df_banco = dados_banco
        else:
            continue

        if df_banco is None or df_banco.empty or 'VALOR' not in df_banco.columns:
            continue
        itens.append((nome_banco, df_banco.copy()))

    if not itens:
        return

    st.markdown(f'#### {titulo}')
    abas_bancos = st.tabs([nome for nome, _ in itens])
    for aba_banco, (nome_banco, df_banco) in zip(abas_bancos, itens):
        with aba_banco:
            df_banco['VALOR'] = pd.to_numeric(df_banco['VALOR'], errors='coerce').fillna(0.0)
            entradas = float(df_banco.loc[df_banco['VALOR'] > 0, 'VALOR'].sum())
            saidas = float(abs(df_banco.loc[df_banco['VALOR'] < 0, 'VALOR'].sum()))
            saldo = entradas - saidas

            card_ent, card_sai, card_saldo = st.columns(3)
            card_ent.metric('Entradas', formatar_moeda(entradas))
            card_sai.metric('Saídas', formatar_moeda(saidas))
            card_saldo.metric('Saldo', formatar_moeda(saldo))

            colunas_previa = [
                coluna for coluna in ['DATA', 'HISTÓRICO', 'VALOR']
                if coluna in df_banco.columns
            ]
            df_previa = df_banco[colunas_previa].copy()
            if 'DATA' in df_previa.columns:
                df_previa['DATA'] = pd.to_datetime(
                    df_previa['DATA'], errors='coerce'
                ).dt.strftime('%d/%m/%Y')

            config_colunas = {}
            if 'DATA' in df_previa.columns:
                config_colunas['DATA'] = st.column_config.TextColumn('Data', width='small')
            if 'HISTÓRICO' in df_previa.columns:
                config_colunas['HISTÓRICO'] = st.column_config.TextColumn(
                    'Histórico', width='large'
                )
            if 'VALOR' in df_previa.columns:
                config_colunas['VALOR'] = st.column_config.NumberColumn(
                    'Valor', format='R$ %.2f'
                )

            st.dataframe(
                df_previa,
                use_container_width=True,
                hide_index=True,
                height=min(360, 38 + max(1, min(len(df_previa), 8)) * 35),
                column_config=config_colunas,
            )
'''

if 'def renderizar_previa_bancos_padrao(' not in text:
    anchor = '# Cache de processamento pesado da empresa 968 - Radani.'
    if anchor not in text:
        raise SystemExit('Âncora do helper não encontrada')
    text = text.replace(anchor, helper + '\n\n' + anchor, 1)

# Adiciona o padrão de prévia imediatamente antes da geração do Modelo Domínio,
# usando o dataframe já processado de cada empresa. Assim não há releitura de arquivos.
dicionarios = [
    'dados_exportacao_por_banco',
    'dados_autokraft',
    'dados_accede',
    'dados_up_pack',
]

for nome_dict in dicionarios:
    pattern = re.compile(
        rf'^(?P<indent>[ \t]*)(?P<lhs>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*gerar_excel_nova_geracao\(\n(?P<argindent>[ \t]*){re.escape(nome_dict)}\s*,',
        re.MULTILINE,
    )

    def repl(match, nome_dict=nome_dict):
        inicio = match.group(0)
        indent = match.group('indent')
        chamada = f"{indent}renderizar_previa_bancos_padrao({nome_dict})\n"
        trecho_anterior = text[max(0, match.start() - 180):match.start()]
        if f'renderizar_previa_bancos_padrao({nome_dict})' in trecho_anterior:
            return inicio
        return chamada + inicio

    text = pattern.sub(repl, text)

# A Radani já possui a prévia pronta em memória; troca o bloco específico pelo mesmo helper
# sem alterar o processamento bancário.
radani_ini = "                previa_bancos_radani = resultado_radani.get('previa_bancos', {})\n"
radani_fim = "                df_detalhes_radani = resultado_radani['detalhes']\n"
if radani_ini in text and radani_fim in text:
    a = text.index(radani_ini)
    b = text.index(radani_fim, a)
    bloco = (
        "                previa_bancos_radani = resultado_radani.get('previa_bancos', {})\n"
        "                renderizar_previa_bancos_padrao(\n"
        "                    previa_bancos_radani,\n"
        "                    ordem=['Itaú', 'Bradesco'],\n"
        "                )\n\n"
    )
    text = text[:a] + bloco + text[b:]

# Garante que as principais empresas multi-banco receberam a chamada do padrão.
obrigatorias = ['dados_accede', 'dados_up_pack']
for nome in obrigatorias:
    if f'renderizar_previa_bancos_padrao({nome})' not in text:
        raise SystemExit(f'Prévia padrão não inserida para {nome}')

if 'renderizar_previa_bancos_padrao(previa_bancos_radani' not in text.replace('\n', ''):
    # A chamada é multilinha; a checagem principal é a função e a variável no bloco.
    if "previa_bancos_radani = resultado_radani.get('previa_bancos', {})" not in text:
        raise SystemExit('Bloco de prévia da Radani não encontrado')

path.write_text(text, encoding='utf-8')
print('Padronização de prévias bancárias aplicada.')
