import streamlit as st
import pandas as pd
import re
import io
from pypdf import PdfReader

st.set_page_config(page_title="Importador Domínio Pro", layout="wide")

# CSS para cards minimalistas
st.markdown("""
    <style>
        .metric { background: #f1f3f5; padding: 10px; border-radius: 5px; text-align: center; border: 1px solid #dee2e6; }
        .m-val { font-weight: bold; font-size: 1.1em; }
    </style>
""", unsafe_allow_html=True)

def limpar_valor(v):
    if not isinstance(v, str): v = str(v)
    v = v.replace('R$', '').replace('.', '').replace(',', '.')
    try: return float(v)
    except: return 0.0

def extrair_dados_pdf(file_bytes):
    reader = PdfReader(io.BytesIO(file_bytes))
    conteudo = []
    for pag in reader.pages:
        linhas = pag.extract_text().split('\n')
        for linha in linhas:
            # Padrão flexível: Data, depois texto, depois valor
            # Busca: DD/MM/AAAA ou DD/MM/AA + texto + valor com vírgula
            match = re.search(r'(\d{2}/\d{2}/\d{2,4})\s+(.*?)\s+([\d\.]*,\d{2})', linha)
            if match:
                conteudo.append({
                    'DATA': match.group(1),
                    'HISTÓRICO': match.group(2).strip(),
                    'VALOR': limpar_valor(match.group(3))
                })
    return pd.DataFrame(conteudo)

st.title("🤖 Importador Inteligente Domínio")
arquivos = st.file_uploader("Arraste extratos (PDF/CSV/Excel)", accept_multiple_files=True)

if arquivos:
    for arq in arquivos:
        st.subheader(f"Arquivo: {arq.name}")
        
        # Leitura
        if arq.name.lower().endswith('.pdf'):
            df = extrair_dados_pdf(arq.getvalue())
        else:
            try:
                df = pd.read_excel(arq) if arq.name.endswith(('.xlsx', '.xls')) else pd.read_csv(arq, sep=None, engine='python')
                df.columns = ['DATA', 'HISTÓRICO', 'VALOR'] # Ajuste se necessário
            except: df = pd.DataFrame()

        if not df.empty:
            # FILTRO LIMPEZA: Remove saldos e linhas vazias
            df = df[~df['HISTÓRICO'].str.contains('SALDO|TOTAL|INICIAL|FINAL|SUBTOTAL', case=False, na=False)]
            
            # Cards
            c1, c2, c3 = st.columns(3)
            c1.markdown(f'<div class="metric"><div class="m-val">{len(df)}</div>Registros</div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric"><div class="m-val">R$ {df[df["VALOR"]>0]["VALOR"].sum():,.2f}</div>Entradas</div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric"><div class="card"><div class="m-val">R$ {abs(df[df["VALOR"]<0]["VALOR"].sum()):,.2f}</div>Saídas</div>', unsafe_allow_html=True)
            
            st.dataframe(df, use_container_width=True)
            
            # Botão
            txt = "\n".join([f"{r['DATA']};;{r['VALOR']:.2f};{r['HISTÓRICO']}" for _, r in df.iterrows()])
            st.download_button("🚀 Baixar .TXT p/ Domínio", txt, f"imp_{arq.name}.txt")
        else:
            st.error("Não identifiquei lançamentos. O layout desse arquivo é muito complexo para o leitor automático.")
