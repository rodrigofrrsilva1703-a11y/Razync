from datetime import date

from razync.task_center import classificar_tarefa, ordenar_tarefas, resumir_tarefas


def test_classifica_atraso_hoje_e_planejada():
    hoje = date(2026, 9, 1)
    assert classificar_tarefa({'status': 'Pendente', 'prazo': '2026-08-31'}, hoje)['faixa'] == 'Atrasada'
    assert classificar_tarefa({'status': 'Pendente', 'prazo': '2026-09-01'}, hoje)['faixa'] == 'Hoje'
    assert classificar_tarefa({'status': 'Pendente', 'prazo': '2026-09-10'}, hoje)['faixa'] == 'Planejada'


def test_resumo_e_ordenacao_profissional():
    hoje = date(2026, 9, 1)
    tarefas = [
        {'titulo': 'Normal', 'status': 'Pendente', 'prioridade': 'Normal', 'prazo': '2026-09-10'},
        {'titulo': 'Atrasada', 'status': 'Pendente', 'prioridade': 'Baixa', 'prazo': '2026-08-30'},
        {'titulo': 'Concluída', 'status': 'Concluída', 'prioridade': 'Urgente', 'prazo': '2026-09-01'},
        {'titulo': 'Hoje urgente', 'status': 'Em andamento', 'prioridade': 'Urgente', 'prazo': '2026-09-01'},
    ]
    resumo = resumir_tarefas(tarefas, hoje)
    assert resumo == {
        'total': 4,
        'abertas': 3,
        'atrasadas': 1,
        'hoje': 1,
        'concluidas': 1,
        'progresso': 25,
    }
    assert [t['titulo'] for t in ordenar_tarefas(tarefas, hoje)][:2] == ['Atrasada', 'Hoje urgente']
