"""Banco Inter da empresa 841 - Lucrativite.

Lê extratos Excel e PDF do Banco Inter, monta lançamentos no padrão do Modelo Domínio
e gera uma conferência diária entre extrato e planilha organizada.
"""

from __future__ import annotations

import io
import re
import unicodedata

import pandas as pd
from pypdf import PdfReader

CONTA_INTER_841 = "506"
BANCO_INTER_841 = "BANCO INTER"
COLUNAS_MODELO = ["DESCRIÇÃO", "DATA", "VALOR", "DÉBITO", "CRÉDITO", "HISTÓRICO"]
MESES_PT = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def _corrigir_mojibake(texto: str) -> str:
    texto = str(texto or "")
    if any(marca in texto for marca in ("Ã", "Â", "â€")):
        try:
            texto = texto.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return texto


def _normalizar_texto(valor) -> str:
    texto = _corrigir_mojibake("" if valor is None else str(valor))
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", texto).strip().casefold()


def _converter_data(valor):
    if pd.isna(valor):
        return pd.NaT
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return pd.Timestamp("1899-12-30") + pd.to_timedelta(float(valor), unit="D")
    return pd.to_datetime(valor, dayfirst=True, errors="coerce")


def _converter_valor(valor) -> float:
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return round(float(valor), 2)
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return round(float(texto), 2)
    except ValueError:
        return 0.0


def _historico_inter(descricao: str, valor: float) -> str:
    descricao = re.sub(r"\s+", " ", str(descricao or "")).strip()
    if not descricao:
        descricao = "Movimento Banco Inter"
    prefixo = "Recebido: " if valor > 0 else "Pago: "
    descricao = re.sub(r"^(?:Recebido|Pago):\s*", "", descricao, flags=re.I)
    return prefixo + descricao


def _registro_inter(data, valor: float, descricao: str) -> dict:
    return {
        "DESCRIÇÃO": BANCO_INTER_841,
        "DATA": pd.Timestamp(data).normalize(),
        "VALOR": round(float(valor), 2),
        "DÉBITO": CONTA_INTER_841 if valor > 0 else "",
        "CRÉDITO": CONTA_INTER_841 if valor < 0 else "",
        "HISTÓRICO": _historico_inter(descricao, valor),
    }


def _localizar_tabela_excel(conteudo: bytes) -> pd.DataFrame:
    if not conteudo:
        raise ValueError("O arquivo do Banco Inter está vazio.")

    planilhas = pd.read_excel(io.BytesIO(conteudo), sheet_name=None, header=None)
    for _, bruto in planilhas.items():
        if bruto is None or bruto.empty:
            continue
        limite = min(len(bruto), 30)
        for indice in range(limite):
            linha = [_normalizar_texto(v) for v in bruto.iloc[indice].tolist()]
            tem_data = any(v in {"data lancamento", "data"} for v in linha)
            tem_descricao = any("descricao" == v or "historico" == v for v in linha)
            tem_valor = any(v == "valor" for v in linha)
            if tem_data and tem_descricao and tem_valor:
                tabela = bruto.iloc[indice + 1 :].copy()
                tabela.columns = bruto.iloc[indice].tolist()
                tabela = tabela.dropna(how="all")
                return tabela.reset_index(drop=True)

    raise ValueError(
        "Não encontrei a tabela do extrato Banco Inter. "
        "O arquivo precisa conter Data Lançamento, Descrição e Valor."
    )


def processar_extrato_inter_841(conteudo: bytes) -> pd.DataFrame:
    tabela = _localizar_tabela_excel(conteudo)

    mapa = {}
    for coluna in tabela.columns:
        normal = _normalizar_texto(coluna)
        if normal in {"data lancamento", "data"} and "data" not in mapa:
            mapa["data"] = coluna
        elif normal in {"descricao", "historico"} and "descricao" not in mapa:
            mapa["descricao"] = coluna
        elif normal == "valor" and "valor" not in mapa:
            mapa["valor"] = coluna

    faltantes = [campo for campo in ("data", "descricao", "valor") if campo not in mapa]
    if faltantes:
        raise ValueError("Colunas obrigatórias não reconhecidas: " + ", ".join(faltantes))

    registros = []
    for _, item in tabela.iterrows():
        data = _converter_data(item.get(mapa["data"]))
        valor = _converter_valor(item.get(mapa["valor"]))
        descricao = "" if pd.isna(item.get(mapa["descricao"])) else _corrigir_mojibake(str(item.get(mapa["descricao"]))).strip()

        if pd.isna(data) or abs(valor) < 0.005:
            continue
        registros.append(_registro_inter(data, valor, descricao))

    if not registros:
        raise ValueError("Nenhum lançamento válido foi encontrado no extrato Banco Inter.")

    return pd.DataFrame(registros, columns=COLUNAS_MODELO).sort_values(
        ["DATA"], kind="stable"
    ).reset_index(drop=True)


