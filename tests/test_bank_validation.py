from razync.bank_validation import (
    diagnostico_pdf_sem_lancamentos,
    validar_fechamento_saldo,
)


def test_fechamento_saldo_bate():
    resultado = validar_fechamento_saldo(100.00, 135.50, [50.00, -14.50])
    assert resultado['disponivel'] is True
    assert resultado['ok'] is True
    assert resultado['saldo_calculado'] == 135.50
    assert resultado['diferenca'] == 0.0


def test_fechamento_saldo_detecta_diferenca():
    resultado = validar_fechamento_saldo(100.00, 136.00, [50.00, -14.50])
    assert resultado['ok'] is False
    assert resultado['diferenca'] == -0.50


def test_fechamento_sem_saldos_nao_inventa_resultado():
    resultado = validar_fechamento_saldo(None, None, [10.00])
    assert resultado['disponivel'] is False
    assert resultado['ok'] is None


def test_diagnostico_ocr_falhou_sem_traceback():
    mensagem = diagnostico_pdf_sem_lancamentos(
        'BANCO BRADESCO', True, ocr_executado=True, erro_ocr='Tesseract indisponível'
    )
    assert 'BRADESCO' in mensagem
    assert 'OCR' in mensagem
    assert 'Tesseract indisponível' in mensagem


def test_diagnostico_ocr_sem_lancamentos():
    mensagem = diagnostico_pdf_sem_lancamentos(
        'BANCO BRADESCO', True, ocr_executado=True
    )
    assert 'nenhum lançamento' in mensagem.lower()
