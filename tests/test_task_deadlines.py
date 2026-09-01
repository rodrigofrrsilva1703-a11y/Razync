from datetime import date

from razync.task_deadlines import calcular_prioridade_empresa


def prioridade(regime, hoje, concluida=False):
    empresa = {'codigo': 3, 'regime': regime}
    tarefas = {'3': {'concluida': concluida}}
    return calcular_prioridade_empresa(
        empresa,
        tarefas,
        hoje,
        date(2026, 9, 1),
    )


def test_prazos_inclusivos_por_regime():
    assert prioridade('lucro real', date(2026, 9, 1))['vencimento'] == date(2026, 9, 10)
    assert prioridade('lucro presumido', date(2026, 9, 1))['vencimento'] == date(2026, 9, 30)
    assert prioridade('simples nacional', date(2026, 9, 1))['vencimento'] == date(2026, 10, 30)


def test_prioridade_atrasada_urgente_e_concluida():
    assert prioridade('lucro real', date(2026, 9, 11))['status'] == 'Atrasada'
    assert prioridade('lucro real', date(2026, 9, 8))['status'] == 'Urgente'
    assert prioridade('lucro real', date(2026, 9, 20), True)['status'] == 'Concluída'
