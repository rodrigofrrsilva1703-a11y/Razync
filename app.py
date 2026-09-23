"""Entrada principal do Razync.

Mantém a aplicação histórica intacta em app_legacy.py e acrescenta a integração
da empresa 841 (Lucrativite) com Banco Inter / conta 506.
"""

# Deploy sync 2026-09-15: auditoria mensal Sicredi v5 da empresa 626.
from pathlib import Path

import razync.company_catalog as _catalogo


# Ativa as empresas acrescentadas ao Organizador antes de carregar a aplicação histórica.
for _empresa in _catalogo.EMPRESAS:
    _chaves_novas = {
        "625": "valean_625", "626": "valean_626", "841": "lucrativite_841",
        "1208": "kairos_1208", "1530": "dias_pereira_1530",
    }
    _codigo_empresa = str(_empresa.get("codigo"))
    if _codigo_empresa in _chaves_novas:
        _empresa["chave_sistema"] = _chaves_novas[_codigo_empresa]

_catalogo.EMPRESAS_POR_REGIME = {
    regime: [empresa for empresa in _catalogo.EMPRESAS if empresa["regime"] == regime]
    for regime in _catalogo.REGIMES_ORDEM
}
_catalogo.EMPRESAS_POR_CHAVE = {
    empresa["chave"]: empresa for empresa in _catalogo.EMPRESAS
}


# Executa o app consolidado anterior sem alterar nenhuma de suas funcionalidades.
_app_legado = Path(__file__).with_name("app_legacy.py")
exec(
    compile(_app_legado.read_text(encoding="utf-8"), str(_app_legado), "exec"),
    globals(),
    globals(),
)


# Integra o Banco Inter ao mesmo motor de conferência usado pelas demais empresas.
_identificar_chave_banco_legado = identificar_chave_banco_empresa
_nome_banco_por_chave_legado = nome_banco_por_chave
_processar_extrato_conferencia_legado = processar_extrato_conferencia_empresa


def identificar_chave_banco_empresa(valor):
    texto = normalizar_texto(texto_celula_seguro(valor))
    if "caixa" in texto or "cef" in texto:
        return "caixa"
    if "inter" in texto:
        return "inter"
    if "safra" in texto:
        return "safra"
    return _identificar_chave_banco_legado(valor)


def nome_banco_por_chave(chave):
    if chave == "caixa":
        return "Caixa"
    if chave == "inter":
        return "Banco Inter"
    if chave == "safra":
        return "Safra"
    return _nome_banco_por_chave_legado(chave)


@st.cache_data(show_spinner=False, ttl=3600, max_entries=24)
def processar_extrato_conferencia_empresa(file_bytes, filename, banco_forcado=None):
    if st.session_state.get("empresa_organizador") == "kairos_1208":
        from razync.kairos_1208 import processar_extrato_1208

        banco_1208 = banco_forcado
        if banco_1208 not in {"itau", "safra", "bradesco"}:
            banco_1208 = identificar_chave_banco_empresa(filename)
        if banco_1208 in {"itau", "safra", "bradesco"}:
            return processar_extrato_1208(file_bytes, banco_1208).to_dict("records")
    if banco_forcado in {"itau_1208", "safra_1208", "bradesco_1208"}:
        from razync.kairos_1208 import processar_extrato_1208

        return processar_extrato_1208(
            file_bytes, banco_forcado.removesuffix("_1208")
        ).to_dict("records")
    if banco_forcado == "itau_1530":
        from razync.dias_pereira_1530 import (
            normalizar_modelo_itau_1530,
            processar_extrato_itau_xls_1530,
        )

        extensao = Path(str(filename or "")).suffix.lower()
        if extensao in {".xls", ".xlsx"}:
            return processar_extrato_itau_xls_1530(file_bytes).to_dict("records")
        registros = _processar_extrato_conferencia_legado(
            file_bytes, filename, "itau"
        )
        return normalizar_modelo_itau_1530(registros).to_dict("records")
    if banco_forcado in {"banco_brasil_625", "caixa_625", "sicredi_625"}:
        from razync.valean_625 import processar_extrato_625

        banco = banco_forcado.removesuffix("_625")
        return processar_extrato_625(file_bytes, banco).to_dict("records")
    if banco_forcado in {"inter", "inter_841"}:
        from razync.lucrativite_841 import processar_extrato_inter_conferencia_841

        return processar_extrato_inter_conferencia_841(
            file_bytes, filename
        ).to_dict("records")
    return _processar_extrato_conferencia_legado(
        file_bytes, filename, banco_forcado
    )


