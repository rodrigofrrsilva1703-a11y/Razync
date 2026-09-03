from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
start=s.index("        with aba_operacoes_gz:\n            st.markdown('#### Conferência com Extrato')")
end=s.index("\n    if st.session_state['empresa_organizador'] == 'eletro_forte':", start)
novo="""        with aba_operacoes_gz:
            st.markdown(f'#### Conferência — {empresa_gz}')
            renderizar_conferencia_autokraft(
                'gz1211',
                bancos_config=[{'nome': 'Itaú', 'slug': 'itau'}],
            )
"""
s=s[:start]+novo+s[end:]
p.write_text(s,encoding='utf-8')
t=p.read_text(encoding='utf-8')
assert "renderizar_conferencia_autokraft(\n                'gz1211'" in t
assert "Fechamento de saldo do extrato Itaú" not in t
assert "Conferência dos BOLETOS RECEBIDOS" not in t
print('conferencia GZ padronizada')
