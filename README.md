# Razync

Sistema privado em Streamlit para operações bancárias e preparação de arquivos contábeis no Modelo Domínio.

## Ferramentas

- Conversor de extratos PDF, OFX, Excel e CSV.
- Conciliação diária entre extrato bancário e Razão.
- Organizador de planilhas por empresa e banco.
- Base Inteligente de classificação integrada ao Supabase.
- Exportação para Excel e TXT no padrão Domínio.

## Empresas configuradas

- 266 - Nova Geração Matriz.
- 1396 - Nova Geração Filial.
- 3 - Autokraft Industrial.
- 178 - Autokraft Projetos.
- 343 - I.S.A.

## Estrutura

- `app.py`: interface e motores contábeis existentes.
- `razync/security.py`: autenticação, limite de tentativas e expiração.
- `razync/companies.py`: configurações centralizadas das empresas Autokraft.
- `tests/`: verificações de funções críticas, imagens e Modelo Domínio.
- `.github/workflows/validate.yml`: validação automática.

## Segurança

Credenciais devem existir somente nos Secrets do Streamlit. Nunca envie
`.streamlit/secrets.toml`, arquivos `.env` ou chaves ao GitHub.

## Validação local

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m py_compile app.py razync/*.py
pytest -q
```