def _renderizar_lucrativite_841():
    from razync.lucrativite_841 import (
        COLUNAS_MODELO as COLUNAS_MODELO_841,
        processar_extrato_inter_841,
    )

    empresa_841 = "841 - LUCRATIVITE SERVICOS ESPECIALIZADOS DE APOIO ADMINISTRATIVO LTDA - ME"

    aba_operacoes, aba_base, aba_fiscal = st.tabs([
        "Organizar arquivos", "Base Inteligente", "Conferência Fiscal"
    ])

    with aba_fiscal:
        from razync.conferencia_fiscal import renderizar_conferencia_fiscal
        renderizar_conferencia_fiscal("lucrativite_841", empresa_841)

    with aba_operacoes:
        st.markdown("#### Banco Inter → Modelo Domínio")
        st.caption(
            "Envie o extrato Excel do Banco Inter. Entradas recebem débito 506 e saídas "
            "recebem crédito 506; a contrapartida fica disponível para classificação pela Base Inteligente."
        )
        arquivo_inter = st.file_uploader(
            "Extrato Banco Inter (.xlsx/.xls)",
            type=["xlsx", "xls"],
            key="lucrativite_841_extrato_inter",
        )

        if arquivo_inter is not None:
            assinatura = hashlib.sha256(arquivo_inter.getvalue()).hexdigest()
            if st.session_state.get("lucrativite_841_assinatura") != assinatura:
                try:
                    modelo_841 = executar_com_loading(
                        "Lendo o Banco Inter e montando os lançamentos...",
                        processar_extrato_inter_841,
                        arquivo_inter.getvalue(),
                    )
                    st.session_state["lucrativite_841_modelo"] = modelo_841
                    st.session_state["lucrativite_841_extrato"] = modelo_841.copy()
                    st.session_state["lucrativite_841_extrato_bytes"] = arquivo_inter.getvalue()
                    st.session_state["lucrativite_841_assinatura"] = assinatura
                    st.session_state.pop("lucrativite_841_erro", None)
                except Exception as erro:
                    st.session_state["lucrativite_841_erro"] = str(erro)
                    st.session_state.pop("lucrativite_841_modelo", None)

        erro_841 = st.session_state.get("lucrativite_841_erro")
        if erro_841:
            st.error(f"Não foi possível processar o extrato Banco Inter: {erro_841}")

        modelo_841 = st.session_state.get("lucrativite_841_modelo")
        if isinstance(modelo_841, pd.DataFrame) and not modelo_841.empty:
            entradas_841 = float(modelo_841.loc[modelo_841["VALOR"] > 0, "VALOR"].sum())
            saidas_841 = float(-modelo_841.loc[modelo_841["VALOR"] < 0, "VALOR"].sum())
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Lançamentos", len(modelo_841))
            m2.metric("Entradas", formatar_moeda(entradas_841))
            m3.metric("Saídas", formatar_moeda(saidas_841))
            m4.metric("Conta bancária", "506 · Inter")

            previa_841 = modelo_841.copy()
            previa_841["DATA"] = pd.to_datetime(previa_841["DATA"]).dt.strftime("%d/%m/%Y")
            st.dataframe(
                previa_841,
                use_container_width=True,
                hide_index=True,
                height=430,
                column_config={
                    "VALOR": st.column_config.NumberColumn("Valor", format="R$ %.2f")
                },
            )

            arquivo_modelo_841 = gerar_excel_modelo_dominio(
                modelo_841[COLUNAS_MODELO_841]
            )
            datas_841 = pd.to_datetime(modelo_841["DATA"])
            st.download_button(
                "Baixar Modelo Domínio · Banco Inter 506",
                data=arquivo_modelo_841,
                file_name=(
                    "LUCRATIVITE_841_INTER_506_MODELO_DOMINIO_"
                    f"{datas_841.min().strftime('%d%m%Y')}_A_"
                    f"{datas_841.max().strftime('%d%m%Y')}.xlsx"
                ),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="lucrativite_841_download_modelo",
            )

        renderizar_conferencia_autokraft(
            "lucrativite_841",
            bancos_config=[{
                "nome": "Banco Inter · Conta 506",
                "slug": "inter",
                "banco": "inter",
                "conta": "506",
            }],
        )

    with aba_base:
        renderizar_base_inteligente_empresa(
            "lucrativite_841",
            empresa_841,
            {"inter"},
            {"inter": "506"},
        )


if st.session_state.get("empresa_organizador") == "lucrativite_841":
    _renderizar_lucrativite_841()


