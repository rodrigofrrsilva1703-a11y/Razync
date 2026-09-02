"""Processamento inteligente da empresa 968 - Radani.

O extrato bancário é a fonte oficial do período e dos totais. As planilhas Jaguar
são usadas apenas para detalhar lançamentos consolidados quando a composição é
matematicamente consistente dentro do período processado.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import itertools
import re
import unicodedata

import pandas as pd


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


def analisar_desmembramentos(extrato: pd.DataFrame, jaguar: pd.DataFrame, banco: str) -> AnaliseRadani:
    """Desmembra somente correspondências fortes; demais candidatas ficam para revisão."""
    if extrato is None or extrato.empty:
        vazio = pd.DataFrame()
        return AnaliseRadani(vazio, vazio, vazio)
    df = extrato.copy()
    df["DATA"] = pd.to_datetime(df["DATA"], dayfirst=True, errors="coerce")
    df["VALOR"] = pd.to_numeric(df["VALOR"], errors="coerce")
    df["HISTÓRICO"] = df.get("HISTÓRICO", "").fillna("").astype(str)
    df = df.dropna(subset=["DATA", "VALOR"]).reset_index(drop=True)
    if jaguar is None:
        jaguar = pd.DataFrame()

    usados_jaguar = set()
    saida = []
    revisoes = []
    detalhes = []

    for idx, mov in df.iterrows():
        hist = str(mov["HISTÓRICO"])
        valor = float(mov["VALOR"])
        forte, moderado = _eh_generico(hist)
        if not (forte or moderado) or jaguar.empty:
            saida.append(mov.to_dict())
            continue

        data = pd.Timestamp(mov["DATA"]).normalize()
        disponiveis = jaguar.loc[~jaguar.index.isin(usados_jaguar)].copy()
        # Primeiro tenta o mesmo dia. Para SISPAG/RH dá peso extra a históricos típicos.
        mesmo_dia = disponiveis[disponiveis["DATA"].dt.normalize() == data].copy()
        if valor < 0:
            mesmo_dia = mesmo_dia[mesmo_dia["VALOR"] < 0]
        elif valor > 0:
            mesmo_dia = mesmo_dia[mesmo_dia["VALOR"] > 0]
        if forte and ("SISPAG" in _norm(hist) or "SALAR" in _norm(hist) or "FOLHA" in _norm(hist)):
            rh = mesmo_dia[mesmo_dia["HISTÓRICO"].map(lambda h: any(k in _norm(h) for k in PALAVRAS_RH))]
            grupo = _subset_exato(rh if len(rh) >= 2 else mesmo_dia, valor, hist)
        else:
            grupo = _subset_exato(mesmo_dia, valor, hist)

        if grupo is not None and len(grupo) >= 2:
            # Mesmo dia + fechamento exato = alta confiança. Substitui o consolidado.
            for jidx, det in grupo.iterrows():
                novo = mov.to_dict()
                novo["DATA"] = pd.Timestamp(det["DATA"])
                novo["VALOR"] = float(det["VALOR"])
                novo["HISTÓRICO"] = str(det["HISTÓRICO"])
                novo["DESCRIÇÃO"] = mov.get("DESCRIÇÃO", banco)
                saida.append(novo)
                usados_jaguar.add(jidx)
                detalhes.append({
                    "BANCO": banco, "DATA BANCO": data, "HISTÓRICO BANCO": hist,
                    "VALOR BANCO": valor, "DATA DETALHE": det["DATA"],
                    "HISTÓRICO DETALHE": det["HISTÓRICO"], "VALOR DETALHE": det["VALOR"],
                    "STATUS": "Identificado - desmembrado",
                })
            continue

        # Procura ±2 dias apenas para sugerir revisão, nunca para substituir automaticamente.
        janela = disponiveis[(disponiveis["DATA"].dt.normalize() >= data - pd.Timedelta(days=2)) &
                             (disponiveis["DATA"].dt.normalize() <= data + pd.Timedelta(days=2))].copy()
        if valor < 0:
            janela = janela[janela["VALOR"] < 0]
        elif valor > 0:
            janela = janela[janela["VALOR"] > 0]
        provavel = _subset_exato(janela, valor, hist)
        if provavel is not None and len(provavel) >= 2:
            revisoes.append({
                "BANCO": banco,
                "DATA": data,
                "HISTÓRICO": hist,
                "VALOR": valor,
                "TOTAL ENCONTRADO": float(provavel["VALOR"].sum()),
                "ITENS": len(provavel),
                "DETALHES": " | ".join(f"{r['HISTÓRICO']} ({r['VALOR']:.2f})" for _, r in provavel.iterrows()),
                "STATUS": "Provável - revisar",
            })
        elif forte or moderado:
            revisoes.append({
                "BANCO": banco, "DATA": data, "HISTÓRICO": hist, "VALOR": valor,
                "TOTAL ENCONTRADO": None, "ITENS": 0, "DETALHES": "",
                "STATUS": "Não identificado",
            })
        saida.append(mov.to_dict())

    organizado = pd.DataFrame(saida)
    if not organizado.empty:
        organizado = organizado.sort_values("DATA", kind="stable").reset_index(drop=True)
    return AnaliseRadani(
        organizado=organizado,
        revisoes=pd.DataFrame(revisoes),
        detalhamentos=pd.DataFrame(detalhes),
    )