def _valor_pdf_inter(texto: str) -> float:
    texto = str(texto or "").strip()
    negativo = texto.startswith("-")
    numero = texto.replace("-", "").replace("R$", "").replace(" ", "")
    numero = numero.replace(".", "").replace(",", ".")
    valor = float(numero)
    return round(-valor if negativo else valor, 2)


def processar_extrato_inter_pdf_841(conteudo: bytes) -> pd.DataFrame:
    """Lê o extrato PDF visual do Banco Inter, como o PDF emitido pelo internet banking."""
    if not conteudo:
        raise ValueError("O PDF do Banco Inter está vazio.")

    try:
        leitor = PdfReader(io.BytesIO(conteudo))
    except Exception as erro:
        raise ValueError(f"Não foi possível abrir o PDF do Banco Inter: {erro}") from erro

    data_atual = None
    registros = []
    padrao_data = re.compile(
        r"(\d{1,2})\s+de\s+([A-Za-zÀ-ÿ]+)\s+de\s+(\d{4})\s+Saldo do dia:",
        flags=re.I,
    )
    padrao_valor = re.compile(r"-?R\$\s*\d{1,3}(?:\.\d{3})*,\d{2}")

    for pagina in leitor.pages:
        texto = pagina.extract_text() or ""
        for linha_bruta in texto.splitlines():
            linha = re.sub(r"\s+", " ", linha_bruta.replace("\xa0", " ")).strip()
            if not linha:
                continue

            achou_data = padrao_data.search(linha)
            if achou_data:
                mes = MESES_PT.get(_normalizar_texto(achou_data.group(2)))
                if mes:
                    data_atual = pd.Timestamp(
                        year=int(achou_data.group(3)),
                        month=mes,
                        day=int(achou_data.group(1)),
                    )
                continue

            if data_atual is None:
                continue
            if linha.startswith((
                "Fale com a gente",
                "SAC:",
                "Solicitado em:",
                "Saldo total",
                "Saldo disponível",
                "Saldo bloqueado",
                "Valor Saldo por transação",
            )):
                continue

            valores = padrao_valor.findall(linha)
            # Cada transação do PDF possui o valor do movimento e o saldo após a transação.
            if len(valores) < 2:
                continue

            posicao_valor = linha.find(valores[0])
            descricao = linha[:posicao_valor].strip()
            if not descricao:
                continue

            valor = _valor_pdf_inter(valores[0])
            if abs(valor) < 0.005:
                continue
            registros.append(_registro_inter(data_atual, valor, descricao))

    if not registros:
        raise ValueError(
            "Nenhum lançamento foi reconhecido no PDF. Use o extrato PDF detalhado do Banco Inter, "
            "com data, descrição, valor e saldo por transação."
        )

    return pd.DataFrame(registros, columns=COLUNAS_MODELO).sort_values(
        ["DATA"], kind="stable"
    ).reset_index(drop=True)


def processar_extrato_inter_conferencia_841(conteudo: bytes, nome_arquivo: str = "") -> pd.DataFrame:
    """Aceita Excel ou PDF no card de extrato da conferência."""
    nome = str(nome_arquivo or "").lower().strip()
    if nome.endswith(".pdf") or conteudo[:5] == b"%PDF-":
        return processar_extrato_inter_pdf_841(conteudo)
    return processar_extrato_inter_841(conteudo)