def _renderizar_valean_625():
    from razync.valean_625 import CONTAS_VALEAN_625, processar_extrato_625

    empresa_625 = "625 - VALEAN SEGURANÇA E MEDICINA DO TRABALHO EIRELI ME"
    # O motor genérico de conferência identifica/destina os arquivos pela chave
    # bancária normal (banco_brasil/caixa/sicredi). O sufixo _625 é interno ao
    # parser e impedia BB/Sicredi de serem associados quando os 3 bancos eram
    # enviados juntos. O wrapper abaixo roteia as chaves normais ao parser 625.
    configs = [
        {"nome": "Banco do Brasil · Conta 8", "slug": "banco_brasil", "banco": "banco_brasil", "conta": "8"},
        {"nome": "Caixa · Conta 504", "slug": "caixa", "banco": "caixa", "conta": "504"},
        {"nome": "Sicredi · Conta 3999", "slug": "sicredi", "banco": "sicredi", "conta": "3999"},
    ]
    aba_operacoes, aba_base, aba_fiscal = st.tabs([
        "Organizar arquivos", "Base Inteligente", "Conferência Fiscal"
    ])

    with aba_fiscal:
        from razync.conferencia_fiscal import renderizar_conferencia_fiscal
        renderizar_conferencia_fiscal("valean_625", empresa_625)

    # A conferência genérica espera identificar o banco pelo conteúdo/estrutura da
    # planilha. O arquivo da 625 é gerado em abas por banco; por isso, lemos a aba
    # correspondente diretamente e devolvemos o quadro normalizado ao motor legado.
    _ler_planilha_conf_legado_625 = globals().get("ler_planilha_organizada_conferencia")

    def _ler_planilha_conferencia_625(file_bytes, banco_slug, conta_alvo=None):
        banco_original = banco_slug
        if isinstance(banco_slug, str) and banco_slug.endswith("_625"):
            banco_slug = banco_slug.removesuffix("_625")
        if banco_slug not in {"banco_brasil", "caixa", "sicredi"}:
            return _ler_planilha_conf_legado_625(file_bytes, banco_original, conta_alvo)
        nomes = {
            "banco_brasil": ["Banco do Brasil", "Banco do Brasil · Conta 8"],
            "caixa": ["Caixa", "Caixa · Conta 504"],
            "sicredi": ["Sicredi", "Sicredi · Conta 3999"],
        }
        xls = pd.ExcelFile(io.BytesIO(file_bytes))
        alvo = next((n for n in nomes[banco_slug] if n in xls.sheet_names), None)
        if alvo is None:
            # Compatibilidade com nomes de abas sanitizados/truncados.
            termo = {"banco_brasil": "brasil", "caixa": "caixa", "sicredi": "sicredi"}[banco_slug]
            alvo = next((n for n in xls.sheet_names if termo in normalizar_texto(n)), None)
        if alvo is None:
            return pd.DataFrame(), pd.DataFrame(), set()
        # O Modelo Domínio pode ter linhas de apresentação antes do cabeçalho.
        # Detecta DATA/VALOR nas primeiras 30 linhas em vez de assumir header=0.
        bruto = pd.read_excel(io.BytesIO(file_bytes), sheet_name=alvo, header=None)
        linha_cabecalho = None
        for idx in range(min(len(bruto), 30)):
            nomes_linha = {
                normalizar_texto(texto_celula_seguro(valor)).strip()
                for valor in bruto.iloc[idx].tolist()
                if texto_celula_seguro(valor)
            }
            if {"data", "valor"}.issubset(nomes_linha):
                linha_cabecalho = idx
                break
        if linha_cabecalho is None:
            return pd.DataFrame(), pd.DataFrame(), set()

        df = pd.read_excel(
            io.BytesIO(file_bytes), sheet_name=alvo, header=linha_cabecalho
        )
        df.columns = [str(c).strip().upper() for c in df.columns]
        if "DATA" not in df.columns or "VALOR" not in df.columns:
            return pd.DataFrame(), pd.DataFrame(), set()
        df["DATA"] = pd.to_datetime(df["DATA"], dayfirst=True, errors="coerce")
        df["VALOR"] = pd.to_numeric(df["VALOR"], errors="coerce")
        df = df.dropna(subset=["DATA", "VALOR"]).reset_index(drop=True)
        return df, pd.DataFrame(), {banco_slug}

    with aba_operacoes:
        st.markdown("#### Extratos bancários → Modelo Domínio")
        st.caption(
            "Envie os extratos dos bancos desejados. O download será um único Excel, "
            "com uma aba separada para cada banco enviado."
        )
        col_bb, col_caixa, col_sicredi = st.columns(3)
        with col_bb:
            arquivo_bb = st.file_uploader(
                "Banco do Brasil · conta 8", type=["pdf"], key="valean_625_bb"
            )
        with col_caixa:
            arquivo_caixa = st.file_uploader(
                "Caixa · conta 504", type=["pdf"], key="valean_625_caixa"
            )
        with col_sicredi:
            arquivo_sicredi = st.file_uploader(
                "Sicredi · conta 3999", type=["pdf"], key="valean_625_sicredi"
            )

        enviados = {
            "Banco do Brasil": ("banco_brasil", arquivo_bb),
            "Caixa": ("caixa", arquivo_caixa),
            "Sicredi": ("sicredi", arquivo_sicredi),
        }
        arquivos_presentes = {nome: item for nome, item in enviados.items() if item[1] is not None}
        if arquivos_presentes and st.button(
            "Processar extratos", type="primary", use_container_width=True,
            key="valean_625_processar"
        ):
            try:
                quadros = {}
                for nome, (banco, arquivo) in arquivos_presentes.items():
                    quadros[nome] = executar_com_loading(
                        f"Lendo {nome}...", processar_extrato_625,
                        arquivo.getvalue(), banco,
                    )
                st.session_state["valean_625_quadros"] = quadros
                st.session_state.pop("valean_625_erro", None)
            except Exception as erro:
                st.session_state["valean_625_erro"] = str(erro)
                st.session_state.pop("valean_625_quadros", None)

        if st.session_state.get("valean_625_erro"):
            st.error(f"Não foi possível montar o Modelo Domínio: {st.session_state['valean_625_erro']}")

        quadros = st.session_state.get("valean_625_quadros", {})
        if quadros:
            # Sanitização final da 625: também limpa resultados antigos que ainda
            # estejam no session_state, garantindo que CPF/CNPJ nunca cheguem à
            # prévia nem ao Excel mesmo sem reprocessar os PDFs.
            from razync.valean_625 import _limpar_cpf_cnpj_historico
            quadros_limpos = {}
            for nome_banco_625, quadro_625 in quadros.items():
                quadro_limpo_625 = quadro_625.copy()
                if "HISTÓRICO" in quadro_limpo_625.columns:
                    def _sanitizar_historico_625(valor):
                        texto = str(valor or "")
                        prefixo = ""
                        resto = texto
                        achado = re.match(r"^\s*((?:Pago|Recebido):)\s*(.*)$", texto, flags=re.I)
                        if achado:
                            prefixo = achado.group(1) + " "
                            resto = achado.group(2)
                        limpo = _limpar_cpf_cnpj_historico(resto)
                        return prefixo + (limpo or "MOVIMENTO BANCÁRIO")
                    quadro_limpo_625["HISTÓRICO"] = quadro_limpo_625["HISTÓRICO"].apply(
                        _sanitizar_historico_625
                    )
                quadros_limpos[nome_banco_625] = quadro_limpo_625
            quadros = quadros_limpos
            st.session_state["valean_625_quadros"] = quadros_limpos

            renderizar_previa_bancos_padrao(
                quadros, ordem=["Banco do Brasil", "Caixa", "Sicredi"]
            )
            dados_excel = {
                nome: {"principal": quadro, "retirados": pd.DataFrame()}
                for nome, quadro in quadros.items()
            }
            arquivo_saida = gerar_excel_nova_geracao(dados_excel)
            todas_datas = pd.concat(
                [pd.to_datetime(q["DATA"], errors="coerce") for q in quadros.values()]
            ).dropna()
            periodo_nome = (
                f"{todas_datas.min().strftime('%d%m%Y')}_A_{todas_datas.max().strftime('%d%m%Y')}"
                if not todas_datas.empty else "PERIODO"
            )
            st.download_button(
                "Baixar Modelo Domínio por banco",
                data=arquivo_saida,
                file_name=f"VALEAN_625_MODELO_DOMINIO_{periodo_nome}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="valean_625_download",
            )

        _ler_planilha_conf_original_625 = globals().get("ler_planilha_organizada_conferencia")
        _processar_extrato_conf_original_625 = globals().get("processar_extrato_conferencia_empresa")

        def _processar_extrato_conferencia_625(file_bytes, filename, banco_forcado=None):
            # Usa sempre o parser dedicado da 625 quando o banco puder ser
            # determinado. Isso é essencial quando os 3 PDFs são enviados juntos,
            # pois nesse caso o motor genérico chama com banco_forcado=None.
            banco_625 = banco_forcado if banco_forcado in {"banco_brasil", "caixa", "sicredi"} else None
            if banco_625 is None:
                nome_arquivo = normalizar_texto(texto_celula_seguro(filename))
                if "caixa" in nome_arquivo or "cef" in nome_arquivo:
                    banco_625 = "caixa"
                elif "sicredi" in nome_arquivo:
                    banco_625 = "sicredi"
                elif "banco do brasil" in nome_arquivo or re.search(r"(^|[^a-z])bb([^a-z]|$)", nome_arquivo):
                    banco_625 = "banco_brasil"
            if banco_625:
                return processar_extrato_625(file_bytes, banco_625).to_dict("records")
            return _processar_extrato_conf_original_625(file_bytes, filename, banco_forcado)

        try:
            globals()["ler_planilha_organizada_conferencia"] = _ler_planilha_conferencia_625
            globals()["processar_extrato_conferencia_empresa"] = _processar_extrato_conferencia_625
            renderizar_conferencia_autokraft(
                "valean_625", bancos_config=configs,
                rotulo_planilha="Planilha final organizada da empresa 625",
            )
        finally:
            globals()["ler_planilha_organizada_conferencia"] = _ler_planilha_conf_original_625
            globals()["processar_extrato_conferencia_empresa"] = _processar_extrato_conf_original_625

    with aba_base:
        renderizar_base_inteligente_empresa(
            "valean_625", empresa_625,
            {"banco_brasil", "caixa", "sicredi"}, CONTAS_VALEAN_625,
        )


