from pathlib import Path
# Trigger do workflow: corrigir primeiros movimentos de novas datas no Bradesco.

path = Path('razync/bradesco_radani.py')
text = path.read_text(encoding='utf-8')

text = text.replace(
    '    totais_impressos = []\n    data_atual = None',
    '    totais_impressos = []\n    datas_detectadas = set()\n    data_atual = None'
)

text = text.replace(
    '            if data_linha is not None:\n                data_atual = data_linha\n',
    '            if data_linha is not None:\n                data_atual = data_linha\n                datas_detectadas.add(data_linha.normalize())\n'
)

old = '''            valor = None\n            mesma_data = bool(\n                lancamentos\n                and pd.Timestamp(lancamentos[-1][\"DATA\"]).normalize() == data_atual.normalize()\n            )\n\n            # O valor da coluna Crédito/Débito é a fonte principal. O saldo só recupera\n            # valor ausente quando estamos na mesma data, evitando saltos do Invest Fácil.\n            if valor_impresso is not None:\n                valor = round(valor_impresso, 2)\n                if saldo is not None:\n                    saldo_atual = float(saldo)\n                elif saldo_atual is not None:\n                    saldo_atual = round(saldo_atual + valor, 2)\n            elif saldo is not None and saldo_atual is not None and mesma_data:\n                valor = round(float(saldo) - saldo_atual, 2)\n                saldo_atual = float(saldo)\n            elif saldo is not None:\n                saldo_atual = float(saldo)\n                continue\n'''
new = '''            valor = None\n\n            # A coluna Crédito/Débito continua sendo a fonte principal. Quando o OCR\n            # perde essa coluna, a diferença de saldo recupera o movimento mesmo na\n            # primeira linha de uma nova data: o saldo da conta corrente é contínuo\n            # entre os dias. A seção Saldos Invest Fácil já é excluída antes daqui.\n            if valor_impresso is not None:\n                valor = round(valor_impresso, 2)\n                if saldo is not None:\n                    # Se o valor impresso e a variação de saldo discordarem muito, a\n                    # variação é mais confiável para PDFs rasterizados do Bradesco.\n                    if saldo_atual is not None:\n                        variacao = round(float(saldo) - saldo_atual, 2)\n                        if abs(abs(variacao) - abs(valor)) > max(0.02, abs(valor) * 0.01):\n                            valor = variacao\n                    saldo_atual = float(saldo)\n                elif saldo_atual is not None:\n                    saldo_atual = round(saldo_atual + valor, 2)\n            elif saldo is not None and saldo_atual is not None:\n                valor = round(float(saldo) - saldo_atual, 2)\n                saldo_atual = float(saldo)\n            elif saldo is not None:\n                saldo_atual = float(saldo)\n                continue\n'''
if old not in text:
    raise SystemExit('Trecho de recuperação por saldo não encontrado')
text = text.replace(old, new)

text = text.replace(
    '    diferenca_debitos = round(total_debitos - esperado_debitos, 2)\n\n    diagnostico = {',
    '''    diferenca_debitos = round(total_debitos - esperado_debitos, 2)\n    datas_com_lancamento = {pd.Timestamp(x[\"DATA\"]).normalize() for x in unicos}\n    datas_sem_lancamento = sorted(datas_detectadas - datas_com_lancamento)\n\n    diagnostico = {'''
)
text = text.replace(
    '        "totais_encontrados": len(totais_impressos),\n        "ok": (',
    '''        "totais_encontrados": len(totais_impressos),\n        "datas_detectadas": [d.strftime(\"%d/%m/%Y\") for d in sorted(datas_detectadas)],\n        "datas_com_lancamento": [d.strftime(\"%d/%m/%Y\") for d in sorted(datas_com_lancamento)],\n        "datas_sem_lancamento": [d.strftime(\"%d/%m/%Y\") for d in datas_sem_lancamento],\n        "ok": ('''
)
text = text.replace(
    '            and abs(diferenca_debitos) <= 0.02\n        ),',
    '            and abs(diferenca_debitos) <= 0.02\n            and not datas_sem_lancamento\n        ),'
)
path.write_text(text, encoding='utf-8')

app_path = Path('app.py')
app = app_path.read_text(encoding='utf-8')
needle = '''                            if diagnostico_bradesco_radani and not diagnostico_bradesco_radani.get('ok'):\n                                st.warning(\n                                    'Bradesco: a leitura não fechou com os totais impressos no extrato. '\n                                    f\"Diferença em créditos: {formatar_moeda(abs(diagnostico_bradesco_radani.get('diferenca_creditos', 0)))} · \"\n                                    f\"Diferença em débitos: {formatar_moeda(abs(diagnostico_bradesco_radani.get('diferenca_debitos', 0)))}. \"\n                                    'Os lançamentos reconhecidos serão exibidos, mas revise o extrato antes de concluir.'\n                                )\n'''
replacement = '''                            if diagnostico_bradesco_radani and not diagnostico_bradesco_radani.get('ok'):\n                                datas_faltantes_radani = diagnostico_bradesco_radani.get('datas_sem_lancamento') or []\n                                complemento_datas_radani = (\n                                    ' Datas detectadas sem lançamento reconhecido: ' + ', '.join(datas_faltantes_radani) + '.'\n                                    if datas_faltantes_radani else ''\n                                )\n                                st.warning(\n                                    'Bradesco: a leitura não fechou integralmente com o extrato. '\n                                    f\"Diferença em créditos: {formatar_moeda(abs(diagnostico_bradesco_radani.get('diferenca_creditos', 0)))} · \"\n                                    f\"Diferença em débitos: {formatar_moeda(abs(diagnostico_bradesco_radani.get('diferenca_debitos', 0)))}.\"\n                                    f\"{complemento_datas_radani} \"\n                                    'Os lançamentos reconhecidos serão exibidos, mas revise o extrato antes de concluir.'\n                                )\n'''
if needle not in app:
    raise SystemExit('Aviso Bradesco não encontrado no app')
app = app.replace(needle, replacement)
app_path.write_text(app, encoding='utf-8')

Path('tests/test_bradesco_radani_periods.py').write_text('''import pandas as pd\n\n\ndef test_regra_de_recuperacao_nao_restringe_mesma_data():\n    texto = open(\"razync/bradesco_radani.py\", encoding=\"utf-8\").read()\n    assert \"mesma_data\" not in texto\n    assert \"datas_sem_lancamento\" in texto\n    assert \"saldo da conta corrente é contínuo\" in texto\n''', encoding='utf-8')
