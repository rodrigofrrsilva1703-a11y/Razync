import streamlit as st
import pandas as pd
import re
import io
import os
from pypdf import PdfReader

st.set_page_config(page_title="Importador Domínio Pro", layout="wide")

# --- CSS PARA ESTILO LIMPO ---
st.markdown("""
    <style>
        .metric-container { background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #e9ecef; text-align: center; }
        .metric-val { font-size: 1.2rem; font-weight: bold; color: #000; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÃO UNIVERSAL DE LIMPEZA DE VALOR ---
def tratar_valor(val):
    s = str(val).replace('R$', '').replace('.', '').replace(',', '.').strip()
    try: return float(s)
    except: return 0.0

# --- LEITOR UNIVERSAL (PDF + PLANILHAS) ---
def ler_arquivo(file_bytes, filename):
    # PDF
    if filename.lower().endswith('.pdf'):
        reader = PdfReader(io.BytesIO(file_bytes))
        linhas = []
        for p in reader.pages:
            linhas.extend(p.extract_text().split('\n'))
        
        dados = []
        for l in linhas:
            # Regex: Data (00/00/0000) + Texto + Valor (-0,00)
            match = re.search(r'(\d{2}/\d{2}/\d{4})\s+(.*?)\s+([\d\.]*,\d{2})', l)
            if match:
                dados.append({'DATA': match.group(1), 'HISTÓRICO': match.group(2).strip(), 'VALOR': tratar_valor(match.group(3))})
        return pd.DataFrame(dados)
    
    # EXCEL/CSV
    else:
        try:
            df = pd.read_excel(io.BytesIO(file_bytes)) if filename.endswith(('.xlsx', '.xls')) else pd.read_csv(io.BytesIO(file_bytes), sep=None, engine='python')
            df.columns = [str(c).upper() for c in df.columns]
            # Tenta achar colunas automaticamente
            c_dt = next((c for c in df.columns if 'DATA' in c or 'DT' in c), df.columns[0])
            c_vl = next((c for c in df.columns if 'VAL' in c), df.columns[-1])
            # Une tudo que for texto no histórico
            c_txt = [c for c in df.columns if c not in [c_dt, c_vl]]
            df['HISTÓRICO'] = df[c_txt].astype(str).agg(' '.join, axis=1)
            df = df.rename(columns={c_dt: 'DATA', c_vl: 'VALOR'})
            return df[['DATA', 'HISTÓRICO', 'VALOR']]
        except: return pd.DataFrame()

# --- INTERFACE ---
st.title("🤖 Importador Inteligente")
arquivos = st.file_uploader("Arraste extratos", accept_multiple_files=True)

if arquivos:
    for arq in arquivos:
        df = ler_arquivo(arq.getvalue(), arq.name)
        if not df.empty:
            # LIMPEZA OBRIGATÓRIA (Saldos e vazios)
            df = df[~df['HISTÓRICO'].str.contains('SALDO|TOTAL|INICIAL|FINAL|SUBTOTAL', case=False, na=False)]
            df['HISTÓRICO'] = df['HISTÓRICO'].str.replace(r'\s+', ' ', regex=True).str.strip()
            
            # METRICAS
            c1, c2, c3 = st.columns(3)
            c1.markdown(f'<div class="metric-container"><div class="metric-val">{len(df)}</div>Registros</div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-container"><div class="metric-val">R$ {df[df["VALOR"]>0]["VALOR"].sum():,.2f}</div>Entradas</div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-container"><div class="metric-val">R$ {abs(df[df["VALOR"]<0]["VALOR"].sum()):,.2f}</div>Saídas</div>', unsafe_allow_html=True)
            
            st.dataframe(df, use_container_width=True)
            
            # DOWNLOAD
            txt = "\n".join([f"{r['DATA']};;{r['VALOR']:.2f};{r['HISTÓRICO']}" for _, r in df.iterrows()])
            st.download_button("🚀 Gerar .TXT p/ Domínio", txt, f"import_{arq.name}.txt", use_container_width=True)
        else:
            st.warning(f"O arquivo {arq.name} não pôde ser lido automaticamente. Verifique se não é um PDF de imagem.")
