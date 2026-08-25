from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

old_import = "from razync.companies import CONFIGURACOES_AUTOKRAFT, CONFIGURACOES_ACCEDE\n"
new_import = old_import + "from razync.company_catalog import EMPRESAS_POR_REGIME, EMPRESAS_POR_CHAVE\n"
assert text.count(old_import) == 1, "Import de empresas não encontrado de forma única"
text = text.replace(old_import, new_import, 1)

old_state = "    empresa_organizador = st.session_state['empresa_organizador']\n\n    col_voltar, col_tit = st.columns([1.2, 8.8])"
new_state = "    empresa_organizador = st.session_state['empresa_organizador']\n    empresa_catalogo_atual = EMPRESAS_POR_CHAVE.get(str(empresa_organizador))\n\n    col_voltar, col_tit = st.columns([1.2, 8.8])"
assert text.count(old_state) == 1, "Bloco de estado do Organizador não encontrado"
text = text.replace(old_state, new_state, 1)

old_title = "        }.get(empresa_organizador, 'Organizador de Planilhas'))"
new_title = "        }.get(\n            empresa_organizador,\n            empresa_catalogo_atual['rotulo'] if empresa_catalogo_atual else 'Organizador de Planilhas'\n        ))"
assert text.count(old_title) == 1, "Título do Organizador não encontrado"
text = text.replace(old_title, new_title, 1)

old_caption = "    }.get(\n        empresa_organizador,\n        'Selecione uma empresa para abrir sua área de trabalho exclusiva.'\n    ))"
new_caption = "    }.get(\n        empresa_organizador,\n        (\n            f\"{empresa_catalogo_atual['regime'].title()} · Área cadastrada para receber ferramentas específicas.\"\n            if empresa_catalogo_atual\n            else 'Selecione uma empresa para abrir sua área de trabalho exclusiva.'\n        )\n    ))"
assert text.count(old_caption) == 1, "Legenda do Organizador não encontrada"
text = text.replace(old_caption, new_caption, 1)

start_marker = "    if empresa_organizador is None:\n        st.markdown(\"##### Empresas disponíveis\")\n"
end_marker = "    if st.session_state['empresa_organizador'] in {\n"
start = text.find(start_marker)
assert start >= 0, "Início dos cards de empresas não encontrado"
end = text.find(end_marker, start)
assert end > start, "Fim dos cards de empresas não encontrado"

new_cards = '''    if empresa_organizador is None:
        st.markdown("##### Empresas disponíveis")
        st.caption("Empresas organizadas pelo regime tributário. As áreas ainda sem ferramentas ficam preparadas para configuração futura.")

        for regime, empresas_regime in EMPRESAS_POR_REGIME.items():
            st.markdown(f"#### {regime.title()}")
            for inicio_linha in range(0, len(empresas_regime), 3):
                colunas_regime = st.columns(3, gap="medium")
                for deslocamento, empresa_catalogo in enumerate(
                    empresas_regime[inicio_linha:inicio_linha + 3]
                ):
                    with colunas_regime[deslocamento]:
                        if st.button(
                            f"**{empresa_catalogo['rotulo']}**",
                            use_container_width=True,
                            key=f"org_empresa_catalogo_{empresa_catalogo['codigo']}"
                        ):
                            chave_destino = empresa_catalogo.get(
                                'chave_sistema', empresa_catalogo['chave']
                            )
                            if chave_destino == 'nova_geracao':
                                st.session_state['org_estabelecimento_nova_geracao_card'] = (
                                    empresa_catalogo.get('estabelecimento', 'matriz')
                                )
                            st.session_state['empresa_organizador'] = chave_destino
                            st.rerun()
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    if empresa_catalogo_atual:
        st.markdown(f"### {empresa_catalogo_atual['rotulo']}")
        st.caption(f"Regime tributário: {empresa_catalogo_atual['regime'].title()}")
        st.info(
            "Empresa cadastrada no Razync. As ferramentas específicas desta empresa "
            "ainda não foram configuradas."
        )

'''
text = text[:start] + new_cards + text[end:]

path.write_text(text, encoding="utf-8")
print("Patch do catálogo de empresas aplicado com sucesso.")
