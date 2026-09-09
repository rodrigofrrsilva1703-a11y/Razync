"""Regras contábeis determinísticas da empresa 1000 — ACCEDE Automação."""

import re
import unicodedata

import pandas as pd


CONTAS_FOLHA_ACCEDE_1000 = {
    "ADTO": "25",
    "PGTO": "187",
    "REEM": "668",
}

_ALIASES_CODIGOS = {
    "ADTO": {"ADTO", "ADT0"},
    "PGTO": {"PGTO", "PGT0", "PAGTO"},
    "REEM": {"REEM", "REEN", "REEMB", "REMEB", "REEMBOLSO", "REMEBOLSO"},
}


def _normalizar(texto) -> str:
    valor = unicodedata.normalize("NFKD", str(texto or ""))
    valor = "".join(c for c in valor if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+", " ", valor.upper()).strip()


def identificar_conta_folha_accede_1000(historico) -> str:
    """Reconhece códigos e variações claras sem classificar palavras ambíguas."""
    texto = _normalizar(historico)
    tokens = set(texto.split())

    for codigo, aliases in _ALIASES_CODIGOS.items():
        if tokens.intersection(aliases):
            return CONTAS_FOLHA_ACCEDE_1000[codigo]

    if re.search(r"\bADIANT\w*\s+(?:DE\s+)?SALARI\w*\b", texto):
        return CONTAS_FOLHA_ACCEDE_1000["ADTO"]
    if re.search(r"\bPAG\w*\s+(?:DE\s+)?SALARI\w*\b", texto):
        return CONTAS_FOLHA_ACCEDE_1000["PGTO"]
    if re.search(r"\bREEMB\w*\b", texto):
        return CONTAS_FOLHA_ACCEDE_1000["REEM"]
    return ""


def aplicar_regras_accede_1000(
    df: pd.DataFrame, conta_bancaria: str
) -> pd.DataFrame:
    """Preenche banco e contrapartidas fixas sem sobrescrever contas existentes."""
    saida = df.copy()
    if saida.empty:
        return saida

    for indice, linha in saida.iterrows():
        valor = pd.to_numeric(linha.get("VALOR"), errors="coerce")
        if pd.isna(valor) or float(valor) == 0:
            continue

        if float(valor) < 0:
            if not str(linha.get("CRÉDITO") or "").strip():
                saida.at[indice, "CRÉDITO"] = conta_bancaria
            conta_folha = identificar_conta_folha_accede_1000(
                linha.get("HISTÓRICO", "")
            )
            if conta_folha and not str(linha.get("DÉBITO") or "").strip():
                saida.at[indice, "DÉBITO"] = conta_folha
        elif not str(linha.get("DÉBITO") or "").strip():
            saida.at[indice, "DÉBITO"] = conta_bancaria
    return saida