if st.session_state.get("empresa_organizador") == "valean_625":
    _renderizar_valean_625()



def _renderizar_valean_626():
    from razync.valean_626 import (
        CONTAS_VALEAN_626,
        PROCESSADOR_VALEAN_626_VERSAO,
        processar_extrato_626,
        processar_multiplos_626,
    )

    empresa_626 = "626 - VALEAN ASSESSORIA EM SEGURANÇA DO TRABALHO LTDA - EPP"
    configs_626 = [
        {"nome": "Banco do Brasil · Conta 8", "slug": "banco_brasil", "banco": "banco_brasil", "conta": "8"},
        {"nome": "Sicredi · Conta 1155", "slug": "sicredi", "banco": "sicredi", "conta": "1155"},
    ]

    # Resultados processados ficam na sessão do Streamlit. Ao mudar qualquer
    # regra de leitura/conciliação da 626, invalida automaticamente a planilha
    # antiga para impedir que o usuário baixe dados gerados pela versão anterior.
    if st.session_state.get("valean_626_processador_versao") != PROCESSADOR_VALEAN_626_VERSAO:
        st.session_state.pop("valean_626_quadros", None)
        st.session_state.pop("valean_626_erro", None)
        st.session_state["valean_626_processador_versao"] = PROCESSADOR_VALEAN_626_VERSAO

    aba_operacoes_626, aba_base_626, aba_fiscal_626 = st.tabs([
        "Organizar arquivos", "Base Inteligente", "Conferência Fiscal"
    ])

    with aba_fiscal_626:
        from razync.conferencia_fiscal import renderizar_conferencia_fiscal
        renderizar_conferencia_fiscal("valean_626", empresa_626)

    with aba_operacoes_626:
        st.markdown("#### Extratos bancários → Modelo Domínio")
        st.caption(f"Versão do processador 626: {PROCESSADOR_VALEAN_626_VERSAO}")
        st.caption(
            "Envie vários PDFs de cada banco. Os períodos serão consolidados em ordem "
            "e o download terá uma aba para Banco do Brasil e outra para Sicredi."
        )
        col_bb_626, col_sicredi_626 = st.columns(2)
        with col_bb_626:
            arquivos_bb_626 = st.file_uploader(
                "Banco do Brasil · conta 8 · vários períodos",
                type=["pdf"], accept_multiple_files=True,
                key="valean_626_bb_multiplos",
            )
        with col_sicredi_626:
            arquivos_sicredi_626 = st.file_uploader(
                "Sicredi · conta 1155 · vários períodos",
                type=["pdf"], accept_multiple_files=True,
                key="valean_626_sicredi_multiplos",
            )

        tem_arquivos_626 = bool(arquivos_bb_626 or arquivos_sicredi_626)
        if tem_arquivos_626 and st.button(
            "Processar períodos", type="primary", use_container_width=True,
            key="valean_626_processar",
        ):
            try:
                quadros_626 = {}
                if arquivos_bb_626:
                    quadros_626["Banco do Brasil"] = executar_com_loading(
                        "Lendo e consolidando os extratos do Banco do Brasil...",
                        processar_multiplos_626,
                        [arquivo.getvalue() for arquivo in arquivos_bb_626],
                        "banco_brasil",
                    )
                if arquivos_sicredi_626:
                    quadros_626["Sicredi"] = executar_com_loading(
                        "Lendo e consolidando os extratos do Sicredi...",
                        processar_multiplos_626,
                        [arquivo.getvalue() for arquivo in arquivos_sicredi_626],
                        "sicredi",
                    )
                st.session_state["valean_626_quadros"] = quadros_626
                st.session_state.pop("valean_626_erro", None)
            except Exception as erro:
                st.session_state["valean_626_erro"] = str(erro)
                st.session_state.pop("valean_626_quadros", None)

        if st.session_state.get("valean_626_erro"):
            st.error(f"Não foi possível processar os extratos da 626: {st.session_state['valean_626_erro']}")

        quadros_626 = st.session_state.get("valean_626_quadros", {})
        if quadros_626:
            # Na empresa 626, o card Saldo deve ser estritamente a diferença
            # entre os mesmos lançamentos mostrados nos cards de entradas e
            # saídas. Remove saldos bancários apenas das cópias de apresentação.
            quadros_previa_626 = {}
            for nome_banco_626, quadro_626 in quadros_626.items():
                quadro_previa_626 = quadro_626.copy()
                quadro_previa_626.attrs.update(quadro_626.attrs)
                quadro_previa_626.attrs.pop("saldo_inicial_extrato", None)
                quadro_previa_626.attrs.pop("saldo_extrato", None)
                quadros_previa_626[nome_banco_626] = quadro_previa_626
            st.markdown("#### Pré-visualização por banco")
            nomes_previa_626 = [
                nome for nome in ["Banco do Brasil", "Sicredi"]
                if nome in quadros_previa_626
            ]
            abas_previa_626 = st.tabs(nomes_previa_626)
            for aba_626, nome_banco_626 in zip(abas_previa_626, nomes_previa_626):
                with aba_626:
                    df_previa_626 = quadros_previa_626[nome_banco_626]
                    valores_626 = pd.to_numeric(
                        df_previa_626["VALOR"], errors="coerce"
                    ).fillna(0.0)
                    entradas_626 = float(valores_626[valores_626 > 0].sum())
                    saidas_626 = float(abs(valores_626[valores_626 < 0].sum()))
                    saldo_626 = entradas_626 - saidas_626
                    col_ent_626, col_sai_626, col_saldo_626 = st.columns(3)
                    col_ent_626.metric("Entradas", formatar_moeda(entradas_626))
                    col_sai_626.metric("Saídas", formatar_moeda(saidas_626))
                    col_saldo_626.metric("Saldo", formatar_moeda(saldo_626))
                    tabela_626 = df_previa_626[["DATA", "HISTÓRICO", "VALOR"]].copy()
                    tabela_626["DATA"] = pd.to_datetime(
                        tabela_626["DATA"], errors="coerce"
                    ).dt.strftime("%d/%m/%Y")
                    st.dataframe(
                        tabela_626, use_container_width=True, hide_index=True,
                        height=min(360, 38 + max(1, min(len(tabela_626), 8)) * 35),
                    )
            quantidades_626 = [
                f"{nome}: {quadro.attrs.get('arquivos_processados', 1)} arquivo(s)"
                for nome, quadro in quadros_626.items()
            ]
            st.caption("Processados: " + " · ".join(quantidades_626))
            for nome_banco_626, quadro_626 in quadros_626.items():
                if quadro_626.attrs.get("avisos_saldo_impresso"):
                    st.info(
                        f"{nome_banco_626}: os saldos corridos do PDF tiveram "
                        "divergência de OCR. Entradas, saídas e saldo abaixo "
                        "foram calculados somente pelos lançamentos."
                    )
            dados_excel_626 = {
                nome: {"principal": quadro, "retirados": pd.DataFrame()}
                for nome, quadro in quadros_626.items()
            }
            arquivo_saida_626 = gerar_excel_nova_geracao(dados_excel_626)
            datas_626 = pd.concat([
                pd.to_datetime(quadro["DATA"], errors="coerce")
                for quadro in quadros_626.values()
            ]).dropna()
            periodo_626 = (
                f"{datas_626.min().strftime('%d%m%Y')}_A_{datas_626.max().strftime('%d%m%Y')}"
                if not datas_626.empty else "PERIODO"
            )
            st.download_button(
                "Baixar Modelo Domínio · períodos consolidados",
                data=arquivo_saida_626,
                file_name=f"VALEAN_626_MODELO_DOMINIO_{periodo_626}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="valean_626_download",
            )

        _proc_conf_original_626 = globals().get("processar_extrato_conferencia_empresa")

        def _processar_extrato_conferencia_626(file_bytes, filename, banco_forcado=None):
            banco_626 = banco_forcado if banco_forcado in {"banco_brasil", "sicredi"} else None
            if banco_626 is None:
                nome = normalizar_texto(texto_celula_seguro(filename))
                if "sicredi" in nome:
                    banco_626 = "sicredi"
                elif "banco do brasil" in nome or re.search(r"(^|[^a-z])bb([^a-z]|$)", nome):
                    banco_626 = "banco_brasil"
            if banco_626:
                return processar_extrato_626(file_bytes, banco_626).to_dict("records")
            return _proc_conf_original_626(file_bytes, filename, banco_forcado)

        try:
            globals()["processar_extrato_conferencia_empresa"] = _processar_extrato_conferencia_626
            renderizar_conferencia_autokraft(
                "valean_626",
                bancos_config=configs_626,
                rotulo_planilha="Planilha final organizada da empresa 626",
            )
        finally:
            globals()["processar_extrato_conferencia_empresa"] = _proc_conf_original_626

    with aba_base_626:
        renderizar_base_inteligente_empresa(
            "valean_626", empresa_626,
            {"banco_brasil", "sicredi"}, CONTAS_VALEAN_626,
        )


