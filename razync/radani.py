"""Processamento inteligente da empresa 968 - Radani.

O extrato bancário é a fonte oficial do período e dos totais. Somente os comprovantes
de pagamento de salários do Itaú podem detalhar SISPAG, sempre com fechamento exato.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import itertools
import re
import unicodedata

import pandas as pd
from pypdf import PdfReader


GENERICOS_FORTES = (
    "SISPAG", "SALARIO", "SALARIOS", "FOLHA", "PAGAMENTO EM LOTE",
    "PAGTO EM LOTE", "PAGAMENTO FUNCIONARIOS", "PAGTO FUNCIONARIOS",
)
GENERICOS_MODERADOS = (
    "PAGAMENTO", "PAGTO", "DEBITO", "TRANSFERENCIA", "TRANSF",
    "TRIBUTO", "IMPOSTO", "COBRANCA", "DIVERSOS", "OUTROS",
)
PALAVRAS_RH = (
    "VALE", "SALARIO", "SALARIOS", "FERIAS", "RESCISAO", "13 SALARIO",
    "DECIMO TERCEIRO", "ADIANTAMENTO", "PENSAO", "FUNCIONARIO",
)


def _norm(txt) -> str:
    txt = "" if txt is None else str(txt)
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", txt).strip().upper()


def _valor_num(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("R$", "").replace(" ", "")
    neg = s.startswith("-") or (s.startswith("(") and s.endswith(")"))
    s = s.strip("()-+")
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        n = float(s)
        return -abs(n) if neg else n
    except ValueError:
        return None


def _achar_cabecalho(df_raw: pd.DataFrame):
    for i in range(min(len(df_raw), 35)):
        vals = [_norm(v) for v in df_raw.iloc[i].tolist()]
        tem_data = any(v in {"DATA", "DT", "DATE"} or v.startswith("DATA ") for v in vals)
        tem_hist = any(any(k in v for k in ("HIST", "LANC", "DESCR", "NOME", "FAVOREC", "COMPLEMENT")) for v in vals)
        tem_val = any(any(k in v for k in ("VALOR", "DEBITO", "CREDITO", "SAIDA", "ENTRADA")) for v in vals)
        if tem_data and tem_hist and tem_val:
            return i, vals
    return None, None


def _indice_coluna(headers, termos):
    for idx, h in enumerate(headers):
        if any(t in h for t in termos):
            return idx
    return None


def ler_jaguar(arquivo_bytes: bytes, nome_arquivo: str = "Jaguar") -> pd.DataFrame:
    """Lê layouts Jaguar heterogêneos procurando cabeçalhos semanticamente."""
    xls = pd.ExcelFile(BytesIO(arquivo_bytes))
    partes = []
    for aba in xls.sheet_names:
        raw = pd.read_excel(xls, sheet_name=aba, header=None, dtype=object)
        cab, headers = _achar_cabecalho(raw)
        if cab is None:
            continue
        idx_data = _indice_coluna(headers, ("DATA", "DT"))
        idx_hist = _indice_coluna(headers, ("HIST", "LANC", "DESCR", "NOME", "FAVOREC", "COMPLEMENT"))
        idx_valor = _indice_coluna(headers, ("VALOR",))
        idx_debito = _indice_coluna(headers, ("DEBITO", "SAIDA"))
        idx_credito = _indice_coluna(headers, ("CREDITO", "ENTRADA"))
        if idx_data is None or idx_hist is None or (idx_valor is None and idx_debito is None and idx_credito is None):
            continue
        corpo = raw.iloc[cab + 1:].copy()
        datas = pd.to_datetime(corpo.iloc[:, idx_data], dayfirst=True, errors="coerce")
        historicos = corpo.iloc[:, idx_hist].fillna("").astype(str).str.strip()
        valores = []
        for _, row in corpo.iterrows():
            if idx_valor is not None:
                valor = _valor_num(row.iloc[idx_valor])
            else:
                deb = _valor_num(row.iloc[idx_debito]) if idx_debito is not None else None
                cred = _valor_num(row.iloc[idx_credito]) if idx_credito is not None else None
                if cred not in (None, 0):
                    valor = abs(cred)
                elif deb not in (None, 0):
                    valor = -abs(deb)
                else:
                    valor = None
            valores.append(valor)
        parte = pd.DataFrame({
            "DATA": datas,
            "HISTÓRICO": historicos,
            "VALOR": valores,
            "ARQUIVO": nome_arquivo,
            "ABA": aba,
        })
        parte = parte.dropna(subset=["DATA", "VALOR"])
        parte = parte[parte["HISTÓRICO"].str.strip() != ""]
        parte = parte[parte["VALOR"].abs() > 0.004]
        partes.append(parte)
    if not partes:
        return pd.DataFrame(columns=["DATA", "HISTÓRICO", "VALOR", "ARQUIVO", "ABA"])
    return pd.concat(partes, ignore_index=True).sort_values("DATA", kind="stable").reset_index(drop=True)


def ler_comprovantes_sispag_pdf(arquivo_bytes: bytes, nome_arquivo: str = "Comprovantes SISPAG") -> pd.DataFrame:
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


def consolidar_jaguares(arquivos: list[tuple[str, bytes]], inicio, fim) -> pd.DataFrame:
    partes = []
    for nome, conteudo in arquivos:
        try:
            df = ler_jaguar(conteudo, nome)
            if not df.empty:
                partes.append(df)
        except Exception:
            continue
    if not partes:
        return pd.DataFrame(columns=["DATA", "HISTÓRICO", "VALOR", "ARQUIVO", "ABA"])
    df = pd.concat(partes, ignore_index=True)
    ini = pd.Timestamp(inicio).normalize()
    final = pd.Timestamp(fim).normalize()
    return df[(df["DATA"].dt.normalize() >= ini) & (df["DATA"].dt.normalize() <= final)].reset_index(drop=True)


def _eh_generico(hist: str) -> tuple[bool, bool]:
    h = _norm(hist)
    forte = any(k in h for k in GENERICOS_FORTES)
    moderado = forte or any(k in h for k in GENERICOS_MODERADOS)
    # Históricos com CPF/CNPJ ou nome longo tendem a já estar individualizados.
    tem_documento = bool(re.search(r"\d{3}[.\s]?\d{3}[.\s]?\d{3}|\d{2}[.\s]?\d{3}[.\s]?\d{3}", h))
    return forte, bool(moderado and not tem_documento)


def _score_item(hist_banco: str, hist_jaguar: str) -> int:
    hb, hj = _norm(hist_banco), _norm(hist_jaguar)
    score = 0
    if "SISPAG" in hb or "SALAR" in hb or "FOLHA" in hb:
        if any(k in hj for k in PALAVRAS_RH):
            score += 5
    tokens_b = {t for t in hb.split() if len(t) >= 4}
    tokens_j = {t for t in hj.split() if len(t) >= 4}
    score += min(4, len(tokens_b & tokens_j))
    return score


def _subset_exato(candidatos: pd.DataFrame, alvo_abs: float, hist_banco: str, limite=24):
    """Busca uma composição exata em centavos, privilegiando contexto sem explodir custo."""
    if candidatos.empty:
        return None
    cand = candidatos.copy()
    cand["ABS_CENTS"] = (cand["VALOR"].abs() * 100).round().astype(int)
    alvo = int(round(abs(alvo_abs) * 100))
    cand = cand[(cand["ABS_CENTS"] > 0) & (cand["ABS_CENTS"] <= alvo)]
    if len(cand) < 2:
        return None
    cand["SCORE"] = cand["HISTÓRICO"].map(lambda h: _score_item(hist_banco, h))
    cand = cand.sort_values(["SCORE", "DATA"], ascending=[False, True], kind="stable").head(limite)
    rows = list(cand.index)
    # DP: soma -> lista de índices. Mantém a primeira composição e limita estados ao alvo.
    dp = {0: []}
    for idx in rows:
        cents = int(cand.at[idx, "ABS_CENTS"])
        novos = {}
        for soma, usados in list(dp.items()):
            ns = soma + cents
            if ns > alvo or ns in dp or ns in novos:
                continue
            novos[ns] = usados + [idx]
        dp.update(novos)
        if alvo in dp and len(dp[alvo]) >= 2:
            return cand.loc[dp[alvo]].copy()
        if len(dp) > 120000:
            break
    return None


@dataclass
class AnaliseRadani:
    organizado: pd.DataFrame
    revisoes: pd.DataFrame
    detalhamentos: pd.DataFrame


def analisar_desmembramentos(extrato: pd.DataFrame, banco: str, comprovantes: pd.DataFrame | None = None) -> AnaliseRadani:
    """Usa comprovantes somente para SISPAG do Itaú; demais movimentos ficam como no extrato."""
    if extrato is None or extrato.empty:
        vazio = pd.DataFrame()
        return AnaliseRadani(vazio, vazio, vazio)

    df = extrato.copy()
    df["DATA"] = pd.to_datetime(df["DATA"], dayfirst=True, errors="coerce")
    df["VALOR"] = pd.to_numeric(df["VALOR"], errors="coerce")
    df["HISTÓRICO"] = df.get("HISTÓRICO", "").fillna("").astype(str)
    df = df.dropna(subset=["DATA", "VALOR"]).reset_index(drop=True)
    if comprovantes is None:
        comprovantes = pd.DataFrame()

    banco_itau = "ITAU" in _norm(banco)
    usados_comprovantes = set()
    saida = []
    revisoes = []
    detalhes = []

    for _, mov in df.iterrows():
        hist = str(mov["HISTÓRICO"])
        valor = float(mov["VALOR"])
        data = pd.Timestamp(mov["DATA"]).normalize()
        eh_sispag = "SISPAG" in _norm(hist) or "SALAR" in _norm(hist) or "FOLHA" in _norm(hist)

        if banco_itau and eh_sispag and not comprovantes.empty:
            comp_disp = comprovantes.loc[~comprovantes.index.isin(usados_comprovantes)].copy()
            comp_dia = comp_disp[comp_disp["DATA"].dt.normalize() == data].copy()
            if valor < 0:
                comp_dia = comp_dia[comp_dia["VALOR"] < 0]
            elif valor > 0:
                comp_dia = comp_dia[comp_dia["VALOR"] > 0]
            grupo_comp = _subset_exato(comp_dia, valor, hist, limite=80)
            if grupo_comp is not None and len(grupo_comp) >= 2:
                for cidx, det in grupo_comp.iterrows():
                    novo = mov.to_dict()
                    # A data bancária é a referência oficial do Modelo Domínio.
                    novo["DATA"] = pd.Timestamp(mov["DATA"])
                    novo["VALOR"] = float(det["VALOR"])
                    novo["HISTÓRICO"] = str(det["HISTÓRICO"])
                    novo["DESCRIÇÃO"] = mov.get("DESCRIÇÃO", banco)
                    saida.append(novo)
                    usados_comprovantes.add(cidx)
                    detalhes.append({
                        "BANCO": banco, "DATA BANCO": data, "HISTÓRICO BANCO": hist,
                        "VALOR BANCO": valor, "DATA DETALHE": det["DATA"],
                        "HISTÓRICO DETALHE": det["HISTÓRICO"], "VALOR DETALHE": det["VALOR"],
                        "STATUS": "Identificado - comprovante SISPAG",
                        "FONTE": "Comprovante SISPAG",
                    })
                continue

            revisoes.append({
                "BANCO": banco, "DATA": data, "HISTÓRICO": hist, "VALOR": valor,
                "TOTAL ENCONTRADO": None, "ITENS": int(len(comp_dia)),
                "DETALHES": "",
                "STATUS": "SISPAG sem fechamento exato nos comprovantes",
            })

        # Bradesco nunca usa comprovantes de salário; qualquer outro lançamento
        # permanece exatamente como veio do extrato.
        saida.append(mov.to_dict())

    organizado = pd.DataFrame(saida)
    if not organizado.empty:
        organizado = organizado.sort_values("DATA", kind="stable").reset_index(drop=True)
    return AnaliseRadani(
        organizado=organizado,
        revisoes=pd.DataFrame(revisoes),
        detalhamentos=pd.DataFrame(detalhes),
    )
