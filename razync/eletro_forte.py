"""Processamento específico da empresa 242 - Eletro Forte.

Os relatórios recebidos usam extensão .xls, mas são tabelas HTML exportadas pelo
sistema do cliente. O módulo preserva DATA, DÉBITO, CRÉDITO, VALOR e HISTÓRICO
e separa os movimentos por conta bancária conforme a regra operacional.
"""
from __future__ import annotations

import html
import io
import re
from datetime import datetime
from typing import Dict

import pandas as pd


CONTAS_ELETRO_FORTE = {
    "8": "Banco BB · Conta 8",
    "508": "Itaú · 105318 · Conta 508",
    "509": "Itaú · 181537 · Conta 509",
    "0": "Revisar · Conta 0",
}


def _texto_celula(valor: str) -> str:
    valor = re.sub(r"<[^>]+>", " ", valor or "")
    return " ".join(html.unescape(valor).replace("\xa0", " ").split()).strip()


def _ler_tabela_html(conteudo: bytes) -> pd.DataFrame:
    texto = conteudo.decode("cp1252", errors="replace")
    linhas = re.findall(r"<tr[^>]*>(.*?)</tr>", texto, flags=re.I | re.S)
    matriz = []
    for linha in linhas:
        celulas = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", linha, flags=re.I | re.S)
        if celulas:
            matriz.append([_texto_celula(celula) for celula in celulas])
    if len(matriz) < 2:
        raise ValueError("Não foi possível localizar a tabela de lançamentos no arquivo.")
    cabecalho = [str(c).strip() for c in matriz[0]]
    largura = len(cabecalho)
    dados = [(linha + [""] * largura)[:largura] for linha in matriz[1:]]
    return pd.DataFrame(dados, columns=cabecalho)


def _norm_coluna(valor: str) -> str:
    texto = str(valor).upper()
    texto = texto.replace("É", "E").replace("Ê", "E").replace("Í", "I")
    texto = texto.replace("Ó", "O").replace("Ô", "O").replace("Á", "A").replace("Ã", "A")
    return re.sub(r"[^A-Z0-9]", "", texto)


def _valor_br(valor) -> float:
    texto = str(valor or "").strip().replace("R$", "").replace(" ", "")
    if not texto:
        return 0.0
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return 0.0


def _conta(valor) -> str:
    texto = str(valor or "").strip()
    texto = re.sub(r"\.0$", "", texto)
    texto = re.sub(r"\D", "", texto)
    return texto.lstrip("0") or "0"


def _data(valor, ano_referencia: int) -> pd.Timestamp:
    texto = str(valor or "").strip()
    if re.fullmatch(r"\d{1,2}/\d{1,2}", texto):
        texto = f"{texto}/{ano_referencia}"
    data = pd.to_datetime(texto, dayfirst=True, errors="coerce")
    return data


def _padronizar(conteudo: bytes, ano_referencia: int) -> pd.DataFrame:
    bruto = _ler_tabela_html(conteudo)
    mapa = {_norm_coluna(col): col for col in bruto.columns}
    col_data = mapa.get("DATA") or mapa.get("DATAPAGTO")
    col_debito = mapa.get("DEBITO")
    col_credito = mapa.get("CREDITO")
    col_valor = mapa.get("VALOR")
    col_historico = mapa.get("HISTORICO")
    faltantes = [nome for nome, col in {
        "DATA": col_data, "DÉBITO": col_debito, "CRÉDITO": col_credito,
        "VALOR": col_valor, "HISTÓRICO": col_historico,
    }.items() if not col]
    if faltantes:
        raise ValueError("Colunas obrigatórias não encontradas: " + ", ".join(faltantes))

    saida = pd.DataFrame({
        "DATA": bruto[col_data].map(lambda v: _data(v, ano_referencia)),
        "DÉBITO": bruto[col_debito].map(_conta),
        "CRÉDITO": bruto[col_credito].map(_conta),
        "VALOR": bruto[col_valor].map(_valor_br),
        "HISTÓRICO": bruto[col_historico].astype(str).str.strip(),
    })
    saida = saida.dropna(subset=["DATA"]).reset_index(drop=True)
    return saida


def processar_despesas(conteudo: bytes, ano_referencia: int) -> pd.DataFrame:
    """Despesa: 001 vira BB/8 e 002 vira Itaú/508 na coluna CRÉDITO."""
    df = _padronizar(conteudo, ano_referencia)
    # A normalização remove zeros à esquerda: 001 -> 1 e 002 -> 2.
    df["CRÉDITO"] = df["CRÉDITO"].replace({"1": "8", "2": "508"})
    return df[["DATA", "DÉBITO", "CRÉDITO", "VALOR", "HISTÓRICO"]]


