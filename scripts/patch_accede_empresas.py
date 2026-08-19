from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

s = s.replace(
    'from razync.companies import CONFIGURACOES_AUTOKRAFT',
    'from razync.companies import CONFIGURACOES_AUTOKRAFT, CONFIGURACOES_ACCEDE',
    1
)

s = s.replace(
    "    if 'daycoval' in texto:\n        return 'daycoval'\n    return ''",
    "    if 'daycoval' in texto:\n        return 'daycoval'\n    if 'sicredi' in texto:\n        return 'sicredi'\n    return ''",
    1
)

s = s.replace(
    "        'daycoval': 'Daycoval'\n    }.get(chave, chave)",
    "        'daycoval': 'Daycoval', 'sicredi': 'Sicredi'\n    }.get(chave, chave)",
    1
)

s = s.replace(
    "                    'fibra': 'BANCO FIBRA', 'daycoval': 'BANCO DAYCOVAL'\n                }[banco_alvo]",
    "                    'fibra': 'BANCO FIBRA', 'daycoval': 'BANCO DAYCOVAL',\n                    'sicredi': 'SICREDI'\n                }[banco_alvo]",
    1
)

s = s.replace(
    "if banco_linha not in {'itau', 'bradesco', 'fibra', 'daycoval'} or not assinatura:",
    "if banco_linha not in {'itau', 'bradesco', 'fibra', 'daycoval', 'sicredi'} or not assinatura:",
    1
)

p.write_text(s, encoding='utf-8')
print('Núcleo ACCEDE/Sicredi aplicado.')
