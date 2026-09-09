"""Entrada principal do Razync.

Mantém a aplicação histórica intacta em app_legacy.py e acrescenta a integração
da empresa 841 (Lucrativite) com Banco Inter / conta 506.
"""

from pathlib import Path

import razync.company_catalog as _catalogo


# Ativa a empresa 841 no Organizador antes de carregar a aplicação histórica.
for _empresa in _catalogo.EMPRESAS:
    if str(_empresa.get("codigo")) == "841":
        _empresa["chave_sistema"] = "lucrativite_841"
        break

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


def _renderizar_lucrativite_841():
    from razync.lucrativite_841 import (
        COLUNAS_MODELO as COLUNAS_MODELO_841,
        conferir_extrato_modelo,
        ler_modelo_para_conferencia,
        processar_extrato_inter_841,
        processar_extrato_inter_conferencia_841,
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

        st.markdown("---")
        st.markdown("#### Conferência com Extrato")
        st.caption(
            "Banco Inter · conta 506. O extrato pode ser Excel ou o PDF detalhado emitido pelo Banco Inter."
        )

        col_planilha_841, col_extrato_841 = st.columns(2)
        with col_planilha_841:
            planilha_final_841 = st.file_uploader(
                "Planilha final organizada",
                type=["xlsx", "xls"],
                key="lucrativite_841_modelo_conferencia",
            )
        with col_extrato_841:
            extrato_conf_841 = st.file_uploader(
                "Extrato Banco Inter para conferência",
                type=["xlsx", "xls", "pdf"],
                key="lucrativite_841_extrato_conferencia",
                help="Aceita Excel ou PDF detalhado do Banco Inter com data, descrição, valor e saldo por transação.",
            )

        try:
            if extrato_conf_841 is not None:
                extrato_df_841 = processar_extrato_inter_conferencia_841(
                    extrato_conf_841.getvalue(),
                    extrato_conf_841.name,
                )
            else:
                extrato_df_841 = st.session_state.get("lucrativite_841_extrato")

            if planilha_final_841 is not None:
                modelo_conf_841 = ler_modelo_para_conferencia(planilha_final_841.getvalue())
            else:
                modelo_conf_841 = st.session_state.get("lucrativite_841_modelo")

            if (
                isinstance(extrato_df_841, pd.DataFrame)
                and not extrato_df_841.empty
                and isinstance(modelo_conf_841, pd.DataFrame)
                and not modelo_conf_841.empty
            ):
                diario_841, resumo_841 = conferir_extrato_modelo(
                    extrato_df_841, modelo_conf_841
                )

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Extrato", resumo_841["qtd_extrato"])
                c2.metric("Planilha", resumo_841["qtd_modelo"])
                c3.metric("Dif. entradas", formatar_moeda(resumo_841["diferenca_entradas"]))
                c4.metric("Dif. saídas", formatar_moeda(resumo_841["diferenca_saidas"]))

                if resumo_841["dias_divergentes"] == 0:
                    st.success(
                        "Conferência concluída: entradas e saídas da planilha batem com o extrato Banco Inter."
                    )
                else:
                    st.warning(
                        f"{resumo_841['dias_divergentes']} dia(s) apresentam divergência. "
                        "Nenhuma diferença foi compensada automaticamente."
                    )

                exibicao_841 = diario_841.copy()
                exibicao_841["DATA"] = pd.to_datetime(exibicao_841["DATA"]).dt.strftime("%d/%m/%Y")
                st.dataframe(
                    exibicao_841,
                    use_container_width=True,
                    hide_index=True,
                    height=420,
                    column_config={
                        coluna: st.column_config.NumberColumn(coluna, format="R$ %.2f")
                        for coluna in [
                            "EXTRATO ENTRADAS",
                            "EXTRATO SAÍDAS",
                            "MODELO ENTRADAS",
                            "MODELO SAÍDAS",
                            "DIF. ENTRADAS",
                            "DIF. SAÍDAS",
                        ]
                    },
                )
            else:
                st.info(
                    "Envie o extrato e a planilha final nesta área para iniciar a conferência. "
                    "Se o extrato já foi processado acima, ele pode ser reutilizado."
                )
        except Exception as erro_conf_841:
            st.error(f"Não foi possível realizar a conferência: {erro_conf_841}")

    with aba_base:
        renderizar_base_inteligente_empresa(
            "lucrativite_841",
            empresa_841,
            {"inter"},
            {"inter": "506"},
        )


if st.session_state.get("empresa_organizador") == "lucrativite_841":
    _renderizar_lucrativite_841()
