from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

antigo_abas = """    abas_diarias = [
        aba for aba in xls.sheet_names if re.fullmatch(r'\\d{2}\\.\\d{2}', str(aba).strip())
    ]
    if not abas_diarias:
        raise ValueError(
            \"Nenhuma aba diária no formato DD.MM foi encontrada no arquivo enviado.\"
        )
"""
novo_abas = """    # Os mapas da Autokraft existem em dois padrões de nome de aba:
    # arquivos antigos usam DD.MM e arquivos mais novos usam DD-MM.
    # Aceitamos ambos sem incluir abas auxiliares de pagamentos/adiantamentos.
    abas_diarias = [
        aba for aba in xls.sheet_names
        if re.fullmatch(r'\\d{2}[.-]\\d{2}', str(aba).strip())
    ]
    if not abas_diarias:
        raise ValueError(
            \"Nenhuma aba diária no formato DD-MM ou DD.MM foi encontrada no arquivo enviado.\"
        )
"""
if antigo_abas not in s:
    raise SystemExit('Bloco de identificação das abas Autokraft não encontrado.')
s = s.replace(antigo_abas, novo_abas, 1)

antigo_data = """            dia, mes = [int(parte) for parte in str(nome_aba).split('.')]
            data_aba = pd.Timestamp(year=ano_referencia, month=mes, day=dia)
"""
novo_data = """            partes_data = re.split(r'[.-]', str(nome_aba).strip())
            if len(partes_data) != 2:
                continue
            dia, mes = [int(parte) for parte in partes_data]
            data_aba = pd.Timestamp(year=ano_referencia, month=mes, day=dia)
"""
if antigo_data not in s:
    raise SystemExit('Fallback de data das abas Autokraft não encontrado.')
s = s.replace(antigo_data, novo_data, 1)

checks = [
    "re.fullmatch(r'\\d{2}[.-]\\d{2}', str(aba).strip())",
    "partes_data = re.split(r'[.-]', str(nome_aba).strip())",
    'DD-MM ou DD.MM',
]
for check in checks:
    if check not in s:
        raise SystemExit(f'Validação falhou: {check}')

p.write_text(s, encoding='utf-8')
print('Leitor Autokraft atualizado para abas DD-MM e DD.MM.')
