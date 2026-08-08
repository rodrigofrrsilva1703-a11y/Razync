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
st.set_page_config(
    page_title="Plataforma Contábil Pro", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# ESTILIZAÇÃO CSS DARK MODE MINIMALISTA E ALINHADA
# ==============================================================================
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 100%;
        }
        
        .stButton>button {
            width: 100% !important;
            border-radius: 6px !important;
            font-weight: 500 !important;
            padding: 0.45rem 1rem !important;
            border: 1px solid #30363d !important;
            background-color: #21262d !important;
            color: #c9d1d9 !important;
            transition: all 0.2s ease;
            box-shadow: none !important;
        }
        .stButton>button:hover {
            background-color: #30363d !important;
            border-color: #8b949e !important;
            color: #ffffff !important;
        }

        .metric-card {
            background-color: #161b22;
            border: 1px solid #30363d;
            padding: 14px;
            border-radius: 8px;
            text-align: center;
        }
        .metric-title {
            font-size: 11px;
            color: #8b949e;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 4px;
            letter-spacing: 0.5px;
        }
        .metric-value {
            font-size: 18px;
            color: #f0f6fc;
            font-weight: 700;
        }

        section[data-testid="stSidebar"] {
            background-color: #0d1117;
            border-right: 1px solid #30363d;
        }

        .tool-card {
            background-color: #161b22;
            border: 1px solid #30363d;
            padding: 24px 20px;
            border-radius: 8px;
            text-align: center;
            height: 160px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            transition: border-color 0.2s ease;
        }
        .tool-card:hover {
            border-color: #8b949e;
        }
        
        .alerta-dominio {
            background-color: #3d1c1c;
            border-left: 5px solid #f85149;
            padding: 16px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .alerta-dominio h4 { margin-top: 0; color: #f85149; font-size: 16px; }
        .alerta-dominio p { margin-bottom: 0; color: #c9d1d9; font-size: 14px; }
        
        .aviso-banner {
            background-color: #161b22;
            border: 1px solid #30363d;
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
        }
        .aviso-banner p { margin: 0; color: #c9d1d9; font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

def limpar_caracteres_ilegais(val):
    if isinstance(val, str):
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', val)
    return val

def sanitizar_dataframe(df):
    for col in df.select_dtypes(include=['object', 'string']).columns:
        df[col] = df[col].apply(limpar_caracteres_ilegais)
    return df

def limpar_valor_monetario(v_val):
    if pd.isna(v_val) or v_val == '': return 0.0
    if isinstance(v_val, (int, float)): return float(v_val)
    s = str(v_val).strip()
    s = re.sub(r'[^\d,\.-]', '', s)
    if not s or s.lower() == 'nan': return 0.0
    if ',' in s and '.' in s:
        last_dot, last_comma = s.rfind('.'), s.rfind(',')
        s = s.replace('.', '').replace(',', '.') if last_comma > last_dot else s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    try: return float(s)
    except: return 0.0

def identificar_banco_inteligente(texto_conteudo, filename_str=""):
    combo = (str(texto_conteudo) + " " + str(filename_str)).upper()
    if "FIBRA" in combo or "58.616.418" in combo: return "BANCO FIBRA"
    elif "BRADESCO" in combo: return "BANCO BRADESCO"
    elif "ITAÚ" in combo or "ITAU" in combo: return "BANCO ITAU"
    elif "SANTANDER" in combo: return "BANCO SANTANDER"
    elif "CAIXA" in combo: return "CAIXA ECONOMICA"
    elif "BANCO DO BRASIL" in combo or " BB " in combo or combo.startswith("BB"): return "BANCO DO BRASIL"
    elif "NUBANK" in combo or "NU PAGAMENTO" in combo: return "NUBANK"
    elif "INTER" in combo: return "BANCO INTER"
    elif "SICOOB" in combo: return "SICOOB"
    elif "SICREDI" in combo: return "SICREDI"
    else: return "BANCO CONTA CORRENTE"

def deduzir_debito_pela_palavra(hist, is_negativo_atual):
    if is_negativo_atual: return True
    hist_upper = str(hist).upper()
    palavras_debito = ['TARIFA', 'EMITIDO', 'PGTO', 'DEBITO', 'CHEQUE', 'SAQUE', 'RESGATE', 'PAGAMENTO', 'IMPOSTO', 'IOF', 'IRRF', 'PIX ENVIADO', 'TED ENVIADA', 'DOC ENVIADO']
    palavras_credito = ['RECEBIDO', 'ESTORNO', 'DEVOLUCAO', 'DEVOLUÇÃO', 'CREDITO']
    if any(w in hist_upper for w in palavras_debito):
        if not any(w in hist_upper for w in palavras_credito):
            return True
    return False

def processar_ofx(file_bytes, filename):
    lancamentos = []
    texto = ""
    for enc in ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']:
        try:
            texto = file_bytes.decode(enc)
            break
        except: pass
    if not texto: texto = file_bytes.decode('latin1', errors='ignore')
    
    banco_detectado = identificar_banco_inteligente(texto, filename)
    raw_blocks = re.split(r'<STMTTRN>', texto, flags=re.IGNORECASE)
    
    for block in raw_blocks[1:]:
        block_clean = re.split(r'</STMTTRN>|</BANKTRANLIST>', block, flags=re.IGNORECASE)[0]
        match_date = re.search(r'<DTPOSTED>\s*(\d{4}[-/\.]?\d{2}[-/\.]?\d{2}|\d{8})', block_clean, re.IGNORECASE)
        match_amt = re.search(r'<TRNAMT>\s*([\+\-]?[\d\.\,]+)', block_clean, re.IGNORECASE)
        match_memo = re.search(r'<(?:MEMO|NAME|PAYEE)>\s*(.*?)(?:\r|\n|<|$)', block_clean, re.IGNORECASE)
        
        if match_date and match_amt:
            dt_s = match_date.group(1).replace('-', '').replace('/', '').replace('.', '')
            if len(dt_s) >= 8: data_fmt = f"{dt_s[6:8]}/{dt_s[4:6]}/{dt_s[:4]}"
            else: continue
            
            valor_float = limpar_valor_monetario(match_amt.group(1).replace('+', '').strip())
            historico = limpar_caracteres_ilegais(match_memo.group(1).strip().replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')) if match_memo else "TRANSACAO OFX"
            if 'SALDO' in historico.upper(): continue
            
            if valor_float != 0:
                lancamentos.append({'DESCRIÇÃO': banco_detectado, 'DATA': data_fmt, 'VALOR': valor_float, 'DÉBITO': '', 'CRÉDITO': '', 'HISTÓRICO': historico})
    return lancamentos

def processar_planilha_universal(file_bytes, filename):
    lancamentos, df = [], None
    ext = os.path.splitext(filename)[1].lower()
    
    if ext in ['.xlsx', '.xls']:
        try: df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
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
                    if df_temp.shape[1] > 1: df = df_temp; break
                except Exception: pass
            if df is not None: break
            
    if df is None or df.empty: return []
    
    texto_amostra = " ".join([str(v) for row in df.head(5).values for v in row if pd.notna(v)])
    banco_detectado = identificar_banco_inteligente(texto_amostra, filename)
    
    header_idx = None
    for idx, row in df.iterrows():
        row_str = " ".join([str(v) for v in row.values if pd.notna(v)]).lower()
        if ('data' in row_str or 'dt' in row_str) and ('valor' in row_str or 'crédito' in row_str or 'credit' in row_str or 'débito' in row_str or 'debit' in row_str or 'lançamento' in row_str):
            header_idx = idx; break
            
    if header_idx is not None and header_idx > 0:
        df.columns = [str(v).strip() for v in df.iloc[header_idx].values]
        df = df.iloc[header_idx+1:].copy()
        
    cols = list(df.columns)
    col_data = next((c for c in cols if any(p in str(c).lower() for p in ['data', 'dt', 'date', 'dia'])), None)
    col_hist = next((c for c in cols if any(p in str(c).lower() for p in ['lançamento', 'lancamento', 'históric', 'historic', 'descriç', 'descric', 'detalhe', 'memo'])), None)
    col_doc = next((c for c in cols if any(p in str(c).lower() for p in ['dcto', 'doc', 'documento', 'num', 'nr'])), None)
    col_val = next((c for c in cols if any(p in str(c).lower() for p in ['valor', 'val', 'monto', 'amount'])), None)
    col_cred = next((c for c in cols if any(p in str(c).lower() for p in ['crédit', 'credit', 'entrada', 'vlr_cred'])), None)
    col_deb = next((c for c in cols if any(p in str(c).lower() for p in ['débit', 'debit', 'saída', 'saida', 'vlr_deb'])), None)
    col_tipo = next((c for c in cols if any(p in str(c).lower() for p in ['tipo', 'natureza', 'operacao', 'operaç', 'c/d'])), None)

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
        
        hist_raw = limpar_caracteres_ilegais(str(row[col_hist]).strip()) if col_hist and pd.notna(row[col_hist]) else 'MOVIMENTO BANCARIO'
        doc_raw = limpar_caracteres_ilegais(str(row[col_doc]).strip()) if col_doc and pd.notna(row[col_doc]) else ''
        hist_fmt = f"{hist_raw} {doc_raw}" if doc_raw and doc_raw.lower() != 'nan' and doc_raw not in hist_raw else hist_raw
        if any(term in hist_fmt.upper() for term in ['SALDO', 'SUBTOTAL', 'TOTAL', 'TRANSPORTAR']): continue
        
        valor_float = 0.0
        
        if col_cred or col_deb:
            v_cred = limpar_valor_monetario(row[col_cred]) if col_cred and pd.notna(row[col_cred]) else 0.0
            v_deb = limpar_valor_monetario(row[col_deb]) if col_deb and pd.notna(row[col_deb]) else 0.0
            
            if v_cred != 0:
                valor_float = abs(v_cred)  
            elif v_deb != 0:
                valor_float = -abs(v_deb) 
                
        elif col_val and pd.notna(row[col_val]):
            val_base = limpar_valor_monetario(row[col_val])
            if val_base != 0:
                is_negativo = False
                tipo_str = str(row[col_tipo]).upper() if col_tipo and pd.notna(row[col_tipo]) else ""
                
                if 'D' in tipo_str or 'SAÍDA' in tipo_str or 'SAIDA' in tipo_str or 'DEBITO' in tipo_str:
                    is_negativo = True
                elif val_base < 0:
                    is_negativo = True
                
                is_negativo = deduzir_debito_pela_palavra(hist_fmt, is_negativo)
                valor_float = -abs(val_base) if is_negativo else abs(val_base)

        if valor_float != 0:
            lancamentos.append({'DESCRIÇÃO': banco_detectado, 'DATA': dt_fmt, 'VALOR': valor_float, 'DÉBITO': '', 'CRÉDITO': '', 'HISTÓRICO': hist_fmt})
            
    return lancamentos

def extrair_periodo_extrato(caminho_pdf):
    try:
        reader = PdfReader(caminho_pdf, strict=False)
        texto = "".join([p.extract_text() for p in reader.pages[:3]])
        datas = re.findall(r'(\d{2}/\d{2}/\d{4})', texto)
        if len(datas) >= 2: return datetime.strptime(datas[0], '%d/%m/%Y'), datetime.strptime(datas[1], '%d/%m/%Y')
        match_c = re.search(r'Mês:\s*([A-Za-zç]+)/(\d{4})', texto, re.IGNORECASE)
        if match_c:
            meses = {'JANEIRO':1, 'FEVEREIRO':2, 'MARCO':3, 'MARÇO':3, 'ABRIL':4, 'MAIO':5, 'JUNHO':6, 'JULHO':7, 'AGOSTO':8, 'SETEMBRO':9, 'OUTUBRO':10, 'NOVEMBRO':11, 'DEZEMBRO':12}
            m_num, ano = meses.get(match_c.group(1).upper(), datetime.now().month), int(match_c.group(2))
            return datetime(ano, m_num, 1), datetime(ano, m_num, calendar.monthrange(ano, m_num)[1])
    except: pass
    return None, None

def processar_pdf_fibra(caminho_pdf):
    lancamentos = []
    try:
        reader = PdfReader(caminho_pdf, strict=False)
        texto = ""
        for page in reader.pages: texto += page.extract_text() + "\n"
        
        texto = texto.replace('\x00', 'ti')
        blocks = re.split(r'\n(?=\d{2}/\d{2}/\d{4}\s+\d{5,})', texto)
        
        for block in blocks[1:]:
            block = re.split(r'\nSALDO', block)[0]
            match_date = re.match(r'^(\d{2}/\d{2}/\d{4})', block)
            if not match_date: continue
            data = match_date.group(1)
            
            vals = re.findall(r'R\$\s*([\d\.]+,\d{2})', block)
            if not vals: continue
            val_str = vals[-1] 
            
            hist = block[10:].replace(f'R$ {val_str}', '').strip()
            hist = re.sub(r'\s+', ' ', hist)
            
            v = limpar_valor_monetario(val_str)
            is_debito = deduzir_debito_pela_palavra(hist, False)
            if is_debito: v = -abs(v)
                
            hist = limpar_caracteres_ilegais(hist)
            lancamentos.append({'DESCRIÇÃO': 'BANCO FIBRA', 'DATA': data, 'VALOR': v, 'DÉBITO': '', 'CRÉDITO': '', 'HISTÓRICO': hist})
    except: pass
    return lancamentos

def processar_pdf_santander(caminho_pdf):
    lancamentos = []
    try:
        reader = PdfReader(caminho_pdf, strict=False)
        date_regex = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(.*)')
        for pagina in reader.pages:
            texto = pagina.extract_text()
            if not texto: continue
            linhas = [l.strip() for l in texto.split('\n') if l.strip()]
            i = 0
            while i < len(linhas):
                linha = linhas[i]
                if any(t in linha.upper() for t in ['SALDO', 'POSIÇÃO EM:', 'CENTRAL DE ATENDIMENTO']): i += 1; continue
                match = date_regex.match(linha)
                if match:
                    dt_str, rest = match.group(1), match.group(2)
                    full_text = rest
                    vals = re.findall(r'(-?\d{1,3}(?:\.\d{3})*,\d{2})', full_text)
                    while not vals and i + 1 < len(linhas):
                        nl = linhas[i+1]
                        if 'Saldo' in nl or 'Central de Atendimento' in nl: break
                        i += 1; full_text += " " + nl
                        vals = re.findall(r'(-?\d{1,3}(?:\.\d{3})*,\d{2})', full_text)
                        if vals: break
                    if vals:
                        val_str = vals[-2] if len(vals) >= 2 else vals[0]
                        hist = limpar_caracteres_ilegais(full_text[:full_text.rfind(val_str)].strip())
                        if 'SALDO' not in hist.upper():
                            try:
                                v = limpar_valor_monetario(val_str)
                                is_negativo = '-' in val_str
                                is_negativo = deduzir_debito_pela_palavra(hist, is_negativo)
                                v = -abs(v) if is_negativo else abs(v)
                                lancamentos.append({'DESCRIÇÃO': 'BANCO SANTANDER', 'DATA': dt_str, 'VALOR': v, 'DÉBITO': '', 'CRÉDITO': '', 'HISTÓRICO': hist})
                            except: pass
                i += 1
    except: pass
    return lancamentos

def processar_pdf_caixa(caminho_pdf):
    lancamentos = []
    try:
        reader = PdfReader(caminho_pdf, strict=False)
        caixa_regex = re.compile(r'^(\d{2}/\d{2}/\d{4})\s*(\d{6})?\s+(.*?)\s+([\d\.]+,\d{2})\s+([CD])\s+[\d\.]+,\d{2}\s+[CD]')
        for pagina in reader.pages:
            texto = pagina.extract_text()
            if not texto: continue
            for linha in texto.split('\n'):
                linha = linha.strip()
                if not linha or 'SALDO' in linha.upper() or 'EXTRATO' in linha.upper(): continue
                match = caixa_regex.search(linha)
                if match:
                    data, doc, historico, val_str, tipo = match.groups()
                    if 'SALDO' in historico.upper(): continue
                    try:
                        v = limpar_valor_monetario(val_str)
                        if tipo == 'D': v = -abs(v)
                        hist_completo = limpar_caracteres_ilegais(f"{historico.strip()} {doc.strip()}" if doc else historico.strip())
                        lancamentos.append({'DESCRIÇÃO': 'CAIXA ECONOMICA', 'DATA': data, 'VALOR': v, 'DÉBITO': '', 'CRÉDITO': '', 'HISTÓRICO': hist_completo})
                    except: pass
    except: pass
    return lancamentos

def processar_pdf_bradesco(caminho_pdf):
    lancamentos = []
    try:
        reader = PdfReader(caminho_pdf, strict=False)
        date_regex = re.compile(r'^(\d{2}/\d{2}/\d{4})')
        current_date, pending_desc = None, ""
        for pagina in reader.pages:
            texto = pagina.extract_text()
            if not texto: continue
            linhas = [l.strip() for l in texto.split('\n') if l.strip()]
            i = 0
            while i < len(linhas):
                linha = linhas[i]
                if any(t in linha.upper() for t in ['EXTRATO DE:', 'TOTAL', 'AGÊNCIA | CONTA', 'FOLHA ', 'SALDOS']): i += 1; continue
                match_date = date_regex.match(linha)
                if match_date: current_date, linha_sem_data = match_date.group(1), linha[len(match_date.group(1)):].strip()
                else: linha_sem_data = linha
                matches_valores = re.findall(r'(-?[\d\.]+\,\d{2})', linha_sem_data)
                if matches_valores and current_date:
                    val_str = matches_valores[-2] if len(matches_valores) >= 2 else matches_valores[0]
                    parte_desc = linha_sem_data[:linha_sem_data.rfind(val_str)].strip()
                    historico_completo = limpar_caracteres_ilegais(f"{pending_desc} {parte_desc}".strip() if pending_desc else parte_desc)
                    pending_desc = ""
                    if 'SALDO' not in historico_completo.upper() and 'TOTAL' not in historico_completo.upper():
                        try:
                            v = limpar_valor_monetario(val_str)
                            is_negativo = '-' in val_str
                            is_negativo = deduzir_debito_pela_palavra(historico_completo, is_negativo)
                            v = -abs(v) if is_negativo else abs(v)
                            lancamentos.append({'DESCRIÇÃO': 'BANCO BRADESCO', 'DATA': current_date, 'VALOR': v, 'DÉBITO': '', 'CRÉDITO': '', 'HISTÓRICO': historico_completo})
                        except: pass
                else:
                    if 'SALDO' not in linha_sem_data.upper() and 'EXTRATO' not in linha_sem_data.upper():
                        pending_desc = limpar_caracteres_ilegais(f"{pending_desc} {linha_sem_data}".strip() if pending_desc else linha_sem_data)
                i += 1
    except: pass
    return lancamentos

def processar_pdf_generico_universal(caminho_pdf):
    lancamentos = []
    try:
        reader = PdfReader(caminho_pdf, strict=False)
        data_atual = None
        for pagina in reader.pages:
            texto = pagina.extract_text()
            if not texto: continue
            for linha in texto.split('\n'):
                linha = linha.strip()
                if not linha or any(s in linha.upper() for s in ['SALDO', 'TOTAL', 'SUBTOTAL', 'INICIAL', 'FINAL', 'BLOQUEADO', 'PAGINA', 'TRANSPORTE', 'DISPONIVEL']): 
                    continue
                match_data = re.search(r'(\d{2}/\d{2}(?:/\d{4})?)', linha)
                if match_data:
                    dt_encontrada = match_data.group(1)
                    if len(dt_encontrada) == 5: 
                        dt_encontrada = f"{dt_encontrada}/{datetime.now().year}"
                    data_atual = dt_encontrada
                matches_vals = re.findall(r'(-?\d{1,3}(?:\.\d{3})*,\d{2}\s*[CD]?)', linha, re.IGNORECASE)
                if matches_vals and data_atual:
                    val_str = matches_vals[-1].strip()
                    is_debito = False
                    if val_str.upper().endswith('D') or '-' in val_str:
                        is_debito = True
                    val_limpo = val_str.upper().replace('C', '').replace('D', '').strip()
                    try:
                        v = limpar_valor_monetario(val_limpo)
                        hist = limpar_caracteres_ilegais(linha.replace(data_atual, '').replace(val_str, '').strip())
                        is_debito = deduzir_debito_pela_palavra(hist, is_debito)
                        if v != 0:
                            if is_debito: v = -abs(v)
                            if len(hist) < 2 or 'SALDO' in hist.upper(): continue
                            lancamentos.append({
                                'DESCRIÇÃO': 'EXTRATO BANCARIO',
                                'DATA': data_atual,
                                'VALOR': v,
                                'DÉBITO': '',
                                'CRÉDITO': '',
                                'HISTÓRICO': hist
                            })
                    except: pass
    except: pass
    return lancamentos

def processar_arquivo_pdf(caminho_pdf):
    try:
        reader = PdfReader(caminho_pdf, strict=False)
        texto_completo = "\n".join([p.extract_text() for p in reader.pages[:2]]).upper()
    except: 
        texto_completo = ""
        
    banco_identificado = identificar_banco_inteligente(texto_completo, os.path.basename(caminho_pdf))
    
    lancamentos = []
    if banco_identificado == "BANCO FIBRA":
        lancamentos = processar_pdf_fibra(caminho_pdf)
    elif banco_identificado == "BANCO BRADESCO":
        lancamentos = processar_pdf_bradesco(caminho_pdf)
    elif banco_identificado == "CAIXA ECONOMICA":
        lancamentos = processar_pdf_caixa(caminho_pdf)
    elif banco_identificado == "BANCO SANTANDER":
        lancamentos = processar_pdf_santander(caminho_pdf)
    else:
        lancamentos = processar_pdf_fibra(caminho_pdf)
        if not lancamentos: lancamentos = processar_pdf_santander(caminho_pdf)
        if not lancamentos: lancamentos = processar_pdf_bradesco(caminho_pdf)
        if not lancamentos: lancamentos = processar_pdf_generico_universal(caminho_pdf)
        
    for l in lancamentos:
        l['DESCRIÇÃO'] = banco_identificado
        
    return lancamentos

def gerar_txt_dominio(df):
    linhas_txt = []
    for _, row in df.iterrows():
        hist_limpo = limpar_caracteres_ilegais(str(row['HISTÓRICO'])).replace(';', ' ')
        linhas_txt.append(f"{row['DATA']};{row['DÉBITO'] if pd.notna(row['DÉBITO']) else ''};{row['CRÉDITO'] if pd.notna(row['CRÉDITO']) else ''};{float(row['VALOR']):.2f};{hist_limpo}\n")
    return "".join(linhas_txt)

def processar_razao_dominio(file_bytes, filename):
    df = None
    ext = os.path.splitext(filename)[1].lower()
    
    try:
        if ext == '.xlsx':
            df = pd.read_excel(io.BytesIO(file_bytes), dtype=str, header=None)
        elif ext == '.xls':
            try:
                df = pd.read_excel(io.BytesIO(file_bytes), dtype=str, header=None, engine='xlrd')
            except Exception as e:
                if "Expected BOF record" in str(e) or "corrupt" in str(e).lower():
                    st.session_state['erro_bof_xls'] = True
                    return None
                try:
                    df = pd.read_html(io.BytesIO(file_bytes), header=None)[0].astype(str)
                except Exception:
                    st.session_state['erro_bof_xls'] = True
                    return None
        else:
            for enc in ['utf-8', 'latin1', 'cp1252']:
                for sep in [';', '\t', '|', ',']:
                    try:
                        df = pd.read_csv(io.BytesIO(file_bytes), sep=sep, encoding=enc, dtype=str, header=None, on_bad_lines='skip')
                        if df.shape[1] > 1: break
                    except: continue
                if df is not None and df.shape[1] > 1: break
    except Exception as e:
        return None
    
    if df is None or df.empty: return None
    
    header_row_idx = 0
    for idx, row in df.iterrows():
        row_str = " ".join([str(v) for v in row.values if pd.notna(v)]).upper()
        if ('DATA' in row_str or 'DT' in row_str) and ('VALOR' in row_str or 'DEBITO' in row_str or 'DÉBITO' in row_str or 'CREDITO' in row_str or 'CRÉDITO' in row_str):
            header_row_idx = idx
            break
            
    if header_row_idx > 0:
        df.columns = [str(v).strip().upper() for v in df.iloc[header_row_idx].values]
        df = df.iloc[header_row_idx+1:].copy()
    else:
        df.columns = [str(v).strip().upper() for v in df.iloc[0].values]
        df = df.iloc[1:].copy()
        
    df.columns = [re.sub(r'[^\w\s]', '', c) for c in df.columns]
    cols = list(df.columns)
    
    col_data = next((c for c in cols if any(p in c for p in ['DATA', 'DT'])), None)
    col_deb = next((c for c in cols if any(p in c for p in ['DEBITO', 'DÉBITO', 'SAIDA', 'DEB'])), None)
    col_cred = next((c for c in cols if any(p in c for p in ['CREDITO', 'CRÉDITO', 'ENTRADA', 'CRE'])), None)
    col_val = next((c for c in cols if any(p in c for p in ['VALOR', 'VL'])), None)
    col_hist = next((c for c in cols if any(p in c for p in ['HISTORICO', 'HISTÓRICO', 'HIST', 'COMPLEMENTO', 'LANCAMENTO', 'DESCRI'])), None)
    
    if not col_data: return None
    
    dados = []
    for _, row in df.iterrows():
        dt_raw = str(row[col_data]).strip() if pd.notna(row[col_data]) else ''
        match_dt = re.search(r'(\d{2}/\d{2}/\d{4})', dt_raw)
        if not match_dt: continue
        dt_fmt = match_dt.group(1)
        
        v_ent = 0.0
        v_sai = 0.0
        
        if col_deb and col_cred:
            v_sai = limpar_valor_monetario(row[col_deb]) if pd.notna(row[col_deb]) else 0.0
            v_ent = limpar_valor_monetario(row[col_cred]) if pd.notna(row[col_cred]) else 0.0
        elif col_val and pd.notna(row[col_val]):
            val_num = limpar_valor_monetario(row[col_val])
            if val_num < 0:
                v_sai = abs(val_num)
            else:
                v_ent = val_num
                
        hist_str = limpar_caracteres_ilegais(str(row[col_hist]).strip()) if col_hist and pd.notna(row[col_hist]) else ''
                
        if v_ent != 0 or v_sai != 0:
            dados.append({'DATA': dt_fmt, 'ENTRADAS_RAZAO': v_ent, 'SAIDAS_RAZAO': v_sai, 'HISTÓRICO': hist_str})
            
    if not dados: return None
    df_res = pd.DataFrame(dados)
    df_res['DATA_DT'] = pd.to_datetime(df_res['DATA'], format='%d/%m/%Y')
    return df_res

# ==============================================================================
# CONTROLE DE ESTADO DE NAVEGAÇÃO
# ==============================================================================
if 'pagina_ativa' not in st.session_state:
    st.session_state['pagina_ativa'] = 'home'

def mudar_pagina(nome_pagina):
    st.session_state['pagina_ativa'] = nome_pagina

# ==============================================================================
# BARRA LATERAL DARK MINIMALISTA
# ==============================================================================
st.sidebar.markdown("<p style='font-size: 14px; font-weight: 600; color: #f0f6fc; margin-bottom: 0px;'>Hub Contábil</p>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='font-size: 11px; color: #8b949e; margin-top: 2px;'>Domínio Systems</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

if st.sidebar.button("Início", use_container_width=True, key="sb_home"):
    mudar_pagina('home')

if st.sidebar.button("Conversor de Extratos", use_container_width=True, key="sb_extratos"):
    mudar_pagina('extratos')

if st.sidebar.button("Conciliação com Razão", use_container_width=True, key="sb_razao"):
    mudar_pagina('razao')

st.sidebar.markdown("---")
st.sidebar.markdown("<p style='font-size: 10px; color: #8b949e; text-align: center;'>v7.0 · Auditoria Fina</p>", unsafe_allow_html=True)

# ==============================================================================
# TELA 1: MENU PRINCIPAL (HOME)
# ==============================================================================
if st.session_state['pagina_ativa'] == 'home':
    st.title("Início")
    st.caption("Selecione uma ferramenta abaixo para começar.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_t1, col_t2, col_t3 = st.columns(3)
    
    with col_t1:
        st.markdown("""
            <div class="tool-card">
                <p style="font-size: 20px; margin-bottom: 8px;">📊</p>
                <p style="font-weight: 600; color: #f0f6fc; margin-bottom: 4px; font-size: 15px;">Conversor de Extratos</p>
                <p style="font-size: 12px; color: #8b949e; line-height: 1.4;">Converta extratos para o formato de importação da Domínio.</p>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        if st.button("Acessar", use_container_width=True, key="btn_abrir_extratos"):
            mudar_pagina('extratos')
            st.rerun()
            
    with col_t2:
        st.markdown("""
            <div class="tool-card">
                <p style="font-size: 20px; margin-bottom: 8px;">🔍</p>
                <p style="font-weight: 600; color: #f0f6fc; margin-bottom: 4px; font-size: 15px;">Conciliação com Razão</p>
                <p style="font-size: 12px; color: #8b949e; line-height: 1.4;">Análise automatizada, rolagem de saldos e auditoria de divergências.</p>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        if st.button("Acessar", use_container_width=True, key="btn_abrir_razao"):
            mudar_pagina('razao')
            st.rerun()
        
    with col_t3:
        st.markdown("""
            <div class="tool-card">
                <p style="font-size: 20px; margin-bottom: 8px;">⚙️</p>
                <p style="font-weight: 600; color: #f0f6fc; margin-bottom: 4px; font-size: 15px;">Em Breve</p>
                <p style="font-size: 12px; color: #8b949e; line-height: 1.4;">Utilitários adicionais para relatórios fiscais.</p>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        st.button("Indisponível", use_container_width=True, disabled=True, key="btn_futuro_2")

# ==============================================================================
# TELA 2: FERRAMENTA DE CONVERSÃO DE EXTRATOS
# ==============================================================================
elif st.session_state['pagina_ativa'] == 'extratos':
    col_voltar, col_tit = st.columns([1.2, 8.8])
    with col_voltar:
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        if st.button("← Voltar", use_container_width=True, key="btn_voltar_home"):
            mudar_pagina('home')
            st.rerun()
    with col_tit:
        st.title("Conversor de Extratos Bancários")
    
    st.caption("Faça o upload dos arquivos para gerar os layouts compatíveis com a Domínio.")
    st.markdown("---")

    arquivos = st.file_uploader(
        "Selecione os extratos (PDF, OFX, CSV, Excel)", 
        type=["pdf", "ofx", "csv", "xlsx", "xls"], 
        accept_multiple_files=True
    )

    if arquivos:
        colunas_dominio = ['DESCRIÇÃO', 'DATA', 'VALOR', 'DÉBITO', 'CRÉDITO', 'HISTÓRICO']
        df_modelo = pd.read_excel("Modelo dominio.xlsx") if os.path.exists("Modelo dominio.xlsx") else pd.DataFrame(columns=colunas_dominio)
        if 'DESCRIÇÃO' not in df_modelo.columns: df_modelo = pd.DataFrame(columns=colunas_dominio)
        
        dados_por_arquivo = {}
        todos_lancamentos_brutos = []
        
        for arquivo in arquivos:
            file_bytes, extensao = arquivo.getvalue(), os.path.splitext(arquivo.name)[1].lower()
            lancamentos, data_ini_doc, data_fim_doc = [], None, None
            
            if extensao == '.ofx': lancamentos = processar_ofx(file_bytes, arquivo.name)
            elif extensao in ['.csv', '.xlsx', '.xls']: lancamentos = processar_planilha_universal(file_bytes, arquivo.name)
            elif extensao == '.pdf':
                caminho_temp = f"temp_{arquivo.name}"
                with open(caminho_temp, "wb") as f: f.write(file_bytes)
                data_ini_doc, data_fim_doc = extrair_periodo_extrato(caminho_temp)
                lancamentos = processar_arquivo_pdf(caminho_temp)
                if os.path.exists(caminho_temp): os.remove(caminho_temp)
                
            if lancamentos:
                df_temp = pd.DataFrame(lancamentos)
                df_temp['ARQUIVO_ORIGEM'] = arquivo.name
                dados_por_arquivo[arquivo.name] = {
                    'lancamentos': lancamentos,
                    'data_ini': data_ini_doc,
                    'data_fim': data_fim_doc
                }
                todos_lancamentos_brutos.extend(lancamentos)

        if todos_lancamentos_brutos:
            if len(arquivos) > 1:
                nomes_abas = ["Visão Consolidada"] + [arq.name for arq in arquivos if arq.name in dados_por_arquivo]
            else:
                nomes_abas = [arq.name for arq in arquivos if arq.name in dados_por_arquivo]
                
            abas = st.tabs(nomes_abas)
            
            if len(arquivos) > 1:
                with abas[0]:
                    st.markdown("### Resumo Consolidado")
                    df_geral_bruto = pd.DataFrame(todos_lancamentos_brutos)
                    df_geral_bruto['DATA_DT'] = pd.to_datetime(df_geral_bruto['DATA'], format='%d/%m/%Y', errors='coerce')
                    df_geral_bruto = df_geral_bruto.dropna(subset=['DATA_DT'])
                    
                    dt_min_geral = df_geral_bruto['DATA_DT'].min().date()
                    dt_max_geral = df_geral_bruto['DATA_DT'].max().date()
                    
                    col_g1, col_g2, col_g3 = st.columns([1, 1, 1.5])
                    with col_g1: data_geral_ini = st.date_input("Data Inicial", value=dt_min_geral, min_value=dt_min_geral, max_value=dt_max_geral, format="DD/MM/YYYY", key="gen_ini")
                    with col_g2: data_geral_fim = st.date_input("Data Final", value=dt_max_geral, min_value=dt_min_geral, max_value=dt_max_geral, format="DD/MM/YYYY", key="gen_fim")
                    with col_g3:
                        st.markdown("<div style='height: 2px;'></div>", unsafe_allow_html=True)
                        termo_busca_geral = st.text_input("Busca rápida", placeholder="Filtrar histórico...", key="gen_busca")
                    
                    df_geral_final = df_geral_bruto[(df_geral_bruto['DATA_DT'].dt.date >= data_geral_ini) & (df_geral_bruto['DATA_DT'].dt.date <= data_geral_fim)].copy()
                    if termo_busca_geral:
                        df_geral_final = df_geral_final[df_geral_final['HISTÓRICO'].str.contains(termo_busca_geral, case=False, na=False)]
                    
                    df_geral_final = df_geral_final.drop(columns=['DATA_DT', 'ARQUIVO_ORIGEM'], errors='ignore')[df_modelo.columns]
                    df_geral_final = sanitizar_dataframe(df_geral_final)
                    
                    tot_cred_g = df_geral_final[df_geral_final['VALOR'] > 0]['VALOR'].sum()
                    tot_deb_g = df_geral_final[df_geral_final['VALOR'] < 0]['VALOR'].sum()
                    saldo_liq_g = tot_cred_g + tot_deb_g
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    cg1, cg2, cg3, cg4 = st.columns(4)
                    with cg1:
                        st.markdown(f'<div class="metric-card"><div class="metric-title">Registros</div><div class="metric-value">{len(df_geral_final)}</div></div>', unsafe_allow_html=True)
                    with cg2:
                        st.markdown(f'<div class="metric-card"><div class="metric-title">Entradas</div><div class="metric-value" style="color: #3fb950;">R$ {tot_cred_g:,.2f}</div></div>'.replace(',', 'X').replace('.', ',').replace('X', '.'), unsafe_allow_html=True)
                    with cg3:
                        st.markdown(f'<div class="metric-card"><div class="metric-title">Saídas</div><div class="metric-value" style="color: #f85149;">R$ {abs(tot_deb_g):,.2f}</div></div>'.replace(',', 'X').replace('.', ',').replace('X', '.'), unsafe_allow_html=True)
                    with cg4:
                        color_g = "#3fb950" if saldo_liq_g >= 0 else "#f85149"
                        st.markdown(f'<div class="metric-card"><div class="metric-title">Saldo Líquido</div><div class="metric-value" style="color: {color_g};">R$ {saldo_liq_g:,.2f}</div></div>'.replace(',', 'X').replace('.', ',').replace('X', '.'), unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("##### Prévia Consolidada")
                    st.dataframe(df_geral_final, use_container_width=True, height=280)
                    
                    st.markdown("##### Exportar")
                    cc_dl1, cc_dl2 = st.columns(2)
                    buf_excel_g = io.BytesIO()
                    with pd.ExcelWriter(buf_excel_g, engine='openpyxl') as writer: df_geral_final.to_excel(writer, index=False)
                    cc_dl1.download_button("Baixar Excel (.XLSX)", data=buf_excel_g.getvalue(), file_name=f"consolidado_geral_{data_geral_ini.strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_excel_geral", use_container_width=True)
                    cc_dl2.download_button("Baixar TXT para Domínio", data=gerar_txt_dominio(df_geral_final), file_name=f"importacao_dominio_consolidado_{data_geral_ini.strftime('%d%m%Y')}.txt", mime="text/plain", key="dl_txt_geral", use_container_width=True)
                    st.markdown("---")

            offset_abas = 1 if len(arquivos) > 1 else 0
            for idx_arq, arquivo in enumerate(arquivos):
                if arquivo.name not in dados_por_arquivo: continue
                
                with abas[idx_arq + offset_abas]:
                    info_arq = dados_por_arquivo[arquivo.name]
                    df_bruto = pd.DataFrame(info_arq['lancamentos'])
                    df_bruto['DATA_DT'] = pd.to_datetime(df_bruto['DATA'], format='%d/%m/%Y', errors='coerce')
                    df_bruto = df_bruto.dropna(subset=['DATA_DT'])
                    dt_min_dataset, dt_max_dataset = df_bruto['DATA_DT'].min().date(), df_bruto['DATA_DT'].max().date()
                    
                    data_ini_doc = info_arq['data_ini']
                    data_fim_doc = info_arq['data_fim']
                    
                    if data_ini_doc and data_ini_doc.date():
                        val_ini_def = max(min(data_ini_doc.date(), dt_max_dataset), dt_min_dataset)
                    else:
                        val_ini_def = dt_min_dataset

                    if data_fim_doc and data_fim_doc.date():
                        val_fim_def = max(min(data_fim_doc.date(), dt_max_dataset), dt_min_dataset)
                    else:
                        val_fim_def = dt_max_dataset

                    if val_ini_def > val_fim_def:
                        val_ini_def, val_fim_def = dt_min_dataset, dt_max_dataset
                    
                    with st.container():
                        col_f1, col_f2, col_f3 = st.columns([1, 1, 1.5])
                        with col_f1: data_sel_ini = st.date_input("Data Inicial", value=val_ini_def, min_value=dt_min_dataset, max_value=dt_max_dataset, format="DD/MM/YYYY", key=f"ini_{idx_arq}")
                        with col_f2: data_sel_fim = st.date_input("Data Final", value=val_fim_def, min_value=dt_min_dataset, max_value=dt_max_dataset, format="DD/MM/YYYY", key=f"fim_{idx_arq}")
                        with col_f3:
                            st.markdown("<div style='height: 2px;'></div>", unsafe_allow_html=True)
                            termo_busca = st.text_input("Busca rápida", placeholder="Digite para filtrar...", key=f"busca_{idx_arq}")

                    df_final = df_bruto[(df_bruto['DATA_DT'].dt.date >= data_sel_ini) & (df_bruto['DATA_DT'].dt.date <= data_sel_fim)].copy()
                    if termo_busca:
                        df_final = df_final[df_final['HISTÓRICO'].str.contains(termo_busca, case=False, na=False)]
                    
                    df_final = df_final.drop(columns=['DATA_DT', 'ARQUIVO_ORIGEM'], errors='ignore')[df_modelo.columns]
                    df_final = sanitizar_dataframe(df_final)

                    total_creditos = df_final[df_final['VALOR'] > 0]['VALOR'].sum()
                    total_debitos = df_final[df_final['VALOR'] < 0]['VALOR'].sum()
                    saldo_liquido = total_creditos + total_debitos
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.markdown(f'<div class="metric-card"><div class="metric-title">Registros</div><div class="metric-value">{len(df_final)}</div></div>', unsafe_allow_html=True)
                    with c2:
                        val_cred_fmt = f"R$ {total_creditos:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        st.markdown(f'<div class="metric-card"><div class="metric-title">Entradas</div><div class="metric-value" style="color: #3fb950;">{val_cred_fmt}</div></div>', unsafe_allow_html=True)
                    with c3:
                        val_deb_fmt = f"R$ {abs(total_debitos):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        st.markdown(f'<div class="metric-card"><div class="metric-title">Saídas</div><div class="metric-value" style="color: #f85149;">{val_deb_fmt}</div></div>', unsafe_allow_html=True)
                    with c4:
                        val_liq_fmt = f"R$ {saldo_liquido:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        color_liq = "#3fb950" if saldo_liquido >= 0 else "#f85149"
                        st.markdown(f'<div class="metric-card"><div class="metric-title">Saldo Líquido</div><div class="metric-value" style="color: {color_liq};">{val_liq_fmt}</div></div>', unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("##### Prévia dos Lançamentos")
                    st.dataframe(df_final, use_container_width=True, height=280)
                    
                    st.markdown("##### Exportar")
                    c_dl1, c_dl2 = st.columns(2)
                    buffer_excel = io.BytesIO()
                    with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer: df_final.to_excel(writer, index=False)
                    c_dl1.download_button("Baixar Excel (.XLSX)", data=buffer_excel.getvalue(), file_name=f"lancamentos_{os.path.splitext(arquivo.name)[0]}_{data_sel_ini.strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"excel_{idx_arq}", use_container_width=True)
                    c_dl2.download_button("Baixar TXT para Domínio", data=gerar_txt_dominio(df_final), file_name=f"importacao_dominio_{os.path.splitext(arquivo.name)[0]}_{data_sel_ini.strftime('%d%m%Y')}.txt", mime="text/plain", key=f"txt_{idx_arq}", use_container_width=True)
        else:
            pass

# ==============================================================================
# TELA 3: CONCILIAÇÃO COM O RAZÃO DA DOMÍNIO
# ==============================================================================
elif st.session_state['pagina_ativa'] == 'razao':
    col_voltar, col_tit = st.columns([1.2, 8.8])
    with col_voltar:
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        if st.button("← Voltar", use_container_width=True, key="btn_voltar_home_razao"):
            mudar_pagina('home')
            st.rerun()
    with col_tit:
        st.title("Conciliação: Extrato x Razão da Domínio")
    
    st.caption("Faça a rolagem do Saldo Acumulado, compare Entradas e Saídas e utilize a Auditoria Fina para descobrir divergências.")
    
    st.markdown("""
        <div class="aviso-banner">
            <p>⚠️ <strong>Dica para o Razão da Domínio:</strong> Para evitar erros de leitura, abra o relatório <code>.xls</code> antigo no Excel e salve-o como <strong>CSV (separado por vírgulas)</strong> antes de anexar abaixo.</p>
        </div>
    """, unsafe_allow_html=True)

    # 1. ENTRADA DOS SALDOS INICIAIS
    st.markdown("##### ⚙️ Configuração de Saldos Iniciais")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        saldo_ini_ext = st.number_input("Saldo Inicial do Extrato Bancário (R$)", value=0.0, step=100.0, format="%.2f")
    with col_s2:
        saldo_ini_raz = st.number_input("Saldo Inicial do Razão da Domínio (R$)", value=0.0, step=100.0, format="%.2f")
        
    st.markdown("---")

    col_up1, col_up2 = st.columns(2)
    with col_up1:
        st.markdown("##### 1. Extrato Bancário")
        arq_extrato = st.file_uploader("Envie o Extrato (PDF, OFX, Excel, CSV)", type=["pdf", "ofx", "csv", "xlsx", "xls"], key="up_extrato")
    with col_up2:
        st.markdown("##### 2. Razão da Domínio")
        arq_razao = st.file_uploader("Envie o Razão exportado (XLSX, XLS ou CSV)", type=["csv", "xlsx", "xls"], key="up_razao")

    if arq_extrato and arq_razao:
        ext_bytes, ext_ext = arq_extrato.getvalue(), os.path.splitext(arq_extrato.name)[1].lower()
        lancamentos_ext = []
        if ext_ext == '.ofx': lancamentos_ext = processar_ofx(ext_bytes, arq_extrato.name)
        elif ext_ext in ['.csv', '.xlsx', '.xls']: lancamentos_ext = processar_planilha_universal(ext_bytes, arq_extrato.name)
        elif ext_ext == '.pdf':
            tmp_ext = f"temp_ext_{arq_extrato.name}"
            with open(tmp_ext, "wb") as f: f.write(ext_bytes)
            lancamentos_ext = processar_arquivo_pdf(tmp_ext)
            if os.path.exists(tmp_ext): os.remove(tmp_ext)
            
        raz_bytes, raz_name = arq_razao.getvalue(), arq_razao.name
        
        if 'erro_bof_xls' in st.session_state:
            del st.session_state['erro_bof_xls']
            
        df_razao_bruto = processar_razao_dominio(raz_bytes, raz_name)

        if st.session_state.get('erro_bof_xls', False):
            st.markdown("""
            <div class="alerta-dominio">
                <h4>🚨 Formato .XLS da Domínio Detectado!</h4>
                <p>O sistema Domínio exporta relatórios em <code>.xls</code> usando um formato binário antigo da Microsoft que oculta os valores originais, impossibilitando a leitura perfeita pelo robô.</p>
                <p style="margin-top: 10px;"><strong>💡 Como resolver agora:</strong><br>
                1. Abra esse arquivo <code>.xls</code> no seu Excel e clique em <b>Salvar Como -> Pasta de Trabalho do Excel (.xlsx)</b> ou <b>CSV (separado por vírgulas)</b>.<br>
                2. Ou exporte o Razão diretamente da Domínio escolhendo a opção <b>Salvar como CSV</b>.</p>
            </div>
            """, unsafe_allow_html=True)
            st.stop()

        if lancamentos_ext and df_razao_bruto is not None and not df_razao_bruto.empty:
            df_ext = pd.DataFrame(lancamentos_ext)
            df_ext['DATA_DT'] = pd.to_datetime(df_ext['DATA'], format='%d/%m/%Y', errors='coerce')
            df_ext = df_ext.dropna(subset=['DATA_DT'])
            
            df_ext['ENTRADAS_EXTRATO'] = df_ext['VALOR'].apply(lambda x: x if x > 0 else 0.0)
            df_ext['SAIDAS_EXTRATO'] = df_ext['VALOR'].apply(lambda x: abs(x) if x < 0 else 0.0)
            
            # Agrupamento Diário
            df_ext_agregado = df_ext.groupby('DATA')[['ENTRADAS_EXTRATO', 'SAIDAS_EXTRATO']].sum().reset_index()
            df_ext_agregado['DATA_DT'] = pd.to_datetime(df_ext_agregado['DATA'], format='%d/%m/%Y')

            df_razao_agregado = df_razao_bruto.groupby(['DATA', 'DATA_DT'])[['ENTRADAS_RAZAO', 'SAIDAS_RAZAO']].sum().reset_index()

            df_conciliacao = pd.merge(df_ext_agregado, 
                                     df_razao_agregado[['DATA', 'DATA_DT', 'ENTRADAS_RAZAO', 'SAIDAS_RAZAO']], 
                                     on=['DATA', 'DATA_DT'], how='outer').fillna(0)
            
            df_conciliacao = df_conciliacao.sort_values('DATA_DT')

            # 2. FILTRO DE PERÍODO
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### 📅 Filtrar Período da Conciliação")
            
            dt_min_geral = df_conciliacao['DATA_DT'].min().date()
            dt_max_geral = df_conciliacao['DATA_DT'].max().date()
            
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                data_ini_filtro = st.date_input("Data Inicial", value=dt_min_geral, min_value=dt_min_geral, max_value=dt_max_geral, format="DD/MM/YYYY", key="raz_ini")
            with col_p2:
                data_fim_filtro = st.date_input("Data Final", value=dt_max_geral, min_value=dt_min_geral, max_value=dt_max_geral, format="DD/MM/YYYY", key="raz_fim")
            
            if data_ini_filtro > data_fim_filtro:
                st.warning("⚠️ A data inicial não pode ser maior que a data final.")
                data_ini_filtro, data_fim_filtro = dt_min_geral, dt_max_geral

            df_conciliacao = df_conciliacao[
                (df_conciliacao['DATA_DT'].dt.date >= data_ini_filtro) & 
                (df_conciliacao['DATA_DT'].dt.date <= data_fim_filtro)
            ].copy()

            # 3. CÁLCULO DE ROLAGEM DE SALDO ACUMULADO
            df_conciliacao = df_conciliacao.sort_values('DATA_DT')
            df_conciliacao['SALDO_EXTRATO'] = saldo_ini_ext + df_conciliacao['ENTRADAS_EXTRATO'].cumsum() - df_conciliacao['SAIDAS_EXTRATO'].cumsum()
            df_conciliacao['SALDO_RAZAO'] = saldo_ini_raz + df_conciliacao['ENTRADAS_RAZAO'].cumsum() - df_conciliacao['SAIDAS_RAZAO'].cumsum()

            df_conciliacao['DIF_ENTRADAS'] = df_conciliacao['ENTRADAS_EXTRATO'] - df_conciliacao['ENTRADAS_RAZAO']
            df_conciliacao['DIF_SAIDAS'] = df_conciliacao['SAIDAS_EXTRATO'] - df_conciliacao['SAIDAS_RAZAO']
            df_conciliacao['DIF_SALDO'] = df_conciliacao['SALDO_EXTRATO'] - df_conciliacao['SALDO_RAZAO']
            
            def status_dia(row):
                if abs(row['DIF_ENTRADAS']) < 0.01 and abs(row['DIF_SAIDAS']) < 0.01 and abs(row['DIF_SALDO']) < 0.01:
                    return "✅ Batendo"
                else:
                    return "❌ Divergente"
                
            df_conciliacao['STATUS'] = df_conciliacao.apply(status_dia, axis=1)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 📊 Resultado da Conferência Diária")
            
            saldo_final_ext = df_conciliacao['SALDO_EXTRATO'].iloc[-1] if not df_conciliacao.empty else saldo_ini_ext
            saldo_final_raz = df_conciliacao['SALDO_RAZAO'].iloc[-1] if not df_conciliacao.empty else saldo_ini_raz
            
            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                st.markdown(f'<div class="metric-card"><div class="metric-title">Saldo Final (Extrato)</div><div class="metric-value" style="color: #f0f6fc;">R$ {saldo_final_ext:,.2f}</div></div>'.replace(',', 'X').replace('.', ',').replace('X', '.'), unsafe_allow_html=True)
            with rc2:
                st.markdown(f'<div class="metric-card"><div class="metric-title">Saldo Final (Razão)</div><div class="metric-value" style="color: #f0f6fc;">R$ {saldo_final_raz:,.2f}</div></div>'.replace(',', 'X').replace('.', ',').replace('X', '.'), unsafe_allow_html=True)
            with rc3:
                dif_final = saldo_final_ext - saldo_final_raz
                cor_dif = "#3fb950" if abs(dif_final) < 0.01 else "#f85149"
                st.markdown(f'<div class="metric-card"><div class="metric-title">Diferença de Saldo Final</div><div class="metric-value" style="color: {cor_dif};">R$ {dif_final:,.2f}</div></div>'.replace(',', 'X').replace('.', ',').replace('X', '.'), unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            
            # Formatação limpa para a Tabela Principal
            df_exibicao = df_conciliacao[['DATA', 'ENTRADAS_EXTRATO', 'SAIDAS_EXTRATO', 'SALDO_EXTRATO', 'ENTRADAS_RAZAO', 'SAIDAS_RAZAO', 'SALDO_RAZAO', 'STATUS']].copy()
            df_exibicao.columns = ['Data', 'Entradas Ext. (R$)', 'Saídas Ext. (R$)', 'Saldo Ext. (R$)', 'Entradas Razão (R$)', 'Saídas Razão (R$)', 'Saldo Razão (R$)', 'Status']
            
            for col in ['Entradas Ext. (R$)', 'Saídas Ext. (R$)', 'Saldo Ext. (R$)', 'Entradas Razão (R$)', 'Saídas Razão (R$)', 'Saldo Razão (R$)']:
                df_exibicao[col] = df_exibicao[col].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

            st.dataframe(df_exibicao, use_container_width=True, height=380)

            # 4. AUDITORIA FINA (RAIO-X)
            df_divergencias = df_conciliacao[df_conciliacao['STATUS'] == '❌ Divergente']
            
            if not df_divergencias.empty:
                st.markdown("---")
                st.markdown("### 🔍 Auditoria Fina (Divergências)")
                st.markdown("Descubra exatamente qual lançamento está faltando no sistema comparando os dias divergentes.")
                
                dia_selecionado = st.selectbox("Selecione um dia com divergência para analisar os lançamentos originais:", df_divergencias['DATA'].tolist())
                
                if dia_selecionado:
                    col_aud1, col_aud2 = st.columns(2)
                    with col_aud1:
                        st.markdown("##### 🏦 Lançamentos do Extrato")
                        df_ext_dia = df_ext[df_ext['DATA'] == dia_selecionado][['HISTÓRICO', 'ENTRADAS_EXTRATO', 'SAIDAS_EXTRATO']]
                        df_ext_dia.columns = ['Histórico Bancário', 'Entrada (R$)', 'Saída (R$)']
                        for c in ['Entrada (R$)', 'Saída (R$)']: df_ext_dia[c] = df_ext_dia[c].apply(lambda x: f"{x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                        st.dataframe(df_ext_dia, use_container_width=True, hide_index=True)
                        
                    with col_aud2:
                        st.markdown("##### 🏢 Lançamentos da Domínio")
                        df_raz_dia = df_razao_bruto[df_razao_bruto['DATA'] == dia_selecionado][['HISTÓRICO', 'ENTRADAS_RAZAO', 'SAIDAS_RAZAO']]
                        df_raz_dia.columns = ['Histórico Contábil', 'Entrada (R$)', 'Saída (R$)']
                        for c in ['Entrada (R$)', 'Saída (R$)']: df_raz_dia[c] = df_raz_dia[c].apply(lambda x: f"{x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                        st.dataframe(df_raz_dia, use_container_width=True, hide_index=True)
            else:
                st.success("✨ Conciliação perfeita! Nenhuma divergência encontrada no período selecionado.")

            # 5. EXPORTAÇÃO DO RELATÓRIO DE AUDITORIA
            st.markdown("---")
            st.markdown("##### 📥 Exportar Relatório de Auditoria")
            st.caption("Faça o download do cruzamento diário e da lista de dias divergentes para correção.")
            
            buf_audit = io.BytesIO()
            with pd.ExcelWriter(buf_audit, engine='openpyxl') as writer:
                # Aba 1: Toda a conciliação
                df_exib_export = df_exibicao.copy()
                df_exib_export.to_excel(writer, sheet_name="Resumo Geral", index=False)
                # Aba 2: Só os dias divergentes (se houver)
                if not df_divergencias.empty:
                    df_div_export = df_divergencias[['DATA', 'ENTRADAS_EXTRATO', 'ENTRADAS_RAZAO', 'DIF_ENTRADAS', 'SAIDAS_EXTRATO', 'SAIDAS_RAZAO', 'DIF_SAIDAS', 'SALDO_EXTRATO', 'SALDO_RAZAO', 'DIF_SALDO']]
                    df_div_export.columns = ['Data', 'Entradas Extrato', 'Entradas Razao', 'Diferenca Entradas', 'Saidas Extrato', 'Saidas Razao', 'Diferenca Saidas', 'Saldo Extrato', 'Saldo Razao', 'Diferenca Saldo']
                    df_div_export.to_excel(writer, sheet_name="Dias Divergentes", index=False)

            st.download_button(
                label="Baixar Relatório em Excel (.XLSX)", 
                data=buf_audit.getvalue(), 
                file_name=f"Auditoria_Conciliacao_{data_ini_filtro.strftime('%d%m%Y')}_a_{data_fim_filtro.strftime('%d%m%Y')}.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                use_container_width=False
            )

        else:
            st.warning("⚠️ Ocorreu um problema ao mapear os dados. Certifique-se de que os arquivos possuem as colunas corretas (Data, Valores/Débito/Crédito).")
    else:
        pass
