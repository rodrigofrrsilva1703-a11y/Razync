"""Leitores bancários da empresa 1208 - Kairos Desmonte Industriais."""

from __future__ import annotations

import io
import re
import unicodedata

import pandas as pd
import pdfplumber


COLUNAS_MODELO = ["DESCRIÇÃO", "DATA", "VALOR", "DÉBITO", "CRÉDITO", "HISTÓRICO"]
CONTAS = {"itau": "508", "safra": "512", "bradesco": "9"}
NOMES = {"itau": "BANCO ITAÚ", "safra": "BANCO SAFRA", "bradesco": "BANCO BRADESCO"}


def _texto(valor) -> str:
    return re.sub(r"\s+", " ", str(valor or "")).strip()


def _normalizar(valor) -> str:
    texto = unicodedata.normalize("NFKD", _texto(valor))
    return "".join(c for c in texto if not unicodedata.combining(c)).upper()


def _moeda(valor) -> float:
    texto = _texto(valor).replace("R$", "").replace(" ", "")
    negativo = texto.endswith("-") or texto.startswith("-") or texto.upper().endswith("DV")
    texto = re.sub(r"(?:CR|DV)$", "", texto, flags=re.I).strip("+-")
    texto = texto.replace(".", "").replace(",", ".")
    try:
        numero = float(texto)
    except ValueError:
        return 0.0
    return round(-abs(numero) if negativo else numero, 2)


def _registro(banco: str, data, valor: float, historico: str) -> dict:
    historico = re.sub(r"^(?:Pago|Recebido)\s*:\s*", "", _texto(historico), flags=re.I)
    prefixo = "Recebido: " if valor > 0 else "Pago: "
    return {
        "DESCRIÇÃO": NOMES[banco],
        "DATA": pd.Timestamp(data).normalize(),
        "VALOR": round(float(valor), 2),
        "DÉBITO": CONTAS[banco] if valor > 0 else "",
        "CRÉDITO": CONTAS[banco] if valor < 0 else "",
        "HISTÓRICO": prefixo + (historico or "MOVIMENTO BANCÁRIO"),
    }


def _linhas_visuais(pagina, x_min=0, x_max=None, tolerancia=2.0):
    palavras = pagina.extract_words(use_text_flow=False, keep_blank_chars=False)
    if x_max is None:
        x_max = pagina.width
    palavras = [p for p in palavras if x_min <= p["x0"] < x_max]
    linhas = []
    for palavra in sorted(palavras, key=lambda p: (p["top"], p["x0"])):
        if not linhas or abs(linhas[-1][0] - palavra["top"]) > tolerancia:
            linhas.append([palavra["top"], [palavra]])
        else:
            linhas[-1][1].append(palavra)
    return [sorted(grupo, key=lambda p: p["x0"]) for _, grupo in linhas]


def _finalizar(registros, banco):
    if not registros:
        raise ValueError(f"Nenhum lançamento válido foi reconhecido no extrato {NOMES[banco]}.")
    return pd.DataFrame(registros, columns=COLUNAS_MODELO).sort_values(
        "DATA", kind="stable"
    ).reset_index(drop=True)


def processar_itau_pdf(conteudo: bytes) -> pd.DataFrame:
    registros = []
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        texto_validacao = " ".join((p.extract_text() or "")[:800] for p in pdf.pages[:2])
        if "KAIROS" not in _normalizar(texto_validacao):
            raise ValueError("O PDF não parece ser o extrato Itaú da empresa 1208.")
        for pagina in pdf.pages:
            palavras = pagina.extract_words(use_text_flow=False, keep_blank_chars=False)
            ancoras = []
            for palavra in palavras:
                if palavra["x0"] < 105 and re.fullmatch(r"\d{2}/\d{2}/\d{4}", palavra["text"]):
                    ancoras.append((palavra["top"], palavra["text"]))
            for posicao, (topo, data_txt) in enumerate(ancoras):
                anterior = ancoras[posicao - 1][0] if posicao else topo - 24
                proximo = ancoras[posicao + 1][0] if posicao + 1 < len(ancoras) else topo + 24
                inicio, fim = (anterior + topo) / 2, (topo + proximo) / 2
                bloco = [p for p in palavras if inicio <= p["top"] < fim]
                data = pd.to_datetime(data_txt, dayfirst=True, errors="coerce")
                historico = _texto(" ".join(p["text"] for p in sorted(bloco, key=lambda x: (x["top"], x["x0"])) if 85 <= p["x0"] < 430))
                candidatos = [p["text"] for p in bloco if 430 <= p["x0"] < 530 and re.search(r"\d,\d{2}$", p["text"])]
                if not candidatos:
                    continue
                valor = _moeda(candidatos[-1])
                hist_norm = _normalizar(historico)
                if pd.isna(data) or abs(valor) < 0.005 or "SALDO" in hist_norm:
                    continue
                registros.append(_registro("itau", data, valor, historico))
    return _finalizar(registros, "itau")


