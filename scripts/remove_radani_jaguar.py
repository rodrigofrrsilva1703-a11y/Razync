from pathlib import Path

app_path = Path('app.py')
app = app_path.read_text(encoding='utf-8')

app = app.replace(
    'from razync.radani import analisar_desmembramentos, consolidar_jaguares, consolidar_comprovantes_sispag',
    'from razync.radani import analisar_desmembramentos, consolidar_comprovantes_sispag'
)

start = app.find("@st.cache_data(show_spinner=False, ttl=1800, max_entries=8)\ndef _radani_cache_jaguares")
end = app.find("@st.cache_data(show_spinner=False, ttl=1800, max_entries=8)\ndef _radani_cache_comprovantes", start)
if start != -1 and end != -1:
    app = app[:start] + app[end:]

app = app.replace(
    "'O extrato define o período e os totais oficiais. Jaguar e comprovantes '\n                'são analisados somente quando você clicar em Processar 968.'",
    "'O extrato define o período e os totais oficiais. Somente os comprovantes de salários do Itaú '\n                'são usados como apoio para desmembrar SISPAG.'"
)

old_upload = '''            col_jaguar_radani, col_comp_radani = st.columns(2)\n            with col_jaguar_radani:\n                jaguares_radani = st.file_uploader(\n                    'Planilhas auxiliares Jaguar',\n                    type=['xlsx', 'xls'],\n                    accept_multiple_files=True,\n                    key='radani_jaguares',\n                    help='Pode enviar Jaguar anual e lançamentos diversos. Só o período do extrato será utilizado.'\n                )\n            with col_comp_radani:\n                comprovantes_sispag_radani = st.file_uploader(\n                    'Comprovantes de salários / SISPAG',\n                    type=['pdf'],\n                    accept_multiple_files=True,\n                    key='radani_comprovantes_sispag',\n                    help='Opcional. Quando o total fecha, os comprovantes têm prioridade sobre a Jaguar.'\n                )\n'''
new_upload = '''            comprovantes_sispag_radani = st.file_uploader(\n                'Comprovantes de salários / SISPAG — somente Itaú',\n                type=['pdf'],\n                accept_multiple_files=True,\n                key='radani_comprovantes_sispag',\n                help=(\n                    'Opcional. A Radani paga salários somente pelo Itaú. Os comprovantes são usados '\n                    'apenas para desmembrar SISPAG quando o total fecha exatamente com o extrato.'\n                )\n            )\n'''
if old_upload not in app:
    raise SystemExit('Bloco de upload Jaguar não encontrado')
app = app.replace(old_upload, new_upload)

app = app.replace(
    "            for arq in (jaguares_radani or []):\n                assinatura_radani.update(arq.name.encode('utf-8', errors='ignore'))\n                assinatura_radani.update(arq.getvalue())\n",
    ''
)
app = app.replace(
    "                    arquivos_jaguar_tuple = tuple(\n                        (arq.name, arq.getvalue()) for arq in (jaguares_radani or [])\n                    )\n",
    ''
)

old_jaguar_period = '''                            jaguar_periodo_radani = (\n                                _radani_cache_jaguares(\n                                    arquivos_jaguar_tuple, inicio_iso, fim_iso\n                                )\n                                if arquivos_jaguar_tuple\n                                else pd.DataFrame()\n                            )\n'''
if old_jaguar_period not in app:
    raise SystemExit('Bloco de processamento Jaguar não encontrado')
app = app.replace(old_jaguar_period, '')

app = app.replace(
    "                                df_extrato_radani,\n                                jaguar_periodo_radani,\n                                nome_banco_radani,\n                                comprovantes_periodo_radani,\n",
    "                                df_extrato_radani,\n                                nome_banco_radani,\n                                comprovantes_periodo_radani,\n"
)

app_path.write_text(app, encoding='utf-8')

radani_path = Path('razync/radani.py')
rad = radani_path.read_text(encoding='utf-8')
start = rad.find('def analisar_desmembramentos(')
if start == -1:
    raise SystemExit('Função analisar_desmembramentos não encontrada')
