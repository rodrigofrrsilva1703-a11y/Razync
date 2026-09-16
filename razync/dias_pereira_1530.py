"""Leitor do extrato Itaú da empresa 1530 - Dias Pereira."""

from __future__ import annotations

import io
import re
import unicodedata

import pandas as pd


CONTA_ITAU_1530 = "508"
COLUNAS_MODELO = ["DESCRIÇÃO", "DATA", "VALOR", "DÉBITO", "CRÉDITO", "HISTÓRICO"]


def _normalizar(valor) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().casefold()


def _texto(valor) -> str:
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return ""
    texto = str(valor).strip()
    try:
        texto = texto.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return re.sub(r"\s+", " ", texto).strip()


def _data(valor):
    if isinstance(valor, (int, float)) and not isinstance(valor, bool) and not pd.isna(valor):
        return pd.Timestamp("1899-12-30") + pd.to_timedelta(float(valor), unit="D")
    return pd.to_datetime(valor, dayfirst=True, errors="coerce")


def _valor(valor) -> float:
    if isinstance(valor, (int, float)) and not isinstance(valor, bool) and not pd.isna(valor):
        return round(float(valor), 2)
    texto = _texto(valor).replace("R$", "").replace(" ", "")
    if not texto:
        return 0.0
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return round(float(texto), 2)
    except ValueError:
        return 0.0


def _registro(data, valor: float, historico: str) -> dict:
    historico = _texto(historico)
    historico = re.sub(r"^(?:Pago|Recebido)\s*:\s*", "", historico, flags=re.I)
    prefixo = "Recebido: " if valor > 0 else "Pago: "
    return {
        "DESCRIÇÃO": "BANCO ITAÚ",
        "DATA": pd.Timestamp(data).normalize(),
        "VALOR": round(float(valor), 2),
        "DÉBITO": CONTA_ITAU_1530 if valor > 0 else "",
        "CRÉDITO": CONTA_ITAU_1530 if valor < 0 else "",
        "HISTÓRICO": prefixo + (historico or "MOVIMENTO BANCÁRIO"),
    }


def processar_extrato_itau_xls_1530(conteudo: bytes) -> pd.DataFrame:
    """Converte o extrato Itaú XLS/XLSX para o Modelo Domínio."""
    xls = pd.ExcelFile(io.BytesIO(conteudo))
    registros = []
    for aba in xls.sheet_names:
        bruto = pd.read_excel(xls, sheet_name=aba, header=None, dtype=object)
        cabecalho = None
        for indice in range(min(len(bruto), 40)):
            nomes = [_normalizar(v) for v in bruto.iloc[indice].tolist()]
            if "data" in nomes and any("lancamento" in n for n in nomes) and any("valor" in n for n in nomes):
                cabecalho = indice
                break
        if cabecalho is None:
            continue

        nomes = [_normalizar(v) for v in bruto.iloc[cabecalho].tolist()]
        col_data = nomes.index("data")
        col_hist = next(i for i, nome in enumerate(nomes) if "lancamento" in nome)
        col_valor = next(i for i, nome in enumerate(nomes) if "valor" in nome)

        for _, linha in bruto.iloc[cabecalho + 1 :].iterrows():
            data = _data(linha.iloc[col_data])
            historico = _texto(linha.iloc[col_hist])
            valor = _valor(linha.iloc[col_valor])
            hist_norm = _normalizar(historico)
            if pd.isna(data) or not historico or abs(valor) < 0.005:
                continue
            if "saldo anterior" in hist_norm or "saldo total" in hist_norm or hist_norm == "saldo":
                continue
            registros.append(_registro(data, valor, historico))

    if not registros:
        raise ValueError("Nenhum lançamento válido foi encontrado no extrato Itaú enviado.")
    return pd.DataFrame(registros, columns=COLUNAS_MODELO).sort_values(
        "DATA", kind="stable"
    ).reset_index(drop=True)


def normalizar_modelo_itau_1530(dados) -> pd.DataFrame:
    """Aplica conta 508 e o layout da empresa aos registros vindos do PDF."""
    df = pd.DataFrame(dados).copy()
    if df.empty:
        raise ValueError("Nenhum lançamento válido foi encontrado no extrato Itaú PDF.")
    df["DATA"] = pd.to_datetime(df.get("DATA"), dayfirst=True, errors="coerce")
    df["VALOR"] = pd.to_numeric(df.get("VALOR"), errors="coerce")
    df = df.dropna(subset=["DATA", "VALOR"])
    df = df[df["VALOR"].abs() >= 0.005].copy()
    registros = [
        _registro(linha["DATA"], linha["VALOR"], linha.get("HISTÓRICO", ""))
        for _, linha in df.iterrows()
    ]
    if not registros:
        raise ValueError("Nenhum lançamento válido foi encontrado no extrato Itaú PDF.")
    return pd.DataFrame(registros, columns=COLUNAS_MODELO).sort_values(
        "DATA", kind="stable"
    ).reset_index(drop=True)
