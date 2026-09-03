from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
s=s.replace("""                    if despesas_ef is not None and not despesas_ef.empty:
                        tabs_nomes_ef.append('Despesas')
                        tabs_dfs_ef.append(despesas_ef)
""", """                    for conta, df_ef in (despesas_ef or {}).items():
                        tabs_nomes_ef.append('Despesa · ' + CONTAS_ELETRO_FORTE.get(conta, conta))
                        tabs_dfs_ef.append(df_ef)
""")
s=s.replace("""                    if despesas_ef is not None and not despesas_ef.empty:
                        arquivo_despesa_ef = gerar_modelo_dominio_eletro_forte(
""", """                    if despesas_ef:
                        arquivo_despesa_ef = gerar_modelo_dominio_eletro_forte(
""")
p.write_text(s,encoding='utf-8')
