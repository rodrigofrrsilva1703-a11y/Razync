from pathlib import Path
import re

p = Path('app.py')
s = p.read_text(encoding='utf-8')

s = re.sub(
    r'^from razync\.companies import .*$',
    'from razync.companies import CONFIGURACOES_AUTOKRAFT, CONFIGURACOES_ACCEDE',
    s,
    count=1,
    flags=re.MULTILINE,
)

p.write_text(s, encoding='utf-8')
print('Import das configurações de empresas normalizado.')
