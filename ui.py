"""Shared visual components. All colors are explicit to prevent theme conflicts."""
import html
import streamlit as st
import plotly.graph_objects as go
RED='#e5484d'; INK='#202536'; MUTED='#747c8e'; BLUE='#5274c8'; TEAL='#219b8f'
PALETTE=[RED,BLUE,TEAL,'#b480ce','#e4a64b']
def style():
    st.markdown('''<style>
    .stApp{background:#f6f7fb;color:#202536}
    [data-testid="stHeader"]{background:#f6f7fb;color:#202536}
    .block-container{padding-top:3.2rem;padding-bottom:2rem;max-width:1540px}
    [data-testid="stSidebar"]{background:#fff;border-right:1px solid #e9eaf0}
    [data-testid="stSidebar"] .block-container{padding-top:1rem}
    h1,h2,h3,h4,p,label{color:inherit}
    [data-testid="stSidebar"] [data-testid="stRadio"] label{padding:5px 0}
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked){background:#fff0f1;border-radius:9px;color:#c8313d}
    [data-testid="stVerticalBlockBorderWrapper"]>div{border-color:#e7e9ef!important;border-radius:16px!important;background:white}
    div[data-testid="stMetric"]{background:white;border:1px solid #e7e9ef;border-radius:14px;padding:16px}
    div[data-testid="stMetric"] *{color:#202536!important}
    .brand{display:flex;align-items:center;gap:10px;margin:8px 0 22px;color:#202536}
    .brand-icon{background:#e5484d;color:#fff;width:40px;height:40px;border-radius:12px;display:grid;place-items:center;font-weight:900;font-size:24px}
    .brand-name{font-size:25px;letter-spacing:-1px;font-weight:800;line-height:1.1}.brand-sub{font-size:10px;letter-spacing:2px;color:#858b9b;margin-top:5px}
    .eyebrow{font-size:11px;font-weight:700;letter-spacing:1.7px;color:#a4a9b8;text-transform:uppercase;margin-bottom:8px}
    .page-title{font-size:30px;font-weight:800;letter-spacing:-1px;color:#202536;line-height:1.2;margin-bottom:8px}
    .page-note{color:#727b8e;font-size:14px;margin-bottom:22px}
    .hero{background:#202536;border-radius:18px;padding:24px 28px;margin:0 0 22px;color:white;display:flex;align-items:center;justify-content:space-between;gap:18px}
    .hero h2{font-size:28px;line-height:1.2;color:white!important;margin:0 0 8px;letter-spacing:-.7px}.hero p{font-size:14px;color:#bec5d7!important;margin:0;max-width:630px}
    .hero-stat{background:#34394b;border-radius:14px;padding:18px 23px;min-width:165px;color:white}.hero-stat strong{display:block;font-size:29px;color:#fff}.hero-stat span{font-size:11px;color:#c1c7d7}
    .kpi{background:white;border:1px solid #e6e8ee;border-radius:15px;padding:18px 20px;min-height:139px;box-sizing:border-box;margin-bottom:10px}
    .kpi-label{font-size:12px;font-weight:600;color:#626d80}.kpi-value{font-size:30px;line-height:1.5;font-weight:800;letter-spacing:-1px;color:#202536}.kpi-note{font-size:11px;color:#697386}
    .kpi.accent{background:#fff0f1;border-color:#f9d9dc}.kpi.accent .kpi-value{color:#d93744}
    .insight{background:#fff6f2;border-left:3px solid #e5484d;padding:14px 17px;border-radius:0 10px 10px 0;color:#596174;font-size:13px;margin:8px 0 18px}.insight b{color:#202536}
    .section-title{font-size:17px;font-weight:750;color:#202536;margin:3px 0 4px}.section-note{font-size:12px;color:#697386;margin-bottom:8px}
    .mini-label{font-size:11px;color:#81899b;text-transform:uppercase;letter-spacing:1px}
    .footer{font-size:11px;color:#9299a8;text-align:center;padding:24px 0 8px;border-top:1px solid #e8eaf0;margin-top:28px}
    .stButton button[kind="primary"],.stDownloadButton button[kind="primary"]{background:#e5484d;color:#fff;border:none}
    [data-testid="stCaptionContainer"]{color:#788194}
    @media(max-width:750px){.hero{padding:20px;display:block}.hero-stat{margin-top:15px}.page-title{font-size:25px}.kpi-value{font-size:25px}}
    </style>''',unsafe_allow_html=True)
def esc(s):return html.escape(str(s))
def title(name,note):
    st.markdown(f'<div class="eyebrow">FITLENS / FITNESS ANALYTICS</div><div class="page-title">{esc(name)}</div><div class="page-note">{esc(note)}</div>',unsafe_allow_html=True)
def kpi(label,value,note='',accent=False):
    st.markdown(f'<div class="kpi {"accent" if accent else ""}"><div class="kpi-label">{esc(label)}</div><div class="kpi-value">{esc(value)}</div><div class="kpi-note">{esc(note)}</div></div>',unsafe_allow_html=True)
def cards(items):
    for i,(col,item) in enumerate(zip(st.columns(len(items)),items)):
        with col:kpi(*item,accent=i==0)
def heading(name,note=''):
    st.markdown(f'<div class="section-title">{esc(name)}</div><div class="section-note">{esc(note)}</div>',unsafe_allow_html=True)
def insight(text):st.markdown('<div class="insight">'+text+'</div>',unsafe_allow_html=True)
def chart(fig,height=325,key=None):
    fig.update_layout(template='plotly_white',height=height,paper_bgcolor='#ffffff',plot_bgcolor='#ffffff',font=dict(family='Arial, sans-serif',size=12,color=INK),margin=dict(l=12,r=18,t=15,b=18),colorway=PALETTE,legend=dict(orientation='h',y=1.12,x=0,font=dict(size=11)),legend_title_text='',hoverlabel=dict(bgcolor='#202536',font_color='white'))
    fig.update_xaxes(gridcolor='#f0f1f5',zeroline=False,title_font=dict(size=11),tickfont=dict(size=11))
    fig.update_yaxes(gridcolor='#f0f1f5',zeroline=False,title_font=dict(size=11),tickfont=dict(size=11))
    st.plotly_chart(fig,width='stretch',theme=None,key=key,config={'displaylogo':False,'modeBarButtonsToRemove':['lasso2d','select2d'],'toImageButtonOptions':{'format':'png','scale':2,'filename':'fitlens_chart'}})
def empty(message):st.info(message)
def fmt(v,suffix='',digits=0):
    import pandas as pd
    return '—' if pd.isna(v) else f'{v:,.{digits}f}{suffix}'
