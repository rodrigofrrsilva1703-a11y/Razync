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
    page_title="Importador Domínio Pro", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# ESTILIZAÇÃO CSS CUSTOMIZADA
# ==============================================================================
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .metric-card {
            background-color: #1a1a2e;
            border: 1px solid #2e2e48;
            padding: 14px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15);
        }
        .metric-title {
            font-size: 11px;
            color: #94a3b8;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 6px;
            letter-spacing: 0.5px;
        }
        .metric-value {
            font-size: 18px;
            color: #f8fafc;
            font-weight: 800;
        }
        section[data-testid="stSidebar"] {
            background-color: #0f172a;
            border-right: 1px solid #1e293b;
        }
        .sidebar-box {
            background-color: #1e293b;
            padding: 12px;
            border-radius: 8px;
            font-size: 13px;
            color: #cbd5e1;
            margin-bottom: 15px;
            border-left: 4px solid #3b82f6;
        }
    </style>
""", unsafe_allow_html=True)

def limpar_valor_monetario(v_val):
    if pd.isna(v_val) or v_val is None: return 0.0
    if isinstance(v_val, (int, float)): return float(v_val)
    s = str(v_val).strip().replace('R$', '').replace('$', '').replace(' ', '')
    if not s or s.lower() == 'nan': return 0.0
    if '.' in s and ',' in s:
        last_dot, last_comma = s.rfind('.'), s.rfind(',')
        s = s.replace('.', '').replace(',', '.') if last_comma > last_dot else s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    try: return float(s)
    except: return 0.0

def processar_ofx(file_bytes, filename):
    lancamentos = []
    texto = ""
    for enc in ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']:
        try:
            texto = file_bytes.decode(enc)
            break
        except: pass
    if not texto: texto = file_bytes.decode('latin1', errors='ignore')
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
            historico = match_memo.group(1).strip().replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>') if match_memo else "TRANSACAO OFX"
            if 'SALDO' in historico.upper(): continue
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
                lancamentos.append({'DESCRIÇÃO': banco, 'DATA': data_fmt, 'VALOR': valor_float, 'DÉBITO': '', 'CRÉDITO': '', 'HISTÓRICO': historico})
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
    header_idx = None
    for idx, row in df.iterrows():
        row_str = " ".join([str(v) for v in row.values if pd.notna(v)]).lower()
        if ('data' in row_str or 'dt' in row_str) and ('valor' in row_str or 'crédito' in row_str or 'débito' in row_str or 'lançamento' in row_str):
            header_idx = idx; break
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
        if any(term in hist_fmt.upper() for term in ['SALDO', 'SUBTOTAL', 'TOTAL', 'TRANSPORTAR']): continue
        valor_float = 0.0
        if col_cred or col_deb:
            v_cred = limpar_valor_monetario(row[col_cred]) if col_cred and pd.notna(row[col_cred]) else 0.0
            v_deb = limpar_valor_monetario(row[col_deb]) if col_deb and pd.notna(row[col_deb]) else 0.0
            if v_cred != 0: valor_float = abs(v_cred)
            elif v_deb != 0: valor_float = -abs(v_deb)
        elif col_val and pd.notna(row[col_val]):
            valor_float = limpar_valor_monetario(row[col_val])
            if col_tipo and pd.notna(row[col_tipo]):
                if 'D' in str(row[col_tipo]).upper() or 'SAÍDA' in str(row[col_tipo]).upper() or 'SAIDA' in str(row[col_tipo]).upper():
                    valor_float = -abs(valor_float)
        if valor_float != 0:
            banco_desc = f"EXTRATO {os.path.splitext(filename)[0].upper()}"
            if "BRADESCO" in filename.upper() or "BRADESCO" in hist_fmt.upper(): banco_desc = "BANCO BRADESCO"
            elif "ITAÚ" in filename.upper() or "ITAU" in filename.upper(): banco_desc = "BANCO ITAU"
            elif "SANTANDER" in filename.upper(): banco_desc = "BANCO SANTANDER"
            elif "CAIXA" in filename.upper(): banco_desc = "CAIXA ECONOMICA"
            lancamentos.append({'DESCRIÇÃO': banco_desc, 'DATA': dt_fmt, 'VALOR': valor_float, 'DÉBITO': '', 'CRÉDITO': '', 'HISTÓRICO': hist_fmt})
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
                        hist = full_text[:full_text.rfind(val_str)].strip()
                        if 'SALDO' not in hist.upper():
                            try:
                                v = limpar_valor_monetario(val_str)
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
                        hist_completo = f"{historico.strip()} {doc.strip()}" if doc else historico.strip()
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
                    historico_completo = f"{pending_desc} {parte_desc}".strip() if pending_desc else parte_desc
                    pending_desc = ""
                    if 'SALDO' not in historico_completo.upper() and 'TOTAL' not in historico_completo.upper():
                        try:
                            v = limpar_valor_monetario(val_str)
                            lancamentos.append({'DESCRIÇÃO': 'BANCO BRADESCO', 'DATA': current_date, 'VALOR': v, 'DÉBITO': '', 'CRÉDITO': '', 'HISTÓRICO': historico_completo})
                        except: pass
                else:
                    if 'SALDO' not in linha_sem_data.upper() and 'EXTRATO' not in linha_sem_data.upper():
                        pending_desc = f"{pending_desc} {linha_sem_data}".strip() if pending_desc else linha_sem_data
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
                        if v != 0:
                            if is_debito: v = -abs(v)
                            hist = linha.replace(data_atual, '').replace(val_str, '').strip()
                            if len(hist) < 2 or 'SALDO' in hist.upper(): continue
                            lancamentos.append({
                                'DESCRIÇÃO': f"EXTRATO {os.path.splitext(os.path.basename(caminho_pdf))[0].upper()}",
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
    nome_arquivo = os.path.basename(caminho_pdf).upper()
    try:
        reader = PdfReader(caminho_pdf, strict=False)
        texto_inicio = reader.pages[0].extract_text().upper() if reader.pages else ""
    except: texto_inicio = ""
    if "CAIXA" in nome_arquivo or "CAIXA" in texto_inicio: return processar_pdf_caixa(caminho_pdf)
    elif "BRADESCO" in nome_arquivo or "BRADESCO" in texto_inicio or "NET EMPRESA" in texto_inicio: return processar_pdf_bradesco(caminho_pdf)
    elif "SANTANDER" in nome_arquivo or "SANTANDER" in texto_inicio: return processar_pdf_santander(caminho_pdf)
    else:
        res = processar_pdf_santander(caminho_pdf)
        if not res: res = processar_pdf_bradesco(caminho_pdf)
        if not res: res = processar_pdf_generico_universal(caminho_pdf)
        return res

def gerar_txt_dominio(df):
    linhas_txt = []
    for _, row in df.iterrows():
        linhas_txt.append(f"{row['DATA']};{row['DÉBITO'] if pd.notna(row['DÉBITO']) else ''};{row['CRÉDITO'] if pd.notna(row['CRÉDITO']) else ''};{float(row['VALOR']):.2f};{str(row['HISTÓRICO']).replace(';', ' ')}\n")
    return "".join(linhas_txt)

# ==============================================================================
# INTERFACE GRÁFICA: BARRA LATERAL REFINADA
# ==============================================================================
st.sidebar.markdown("### 🤖 Importador Pro")
st.sidebar.markdown("<p style='font-size: 13px; color: #94a3b8;'>Conciliação Bancária Automatizada para Domínio Systems.</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

st.sidebar.markdown("#### 📂 Envio de Arquivos")
st.sidebar.markdown("<div class='sidebar-box'><b>Dica:</b> Envie um ou vários arquivos bancários para gerar resumos individuais ou consolidados.</div>", unsafe_allow_html=True)

arquivos = st.sidebar.file_uploader(
    "Arraste os extratos aqui", 
    type=["pdf", "ofx", "csv", "xlsx", "xls"], 
    accept_multiple_files=True,
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("<p style='font-size: 11px; color: #64748b; text-align: center;'>Versão 3.5 · Advanced Engine</p>", unsafe_allow_html=True)

# ==============================================================================
# TELA PRINCIPAL
# ==============================================================================
st.title("⚡ Painel de Conciliação")
st.caption("Converta extratos em layouts compatíveis para importação na Domínio de forma rápida e segura.")

if arquivos:
    colunas_dominio = ['DESCRIÇÃO', 'DATA', 'VALOR', 'DÉBITO', 'CRÉDITO', 'HISTÓRICO']
    df_modelo = pd.read_excel("Modelo dominio.xlsx") if os.path.exists("Modelo dominio.xlsx") else pd.DataFrame(columns=colunas_dominio)
    if 'DESCRIÇÃO' not in df_modelo.columns: df_modelo = pd.DataFrame(columns=colunas_dominio)
    
    # Processa todos os arquivos primeiro para alimentar o sistema
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
        # Monta as abas (se houver mais de 1 arquivo, cria a aba Consolidada primeiro)
        if len(arquivos) > 1:
            nomes_abas = ["🌐 Visão Consolidada (Geral)"] + [arq.name for arq in arquivos if arq.name in dados_por_arquivo]
        else:
            nomes_abas = [arq.name for arq in arquivos if arq.name in dados_por_arquivo]
            
        abas = st.tabs(nomes_abas)
        
        # ======================================================================
        # ABA 1: VISÃO CONSOLIDADA (CASO HAJA MAIS DE UM ARQUIVO)
        # ======================================================================
        if len(arquivos) > 1:
            with abas[0]:
                st.markdown("### 🌐 Resumo Consolidado de Todos os Extratos")
                df_geral_bruto = pd.DataFrame(todos_lancamentos_brutos)
                df_geral_bruto['DATA_DT'] = pd.to_datetime(df_geral_bruto['DATA'], format='%d/%m/%Y', errors='coerce')
                df_geral_bruto = df_geral_bruto.dropna(subset=['DATA_DT'])
                
                dt_min_geral = df_geral_bruto['DATA_DT'].min().date()
                dt_max_geral = df_geral_bruto['DATA_DT'].max().date()
                
                col_g1, col_g2, col_g3 = st.columns([1, 1, 1.5])
                with col_g1: data_geral_ini = st.date_input("📅 Data Inicial Geral", value=dt_min_geral, min_value=dt_min_geral, max_value=dt_max_geral, format="DD/MM/YYYY", key="gen_ini")
                with col_g2: data_geral_fim = st.date_input("📅 Data Final Geral", value=dt_max_geral, min_value=dt_min_geral, max_value=dt_max_geral, format="DD/MM/YYYY", key="gen_fim")
                with col_g3:
                    st.markdown("<div style='height: 2px;'></div>", unsafe_allow_html=True)
                    termo_busca_geral = st.text_input("🔍 Busca rápida geral", placeholder="Filtrar histórico...", key="gen_busca")
                
                df_geral_final = df_geral_bruto[(df_geral_bruto['DATA_DT'].dt.date >= data_geral_ini) & (df_geral_bruto['DATA_DT'].dt.date <= data_geral_fim)].copy()
                if termo_busca_geral:
                    df_geral_final = df_geral_final[df_geral_final['HISTÓRICO'].str.contains(termo_busca_geral, case=False, na=False)]
                
                df_geral_final = df_geral_final.drop(columns=['DATA_DT', 'ARQUIVO_ORIGEM'], errors='ignore')[df_modelo.columns]
                
                tot_cred_g = df_geral_final[df_geral_final['VALOR'] > 0]['VALOR'].sum()
                tot_deb_g = df_geral_final[df_geral_final['VALOR'] < 0]['VALOR'].sum()
                saldo_liq_g = tot_cred_g + tot_deb_g
                
                st.markdown("<br>", unsafe_allow_html=True)
                cg1, cg2, cg3, cg4 = st.columns(4)
                with cg1:
                    st.markdown(f'<div class="metric-card"><div class="metric-title">Total Registros</div><div class="metric-value">{len(df_geral_final)}</div></div>', unsafe_allow_html=True)
                with cg2:
                    st.markdown(f'<div class="metric-card"><div class="metric-title">Entradas Totais</div><div class="metric-value" style="color: #4ade80;">R$ {tot_cred_g:,.2f}</div></div>'.replace(',', 'X').replace('.', ',').replace('X', '.'), unsafe_allow_html=True)
                with cg3:
                    st.markdown(f'<div class="metric-card"><div class="metric-title">Saídas Totais</div><div class="metric-value" style="color: #f87171;">R$ {abs(tot_deb_g):,.2f}</div></div>'.replace(',', 'X').replace('.', ',').replace('X', '.'), unsafe_allow_html=True)
                with cg4:
                    color_g = "#4ade80" if saldo_liq_g >= 0 else "#f87171"
                    st.markdown(f'<div class="metric-card"><div class="metric-title">Saldo Líquido Geral</div><div class="metric-value" style="color: {color_g};">R$ {saldo_liq_g:,.2f}</div></div>'.replace(',', 'X').replace('.', ',').replace('X', '.'), unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                
                # Gráfico Visual de Movimentação por Data (Opção 4)
                if not df_geral_final.empty:
                    st.markdown("##### 📈 Fluxo de Caixa Consolidado (Entradas vs Saídas por Data)")
                    df_grafico = df_geral_final.copy()
                    df_grafico['DATA'] = pd.to_datetime(df_grafico['DATA'], format='%d/%m/%Y')
                    df_grafico_grouped = df_grafico.groupby('DATA')['VALOR'].sum()
                    st.bar_chart(df_grafico_grouped)

                st.markdown("##### 📋 Prévia Consolidada")
                st.dataframe(df_geral_final, use_container_width=True, height=280)
                
                st.markdown("##### 📥 Exportar Consolidado")
                cc_dl1, cc_dl2 = st.columns(2)
                buf_excel_g = io.BytesIO()
                with pd.ExcelWriter(buf_excel_g, engine='openpyxl') as writer: df_geral_final.to_excel(writer, index=False)
                cc_dl1.download_button("📊 Baixar Excel Consolidado (.XLSX)", data=buf_excel_g.getvalue(), file_name=f"consolidado_geral_{data_geral_ini.strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_excel_geral", use_container_width=True)
                cc_dl2.download_button("🚀 Baixar TXT Consolidado para Domínio", data=gerar_txt_dominio(df_geral_final), file_name=f"importacao_dominio_consolidado_{data_geral_ini.strftime('%d%m%Y')}.txt", mime="text/plain", key="dl_txt_geral", use_container_width=True)
                st.markdown("---")

        # ======================================================================
        # ABAS INDIVIDUAIS POR ARQUIVO
        # ======================================================================
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
                    with col_f1: data_sel_ini = st.date_input("📅 Data Inicial", value=val_ini_def, min_value=dt_min_dataset, max_value=dt_max_dataset, format="DD/MM/YYYY", key=f"ini_{idx_arq}")
                    with col_f2: data_sel_fim = st.date_input("📅 Data Final", value=val_fim_def, min_value=dt_min_dataset, max_value=dt_max_dataset, format="DD/MM/YYYY", key=f"fim_{idx_arq}")
                    with col_f3:
                        st.markdown("<div style='height: 2px;'></div>", unsafe_allow_html=True)
                        termo_busca = st.text_input("🔍 Busca rápida no histórico", placeholder="Digite para filtrar...", key=f"busca_{idx_arq}")

                df_final = df_bruto[(df_bruto['DATA_DT'].dt.date >= data_sel_ini) & (df_bruto['DATA_DT'].dt.date <= data_sel_fim)].copy()
                if termo_busca:
                    df_final = df_final[df_final['HISTÓRICO'].str.contains(termo_busca, case=False, na=False)]
                
                df_final = df_final.drop(columns=['DATA_DT', 'ARQUIVO_ORIGEM'], errors='ignore')[df_modelo.columns]
                total_creditos = df_final[df_final['VALOR'] > 0]['VALOR'].sum()
                total_debitos = df_final[df_final['VALOR'] < 0]['VALOR'].sum()
                saldo_liquido = total_creditos + total_debitos
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.markdown(f'<div class="metric-card"><div class="metric-title">Registros</div><div class="metric-value">{len(df_final)}</div></div>', unsafe_allow_html=True)
                with c2:
                    val_cred_fmt = f"R$ {total_creditos:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    st.markdown(f'<div class="metric-card"><div class="metric-title">Entradas</div><div class="metric-value" style="color: #4ade80;">{val_cred_fmt}</div></div>', unsafe_allow_html=True)
                with c3:
                    val_deb_fmt = f"R$ {abs(total_debitos):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    st.markdown(f'<div class="metric-card"><div class="metric-title">Saídas</div><div class="metric-value" style="color: #f87171;">{val_deb_fmt}</div></div>', unsafe_allow_html=True)
                with c4:
                    val_liq_fmt = f"R$ {saldo_liquido:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    color_liq = "#4ade80" if saldo_liquido >= 0 else "#f87171"
                    st.markdown(f'<div class="metric-card"><div class="metric-title">Saldo Líquido</div><div class="metric-value" style="color: {color_liq};">{val_liq_fmt}</div></div>', unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                
                # Gráfico Individual por Arquivo (Opção 4)
                if not df_final.empty:
                    st.markdown("##### 📈 Gráfico de Movimentações Diárias")
                    df_graf_ind = df_final.copy()
                    df_graf_ind['DATA'] = pd.to_datetime(df_graf_ind['DATA'], format='%d/%m/%Y')
                    st.bar_chart(df_graf_ind.groupby('DATA')['VALOR'].sum())

                st.markdown("##### 📋 Prévia dos Lançamentos")
                st.dataframe(df_final, use_container_width=True, height=280)
                
                st.markdown("##### 📥 Exportar Arquivos")
                c_dl1, c_dl2 = st.columns(2)
                buffer_excel = io.BytesIO()
                with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer: df_final.to_excel(writer, index=False)
                c_dl1.download_button("📊 Baixar em Excel (.XLSX)", data=buffer_excel.getvalue(), file_name=f"lancamentos_{os.path.splitext(arquivo.name)[0]}_{data_sel_ini.strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"excel_{idx_arq}", use_container_width=True)
                c_dl2.download_button("🚀 Baixar TXT para Domínio", data=gerar_txt_dominio(df_final), file_name=f"importacao_dominio_{os.path.splitext(arquivo.name)[0]}_{data_sel_ini.strftime('%d%m%Y')}.txt", mime="text/plain", key=f"txt_{idx_arq}", use_container_width=True)
    else:
        st.warning("⚠️ Não foi possível extrair lançamentos válidos de nenhum dos arquivos enviados.")
else:
    st.info("👈 Comece enviando um ou mais arquivos de extrato bancário na **Barra Lateral** à esquerda para visualizar a conciliação e os gráficos.")