new_func = '''def analisar_desmembramentos(extrato: pd.DataFrame, banco: str, comprovantes: pd.DataFrame | None = None) -> AnaliseRadani:\n    \"\"\"Usa comprovantes somente para SISPAG do Itaú; demais movimentos ficam como no extrato.\"\"\"\n    if extrato is None or extrato.empty:\n        vazio = pd.DataFrame()\n        return AnaliseRadani(vazio, vazio, vazio)\n\n    df = extrato.copy()\n    df[\"DATA\"] = pd.to_datetime(df[\"DATA\"], dayfirst=True, errors=\"coerce\")\n    df[\"VALOR\"] = pd.to_numeric(df[\"VALOR\"], errors=\"coerce\")\n    df[\"HISTÓRICO\"] = df.get(\"HISTÓRICO\", \"\").fillna(\"\").astype(str)\n    df = df.dropna(subset=[\"DATA\", \"VALOR\"]).reset_index(drop=True)\n    if comprovantes is None:\n        comprovantes = pd.DataFrame()\n\n    banco_itau = \"ITAU\" in _norm(banco)\n    usados_comprovantes = set()\n    saida = []\n    revisoes = []\n    detalhes = []\n\n    for _, mov in df.iterrows():\n        hist = str(mov[\"HISTÓRICO\"])\n        valor = float(mov[\"VALOR\"])\n        data = pd.Timestamp(mov[\"DATA\"]).normalize()\n        eh_sispag = \"SISPAG\" in _norm(hist) or \"SALAR\" in _norm(hist) or \"FOLHA\" in _norm(hist)\n\n        if banco_itau and eh_sispag and not comprovantes.empty:\n            comp_disp = comprovantes.loc[~comprovantes.index.isin(usados_comprovantes)].copy()\n            comp_dia = comp_disp[comp_disp[\"DATA\"].dt.normalize() == data].copy()\n            if valor < 0:\n                comp_dia = comp_dia[comp_dia[\"VALOR\"] < 0]\n            elif valor > 0:\n                comp_dia = comp_dia[comp_dia[\"VALOR\"] > 0]\n            grupo_comp = _subset_exato(comp_dia, valor, hist, limite=80)\n            if grupo_comp is not None and len(grupo_comp) >= 2:\n                for cidx, det in grupo_comp.iterrows():\n                    novo = mov.to_dict()\n                    # A data bancária é a referência oficial do Modelo Domínio.\n                    novo[\"DATA\"] = pd.Timestamp(mov[\"DATA\"])\n                    novo[\"VALOR\"] = float(det[\"VALOR\"])\n                    novo[\"HISTÓRICO\"] = str(det[\"HISTÓRICO\"])\n                    novo[\"DESCRIÇÃO\"] = mov.get(\"DESCRIÇÃO\", banco)\n                    saida.append(novo)\n                    usados_comprovantes.add(cidx)\n                    detalhes.append({\n                        \"BANCO\": banco, \"DATA BANCO\": data, \"HISTÓRICO BANCO\": hist,\n                        \"VALOR BANCO\": valor, \"DATA DETALHE\": det[\"DATA\"],\n                        \"HISTÓRICO DETALHE\": det[\"HISTÓRICO\"], \"VALOR DETALHE\": det[\"VALOR\"],\n                        \"STATUS\": \"Identificado - comprovante SISPAG\",\n                        \"FONTE\": \"Comprovante SISPAG\",\n                    })\n                continue\n\n            revisoes.append({\n                \"BANCO\": banco, \"DATA\": data, \"HISTÓRICO\": hist, \"VALOR\": valor,\n                \"TOTAL ENCONTRADO\": None, \"ITENS\": int(len(comp_dia)),\n                \"DETALHES\": \"\",\n                \"STATUS\": \"SISPAG sem fechamento exato nos comprovantes\",\n            })\n\n        # Bradesco nunca usa comprovantes de salário; qualquer outro lançamento\n        # permanece exatamente como veio do extrato.\n        saida.append(mov.to_dict())\n\n    organizado = pd.DataFrame(saida)\n    if not organizado.empty:\n        organizado = organizado.sort_values(\"DATA\", kind=\"stable\").reset_index(drop=True)\n    return AnaliseRadani(\n        organizado=organizado,\n        revisoes=pd.DataFrame(revisoes),\n        detalhamentos=pd.DataFrame(detalhes),\n    )\n'''
rad = rad[:start] + new_func
rad = rad.replace(
    'O extrato bancário é a fonte oficial do período e dos totais. As planilhas Jaguar\nsão usadas apenas para detalhar lançamentos consolidados quando a composição é\nmatematicamente consistente dentro do período processado.',
    'O extrato bancário é a fonte oficial do período e dos totais. Somente os comprovantes\nde pagamento de salários do Itaú podem detalhar SISPAG, sempre com fechamento exato.'
)
radani_path.write_text(rad, encoding='utf-8')

