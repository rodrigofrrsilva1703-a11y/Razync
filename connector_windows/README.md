# Conector Razync para Windows

MVP do serviço local que permite ao Razync usar certificados já instalados no
Windows sem enviar ou exportar a chave privada.

## O que já funciona

- Serviço HTTP limitado a `127.0.0.1:17891`.
- Pareamento por código e token local.
- Lista certificados com chave privada dos repositórios do usuário e da máquina.
- Assina desafios SHA-256/RSA dentro do Windows.
- Compatível com certificados A1 instalados e preparado para certificados A3
  cujo provedor disponibilize uma chave RSA pelo repositório do Windows.
- CORS limitado ao Razync publicado e aos endereços locais de desenvolvimento.

## Instalação de desenvolvimento

1. Baixe a pasta `connector_windows`.
2. Clique com o botão direito em `install.ps1` e execute com PowerShell.
3. Caso o Windows bloqueie o script, abra o PowerShell nessa pasta e execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

O instalador copia os arquivos para
`%LOCALAPPDATA%\Razync\Connector\app` e adiciona a inicialização automática
somente para o usuário atual.

## API local

- `GET /v1/health`: teste público de disponibilidade.
- `POST /v1/pair`: troca o código exibido pelo token local.
- `GET /v1/certificates`: lista certificados, exige Bearer token.
- `POST /v1/sign`: assina um desafio Base64, exige Bearer token.

A chave privada nunca é retornada. A rota de assinatura retorna a assinatura e o
certificado público para validação no servidor.

## Próximas etapas

1. Componente do Streamlit para detectar e parear o conector pelo navegador.
2. Validação criptográfica do desafio no backend do Razync.
3. Fila assinada de operações autorizadas.
4. Adaptador específico para consulta de DCTFWeb/e-CAC.
5. Empacotamento em executável e instalador assinado.
