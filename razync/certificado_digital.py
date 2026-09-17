"""Cadastro seguro de certificados digitais A1 por empresa."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography import x509
from cryptography.x509.oid import NameOID, ObjectIdentifier


OID_CNPJ = ObjectIdentifier("2.16.76.1.3.3")


def _cnpj_valido(cnpj: str) -> bool:
    if not re.fullmatch(r"\d{14}", cnpj) or len(set(cnpj)) == 1:
        return False
    numeros = [int(numero) for numero in cnpj]
    for tamanho, pesos in ((12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]),
                           (13, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])):
        resto = sum(numeros[i] * pesos[i] for i in range(tamanho)) % 11
        digito = 0 if resto < 2 else 11 - resto
        if numeros[tamanho] != digito:
            return False
    return True


def _extrair_cnpj(certificado) -> str:
    textos: list[str] = []
    for item in certificado.subject:
        textos.append(str(item.value))
    try:
        san = certificado.extensions.get_extension_for_class(
            x509.SubjectAlternativeName
        ).value
        for nome in san:
            valor = getattr(nome, "value", "")
            if isinstance(valor, bytes):
                textos.append(valor.decode("latin1", errors="ignore"))
                textos.append(valor.hex())
            else:
                textos.append(str(valor))
    except x509.ExtensionNotFound:
        pass
    for texto in textos:
        somente_numeros = re.sub(r"\D", "", texto)
        for inicio in range(max(1, len(somente_numeros) - 13)):
            candidato = somente_numeros[inicio:inicio + 14]
            if _cnpj_valido(candidato):
                return candidato
    return ""


def _configuracao():
    import streamlit as st

    secao = st.secrets.get("supabase", {})
    url = str(secao.get("url", "") or st.secrets.get("SUPABASE_URL", "")).rstrip("/")
    chave = str(
        secao.get("service_key", "") or st.secrets.get("SUPABASE_SERVICE_KEY", "")
    )
    chave_mestra = str(
        st.secrets.get("CERTIFICATES_MASTER_KEY", "")
        or secao.get("certificates_master_key", "")
        or chave
    )
    if "/rest/v1" in url:
        url = url.split("/rest/v1", 1)[0]
    return url, chave, chave_mestra


def _chave_aes(segredo: str) -> bytes:
    if not segredo:
        raise RuntimeError("A chave de criptografia dos certificados não foi configurada.")
    return hashlib.sha256(("razync-certificados-v1::" + segredo).encode()).digest()


def _cifrar(pfx: bytes, senha: str, segredo: str) -> str:
    nonce = os.urandom(12)
    payload = json.dumps({
        "pfx": base64.b64encode(pfx).decode("ascii"), "senha": senha,
    }, separators=(",", ":")).encode()
    cifrado = AESGCM(_chave_aes(segredo)).encrypt(nonce, payload, b"razync-certificado-a1")
    return base64.b64encode(nonce + cifrado).decode("ascii")


def decifrar_certificado(pacote: str, segredo: str) -> tuple[bytes, str]:
    bruto = base64.b64decode(pacote)
    payload = AESGCM(_chave_aes(segredo)).decrypt(
        bruto[:12], bruto[12:], b"razync-certificado-a1"
    )
    dados = json.loads(payload.decode())
    return base64.b64decode(dados["pfx"]), str(dados["senha"])


def validar_certificado(pfx: bytes, senha: str) -> dict:
    try:
        chave_privada, certificado, _ = pkcs12.load_key_and_certificates(
            pfx, senha.encode("utf-8")
        )
    except Exception as erro:
        raise ValueError("Não foi possível abrir o certificado. Confira o arquivo e a senha.") from erro
    if certificado is None or chave_privada is None:
        raise ValueError("O arquivo não contém um certificado A1 com chave privada.")

    def atributo(oid):
        encontrados = certificado.subject.get_attributes_for_oid(oid)
        return str(encontrados[0].value) if encontrados else ""

    cnpj = _extrair_cnpj(certificado)
    titular = atributo(NameOID.COMMON_NAME)
    emissor_cn = certificado.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
    inicio = getattr(certificado, "not_valid_before_utc", None)
    fim = getattr(certificado, "not_valid_after_utc", None)
    if inicio is None:
        inicio = certificado.not_valid_before.replace(tzinfo=timezone.utc)
    if fim is None:
        fim = certificado.not_valid_after.replace(tzinfo=timezone.utc)
    return {
        "cnpj": cnpj,
        "titular": titular,
        "emissor": str(emissor_cn[0].value) if emissor_cn else certificado.issuer.rfc4514_string(),
        "numero_serie": format(certificado.serial_number, "X"),
        "validade_inicio": inicio.date().isoformat(),
        "validade_fim": fim.date().isoformat(),
        "fingerprint_sha256": certificado.fingerprint(hashes.SHA256()).hex().upper(),
    }


def _requisicao(caminho: str, metodo: str = "GET", dados=None, prefer: str = ""):
    url, chave, _ = _configuracao()
    if not url or not chave:
        raise RuntimeError("O armazenamento seguro ainda não foi configurado no servidor.")
    corpo = json.dumps(dados).encode() if dados is not None else None
    headers = {
        "apikey": chave, "Authorization": f"Bearer {chave}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(
        f"{url}/rest/v1/{caminho}", data=corpo, headers=headers, method=metodo
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resposta:
            conteudo = resposta.read().decode()
            return json.loads(conteudo) if conteudo else []
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode(errors="ignore")
        raise RuntimeError(f"Falha no armazenamento seguro ({erro.code}): {detalhe[:180]}") from erro


def buscar_certificado(empresa: str) -> dict | None:
    consulta = (
        "certificados_digitais?empresa=eq." + urllib.parse.quote(empresa)
        + "&select=empresa,codigo_empresa,cnpj,titular,emissor,numero_serie,"
        "validade_inicio,validade_fim,fingerprint_sha256,atualizado_em&limit=1"
    )
    registros = _requisicao(consulta)
    return registros[0] if registros else None


def salvar_certificado(
    empresa: str, codigo: str, pfx: bytes, senha: str, cnpj_manual: str = "",
) -> dict:
    _, _, segredo = _configuracao()
    metadados = validar_certificado(pfx, senha)
    if not metadados["cnpj"]:
        manual = re.sub(r"\D", "", cnpj_manual)
        if not _cnpj_valido(manual):
            raise ValueError(
                "O certificado não informou o CNPJ. Digite um CNPJ válido no campo manual."
            )
        metadados["cnpj"] = manual
    registro = {
        "empresa": empresa, "codigo_empresa": codigo,
        **metadados, "pacote_criptografado": _cifrar(pfx, senha, segredo),
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
    }
    retorno = _requisicao(
        "certificados_digitais?on_conflict=empresa", "POST", registro,
        "resolution=merge-duplicates,return=representation",
    )
    return retorno[0] if retorno else metadados


def excluir_certificado(empresa: str) -> None:
    _requisicao(
        "certificados_digitais?empresa=eq." + urllib.parse.quote(empresa),
        "DELETE", prefer="return=minimal",
    )


def renderizar_certificado_digital(empresa: str, nome_empresa: str) -> None:
    import streamlit as st

    codigo = (re.match(r"\s*(\d+)", nome_empresa) or [None, empresa])[1]
    chave_visual = re.sub(r"[^a-zA-Z0-9_]+", "_", empresa)
    st.markdown(
        """
        <style>
        [class*="st-key-rz_certificado_"] {
            position: fixed;
            right: 1.15rem;
            top: 4.6rem;
            bottom: auto;
            z-index: 999;
            width: auto;
            margin: 0;
            padding: 0;
            border: 0;
            background: transparent;
        }
        [class*="st-key-rz_certificado_"] [data-testid="stPopover"] button {
            min-height: 2.25rem;
            width: auto;
            padding: .34rem .78rem;
            border: 1px solid rgba(91, 203, 255, .38);
            border-radius: 999px;
            background:
                linear-gradient(135deg, rgba(21, 49, 64, .94), rgba(7, 22, 32, .97)) padding-box,
                linear-gradient(135deg, rgba(92, 211, 255, .55), rgba(27, 117, 164, .18)) border-box;
            box-shadow:
                0 10px 28px rgba(0, 0, 0, .32),
                inset 0 1px 0 rgba(255, 255, 255, .08);
            color: #f1f9fc;
            font-size: .72rem;
            font-weight: 650;
            letter-spacing: .01em;
            backdrop-filter: blur(14px) saturate(125%);
            transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
        }
        [class*="st-key-rz_certificado_"] [data-testid="stPopover"] button:hover {
            border-color: rgba(102, 218, 255, .82);
            transform: translateY(-2px);
            box-shadow:
                0 13px 32px rgba(0, 0, 0, .38),
                0 0 0 3px rgba(44, 183, 230, .08),
                inset 0 1px 0 rgba(255, 255, 255, .12);
        }
        [class*="st-key-rz_certificado_"] [data-testid="stPopover"] button:active {
            transform: translateY(0) scale(.98);
        }
        @media (max-width: 640px) {
            [class*="st-key-rz_certificado_"] {right: .7rem; top: 4.2rem; bottom: auto;}
            [class*="st-key-rz_certificado_"] [data-testid="stPopover"] button {
                min-height: 2rem; padding: .25rem .62rem; font-size: .68rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    try:
        atual = buscar_certificado(empresa)
    except Exception as erro:
        atual = None
        erro_carregamento = str(erro)
    else:
        erro_carregamento = ""

    if erro_carregamento:
        indicador, status = "🔴", "Indisponível"
    elif atual:
        validade_status = date.fromisoformat(atual["validade_fim"])
        dias_status = (validade_status - date.today()).days
        indicador = "🟢" if dias_status > 30 else "🟡" if dias_status >= 0 else "🔴"
        status = "Ativo" if dias_status >= 0 else "Vencido"
    else:
        indicador, status = "⚪", "Não cadastrado"

    with st.container(key=f"rz_certificado_{chave_visual}"):
        with st.popover(f"◈  Certificado  {indicador}"):
                st.markdown("#### Certificado Digital A1")
                st.caption(f"Status: {status}")
                if erro_carregamento:
                    st.error(erro_carregamento)
                    return
                if atual:
                    validade = date.fromisoformat(atual["validade_fim"])
                    st.write(f"**Titular:** {atual['titular'] or 'Não informado'}")
                    st.write(f"**CNPJ:** {atual['cnpj'] or 'Não informado'}")
                    st.write(f"**Validade:** {validade.strftime('%d/%m/%Y')}")
                    st.caption(
                        f"Emissor: {atual['emissor']} · Série final: "
                        f"…{str(atual['numero_serie'])[-8:]}"
                    )
                st.markdown("##### Usar certificado instalado")
                try:
                    from razync.connector_windows import render_connector_windows
                    render_connector_windows(empresa)
                except Exception as erro:
                    st.caption(f"Conector Windows indisponível: {erro}")

                st.markdown("##### Ou enviar certificado A1")
                st.caption(
                    "Arquivo e senha são armazenados com criptografia."
                )
                with st.form(f"form_certificado_{empresa}", clear_on_submit=True):
                    arquivo = st.file_uploader(
                        "Certificado A1", type=["pfx", "p12"],
                        help="Arquivo .pfx ou .p12.",
                    )
                    senha = st.text_input("Senha", type="password")
                    cnpj_manual = st.text_input(
                        "CNPJ manual (opcional)",
                        help="Use apenas se não for identificado automaticamente.",
                    )
                    confirmar = st.form_submit_button(
                        "Validar e salvar", type="primary", use_container_width=True
                    )
                if confirmar:
                    if arquivo is None or not senha:
                        st.error("Envie o certificado e informe a senha.")
                    else:
                        try:
                            metadados = validar_certificado(arquivo.getvalue(), senha)
                            salvo = salvar_certificado(
                                empresa, str(codigo), arquivo.getvalue(), senha, cnpj_manual
                            )
                            st.success(
                                "Certificado vinculado. CNPJ: "
                                + str(salvo.get("cnpj") or metadados.get("cnpj"))
                            )
                            st.rerun()
                        except Exception as erro:
                            st.error(str(erro))

                if atual:
                    st.markdown("---")
                    confirmar_exclusao = st.checkbox(
                        "Confirmar remoção", key=f"excluir_cert_{empresa}"
                    )
                    if st.button(
                        "Remover", disabled=not confirmar_exclusao,
                        key=f"btn_excluir_cert_{empresa}", use_container_width=True,
                    ):
                        excluir_certificado(empresa)
                        st.success("Certificado removido.")
                        st.rerun()
