from pathlib import Path

p = Path('razync/gz_1211.py')
s = p.read_text(encoding='utf-8')

anchor = '''def ler_extrato_itau_gz(conteudo: bytes) -> pd.DataFrame:\n    """Extrai movimentos do extrato Itaú e ignora linhas de saldo."""\n'''
insert = '''def ler_saldos_extrato_itau_gz(conteudo: bytes) -> dict:\n    """Lê saldo inicial e saldo final impressos no extrato Itaú da GZ."""\n    texto = _texto_pdf(conteudo)\n    saldo_inicial = None\n    saldo_final = None\n\n    m_inicial = re.search(\n        r"\\b\\d{2}/\\d{2}/\\d{4}\\s+SALDO ANTERIOR\\s+([\\d.]+,\\d{2})",\n        texto, re.I\n    )\n    if m_inicial:\n        saldo_inicial = _moeda_br(m_inicial.group(1))\n\n    finais = re.findall(\n        r"\\b\\d{2}/\\d{2}/\\d{4}\\s+SALDO (?:EM CONTA CORRENTE|TOTAL DISPONÍVEL DIA)\\s+([\\d.]+,\\d{2})",\n        texto, re.I\n    )\n    if finais:\n        saldo_final = _moeda_br(finais[-1])\n\n    return {\n        "saldo_inicial": round(float(saldo_inicial), 2) if saldo_inicial is not None else None,\n        "saldo_final_informado": round(float(saldo_final), 2) if saldo_final is not None else None,\n    }\n\n\n'''
if insert not in s:
    s = s.replace(anchor, insert + anchor)

old = '''    extrato = ler_extrato_itau_gz(extrato_bytes)\n    boletos = ler_boletos_liquidados_gz(boletos_bytes)\n'''
new = '''    extrato = ler_extrato_itau_gz(extrato_bytes)\n    saldos_extrato = ler_saldos_extrato_itau_gz(extrato_bytes)\n    boletos = ler_boletos_liquidados_gz(boletos_bytes)\n'''
s = s.replace(old, new)

old_resumo = '''        "total_extrato": round(float(extrato["VALOR"].sum()), 2),\n        "total_modelo": round(float(df_saida["VALOR"].sum()), 2),\n    }\n'''
new_resumo = '''        "total_extrato": round(float(extrato["VALOR"].sum()), 2),\n        "total_modelo": round(float(df_saida["VALOR"].sum()), 2),\n        "saldo_inicial": saldos_extrato.get("saldo_inicial"),\n        "saldo_final_informado": saldos_extrato.get("saldo_final_informado"),\n    }\n    if resumo["saldo_inicial"] is not None:\n        resumo["saldo_final_calculado"] = round(\n            float(resumo["saldo_inicial"]) + float(resumo["total_extrato"]), 2\n        )\n    else:\n        resumo["saldo_final_calculado"] = None\n    if (\n        resumo["saldo_final_calculado"] is not None\n        and resumo["saldo_final_informado"] is not None\n    ):\n        resumo["diferenca_saldo_extrato"] = round(\n            float(resumo["saldo_final_informado"]) - float(resumo["saldo_final_calculado"]), 2\n        )\n    else:\n        resumo["diferenca_saldo_extrato"] = None\n'''
s = s.replace(old_resumo, new_resumo)
p.write_text(s, encoding='utf-8')

# UI da 1211: trocar bloco de 3 métricas financeiras da conferência por diagnóstico completo de saldo.
p = Path('app.py')
s = p.read_text(encoding='utf-8')
old_ui = '''                c1_gz, c2_gz, c3_gz = st.columns(3)\n                c1_gz.metric('Total líquido extrato', formatar_moeda(total_ext_gz))\n                c2_gz.metric('Total líquido Modelo', formatar_moeda(total_mod_gz))\n                c3_gz.metric('Diferença', formatar_moeda(dif_total_gz))\n                if abs(dif_total_gz) <= 0.02:\n                    st.success('O total financeiro do Modelo Domínio está preservado em relação ao extrato.')\n                else:\n                    st.error('O total financeiro do Modelo Domínio não está fechando com o extrato.')\n'''
new_ui = '''                c1_gz, c2_gz, c3_gz = st.columns(3)\n                c1_gz.metric('Total líquido extrato', formatar_moeda(total_ext_gz))\n                c2_gz.metric('Total líquido Modelo', formatar_moeda(total_mod_gz))\n                c3_gz.metric('Diferença Modelo × Extrato', formatar_moeda(dif_total_gz))\n                if abs(dif_total_gz) <= 0.02:\n                    st.success('O Modelo Domínio preserva exatamente a movimentação reconhecida do extrato.')\n                else:\n                    st.error('O Modelo Domínio não está preservando a movimentação reconhecida do extrato.')\n\n                saldo_inicial_gz = resumo_conf_gz.get('saldo_inicial')\n                saldo_calc_gz = resumo_conf_gz.get('saldo_final_calculado')\n                saldo_final_gz = resumo_conf_gz.get('saldo_final_informado')\n                dif_saldo_gz = resumo_conf_gz.get('diferenca_saldo_extrato')\n                if saldo_inicial_gz is not None and saldo_final_gz is not None:\n                    st.markdown('##### Fechamento de saldo do extrato Itaú')\n                    sc1_gz, sc2_gz, sc3_gz, sc4_gz = st.columns(4)\n                    sc1_gz.metric('Saldo inicial', formatar_moeda(saldo_inicial_gz))\n                    sc2_gz.metric('Movimentação', formatar_moeda(total_ext_gz))\n                    sc3_gz.metric('Saldo calculado', formatar_moeda(saldo_calc_gz))\n                    sc4_gz.metric('Saldo final Itaú', formatar_moeda(saldo_final_gz))\n                    if dif_saldo_gz is not None and abs(float(dif_saldo_gz)) > 0.02:\n                        st.warning(\n                            'O próprio extrato possui diferença de fechamento de '\n                            f'{formatar_moeda(abs(float(dif_saldo_gz)))} entre os lançamentos '\n                            'listados e o saldo final informado. Nenhum ajuste contábil foi criado automaticamente.'\n                        )\n                    else:\n                        st.success('Os lançamentos do extrato fecham com o saldo final informado pelo Itaú.')\n'''
if old_ui not in s:
    raise SystemExit('bloco UI GZ não encontrado')
s = s.replace(old_ui, new_ui, 1)
p.write_text(s, encoding='utf-8')

print('diagnóstico de saldo GZ atualizado')
