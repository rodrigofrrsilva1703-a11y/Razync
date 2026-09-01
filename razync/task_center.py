from datetime import date, datetime


PRIORIDADE_ORDEM = {'Urgente': 0, 'Alta': 1, 'Normal': 2, 'Baixa': 3}
STATUS_FINAIS = {'Concluída', 'Cancelada'}


def _parse_data(valor):
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return datetime.fromisoformat(str(valor)[:10]).date()


def classificar_tarefa(tarefa, hoje):
    status = str(tarefa.get('status') or 'Pendente')
    prazo = _parse_data(tarefa.get('prazo'))
    if status in STATUS_FINAIS:
        return {'faixa': status, 'ordem': 5, 'dias_restantes': None, 'atrasada': False}
    if prazo is None:
        return {'faixa': 'Sem prazo', 'ordem': 4, 'dias_restantes': None, 'atrasada': False}
    dias = (prazo - hoje).days
    if dias < 0:
        return {'faixa': 'Atrasada', 'ordem': 0, 'dias_restantes': dias, 'atrasada': True}
    if dias == 0:
        return {'faixa': 'Hoje', 'ordem': 1, 'dias_restantes': 0, 'atrasada': False}
    if dias <= 3:
        return {'faixa': 'Próxima', 'ordem': 2, 'dias_restantes': dias, 'atrasada': False}
    return {'faixa': 'Planejada', 'ordem': 3, 'dias_restantes': dias, 'atrasada': False}


def ordenar_tarefas(tarefas, hoje):
    def chave(tarefa):
        classificacao = classificar_tarefa(tarefa, hoje)
        prazo = _parse_data(tarefa.get('prazo')) or date.max
        prioridade = PRIORIDADE_ORDEM.get(str(tarefa.get('prioridade') or 'Normal'), 2)
        return (classificacao['ordem'], prioridade, prazo, str(tarefa.get('titulo') or '').casefold())

    return sorted(tarefas, key=chave)


def resumir_tarefas(tarefas, hoje):
    total = len(tarefas)
    concluidas = sum(1 for t in tarefas if str(t.get('status')) == 'Concluída')
    abertas = sum(1 for t in tarefas if str(t.get('status')) not in STATUS_FINAIS)
    atrasadas = sum(1 for t in tarefas if classificar_tarefa(t, hoje)['faixa'] == 'Atrasada')
    hoje_qtd = sum(1 for t in tarefas if classificar_tarefa(t, hoje)['faixa'] == 'Hoje')
    progresso = round((concluidas / total) * 100) if total else 0
    return {
        'total': total,
        'abertas': abertas,
        'atrasadas': atrasadas,
        'hoje': hoje_qtd,
        'concluidas': concluidas,
        'progresso': progresso,
    }
