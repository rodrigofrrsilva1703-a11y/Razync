from pathlib import Path
p=Path('app_legacy.py')
s=p.read_text(encoding='utf-8')
terms=['Pago:', 'Recebido:', 'nova_geracao', '266', '1396']
for term in terms:
    print('\n###',term)
    start=0
    count=0
    while True:
        i=s.find(term,start)
        if i<0: break
        count+=1
        line=s.count('\n',0,i)+1
        a=max(0,i-500); b=min(len(s),i+900)
        print(f'--- occurrence {count} line {line} ---')
        print(s[a:b])
        start=i+len(term)
        if count>=20: break
