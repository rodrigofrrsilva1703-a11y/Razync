from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

# A Conciliação com Razão deve analisar no sentido contábil Razão - Extrato.
# O leitor dos extratos permanece intacto; alteramos somente as diferenças.
old = '''                df_conciliacao['DIF_ENTRADAS'] = df_conciliacao['ENTRADAS_EXTRATO'] - df_conciliacao['ENTRADAS_RAZAO']
                df_conciliacao['DIF_SAIDAS'] = df_conciliacao['SAIDAS_EXTRATO'] - df_conciliacao['SAIDAS_RAZAO']
'''
new = '''                # Sentido correto da análise: RAZÃO - EXTRATO.
                # Valor positivo = há mais no Razão do que no Extrato.
                # Valor negativo = há mais no Extrato do que no Razão.
                df_conciliacao['DIF_ENTRADAS'] = (
                    df_conciliacao['ENTRADAS_RAZAO'] - df_conciliacao['ENTRADAS_EXTRATO']
                )
                df_conciliacao['DIF_SAIDAS'] = (
                    df_conciliacao['SAIDAS_RAZAO'] - df_conciliacao['SAIDAS_EXTRATO']
                )
'''
if text.count(old) != 1:
    raise SystemExit(f'Bloco de diferenças encontrado {text.count(old)} vezes.')
text = text.replace(old, new, 1)

# Deixa o sentido da análise explícito na tela para evitar interpretação invertida.
old_caption = '''    st.caption("Acompanhe a conferência diária comparando diretamente as Entradas e Saídas do Extrato com o Razão da Domínio.")
'''
new_caption = '''    st.caption(
        "Acompanhe a conferência diária comparando Entradas e Saídas. "
        "As diferenças são calculadas no sentido Razão − Extrato."
    )
'''
if old_caption in text:
    text = text.replace(old_caption, new_caption, 1)

checks = [
    "df_conciliacao['ENTRADAS_RAZAO'] - df_conciliacao['ENTRADAS_EXTRATO']",
    "df_conciliacao['SAIDAS_RAZAO'] - df_conciliacao['SAIDAS_EXTRATO']",
    'Razão − Extrato',
    "lambda row: \"✅ Batendo\" if abs(row['DIF_ENTRADAS']) < 0.01 and abs(row['DIF_SAIDAS']) < 0.01 else \"❌ Divergente\"",
]
for check in checks:
    if check not in text:
        raise SystemExit(f'Validação falhou: {check}')

path.write_text(text, encoding='utf-8')
print('Conciliação com Razão corrigida para analisar no sentido Razão - Extrato.')
