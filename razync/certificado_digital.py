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
            border: 1px solid rgba(58, 142, 181, .28);
            border-radius: 14px;
            background: linear-gradient(135deg, rgba(12, 28, 39, .98), rgba(8, 20, 29, .98));
            padding: .78rem .95rem .62rem;
            margin: .15rem 0 .85rem;
            box-shadow: 0 8px 24px rgba(0, 0, 0, .10);
        }
        [class*="st-key-rz_certificado_"] [data-testid="stMetric"] {
            background: rgba(13, 36, 49, .72);
            border: 1px solid rgba(73, 126, 154, .22);
            border-radius: 10px;
            padding: .55rem .7rem;
        }
        [class*="st-key-rz_certificado_"] [data-testid="stExpander"] {
            border-color: rgba(73, 126, 154, .25);
            border-radius: 10px;
            background: rgba(6, 17, 24, .38);
        }
        .rz-cert-title {font-size: .96rem; font-weight: 750; color: #eef7fb;}
        .rz-cert-copy {font-size: .73rem; color: #8298a7; margin-top: .08rem;}
        .rz-cert-status {text-align: right; font-size: .75rem; font-weight: 700; padding-top: .25rem;}
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

    with st.container(key=f"rz_certificado_{chave_visual}"):
        titulo_col, status_col = st.columns([4, 1.35], vertical_alignment="center")
        with titulo_col:
            st.markdown(
                '<div class="rz-cert-title">🔐 Certificado Digital</div>'
                '<div class="rz-cert-copy">Acesso protegido para consultas fiscais da empresa.</div>',
                unsafe_allow_html=True,
            )
        with status_col:
            if erro_carregamento:
                cor, status = "#f85149", "Indisponível"
            elif atual:
                validade_status = date.fromisoformat(atual["validade_fim"])
                dias_status = (validade_status - date.today()).days
                cor = "#3fb950" if dias_status > 30 else "#d6a84b" if dias_status >= 0 else "#f85149"
                status = "Ativo" if dias_status >= 0 else "Vencido"
            else:
                cor, status = "#8298a7", "Não cadastrado"
            st.markdown(
                f'<div class="rz-cert-status" style="color:{cor};">● {status}</div>',
                unsafe_allow_html=True,
            )

        if erro_carregamento:
            st.error(erro_carregamento)
            return
        if atual:
            validade = date.fromisoformat(atual["validade_fim"])
            dias = (validade - date.today()).days
            if dias < 0:
                st.error(f"Certificado vencido em {validade.strftime('%d/%m/%Y')}.")
            elif dias <= 30:
                st.warning(f"Certificado vence em {dias} dia(s): {validade.strftime('%d/%m/%Y')}.")
            else:
                st.success(f"Certificado válido até {validade.strftime('%d/%m/%Y')}.")
            m1, m2, m3 = st.columns([1.25, 1.45, 1])
            m1.metric("CNPJ", atual["cnpj"] or "Não informado")
            m2.metric("Titular", atual["titular"] or "Não informado")
            m3.metric("Validade", validade.strftime("%d/%m/%Y"))
            st.caption(
                f"Emissor: {atual['emissor']} · Série final: "
                f"…{str(atual['numero_serie'])[-8:]}"
            )
        else:
            st.info(
                "Nenhum certificado vinculado. Cadastre um A1 para preparar as "
                "consultas fiscais automáticas."
            )

        rotulo_gerenciar = "Substituir ou remover" if atual else "Cadastrar certificado A1"
        with st.expander(rotulo_gerenciar, expanded=not atual):
            st.caption(
                "O arquivo e a senha são criptografados antes do armazenamento. "
                "A senha nunca é exibida novamente."
            )
            with st.form(f"form_certificado_{empresa}", clear_on_submit=True):
                arquivo = st.file_uploader(
                    "Arquivo do certificado", type=["pfx", "p12"],
                    help="Selecione o arquivo A1 no formato .pfx ou .p12.",
                )
                col_senha, col_cnpj = st.columns(2)
                with col_senha:
                    senha = st.text_input("Senha", type="password")
                with col_cnpj:
                    cnpj_manual = st.text_input(
                        "CNPJ manual (opcional)",
                        help="Use apenas se o certificado não informar automaticamente.",
                    )
                confirmar = st.form_submit_button(
                    "Validar e salvar certificado", type="primary", use_container_width=True
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
                            "Certificado vinculado. CNPJ reconhecido: "
                            + str(salvo.get("cnpj") or metadados.get("cnpj"))
                        )
                        st.rerun()
                    except Exception as erro:
                        st.error(str(erro))

            if atual:
                st.markdown("---")
                st.caption("Remova somente quando o certificado não for mais utilizado.")
                confirmar_exclusao = st.checkbox(
                    "Confirmo a remoção", key=f"excluir_cert_{empresa}"
                )
                if st.button(
                    "Remover certificado", disabled=not confirmar_exclusao,
                    key=f"btn_excluir_cert_{empresa}", use_container_width=True,
                ):
                    excluir_certificado(empresa)
                    st.success("Certificado removido.")
                    st.rerun()
