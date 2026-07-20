import streamlit as st
import pandas as pd

import db
from api import get_news
from auth import login_gate, sidebar_user_box
from style import apply_style

st.set_page_config(page_title="Notícias e Fatos Relevantes", page_icon="📰", layout="wide")
apply_style()
db.init_db()
user_email = login_gate()
sidebar_user_box()

st.title("Notícias e Fatos Relevantes")
st.caption("Últimas notícias de cada ativo da sua carteira, via Yahoo Finance.")

ativos = db.get_ativos(user_email)

if not ativos:
    st.info("Cadastre seus ativos na tela 'Carteira Principal' para ver notícias sobre eles.")
    st.stop()

tickers = sorted({a["ticker"] for a in ativos})

if st.button("Atualizar notícias"):
    get_news.clear()


def formatar_data(valor):
    if not valor:
        return None
    try:
        if isinstance(valor, (int, float)):
            return pd.to_datetime(valor, unit="s")
        return pd.to_datetime(valor)
    except Exception:
        return None


def renderizar_card(n):
    data_dt = formatar_data(n.get("data"))
    data_fmt = data_dt.strftime("%d/%m/%Y %H:%M") if data_dt is not None else ""

    col_img, col_txt = st.columns([1, 4])
    with col_img:
        if n.get("imagem"):
            st.image(n["imagem"], use_container_width=True)
        else:
            st.markdown(
                "<div style='background:#1a1f2b; border-radius:8px; height:90px; "
                "display:flex; align-items:center; justify-content:center; color:#5a6474;'>"
                "📰</div>",
                unsafe_allow_html=True,
            )
    with col_txt:
        if n.get("link"):
            st.markdown(f"**[{n['titulo']}]({n['link']})**")
        else:
            st.markdown(f"**{n['titulo']}**")
        linha_meta = f"🏷️ {n.get('ticker', '')} · {n.get('publisher', '—')}"
        if data_fmt:
            linha_meta += f" · {data_fmt}"
        st.caption(linha_meta)
    st.divider()


tab_por_ativo, tab_tudo = st.tabs(["Por ativo", "Todas juntas (mais recentes primeiro)"])

with tab_por_ativo:
    for ticker in tickers:
        with st.expander(f"📌 {ticker}", expanded=False):
            with st.spinner(f"Buscando notícias de {ticker}..."):
                noticias = get_news(ticker)

            if not noticias:
                st.caption("Nenhuma notícia encontrada para este ativo no momento.")
                continue

            for n in noticias:
                renderizar_card(n)

with tab_tudo:
    todas = []
    with st.spinner("Buscando notícias de todos os ativos..."):
        for ticker in tickers:
            todas.extend(get_news(ticker))

    if not todas:
        st.info("Nenhuma notícia encontrada para os ativos da sua carteira no momento.")
    else:
        for n in todas:
            n["_data_ordenacao"] = formatar_data(n.get("data")) or pd.Timestamp.min
        todas.sort(key=lambda n: n["_data_ordenacao"], reverse=True)

        for n in todas:
            renderizar_card(n)