test_path = Path('tests/test_radani.py')
test_path.write_text('''import pandas as pd\n\nfrom razync.radani import analisar_desmembramentos\n\n\ndef _extrato(valor=-33000.0, hist='SISPAG SALARIOS', banco='BANCO ITAU'):\n    return pd.DataFrame([{\n        'DESCRIÇÃO': banco, 'DATA': pd.Timestamp('2026-06-15'), 'VALOR': valor,\n        'DÉBITO': '', 'CRÉDITO': '', 'HISTÓRICO': hist,\n    }])\n\n\ndef _comprovantes():\n    return pd.DataFrame([\n        {'DATA': pd.Timestamp('2026-06-15'), 'HISTÓRICO': 'FUNC A VALE', 'VALOR': -20000.0, 'ARQUIVO': 'C', 'TIPO': 'VALE', 'FONTE': 'Comprovante SISPAG'},\n        {'DATA': pd.Timestamp('2026-06-15'), 'HISTÓRICO': 'FUNC B VALE', 'VALOR': -13000.0, 'ARQUIVO': 'C', 'TIPO': 'VALE', 'FONTE': 'Comprovante SISPAG'},\n    ])\n\n\ndef test_itau_sispag_fecha_com_comprovantes_e_desmembra():\n    res = analisar_desmembramentos(_extrato(), 'Itaú', comprovantes=_comprovantes())\n    assert len(res.organizado) == 2\n    assert round(res.organizado['VALOR'].sum(), 2) == -33000.0\n    assert set(res.detalhamentos['FONTE']) == {'Comprovante SISPAG'}\n    assert res.revisoes.empty\n\n\ndef test_itau_sispag_sem_comprovante_fica_original():\n    res = analisar_desmembramentos(_extrato(), 'Itaú', comprovantes=pd.DataFrame())\n    assert len(res.organizado) == 1\n    assert res.organizado.iloc[0]['HISTÓRICO'] == 'SISPAG SALARIOS'\n    assert res.detalhamentos.empty\n\n\ndef test_bradesco_nao_usa_comprovantes_de_salario():\n    extrato = _extrato(banco='BANCO BRADESCO')\n    res = analisar_desmembramentos(extrato, 'Bradesco', comprovantes=_comprovantes())\n    assert len(res.organizado) == 1\n    assert res.organizado.iloc[0]['HISTÓRICO'] == 'SISPAG SALARIOS'\n    assert res.detalhamentos.empty\n    assert res.revisoes.empty\n\n\ndef test_pix_itau_permanece_como_extrato():\n    extrato = _extrato(-150.0, 'PIX ENVIADO JOSE CLAUDIO')\n    res = analisar_desmembramentos(extrato, 'Itaú', comprovantes=_comprovantes())\n    assert len(res.organizado) == 1\n    assert res.organizado.iloc[0]['HISTÓRICO'].startswith('PIX ENVIADO')\n''', encoding='utf-8')
