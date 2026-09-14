from pathlib import Path

app = Path('app.py')
texto = app.read_text(encoding='utf-8')
texto = texto.replace(
    '_chaves_novas = {"625": "valean_625", "841": "lucrativite_841"}',
    '_chaves_novas = {"625": "valean_625", "626": "valean_626", "841": "lucrativite_841"}',
)

marcador = 'def _renderizar_valean_626():'
if marcador not in texto:
    texto += r'''


def _renderizar_valean_626():
    from razync.valean_626 import (
        CONTAS_VALEAN_626,
        processar_extrato_626,
        processar_multiplos_626,
    )

    empresa_626 = "626 - VALEAN ASSESSORIA EM SEGURANÇA DO TRABALHO LTDA - EPP"
    configs_626 = [
        {"nome": "Banco do Brasil · Conta 8", "slug": "banco_brasil", "banco": "banco_brasil", "conta": "8"},
        {"nome": "Sicredi · Conta 1155", "slug": "sicredi", "banco": "sicredi", "conta": "1155"},
    ]
    aba_operacoes_626, aba_base_626 = st.tabs(["Organizar arquivos", "Base Inteligente"])

    with aba_operacoes_626:
        st.markdown("#### Extratos bancários → Modelo Domínio")
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
            renderizar_previa_bancos_padrao(
                quadros_626, ordem=["Banco do Brasil", "Sicredi"]
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
'''

app.write_text(texto, encoding='utf-8')

legacy = Path('app_legacy.py')
leg = legacy.read_text(encoding='utf-8')
# Garante que a importação da Base Inteligente reconheça os bancos usados pelas
# empresas Valean 625/626. Adicionar as chaves é retrocompatível com as demais.
old = """bancos_validos = {\n                    'itau', 'bradesco', 'fibra', 'daycoval', 'sicredi',\n                    'santander', 'btg'\n                }"""
new = """bancos_validos = {\n                    'itau', 'bradesco', 'fibra', 'daycoval', 'sicredi',\n                    'santander', 'btg', 'banco_brasil', 'caixa'\n                }"""
if old in leg:
    leg = leg.replace(old, new)
legacy.write_text(leg, encoding='utf-8')
