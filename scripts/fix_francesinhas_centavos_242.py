from pathlib import Path

path = Path('razync/eletro_forte.py')
text = path.read_text(encoding='utf-8')
old = '''                valor_linha = round(float(linha.get("VALOR", 0) or 0), 2)\n                # Alguns relatórios recebidos podem vir com diferença de 1 centavo\n                # em relação à francesinha. A francesinha é a fonte de verdade.\n                if abs(valor_linha - valor_correto) > 0.01:\n                    continue\n'''
new = '''                valor_linha = round(float(linha.get("VALOR", 0) or 0), 2)\n                # Compara em centavos inteiros para evitar que 704,25 x 704,26\n                # vire 0,010000000000... no ponto flutuante e seja rejeitado.\n                # A francesinha é a fonte de verdade e aceita até 1 centavo.\n                centavos_linha = int(round(valor_linha * 100))\n                centavos_correto = int(round(valor_correto * 100))\n                if abs(centavos_linha - centavos_correto) > 1:\n                    continue\n'''
if old not in text:
    raise SystemExit('Trecho de tolerância não encontrado')
text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
