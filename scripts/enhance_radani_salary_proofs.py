from pathlib import Path

radani_path = Path('razync/radani.py')
s = radani_path.read_text(encoding='utf-8')

# Imports
s = s.replace('import pandas as pd\n', 'import pandas as pd\nfrom pypdf import PdfReader\n', 1)

anchor = '''def consolidar_jaguares(arquivos: list[tuple[str, bytes]], inicio, fim) -> pd.DataFrame:\n'''
proof_code = r'''def ler_comprovantes_sispag_pdf(arquivo_bytes: bytes, nome_arquivo: str = "Comprovantes SISPAG") -> pd.DataFrame:
    """Extrai beneficiário, valor, data e tipo de cada comprovante Itaú SISPAG."""
    try:
        reader = PdfReader(BytesIO(arquivo_bytes), strict=False)
    except Exception:
        return pd.DataFrame(columns=["DATA", "HISTÓRICO", "VALOR", "ARQUIVO", "TIPO", "FONTE"])

    linhas = []
    for pagina in reader.pages:
        texto = pagina.extract_text() or ""
        norm = _norm(texto)
        if "SISPAG SALARIOS" not in norm:
            continue

        m_nome = re.search(r"Nome:\s*(.*?)\s+Ag[êe]ncia:", texto, flags=re.I | re.S)
        m_valor = re.search(r"Valor:\s*R\$\s*([\d.]+,\d{2})", texto, flags=re.I)
        m_data = re.search(r"Transfer[êe]ncia efetuada em\s*(\d{2}/\d{2}/\d{4})", texto, flags=re.I)
        m_tipo = re.search(
            r"Informa[cç][õo]es fornecidas pelo\s*pagador:\s*(.*?)\s*Transfer[êe]ncia efetuada em",
            texto,
            flags=re.I | re.S,
        )
        if not (m_nome and m_valor and m_data):
            continue

        nome = re.sub(r"\s+", " ", m_nome.group(1)).strip()
        tipo = re.sub(r"\s+", " ", m_tipo.group(1)).strip() if m_tipo else "SALARIO"
        valor = _valor_num(m_valor.group(1))
        data = pd.to_datetime(m_data.group(1), dayfirst=True, errors="coerce")
        if valor is None or pd.isna(data):
            continue

        linhas.append({
            "DATA": data,
            "HISTÓRICO": f"{nome} {tipo}".strip(),
            "VALOR": -abs(float(valor)),
            "ARQUIVO": nome_arquivo,
            "TIPO": tipo,
            "FONTE": "Comprovante SISPAG",
        })

    if not linhas:
        return pd.DataFrame(columns=["DATA", "HISTÓRICO", "VALOR", "ARQUIVO", "TIPO", "FONTE"])
    return pd.DataFrame(linhas).sort_values(["DATA", "HISTÓRICO"], kind="stable").reset_index(drop=True)


def consolidar_comprovantes_sispag(arquivos: list[tuple[str, bytes]], inicio, fim) -> pd.DataFrame:
    partes = []
    for nome, conteudo in arquivos:
        try:
            df = ler_comprovantes_sispag_pdf(conteudo, nome)
            if not df.empty:
                partes.append(df)
        except Exception:
            continue
    if not partes:
        return pd.DataFrame(columns=["DATA", "HISTÓRICO", "VALOR", "ARQUIVO", "TIPO", "FONTE"])
    df = pd.concat(partes, ignore_index=True)
    ini = pd.Timestamp(inicio).normalize()
    final = pd.Timestamp(fim).normalize()
    return df[(df["DATA"].dt.normalize() >= ini) & (df["DATA"].dt.normalize() <= final)].reset_index(drop=True)


'''
if 'def ler_comprovantes_sispag_pdf' not in s:
    if anchor not in s:
        raise SystemExit('Anchor consolidar_jaguares not found')
    s = s.replace(anchor, proof_code + anchor, 1)

old_sig = 'def analisar_desmembramentos(extrato: pd.DataFrame, jaguar: pd.DataFrame, banco: str) -> AnaliseRadani:'
new_sig = 'def analisar_desmembramentos(extrato: pd.DataFrame, jaguar: pd.DataFrame, banco: str, comprovantes: pd.DataFrame | None = None) -> AnaliseRadani:'
s = s.replace(old_sig, new_sig, 1)

