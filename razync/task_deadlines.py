from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


PRAZOS_EMPRESAS_DIAS = {
    'lucro real': 10,
    'lucro presumido': 30,
    'simples nacional': 60,
}


def obter_competencia_operacional():
    hoje = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    return hoje, hoje.replace(day=1)


def calcular_prioridade_empresa(empresa, tarefas_competencia, hoje, competencia):
    regime = str(empresa.get('regime', '')).casefold().strip()
    prazo_dias = PRAZOS_EMPRESAS_DIAS.get(regime, 60)
    vencimento = competencia + timedelta(days=prazo_dias - 1)
    codigo = str(empresa.get('codigo', ''))
    concluida = bool(
        tarefas_competencia.get(codigo, {}).get('concluida', False)
    )
    dias_restantes = (vencimento - hoje).days

    if concluida:
        status, classe, ordem = 'Concluída', 'concluida', 4
    elif dias_restantes < 0:
        status, classe, ordem = 'Atrasada', 'atrasada', 0
    elif dias_restantes <= 3:
        status, classe, ordem = 'Urgente', 'urgente', 1
    elif dias_restantes <= 7:
        status, classe, ordem = 'Próxima', 'proxima', 2
    else:
        status, classe, ordem = 'No prazo', 'no-prazo', 3

    return {
        'status': status,
        'classe': classe,
        'ordem': ordem,
        'vencimento': vencimento,
        'dias_restantes': dias_restantes,
        'concluida': concluida,
        'prazo_dias': prazo_dias,
    }
