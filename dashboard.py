"""
Dashboard Prestação de Contas - Igreja
Requisitos: pip install dash plotly pandas openpyxl
Uso: python dashboard_app.py
Acesse: http://localhost:8050
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import os

# ── Configurações ─────────────────────────────────────────────────────────────
ARQUIVO_EXCEL = "DADOS_DASHBOARD_CONSOLIDADO.xlsx"

CORES = {
    "primaria":   "#1B3A6B",
    "receita":    "#2ECC71",
    "despesa":    "#E74C3C",
    "destaque":   "#F39C12",
    "fundo":      "#F4F6F9",
    "card":       "#FFFFFF",
    "texto":      "#2C3E50",
    "subtexto":   "#7F8C8D",
    "pessoal":    "#3498DB",
    "outras":     "#9B59B6",
}

MESES_ORD = ['JANEIRO','FEVEREIRO','MARÇO','ABRIL','MAIO','JUNHO',
             'JULHO','AGOSTO','SETEMBRO','OUTUBRO','NOVEMBRO','DEZEMBRO']
MESES_ABR = ['Jan','Fev','Mar','Abr','Mai','Jun',
             'Jul','Ago','Set','Out','Nov','Dez']

# ── Leitura e preparação dos dados ───────────────────────────────────────────
df_base = pd.read_excel(ARQUIVO_EXCEL, sheet_name='Base_Pivotada')
df_orca = pd.read_excel(ARQUIVO_EXCEL, sheet_name='Resumo_Orcado_Realizado')

df_base['MES_N']   = df_base['MES'].map({m: i+1 for i, m in enumerate(MESES_ORD)})
df_base['MES_ABR'] = df_base['MES'].map({m: a for m, a in zip(MESES_ORD, MESES_ABR)})

receita_mes  = df_base[df_base['CENTRORESULDADO']=='RECEITA'].groupby('MES_N')['VALOR'].sum().sort_index()
desp_pes_mes = df_base[df_base['CENTRORESULDADO']=='DESPESAS PESSOAL'].groupby('MES_N')['VALOR'].sum().sort_index()
outras_mes   = df_base[df_base['CENTRORESULDADO']=='OUTRAS DESPESAS'].groupby('MES_N')['VALOR'].sum().sort_index()

rec_v   = receita_mes.values
dep_v   = desp_pes_mes.values
out_v   = outras_mes.values
saldo_v = rec_v - dep_v - out_v

total_receita  = rec_v.sum()
total_desp_pes = dep_v.sum()
total_outras   = out_v.sum()
total_despesas = total_desp_pes + total_outras
saldo_total    = total_receita - total_despesas
pct_exec       = total_despesas / total_receita * 100

rec_orca = df_orca[df_orca['RECDESP']==1]['ORÇADO'].sum()
rec_real = df_orca[df_orca['RECDESP']==1]['REALIZADO'].sum()
dep_orca = df_orca[df_orca['RECDESP']==-1]['ORÇADO'].sum()
dep_real = df_orca[df_orca['RECDESP']==-1]['REALIZADO'].sum()

pct_rec = rec_real / rec_orca * 100 if rec_orca else 0
pct_dep = dep_real / dep_orca * 100 if dep_orca else 0


# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_brl(v):
    return f"R$ {v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

def card_style(borda):
    return {
        "background": CORES["card"],
        "borderRadius": "12px",
        "padding": "20px 16px",
        "textAlign": "center",
        "boxShadow": "0 2px 10px rgba(0,0,0,0.08)",
        "borderTop": f"4px solid {borda}",
        "flex": "1",
        "minWidth": "180px",
    }

def make_card(titulo, valor, sub, cor):
    return html.Div([
        html.P(titulo, style={"color": CORES["subtexto"], "fontWeight": "700",
                               "fontSize": "11px", "marginBottom": "6px", "letterSpacing": "0.5px"}),
        html.H3(valor, style={"color": cor, "margin": "4px 0", "fontSize": "22px"}),
        html.P(sub, style={"color": CORES["subtexto"], "fontSize": "11px", "margin": "0"}),
    ], style=card_style(cor))


# ════════════════════════════════════════════════════════════════════════════════
#  GRÁFICOS
# ════════════════════════════════════════════════════════════════════════════════

def fig_receita_despesa():
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Receita', x=MESES_ABR, y=rec_v,
                         marker_color=CORES["receita"], opacity=0.85))
    fig.add_trace(go.Bar(name='Despesa Total', x=MESES_ABR, y=dep_v + out_v,
                         marker_color=CORES["despesa"], opacity=0.85))
    fig.update_layout(
        title=dict(text="Receita vs Despesa Total por Mês", y=0.97, x=0.5, xanchor='center'),
        barmode='group', plot_bgcolor=CORES["fundo"], paper_bgcolor=CORES["fundo"],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis_tickprefix="R$", yaxis_tickformat=",.0f",
        margin=dict(t=70, b=20, l=10, r=10)
    )
    return fig

def fig_saldo_mensal():
    cores_saldo = [CORES["receita"] if s >= 0 else CORES["despesa"] for s in saldo_v]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=MESES_ABR, y=saldo_v, marker_color=cores_saldo,
                         name='Saldo', opacity=0.8))
    fig.add_trace(go.Scatter(x=MESES_ABR, y=saldo_v, mode='lines+markers',
                             line=dict(color=CORES["primaria"], width=2),
                             marker=dict(size=7), name='Tendência'))
    fig.add_hline(y=0, line_dash="dash", line_color=CORES["texto"], opacity=0.5)
    fig.update_layout(
        title="Saldo Mensal (Receita − Despesas)",
        plot_bgcolor=CORES["fundo"], paper_bgcolor=CORES["fundo"],
        showlegend=False, yaxis_tickprefix="R$", yaxis_tickformat=",.0f",
        margin=dict(t=50, b=20, l=10, r=10)
    )
    return fig

def fig_pizza_receita():
    rec_nat = (df_base[df_base['CENTRORESULDADO']=='RECEITA']
               .groupby('NATUREZA')['VALOR'].sum())
    rec_nat = rec_nat[rec_nat > 0]
    fig = go.Figure(go.Pie(labels=rec_nat.index, values=rec_nat.values,
                            hole=0.4, textinfo='percent+label',
                            marker_colors=px.colors.sequential.Blues_r[:len(rec_nat)]))
    fig.update_layout(title={'text': "Composição das Receitas",
                            'y': 0.985
                        },
                      plot_bgcolor=CORES["fundo"], paper_bgcolor=CORES["fundo"],
                      showlegend=False, margin=dict(t=50, b=20, l=10, r=10))
    return fig

def fig_pizza_despesa():
    fig = go.Figure(go.Pie(
        labels=['Despesas Pessoal', 'Outras Despesas'],
        values=[total_desp_pes, total_outras],
        hole=0.4, textinfo='percent+label',
        marker_colors=[CORES["despesa"], CORES["destaque"]]))
    fig.update_layout(title="Composição das Despesas",
                      plot_bgcolor=CORES["fundo"], paper_bgcolor=CORES["fundo"],
                      showlegend=False, margin=dict(t=50, b=20, l=10, r=10))
    return fig

def fig_acumulado():
    rec_acum = np.cumsum(rec_v)
    dep_acum = np.cumsum(dep_v + out_v)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=MESES_ABR, y=rec_acum, name='Receita Acumulada',
                             fill='tonexty', mode='lines+markers',
                             line=dict(color=CORES["receita"], width=2),
                             marker=dict(size=6)))
    fig.add_trace(go.Scatter(x=MESES_ABR, y=dep_acum, name='Despesa Acumulada',
                             fill='tozeroy', mode='lines+markers',
                             line=dict(color=CORES["despesa"], width=2),
                             marker=dict(size=6)))
    fig.update_layout(
        title=dict(text="Evolução Acumulada Anual", y=0.97, x=0.5, xanchor='center'),
        plot_bgcolor=CORES["fundo"], paper_bgcolor=CORES["fundo"],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis_tickprefix="R$", yaxis_tickformat=",.0f",
        margin=dict(t=70, b=20, l=10, r=10)
    )
    return fig

def fig_orca_receitas():
    df = df_orca[df_orca['RECDESP']==1].sort_values('REALIZADO')
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Orçado', y=df['NATUREZA'], x=df['ORÇADO'],
                         orientation='h', marker_color=CORES["primaria"], opacity=0.6))
    fig.add_trace(go.Bar(name='Realizado', y=df['NATUREZA'], x=df['REALIZADO'],
                         orientation='h', marker_color=CORES["receita"], opacity=0.9))
    fig.update_layout(title=dict(text="Receitas: Orçado vs Realizado", y=0.97, x=0.5, xanchor='center'),
                      barmode='group',
                      plot_bgcolor=CORES["fundo"], paper_bgcolor=CORES["fundo"],
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                      xaxis_tickprefix="R$", xaxis_tickformat=",.0f",
                      margin=dict(t=70, b=20, l=10, r=10))
    return fig

def fig_orca_despesas():
    df = df_orca[df_orca['RECDESP']==-1].sort_values('REALIZADO')
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Orçado', y=df['NATUREZA'], x=df['ORÇADO'],
                         orientation='h', marker_color=CORES["primaria"], opacity=0.6))
    fig.add_trace(go.Bar(name='Realizado', y=df['NATUREZA'], x=df['REALIZADO'],
                         orientation='h', marker_color=CORES["despesa"], opacity=0.9))
    fig.update_layout(title=dict(text="Despesas: Orçado vs Realizado", y=0.97, x=0.5, xanchor='center'),
                      barmode='group',
                      plot_bgcolor=CORES["fundo"], paper_bgcolor=CORES["fundo"],
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                      xaxis_tickprefix="R$", xaxis_tickformat=",.0f",
                      height=520, margin=dict(t=70, b=20, l=10, r=10))
    return fig

def fig_atingimento_receitas():
    df = df_orca[(df_orca['RECDESP']==1) & (df_orca['ORÇADO']>0)].sort_values('PERC_ATINGIMENTO')
    pcts = df['PERC_ATINGIMENTO'] * 100
    cores = [CORES["receita"] if p >= 100 else CORES["despesa"] for p in pcts]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=df['NATUREZA'], x=pcts, orientation='h',
                         marker_color=cores, opacity=0.85,
                         text=[f"{p:.0f}%" for p in pcts], textposition='outside'))
    fig.add_vline(x=100, line_dash="dash", line_color=CORES["primaria"],
                  annotation_text="Meta 100%", annotation_position="top right")
    fig.update_layout(title="% Atingimento – Receitas",
                      plot_bgcolor=CORES["fundo"], paper_bgcolor=CORES["fundo"],
                      xaxis_title="% Atingimento", showlegend=False,
                      margin=dict(t=50, b=20, l=10, r=50))
    return fig

def fig_atingimento_despesas():
    df = df_orca[(df_orca['RECDESP']==-1) & (df_orca['ORÇADO']>0)].sort_values('PERC_ATINGIMENTO')
    pcts = df['PERC_ATINGIMENTO'] * 100
    cores = [CORES["receita"] if p <= 100 else CORES["despesa"] for p in pcts]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=df['NATUREZA'], x=pcts, orientation='h',
                         marker_color=cores, opacity=0.85,
                         text=[f"{p:.0f}%" for p in pcts], textposition='outside'))
    fig.add_vline(x=100, line_dash="dash", line_color=CORES["primaria"],
                  annotation_text="Meta 100%", annotation_position="top right")
    fig.update_layout(title="% Atingimento – Despesas (≤100% = dentro do orçado)",
                      plot_bgcolor=CORES["fundo"], paper_bgcolor=CORES["fundo"],
                      xaxis_title="% Atingimento", showlegend=False,
                      height=520, margin=dict(t=50, b=20, l=10, r=50))
    return fig

def fig_receitas_stack():
    rec_nat = (df_base[df_base['CENTRORESULDADO']=='RECEITA']
               .groupby(['MES_N','NATUREZA'])['VALOR'].sum().reset_index())
    naturezas = rec_nat.groupby('NATUREZA')['VALOR'].sum().sort_values(ascending=False).index
    media_total = df_base[df_base['CENTRORESULDADO']=='RECEITA'].groupby('MES_N')['VALOR'].sum().mean()

    # Cores bem distintas para cada natureza
    PALETA_REC = ['#1B3A6B','#2ECC71','#F39C12','#9B59B6','#1ABC9C','#E67E22']
    fig = go.Figure()
    for i, nat in enumerate(naturezas):
        vals = []
        for m in range(1, 13):
            v = rec_nat[(rec_nat['MES_N']==m) & (rec_nat['NATUREZA']==nat)]['VALOR']
            vals.append(float(v.values[0]) if len(v) else 0)
        fig.add_trace(go.Bar(name=nat, x=MESES_ABR, y=vals,
                              marker_color=PALETA_REC[i % len(PALETA_REC)]))
    fig.add_hline(y=media_total, line_dash="dash", line_color=CORES["destaque"], line_width=2,
                  annotation_text=f"Média: {fmt_brl(media_total)}",
                  annotation_font_color=CORES["destaque"],
                  annotation_position="top right")
    fig.update_layout(
        title=dict(text="Receitas por Natureza (Mensal)", y=0.97, x=0.5, xanchor='center'),
        barmode='stack', plot_bgcolor=CORES["fundo"], paper_bgcolor=CORES["fundo"],
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5, font_size=10),
        yaxis_tickprefix="R$", yaxis_tickformat=",.0f",
        margin=dict(t=70, b=120, l=10, r=10)
    )
    return fig

def fig_desp_pessoal_stack():
    sal_nat = (df_base[df_base['CENTRORESULDADO']=='DESPESAS PESSOAL']
               .groupby(['MES_N','NATUREZA'])['VALOR'].sum().reset_index())
    naturezas = sal_nat.groupby('NATUREZA')['VALOR'].sum().sort_values(ascending=False).index
    media_pes = df_base[df_base['CENTRORESULDADO']=='DESPESAS PESSOAL'].groupby('MES_N')['VALOR'].sum().mean()
    fig = go.Figure()
    PALETA_PES = ['#1B3A6B','#3498DB','#5DADE2','#85C1E9','#2874A6','#1A5276','#AED6F1','#21618C']
    for i, nat in enumerate(naturezas):
        vals = []
        for m in range(1,13):
            v = sal_nat[(sal_nat['MES_N']==m) & (sal_nat['NATUREZA']==nat)]['VALOR']
            vals.append(float(v.values[0]) if len(v) else 0)
        fig.add_trace(go.Bar(name=nat, x=MESES_ABR, y=vals,
                              marker_color=PALETA_PES[i % len(PALETA_PES)],
                              marker_line_color='white', marker_line_width=0.8))
    fig.add_hline(y=media_pes, line_dash="dash", line_color=CORES["destaque"], line_width=2,
                  annotation_text=f"Média: {fmt_brl(media_pes)}",
                  annotation_font_color=CORES["destaque"],
                  annotation_position="top right")
    fig.update_layout(
        title=dict(text="Despesas de Pessoal por Natureza", y=0.97, x=0.5, xanchor='center'),
        barmode='stack', plot_bgcolor=CORES["fundo"], paper_bgcolor=CORES["fundo"],
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5, font_size=9),
        yaxis_tickprefix="R$", yaxis_tickformat=",.0f",
        margin=dict(t=70, b=120, l=10, r=10)
    )
    return fig

def fig_outras_despesas_stack():
    out_nat = (df_base[df_base['CENTRORESULDADO']=='OUTRAS DESPESAS']
               .groupby(['MES_N','NATUREZA'])['VALOR'].sum().reset_index())
    todas_nat = out_nat.groupby('NATUREZA')['VALOR'].sum().sort_values(ascending=False).index
    media_out = df_base[df_base['CENTRORESULDADO']=='OUTRAS DESPESAS'].groupby('MES_N')['VALOR'].sum().mean()
    fig = go.Figure()
    PALETA_OUT = ['#E74C3C','#C0392B','#E67E22','#D35400','#F39C12','#9B59B6','#6C3483','#CB4335',
                  '#A93226','#BA4A00','#7D6608','#4A235A']
    for i, nat in enumerate(todas_nat):
        vals = []
        for m in range(1,13):
            v = out_nat[(out_nat['MES_N']==m) & (out_nat['NATUREZA']==nat)]['VALOR']
            vals.append(float(v.values[0]) if len(v) else 0)
        fig.add_trace(go.Bar(name=nat[:25], x=MESES_ABR, y=vals,
                              marker_color=PALETA_OUT[i % len(PALETA_OUT)],
                              marker_line_color='white', marker_line_width=0.8))
    fig.add_hline(y=media_out, line_dash="dash", line_color=CORES["texto"], line_width=2,
                  annotation_text=f"Média: {fmt_brl(media_out)}",
                  annotation_font_color=CORES["texto"],
                  annotation_position="top right")
    fig.update_layout(
        title=dict(text="Outras Despesas por Natureza", y=0.97, x=0.5, xanchor='center'),
        barmode='stack', plot_bgcolor=CORES["fundo"], paper_bgcolor=CORES["fundo"],
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5, font_size=9),
        yaxis_tickprefix="R$", yaxis_tickformat=",.0f",
        margin=dict(t=70, b=120, l=10, r=10)
    )
    return fig

def tabela_top_despesas():
    # Agrupa despesas de pessoal em uma única linha "Pessoal"
    df_desp = df_base[df_base['RECDESP']==-1].copy()
    df_desp['NATUREZA_AGR'] = df_desp.apply(
        lambda r: 'Pessoal' if r['CENTRORESULDADO']=='DESPESAS PESSOAL' else r['NATUREZA'], axis=1)
    df_desp['CENTRO_AGR'] = df_desp.apply(
        lambda r: 'DESPESAS PESSOAL' if r['CENTRORESULDADO']=='DESPESAS PESSOAL' else r['CENTRORESULDADO'], axis=1)
    top = (df_desp.groupby(['CENTRO_AGR','NATUREZA_AGR'])['VALOR'].sum()
           .sort_values(ascending=False).reset_index())
    top.columns = ['CENTRORESULDADO','NATUREZA','VALOR']
    top['TOTAL'] = top['VALOR'].apply(fmt_brl)
    top.insert(0, 'POS', [f"{i+1}º" for i in range(len(top))])
    return dash_table.DataTable(
        columns=[
            {"name": "#",           "id": "POS"},
            {"name": "Centro",      "id": "CENTRORESULDADO"},
            {"name": "Natureza",    "id": "NATUREZA"},
            {"name": "Total Anual", "id": "TOTAL"},
        ],
        data=top[['POS','CENTRORESULDADO','NATUREZA','TOTAL']].to_dict('records'),
        style_header={
            'backgroundColor': CORES["primaria"], 'color': 'white',
            'fontWeight': 'bold', 'textAlign': 'center', 'fontSize': '12px'
        },
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#EAF0FB'},
            {'if': {'column_id': 'POS'}, 'fontWeight': 'bold', 'color': CORES["primaria"], 'textAlign': 'center'},
        ],
        style_cell={'padding': '8px 12px', 'fontSize': '12px', 'textAlign': 'left',
                    'border': '1px solid #ddd'},
        style_cell_conditional=[
            {'if': {'column_id': 'POS'},   'width': '40px'},
            {'if': {'column_id': 'TOTAL'}, 'textAlign': 'right'},
        ],
        style_table={'borderRadius': '8px', 'overflow': 'hidden'},
    )


# ════════════════════════════════════════════════════════════════════════════════
#  LAYOUT
# ════════════════════════════════════════════════════════════════════════════════
app = dash.Dash(__name__, title="Prestação de Contas IPO - 2025", suppress_callback_exceptions=True)

ESTILO_ABA = {
    "padding": "10px 22px",
    "fontWeight": "600",
    "fontSize": "13px",
    "cursor": "pointer",
    "border": "none",
    "borderBottom": f"3px solid transparent",
    "background": "none",
    "color": CORES["subtexto"],
}

ESTILO_SECAO = {
    "background": CORES["fundo"],
    "minHeight": "100vh",
    "fontFamily": "'Segoe UI', Arial, sans-serif",
    "color": CORES["texto"],
}

ESTILO_CONTEUDO = {"maxWidth": "1400px", "margin": "0 auto", "padding": "0 24px 40px"}

app.layout = html.Div(style=ESTILO_SECAO, children=[

    # Cabeçalho
    html.Div(style={
        "background": CORES["primaria"], "padding": "22px 32px",
        "display": "flex", "alignItems": "center", "justifyContent": "space-between"
    }, children=[
        html.Div([
            html.H1("⛪ Prestação de Contas IPO - 2025", style={
                "color": "white", "margin": "0", "fontSize": "22px", "fontWeight": "700"}),
            html.P("Dashboard Financeiro Anual", style={
                "color": "rgba(255,255,255,0.7)", "margin": "2px 0 0", "fontSize": "13px"}),
        ]),
        html.Div(style={"textAlign": "right"}, children=[
            html.P("Exercício Anual", style={"color": "white", "margin": "0", "fontWeight": "600"}),
            html.P("12 meses de dados", style={"color": "rgba(255,255,255,0.7)", "fontSize": "12px", "margin": "0"}),
        ])
    ]),

    # Abas de navegação
    dcc.Tabs(id='tabs', value='tab-1', children=[
        dcc.Tab(label='📊 Visão Geral', value='tab-1'),
        dcc.Tab(label='🎯 Orçado vs Realizado', value='tab-2'),
        dcc.Tab(label='📅 Detalhamento Mensal', value='tab-3'),
    ], style={"marginBottom": "0"},
       colors={"border": "#ddd", "primary": CORES["primaria"], "background": CORES["fundo"]}),

    html.Div(id='conteudo-tab'),
])


# ── Callback principal ────────────────────────────────────────────────────────
@app.callback(Output('conteudo-tab', 'children'), Input('tabs', 'value'))
def render_tab(tab):

    # ── ABA 1 – VISÃO GERAL ───────────────────────────────────────────────────
    if tab == 'tab-1':
        cor_saldo = CORES["receita"] if saldo_total >= 0 else CORES["despesa"]
        return html.Div(style=ESTILO_CONTEUDO, children=[
            html.Br(),
            html.Div(style={"display": "flex", "gap": "16px", "flexWrap": "wrap"}, children=[
                make_card("TOTAL RECEITAS",  fmt_brl(total_receita),  "12 meses",             CORES["receita"]),
                make_card("TOTAL DESPESAS",  fmt_brl(total_despesas), "12 meses",             CORES["despesa"]),
                make_card("SALDO DO ANO",    fmt_brl(saldo_total),    "Receita − Despesa",    cor_saldo),
                make_card("COMPROMETIMENTO", f"{pct_exec:.1f}%",      "Despesa / Receita",    CORES["destaque"]),
            ]),
            html.Br(),
            html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px"}, children=[
                dcc.Graph(figure=fig_receita_despesa()),
                dcc.Graph(figure=fig_saldo_mensal()),
                dcc.Graph(figure=fig_pizza_receita()),
                dcc.Graph(figure=fig_pizza_despesa()),
            ]),
            html.Br(),
            dcc.Graph(figure=fig_acumulado()),
        ])

    # ── ABA 2 – ORÇADO vs REALIZADO ───────────────────────────────────────────
    elif tab == 'tab-2':
        cor_rec = CORES["receita"] if pct_rec >= 100 else CORES["despesa"]
        cor_dep = CORES["receita"] if pct_dep <= 100 else CORES["despesa"]
        return html.Div(style=ESTILO_CONTEUDO, children=[
            html.Br(),
            html.Div(style={"display": "flex", "gap": "16px", "flexWrap": "wrap"}, children=[
                make_card("RECEITA ORÇADA",    fmt_brl(rec_orca), "",                        CORES["primaria"]),
                make_card("RECEITA REALIZADA", fmt_brl(rec_real), f"{pct_rec:.1f}% do orçado", cor_rec),
                make_card("DESPESA ORÇADA",    fmt_brl(dep_orca), "",                        CORES["primaria"]),
                make_card("DESPESA REALIZADA", fmt_brl(dep_real), f"{pct_dep:.1f}% do orçado", cor_dep),
            ]),
            html.Br(),
            html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px"}, children=[
                dcc.Graph(figure=fig_orca_receitas()),
                dcc.Graph(figure=fig_atingimento_receitas()),
            ]),
            html.Br(),
            html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px"}, children=[
                dcc.Graph(figure=fig_orca_despesas()),
                dcc.Graph(figure=fig_atingimento_despesas()),
            ]),
        ])

    # ── ABA 3 – DETALHAMENTO MENSAL ───────────────────────────────────────────
    elif tab == 'tab-3':
        return html.Div(style=ESTILO_CONTEUDO, children=[
            html.Br(),
            html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px"}, children=[
                dcc.Graph(figure=fig_receitas_stack()),
                dcc.Graph(figure=fig_desp_pessoal_stack()),
                dcc.Graph(figure=fig_outras_despesas_stack()),
                html.Div([
                    html.H3("🏆 Ranking Despesas",
                            style={"color": CORES["primaria"], "marginBottom": "12px", "fontSize": "15px"}),
                    tabela_top_despesas()
                ], style={"background": CORES["card"], "borderRadius": "12px",
                           "padding": "20px", "boxShadow": "0 2px 10px rgba(0,0,0,0.07)"}),
            ]),
        ])


# ── Inicialização ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    if not os.path.exists(ARQUIVO_EXCEL):
        print(f"\n⚠️  Arquivo '{ARQUIVO_EXCEL}' não encontrado na pasta atual.")
        print("   Coloque o arquivo Excel na mesma pasta deste script e tente novamente.\n")
    else:
        print("\n✅ Dashboard iniciado! Acesse: http://localhost:8050\n")
        app.run(debug=False, host='0.0.0.0', port=8050)

server = app.server