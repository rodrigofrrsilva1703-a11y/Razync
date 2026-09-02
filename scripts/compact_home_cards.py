from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
marker = '/* Home compact dashboard v4 */'
if marker not in s:
    raise SystemExit('Home compact dashboard v4 não encontrado')

css = r'''

/* Home compact cards v5 */
.rz-home-metrics {
    gap: .48rem !important;
    margin: .55rem 0 .7rem !important;
}
.rz-home-metric {
    min-height: 84px !important;
    padding: .68rem .78rem !important;
    border-radius: 11px !important;
}
.rz-home-metric-label {
    font-size: .59rem !important;
    margin-bottom: .2rem !important;
}
.rz-home-metric-value {
    font-size: 1.38rem !important;
    line-height: 1 !important;
}
.rz-home-metric-sub {
    margin-top: .22rem !important;
    font-size: .63rem !important;
}
.rz-home-progress-track {
    height: 4px !important;
    margin-top: .38rem !important;
}
.rz-home-main-grid {
    gap: .8rem !important;
}
.rz-home-actions .stButton > button {
    min-height: 66px !important;
    padding: .7rem .85rem !important;
    border-radius: 11px !important;
}
.rz-home-actions .stButton > button p {
    font-size: .74rem !important;
    line-height: 1.25 !important;
}
.rz-home-actions .stButton > button strong {
    font-size: .87rem !important;
}
.rz-home-overview {
    padding: .82rem .9rem !important;
    border-radius: 12px !important;
}
.rz-home-overview-title {
    font-size: 1rem !important;
    margin-bottom: .18rem !important;
}
.rz-home-overview-copy {
    font-size: .69rem !important;
    margin-bottom: .5rem !important;
}
.rz-home-overview-row {
    padding: .42rem 0 !important;
    gap: .45rem !important;
}
.rz-home-overview-row strong {
    font-size: .7rem !important;
}
.rz-home-overview-row span {
    font-size: .62rem !important;
}
@media (max-width: 900px) {
    .rz-home-metric { min-height: 78px !important; }
    .rz-home-actions .stButton > button { min-height: 62px !important; }
}
'''

needle = "\n# TELA 1: MENU PRINCIPAL (HOME)\n"
if needle not in s:
    raise SystemExit('ponto de inserção não encontrado')
s = s.replace(needle, "\nst.markdown('''<style>" + css + "</style>''', unsafe_allow_html=True)\n" + needle, 1)
p.write_text(s, encoding='utf-8')
