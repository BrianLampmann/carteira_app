import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

import db
from auth import login_gate, sidebar_user_box
from style import apply_style

st.set_page_config(page_title="Crescimento e Aportes", page_icon="📈", layout="wide")
apply_style()
db.init_db()
user_email = login_gate()
sidebar_user_box()

st.title("📈 Crescimento e Aportes")

tab_patrimonio, tab_proventos = st.tabs(["Evolução Patrimonial", "Proventos Recebidos"])

# =========================================================
# EVOLUÇÃO PATRIMONIAL
# =========================================================
with tab_patrimonio:
    st.subheader("Lançar evolução patrimonial")

    with st.form("form_patrimonio", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        data_lanc = c1.date_input("Data", value=date.today())
        valor_total = c2.number_input("Valor total do patrimônio (R$)", min_value=0.0, format="%.2f")
        aporte = c3.number_input("Aporte no período (R$)", min_value=0.0, format="%.2f")
        enviar = st.form_submit_button("➕ Adicionar lançamento", type="primary")
        if enviar:
            db.add_patrimonio(user_email, str(data_lanc), valor_total, aporte)
            st.success("Lançamento adicionado!")
            st.rerun()

    historico = db.get_patrimonio_historico(user_email)
    if historico:
        df_hist = pd.DataFrame(historico)
        df_hist["data"] = pd.to_datetime(df_hist["data"])
        df_hist = df_hist.sort_values("data")

        fig = px.line(df_hist, x="data", y="valor_total", markers=True, title="Evolução do patrimônio")
        st.plotly_chart(fig, use_container_width=True, key="linha_patrimonio")

        df_hist["ano"] = df_hist["data"].dt.year
        df_aporte_ano = df_hist.groupby("ano", as_index=False)["aporte"].sum()
        fig2 = px.bar(df_aporte_ano, x="ano", y="aporte", title="Soma dos aportes por ano", text_auto=".2s")
        st.plotly_chart(fig2, use_container_width=True, key="bar_aportes")

        st.subheader("Histórico lançado")
        for row in historico:
            c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
            c1.write(row["data"])
            c2.write(f"R$ {row['valor_total']:,.2f}")
            c3.write(f"Aporte: R$ {row['aporte']:,.2f}")
            if c4.button("🗑️", key=f"del_pat_{row['id']}"):
                db.delete_patrimonio(user_email, row["id"])
                st.rerun()
    else:
        st.info("Nenhum lançamento de patrimônio ainda. Use o formulário acima.")

# =========================================================
# PROVENTOS
# =========================================================
with tab_proventos:
    st.subheader("Lançar provento recebido")

    with st.form("form_provento", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        origem = c1.text_input("Origem (ticker ou nome)")
        categoria = c2.selectbox("Categoria", ["Dividendo/JCP", "Renda Fixa", "CDI", "FGTS"])
        valor = c3.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        data_prov = c4.date_input("Data", value=date.today(), key="data_provento")
        enviar_p = st.form_submit_button("➕ Adicionar provento", type="primary")
        if enviar_p:
            if origem.strip():
                db.add_provento(user_email, origem.strip(), categoria, valor, str(data_prov))
                st.success("Provento adicionado!")
                st.rerun()
            else:
                st.warning("Informe a origem do provento.")

    proventos = db.get_proventos(user_email)
    if proventos:
        df_prov = pd.DataFrame(proventos)
        df_prov["data"] = pd.to_datetime(df_prov["data"])

        resumo = df_prov.groupby("categoria", as_index=False)["valor"].sum()
        cols = st.columns(len(resumo)) if len(resumo) > 0 else []
        for i, r in resumo.iterrows():
            cols[i].metric(r["categoria"], f"R$ {r['valor']:,.2f}")

        df_mes = df_prov.copy()
        df_mes["mes"] = df_mes["data"].dt.to_period("M").astype(str)
        df_mes_agg = df_mes.groupby(["mes", "categoria"], as_index=False)["valor"].sum()
        fig = px.bar(df_mes_agg, x="mes", y="valor", color="categoria", title="Proventos por mês e categoria", barmode="stack")
        st.plotly_chart(fig, use_container_width=True, key="bar_proventos_mes")

        st.divider()
        st.subheader("Evolução de dividendos e YoC realizado")

        df_dividendos = df_prov[df_prov["categoria"] == "Dividendo/JCP"].copy()
        if not df_dividendos.empty:
            df_dividendos["mes"] = df_dividendos["data"].dt.to_period("M").dt.to_timestamp()
            df_div_mes = df_dividendos.groupby("mes", as_index=False)["valor"].sum().sort_values("mes")
            df_div_mes["acumulado"] = df_div_mes["valor"].cumsum()

            col_a, col_b = st.columns(2)
            with col_a:
                fig_mensal = px.line(df_div_mes, x="mes", y="valor", markers=True,
                                      title="Dividendos recebidos por mês (Ações/FIIs)")
                st.plotly_chart(fig_mensal, use_container_width=True, key="linha_dividendos_mensal")
            with col_b:
                fig_acum = px.area(df_div_mes, x="mes", y="acumulado",
                                    title="Dividendos acumulados ao longo do tempo")
                st.plotly_chart(fig_acum, use_container_width=True, key="area_dividendos_acumulado")

            # YoC realizado: dividendo do mês / total investido hoje em Ações+FIIs
            ativos_atuais = db.get_ativos(user_email)
            total_investido = sum(a["quantidade"] * a["preco_medio"] for a in ativos_atuais)
            if total_investido:
                df_div_mes["yoc_mensal_pct"] = df_div_mes["valor"] / total_investido * 100
                df_div_mes["yoc_media_12m_pct"] = df_div_mes["yoc_mensal_pct"].rolling(12, min_periods=1).mean()

                fig_yoc = px.line(
                    df_div_mes, x="mes", y=["yoc_mensal_pct", "yoc_media_12m_pct"],
                    markers=True, title="YoC mensal realizado (%) — dividendo do mês ÷ valor investido hoje",
                    labels={"value": "YoC (%)", "mes": "Mês", "variable": "Série"},
                )
                fig_yoc.for_each_trace(lambda t: t.update(
                    name={"yoc_mensal_pct": "YoC do mês", "yoc_media_12m_pct": "Média móvel 12m"}.get(t.name, t.name)
                ))
                st.plotly_chart(fig_yoc, use_container_width=True, key="linha_yoc_realizado")
                st.caption(
                    "O YoC realizado usa o valor investido **atual** em Ações/FIIs como base fixa "
                    "(não o valor investido em cada mês histórico), então serve para ver a tendência "
                    "de quanto sua carteira de hoje já teria rendido em dividendos mês a mês."
                )
            else:
                st.info("Cadastre ativos na Carteira Principal para calcular o YoC realizado.")
        else:
            st.info("Lance proventos com categoria 'Dividendo/JCP' para ver a evolução de dividendos e YoC.")

        st.subheader("Lançamentos")
        for row in proventos:
            c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1])
            c1.write(row["origem"])
            c2.write(row["categoria"])
            c3.write(f"R$ {row['valor']:,.2f}")
            c4.write(row["data"])
            if c5.button("🗑️", key=f"del_prov_{row['id']}"):
                db.delete_provento(user_email, row["id"])
                st.rerun()
    else:
        st.info("Nenhum provento lançado ainda. Use o formulário acima.")