"""Leitura de Razão contábil exportado pelo Domínio para a Base Inteligente."""

from __future__ import annotations

import io
import os
import re
import struct
import unicodedata

import pandas as pd


def _normalizar(valor) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii").casefold()
    return re.sub(r"[^a-z0-9]+", "", texto)


def _conta(valor) -> str:
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return ""
    texto = str(valor or "").strip()
    if re.fullmatch(r"\d+\.0", texto):
        texto = texto[:-2]
    return re.sub(r"\s+", "", texto)


def _numero(valor) -> float:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if not texto or texto.casefold() == "nan":
        return 0.0
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return 0.0


def _recuperar_xls_biff_irregular(file_bytes: bytes):
    try:
        from xlrd.compdoc import CompDoc

        documento = CompDoc(file_bytes, ignore_workbook_corruption=True)
        fluxo_original = (
            documento.get_named_stream("Workbook")
            or documento.get_named_stream("Book")
        )
        if not fluxo_original:
            return None
        fluxo = bytearray(fluxo_original)
        registros_abas = []
        posicao = 0
        fim_globais = None
        while posicao + 4 <= len(fluxo):
            codigo, tamanho = struct.unpack_from("<HH", fluxo, posicao)
            fim = posicao + 4 + tamanho
            if fim > len(fluxo):
                break
            if codigo == 0x0085 and tamanho >= 4:
                registros_abas.append(posicao)
            posicao = fim
            if codigo == 0x000A:
                fim_globais = posicao
                break
        if not registros_abas or fim_globais is None:
            return None

        inicios = []
        cursor = fim_globais
        while True:
            indice = fluxo.find(b"\x09\x08", cursor)
            if indice < 0:
                break
            if indice + 8 <= len(fluxo):
                tamanho = struct.unpack_from("<H", fluxo, indice + 2)[0]
                if tamanho >= 4 and indice + 4 + tamanho <= len(fluxo):
                    versao, tipo = struct.unpack_from("<HH", fluxo, indice + 4)
                    if versao in (0x0500, 0x0600) and tipo in (0x0010, 0x0020, 0x0040):
                        inicios.append(indice)
            cursor = indice + 2
        if len(inicios) < len(registros_abas):
            return None
        for registro, inicio in zip(registros_abas, inicios):
            struct.pack_into("<I", fluxo, registro + 4, inicio)
        xls = pd.ExcelFile(io.BytesIO(bytes(fluxo)), engine="xlrd")
        return pd.read_excel(xls, sheet_name=xls.sheet_names[0], header=None, dtype=object)
    except Exception:
        return None


def _ler_bruto(file_bytes: bytes, filename: str):
    extensao = os.path.splitext(filename)[1].casefold()
    try:
        if extensao == ".xlsx":
            xls = pd.ExcelFile(io.BytesIO(file_bytes))
            return pd.read_excel(xls, sheet_name=xls.sheet_names[0], header=None, dtype=object)
        if extensao == ".xls":
            try:
                return pd.read_excel(io.BytesIO(file_bytes), header=None, dtype=object, engine="xlrd")
            except Exception:
                try:
                    tabelas = pd.read_html(io.BytesIO(file_bytes), header=None)
                    if tabelas:
                        return tabelas[0]
                except Exception:
                    pass
                return _recuperar_xls_biff_irregular(file_bytes)
    except Exception:
        return None
    return None


def ler_razao_dominio_base(file_bytes: bytes, filename: str, contas_bancarias: dict):
    """Retorna lançamentos bancários do Razão com a contrapartida contábil."""
    bruto = _ler_bruto(file_bytes, filename)
    if bruto is None or bruto.empty:
        return []

    linha_cabecalho = None
    mapa = {}
    for indice, linha in bruto.iterrows():
        teste = {_normalizar(valor): coluna for coluna, valor in linha.items() if pd.notna(valor)}
        if "data" in teste and "historico" in teste and "ctacpart" in teste:
            linha_cabecalho = indice
            mapa = teste
            break
    if linha_cabecalho is None:
        return []

    col_data = mapa["data"]
    col_historico = mapa["historico"]
    col_contrapartida = mapa["ctacpart"]
    col_debito = mapa.get("debito")
    col_credito = mapa.get("credito")
    if col_debito is None or col_credito is None:
        return []

    bancos_por_conta = {
        _conta(numero): banco for banco, numero in contas_bancarias.items()
    }
    banco_atual = ""
    conta_banco_atual = ""
    registros = []
    for _, linha in bruto.iloc[linha_cabecalho + 1 :].iterrows():
        primeiro = _normalizar(linha.iloc[0] if len(linha) else "")
        if primeiro == "conta":
            numero_conta = _conta(linha.iloc[1] if len(linha) > 1 else "")
            banco_atual = bancos_por_conta.get(numero_conta, "")
            conta_banco_atual = numero_conta if banco_atual else ""
            continue
        if not banco_atual:
            continue

        data = pd.to_datetime(linha.get(col_data), dayfirst=True, errors="coerce")
        historico_bruto = linha.get(col_historico)
        historico = (
            "" if pd.isna(historico_bruto)
            else re.sub(r"\s+", " ", str(historico_bruto)).strip()
        )
        contrapartida = _conta(linha.get(col_contrapartida))
        debito = abs(_numero(linha.get(col_debito)))
        credito = abs(_numero(linha.get(col_credito)))
        if pd.isna(data) or not historico or not contrapartida:
            continue
        if debito > 0 and credito == 0:
            conta_debito, conta_credito, valor = conta_banco_atual, contrapartida, debito
        elif credito > 0 and debito == 0:
            conta_debito, conta_credito, valor = contrapartida, conta_banco_atual, -credito
        else:
            continue
        registros.append({
            "banco": banco_atual,
            "data": pd.Timestamp(data).normalize(),
            "historico": historico,
            "contrapartida": contrapartida,
            "debito": conta_debito,
            "credito": conta_credito,
            "valor": round(valor, 2),
        })
    return registros
