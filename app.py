"""Entrada principal do Razync.

Mantém a aplicação histórica intacta em app_legacy.py e acrescenta a integração
da empresa 841 (Lucrativite) com Banco Inter / conta 506.
"""

# Deploy sync 2026-09-09: históricos Nova Geração 266/1396 preservam PAGO/RECEBIDO original sem prefixo extra.
from pathlib import Path

import razync.company_catalog as _catalogo


# Ativa as empresas acrescentadas ao Organizador antes de carregar a aplicação histórica.
for _empresa in _catalogo.EMPRESAS:
    _chaves_novas = {"625": "valean_625", "841": "lucrativite_841"}
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
    return _identificar_chave_banco_legado(valor)


def nome_banco_por_chave(chave):
    if chave == "caixa":
        return "Caixa"
    if chave == "inter":
        return "Banco Inter"
    return _nome_banco_por_chave_legado(chave)


@st.cache_data(show_spinner=False, ttl=3600, max_entries=24)
def processar_extrato_conferencia_empresa(file_bytes, filename, banco_forcado=None):
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

    aba_operacoes, aba_base = st.tabs(["Organizar arquivos", "Base Inteligente"])

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
    configs = [
        {"nome": "Banco do Brasil · Conta 8", "slug": "banco_brasil", "banco": "banco_brasil_625", "conta": "8"},
        {"nome": "Caixa · Conta 508", "slug": "caixa", "banco": "caixa_625", "conta": "508"},
        {"nome": "Sicredi · Conta 3999", "slug": "sicredi", "banco": "sicredi_625", "conta": "3999"},
    ]
    aba_operacoes, aba_base = st.tabs(["Organizar arquivos", "Base Inteligente"])

    # A conferência genérica espera identificar o banco pelo conteúdo/estrutura da
    # planilha. O arquivo da 625 é gerado em abas por banco; por isso, lemos a aba
    # correspondente diretamente e devolvemos o quadro normalizado ao motor legado.
    _ler_planilha_conf_legado_625 = globals().get("ler_planilha_organizada_conferencia")

    def _ler_planilha_conferencia_625(file_bytes, banco_slug):
        if banco_slug not in {"banco_brasil", "caixa", "sicredi"}:
            return _ler_planilha_conf_legado_625(file_bytes, banco_slug)
        nomes = {
            "banco_brasil": ["Banco do Brasil", "Banco do Brasil · Conta 8"],
            "caixa": ["Caixa", "Caixa · Conta 508"],
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
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=alvo)
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
                "Caixa · conta 508", type=["pdf"], key="valean_625_caixa"
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
        try:
            globals()["ler_planilha_organizada_conferencia"] = _ler_planilha_conferencia_625
            renderizar_conferencia_autokraft(
                "valean_625", bancos_config=configs,
                rotulo_planilha="Planilha final organizada da empresa 625",
            )
        finally:
            globals()["ler_planilha_organizada_conferencia"] = _ler_planilha_conf_original_625

    with aba_base:
        renderizar_base_inteligente_empresa(
            "valean_625", empresa_625,
            {"banco_brasil", "caixa", "sicredi"}, CONTAS_VALEAN_625,
        )


if st.session_state.get("empresa_organizador") == "valean_625":
    _renderizar_valean_625()