old_init = '''    if jaguar is None:\n        jaguar = pd.DataFrame()\n\n    usados_jaguar = set()\n'''
new_init = '''    if jaguar is None:\n        jaguar = pd.DataFrame()\n    if comprovantes is None:\n        comprovantes = pd.DataFrame()\n\n    usados_jaguar = set()\n    usados_comprovantes = set()\n'''
if old_init not in s:
    raise SystemExit('Analysis init anchor not found')
s = s.replace(old_init, new_init, 1)

anchor_loop = '''        forte, moderado = _eh_generico(hist)\n        if not (forte or moderado) or jaguar.empty:\n            saida.append(mov.to_dict())\n            continue\n\n        data = pd.Timestamp(mov["DATA"]).normalize()\n'''
new_loop = '''        forte, moderado = _eh_generico(hist)\n        data = pd.Timestamp(mov["DATA"]).normalize()\n\n        # Para SISPAG, comprovantes bancários são a evidência mais forte.\n        # Se beneficiários do mesmo dia fecharem exatamente o total do extrato,\n        # substitui o consolidado antes de consultar a Jaguar.\n        eh_sispag = "SISPAG" in _norm(hist) or "SALAR" in _norm(hist) or "FOLHA" in _norm(hist)\n        if eh_sispag and not comprovantes.empty:\n            comp_disp = comprovantes.loc[~comprovantes.index.isin(usados_comprovantes)].copy()\n            comp_dia = comp_disp[comp_disp["DATA"].dt.normalize() == data].copy()\n            if valor < 0:\n                comp_dia = comp_dia[comp_dia["VALOR"] < 0]\n            elif valor > 0:\n                comp_dia = comp_dia[comp_dia["VALOR"] > 0]\n            grupo_comp = _subset_exato(comp_dia, valor, hist, limite=80)\n            if grupo_comp is not None and len(grupo_comp) >= 2:\n                for cidx, det in grupo_comp.iterrows():\n                    novo = mov.to_dict()\n                    novo["DATA"] = pd.Timestamp(det["DATA"])\n                    novo["VALOR"] = float(det["VALOR"])\n                    novo["HISTÓRICO"] = str(det["HISTÓRICO"])\n                    novo["DESCRIÇÃO"] = mov.get("DESCRIÇÃO", banco)\n                    saida.append(novo)\n                    usados_comprovantes.add(cidx)\n                    detalhes.append({\n                        "BANCO": banco, "DATA BANCO": data, "HISTÓRICO BANCO": hist,\n                        "VALOR BANCO": valor, "DATA DETALHE": det["DATA"],\n                        "HISTÓRICO DETALHE": det["HISTÓRICO"], "VALOR DETALHE": det["VALOR"],\n                        "STATUS": "Identificado - comprovante SISPAG",\n                        "FONTE": "Comprovante SISPAG",\n                    })\n                continue\n\n        if not (forte or moderado) or jaguar.empty:\n            saida.append(mov.to_dict())\n            continue\n\n'''
if anchor_loop not in s:
    raise SystemExit('Loop anchor not found')
s = s.replace(anchor_loop, new_loop, 1)

# Add FONTE to Jaguar detail for transparency.
s = s.replace('''                    "STATUS": "Identificado - desmembrado",\n                })''', '''                    "STATUS": "Identificado - desmembrado",\n                    "FONTE": "Planilha Jaguar",\n                })''', 1)
radani_path.write_text(s, encoding='utf-8')

# App integration
app_path = Path('app.py')
app = app_path.read_text(encoding='utf-8')
app = app.replace(
    'from razync.radani import analisar_desmembramentos, consolidar_jaguares\n',
    'from razync.radani import analisar_desmembramentos, consolidar_jaguares, consolidar_comprovantes_sispag\n',
    1,
)
app = app.replace('"contas_bancarias": {"itau": "", "bradesco": ""},', '"contas_bancarias": {"itau": "508", "bradesco": "9"},', 1)
app = app.replace(
    '''        with aba_base_radani:\n            st.info(\n                'A Base Inteligente da 968 é isolada das demais empresas. '\n                'As contas bancárias do Domínio ainda não foram informadas; '\n                'o aprendizado de contrapartidas funciona normalmente, mas a conta do banco '\n                'só será preenchida automaticamente depois da configuração.'\n            )\n            renderizar_base_inteligente_empresa(''',
    '''        with aba_base_radani:\n            st.caption('Base exclusiva da 968 · Itaú conta 508 · Bradesco conta 9.')\n            renderizar_base_inteligente_empresa(''',
    1,
)

