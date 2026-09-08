"""Organização bancária da empresa 1402 - VGV Empreendimentos."""
from __future__ import annotations

import io
import re
import shutil
import subprocess
import tempfile
import unicodedata
from collections import defaultdict

import pandas as pd


CONTA_BTG_VGV = "510"
COLUNAS_MODELO = ["DESCRIÇÃO", "DATA", "VALOR", "DÉBITO", "CRÉDITO", "HISTÓRICO"]


def _normalizar(valor) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    return re.sub(r"[^A-Z0-9]", "", texto.encode("ascii", "ignore").decode().upper())


def _valor_monetario(valor) -> float:
    if valor is None or pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if not texto:
        return 0.0
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return 0.0


def ler_caixa_vgv(conteudo: bytes) -> pd.DataFrame:
    """Lê o caixa detalhado, ignorando linhas usadas somente para saldo."""
    bruto = pd.read_excel(io.BytesIO(conteudo), sheet_name=0, header=None, dtype=object)
    linha_cabecalho = None
    mapa = {}
    for indice in range(min(30, len(bruto))):
        atual = {_normalizar(v): coluna for coluna, v in enumerate(bruto.iloc[indice])}
        if {"DATA", "ENTRADA", "SAIDA", "HISTORICO"}.issubset(atual):
            linha_cabecalho, mapa = indice, atual
            break
    if linha_cabecalho is None:
        raise ValueError(
            "Não foram encontradas as colunas DATA, ENTRADA, SAÍDA e HISTÓRICO."
        )

    registros = []
    for _, linha in bruto.iloc[linha_cabecalho + 1:].iterrows():
        data = pd.to_datetime(linha.iloc[mapa["DATA"]], dayfirst=True, errors="coerce")
        entrada = abs(_valor_monetario(linha.iloc[mapa["ENTRADA"]]))
        saida = abs(_valor_monetario(linha.iloc[mapa["SAIDA"]]))
        historico = str(linha.iloc[mapa["HISTORICO"]] or "").strip()
        if pd.isna(data) or not historico or historico.lower() == "nan":
            continue
        if entrada and saida:
            raise ValueError(
                f"A linha de {data.strftime('%d/%m/%Y')} possui entrada e saída ao mesmo tempo."
            )
        if not entrada and not saida:
            continue
        valor = round(entrada if entrada else -saida, 2)
        prefixo = "Recebido: " if valor > 0 else "Pago: "
        if not historico.lower().startswith(("recebido: ", "pago: ")):
            historico = prefixo + historico
        registros.append({
            "DESCRIÇÃO": "BANCO BTG",
            "DATA": data.normalize(),
            "VALOR": valor,
            "DÉBITO": CONTA_BTG_VGV if valor > 0 else "",
            "CRÉDITO": CONTA_BTG_VGV if valor < 0 else "",
            "HISTÓRICO": historico,
        })
    if not registros:
        raise ValueError("Nenhum movimento foi encontrado na planilha Caixa VGV.")
    return pd.DataFrame(registros, columns=COLUNAS_MODELO)


def _ocr_paginas(conteudo: bytes):
    """Renderiza o PDF e devolve as palavras com posição para leitura da tabela."""
    try:
        import fitz
    except ImportError as erro:
        raise ValueError("Os componentes de leitura OCR do extrato BTG não estão disponíveis.") from erro

    executavel = shutil.which("tesseract")
    if not executavel:
        raise ValueError("O leitor OCR necessário para o extrato BTG não está instalado.")
    idiomas = subprocess.run(
        [executavel, "--list-langs"], capture_output=True, text=True, check=False
    ).stdout.splitlines()
    idioma = "por" if "por" in idiomas else "eng"

    documento = fitz.open(stream=conteudo, filetype="pdf")
    paginas = []
    try:
        for pagina in documento:
            pix = pagina.get_pixmap(matrix=fitz.Matrix(3.0, 3.0), alpha=False)
            with tempfile.NamedTemporaryFile(suffix=".png") as imagem:
                pix.save(imagem.name)
                resultado = subprocess.run(
                    [executavel, imagem.name, "stdout", "-l", idioma, "--psm", "11", "tsv"],
                    capture_output=True, text=True, check=False,
                )
            if resultado.returncode != 0:
                raise ValueError("Não foi possível executar a leitura OCR do extrato BTG.")
            dados = pd.read_csv(io.StringIO(resultado.stdout), sep="\t")
            paginas.append((pix.width, dados))
    finally:
        documento.close()
    return paginas


