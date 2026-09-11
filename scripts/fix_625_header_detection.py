from pathlib import Path

p=Path('app.py')
s=p.read_text(encoding='utf-8')
old='''        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=alvo)\n        df.columns = [str(c).strip().upper() for c in df.columns]\n        if "DATA" not in df.columns or "VALOR" not in df.columns:\n            return pd.DataFrame(), pd.DataFrame(), set()\n        df["DATA"] = pd.to_datetime(df["DATA"], dayfirst=True, errors="coerce")\n        df["VALOR"] = pd.to_numeric(df["VALOR"], errors="coerce")\n        df = df.dropna(subset=["DATA", "VALOR"]).reset_index(drop=True)\n        return df, pd.DataFrame(), {banco_slug}\n'''
new='''        # O Modelo Domínio pode ter linhas de apresentação antes do cabeçalho.\n        # Detecta DATA/VALOR nas primeiras 30 linhas em vez de assumir header=0.\n        bruto = pd.read_excel(io.BytesIO(file_bytes), sheet_name=alvo, header=None)\n        linha_cabecalho = None\n        for idx in range(min(len(bruto), 30)):\n            nomes_linha = {\n                normalizar_texto(texto_celula_seguro(valor)).strip()\n                for valor in bruto.iloc[idx].tolist()\n                if texto_celula_seguro(valor)\n            }\n            if {"data", "valor"}.issubset(nomes_linha):\n                linha_cabecalho = idx\n                break\n        if linha_cabecalho is None:\n            return pd.DataFrame(), pd.DataFrame(), set()\n\n        df = pd.read_excel(\n            io.BytesIO(file_bytes), sheet_name=alvo, header=linha_cabecalho\n        )\n        df.columns = [str(c).strip().upper() for c in df.columns]\n        if "DATA" not in df.columns or "VALOR" not in df.columns:\n            return pd.DataFrame(), pd.DataFrame(), set()\n        df["DATA"] = pd.to_datetime(df["DATA"], dayfirst=True, errors="coerce")\n        df["VALOR"] = pd.to_numeric(df["VALOR"], errors="coerce")\n        df = df.dropna(subset=["DATA", "VALOR"]).reset_index(drop=True)\n        return df, pd.DataFrame(), {banco_slug}\n'''
if old not in s:
    raise SystemExit('trecho de leitura da planilha 625 não encontrado')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
assert 'linha_cabecalho = None' in s
assert 'header=linha_cabecalho' in s
print('OK: cabeçalho da planilha 625 detectado automaticamente')
