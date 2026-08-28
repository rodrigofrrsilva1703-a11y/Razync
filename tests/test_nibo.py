from razync.nibo import _valor_br


def test_valor_br_corrige_virgula_perdida_pelo_ocr():
    assert _valor_br("20.11583") == 20115.83
    assert _valor_br("(20.11583)") == -20115.83


def test_valor_br_preserva_formatos_normais():
    assert _valor_br("61.722,68") == 61722.68
    assert _valor_br("(41.271,20)") == -41271.20
    assert _valor_br("123.45") == 123.45