def processar_safra_pdf(conteudo: bytes) -> pd.DataFrame:
    registros = []
    saldos = []
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        texto_validacao = " ".join((p.extract_text() or "")[:800] for p in pdf.pages[:2])
        if "SAFRA" not in _normalizar(texto_validacao) or "KAIROS" not in _normalizar(texto_validacao):
            raise ValueError("O PDF não parece ser o extrato Safra da empresa 1208.")
        for pagina in pdf.pages:
            for palavras in _linhas_visuais(pagina):
                data_txt = next((p["text"] for p in palavras if p["x0"] < 65 and re.fullmatch(r"\d{2}/\d{2}", p["text"])), None)
                if not data_txt:
                    continue
                historico = _texto(" ".join(p["text"] for p in palavras if 60 <= p["x0"] < 500))
                candidatos = [p["text"] for p in palavras if p["x0"] >= 500 and re.search(r"\d,\d{2}$", p["text"])]
                hist_norm = _normalizar(historico)
                if not candidatos:
                    continue
                valor = _moeda(candidatos[-1])
                data = pd.to_datetime(f"{data_txt}/2026", dayfirst=True, errors="coerce")
                if "SALDO TOTAL" in hist_norm:
                    if pd.notna(data):
                        saldos.append((pd.Timestamp(data).normalize(), valor))
                    continue
                if "SALDO" in hist_norm:
                    continue
                if abs(valor) < 0.005:
                    continue
                if pd.notna(data):
                    registros.append(_registro("safra", data, valor, historico))
    # O PDF do Safra pode omitir a descrição de movimentos que ainda aparecem na
    # evolução do saldo. Nesses casos, registra apenas a diferença comprovada entre
    # dois saldos diários, mantendo entradas - saídas igual ao saldo do extrato.
    if saldos:
        movimentos = pd.DataFrame(registros)
        saldo_anterior = saldos[0][1]
        for data, saldo in saldos[1:]:
            total_dia = 0.0
            if not movimentos.empty:
                total_dia = float(movimentos.loc[movimentos["DATA"] == data, "VALOR"].sum())
            diferenca = round(saldo - saldo_anterior - total_dia, 2)
            if abs(diferenca) > 0.02:
                registro = _registro("safra", data, diferenca, "MOVIMENTO NÃO DESCRITO NO PDF (RECONCILIAÇÃO DO SALDO)")
                registros.append(registro)
                movimentos = pd.concat([movimentos, pd.DataFrame([registro])], ignore_index=True)
            saldo_anterior = saldo
    return _finalizar(registros, "safra")


def processar_bradesco_pdf(conteudo: bytes) -> pd.DataFrame:
    registros = []
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        texto_validacao = " ".join((p.extract_text() or "")[:1000] for p in pdf.pages[:2])
        validacao = _normalizar(texto_validacao)
        if "KAIROS" not in validacao or ("16.803-3" not in texto_validacao and "16.803" not in texto_validacao):
            raise ValueError("O PDF não parece ser o extrato Bradesco da empresa 1208.")
        for pagina in pdf.pages:
            for inicio, fim in ((0, pagina.width / 2), (pagina.width / 2, pagina.width)):
                ultimo = None
                largura = fim - inicio
                for palavras in _linhas_visuais(pagina, inicio, fim, 1.8):
                    locais = [(p["x0"] - inicio, p["text"]) for p in palavras]
                    data_txt = next((t for x, t in locais if x < 80 and re.fullmatch(r"\d{2}/\d{2}/\d{2}", t)), None)
                    if not data_txt:
                        if ultimo is not None:
                            comp = _texto(" ".join(t for x, t in locais if 45 <= x < largura - 85))
                            if comp and not any(k in _normalizar(comp) for k in ("SALDO EM", "TRANSPORTE", "EXTRATO SEGUNDA VIA")):
                                ultimo["HISTÓRICO"] = _texto(ultimo["HISTÓRICO"] + " " + comp)
                        continue
                    historico = _texto(" ".join(t for x, t in locais if 45 <= x < 205))
                    candidatos = [t for x, t in locais if x >= 270 and re.search(r"\d,\d{2}(?:-|CR|DV)?$", t, re.I)]
                    hist_norm = _normalizar(historico)
                    if not candidatos or "SALDO" in hist_norm or "TRANSPORTE" in hist_norm:
                        continue
                    valor = _moeda(candidatos[-1])
                    data = pd.to_datetime(data_txt, dayfirst=True, errors="coerce")
                    if pd.isna(data) or abs(valor) < 0.005:
                        continue
                    ultimo = _registro("bradesco", data, valor, historico)
                    registros.append(ultimo)
    return _finalizar(registros, "bradesco")


def processar_extrato_1208(conteudo: bytes, banco: str) -> pd.DataFrame:
    banco = _normalizar(banco).lower()
    banco = "itau" if "itau" in banco else "safra" if "safra" in banco else "bradesco" if "bradesco" in banco else banco
    leitores = {"itau": processar_itau_pdf, "safra": processar_safra_pdf, "bradesco": processar_bradesco_pdf}
    if banco not in leitores:
        raise ValueError("Banco não suportado para a empresa 1208.")
    return leitores[banco](conteudo)


