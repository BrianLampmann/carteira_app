import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

import db
from api import get_prices, get_variacoes_diarias
from auth import login_gate, sidebar_user_box
from nav import render_sidebar_nav
from style import apply_style

st.set_page_config(page_title="Painel Geral", page_icon="", layout="wide")
apply_style()
db.init_db()
user_email = login_gate()
render_sidebar_nav(user_email)
sidebar_user_box()

st.title("Painel Geral")
st.caption(f"Bem-vindo(a), {user_email}")

# ---------- Dados base ----------
ativos = db.get_ativos(user_email)
renda_fixa = db.get_renda_fixa(user_email)
metas = db.get_metas(user_email)
historico = db.get_patrimonio_historico(user_email)
proventos = db.get_proventos(user_email)

tickers = [a["ticker"] for a in ativos]
precos = get_prices(tickers) if tickers else {}

total_acoes = 0.0
total_fiis = 0.0
for a in ativos:
    preco_atual = precos.get(a["ticker"].upper()) or a["preco_medio"]
    valor_atual = a["quantidade"] * preco_atual
    if a["tipo"] == "Ação":
        total_acoes += valor_atual
    else:
        total_fiis += valor_atual

total_rf = sum(r["valor_investido"] for r in renda_fixa)
total_geral = total_acoes + total_fiis + total_rf

# ---------- Alertas configurados na tela "Alertas" ----------
from alerts import calcular_alertas_disparados, TIPOS_LABEL


@st.dialog("Alertas")
def mostrar_popup_alertas(disparados):
    st.write("As seguintes condições que você configurou foram atingidas:")
    for al in disparados:
        rotulo = TIPOS_LABEL.get(al["tipo"], al["tipo"])
        escopo = al["ticker"] or "Carteira toda"
        if al["tipo"] in ("variacao_pct_dia", "yoc_minimo", "concentracao_maxima"):
            st.warning(f"{rotulo} ({escopo}): valor atual {al['valor_atual']:.2f}% - limite configurado: {al['limite']:.2f}%")
        else:
            st.warning(f"{rotulo} ({escopo}): valor atual R$ {al['valor_atual']:.2f} - limite configurado: R$ {al['limite']:.2f}")
    st.caption("Gerencie ou desative esses alertas na tela 'Alertas'.")
    if st.button("Fechar", use_container_width=True):
        st.rerun()


if not st.session_state.get("alertas_ja_verificados"):
    st.session_state["alertas_ja_verificados"] = True

    alertas_config = db.get_alertas(user_email)
    tickers_para_variacao = [a["ticker"] for a in ativos]
    variacoes = get_variacoes_diarias(tickers_para_variacao) if tickers_para_variacao else {}

    disparados = calcular_alertas_disparados(alertas_config, ativos, precos, variacoes, total_geral)

    if disparados:
        for al in disparados:
            db.add_alerta_historico(user_email, al["tipo"], al["ticker"], al["valor_atual"], al["limite"])
        mostrar_popup_alertas(disparados)



# ---------- Cartões principais ----------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Patrimônio total", f"R$ {total_geral:,.2f}")
col2.metric("Ações", f"R$ {total_acoes:,.2f}")
col3.metric("FIIs", f"R$ {total_fiis:,.2f}")
col4.metric("Renda Fixa", f"R$ {total_rf:,.2f}")

st.divider()

# ---------- Evolução patrimonial + meta ----------
col_a, col_b = st.columns([2, 1])

with col_a:
    st.subheader("Evolução patrimonial")
    if historico:
        df_hist = pd.DataFrame(historico)
        df_hist["data"] = pd.to_datetime(df_hist["data"])
        df_hist = df_hist.sort_values("data").tail(12)
        fig = px.line(df_hist, x="data", y="valor_total", markers=True)
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True, key="home_patrimonio")
    else:
        st.caption("Sem lançamentos de patrimônio ainda. Lance em Crescimento e Aportes.")

with col_b:
    st.subheader("Meta desejada")
    meta_desejada = metas.get("meta_desejada") or 0
    if meta_desejada:
        pct = min(total_geral / meta_desejada * 100, 100)
        st.metric("Progresso", f"{pct:.1f}%")
        st.progress(pct / 100)
        st.caption(f"Faltam R$ {max(meta_desejada - total_geral, 0):,.2f}")
    else:
        st.caption("Configure sua meta na tela Metas.")

st.divider()

# ---------- Dividendos ----------
st.subheader("Dividendos recebidos")
if proventos:
    df_prov = pd.DataFrame(proventos)
    df_prov["data"] = pd.to_datetime(df_prov["data"])
    hoje = date.today()
    do_ano = df_prov[df_prov["data"].dt.year == hoje.year]
    do_mes = do_ano[do_ano["data"].dt.month == hoje.month]

    col_x, col_y, col_z = st.columns(3)
    col_x.metric("Este mês", f"R$ {do_mes['valor'].sum():,.2f}")
    col_y.metric("Este ano", f"R$ {do_ano['valor'].sum():,.2f}")
    col_z.metric("Total histórico", f"R$ {df_prov['valor'].sum():,.2f}")
else:
    st.caption("Nenhum provento lançado ainda. Lance em Crescimento e Aportes.")

st.divider()

# ---------- Navegação ----------
st.subheader("Navegação rápida")
st.markdown(
    """
- **Carteira Principal** — cadastro de ativos e renda fixa, com todos os cálculos.
- **Exposição da Carteira** — gráficos de exposição e diversificação.
- **Crescimento e Aportes** — evolução patrimonial e proventos recebidos.
- **Metas** — metas de patrimônio, reserva de emergência e progresso do ano.
- **Contabilidade Mensal** — receitas e despesas mês a mês.
- **Notícias e Fatos Relevantes** — últimas notícias dos seus ativos.
"""
)