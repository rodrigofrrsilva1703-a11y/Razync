from pathlib import Path


def test_central_tem_conclusao_em_lote_e_automatica():
    app = Path("app.py").read_text(encoding="utf-8")
    assert "salvar_status_tarefas_empresas_em_lote" in app
    assert "registrar_conclusao_automatica_empresa" in app
    assert "Concluir selecionadas" in app
    assert "Reabrir selecionadas" in app
    assert "tarefas_conclusao_automatica" in app
    assert "Organizador · L. Carlos Gomes" in app
    assert "Organizador · Nova Geração" in app