jaguar_block = '''            jaguares_radani = st.file_uploader(\n                'Planilhas auxiliares Jaguar',\n                type=['xlsx', 'xls'],\n                accept_multiple_files=True,\n                key='radani_jaguares',\n                help='Pode enviar arquivos Jaguar do ano e lançamentos diversos. O Razync usa somente o período dos extratos.'\n            )\n\n'''
proof_uploader = jaguar_block + '''            comprovantes_sispag_radani = st.file_uploader(\n                'Comprovantes de salários / SISPAG',\n                type=['pdf'],\n                accept_multiple_files=True,\n                key='radani_comprovantes_sispag',\n                help='Opcional, mas recomendado. Nome, valor e data dos comprovantes têm prioridade para detalhar SISPAG quando fecham o total do extrato.'\n            )\n\n'''
if 'radani_comprovantes_sispag' not in app:
    if jaguar_block not in app:
        raise SystemExit('Jaguar uploader anchor not found')
    app = app.replace(jaguar_block, proof_uploader, 1)

analysis_old = '''                    jaguar_periodo_radani = consolidar_jaguares(\n                        arquivos_jaguar_radani, inicio_radani, fim_radani\n                    )\n                    analise_radani = analisar_desmembramentos(\n                        df_extrato_radani, jaguar_periodo_radani, nome_banco_radani\n                    )\n'''
analysis_new = '''                    jaguar_periodo_radani = consolidar_jaguares(\n                        arquivos_jaguar_radani, inicio_radani, fim_radani\n                    )\n                    arquivos_comprovantes_radani = [\n                        (arq.name, arq.getvalue()) for arq in (comprovantes_sispag_radani or [])\n                    ]\n                    comprovantes_periodo_radani = consolidar_comprovantes_sispag(\n                        arquivos_comprovantes_radani, inicio_radani, fim_radani\n                    )\n                    analise_radani = analisar_desmembramentos(\n                        df_extrato_radani,\n                        jaguar_periodo_radani,\n                        nome_banco_radani,\n                        comprovantes=comprovantes_periodo_radani,\n                    )\n'''
if analysis_old not in app:
    raise SystemExit('Analysis call anchor not found')
app = app.replace(analysis_old, analysis_new, 1)
app_path.write_text(app, encoding='utf-8')

# Tests
p = Path('tests/test_radani.py')
t = p.read_text(encoding='utf-8')
t = t.replace('from razync.radani import analisar_desmembramentos\n', 'from razync.radani import analisar_desmembramentos\n', 1)
if 'test_comprovantes_sispag_tem_prioridade' not in t:
    t += '''\n\ndef test_comprovantes_sispag_tem_prioridade():\n    comprovantes = pd.DataFrame([\n        {'DATA': pd.Timestamp('2026-06-15'), 'HISTÓRICO': 'FUNC A VALE', 'VALOR': -20000.0, 'ARQUIVO': 'C', 'TIPO': 'VALE', 'FONTE': 'Comprovante SISPAG'},\n        {'DATA': pd.Timestamp('2026-06-15'), 'HISTÓRICO': 'FUNC B VALE', 'VALOR': -13000.0, 'ARQUIVO': 'C', 'TIPO': 'VALE', 'FONTE': 'Comprovante SISPAG'},\n    ])\n    jaguar = pd.DataFrame([\n        {'DATA': pd.Timestamp('2026-06-15'), 'HISTÓRICO': 'OUTRO A VALE', 'VALOR': -18000.0, 'ARQUIVO': 'J', 'ABA': 'Junho'},\n        {'DATA': pd.Timestamp('2026-06-15'), 'HISTÓRICO': 'OUTRO B VALE', 'VALOR': -15000.0, 'ARQUIVO': 'J', 'ABA': 'Junho'},\n    ])\n    res = analisar_desmembramentos(_extrato(), jaguar, 'Itaú', comprovantes=comprovantes)\n    assert set(res.organizado['HISTÓRICO']) == {'FUNC A VALE', 'FUNC B VALE'}\n    assert set(res.detalhamentos['FONTE']) == {'Comprovante SISPAG'}\n    assert res.revisoes.empty\n'''
p.write_text(t, encoding='utf-8')