def ler_contas_pagas(conteudo: bytes) -> pd.DataFrame:
    """Extrai itens pagos para detalhamento, sem criar movimentos bancários."""
    xls = pd.ExcelFile(io.BytesIO(conteudo))
    itens = []
    padrao_grupo = re.compile(r"PAGAMENTOS?\s*[-–:]?\s*(\d{2}/\d{2}/\d{2,4})", re.I)
    for aba in xls.sheet_names:
        bruto = pd.read_excel(xls, sheet_name=aba, header=None, dtype=object)
        # Abas recentes usam uma tabela direta: Fornecedor, Vencimento, ... Valor Pago.
        cabecalho_direto = None
        for indice in range(min(len(bruto), 10)):
            nomes = [_normalizar(v) for v in bruto.iloc[indice].tolist()]
            if "FORNECEDOR" in nomes and "VENCIMENTO" in nomes and "VALOR PAGO" in nomes:
                cabecalho_direto = (indice, nomes.index("FORNECEDOR"), nomes.index("VENCIMENTO"), nomes.index("VALOR PAGO"))
                break
        if cabecalho_direto:
            indice, col_desc, col_data, col_valor = cabecalho_direto
            for _, linha in bruto.iloc[indice + 1:].iterrows():
                data = pd.to_datetime(linha.iloc[col_data], dayfirst=True, errors="coerce")
                valor_raw = linha.iloc[col_valor]
                if pd.isna(data) or not isinstance(valor_raw, (int, float)) or pd.isna(valor_raw) or abs(float(valor_raw)) < 0.01:
                    continue
                descricao = _texto(linha.iloc[col_desc])
                categoria = _texto(linha.iloc[3]) if len(linha) > 3 else ""
                itens.append({"DATA": pd.Timestamp(data).normalize(), "VALOR": round(abs(float(valor_raw)), 2), "HISTÓRICO": _texto(descricao + " " + categoria)})
            continue

        data_grupo = None
        for _, linha in bruto.iterrows():
            valores_brutos = linha.tolist()
            valores = [_texto(v) if pd.notna(v) else "" for v in valores_brutos]
            conjunto = " ".join(v for v in valores[:5] if v)
            achado = padrao_grupo.search(conjunto)
            if achado:
                data_grupo = pd.to_datetime(achado.group(1), dayfirst=True, errors="coerce")
                continue
            if data_grupo is None:
                continue
            descricao = valores[1] if len(valores) > 1 else ""
            valor_raw = valores_brutos[2] if len(valores_brutos) > 2 else None
            if not descricao or not isinstance(valor_raw, (int, float)) or isinstance(valor_raw, bool) or pd.isna(valor_raw) or abs(float(valor_raw)) < 0.01:
                continue
            norm = _normalizar(descricao)
            if any(k in norm for k in ("TOTAL", "DESCRICAO PAGTO", "DECRICAO PAGTO")):
                continue
            empresa = valores[3] if len(valores) > 3 else ""
            centro = valores[4] if len(valores) > 4 else ""
            itens.append({"DATA": pd.Timestamp(data_grupo).normalize(), "VALOR": round(abs(float(valor_raw)), 2), "HISTÓRICO": _texto(" ".join(x for x in (descricao, empresa, centro) if x))})
    return pd.DataFrame(itens, columns=["DATA", "VALOR", "HISTÓRICO"])


def detalhar_com_contas_pagas(modelos: dict[str, pd.DataFrame], detalhes: pd.DataFrame):
    """Substitui somente um débito genérico cuja data e total fecham com os itens."""
    saida = {b: df.copy() for b, df in modelos.items()}
    aplicados = []
    if detalhes is None or detalhes.empty:
        return saida, aplicados
    for data, grupo in detalhes.groupby("DATA", sort=False):
        total = round(float(grupo["VALOR"].sum()), 2)
        candidatos = []
        for banco, df in saida.items():
            mascara = (
                (pd.to_datetime(df["DATA"]).dt.normalize() == pd.Timestamp(data))
                & (df["VALOR"] < 0)
                & (df["VALOR"].abs().round(2) == total)
                & df["HISTÓRICO"].map(lambda x: any(k in _normalizar(x) for k in ("FORNECEDOR", "SISPAG", "PAGTO ELETRON COBRANCA")))
            )
            candidatos.extend((banco, indice) for indice in df.index[mascara])
        if len(candidatos) != 1:
            continue
        banco, indice = candidatos[0]
        original = saida[banco].loc[indice]
        novos = []
        for _, item in grupo.iterrows():
            novos.append(_registro(banco, data, -float(item["VALOR"]), item["HISTÓRICO"]))
        saida[banco] = pd.concat([
            saida[banco].drop(index=indice),
            pd.DataFrame(novos, columns=COLUNAS_MODELO),
        ], ignore_index=True).sort_values("DATA", kind="stable").reset_index(drop=True)
        aplicados.append({"banco": banco, "data": pd.Timestamp(data), "valor": abs(float(original["VALOR"])), "itens": len(novos)})
    return saida, aplicados
