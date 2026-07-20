import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from export import dataframes_to_excel_bytes

import db
from auth import login_gate, sidebar_user_box
from nav import render_sidebar_nav
from style import apply_style

st.set_page_config(page_title="Contabilidade Mensal", page_icon="", layout="wide")
apply_style()
db.init_db()
user_email = login_gate()
render_sidebar_nav(user_email)
sidebar_user_box()

st.title("Contabilidade Mensal")
col_titulo, col_download = st.columns([5, 1])
with col_download:
    excel_bytes = dataframes_to_excel_bytes({
        "Categorias Receita": pd.DataFrame(db.get_categorias(user_email, "Receita")),
        "Categorias Despesa": pd.DataFrame(db.get_categorias(user_email, "Despesa")),
        "Lancamentos": pd.DataFrame(db.get_todos_lancamentos(user_email)),
    })
    st.download_button(
        "Baixar (Excel)", data=excel_bytes,
        file_name="contabilidade_mensal.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def editor_categorias(tipo, texto_especial, ajuda_especial):
    st.markdown(f"**Categorias de {tipo}**")
    cats = db.get_categorias(user_email, tipo)
    df = pd.DataFrame(cats) if cats else pd.DataFrame(columns=["nome", "especial"])
    if not df.empty:
        df = df[["nome", "especial"]]
        df["especial"] = df["especial"].astype(bool)

    edited = st.data_editor(
        df, num_rows="dynamic", use_container_width=True, hide_index=True,
        column_config={
            "nome": st.column_config.TextColumn("Categoria", required=True),
            "especial": st.column_config.CheckboxColumn(texto_especial, help=ajuda_especial, default=False),
        },
        key=f"editor_cat_{tipo}",
    )
    if st.button(f"Salvar categorias de {tipo}", key=f"btn_cat_{tipo}"):
        lista = []
        for _, row in edited.iterrows():
            nome = str(row.get("nome") or "").strip()
            if nome:
                lista.append({"nome": nome, "especial": bool(row.get("especial"))})
        db.replace_categorias(user_email, tipo, lista)
        st.success("Categorias salvas!")
        st.rerun()


with st.expander("Gerenciar categorias", expanded=False):
    col_a, col_b = st.columns(2)
    with col_a:
        editor_categorias(
            "Receita", "É saque/transferência?",
            "Marque itens como 'Saque P/ Conta' — eles são excluídos do cálculo de 'Sobras sem saques'."
        )
    with col_b:
        editor_categorias(
            "Despesa", "É investimento?",
            "Marque itens como 'Investimentos' (aportes) — eles são excluídos da despesa líquida usada no cálculo de sobras."
        )

st.divider()

anos_existentes = db.get_anos_contab(user_email)
ano_atual = date.today().year
opcoes_ano = sorted(set(anos_existentes) | {ano_atual})
ano = st.selectbox("Ano", opcoes_ano, index=opcoes_ano.index(ano_atual) if ano_atual in opcoes_ano else 0)

col_novo1, col_novo2 = st.columns([1, 4])
with col_novo1:
    novo_ano = st.number_input("Adicionar novo ano", min_value=2000, max_value=2100, value=ano_atual + 1, step=1, label_visibility="collapsed")
with col_novo2:
    if st.button("Adicionar ano"):
        db.save_lancamentos_ano(user_email, "Receita", int(novo_ano), {})
        st.rerun()

st.divider()


def grid_lancamentos(tipo, ano):
    cats = db.get_categorias(user_email, tipo)
    if not cats:
        st.info(f"Cadastre categorias de {tipo} em 'Gerenciar categorias' acima.")
        return None

    dados_salvos = db.get_lancamentos_ano(user_email, tipo, ano)
    linhas = []
    for c in cats:
        linha = {"Categoria": c["nome"]}
        valores_mes = dados_salvos.get(c["nome"], {})
        for i, m in enumerate(MESES, start=1):
            linha[m] = valores_mes.get(i, 0.0)
        linhas.append(linha)
    df = pd.DataFrame(linhas)

    col_config = {"Categoria": st.column_config.TextColumn("Categoria", disabled=True)}
    for m in MESES:
        col_config[m] = st.column_config.NumberColumn(m, format="R$ %.2f", min_value=0.0)

    edited = st.data_editor(
        df, use_container_width=True, hide_index=True, column_config=col_config,
        key=f"grid_{tipo}_{ano}",
    )

    if st.button(f"Salvar {tipo.lower()}s de {ano}", key=f"btn_grid_{tipo}_{ano}"):
        dados = {}
        for _, row in edited.iterrows():
            dados[row["Categoria"]] = {i: float(row[m] or 0) for i, m in enumerate(MESES, start=1)}
        db.save_lancamentos_ano(user_email, tipo, ano, dados)
        st.success("Lançamentos salvos!")
        st.rerun()

    return edited


tab_receitas, tab_despesas, tab_resumo = st.tabs(["Receitas", "Despesas", "Resumo do Mês"])

with tab_receitas:
    df_receitas = grid_lancamentos("Receita", ano)

with tab_despesas:
    df_despesas = grid_lancamentos("Despesa", ano)

with tab_resumo:
    cats_receita = db.get_categorias(user_email, "Receita")
    cats_despesa = db.get_categorias(user_email, "Despesa")

    if not cats_receita or not cats_despesa:
        st.info("Cadastre categorias de Receita e Despesa para ver o resumo.")
    else:
        dados_receita = db.get_lancamentos_ano(user_email, "Receita", ano)
        dados_despesa = db.get_lancamentos_ano(user_email, "Despesa", ano)

        nomes_saque = {c["nome"] for c in cats_receita if c["especial"]}
        nomes_invest = {c["nome"] for c in cats_despesa if c["especial"]}

        resumo = []
        for i, m in enumerate(MESES, start=1):
            receita_total = sum(dados_receita.get(c["nome"], {}).get(i, 0) for c in cats_receita)
            receita_saques = sum(dados_receita.get(c["nome"], {}).get(i, 0) for c in cats_receita if c["nome"] in nomes_saque)
            receita_liquida = receita_total - receita_saques

            despesa_bruta = sum(dados_despesa.get(c["nome"], {}).get(i, 0) for c in cats_despesa)
            despesa_investimento = sum(dados_despesa.get(c["nome"], {}).get(i, 0) for c in cats_despesa if c["nome"] in nomes_invest)
            despesa_liquida = despesa_bruta - despesa_investimento

            sobras = receita_total - despesa_liquida
            sobras_sem_saques = receita_liquida - despesa_liquida
            sobras_pct = (sobras / receita_total * 100) if receita_total else None

            resumo.append({
                "Mês": m, "Receita Total": receita_total, "Despesa Bruta": despesa_bruta,
                "Investido no mês": despesa_investimento, "Despesa Líquida": despesa_liquida,
                "Sobras ($)": sobras, "Sobras s/ saques": sobras_sem_saques, "Sobras (%)": sobras_pct,
            })

        df_resumo = pd.DataFrame(resumo)

        st.dataframe(
            df_resumo.style.format({
                "Receita Total": "R$ {:.2f}", "Despesa Bruta": "R$ {:.2f}", "Investido no mês": "R$ {:.2f}",
                "Despesa Líquida": "R$ {:.2f}", "Sobras ($)": "R$ {:+.2f}", "Sobras s/ saques": "R$ {:+.2f}",
                "Sobras (%)": "{:+.2f}%",
            }, na_rep="—"),
            use_container_width=True, hide_index=True,
        )

        meses_com_dados = df_resumo[(df_resumo["Receita Total"] > 0) | (df_resumo["Despesa Bruta"] > 0)]
        n_meses = len(meses_com_dados) or 1

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Despesa média mensal", f"R$ {meses_com_dados['Despesa Líquida'].sum() / n_meses:,.2f}")
        c2.metric("Sobra média mensal", f"R$ {meses_com_dados['Sobras ($)'].sum() / n_meses:,.2f}")
        c3.metric("Sobra média s/ saques", f"R$ {meses_com_dados['Sobras s/ saques'].sum() / n_meses:,.2f}")
        media_pct = meses_com_dados["Sobras (%)"].dropna().mean()
        c4.metric("Média % poupada", f"{media_pct:.2f}%" if pd.notna(media_pct) else "—")
        st.caption(f"Médias calculadas sobre os {n_meses} mês(es) com lançamentos em {ano}.")

        st.divider()
        st.subheader("Receitas x Despesas x Sobras")
        fig = go.Figure()
        fig.add_bar(x=df_resumo["Mês"], y=df_resumo["Receita Total"], name="Receita Total", marker_color="#3ddc84")
        fig.add_bar(x=df_resumo["Mês"], y=df_resumo["Despesa Líquida"], name="Despesa Líquida", marker_color="#ff6b6b")
        fig.add_trace(go.Scatter(x=df_resumo["Mês"], y=df_resumo["Sobras ($)"], name="Sobras ($)",
                                  mode="lines+markers", line=dict(color="#4C8BF5", width=3)))
        fig.update_layout(barmode="group")
        st.plotly_chart(fig, use_container_width=True, key="grafico_resumo_mensal")

        st.divider()
        st.subheader(f"Totais do ano {ano} por categoria")
        col_r, col_d = st.columns(2)
        with col_r:
            st.markdown("**Receitas**")
            totais_r = [{"Categoria": c["nome"], "Total no ano": sum(dados_receita.get(c["nome"], {}).values())} for c in cats_receita]
            st.dataframe(pd.DataFrame(totais_r).style.format({"Total no ano": "R$ {:.2f}"}),
                         use_container_width=True, hide_index=True)
        with col_d:
            st.markdown("**Despesas**")
            totais_d = [{"Categoria": c["nome"], "Total no ano": sum(dados_despesa.get(c["nome"], {}).values())} for c in cats_despesa]
            st.dataframe(pd.DataFrame(totais_d).style.format({"Total no ano": "R$ {:.2f}"}),
                         use_container_width=True, hide_index=True)