if st.session_state.get("empresa_organizador") == "valean_626":
    _renderizar_valean_626()


def _renderizar_dias_pereira_1530():
    from razync.dias_pereira_1530 import (
        COLUNAS_MODELO,
        CONTA_ITAU_1530,
        normalizar_modelo_itau_1530,
        processar_extrato_itau_xls_1530,
    )

    empresa = "1530 - DIAS PEREIRA SOCIEDADE INDIVIDUAL DE ADVOCACIA"
    aba_operacoes, aba_base, aba_fiscal = st.tabs([
        "Organizar arquivos", "Base Inteligente", "Conferência Fiscal"
    ])

    with aba_fiscal:
        from razync.conferencia_fiscal import renderizar_conferencia_fiscal
        renderizar_conferencia_fiscal("dias_pereira_1530", empresa)

    with aba_operacoes:
        st.markdown("#### Extrato Itaú → Modelo Domínio")
        st.caption(
            "Envie extratos Itaú em XLS, XLSX ou PDF. Entradas recebem débito 508 "
            "e saídas recebem crédito 508. Linhas de saldo não são importadas."
        )
        arquivos = st.file_uploader(
            "Extrato(s) Itaú · conta Domínio 508",
            type=["xls", "xlsx", "pdf"], accept_multiple_files=True,
            key="dias_pereira_1530_extratos_itau",
        )
        if arquivos:
            try:
                quadros = []
                assinaturas = set()
                for arquivo in arquivos:
                    conteudo = arquivo.getvalue()
                    assinatura = hashlib.sha256(conteudo).hexdigest()
                    if assinatura in assinaturas:
                        continue
                    assinaturas.add(assinatura)
                    extensao = Path(arquivo.name).suffix.lower()
                    if extensao in {".xls", ".xlsx"}:
                        quadro = processar_extrato_itau_xls_1530(conteudo)
                    else:
                        registros = _processar_extrato_conferencia_legado(
                            conteudo, arquivo.name, "itau"
                        )
                        quadro = normalizar_modelo_itau_1530(registros)
                    quadros.append(quadro)
                if not quadros:
                    raise ValueError("Nenhum extrato válido foi processado.")
                modelo = pd.concat(quadros, ignore_index=True).sort_values(
                    "DATA", kind="stable"
                ).reset_index(drop=True)
                st.session_state["dias_pereira_1530_modelo"] = modelo
                st.session_state.pop("dias_pereira_1530_erro", None)
            except Exception as erro:
                st.session_state["dias_pereira_1530_erro"] = str(erro)
                st.session_state.pop("dias_pereira_1530_modelo", None)

        if st.session_state.get("dias_pereira_1530_erro"):
            st.error(
                "Não foi possível processar o extrato Itaú da empresa 1530: "
                + st.session_state["dias_pereira_1530_erro"]
            )

        modelo = st.session_state.get("dias_pereira_1530_modelo")
        if isinstance(modelo, pd.DataFrame) and not modelo.empty:
            entradas = float(modelo.loc[modelo["VALOR"] > 0, "VALOR"].sum())
            saidas = float(-modelo.loc[modelo["VALOR"] < 0, "VALOR"].sum())
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Lançamentos", len(modelo))
            m2.metric("Entradas", formatar_moeda(entradas))
            m3.metric("Saídas", formatar_moeda(saidas))
            m4.metric("Conta bancária", f"{CONTA_ITAU_1530} · Itaú")

            previa = modelo.copy()
            previa["DATA"] = pd.to_datetime(previa["DATA"]).dt.strftime("%d/%m/%Y")
            st.dataframe(previa, use_container_width=True, hide_index=True, height=430)
            datas = pd.to_datetime(modelo["DATA"])
            st.download_button(
                "Baixar Modelo Domínio · Itaú 508",
                data=gerar_excel_modelo_dominio(
                    modelo[COLUNAS_MODELO], formato_data="dd/mm/yyyy"
                ),
                file_name=(
                    "DIAS_PEREIRA_1530_ITAU_508_MODELO_DOMINIO_"
                    f"{datas.min().strftime('%d%m%Y')}_A_{datas.max().strftime('%d%m%Y')}.xlsx"
                ),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="dias_pereira_1530_download",
            )

        renderizar_conferencia_autokraft(
            "dias_pereira_1530",
            bancos_config=[{
                "nome": "Itaú · Conta 508", "slug": "itau_1530",
                "banco": "itau_1530", "conta": "508",
            }],
            rotulo_planilha="Modelo Domínio final da empresa 1530",
        )

    with aba_base:
        renderizar_base_inteligente_empresa(
            "dias_pereira_1530", empresa, {"itau"}, {"itau": "508"}
        )


