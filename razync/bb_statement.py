import io
import re
from datetime import datetime

from pypdf import PdfReader


_VALOR_RE = r"\d{1,3}(?:\.\d{3})*,\d{2}"
_LINHA_RE = re.compile(
    rf"^(?P<data>\d{{2}}/\d{{2}}/\d{{4}})\s+"
    rf"(?P<ag>\d{{4}})\s+(?P<lote>\d{{5}})\s+"
    rf"(?P<miolo>.*?)\s+(?P<valor>{_VALOR_RE})\s*(?P<natureza>[CD])"
    rf"(?:\s*(?P<saldo>{_VALOR_RE})\s*[CD])?\s*$",
    re.I,
)


def _valor_br(texto: str) -> float:
    return float(texto.replace('.', '').replace(',', '.'))


def parece_extrato_bb_autorizavel(file_bytes: bytes) -> bool:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        texto = '\n'.join((p.extract_text() or '') for p in reader.pages[:2])
    except Exception:
        return False
    baixo = texto.lower()
    return (
        'extrato de conta corrente - autoriz' in baixo
        and 'agência' in baixo
        and 'conta corrente' in baixo
        and 'bb rende fácil' in baixo
    )


def processar_extrato_bb_autorizavel(file_bytes: bytes):
    """Lê o extrato BB Empresa no formato 'Extrato de conta corrente - Autorizável'.

    O PDF coloca o favorecido/pagador na linha seguinte e, em linhas de Rende Fácil,
    pode colar o movimento ao saldo (ex.: '15.472,09 C0,00 C'). O parser usa a
    primeira quantia como movimento e mantém BB Rende Fácil como lançamento real,
    ignorando apenas linhas que sejam efetivamente saldos.
    """
    reader = PdfReader(io.BytesIO(file_bytes))
    linhas = []
    for pagina in reader.pages:
        linhas.extend((pagina.extract_text() or '').splitlines())

    registros = []
    atual = None
    termos_ignorar = (
        'saldo anterior',
        's a l d o',
    )

    for linha_original in linhas:
        linha = re.sub(r'\s+', ' ', linha_original).strip()
        if not linha:
            continue

        m = _LINHA_RE.match(linha)
        if m:
            if atual is not None:
                registros.append(atual)
                atual = None

            miolo = m.group('miolo').strip()
            miolo_norm = miolo.lower()
            if any(t in miolo_norm for t in termos_ignorar):
                continue

            # O último token do miolo é o Documento; o restante é o histórico.
            partes = miolo.rsplit(' ', 1)
            historico = partes[0].strip() if len(partes) == 2 else miolo
            documento = partes[1].strip() if len(partes) == 2 else ''
            valor = _valor_br(m.group('valor'))
            if m.group('natureza').upper() == 'D':
                valor = -valor

            atual = {
                'DATA': datetime.strptime(m.group('data'), '%d/%m/%Y'),
                'VALOR': round(valor, 2),
                'HISTÓRICO': historico,
                'DESCRIÇÃO': 'BANCO DO BRASIL',
                'DOCUMENTO': documento,
            }
            continue

        # Complemento/favorecido da linha imediatamente anterior. Cabeçalhos e rodapés
        # não são anexados. A conferência usa o valor/data; o complemento melhora o log.
        if atual is not None:
            baixo = linha.lower()
            if not (
                linha.startswith('Extrato de conta corrente')
                or linha.startswith('Cliente - Conta atual')
                or linha.startswith('Lançamentos')
                or linha.startswith('Dt. balancete')
                or linha.startswith('Período do extrato')
                or linha.startswith('Agência ')
                or linha.startswith('Conta corrente ')
                or linha.startswith('Transação efetuada')
                or linha.startswith('Serviço de Atendimento')
                or linha.startswith('Para deficientes')
                or linha.startswith('Ouvidoria')
                or baixo == 'rende facil'
            ):
                atual['HISTÓRICO'] = (atual['HISTÓRICO'] + ' ' + linha).strip()

    if atual is not None:
        registros.append(atual)

    return registros
