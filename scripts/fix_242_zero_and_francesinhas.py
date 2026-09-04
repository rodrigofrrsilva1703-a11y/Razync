from pathlib import Path
p=Path('app.py')
s=p.read_text(encoding='utf-8')
old="""            if coluna_regra in {'debito', 'credito'}:\n                atual_regra = debito_atual if coluna_regra == 'debito' else credito_atual\n                if atual_regra not in valores_regra:\n                    resumo['preservados_regra'] += 1\n                    resumo['ja_preenchidos'] += 1\n                    continue\n                resumo['elegiveis_regra'] += 1\n                if coluna_regra == 'debito':\n                    ws.cell(numero_linha, col_debito).value = None\n                    debito_atual = ''\n                else:\n                    ws.cell(numero_linha, col_credito).value = None\n                    credito_atual = ''\n"""
new="""            if coluna_regra in {'debito', 'credito'}:\n                atual_regra = debito_atual if coluna_regra == 'debito' else credito_atual\n                if atual_regra not in valores_regra:\n                    resumo['preservados_regra'] += 1\n                    resumo['ja_preenchidos'] += 1\n                    continue\n                resumo['elegiveis_regra'] += 1\n                # Na 242, o 0 é apenas marcador de pendência. Não o apaga antes de\n                # confirmar uma classificação segura: se a Base não encontrar conta,\n                # o arquivo deve continuar com 0 (nunca trocar por 1000 ou outro valor).\n                if atual_regra == '0':\n                    pass\n                elif coluna_regra == 'debito':\n                    ws.cell(numero_linha, col_debito).value = None\n                    debito_atual = ''\n                else:\n                    ws.cell(numero_linha, col_credito).value = None\n                    credito_atual = ''\n"""
if old not in s: raise SystemExit('bloco classificacao nao encontrado')
s=s.replace(old,new,1)
# Depois de definir a contrapartida, 0 precisa ser tratado como vazio apenas para busca,
# mas só substituído quando houver uma conta realmente segura.
old2="""            contrapartida_atual = texto_celula_seguro(\n                ws.cell(numero_linha, coluna_contrapartida).value\n            )\n            if contrapartida_atual:\n                resumo['automaticos'] += 1\n                if linha_estava_parcial:\n                    resumo['parciais_completados'] += 1\n                continue\n"""
new2="""            contrapartida_atual = texto_celula_seguro(\n                ws.cell(numero_linha, coluna_contrapartida).value\n            )\n            marcador_zero = (empresa_classificacao == 'eletro_forte' and contrapartida_atual == '0')\n            if contrapartida_atual and not marcador_zero:\n                resumo['automaticos'] += 1\n                if linha_estava_parcial:\n                    resumo['parciais_completados'] += 1\n                continue\n"""
if old2 not in s: raise SystemExit('bloco contrapartida nao encontrado')
s=s.replace(old2,new2,1)
# Remover regra especial de antecipado para a 242; ela estava podendo forçar conta sem base.
old3="""            if 'antecipad' in normalizar_texto(historico):\n                ws.cell(numero_linha, coluna_contrapartida).value = 532\n                resumo['automaticos'] += 1\n                resumo['antecipados'] += 1\n                if linha_estava_parcial:\n                    resumo['parciais_completados'] += 1\n            elif conta_segura:\n"""
new3="""            if 'antecipad' in normalizar_texto(historico) and empresa_classificacao != 'eletro_forte':\n                ws.cell(numero_linha, coluna_contrapartida).value = 532\n                resumo['automaticos'] += 1\n                resumo['antecipados'] += 1\n                if linha_estava_parcial:\n                    resumo['parciais_completados'] += 1\n            elif conta_segura:\n"""
if old3 not in s: raise SystemExit('bloco antecipado nao encontrado')
s=s.replace(old3,new3,1)
p.write_text(s,encoding='utf-8')
# Garantia explícita no matcher de francesinhas: 1 centavo e janela simétrica de 7 dias.
p=Path('razync/eletro_forte.py'); s=p.read_text(encoding='utf-8')
s=s.replace("if abs(valor_linha_centavos - valor_correto_centavos) > 1:","if abs(valor_linha_centavos - valor_correto_centavos) > 1:")
s=s.replace("if not 0 <= diferenca_dias <= limite_dias:","if abs(diferenca_dias) > limite_dias:")
p.write_text(s,encoding='utf-8')