def processar_extrato_btg_vgv(conteudo: bytes) -> pd.DataFrame:
    """Extrai movimentos do extrato visual BTG pela posição das colunas."""
    registros = []
    regex_data = re.compile(r"^\d{2}/\d{2}/\d{4}$")
    regex_valor = re.compile(r"^-?[\d.]+,\d{2}$")
    for largura, dados in _ocr_paginas(conteudo):
        dados = dados.dropna(subset=["text"]).copy()
        dados["text"] = dados["text"].astype(str).str.strip()
        dados = dados[dados["text"] != ""]
        for _, token_data in dados[dados["text"].str.match(regex_data)].iterrows():
            if float(token_data["left"]) > largura * 0.25:
                continue
            centro_y = float(token_data["top"]) + float(token_data["height"]) / 2
            centros = dados["top"].astype(float) + dados["height"].astype(float) / 2
            valores_movimento = dados[
                (centros.sub(centro_y).abs() <= max(18, float(token_data["height"])))
                & (dados["left"].astype(float) > largura * 0.45)
                & (dados["left"].astype(float) < largura * 0.72)
                & dados["text"].str.match(regex_valor)
            ].sort_values("left")
            # A coluna do movimento fica antes da coluna do saldo. Assim, saldos
            # inicial/final não são confundidos com lançamentos, mesmo quando o
            # OCR fragmenta o saldo em mais de uma palavra.
            if valores_movimento.empty:
                continue
            valor = round(_valor_monetario(valores_movimento.iloc[0]["text"]), 2)
            if abs(valor) < 0.005:
                continue
            data = pd.to_datetime(token_data["text"], dayfirst=True, errors="coerce")
            if pd.isna(data):
                continue
            registros.append({
                "DESCRIÇÃO": "BANCO BTG",
                "DATA": data.normalize(),
                "VALOR": valor,
                "DÉBITO": "",
                "CRÉDITO": "",
                "HISTÓRICO": "MOVIMENTO BTG",
            })
    if not registros:
        raise ValueError("Nenhum lançamento foi reconhecido no extrato BTG.")
    return pd.DataFrame(registros, columns=COLUNAS_MODELO).sort_values(
        ["DATA", "VALOR"], kind="stable"
    ).reset_index(drop=True)


def processar_vgv(conteudo_planilha: bytes, conteudo_extrato: bytes):
    """Monta o Modelo Domínio com históricos do caixa e confere contra o BTG."""
    modelo = ler_caixa_vgv(conteudo_planilha)
    extrato = processar_extrato_btg_vgv(conteudo_extrato)
    disponiveis = defaultdict(list)
    for indice, linha in extrato.iterrows():
        chave = (pd.Timestamp(linha["DATA"]).normalize(), int(round(float(linha["VALOR"]) * 100)))
        disponiveis[chave].append(indice)

    pareados = set()
    status = []
    for _, linha in modelo.iterrows():
        chave = (pd.Timestamp(linha["DATA"]).normalize(), int(round(float(linha["VALOR"]) * 100)))
        candidatos = disponiveis.get(chave, [])
        if candidatos:
            pareados.add(candidatos.pop(0))
            status.append("Conferido")
        else:
            status.append("Sem correspondência no extrato")

    modelo = modelo.copy()
    modelo["CONFERÊNCIA"] = status
    sem_planilha = extrato.loc[
        [indice for indice in extrato.index if indice not in pareados]
    ].copy()
    resumo = {
        "planilha": len(modelo),
        "extrato": len(extrato),
        "conferidos": len(pareados),
        "sem_extrato": int((modelo["CONFERÊNCIA"] != "Conferido").sum()),
        "sem_planilha": len(sem_planilha),
        "entradas": round(float(modelo.loc[modelo["VALOR"] > 0, "VALOR"].sum()), 2),
        "saidas": round(float(-modelo.loc[modelo["VALOR"] < 0, "VALOR"].sum()), 2),
    }
    return modelo, extrato, sem_planilha, resumo
