import streamlit as st
import pandas as pd
import openpyxl
import re
import calendar
import io
import os
import unicodedata
from datetime import datetime
from pypdf import PdfReader
import traceback

# Configuração da página Web
st.set_page_config(
    page_title="Plataforma Contábil Pro", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# ESTILIZAÇÃO CSS DARK MODE
# ==============================================================================
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 100%; }
        .stButton>button { width: 100% !important; border-radius: 6px !important; font-weight: 500 !important; padding: 0.45rem 1rem !important; border: 1px solid #30363d !important; background-color: #21262d !important; color: #c9d1d9 !important; transition: all 0.2s ease; box-shadow: none !important; }
        .stButton>button:hover { background-color: #30363d !important; border-color: #8b949e !important; color: #ffffff !important; }
        .metric-card { background-color: #161b22; border: 1px solid #30363d; padding: 14px; border-radius: 8px; text-align: center; }
        .metric-title { font-size: 11px; color: #8b949e; text-transform: uppercase; font-weight: 600; margin-bottom: 4px; letter-spacing: 0.5px; }
        .metric-value { font-size: 18px; color: #f0f6fc; font-weight: 700; }
        section[data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
        .tool-card { background-color: #161b22; border: 1px solid #30363d; padding: 24px 20px; border-radius: 8px; text-align: center; height: 160px; display: flex; flex-direction: column; justify-content: center; align-items: center; transition: border-color 0.2s ease; }
        .tool-card:hover { border-color: #8b949e; }
        .alerta-dominio { background-color: #3d1c1c; border-left: 5px solid #f85149; padding: 16px; border-radius: 4px; margin-bottom: 20px; }
        .alerta-dominio h4 { margin-top: 0; color: #f85149; font-size: 16px; }
        .alerta-dominio p { margin-bottom: 0; color: #c9d1d9; font-size: 14px; }
        .aviso-banner { background-color: #161b22; border: 1px solid #30363d; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; }
        .aviso-banner p { margin: 0; color: #c9d1d9; font-size: 14px; }
        
        /* Alinhamento perfeito entre date_input e text_input */
        .stTextInput { margin-top: -2px; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# FUNÇÕES DE LIMPEZA E FORMATAÇÃO (MECÂNICAS)
# ==============================================================================
def limpar_caracteres_ilegais(val):
    if isinstance(val, str): return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', val)
    return val

def normalizar_texto(texto):
    if not isinstance(texto, str): return ""
    return ''.join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn').lower()

def formatar_moeda(valor):
    try: return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return "R$ 0,00"

def sanitizar_dataframe(df):
    for col in df.select_dtypes(include=['object', 'string']).columns: df[col] = df[col].apply(limpar_caracteres_ilegais)
    return df

def interpretar_sinal_inteligente(historico_str, valor_num, explicit_nature=""):
    """
    Motor Inteligente Universal:
    Avalia se o lançamento é Entrada (+) ou Saída (-) com base em indicadores
    explícitos e análise semântica do histórico.
    """
    val = abs(float(valor_num))
    ind = normalizar_texto(str(explicit_nature))
    h_norm = normalizar_texto(historico_str)
    
    # 1. Indicador explícito de natureza (C/D, Crédito/Débito, Entrada/Saída)
    if any(k in ind for k in ['d', 'deb', 'saida', 'pagamento', 'debito', 'pagto']):
        return -val
    if any(k in ind for k in ['c', 'cred', 'entrada', 'credito', 'recebimento']):
        return val
        
    # 2. Se o valor já veio negativo do arquivo
    if valor_num < 0:
        return -val
        
    # 3. Análise semântica inteligente por palavras-chave de saída no histórico
    termos_saida = [
        'boleto pago', 'pix env', 'pix enviado', 'ted env', 'doc env', 'pagto', 'pagamento', 
        'tarifa', 'manut', 'cobranca', 'debito', 'saque', 'compra', 'cartao', 
        'transferencia env', 'transf env', 'cpfl', 'darf', 'gps', 'iss', 'imposto',
        'aplicacao', 'aplic', 'investimento', 'estorno deb', 'saida', 'db', 'sispag',
        'concessionaria', 'tributo'
    ]
    
    if any(termo in h_norm for termo in termos_saida):
        return -val
        
    # Padrão para recebimentos, pix recebido, ted recebida, rendimentos, etc.
    return val

def limpar_valor_monetario(v_val):
    if pd.isna(v_val) or v_val == '': return 0.0
    if isinstance(v_val, (int, float)): return float(v_val)
    
    s = str(v_val).strip().upper()
    is_negative = False
    if '-' in s or s.endswith('D') or s.endswith('SAÍDA') or s.endswith('SAIDA') or re.search(r'\(\s*[\d\.,]+\s*\)', s):
        is_negative = True
        
    s = re.sub(r'[^\d,\.]', '', s)
    if not s: return 0.0
    
    if ',' in s and '.' in s:
        last_dot, last_comma = s.rfind('.'), s.rfind(',')
        s = s.replace('.', '').replace(',', '.') if last_comma > last_dot else s.replace(',', '')
    elif ',' in s: 
        s = s.replace(',', '.')
        
    try: 
        val = float(s)
        return -abs(val) if is_negative else abs(val)
    except: 
        return 0.0

def identificar_banco_inteligente(texto_conteudo, filename_str=""):
    combo = (str(texto_conteudo) + " " + str(filename_str)).upper()
    if "ITAÚ" in combo or "ITAU" in combo or "0341" in combo: return "BANCO ITAU"
    elif "FIBRA" in combo or "58.616.418" in combo: return "BANCO FIBRA"
    elif "BRADESCO" in combo: return "BANCO BRADESCO"
    elif "SANTANDER" in combo: return "BANCO SANTANDER"
    elif "CAIXA" in combo: return "CAIXA ECONOMICA"
    elif "BANCO DO BRASIL" in combo or " BB " in combo or combo.startswith("BB"): return "BANCO DO BRASIL"
    elif "NUBANK" in combo or "NU PAGAMENTO" in combo: return "NUBANK"
    elif "INTER" in combo: return "BANCO INTER"
    elif "SICOOB" in combo: return "SICOOB"
    elif "SICREDI" in combo: return "SICREDI"
    else: return "BANCO CONTA CORRENTE"

# ==============================================================================
# MOTORES DE EXTRAÇÃO UNIVERSAL (OFX, PLANILHAS, PDF)
# ==============================================================================
def processar_ofx(file_bytes, filename):
    lancamentos = []
    texto = ""
    for enc in ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']:
        try: texto = file_bytes.decode(enc); break
        except: pass
    if not texto: texto = file_bytes.decode('latin1', errors='ignore')
    
    banco_detectado = identificar_banco_inteligente(texto, filename)
    raw_blocks = re.split(r'<STMTTRN>', texto, flags=re.IGNORECASE)
    
    for block in raw_blocks[1:]:
        block_clean = re.split(r'</STMTTRN>|</BANKTRANLIST>', block, flags=re.IGNORECASE)[0]
        match_date = re.search(r'<DTPOSTED>\s*(\d{4}[-/\.]?\d{2}[-/\.]?\d{2}|\d{8})', block_clean, re.IGNORECASE)
        match_amt = re.search(r'<TRNAMT>\s*([\+\-]?[\d\.\,]+)', block_clean, re.IGNORECASE)
        match_memo = re.search(r'<(?:MEMO|NAME|PAYEE)>\s*(.*?)(?:\r|\n|<|$)', block_clean, re.IGNORECASE)
        match_type = re.search(r'<TRNTYPE>\s*([A-Z]+)', block_clean, re.IGNORECASE)
        
        if match_date and match_amt:
            dt_s = match_date.group(1).replace('-', '').replace('/', '').replace('.', '')
            if len(dt_s) >= 8: data_fmt = f"{dt_s[6:8]}/{dt_s[4:6]}/{dt_s[:4]}"
            else: continue
            
            valor_bruto = limpar_valor_monetario(match_amt.group(1).strip())
            trntype = match_type.group(1).upper() if match_type else ""
            historico = limpar_caracteres_ilegais(match_memo.group(1).strip().replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')) if match_memo else "TRANSACAO OFX"
            
            if 'SALDO' in historico.upper(): continue
            
            # Se for OFX, o TRNTYPE 'DEBIT' ou 'PAYMENT' força negativo, 'CREDIT' força positivo
            if trntype in ['DEBIT', 'PAYMENT', 'FEE']:
                valor_float = -abs(valor_bruto)
            elif trntype in ['CREDIT', 'DEP', 'DIRECTDEP']:
                valor_float = abs(valor_bruto)
            else:
                valor_float = interpretar_sinal_inteligente(historico, valor_bruto)
                
            if valor_float != 0: 
                lancamentos.append({'DESCRIÇÃO': banco_detectado, 'DATA': data_fmt, 'VALOR': valor_float, 'DÉBITO': '', 'CRÉDITO': '', 'HISTÓRICO': historico})
    return lancamentos

def processar_planilha_universal(file_bytes, filename):
    lancamentos, df = [], None
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.xlsx', '.xls']:
        try:
            xls = pd.ExcelFile(io.BytesIO(file_bytes))
            for sheet in xls.sheet_names:
                df_temp = pd.read_excel(xls, sheet_name=sheet, dtype=str)
                if df_temp is not None and not df_temp.empty and df_temp.shape[1] > 1:
                    df = df_temp
                    break
        except Exception:
            try: dfs = pd.read_html(io.BytesIO(file_bytes))
            except Exception: pass
            if dfs: df = dfs[0]
    if df is None:
        for enc in ['utf-8', 'latin1', 'cp1252', 'iso-8859-1', 'utf-16']:
            for sep in [';', ',', '\t', '|']:
                try: df_temp = pd.read_csv(io.BytesIO(file_bytes), sep=sep, encoding=enc, dtype=str)
                except Exception: pass
                if df_temp is not None and df_temp.shape[1] > 1: df = df_temp; break
            if df is not None: break
    if df is None or df.empty: return []
    
    texto_amostra = " ".join([str(v) for row in df.head(10).values for v in row if pd.notna(v)])
    banco_detectado = identificar_banco_inteligente(texto_amostra, filename)
    
    header_idx = None
    for idx, row in df.iterrows():
        row_str = normalizar_texto(" ".join([str(v) for v in row.values if pd.notna(v)]))
        if ('data' in row_str or 'dt' in row_str) and ('valor' in row_str or 'credito' in row_str or 'debito' in row_str or 'lancamento' in row_str or 'historico' in row_str):
            header_idx = idx; break
            
    if header_idx is not None:
        df.columns = [str(v).strip() for v in df.iloc[header_idx].values]
        df = df.iloc[header_idx+1:].copy()
    
    cols_map = {c: normalizar_texto(c) for c in df.columns}
    col_data = next((c for c, nc in cols_map.items() if any(p in nc for p in ['data', 'dt', 'date', 'dia'])), None)
    col_hist = next((c for c, nc in cols_map.items() if any(p in nc for p in ['lancamento', 'historico', 'hist', 'razao social', 'descric', 'detalhe', 'memo'])), None)
    col_val = next((c for c, nc in cols_map.items() if any(p in nc for p in ['valor', 'val', 'monto', 'amount'])), None)
    col_cred = next((c for c, nc in cols_map.items() if any(p in nc for p in ['credito', 'credit', 'entrada', 'vlr_cred', 'crd'])), None)
    col_deb = next((c for c, nc in cols_map.items() if any(p in nc for p in ['debito', 'debit', 'saida', 'vlr_deb', 'deb'])), None)
    col_tipo = next((c for c, nc in cols_map.items() if any(p in nc for p in ['tipo', 'natureza', 'operacao', 'c/d'])), None)

    if not col_data: return []
    
    for _, row in df.iterrows():
        dt_raw = str(row[col_data]).strip() if pd.notna(row[col_data]) else ''
        if dt_raw.upper() in ['TOTAL', 'ÚLTIMOS LANÇAMENTOS', 'ULTIMOS LANCAMENTOS', 'SALDOS INVEST FÁCIL / PLUS', 'NAN', 'SALDO ANTERIOR']:
            if dt_raw.upper() == 'TOTAL': break
            continue
            
        match_dt = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', dt_raw)
        if not match_dt: continue
        dt_fmt = match_dt.group(1).replace('-', '/')
        
        hist_raw = limpar_caracteres_ilegais(str(row[col_hist]).strip()) if col_hist and pd.notna(row[col_hist]) else 'MOVIMENTO BANCARIO'
        hist_fmt = hist_raw if hist_raw.lower() != 'nan' else 'MOVIMENTO BANCARIO'
        if any(term in hist_fmt.upper() for term in ['SALDO', 'SUBTOTAL', 'TOTAL', 'TRANSPORTAR']): continue
        
        valor_float = 0.0
        
        if col_cred or col_deb:
            v_cred = limpar_valor_monetario(row[col_cred]) if col_cred and pd.notna(row[col_cred]) else 0.0
            v_deb = limpar_valor_monetario(row[col_deb]) if col_deb and pd.notna(row[col_deb]) else 0.0
            if v_cred != 0: valor_float = abs(v_cred)
            elif v_deb != 0: valor_float = -abs(v_deb)
        elif col_val and pd.notna(row[col_val]):
            val_cru = limpar_valor_monetario(row[col_val])
            tipo_str = str(row[col_tipo]).strip() if col_tipo and pd.notna(row[col_tipo]) else ""
            valor_float = interpretar_sinal_inteligente(hist_fmt, val_cru, tipo_str)

        if valor_float != 0:
            lancamentos.append({'DESCRIÇÃO': banco_detectado, 'DATA': dt_fmt, 'VALOR': valor_float, 'DÉBITO': '', 'CRÉDITO': '', 'HISTÓRICO': hist_fmt})
    return lancamentos

def extrair_periodo_extrato(caminho_pdf):
    try:
        reader = PdfReader(caminho_pdf, strict=False)
        texto = "".join([p.extract_text() for p in reader.pages[:3]])
        datas = re.findall(r'(\d{2}/\d{2}/\d{4})', texto)
        if len(datas) >= 2: return datetime.strptime(datas[0], '%d/%m/%Y'), datetime.strptime(datas[1], '%d/%m/%Y')
    except: pass
    return None, None

def processar_arquivo_pdf(caminho_pdf):
    lancamentos = []
    try:
        reader = PdfReader(caminho_pdf, strict=False)
        texto_completo = ""
        for pagina in reader.pages:
            texto_completo += (pagina.extract_text() or "") + "\n"
            
        banco_identificado = identificar_banco_inteligente(texto_completo, os.path.basename(caminho_pdf))
        linhas = [l.strip() for l in texto_completo.split('\n') if l.strip()]
        date_regex = re.compile(r'^(\d{2}/\d{2}/\d{4})')
        
        i = 0
        while i < len(linhas):
            linha = linhas[i]
            match_date = date_regex.match(linha)
            if match_date:
                data_str = match_date.group(1)
                bloco_linhas = [linha]
                j = i + 1
                while j < len(linhas):
                    next_linha = linhas[j]
                    if date_regex.match(next_linha) or 'SALDO' in next_linha.upper() or 'Página' in next_linha:
                        break
                    bloco_linhas.append(next_linha)
                    j += 1
                
                texto_bloco = " ".join(bloco_linhas)
                vals = re.findall(r'(?:R\$)?\s*(-?[\d\.]+,\d{2})', texto_bloco)
                
                if vals:
                    val_str = vals[-1]
                    v_num = limpar_valor_monetario(val_str)
                    
                    hist = texto_bloco.replace(data_str, '')
                    for v in vals:
                        hist = hist.replace(v, '').replace('R$', '')
                    hist = re.sub(r'\s+', ' ', hist).strip()
                    
                    if 'SALDO' not in hist.upper() and v_num != 0:
                        v_final = interpretar_sinal_inteligente(hist, v_num)
                        lancamentos.append({'DESCRIÇÃO': banco_identificado, 'DATA': data_str, 'VALOR': v_final, 'DÉBITO': '', 'CRÉDITO': '', 'HISTÓRICO': limpar_caracteres_ilegais(hist)})
                i = j - 1
            i += 1
    except Exception as e:
        print(f"Erro no processamento PDF universal: {e}")
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
            xls = pd.ExcelFile(io.BytesIO(file_bytes))
            for sheet in xls.sheet_names:
                df_temp = pd.read_excel(xls, sheet_name=sheet, dtype=str, header=None)
                if df_temp is not None and not df_temp.empty and df_temp.shape[1] > 1:
                    df = df_temp
                    break
        elif ext == '.xls':
            try: df = pd.read_excel(io.BytesIO(file_bytes), dtype=str, header=None, engine='xlrd')
            except Exception as e:
                if "Expected BOF record" in str(e) or "corrupt" in str(e).lower():
                    st.session_state['erro_bof_xls'] = True
                    return None
                try: df = pd.read_html(io.BytesIO(file_bytes), header=None)[0].astype(str)
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
    except Exception: return None
    
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
        match_dt = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', dt_raw)
        if not match_dt: continue
        dt_fmt = match_dt.group(1).replace('-', '/')
        
        v_ent, v_sai = 0.0, 0.0
        
        if col_deb and col_cred:
            v_sai = abs(limpar_valor_monetario(row[col_deb])) if pd.notna(row[col_deb]) else 0.0
            v_ent = abs(limpar_valor_monetario(row[col_cred])) if pd.notna(row[col_cred]) else 0.0
        elif col_val and pd.notna(row[col_val]):
            val_num = limpar_valor_monetario(row[col_val])
            if val_num < 0: v_sai = abs(val_num)
            else: v_ent = val_num
                
        hist_str = limpar_caracteres_ilegais(str(row[col_hist]).strip()) if col_hist and pd.notna(row[col_hist]) else 'LANCAMENTO RAZAO'
                
        if v_ent != 0 or v_sai != 0:
            dados.append({'DATA': dt_fmt, 'ENTRADAS_RAZAO': v_ent, 'SAIDAS_RAZAO': v_sai, 'HISTÓRICO': hist_str})
            
    if not dados: return None
    df_res = pd.DataFrame(dados)
    df_res['DATA_DT'] = pd.to_datetime(df_res['DATA'], dayfirst=True, errors='coerce')
    return df_res.dropna(subset=['DATA_DT'])

# ==============================================================================
# CONTROLE DE ESTADO DE NAVEGAÇÃO
# ==============================================================================
if 'pagina_ativa' not in st.session_state: st.session_state['pagina_ativa'] = 'home'
def mudar_pagina(nome_pagina): st.session_state['pagina_ativa'] = nome_pagina

# ==============================================================================
# BARRA LATERAL DARK MINIMALISTA
# ==============================================================================
st.sidebar.markdown("<p style='font-size: 14px; font-weight: 600; color: #f0f6fc; margin-bottom: 0px;'>Hub Contábil</p>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='font-size: 11px; color: #8b949e; margin-top: 2px;'>Domínio Systems</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

if st.sidebar.button("Início", use_container_width=True, key="sb_home"): mudar_pagina('home')
if st.sidebar.button("Conversor de Extratos", use_container_width=True, key="sb_extratos"): mudar_pagina('extratos')
if st.sidebar.button("Conciliação com Razão", use_container_width=True, key="sb_razao"): mudar_pagina('razao')
st.sidebar.markdown("---")
st.sidebar.markdown("<p style='font-size: 10px; color: #8b949e; text-align: center;'>v9.1 · Clear View</p>", unsafe_allow_html=True)

# ==============================================================================
# TELA 1: MENU PRINCIPAL (HOME)
# ==============================================================================
if st.session_state['pagina_ativa'] == 'home':
    st.title("Início")
    st.caption("Selecione uma ferramenta abaixo para começar.")
    st.markdown("<br>", unsafe_allow_html=True)
    col_t1, col_t2, col_t3 = st.columns(3)
    
    with col_t1:
        st.markdown("""<div class="tool-card"><p style="font-size: 20px; margin-bottom: 8px;">📊</p><p style="font-weight: 600; color: #f0f6fc; margin-bottom: 4px; font-size: 15px;">Conversor de Extratos</p><p style="font-size: 12px; color: #8b949e; line-height: 1.4;">Converta extratos para o formato de importação da Domínio.</p></div>""", unsafe_allow_html=True)
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        if st.button("Acessar", use_container_width=True, key="btn_abrir_extratos"):
            mudar_pagina('extratos')
            st.rerun()
            
    with col_t2:
        st.markdown("""<div class="tool-card"><p style="font-size: 20px; margin-bottom: 8px;">🔍</p><p style="font-weight: 600; color: #f0f6fc; margin-bottom: 4px; font-size: 15px;">Conciliação com Razão</p><p style="font-size: 12px; color: #8b949e; line-height: 1.4;">Análise automatizada, rolagem de saldos e auditoria de divergências.</p></div>""", unsafe_allow_html=True)
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        if st.button("Acessar", use_container_width=True, key="btn_abrir_razao"):
            mudar_pagina('razao')
            st.rerun()
        
    with col_t3:
        st.markdown("""<div class="tool-card"><p style="font-size: 20px; margin-bottom: 8px;">⚙️</p><p style="font-weight: 600; color: #f0f6fc; margin-bottom: 4px; font-size: 15px;">Em Breve</p><p style="font-size: 12px; color: #8b949e; line-height: 1.4;">Utilitários adicionais para relatórios fiscais.</p></div>""", unsafe_allow_html=True)
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
    with col_tit: st.title("Conversor de Extratos Bancários")
    st.caption("Faça o upload dos arquivos para gerar os layouts compatíveis com a Domínio.")
    st.markdown("---")

    arquivos = st.file_uploader("Selecione os extratos (PDF, OFX, CSV, Excel)", type=["pdf", "ofx", "csv", "xlsx", "xls"], accept_multiple_files=True)

    if arquivos:
        try:
            colunas_dominio = ['DESCRIÇÃO', 'DATA', 'VALOR', 'DÉBITO', 'CRÉDITO', 'HISTÓRICO']
            df_modelo = pd.read_excel("Modelo dominio.xlsx") if os.path.exists("Modelo dominio.xlsx") else pd.DataFrame(columns=colunas_dominio)
            if 'DESCRIÇÃO' not in df_modelo.columns: df_modelo = pd.DataFrame(columns=colunas_dominio)
            
            dados_por_arquivo, todos_lancamentos_brutos = {}, []
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
                    dados_por_arquivo[arquivo.name] = {'lancamentos': lancamentos, 'data_ini': data_ini_doc, 'data_fim': data_fim_doc}
                    todos_lancamentos_brutos.extend(lancamentos)

            if todos_lancamentos_brutos:
                nomes_abas = ["Visão Consolidada"] + [arq.name for arq in arquivos if arq.name in dados_por_arquivo] if len(arquivos) > 1 else [arq.name for arq in arquivos if arq.name in dados_por_arquivo]
                abas = st.tabs(nomes_abas)
                
                if len(arquivos) > 1:
                    with abas[0]:
                        st.markdown("### Resumo Consolidado")
                        df_geral_bruto = pd.DataFrame(todos_lancamentos_brutos)
                        df_geral_bruto['DATA_DT'] = pd.to_datetime(df_geral_bruto['DATA'], dayfirst=True, errors='coerce')
                        df_geral_bruto = df_geral_bruto.dropna(subset=['DATA_DT'])
                        
                        if df_geral_bruto.empty:
                            st.warning("Nenhum lançamento válido encontrado.")
                        else:
                            dt_min_geral, dt_max_geral = df_geral_bruto['DATA_DT'].min().date(), df_geral_bruto['DATA_DT'].max().date()
                            col_g1, col_g2, col_g3 = st.columns([1, 1, 1.5])
                            with col_g1: data_geral_ini = st.date_input("Data Inicial", value=dt_min_geral, min_value=dt_min_geral, max_value=dt_max_geral, format="DD/MM/YYYY", key="gen_ini")
                            with col_g2: data_geral_fim = st.date_input("Data Final", value=dt_max_geral, min_value=dt_min_geral, max_value=dt_max_geral, format="DD/MM/YYYY", key="gen_fim")
                            with col_g3: 
                                st.markdown("<label style='font-size:14px; font-weight:400; color:inherit;'>Busca rápida</label>", unsafe_allow_html=True)
                                termo_busca_geral = st.text_input("Busca rápida", placeholder="Filtrar histórico...", label_visibility="collapsed", key="gen_busca")
                            
                            df_geral_final = df_geral_bruto[(df_geral_bruto['DATA_DT'].dt.date >= data_geral_ini) & (df_geral_bruto['DATA_DT'].dt.date <= data_geral_fim)].copy()
                            if termo_busca_geral: df_geral_final = df_geral_final[df_geral_final['HISTÓRICO'].str.contains(termo_busca_geral, case=False, na=False)]
                            
                            df_geral_final = df_geral_final.drop(columns=['DATA_DT', 'ARQUIVO_ORIGEM'], errors='ignore')[df_modelo.columns]
                            df_geral_final = sanitizar_dataframe(df_geral_final)
                            
                            tot_cred_g, tot_deb_g = df_geral_final[df_geral_final['VALOR'] > 0]['VALOR'].sum(), df_geral_final[df_geral_final['VALOR'] < 0]['VALOR'].sum()
                            saldo_liq_g = tot_cred_g + tot_deb_g
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            cg1, cg2, cg3, cg4 = st.columns(4)
                            with cg1: st.markdown(f'<div class="metric-card"><div class="metric-title">Registros</div><div class="metric-value">{len(df_geral_final)}</div></div>', unsafe_allow_html=True)
                            with cg2: st.markdown(f'<div class="metric-card"><div class="metric-title">Entradas</div><div class="metric-value" style="color: #3fb950;">{formatar_moeda(tot_cred_g)}</div></div>', unsafe_allow_html=True)
                            with cg3: st.markdown(f'<div class="metric-card"><div class="metric-title">Saídas</div><div class="metric-value" style="color: #f85149;">{formatar_moeda(abs(tot_deb_g))}</div></div>', unsafe_allow_html=True)
                            with cg4:
                                color_g = "#3fb950" if saldo_liq_g >= 0 else "#f85149"
                                st.markdown(f'<div class="metric-card"><div class="metric-title">Saldo Líquido</div><div class="metric-value" style="color: {color_g};">{formatar_moeda(saldo_liq_g)}</div></div>', unsafe_allow_html=True)

                            st.markdown("<br>", unsafe_allow_html=True); st.markdown("##### Prévia Consolidada")
                            st.dataframe(df_geral_final, use_container_width=True, height=280)
                            
                            st.markdown("##### Exportar")
                            cc_dl1, cc_dl2 = st.columns(2)
                            buf_excel_g = io.BytesIO()
                            with pd.ExcelWriter(buf_excel_g, engine='openpyxl') as writer: df_geral_final.to_excel(writer, index=False)
                            cc_dl1.download_button("Baixar Excel (.XLSX)", data=buf_excel_g.getvalue(), file_name=f"consolidado_geral_{data_geral_ini.strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_excel_geral", use_container_width=True)
                            cc_dl2.download_button("Baixar TXT para Domínio", data=gerar_txt_dominio(df_geral_final), file_name=f"importacao_dominio_consolidado_{data_geral_ini.strftime('%d%m%Y')}.txt", mime="text/plain", key="dl_txt_geral", use_container_width=True)

                offset_abas = 1 if len(arquivos) > 1 else 0
                for idx_arq, arquivo in enumerate(arquivos):
                    if arquivo.name not in dados_por_arquivo: continue
                    with abas[idx_arq + offset_abas]:
                        info_arq = dados_por_arquivo[arquivo.name]
                        df_bruto = pd.DataFrame(info_arq['lancamentos'])
                        df_bruto['DATA_DT'] = pd.to_datetime(df_bruto['DATA'], dayfirst=True, errors='coerce')
                        df_bruto = df_bruto.dropna(subset=['DATA_DT'])
                        
                        if df_bruto.empty:
                            st.warning("Não há dados válidos neste arquivo.")
                            continue
                            
                        dt_min_dataset, dt_max_dataset = df_bruto['DATA_DT'].min().date(), df_bruto['DATA_DT'].max().date()
                        
                        data_ini_doc, data_fim_doc = info_arq['data_ini'], info_arq['data_fim']
                        val_ini_def = max(min(data_ini_doc.date(), dt_max_dataset), dt_min_dataset) if data_ini_doc and data_ini_doc.date() else dt_min_dataset
                        val_fim_def = max(min(data_fim_doc.date(), dt_max_dataset), dt_min_dataset) if data_fim_doc and data_fim_doc.date() else dt_max_dataset
                        if val_ini_def > val_fim_def: val_ini_def, val_fim_def = dt_min_dataset, dt_max_dataset
                        
                        with st.container():
                            col_f1, col_f2, col_f3 = st.columns([1, 1, 1.5])
                            with col_f1: data_sel_ini = st.date_input("Data Inicial", value=val_ini_def, min_value=dt_min_dataset, max_value=dt_max_dataset, format="DD/MM/YYYY", key=f"ini_{idx_arq}")
                            with col_f2: data_sel_fim = st.date_input("Data Final", value=val_fim_def, min_value=dt_min_dataset, max_value=dt_max_dataset, format="DD/MM/YYYY", key=f"fim_{idx_arq}")
                            with col_f3: 
                                st.markdown("<label style='font-size:14px; font-weight:400; color:inherit;'>Busca rápida</label>", unsafe_allow_html=True)
                                termo_busca = st.text_input("Busca rápida", placeholder="Digite para filtrar...", label_visibility="collapsed", key=f"busca_{idx_arq}")

                        df_final = df_bruto[(df_bruto['DATA_DT'].dt.date >= data_sel_ini) & (df_bruto['DATA_DT'].dt.date <= data_sel_fim)].copy()
                        if termo_busca: df_final = df_final[df_final['HISTÓRICO'].str.contains(termo_busca, case=False, na=False)]
                        
                        df_final = df_final.drop(columns=['DATA_DT', 'ARQUIVO_ORIGEM'], errors='ignore')[df_modelo.columns]
                        df_final = sanitizar_dataframe(df_final)

                        total_creditos, total_debitos = df_final[df_final['VALOR'] > 0]['VALOR'].sum(), df_final[df_final['VALOR'] < 0]['VALOR'].sum()
                        saldo_liquido = total_creditos + total_debitos
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        c1, c2, c3, c4 = st.columns(4)
                        with c1: st.markdown(f'<div class="metric-card"><div class="metric-title">Registros</div><div class="metric-value">{len(df_final)}</div></div>', unsafe_allow_html=True)
                        with c2: st.markdown(f'<div class="metric-card"><div class="metric-title">Entradas</div><div class="metric-value" style="color: #3fb950;">{formatar_moeda(total_creditos)}</div></div>', unsafe_allow_html=True)
                        with c3: st.markdown(f'<div class="metric-card"><div class="metric-title">Saídas</div><div class="metric-value" style="color: #f85149;">{formatar_moeda(abs(total_debitos))}</div></div>', unsafe_allow_html=True)
                        with c4:
                            color_liq = "#3fb950" if saldo_liquido >= 0 else "#f85149"
                            st.markdown(f'<div class="metric-card"><div class="metric-title">Saldo Líquido</div><div class="metric-value" style="color: {color_liq};">{formatar_moeda(saldo_liquido)}</div></div>', unsafe_allow_html=True)

                        st.markdown("<br>", unsafe_allow_html=True); st.markdown("##### Prévia dos Lançamentos")
                        st.dataframe(df_final, use_container_width=True, height=280)
                        
                        st.markdown("##### Exportar")
                        c_dl1, c_dl2 = st.columns(2)
                        buffer_excel = io.BytesIO()
                        with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer: df_final.to_excel(writer, index=False)
                        c_dl1.download_button("Baixar Excel (.XLSX)", data=buffer_excel.getvalue(), file_name=f"lancamentos_{os.path.splitext(arquivo.name)[0]}_{data_sel_ini.strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"excel_{idx_arq}", use_container_width=True)
                        c_dl2.download_button("Baixar TXT para Domínio", data=gerar_txt_dominio(df_final), file_name=f"importacao_dominio_{os.path.splitext(arquivo.name)[0]}_{data_sel_ini.strftime('%d%m%Y')}.txt", mime="text/plain", key=f"txt_{idx_arq}", use_container_width=True)
        except Exception as e:
            st.error(f"🛑 Ocorreu um erro na aba extratos. Detalhes: {e}")

# ==============================================================================
# TELA 3: CONCILIAÇÃO COM O RAZÃO DA DOMÍNIO
# ==============================================================================
elif st.session_state['pagina_ativa'] == 'razao':
    col_voltar, col_tit = st.columns([1.2, 8.8])
    with col_voltar:
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        if st.button("← Voltar", use_container_width=True, key="btn_voltar_home_razao"): mudar_pagina('home'); st.rerun()
    with col_tit: st.title("Conciliação: Extrato x Razão da Domínio")
    
    st.caption("Acompanhe a conferência diária comparando diretamente as Entradas e Saídas do Extrato com o Razão da Domínio.")
    st.markdown("""<div class="aviso-banner"><p>⚠️ <strong>Dica para o Razão da Domínio:</strong> Para evitar erros de leitura, abra o relatório <code>.xls</code> antigo no Excel e salve-o como <strong>CSV (separado por vírgulas)</strong> antes de anexar abaixo.</p></div>""", unsafe_allow_html=True)

    st.markdown("##### 📁 Arquivos de Importação")
    col_up1, col_up2 = st.columns(2)
    with col_up1: arq_extrato = st.file_uploader("1º - Envie o Extrato (PDF, OFX, Excel, CSV)", type=["pdf", "ofx", "csv", "xlsx", "xls"], key="up_extrato")
    with col_up2: arq_razao = st.file_uploader("2º - Envie o Razão exportado (CSV ou XLSX)", type=["csv", "xlsx", "xls"], key="up_razao")

    if arq_extrato and arq_razao:
        try:
            ext_bytes, ext_ext = arq_extrato.getvalue(), os.path.splitext(arq_extrato.name)[1].lower()
            lancamentos_ext = []
            if ext_ext == '.ofx': lancamentos_ext = processar_ofx(ext_bytes, arq_extrato.name)
            elif ext_ext in ['.csv', '.xlsx', '.xls']: lancamentos_ext = processar_planilha_universal(ext_bytes, arq_extrato.name)
            elif ext_ext == '.pdf':
                tmp_ext = f"temp_ext_conc_{arq_extrato.name}"
                with open(tmp_ext, "wb") as f: f.write(ext_bytes)
                lancamentos_ext = processar_arquivo_pdf(tmp_ext)
                if os.path.exists(tmp_ext): os.remove(tmp_ext)
                
            raz_bytes, raz_name = arq_razao.getvalue(), arq_razao.name
            
            if 'erro_bof_xls' in st.session_state: del st.session_state['erro_bof_xls']
            df_razao_bruto = processar_razao_dominio(raz_bytes, raz_name)

            if st.session_state.get('erro_bof_xls', False):
                st.markdown("""<div class="alerta-dominio"><h4>🚨 Formato .XLS da Domínio Detectado!</h4><p>O sistema Domínio exporta relatórios em <code>.xls</code> usando um formato binário antigo da Microsoft que oculta os valores originais.</p><p style="margin-top: 10px;"><strong>💡 Como resolver agora:</strong><br>Abra o arquivo <code>.xls</code> no seu Excel e clique em <b>Salvar Como -> CSV (separado por vírgulas)</b> ou <b>Pasta de Trabalho do Excel (.xlsx)</b> e anexe novamente.</p></div>""", unsafe_allow_html=True)
                st.stop()

            if lancamentos_ext and df_razao_bruto is not None and not df_razao_bruto.empty:
                # ---------------- PREPARAÇÃO DOS DADOS ----------------
                df_ext = pd.DataFrame(lancamentos_ext)
                df_ext['DATA_DT'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
                df_ext = df_ext.dropna(subset=['DATA_DT'])
                
                df_ext['ENTRADAS_EXTRATO'] = df_ext['VALOR'].apply(lambda x: x if x > 0 else 0.0)
                df_ext['SAIDAS_EXTRATO'] = df_ext['VALOR'].apply(lambda x: abs(x) if x < 0 else 0.0)
                df_ext_agregado = df_ext.groupby('DATA_DT')[['ENTRADAS_EXTRATO', 'SAIDAS_EXTRATO']].sum().reset_index()
                
                df_razao_bruto['DATA_DT'] = pd.to_datetime(df_razao_bruto['DATA'], dayfirst=True, errors='coerce')
                df_razao_bruto = df_razao_bruto.dropna(subset=['DATA_DT'])
                df_razao_agregado = df_razao_bruto.groupby('DATA_DT')[['ENTRADAS_RAZAO', 'SAIDAS_RAZAO']].sum().reset_index()

                for col in ['ENTRADAS_EXTRATO', 'SAIDAS_EXTRATO']:
                    if col not in df_ext_agregado.columns: df_ext_agregado[col] = 0.0
                for col in ['ENTRADAS_RAZAO', 'SAIDAS_RAZAO']:
                    if col not in df_razao_agregado.columns: df_razao_agregado[col] = 0.0

                df_conciliacao = pd.merge(df_ext_agregado, df_razao_agregado, on='DATA_DT', how='outer').fillna(0.0)
                df_conciliacao = df_conciliacao.sort_values('DATA_DT')
                df_conciliacao['DATA_EXIBICAO'] = df_conciliacao['DATA_DT'].dt.strftime('%d/%m/%Y')

                if df_conciliacao.empty:
                    st.warning("⚠️ Não conseguimos cruzar as datas. Verifique se os arquivos contêm datas válidas.")
                    st.stop()

                # ---------------- FILTRO DE PERÍODO ----------------
                st.markdown("---")
                st.markdown("##### 📅 Filtro de Período da Conciliação")
                
                dt_min_geral, dt_max_geral = df_conciliacao['DATA_DT'].min().date(), df_conciliacao['DATA_DT'].max().date()
                col_p1, col_p2 = st.columns(2)
                with col_p1: data_ini_filtro = st.date_input("Data Inicial", value=dt_min_geral, min_value=dt_min_geral, max_value=dt_max_geral, format="DD/MM/YYYY", key="raz_ini")
                with col_p2: data_fim_filtro = st.date_input("Data Final", value=dt_max_geral, min_value=dt_min_geral, max_value=dt_max_geral, format="DD/MM/YYYY", key="raz_fim")
                
                if data_ini_filtro > data_fim_filtro:
                    st.warning("⚠️ A data inicial não pode ser maior que a data final.")
                    data_ini_filtro, data_fim_filtro = dt_min_geral, dt_max_geral

                df_conciliacao = df_conciliacao[(df_conciliacao['DATA_DT'].dt.date >= data_ini_filtro) & (df_conciliacao['DATA_DT'].dt.date <= data_fim_filtro)].copy()

                if df_conciliacao.empty:
                    st.info("Nenhuma movimentação no período selecionado.")
                    st.stop()

                # ---------------- CÁLCULOS DE DIFERENÇAS ----------------
                df_conciliacao = df_conciliacao.sort_values('DATA_DT')
                df_conciliacao['DIF_ENTRADAS'] = df_conciliacao['ENTRADAS_EXTRATO'] - df_conciliacao['ENTRADAS_RAZAO']
                df_conciliacao['DIF_SAIDAS'] = df_conciliacao['SAIDAS_EXTRATO'] - df_conciliacao['SAIDAS_RAZAO']
                
                df_conciliacao['STATUS'] = df_conciliacao.apply(
                    lambda row: "✅ Batendo" if abs(row['DIF_ENTRADAS']) < 0.01 and abs(row['DIF_SAIDAS']) < 0.01 else "❌ Divergente", 
                    axis=1
                )
                
                # ---------------- 4 CARDS RESUMO ----------------
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("### 📊 Resultado da Conferência Diária")
                
                tot_ent_ext = df_conciliacao['ENTRADAS_EXTRATO'].sum()
                tot_sai_ext = df_conciliacao['SAIDAS_EXTRATO'].sum()
                tot_ent_raz = df_conciliacao['ENTRADAS_RAZAO'].sum()
                tot_sai_raz = df_conciliacao['SAIDAS_RAZAO'].sum()
                
                rc1, rc2, rc3, rc4 = st.columns(4)
                with rc1: st.markdown(f'<div class="metric-card"><div class="metric-title">Total Entradas (Extrato)</div><div class="metric-value" style="color: #3fb950;">{formatar_moeda(tot_ent_ext)}</div></div>', unsafe_allow_html=True)
                with rc2: st.markdown(f'<div class="metric-card"><div class="metric-title">Total Entradas (Razão)</div><div class="metric-value" style="color: #3fb950;">{formatar_moeda(tot_ent_raz)}</div></div>', unsafe_allow_html=True)
                with rc3: st.markdown(f'<div class="metric-card"><div class="metric-title">Total Saídas (Extrato)</div><div class="metric-value" style="color: #f85149;">{formatar_moeda(abs(tot_sai_ext))}</div></div>', unsafe_allow_html=True)
                with rc4: st.markdown(f'<div class="metric-card"><div class="metric-title">Total Saídas (Razão)</div><div class="metric-value" style="color: #f85149;">{formatar_moeda(abs(tot_sai_raz))}</div></div>', unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                
                # ---------------- TABELA DE EXIBIÇÃO ----------------
                df_exibicao = df_conciliacao[['DATA_EXIBICAO', 'ENTRADAS_EXTRATO', 'ENTRADAS_RAZAO', 'DIF_ENTRADAS', 'SAIDAS_EXTRATO', 'SAIDAS_RAZAO', 'DIF_SAIDAS', 'STATUS']].copy()
                df_exibicao.columns = ['Data', 'Entradas Ext. (R$)', 'Entradas Razão (R$)', 'Dif. Entradas (R$)', 'Saídas Ext. (R$)', 'Saídas Razão (R$)', 'Dif. Saídas (R$)', 'Status']
                
                st.dataframe(
                    df_exibicao, 
                    use_container_width=True, 
                    height=380,
                    column_config={
                        "Entradas Ext. (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Entradas Razão (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Dif. Entradas (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Saídas Ext. (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Saídas Razão (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Dif. Saídas (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                    }
                )

                # ---------------- EXPORTAÇÃO EXCEL BLINDADA ----------------
                st.markdown("---")
                st.markdown("##### 📥 Exportar Relatório de Conciliação")
                st.caption("Faça o download da conferência completa em formato Excel.")
                
                buf_audit = io.BytesIO()
                with pd.ExcelWriter(buf_audit, engine='openpyxl') as writer:
                    df_exib_excel = df_exibicao.copy()
                    for col in ['Entradas Ext. (R$)', 'Entradas Razão (R$)', 'Dif. Entradas (R$)', 'Saídas Ext. (R$)', 'Saídas Razão (R$)', 'Dif. Saídas (R$)']:
                        df_exib_excel[col] = df_exib_excel[col].apply(formatar_moeda)
                        
                    sanitizar_dataframe(df_exib_excel).to_excel(writer, sheet_name="Resumo Geral", index=False)
                    
                    df_divergencias = df_conciliacao[df_conciliacao['STATUS'] == '❌ Divergente'].copy()
                    if not df_divergencias.empty:
                        df_div_export = df_divergencias[['DATA_EXIBICAO', 'ENTRADAS_EXTRATO', 'ENTRADAS_RAZAO', 'DIF_ENTRADAS', 'SAIDAS_EXTRATO', 'SAIDAS_RAZAO', 'DIF_SAIDAS']].copy()
                        df_div_export.columns = ['Data', 'Entradas Extrato', 'Entradas Razao', 'Diferenca Entradas', 'Saidas Extrato', 'Saidas Razao', 'Diferenca Saidas']
                        for col in df_div_export.columns[1:]: df_div_export[col] = df_div_export[col].apply(formatar_moeda)
                        sanitizar_dataframe(df_div_export).to_excel(writer, sheet_name="Dias Divergentes", index=False)

                st.download_button(
                    label="Baixar Relatório em Excel (.XLSX)", 
                    data=buf_audit.getvalue(), 
                    file_name=f"Analise_Conciliacao_{data_ini_filtro.strftime('%d%m%Y')}_a_{data_fim_filtro.strftime('%d%m%Y')}.xlsx", 
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                    use_container_width=False
                )

            else:
                st.warning("⚠️ Não conseguimos extrair as linhas contábeis válidas. Verifique se os arquivos contêm Data e Valor.")
        
        except Exception as e:
            st.error(f"🛑 Ocorreu um erro no cruzamento dos dados. Tire um print e envie para análise: \n{traceback.format_exc()}")
