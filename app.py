import streamlit as st
import pandas as pd
import openpyxl
import re
import calendar
import io
import os
from datetime import datetime
from pypdf import PdfReader

# Configuração da página Web (Layout largo e limpo)
st.set_page_config(page_title="Importador Universal - Domínio", page_icon="🤖", layout="wide")


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
        texto = "".join([p.extract_text() + "\n" for p in reader.pages[:2]])
        match_s = re.search(r'Períodos?:\s*(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE)
        if match_s: return datetime.strptime(match_s.group(1), '%d/%m/%Y'), datetime.strptime(match_s.group(2), '%d/%m/%Y')
        match_b = re.search(r'(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})', texto)
        if match_b and ("BRADESCO" in texto.upper() or "NET EMPRESA" in texto.upper()):
            return datetime.strptime(match_b.group(1), '%d/%m/%Y'), datetime.strptime(match_b.group(2), '%d/%m/%Y')
        match_c = re.search(r'Mês:\s*([A-Za-zç]+)/(\d{4})', texto, re.IGNORECASE)
        if match_c:
            meses = {'JANEIRO':1, 'FEVEREIRO':2, 'MARCO':3, 'MARÇO':3, 'ABRIL':4, 'MAIO':5, 'JUNHO':6, 'JULHO':7, 'AGOSTO':8, 'SETEMBRO':9, 'OUTUBRO':10, 'NOVEMBRO':11, 'DEZEMBRO':12}
            m_num, ano = meses.get(match_c.group(1).upper(), 6), int(match_c.group(2))
            match_dia = re.search(r'Período:\s*(\d+)\s*-\s*(\d+)', texto, re.IGNORECASE)
            d_ini = int(match_dia.group(1)) if match_dia else 1
            d_fim = int(match_dia.group(2)) if match_dia else calendar.monthrange(ano, m_num)[1]
            return datetime(ano, m_num, d_ini), datetime(ano, m_num, d_fim)
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
                if any(t in linha.upper() for t in ['SALDO DISPONÍVEL', 'POSIÇÃO EM:', 'CENTRAL DE ATENDIMENTO']): i += 1; continue
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
                        try:
                            v = limpar_valor_monetario(val_str)
                            if 'SALDO' not in hist.upper():
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
                if any(t in linha.upper() for t in ['EXTRATO DE:', 'TOTAL DISPONÍVEL', 'AGÊNCIA | CONTA', 'FOLHA ', 'SALDOS INVEST']): i += 1; continue
                match_date = date_regex.match(linha)
                if match_date: current_date, linha_sem_data = match_date.group(1), linha[len(match_date.group(1)):].strip()
                else: linha_sem_data = linha
                matches_valores = re.findall(r'(-?[\d\.]+\,\d{2})', linha_sem_data)
                if matches_valores and current_date:
                    val_str = matches_valores[-2] if len(matches_valores) >= 2 else matches_valores[0]
                    parte_desc = linha_sem_data[:linha_sem_data.rfind(val_str)].strip()
                    historico_completo = f"{pending_desc} {parte_desc}".strip() if pending_desc else parte_desc
                    pending_desc = ""
                    try:
                        v = limpar_valor_monetario(val_str)
                        if 'SALDO' not in historico_completo.upper() and 'TOTAL' not in historico_completo.upper():
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
        banco_nome = "BANCO EXTRATO"
        
        for pagina in reader.pages:
            texto = pagina.extract_text()
            if not texto: continue
            
            for linha in texto.split('\n'):
                linha = linha.strip()
                if not linha or any(s in linha.upper() for s in ['SALDO', 'TOTAL', 'SUBTOTAL', 'INICIAL', 'FINAL']):
                    continue
                
                match_data = re.search(r'(\d{2}/\d{2}(?:/\d{4})?)', linha)
                matches_vals = re.findall(r'(-?\d{1,3}(?:\.\d{3})*,\d{2})', linha)
                
                if match_data and matches_vals:
                    dt = match_data.group(1)
                    if len(dt) == 5: dt = f"{dt}/{datetime.now().year}"
                    
                    val_str = matches_vals[-1]
                    hist = linha.replace(dt, '').replace(val_str, '').strip()
                    
                    try:
                        v = limpar_valor_monetario(val_str)
                        if v != 0 and len(hist) > 2:
                            lancamentos.append({
                                'DESCRIÇÃO': banco_nome,
                                'DATA': dt,
                                'VALOR': v,
                                'DÉBITO': '',
                                'CRÉDITO': '',
                                'HISTÓRICO': hist
                            })
                    except: pass
    except Exception as e:
        st.error(f"Erro no leitor genérico: {e}")
    return lancamentos

def processar_arquivo_pdf(caminho_pdf):
    nome_arquivo = os.path.basename(caminho_pdf).upper()
    try:
        reader = PdfReader(caminho_pdf, strict=False)
        texto_inicio = reader.pages[0].extract_text().upper() if reader.pages else ""
    except: texto_inicio = ""

    if "CAIXA" in nome_arquivo or "CAIXA" in texto_inicio:
        return processar_pdf_caixa(caminho_pdf)
    elif "BRADESCO" in nome_arquivo or "BRADESCO" in texto_inicio or "NET EMPRESA" in texto_inicio:
        return processar_pdf_bradesco(caminho_pdf)
    elif "SANTANDER" in nome_arquivo or "SANTANDER" in texto_inicio:
        return processar_pdf_santander(caminho_pdf)
    else:
        res = processar_pdf_santander(caminho_pdf)
        if not res:
            res = processar_pdf_generico_universal(caminho_pdf)
        return res


# ==============================================================================
# 5. GERADOR DE ARQUIVO TXT (LEIAUTE GERENCIADOR DE IMPORTAÇÃO DOMÍNIO)
# ==============================================================================
def gerar_txt_dominio(df):
    linhas_txt = []
    for _, row in df.iterrows():
        data = row['DATA']
        debito = row['DÉBITO'] if pd.notna(row['DÉBITO']) else ''
        credito = row['CRÉDITO'] if pd.notna(row['CRÉDITO']) else ''
        valor = f"{float(row['VALOR']):.2f}"
        historico = str(row['HISTÓRICO']).replace(';', ' ')
        linha = f"{data};{debito};{credito};{valor};{historico}\n"
        linhas_txt.append(linha)
    return "".join(linhas_txt)


# ==============================================================================
# 6. INTERFACE GRÁFICA DO SISTEMA (ESTILO CLEAN & MODERN)
# ==============================================================================

# Injetando estilo CSS customizado para deixar os cards e containers super modernos
st.markdown("""
    <style>
        .main { background-color: #fafbfd; }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #f1f3f6;
            border-radius: 8px 8px 0px 0px;
            padding: 10px 20px;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background-color: #ffffff !important;
            border-top: 3px solid #0066cc !important;
        }
    </style>
""", unsafe_allow_html=True)

st.sidebar.title("⚡ Painel de Controle")
st.sidebar.markdown("---")
st.sidebar.markdown("### 📤 Upload de Arquivos")

arquivos = st.sidebar.file_uploader(
    "Arraste os extratos bancários (PDF, OFX, CSV, Excel)",
    type=["pdf", "ofx", "csv", "xlsx", "xls"],
    accept_multiple_files=True
)

st.title("🤖 Importador Inteligente Domínio")
st.caption("Ambiente de conciliação bancária de alta performance e visual limpo.")

if arquivos:
    st.sidebar.success(f"{len(arquivos)} arquivo(s) carregado(s).")
    
    colunas_dominio = ['DESCRIÇÃO', 'DATA', 'VALOR', 'DÉBITO', 'CRÉDITO', 'HISTÓRICO']
    if os.path.exists("Modelo dominio.xlsx"):
        try:
            df_modelo = pd.read_excel("Modelo dominio.xlsx")
            if 'DESCRIÇÃO' not in df_modelo.columns:
                df_modelo = pd.DataFrame(columns=colunas_dominio)
        except:
            df_modelo = pd.DataFrame(columns=colunas_dominio)
    else:
        df_modelo = pd.DataFrame(columns=colunas_dominio)

    nomes_abas = [arq.name for arq in arquivos]
    abas = st.tabs(nomes_abas)

    for idx_arq, arquivo in enumerate(arquivos):
        with abas[idx_arq]:
            
            # Container limpo para o arquivo
            with st.container():
                st.markdown(f"### 📑 Análise do Extrato: `{arquivo.name}`")
                
                file_bytes = arquivo.getvalue()
                extensao = os.path.splitext(arquivo.name)[1].lower()
                lancamentos = []
                data_ini_doc, data_fim_doc = None, None

                if extensao == '.ofx':
                    lancamentos = processar_ofx(file_bytes, arquivo.name)
                elif extensao in ['.csv', '.xlsx', '.xls']:
                    lancamentos = processar_planilha_universal(file_bytes, arquivo.name)
                elif extensao == '.pdf':
                    caminho_temp = f"temp_{arquivo.name}"
                    with open(caminho_temp, "wb") as f:
                        f.write(file_bytes)
                    data_ini_doc, data_fim_doc = extrair_periodo_extrato(caminho_temp)
                    lancamentos = processar_arquivo_pdf(caminho_temp)
                    if os.path.exists(caminho_temp):
                        os.remove(caminho_temp)

                if lancamentos:
                    df_bruto = pd.DataFrame(lancamentos)
                    df_bruto['DATA_DT'] = pd.to_datetime(df_bruto['DATA'], format='%d/%m/%Y', errors='coerce')
                    df_bruto = df_bruto.dropna(subset=['DATA_DT'])
                    
                    dt_min_dataset = df_bruto['DATA_DT'].min().date()
                    dt_max_dataset = df_bruto['DATA_DT'].max().date()

                    val_ini_def = data_ini_doc.date() if data_ini_doc else dt_min_dataset
                    val_fim_def = data_fim_doc.date() if data_fim_doc else dt_max_dataset

                    # Bloco de Filtros com visual moderno
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        data_sel_ini = st.date_input("📅 Data Inicial", value=val_ini_def, min_value=dt_min_dataset, max_value=dt_max_dataset, format="DD/MM/YYYY", key=f"ini_{idx_arq}")
                    with col_f2:
                        data_sel_fim = st.date_input("📅 Data Final", value=val_fim_def, min_value=dt_min_dataset, max_value=dt_max_dataset, format="DD/MM/YYYY", key=f"fim_{idx_arq}")

                    df_final = df_bruto[(df_bruto['DATA_DT'].dt.date >= data_sel_ini) & (df_bruto['DATA_DT'].dt.date <= data_sel_fim)].copy()

                    # Filtro avançado discreto
                    with st.expander("🔍 Busca rápida por palavra-chave no histórico"):
                        termo_busca = st.text_input("Digite o termo (ex: PIX, TED, ENEL):", key=f"busca_{idx_arq}", label_visibility="collapsed")
                        if termo_busca:
                            df_final = df_final[df_final['HISTÓRICO'].str.contains(termo_busca, case=False, na=False)]

                    df_final = df_final.drop(columns=['DATA_DT'])
                    df_final = df_final[df_modelo.columns]
                    
                    # Métricas modernas lado a lado
                    total_creditos = df_final[df_final['VALOR'] > 0]['VALOR'].sum()
                    total_debitos = df_final[df_final['VALOR'] < 0]['VALOR'].sum()
                    saldo_liquido = total_creditos + total_debitos
                    
                    st.markdown("---")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Qtd. Registros", len(df_final))
                    m2.metric("Entradas", f"R$ {total_creditos:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                    m3.metric("Saídas", f"R$ {abs(total_debitos):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                    m4.metric("Saldo Líquido", f"R$ {saldo_liquido:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

                    # Alerta de caixa limpo
                    if saldo_liquido > 0:
                        st.success(f"✨ **Caixa Saudável no Período:** Superávit de **R$ {saldo_liquido:,.2f}**.".replace(',', 'X').replace('.', ',').replace('X', '.'))
                    elif saldo_liquido < 0:
                        st.warning(f"⚠️ **Atenção:** Déficit no período de **R$ {abs(saldo_liquido):,.2f}**.".replace(',', 'X').replace('.', ',').replace('X', '.'))

                    # Tabela limpa e moderna
                    st.markdown("##### 📋 Prévia dos Lançamentos Formatados")
                    st.dataframe(df_final, use_container_width=True, height=350)

                    # Botões de download organizados
                    st.markdown("##### 📥 Exportar Arquivos para a Domínio")
                    c_dl1, c_dl2 = st.columns(2)
                    
                    buffer_excel = io.BytesIO()
                    with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
                        df_final.to_excel(writer, index=False)
                    
                    c_dl1.download_button(
                        label="📊 Baixar Planilha em Excel (.XLSX)",
                        data=buffer_excel.getvalue(),
                        file_name=f"lancamentos_{os.path.splitext(arquivo.name)[0]}_{data_sel_ini.strftime('%d%m%Y')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"excel_{idx_arq}",
                        use_container_width=True
                    )

                    texto_txt = gerar_txt_dominio(df_final)
                    c_dl2.download_button(
                        label="🚀 Baixar Arquivo TXT da Domínio",
                        data=texto_txt,
                        file_name=f"importacao_dominio_{os.path.splitext(arquivo.name)[0]}_{data_sel_ini.strftime('%d%m%Y')}.txt",
                        mime="text/plain",
                        key=f"txt_{idx_arq}",
                        use_container_width=True
                    )
                else:
                    st.warning("Não foi possível extrair lançamentos válidos deste arquivo.")
else:
    # Tela inicial limpa com instruções visuais
    st.info("👈 Para começar, utilize a **Barra Lateral à esquerda** para arrastar e soltar os seus arquivos de extrato (PDF, OFX, Planilhas). O sistema fará a leitura automática de forma instantânea.")