def ler_modelo_para_conferencia(conteudo: bytes) -> pd.DataFrame:
    """Lê Modelo Domínio ou planilha final e extrai Data/Valor/Débito/Crédito."""
    if not conteudo:
        raise ValueError("A planilha para conferência está vazia.")

    planilhas = pd.read_excel(io.BytesIO(conteudo), sheet_name=None, header=None)
    candidatos = []
    for nome, bruto in planilhas.items():
        if bruto is None or bruto.empty:
            continue
        for indice in range(min(len(bruto), 40)):
            linha = [_normalizar_texto(v) for v in bruto.iloc[indice].tolist()]
            if "data" in linha and "valor" in linha:
                tabela = bruto.iloc[indice + 1 :].copy()
                tabela.columns = bruto.iloc[indice].tolist()
                tabela = tabela.dropna(how="all")
                candidatos.append((nome, tabela))
                break

    if not candidatos:
        raise ValueError("Não encontrei as colunas DATA e VALOR na planilha de conferência.")

    partes = []
    for _, tabela in candidatos:
        mapa = {}
        for coluna in tabela.columns:
            normal = _normalizar_texto(coluna)
            if normal == "data" and "data" not in mapa:
                mapa["data"] = coluna
            elif normal == "valor" and "valor" not in mapa:
                mapa["valor"] = coluna
            elif normal in {"debito", "deb"} and "debito" not in mapa:
                mapa["debito"] = coluna
            elif normal in {"credito", "cred"} and "credito" not in mapa:
                mapa["credito"] = coluna

        if "data" not in mapa or "valor" not in mapa:
            continue

        for _, item in tabela.iterrows():
            data = _converter_data(item.get(mapa["data"]))
            valor = _converter_valor(item.get(mapa["valor"]))
            if pd.isna(data) or abs(valor) < 0.005:
                continue
            debito = str(item.get(mapa.get("debito"), "") or "").strip()
            credito = str(item.get(mapa.get("credito"), "") or "").strip()

            if debito and CONTA_INTER_841 in re.findall(r"\d+", debito):
                valor = abs(valor)
            elif credito and CONTA_INTER_841 in re.findall(r"\d+", credito):
                valor = -abs(valor)

            partes.append(
                {
                    "DATA": pd.Timestamp(data).normalize(),
                    "VALOR": round(float(valor), 2),
                    "DÉBITO": debito,
                    "CRÉDITO": credito,
                }
            )

    if not partes:
        raise ValueError("Nenhum lançamento válido foi reconhecido na planilha final.")
    return pd.DataFrame(partes)


def conferir_extrato_modelo(extrato: pd.DataFrame, modelo: pd.DataFrame):
    """Compara entradas e saídas por dia e retorna detalhe e resumo."""
    ext = extrato[["DATA", "VALOR"]].copy()
    mod = modelo[["DATA", "VALOR"]].copy()
    ext["DATA"] = pd.to_datetime(ext["DATA"]).dt.normalize()
    mod["DATA"] = pd.to_datetime(mod["DATA"]).dt.normalize()

    def _resumir(df, prefixo):
        agrupado = (
            df.assign(
                ENTRADAS=df["VALOR"].where(df["VALOR"] > 0, 0.0),
                SAIDAS=(-df["VALOR"].where(df["VALOR"] < 0, 0.0)),
            )
            .groupby("DATA", as_index=False)
            .agg(
                **{
                    f"{prefixo} ENTRADAS": ("ENTRADAS", "sum"),
                    f"{prefixo} SAÍDAS": ("SAIDAS", "sum"),
                    f"{prefixo} QTD": ("VALOR", "size"),
                }
            )
        )
        return agrupado

    diario = _resumir(ext, "EXTRATO").merge(
        _resumir(mod, "MODELO"), on="DATA", how="outer"
    ).fillna(0)
    diario["DIF. ENTRADAS"] = diario["MODELO ENTRADAS"] - diario["EXTRATO ENTRADAS"]
    diario["DIF. SAÍDAS"] = diario["MODELO SAÍDAS"] - diario["EXTRATO SAÍDAS"]
    diario["STATUS"] = diario.apply(
        lambda r: "✅ Batendo"
        if abs(r["DIF. ENTRADAS"]) < 0.01 and abs(r["DIF. SAÍDAS"]) < 0.01
        else "❌ Divergente",
        axis=1,
    )
    diario = diario.sort_values("DATA").reset_index(drop=True)

    entradas_ext = float(ext.loc[ext["VALOR"] > 0, "VALOR"].sum())
    saidas_ext = float(-ext.loc[ext["VALOR"] < 0, "VALOR"].sum())
    entradas_mod = float(mod.loc[mod["VALOR"] > 0, "VALOR"].sum())
    saidas_mod = float(-mod.loc[mod["VALOR"] < 0, "VALOR"].sum())
    resumo = {
        "qtd_extrato": len(ext),
        "qtd_modelo": len(mod),
        "entradas_extrato": round(entradas_ext, 2),
        "saidas_extrato": round(saidas_ext, 2),
        "entradas_modelo": round(entradas_mod, 2),
        "saidas_modelo": round(saidas_mod, 2),
        "diferenca_entradas": round(entradas_mod - entradas_ext, 2),
        "diferenca_saidas": round(saidas_mod - saidas_ext, 2),
        "dias_divergentes": int((diario["STATUS"] != "✅ Batendo").sum()),
    }
    return diario, resumo
