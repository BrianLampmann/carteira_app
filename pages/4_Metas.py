import streamlit as st
import pandas as pd
from datetime import date
from export import dataframes_to_excel_bytes
import db
from api import get_prices
from auth import login_gate, sidebar_user_box
from nav import render_sidebar_nav
from style import apply_style

st.set_page_config(page_title="Metas", page_icon="", layout="wide")
apply_style()
db.init_db()
user_email = login_gate()
render_sidebar_nav(user_email)
sidebar_user_box()

st.title("Metas")
col_titulo, col_download = st.columns([5, 1])
with col_download:
    excel_bytes = dataframes_to_excel_bytes({
        "Metas": pd.DataFrame([db.get_metas(user_email)]),
    })
    st.download_button(
        "Baixar (Excel)", data=excel_bytes,
        file_name="metas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
# ---------- Dados atuais da carteira ----------
ativos = db.get_ativos(user_email)
renda_fixa = db.get_renda_fixa(user_email)
tickers = [a["ticker"] for a in ativos]
precos = get_prices(tickers) if tickers else {}

total_acoes, total_fiis, soma_yoc, n_yoc = 0.0, 0.0, 0.0, 0
for a in ativos:
    preco_atual = precos.get(a["ticker"]) or a["preco_medio"]
    valor_atual = a["quantidade"] * preco_atual
    if a["tipo"] == "Ação":
        total_acoes += valor_atual
    else:
        total_fiis += valor_atual
    if a["dividendo_anual"] and a["preco_medio"]:
        soma_yoc += (a["dividendo_anual"] / a["preco_medio"]) * 100
        n_yoc += 1

total_rf = sum(r["valor_investido"] for r in renda_fixa) if renda_fixa else 0
total_acoes_fiis = total_acoes + total_fiis
total_geral = total_acoes_fiis + total_rf
media_yoc = (soma_yoc / n_yoc) if n_yoc else 0

# ---------- Totais ----------
st.subheader("Totais atuais")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Ações", f"R$ {total_acoes:,.2f}")
c2.metric("Total Ações + FIIs", f"R$ {total_acoes_fiis:,.2f}")
c3.metric("Total Renda Fixa / Fundo", f"R$ {total_rf:,.2f}")
c4.metric("Total geral", f"R$ {total_geral:,.2f}")

st.divider()

# ---------- Formulário de metas ----------
metas = db.get_metas(user_email)
st.subheader("Configurar metas")

with st.form("form_metas"):
    c1, c2, c3 = st.columns(3)
    ano_meta = c1.number_input("Ano da meta", min_value=date.today().year, max_value=date.today().year + 10,
                                value=int(metas["ano_meta"]) if metas["ano_meta"] >= date.today().year else date.today().year)
    meta_acoes_fiis = c2.number_input("Meta Ações/FIIs para o ano (R$)", min_value=0.0, format="%.2f", value=float(metas["meta_acoes_fiis"]))
    meta_fundo = c3.number_input("Meta Renda Fixa/Fundo para o ano (R$)", min_value=0.0, format="%.2f", value=float(metas["meta_fundo"]))

    c4, c5, c6 = st.columns(3)
    custo_estimado_mensal = c4.number_input("Custo estimado mensal (R$)", min_value=0.0, format="%.2f", value=float(metas["custo_estimado_mensal"]))
    reserva_meses = c5.number_input("Reserva de emergência (meses)", min_value=0, step=1, value=int(metas["reserva_meses"]))
    valor_na_reserva = c6.number_input("Valor atual guardado na reserva (R$)", min_value=0.0, format="%.2f", value=float(metas["valor_na_reserva"]))

    c7, c8 = st.columns(2)
    meta_desejada = c7.number_input("Meta desejada (R$)", min_value=0.0, format="%.2f", value=float(metas["meta_desejada"]))
    meta_master = c8.number_input("Meta master (R$)", min_value=0.0, format="%.2f", value=float(metas["meta_master"]))

    salvar = st.form_submit_button("Salvar metas", type="primary")
    if salvar:
        db.save_metas(user_email, meta_acoes_fiis, meta_fundo, int(ano_meta), custo_estimado_mensal,
                       int(reserva_meses), valor_na_reserva, meta_desejada, meta_master)
        st.success("Metas salvas!")
        st.rerun()

metas = db.get_metas(user_email)
st.divider()

# ---------- Progresso da meta do ano ----------
st.subheader(f"Progresso da meta {metas['ano_meta']}")

hoje = date.today()
if hoje.year < metas["ano_meta"]:
    meses_restantes = (metas["ano_meta"] - hoje.year) * 12 + (12 - hoje.month + 1)
elif hoje.year == metas["ano_meta"]:
    meses_restantes = max(12 - hoje.month + 1, 1)
else:
    meses_restantes = 1

def bloco_meta(nome, atual, meta_valor, meses):
    falta_r = max(meta_valor - atual, 0)
    falta_pct = (falta_r / meta_valor * 100) if meta_valor else 0
    ideia_mes = falta_r / meses if meses else 0
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(f"Meta {nome}", f"R$ {meta_valor:,.2f}")
    col2.metric("Falta %", f"{falta_pct:.2f}%")
    col3.metric("Falta R$", f"R$ {falta_r:,.2f}")
    col4.metric("Ideia por mês", f"R$ {ideia_mes:,.2f}")

bloco_meta("Ações/FIIs", total_acoes_fiis, metas["meta_acoes_fiis"], meses_restantes)
bloco_meta("Renda Fixa/Fundo", total_rf, metas["meta_fundo"], meses_restantes)

st.caption(f"Considerando {meses_restantes} mês(es) restante(s) até o fim de {metas['ano_meta']}. Média YoC atual da carteira: {media_yoc:.2f}%")

st.divider()

# ---------- Reserva de emergência ----------
st.subheader("Reserva de emergência")
valor_minimo_reserva = metas["custo_estimado_mensal"] * metas["reserva_meses"]
resultado_reserva = metas["valor_na_reserva"] - valor_minimo_reserva

c1, c2, c3, c4 = st.columns(4)
c1.metric("Custo estimado mensal", f"R$ {metas['custo_estimado_mensal']:,.2f}")
c2.metric("Valor mínimo na reserva", f"R$ {valor_minimo_reserva:,.2f}")
c3.metric("Valor atual na reserva", f"R$ {metas['valor_na_reserva']:,.2f}")
c4.metric("Resultado", f"R$ {resultado_reserva:,.2f}", delta=("Completa" if resultado_reserva >= 0 else "Faltando"))

st.divider()

# ---------- Metas desejada e master ----------
st.subheader("Metas de longo prazo")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Meta desejada**")
    pct = (total_geral / metas["meta_desejada"] * 100) if metas["meta_desejada"] else 0
    st.metric("Quão perto", f"{pct:.2f}%")
    st.progress(min(pct / 100, 1.0))
    st.caption(f"Falta: {max(100 - pct, 0):.2f}% (R$ {max(metas['meta_desejada'] - total_geral, 0):,.2f})")

with col2:
    st.markdown("**Meta master**")
    pct_m = (total_geral / metas["meta_master"] * 100) if metas["meta_master"] else 0
    st.metric("Quão perto", f"{pct_m:.2f}%")
    st.progress(min(pct_m / 100, 1.0))
    st.caption(f"Falta: {max(100 - pct_m, 0):.2f}% (R$ {max(metas['meta_master'] - total_geral, 0):,.2f})")

st.divider()

# ---------- Soma de rendimentos por ano ----------
st.subheader("Soma de rendimentos por ano")
proventos = db.get_proventos(user_email)
if proventos:
    df = pd.DataFrame(proventos)
    df["data"] = pd.to_datetime(df["data"])
    df["ano"] = df["data"].dt.year
    df["grupo"] = df["categoria"].apply(lambda c: "Ações" if c == "Dividendo/JCP" else "Renda Fixa")

    for ano in sorted(df["ano"].unique(), reverse=True):
        df_ano = df[df["ano"] == ano]
        soma_acoes = df_ano.loc[df_ano["grupo"] == "Ações", "valor"].sum()
        soma_rf = df_ano.loc[df_ano["grupo"] == "Renda Fixa", "valor"].sum()
        meses_com_dados = df_ano["data"].dt.month.nunique() or 1

        with st.expander(f"{ano} - Total: R$ {(soma_acoes + soma_rf):,.2f}", expanded=(ano == hoje.year)):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Ações", f"R$ {soma_acoes:,.2f}")
            c2.metric("Renda Fixa", f"R$ {soma_rf:,.2f}")
            c3.metric("Total", f"R$ {(soma_acoes + soma_rf):,.2f}")
            c4.metric("Média mensal", f"R$ {((soma_acoes + soma_rf) / meses_com_dados):,.2f}")
else:
    st.info("Lance seus proventos na tela 'Crescimento e Aportes' para ver o resumo por ano.")