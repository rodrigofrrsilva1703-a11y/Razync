import streamlit as st
import pandas as pd
import openpyxl
import re
import calendar
import io
import os
from datetime import datetime
from pypdf import PdfReader

# Configuração da página Web
st.set_page_config(page_title="Importador Domínio Pro", page_icon="🤖", layout="wide")

# ==============================================================================
# FUNÇÃO AUXILIAR UNIVERSAL DE TRATAMENTO NUMÉRICO MONETÁRIO
# ==============================================================================
def limpar_valor_monetario(v_val):
    if pd.isna(v_val) or v_val is None:
        return 0.0
    if isinstance(v_val, (int, float)):
        return float(v_val)
        
    s = str(v_val).strip().replace('R$', '').replace('$', '').replace(' ', '')
    if not s or s.lower() == 'nan':
        return 0.0

    if '.' in s and ',' in s:
        last_dot = s.rfind('.')
        last_comma = s.rfind(',')
        if last_comma > last_dot:
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')

    try:
        return float(s)
    except:
        return 0.0

# ==============================================================================
# 1. MOTOR INTELIGENTE: LEITURA DE OFX
# ==============================================================================
def processar_ofx(file_bytes, filename):
    lancamentos = []
    texto = ""
    for enc in ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']:
        try:
            texto = file_bytes.decode(enc)
            break
        except:
            pass
            
    if not texto:
        texto = file_bytes.decode('latin1', errors='ignore')

    raw_blocks = re.split(r'<STMTTRN>', texto, flags=re.IGNORECASE)
    
    for block in raw_blocks[1:]:
        block_clean = re.split(r'</STMTTRN>|</BANKTRANLIST>', block, flags=re.IGNORECASE)[0]
        
        match_date = re.search(r'<DTPOSTED>\s*(\d{4}[-/\.]?\d{2}[-/\.]?\d{2}|\d{8})', block_clean, re.IGNORECASE)
        match_amt = re.search(r'<TRNAMT>\s*([\+\-]?[\d\.\,]+)', block_clean, re.IGNORECASE)
        match_memo = re.search(r'<(?:MEMO|NAME|PAYEE)>\s*(.*?)(?:\r|\n|<|$)', block_clean, re.IGNORECASE)
        
        if match_date and match_amt:
            dt_s = match_date.group(1).replace('-', '').replace('/', '').replace('.', '')
            if len(dt_s) >= 8:
                data_fmt = f"{dt_s[6:8]}/{dt_s[4:6]}/{dt_s[:4]}"
            else:
                continue
                
            amt_str = match_amt.group(1).replace('+', '').strip()
            valor_float = limpar_valor_monetario(amt_str)
            
            historico = match_memo.group(1).strip() if match_memo else "TRANSACAO OFX"
            historico = historico.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
            
            banco = "BANCO OFX"
            fn_upper = filename.upper()
            if "ITAU" in fn_upper: banco = "BANCO ITAU"
            elif "BRADESCO" in fn_upper: banco = "BANCO BRADESCO"
            elif "SANTANDER" in fn_upper: banco = "BANCO SANTANDER"
            elif "BB" in fn_upper or "BRASIL" in fn_upper: banco = "BANCO DO BRASIL"
            elif "CAIXA" in fn_upper: banco = "CAIXA ECONOMICA"
            elif "SICOOB" in fn_upper: banco = "SICOOB"
            elif "SICREDI" in fn_upper: banco = "SICREDI"
            elif "NUBANK" in fn_upper or "NU " in fn_upper: banco = "NUBANK"
            elif "INTER" in fn_upper: banco = "BANCO INTER"
            
            if valor_float != 0:
                lancamentos.append({
                    'DESCRIÇÃO': banco,
                    'DATA': data_fmt,
                    'VALOR': valor_float,
                    'DÉBITO': '',
                    'CRÉDITO': '',
                    'HISTÓRICO': historico
                })
            
    return lancamentos

