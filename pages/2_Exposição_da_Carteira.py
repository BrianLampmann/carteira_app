import streamlit as st
import pandas as pd
import plotly.express as px

import db
from api import get_prices
from auth import login_gate, sidebar_user_box
from style import apply_style

st.set_page_config(page_title="Exposição da Carteira", page_icon="", layout="wide")
apply_style()
db.init_db()
user_email = login_gate()
sidebar_user_box()

st.title("Exposição da Carteira")

ativos = db.get_ativos(user_email)
renda_fixa = db.get_renda_fixa(user_email)

if not ativos and not renda_fixa:
    st.info("Cadastre ativos e/ou renda fixa na tela 'Carteira Principal' para ver os gráficos.")
    st.stop()

tickers = [a["ticker"] for a in ativos]
precos = get_prices(tickers) if tickers else {}

linhas = []
for a in ativos:
    preco_atual = precos.get(a["ticker"]) or a["preco_medio"]
    valor_atual = a["quantidade"] * preco_atual
    linhas.append({"Ativo": a["ticker"], "Tipo": a["tipo"], "Setor": a["setor"] or "Não informado", "Valor": valor_atual})

df_ativos = pd.DataFrame(linhas)
total_acoes = df_ativos.loc[df_ativos["Tipo"] == "Ação", "Valor"].sum() if not df_ativos.empty else 0
total_fiis = df_ativos.loc[df_ativos["Tipo"] == "FII", "Valor"].sum() if not df_ativos.empty else 0
total_rf = sum(r["valor_investido"] for r in renda_fixa) if renda_fixa else 0
total_geral = total_acoes + total_fiis + total_rf

c1, c2, c3, c4 = st.columns(4)
c1.metric("Ações", f"R$ {total_acoes:,.2f}")
c2.metric("FIIs", f"R$ {total_fiis:,.2f}")
c3.metric("Renda Fixa", f"R$ {total_rf:,.2f}")
c4.metric("Patrimônio total", f"R$ {total_geral:,.2f}")

st.divider()

# ---------- 1. Pizza + barra: Ações x FIIs x Renda Fixa ----------
col1, col2 = st.columns(2)
df_macro = pd.DataFrame({"Categoria": ["Ações", "FIIs", "Renda Fixa"], "Valor": [total_acoes, total_fiis, total_rf]})
df_macro = df_macro[df_macro["Valor"] > 0]

with col1:
    st.subheader("Ações x FIIs x Renda Fixa")
    if not df_macro.empty:
        fig = px.pie(df_macro, names="Categoria", values="Valor", hole=0.4)
        st.plotly_chart(fig, use_container_width=True, key="pie_macro")

with col2:
    st.subheader("Ações x FIIs x Renda Fixa (barras)")
    if not df_macro.empty:
        fig = px.bar(df_macro, x="Categoria", y="Valor", color="Categoria", text_auto=".2s")
        st.plotly_chart(fig, use_container_width=True, key="bar_macro")

st.divider()

# ---------- 2. Exposição individual por ativo (barra horizontal) ----------
st.subheader("Exposição de cada ativo (Ações e FIIs)")
if not df_ativos.empty:
    df_ativos_sorted = df_ativos.sort_values("Valor", ascending=True)
    fig = px.bar(df_ativos_sorted, x="Valor", y="Ativo", color="Tipo", orientation="h", text_auto=".2s")
    st.plotly_chart(fig, use_container_width=True, key="bar_ativos")
else:
    st.caption("Nenhum ativo cadastrado ainda.")

st.divider()

# ---------- 3. Pizza: exposição de cada ativo + FIIs x Ações ----------
col3, col4 = st.columns(2)
with col3:
    st.subheader("Exposição de cada ativo (pizza)")
    if not df_ativos.empty:
        fig = px.pie(df_ativos, names="Ativo", values="Valor", hole=0.3)
        st.plotly_chart(fig, use_container_width=True, key="pie_ativos")

with col4:
    st.subheader("FIIs x Ações")
    df_af = pd.DataFrame({"Categoria": ["Ações", "FIIs"], "Valor": [total_acoes, total_fiis]})
    df_af = df_af[df_af["Valor"] > 0]
    if not df_af.empty:
        fig = px.pie(df_af, names="Categoria", values="Valor", hole=0.4)
        st.plotly_chart(fig, use_container_width=True, key="pie_acoes_fiis")

st.divider()

# ---------- 4. Pizza: Renda Fixa x (Ações+FIIs) + Setor ----------
col5, col6 = st.columns(2)
with col5:
    st.subheader("Renda Fixa x Variável (Ações + FIIs)")
    df_rf_vs = pd.DataFrame({"Categoria": ["Renda Fixa", "Ações + FIIs"], "Valor": [total_rf, total_acoes + total_fiis]})
    df_rf_vs = df_rf_vs[df_rf_vs["Valor"] > 0]
    if not df_rf_vs.empty:
        fig = px.pie(df_rf_vs, names="Categoria", values="Valor", hole=0.4)
        st.plotly_chart(fig, use_container_width=True, key="pie_rf_vs")

with col6:
    st.subheader("Diversificação por setor")
    if not df_ativos.empty:
        df_setor = df_ativos.groupby("Setor", as_index=False)["Valor"].sum()
        fig = px.pie(df_setor, names="Setor", values="Valor", hole=0.3)
        st.plotly_chart(fig, use_container_width=True, key="pie_setor")
    else:
        st.caption("Cadastre o setor dos ativos para ver esse gráfico.")