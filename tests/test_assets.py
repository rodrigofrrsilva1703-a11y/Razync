from pathlib import Path

import openpyxl
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def test_imagens_da_marca_abrem():
    for nome in ["razync-icon.png", "razync-logo-original.png"]:
        caminho = ROOT / "assets" / nome
        assert caminho.exists()
        with Image.open(caminho) as imagem:
            imagem.verify()


def test_modelo_dominio_abre():
    caminho = ROOT / "Modelo dominio.xlsx"
    pasta = openpyxl.load_workbook(caminho, read_only=True, data_only=False)
    assert pasta.sheetnames
    pasta.close()