# ==============================================================================
# 2. MOTOR INTELIGENTE: LEITURA UNIVERSAL DE PLANILHAS (XLS, XLSX, CSV, HTML-XLS)
# ==============================================================================
def processar_planilha_universal(file_bytes, filename):
    lancamentos = []
    df = None
    ext = os.path.splitext(filename)[1].lower()

    if ext in ['.xlsx', '.xls']:
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
        except Exception:
            try:
                dfs = pd.read_html(io.BytesIO(file_bytes))
                if dfs: df = dfs[0]
            except Exception: pass

    if df is None:
        for enc in ['utf-8', 'latin1', 'cp1252', 'iso-8859-1', 'utf-16']:
            for sep in [';', ',', '\t', '|']:
                try:
                    df_temp = pd.read_csv(io.BytesIO(file_bytes), sep=sep, encoding=enc, dtype=str)
                    if df_temp.shape[1] > 1:
                        df = df_temp
                        break
                except Exception: pass
            if df is not None: break

    if df is None or df.empty: return []

    header_idx = None
    for idx, row in df.iterrows():
        row_str = " ".join([str(v) for v in row.values if pd.notna(v)]).lower()
        if ('data' in row_str or 'dt' in row_str) and ('valor' in row_str or 'crédito' in row_str or 'débito' in row_str or 'lançamento' in row_str):
            header_idx = idx
            break

    if header_idx is not None and header_idx > 0:
        df.columns = [str(v).strip() for v in df.iloc[header_idx].values]
        df = df.iloc[header_idx+1:].copy()

    cols = list(df.columns)
    col_data = next((c for c in cols if any(p in str(c).lower() for p in ['data', 'dt', 'date', 'dia'])), None)
    col_hist = next((c for c in cols if any(p in str(c).lower() for p in ['lançamento', 'lancamento', 'históric', 'historic', 'descriç', 'descric', 'detalhe', 'memo'])), None)
    col_doc = next((c for c in cols if any(p in str(c).lower() for p in ['dcto', 'doc', 'documento', 'num', 'nr'])), None)
    col_val = next((c for c in cols if any(p in str(c).lower() for p in ['valor', 'val', 'monto', 'amount'])), None)
    col_cred = next((c for c in cols if any(p in str(c).lower() for p in ['crédit', 'credit', 'entrada'])), None)
    col_deb = next((c for c in cols if any(p in str(c).lower() for p in ['débit', 'debit', 'saída', 'saida'])), None)
    col_tipo = next((c for c in cols if any(p in str(c).lower() for p in ['tipo', 'natureza', 'operacao', 'operaç'])), None)

    if not col_data: return []

    for _, row in df.iterrows():
        dt_raw = str(row[col_data]).strip() if pd.notna(row[col_data]) else ''
        if dt_raw.upper() in ['TOTAL', 'ÚLTIMOS LANÇAMENTOS', 'ULTIMOS LANCAMENTOS', 'SALDOS INVEST FÁCIL / PLUS', 'NAN']:
            if dt_raw.upper() == 'TOTAL': break
                
        match_dt = re.search(r'(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{2})', dt_raw)
        if not match_dt: continue
            
        raw_dt = match_dt.group(1)
        if '-' in raw_dt:
            parts = raw_dt.split('-')
            dt_fmt = f"{parts[2]}/{parts[1]}/{parts[0]}"
        elif len(raw_dt.split('/')[2]) == 2:
            parts = raw_dt.split('/')
            dt_fmt = f"{parts[0]}/{parts[1]}/20{parts[2]}"
        else: dt_fmt = raw_dt

        hist_raw = str(row[col_hist]).strip() if col_hist and pd.notna(row[col_hist]) else 'MOVIMENTO BANCARIO'
        doc_raw = str(row[col_doc]).strip() if col_doc and pd.notna(row[col_doc]) else ''
        hist_fmt = f"{hist_raw} {doc_raw}" if doc_raw and doc_raw.lower() != 'nan' and doc_raw not in hist_raw else hist_raw

        if any(term in hist_fmt.upper() for term in ['SALDO ANTERIOR', 'SALDO ATUAL', 'SALDO DIA', 'SALDO DISPONÍVEL', 'SUBTOTAL']):
            continue

        valor_float = 0.0
        if col_cred or col_deb:
            v_cred = limpar_valor_monetario(row[col_cred]) if col_cred and pd.notna(row[col_cred]) else 0.0
            v_deb = limpar_valor_monetario(row[col_deb]) if col_deb and pd.notna(row[col_deb]) else 0.0
            
            if v_cred != 0: valor_float = abs(v_cred)
            elif v_deb != 0: valor_float = -abs(v_deb)
        elif col_val and pd.notna(row[col_val]):
            valor_float = limpar_valor_monetario(row[col_val])
            if col_tipo and pd.notna(row[col_tipo]):
                t_str = str(row[col_tipo]).upper()
                if 'D' in t_str or 'SAÍDA' in t_str or 'SAIDA' in t_str:
                    valor_float = -abs(valor_float)

        if valor_float != 0:
            banco_desc = f"EXTRATO {os.path.splitext(filename)[0].upper()}"
            if "BRADESCO" in filename.upper() or "BRADESCO" in hist_fmt.upper(): banco_desc = "BANCO BRADESCO"
            elif "ITAÚ" in filename.upper() or "ITAU" in filename.upper(): banco_desc = "BANCO ITAU"
            elif "SANTANDER" in filename.upper(): banco_desc = "BANCO SANTANDER"
            elif "CAIXA" in filename.upper(): banco_desc = "CAIXA ECONOMICA"

            lancamentos.append({'DESCRIÇÃO': banco_desc, 'DATA': dt_fmt, 'VALOR': valor_float, 'DÉBITO': '', 'CRÉDITO': '', 'HISTÓRICO': hist_fmt})

    return lancamentos

# ==============================================================================
# 3. MOTOR INTELIGENTE: LEITURA DE PDFS
# ==============================================================================
def extrair_periodo_extrato(caminho_pdf):
    try:
        reader = PdfReader(caminho_pdf, strict=False)
        # Lê as primeiras 3 páginas para encontrar datas
        texto = "".join([p.extract_text() for p in reader.pages[:3]])
        
        # Tenta encontrar par de datas (ex: 01/05/2026 a 31/05/2026)
        datas = re.findall(r'(\d{2}/\d{2}/\d{4})', texto)
        if len(datas) >= 2:
            return datetime.strptime(datas[0], '%d/%m/%Y'), datetime.strptime(datas[1], '%d/%m/%Y')
        
        # Fallback para "Mês: Nome/Ano"
        match_c = re.search(r'Mês:\s*([A-Za-zç]+)/(\d{4})', texto, re.IGNORECASE)
        if match_c:
            meses = {'JANEIRO':1, 'FEVEREIRO':2, 'MARCO':3, 'MARÇO':3, 'ABRIL':4, 'MAIO':5, 'JUNHO':6, 
                     'JULHO':7, 'AGOSTO':8, 'SETEMBRO':9, 'OUTUBRO':10, 'NOVEMBRO':11, 'DEZEMBRO':12}
            nome_mes = match_c.group(1).upper()
            m_num = meses.get(nome_mes, datetime.now().month)
            ano = int(match_c.group(2))
            return datetime(ano, m_num, 1), datetime(ano, m_num, calendar.monthrange(ano, m_num)[1])
            
    except: 
        pass
    return None, None

# ... (restante das funções de processamento de PDF permanecem iguais)
