import streamlit as st
import pandas as pd
import re
import io
import os
from datetime import datetime
from pypdf import PdfReader

# Configuração da página
st.set_page_config(page_title="Importador Domínio Pro", page_icon="🤖", layout="wide")

# CSS para cards compactos e layout limpo
st.markdown("""
    <style>
        .card { background-color: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #dee2e6; text-align: center; }
        .label { font-size: 0.70rem; color: #6c757d; text-transform: uppercase; margin-bottom: 5px; }
        .value { font-size: 0.95rem; font-weight: bold; color: #212529; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE PROCESSAMENTO ---
def limpar_valor_monetario(v_val):
    if pd.isna(v_val) or v_val == '': return 0.0
    s = str(v_val).strip().replace('R$', '').replace('$', '').replace(' ', '')
    if '.' in s and ',' in s: s = s.replace('.', '').replace(',', '.')
    elif ',' in s: s = s.replace(',', '.')
    try: return float(s)
    except: return 0.0

def processar_ofx(file_bytes):
    texto = file_bytes.decode('utf-8', errors='ignore')
    transacoes = re.findall(r'<STMTTRN>(.*?)</STMTTRN>', texto, re.DOTALL)
    dados = []
    for t in transacoes:
        dt = re.search(r'<DTPOSTED>(\d{8})', t)
        val = re.search(r'<TRNAMT>([-+]?[\d.]+)', t)
        memo = re.search(r'<MEMO>(.*?)(?:<|$)', t)
        if dt and val:
            dados.append({
                'DATA': f"{dt.group(1)[6:8]}/{dt.group(1)[4:6]}/{dt.group(1)[:4]}",
                'VALOR': limpar_valor_monetario(val.group(1)),
                'HISTÓRICO': memo.group(1).strip() if memo else "TRANSACAO"
            })
    return pd.DataFrame(dados)

def processar_planilha_universal(file_bytes, filename):
    try:
        if filename.endswith('.csv'): df = pd.read_csv(io.BytesIO(file_bytes), sep=None, engine='python')
        else: df = pd.read_excel(io.BytesIO(file_bytes))
        df.columns = [str(c).upper() for c in df.columns]
        
        # Identifica colunas
        col_data = next((c for c in df.columns if 'DATA' in c or 'DT' in c), df.columns[0])
        col_valor = next((c for c in df.columns if 'VALOR' in c or 'VAL' in c), df.columns[-1])
        col_hist = [c for c in df.columns if c not in [col_data, col_valor]]
        
        df['HISTÓRICO'] = df[col_hist].astype(str).agg(' '.join, axis=1).str.replace('nan', '', regex=False).str.strip()
        df['DATA'] = df[col_data]
        df['VALOR'] = df[col_valor].apply(limpar_valor_monetario)
        return df[['DATA', 'VALOR', 'HISTÓRICO']]
    except: return pd.DataFrame()

# --- INTERFACE ---
st.sidebar.title("⚡ Painel de Controle")
arquivos = st.sidebar.file_uploader("Arraste os extratos", type=["ofx", "csv", "xlsx", "xls"], accept_multiple_files=True)

st.title("🤖 Importador Inteligente Domínio")

if arquivos:
    abas = st.tabs([a.name for a in arquivos])
    for idx, arquivo in enumerate(arquivos):
        with abas[idx]:
            if arquivo.name.endswith('.ofx'): df = processar_ofx(arquivo.getvalue())
            else: df = processar_planilha_universal(arquivo.getvalue(), arquivo.name)
            
            # --- LIMPEZA DE SALDOS E CONSOLIDAÇÃO ---
            if not df.empty:
                df = df[~df['HISTÓRICO'].str.contains('SALDO|TOTAL|INICIAL|FINAL|DISPONÍVEL|SUBTOTAL', case=False, na=False)]
                df['HISTÓRICO'] = df['HISTÓRICO'].str.replace(r'\s+', ' ', regex=True).str.strip()
                
                # Cards
                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(f'<div class="card"><div class="label">Registros</div><div class="value">{len(df)}</div></div>', unsafe_allow_html=True)
                c2.markdown(f'<div class="card"><div class="label">Entradas</div><div class="value">R$ {df[df["VALOR"]>0]["VALOR"].sum():,.2f}</div></div>', unsafe_allow_html=True)
                c3.markdown(f'<div class="card"><div class="label">Saídas</div><div class="value">R$ {abs(df[df["VALOR"]<0]["VALOR"].sum()):,.2f}</div></div>', unsafe_allow_html=True)
                c4.markdown(f'<div class="card"><div class="label">Saldo Líquido</div><div class="value">R$ {df["VALOR"].sum():,.2f}</div></div>', unsafe_allow_html=True)
                
                st.write("")
                st.dataframe(df, use_container_width=True)
                
                txt = "\n".join([f"{r['DATA']};;{r['VALOR']:.2f};{r['HISTÓRICO']}" for _, r in df.iterrows()])
                st.download_button("🚀 Gerar .TXT p/ Domínio", txt, file_name=f"import_{arquivo.name}.txt", use_container_width=True)
else:
    st.info("Utilize a barra lateral para carregar arquivos.")