if st.session_state.get("empresa_organizador") == "dias_pereira_1530":
    _renderizar_dias_pereira_1530()


def _renderizar_kairos_1208():
    from razync.kairos_1208 import (
        COLUNAS_MODELO, CONTAS, detalhar_com_contas_pagas, ler_contas_pagas,
        processar_extrato_1208,
    )

    empresa = "1208 - KAIROS DESMONTE INDUSTRIAIS EIRELI - ME"
    aba_operacoes, aba_base, aba_fiscal = st.tabs([
        "Organizar arquivos", "Base Inteligente", "Conferência Fiscal"
    ])

    with aba_fiscal:
        from razync.conferencia_fiscal import renderizar_conferencia_fiscal
        renderizar_conferencia_fiscal("kairos_1208", empresa)

    with aba_operacoes:
        st.markdown("#### Extratos bancários → Modelo Domínio")
        st.caption(
            "Envie os extratos de janeiro a agosto de 2026. Os valores vêm dos PDFs. "
            "A planilha de contas pagas somente detalha débitos quando data e total fecham exatamente."
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            itau = st.file_uploader("Itaú · conta 508", type=["pdf"], accept_multiple_files=True, key="kairos_1208_itau")
        with col2:
            safra = st.file_uploader("Safra · conta 512", type=["pdf"], accept_multiple_files=True, key="kairos_1208_safra")
        with col3:
            bradesco = st.file_uploader("Bradesco · conta 9", type=["pdf"], accept_multiple_files=True, key="kairos_1208_bradesco")
        contas_pagas = st.file_uploader(
            "Planilha de contas pagas (opcional, usada apenas para detalhamento)",
            type=["xlsx", "xls"], key="kairos_1208_contas_pagas",
        )

        if st.button("Processar extratos da empresa 1208", type="primary", use_container_width=True, key="kairos_1208_processar"):
            try:
                modelos = {}
                for banco, arquivos in (("itau", itau), ("safra", safra), ("bradesco", bradesco)):
                    quadros, vistos = [], set()
                    for arquivo in arquivos or []:
                        conteudo = arquivo.getvalue()
                        assinatura = hashlib.sha256(conteudo).hexdigest()
                        if assinatura in vistos:
                            continue
                        vistos.add(assinatura)
                        quadros.append(processar_extrato_1208(conteudo, banco))
                    if quadros:
                        modelos[banco] = pd.concat(quadros, ignore_index=True).sort_values("DATA", kind="stable").reset_index(drop=True)
                if not modelos:
                    raise ValueError("Envie pelo menos um extrato bancário em PDF.")
                aplicados = []
                if contas_pagas is not None:
                    detalhes = ler_contas_pagas(contas_pagas.getvalue())
                    modelos, aplicados = detalhar_com_contas_pagas(modelos, detalhes)
                st.session_state["kairos_1208_modelos"] = modelos
                st.session_state["kairos_1208_detalhes_aplicados"] = aplicados
                st.session_state.pop("kairos_1208_erro", None)
            except Exception as erro:
                st.session_state["kairos_1208_erro"] = str(erro)
                st.session_state.pop("kairos_1208_modelos", None)

        if st.session_state.get("kairos_1208_erro"):
            st.error("Não foi possível processar os arquivos da empresa 1208: " + st.session_state["kairos_1208_erro"])

        modelos = st.session_state.get("kairos_1208_modelos")
        if isinstance(modelos, dict) and modelos:
            for banco, modelo in modelos.items():
                nome = {"itau": "Itaú", "safra": "Safra", "bradesco": "Bradesco"}[banco]
                entradas = float(modelo.loc[modelo["VALOR"] > 0, "VALOR"].sum())
                saidas = float(-modelo.loc[modelo["VALOR"] < 0, "VALOR"].sum())
                st.markdown(f"##### {nome} · conta {CONTAS[banco]}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Lançamentos", len(modelo))
                m2.metric("Entradas", formatar_moeda(entradas))
                m3.metric("Saídas", formatar_moeda(saidas))
                m4.metric("Saldo (entradas - saídas)", formatar_moeda(entradas - saidas))
                previa = modelo.copy()
                previa["DATA"] = pd.to_datetime(previa["DATA"]).dt.strftime("%d/%m/%Y")
                st.dataframe(previa, use_container_width=True, hide_index=True, height=280)
            aplicados = st.session_state.get("kairos_1208_detalhes_aplicados", [])
            if aplicados:
                st.success(f"{len(aplicados)} lançamento(s) foram detalhados pela planilha de contas pagas sem alterar os totais bancários.")
            dados_excel = {
                f"{ {'itau':'Itaú','safra':'Safra','bradesco':'Bradesco'}[b] } {CONTAS[b]}": {"principal": df[COLUNAS_MODELO], "retirados": pd.DataFrame()}
                for b, df in modelos.items()
            }
            st.download_button(
                "Baixar Modelo Domínio · empresa 1208",
                data=gerar_excel_nova_geracao(dados_excel, prefixar_historicos=False),
                file_name="KAIROS_1208_MODELO_DOMINIO_01_A_08_2026.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True, key="kairos_1208_download",
            )

        renderizar_conferencia_autokraft(
            "kairos_1208",
            bancos_config=[
                {"nome": "Itaú · Conta 508", "slug": "itau_1208", "banco": "itau", "conta": "508"},
                {"nome": "Safra · Conta 512", "slug": "safra_1208", "banco": "safra", "conta": "512"},
                {"nome": "Bradesco · Conta 9", "slug": "bradesco_1208", "banco": "bradesco", "conta": "9"},
            ],
            rotulo_planilha="Modelo Domínio final da empresa 1208",
        )

    with aba_base:
        renderizar_base_inteligente_empresa(
            "kairos_1208", empresa, {"itau", "safra", "bradesco"}, CONTAS
        )


if st.session_state.get("empresa_organizador") == "kairos_1208":
    _renderizar_kairos_1208()


def _renderizar_conferencia_fiscal_autokraft():
    from razync.conferencia_fiscal import gerar_relatorio_excel, processar_conferencia

    st.markdown("---")
    st.markdown("### Conferência Fiscal × Contábil")
    st.caption(
        "Envie o Resumo por Acumulador e o Razão do mesmo período. Somente acumuladores "
        "com conta preenchida são conferidos. Pagamentos, recebimentos e outros movimentos "
        "não fiscais são separados como alertas, sem distorcer a conferência principal."
    )
    col_fiscal, col_razao = st.columns(2)
    with col_fiscal:
        arquivo_acumuladores = st.file_uploader(
            "Relatório de acumuladores do Domínio", type=["xls", "xlsx"],
            key="autokraft_3_acumuladores_fiscais",
        )
    with col_razao:
        arquivo_razao = st.file_uploader(
            "Razão com todas as contas", type=["xls", "xlsx"],
            key="autokraft_3_razao_fiscal",
        )
    if arquivo_acumuladores is None or arquivo_razao is None:
        st.info("Envie os dois relatórios. A conferência começará automaticamente.")
        return

    assinatura_fiscal = hashlib.sha256(
        arquivo_acumuladores.getvalue() + arquivo_razao.getvalue()
    ).hexdigest()
    if st.session_state.get("autokraft_3_assinatura_fiscal") != assinatura_fiscal:
        try:
            resultado = executar_com_loading(
                "Cruzando acumuladores, contas e lançamentos do razão...",
                processar_conferencia,
                arquivo_acumuladores.getvalue(), arquivo_acumuladores.name,
                arquivo_razao.getvalue(), arquivo_razao.name,
            )
            st.session_state["autokraft_3_resultado_fiscal"] = resultado
            st.session_state["autokraft_3_assinatura_fiscal"] = assinatura_fiscal
            st.session_state.pop("autokraft_3_erro_fiscal", None)
        except Exception as erro:
            st.session_state["autokraft_3_erro_fiscal"] = str(erro)
            st.session_state.pop("autokraft_3_resultado_fiscal", None)

    if st.session_state.get("autokraft_3_erro_fiscal"):
        st.error("Não foi possível concluir a conferência: " + st.session_state["autokraft_3_erro_fiscal"])

    resultado = st.session_state.get("autokraft_3_resultado_fiscal")
    if not isinstance(resultado, dict):
        return
    resumo = resultado.get("resumo", pd.DataFrame())
    detalhes = resultado.get("detalhes", pd.DataFrame())
    if resumo.empty:
        st.warning("Nenhuma conta pôde ser comparada.")
        return
    conferidas = int(resumo["SITUAÇÃO"].astype(str).str.startswith("CONFERE").sum())
    alertas = int(resumo["LANÇAMENTOS EXTRAS"].sum())
    revisar = int((resumo["SITUAÇÃO"] == "REVISAR").sum())
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Contas analisadas", len(resumo))
    m2.metric("Fiscal conferido", conferidas)
    m3.metric("Lançamentos em alerta", alertas)
    m4.metric("Contas para revisar", revisar)
    periodo = resultado.get("periodo_fiscal", {})
    inicio = pd.to_datetime(periodo.get("inicio"), errors="coerce")
    fim = pd.to_datetime(periodo.get("fim"), errors="coerce")
    periodo_nome = (
        f"{inicio.strftime('%m%Y')}" if pd.notna(inicio)
        else "PERIODO_ANALISADO"
    )
    st.download_button(
        "Baixar relatório completo da conferência",
        data=gerar_relatorio_excel(resultado),
        file_name=f"AUTOKRAFT_3_CONFERENCIA_FISCAL_{periodo_nome}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="autokraft_3_download_conferencia_fiscal",
    )
    if revisar:
        st.error(f"{revisar} conta(s) possuem diferença fiscal e precisam de revisão.")
    elif alertas:
        st.warning(
            "Os valores fiscais conferem, mas existem lançamentos contábeis adicionais "
            "que devem ser revisados."
        )
    else:
        st.success("Todas as contas conferem e não foram encontrados lançamentos adicionais.")

    aba_visao, aba_alertas, aba_todos = st.tabs([
        "Visão geral", f"Alertas ({alertas})", "Todos os lançamentos"
    ])

    with aba_visao:
        st.markdown("#### Conferência por conta")
        ordem = {"REVISAR": 0, "AUSENTE NO CONTÁBIL": 1, "CONFERE COM ALERTAS": 2, "CONFERE": 3}
        resumo_ordenado = resumo.assign(
            _ORDEM=resumo["SITUAÇÃO"].map(ordem).fillna(9)
        ).sort_values(["_ORDEM", "CONTA"])
        for _, conta_resultado in resumo_ordenado.iterrows():
            conta = str(conta_resultado["CONTA"])
            situacao = str(conta_resultado["SITUAÇÃO"])
            extras_conta = int(conta_resultado["LANÇAMENTOS EXTRAS"])
            titulo = f"Conta {conta} · {situacao}"
            if extras_conta:
                titulo += f" · {extras_conta} alerta(s)"
            with st.expander(
                titulo,
                expanded=situacao != "CONFERE",
            ):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Valor fiscal", formatar_moeda(conta_resultado["VALOR FISCAL"]))
                c2.metric("Contábil compatível", formatar_moeda(conta_resultado["CONTÁBIL COMPATÍVEL"]))
                c3.metric("Diferença fiscal", formatar_moeda(conta_resultado["DIFERENÇA FISCAL"]))
                c4.metric("Total movimentado", formatar_moeda(conta_resultado["TOTAL DA CONTA"]))
                st.caption(
                    f"Acumulador(es): {conta_resultado['ACUMULADORES']} · "
                    f"Natureza analisada: {conta_resultado['TIPO'].title()}"
                )
                movimentos_conta = detalhes[detalhes["CONTA"].astype(str).eq(conta)].copy()
                if not movimentos_conta.empty:
                    movimentos_conta["DATA"] = pd.to_datetime(
                        movimentos_conta["DATA"]
                    ).dt.strftime("%d/%m/%Y")
                    st.dataframe(
                        movimentos_conta[[
                            "DATA", "HISTÓRICO", "CONTRAPARTIDA", "VALOR", "CLASSIFICAÇÃO"
                        ]],
                        use_container_width=True, hide_index=True,
                        column_config={
                            "VALOR": st.column_config.NumberColumn(format="R$ %.2f"),
                            "HISTÓRICO": st.column_config.TextColumn(width="large"),
                            "CLASSIFICAÇÃO": st.column_config.TextColumn(width="medium"),
                        },
                    )

    with aba_alertas:
        alertas_df = detalhes[
            detalhes["CLASSIFICAÇÃO"].eq("ALERTA - NÃO FISCAL")
        ].copy()
        if alertas_df.empty:
            st.success("Nenhum lançamento adicional foi encontrado nas contas conferidas.")
        else:
            st.caption(
                "Estes lançamentos não foram usados para fechar o valor fiscal. "
                "Revise a conta contábil e a contrapartida antes de corrigir."
            )
            alertas_df["DATA"] = pd.to_datetime(alertas_df["DATA"]).dt.strftime("%d/%m/%Y")
            st.dataframe(
                alertas_df[["CONTA", "DATA", "HISTÓRICO", "CONTRAPARTIDA", "VALOR"]],
                use_container_width=True, hide_index=True,
                column_config={
                    "VALOR": st.column_config.NumberColumn(format="R$ %.2f"),
                    "HISTÓRICO": st.column_config.TextColumn(width="large"),
                },
            )

    with aba_todos:
        exibicao = detalhes.copy()
        if not exibicao.empty:
            exibicao["DATA"] = pd.to_datetime(exibicao["DATA"]).dt.strftime("%d/%m/%Y")
            st.dataframe(
                exibicao, use_container_width=True, hide_index=True,
                column_config={
                    "VALOR": st.column_config.NumberColumn(format="R$ %.2f"),
                    "HISTÓRICO": st.column_config.TextColumn(width="large"),
                },
            )


# A conferência da Autokraft agora é renderizada dentro da aba padrão, como nas
# demais empresas. A função legada acima permanece apenas para compatibilidade.


# Empresas que já exibem a conferência ao lado da Base Inteligente. Para qualquer
# empresa cadastrada que ainda não tenha ferramentas bancárias próprias, a aba
# fiscal continua disponível, garantindo cobertura obrigatória em todo o cadastro.
_EMPRESAS_COM_ABA_FISCAL = {
    "hw_88", "engekraft_969", "gz_1211", "eletro_forte_filial", "eletro_forte",
    "lcarlos", "vgv_1402", "autokraft_industrial", "autokraft_projetos", "isa",
    "accede_automacao", "accede_equipamentos", "radani", "up_pack", "nova_geracao",
    "dias_pereira", "lucrativite_841", "valean_625", "valean_626",
    "dias_pereira_1530", "kairos_1208", "maria_narbutis_1532",
}
_empresa_selecionada_fiscal = st.session_state.get("empresa_organizador")
if (
    _empresa_selecionada_fiscal
    and _empresa_selecionada_fiscal not in _EMPRESAS_COM_ABA_FISCAL
):
    _cadastro_fiscal = next(
        (
            item for item in _catalogo.EMPRESAS
            if item.get("chave_sistema", item.get("chave")) == _empresa_selecionada_fiscal
        ),
        None,
    )
    _nome_empresa_fiscal = (
        f"{_cadastro_fiscal.get('codigo')} - {_cadastro_fiscal.get('nome')}"
        if _cadastro_fiscal else str(_empresa_selecionada_fiscal)
    )
    _aba_fiscal_obrigatoria = st.tabs(["Conferência Fiscal"])[0]
    with _aba_fiscal_obrigatoria:
        from razync.conferencia_fiscal import renderizar_conferencia_fiscal
        renderizar_conferencia_fiscal(_empresa_selecionada_fiscal, _nome_empresa_fiscal)
