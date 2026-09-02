"""Catálogo das empresas atendidas pelo Razync, organizado por regime tributário.

Empresas já implementadas apontam para a chave de sistema existente. As demais
ficam cadastradas como áreas pendentes, sem inventar ferramentas, bancos ou contas.
"""

EMPRESAS = [
    {"codigo": 3, "nome": "AUTOKRAFT INDUSTRIAL DO NORDESTE LTDA", "regime": "LUCRO REAL", "chave_sistema": "autokraft_industrial"},
    {"codigo": 47, "nome": "CRJ CORRETORA DE SEGUROS LTDA", "regime": "SIMPLES NACIONAL"},
    {"codigo": 88, "nome": "H & W SERVICOS MEDICOS S S LTDA", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 154, "nome": "R.M. SERVICOS POSTAIS LTDA. - EPP", "regime": "SIMPLES NACIONAL"},
    {"codigo": 178, "nome": "AUTOKRAFT PROJETOS E SERVICOS LTDA – ME", "regime": "LUCRO PRESUMIDO", "chave_sistema": "autokraft_projetos"},
    {"codigo": 257, "nome": "F. CHAUVIN INDÚSTRIA, COMÉRCIO, IMPORTAÇÃO E EXPORTAÇÃO DE COSMÉTICOS LTDA", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 266, "nome": "NOVA GERACAO COMERCIAL ELETRICA LTDA", "regime": "LUCRO PRESUMIDO", "chave_sistema": "nova_geracao", "estabelecimento": "matriz"},
    {"codigo": 242, "nome": "ELETRO FORTE COMERCIAL ELETRICA LTDA", "regime": "LUCRO REAL"},
    {"codigo": 285, "nome": "L. CARLOS GOMES – ME", "regime": "LUCRO REAL", "chave_sistema": "lcarlos"},
    {"codigo": 321, "nome": "SISTEMA SERVICOS DE AUTOMACAO LTDA EPP", "regime": "SIMPLES NACIONAL"},
    {"codigo": 336, "nome": "BRAMEX-FER COMERCIO DE FERROS E RECICLÁVEIS LTDA", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 343, "nome": "ISA - INTEGRADORA DE SISTEMAS DE AUTOMACAO COMERCIO E INDUSTRIA EIRELI", "regime": "SIMPLES NACIONAL", "chave_sistema": "isa"},
    {"codigo": 569, "nome": "V1BB CORRETAGEM DE SEGUROS LTDA.", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 625, "nome": "VALEAN SEGURANÇA E MEDICINA DO TRABALHO EIRELI ME", "regime": "SIMPLES NACIONAL"},
    {"codigo": 626, "nome": "VALEAN ASSESSORIA EM SEGURANÇA DO TRABALHO LTDA - EPP", "regime": "SIMPLES NACIONAL"},
    {"codigo": 734, "nome": "NDC TREINAMENTOS PSICANALISE E INOVACAO EM EMPRESAS LTDA", "regime": "SIMPLES NACIONAL"},
    {"codigo": 770, "nome": "BRAMEX SERVICE E SERVICOS DE FERROS LTDA - ME", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 831, "nome": "SUDANY HOLDING PATRIMONIAL LTDA", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 832, "nome": "DANFAT HOLDING PATRIMONIAL EIRELI", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 841, "nome": "LUCRATIVITE SERVICOS ESPECIALIZADOS DE APOIO ADMINISTRATIVO LTDA - ME", "regime": "SIMPLES NACIONAL"},
    {"codigo": 912, "nome": "VITAL SAFETY CONSULTORIA E TREINAMENTO LTDA - ME", "regime": "SIMPLES NACIONAL"},
    {"codigo": 964, "nome": "WILLIANS VENANCIO ALMEIDA - ME", "regime": "SIMPLES NACIONAL"},
    {"codigo": 968, "nome": "RADANI ELETRONICA E AUTOMACAO LTDA", "regime": "SIMPLES NACIONAL"},
    {"codigo": 969, "nome": "ENGEKRAFT AUTOMAÇÃO LTDA - EPP", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 993, "nome": "SPIRA CONSTRUTORA E INCORPORAÇÃO EIRELI", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 1000, "nome": "ACCEDE AUTOMACAO INDUSTRIAL EIRELI", "regime": "LUCRO PRESUMIDO", "chave_sistema": "accede_automacao"},
    {"codigo": 1001, "nome": "ACCEDE EQUIPAMENTOS INDUSTRIAIS LTDA - EPP", "regime": "LUCRO PRESUMIDO", "chave_sistema": "accede_equipamentos"},
    {"codigo": 1064, "nome": "TECH CONTROL AUTOMACAO BRASIL LTDA", "regime": "SIMPLES NACIONAL"},
    {"codigo": 1096, "nome": "UP PACK BRAZIL EIRELI EPP", "regime": "LUCRO PRESUMIDO", "chave_sistema": "up_pack"},
    {"codigo": 1108, "nome": "CHM HOLDING PATRIMONIAL LTDA", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 1111, "nome": "VAREJAO DOS PRIMOS COM MAT ELET TINTAS E FERRAGENS LTDA", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 1112, "nome": "VAREJAO DOS PRIMOS COM MAT ELET TINTAS E FERRAGENS LTDA (Filial 0001)", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 1113, "nome": "VAREJAO DOS PRIMOS COM MAT ELET TINTAS E FERRAGENS LTDA (Filial 0002)", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 1114, "nome": "VAREJAO DOS PRIMOS COM MAT ELET TINTAS E FERRAGENS LTDA (Filial 0003)", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 1198, "nome": "TWV ADMINISTRADORA HOTELEIRA LTDA", "regime": "SIMPLES NACIONAL"},
    {"codigo": 1208, "nome": "KAIROS DESMONTE INDUSTRIAIS EIRELI - ME", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 1211, "nome": "GZ IMPORTADORA E EXPORTADORA LTDA EPP (ANTIGA BODY-UP)", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 1248, "nome": "RGR IMPORTADORA E EXPORTADORA LTDA - EPP", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 1320, "nome": "T. W. GUAIMBÊ – EXCLUSIVE SUÍTES HOTEL LTDA", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 1396, "nome": "NOVA GERAÇÃO COMERCIAL ELETRICA LTDA (FILIAL)", "regime": "LUCRO PRESUMIDO", "chave_sistema": "nova_geracao", "estabelecimento": "filial"},
    {"codigo": 1402, "nome": "VGV EMPREENDIMENTOS LTDA - ME", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 1408, "nome": "ELETRO FORTE COMERCIAL ELÉTRICA LTDA. (FILIAL)", "regime": "LUCRO REAL"},
    {"codigo": 1487, "nome": "H & G CONSULTORIA FINANCEIRAS LTDA (Cliente a partir de 01/09/2025)", "regime": "SIMPLES NACIONAL"},
    {"codigo": 1520, "nome": "SOUZA LEMES HOLDING PATRIMONIAL LTDA", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 1522, "nome": "PRISCILA CAMARGO GARCIA DE OLIVEIRA LTDA", "regime": "SIMPLES NACIONAL"},
    {"codigo": 1529, "nome": "DIAS E PEREIRA SOCIEDADE DE ADVOGADOS", "regime": "LUCRO PRESUMIDO", "chave_sistema": "dias_pereira"},
    {"codigo": 1530, "nome": "DIAS PEREIRA SOCIEDADE INDIVIDUAL DE ADVOCACIA", "regime": "LUCRO PRESUMIDO"},
    {"codigo": 1532, "nome": "MARIA APARECIDA DIAS PEREIRA NARBUTIS SOCIEDADE UNIPESSOAL LTDA", "regime": "SIMPLES NACIONAL"},
]

REGIMES_ORDEM = ("LUCRO REAL", "LUCRO PRESUMIDO", "SIMPLES NACIONAL")

for empresa in EMPRESAS:
    empresa.setdefault("chave", f"cadastro_{empresa['codigo']}")
    empresa["rotulo"] = f"{empresa['codigo']} - {empresa['nome']}"

EMPRESAS_POR_REGIME = {
    regime: [empresa for empresa in EMPRESAS if empresa["regime"] == regime]
    for regime in REGIMES_ORDEM
}

EMPRESAS_POR_CHAVE = {empresa["chave"]: empresa for empresa in EMPRESAS}