def _separar_por_conta(df: pd.DataFrame, coluna_conta: str) -> Dict[str, pd.DataFrame]:
    resultado: Dict[str, pd.DataFrame] = {}
    ordem = ["8", "508", "509", "0"]
    contas_presentes = list(dict.fromkeys(df[coluna_conta].astype(str).tolist()))
    for conta in ordem + [c for c in contas_presentes if c not in ordem]:
        parte = df.loc[df[coluna_conta].astype(str) == conta].copy()
        if not parte.empty:
            resultado[conta] = parte.reset_index(drop=True)
    return resultado


def processar_fornecedores(conteudo: bytes, ano_referencia: int) -> Dict[str, pd.DataFrame]:
    """Fornecedor: separa pela conta presente na coluna CRÉDITO, incluindo zero."""
    df = _padronizar(conteudo, ano_referencia)
    return _separar_por_conta(df, "CRÉDITO")


def processar_recebidos(conteudo: bytes, ano_referencia: int) -> Dict[str, pd.DataFrame]:
    """Recebido: separa pela conta presente na coluna DÉBITO, incluindo zero."""
    df = _padronizar(conteudo, ano_referencia)
    return _separar_por_conta(df, "DÉBITO")


def inferir_ano_recebidos(conteudo: bytes) -> int | None:
    """Tenta obter o ano do relatório Recebidos, que normalmente traz data completa."""
    try:
        bruto = _ler_tabela_html(conteudo)
    except Exception:
        return None
    for valor in bruto.astype(str).to_numpy().ravel():
        achou = re.search(r"\b\d{1,2}/\d{1,2}/(20\d{2})\b", valor)
        if achou:
            return int(achou.group(1))
    return None


def _nome_aba(prefixo: str, conta: str) -> str:
    nomes = {
        "8": "BB 8",
        "508": "Itau 508",
        "509": "Itau 509",
        "0": "Revisar 0",
    }
    return f"{prefixo} - {nomes.get(conta, conta)}"[:31]


def gerar_modelo_dominio_eletro_forte(
    despesas: pd.DataFrame | None,
    fornecedores: Dict[str, pd.DataFrame] | None,
    recebidos: Dict[str, pd.DataFrame] | None,
) -> bytes:
    """Gera um único XLSX com abas independentes para cada origem/conta."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    wb.remove(wb.active)
    cabecalho = ["DATA", "DÉBITO", "CRÉDITO", "VALOR", "HISTÓRICO"]

    conjuntos = []
    if despesas is not None and not despesas.empty:
        conjuntos.append(("Despesas", despesas))
    for conta, df in (fornecedores or {}).items():
        conjuntos.append((_nome_aba("Fornecedor", conta), df))
    for conta, df in (recebidos or {}).items():
        conjuntos.append((_nome_aba("Recebido", conta), df))

    if not conjuntos:
        raise ValueError("Nenhum lançamento válido foi encontrado nos arquivos enviados.")

    for nome, df in conjuntos:
        ws = wb.create_sheet(nome)
        ws.append(cabecalho)
        for celula in ws[1]:
            celula.font = Font(bold=True, color="FFFFFF")
            celula.fill = PatternFill("solid", fgColor="17324D")
        for _, linha in df[cabecalho].iterrows():
            ws.append([
                linha["DATA"].to_pydatetime() if hasattr(linha["DATA"], "to_pydatetime") else linha["DATA"],
                int(linha["DÉBITO"]) if str(linha["DÉBITO"]).isdigit() else linha["DÉBITO"],
                int(linha["CRÉDITO"]) if str(linha["CRÉDITO"]).isdigit() else linha["CRÉDITO"],
                float(linha["VALOR"]),
                linha["HISTÓRICO"],
            ])
        for celula in ws["A"][1:]:
            celula.number_format = "dd/mm/yyyy"
        for celula in ws["D"][1:]:
            celula.number_format = '#,##0.00'
        ws.freeze_panes = "A2"
        ws.column_dimensions["A"].width = 13
        ws.column_dimensions["B"].width = 12
        ws.column_dimensions["C"].width = 12
        ws.column_dimensions["D"].width = 16
        ws.column_dimensions["E"].width = 58

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
