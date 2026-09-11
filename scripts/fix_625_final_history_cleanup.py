from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
old = '''        quadros = st.session_state.get("valean_625_quadros", {})
        if quadros:
            renderizar_previa_bancos_padrao(
                quadros, ordem=["Banco do Brasil", "Caixa", "Sicredi"]
            )
'''
new = '''        quadros = st.session_state.get("valean_625_quadros", {})
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
                        achado = re.match(r"^\\s*((?:Pago|Recebido):)\\s*(.*)$", texto, flags=re.I)
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
'''
if old not in s:
    raise SystemExit('bloco quadros 625 não encontrado')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('OK: limpeza final 625 aplicada antes da prévia/exportação')
