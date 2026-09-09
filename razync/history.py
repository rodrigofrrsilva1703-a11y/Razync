"""Padronização de históricos exportados para o Modelo Domínio."""

import re

import pandas as pd


_PREFIXO_MOVIMENTO = re.compile(r"^\s*(?:pago|recebido)\s*:\s*", re.IGNORECASE)


def prefixar_historico_movimento(historico, valor) -> str:
    """Aplica Pago:/Recebido: conforme o sinal, sem duplicar prefixos."""
    texto = "" if pd.isna(historico) else str(historico).strip()
    texto_sem_prefixo = _PREFIXO_MOVIMENTO.sub("", texto).strip()
    valor_numerico = pd.to_numeric(valor, errors="coerce")

    if pd.isna(valor_numerico) or float(valor_numerico) == 0:
        return texto
    prefixo = "Pago:" if float(valor_numerico) < 0 else "Recebido:"
    return f"{prefixo} {texto_sem_prefixo}".rstrip()


def padronizar_historicos_modelo(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna uma cópia com históricos padronizados somente para exportação."""
    saida = df.copy()
    if "HISTÓRICO" not in saida.columns or "VALOR" not in saida.columns:
        return saida
    saida["HISTÓRICO"] = [
        prefixar_historico_movimento(historico, valor)
        for historico, valor in zip(saida["HISTÓRICO"], saida["VALOR"])
    ]
    return saida
