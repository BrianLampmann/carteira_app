import streamlit as st
import pandas as pd
from datetime import date

import db
from api import get_prices
from auth import login_gate, sidebar_user_box
from style import apply_style, tabela_carteira

st.set_page_config(page_title="Carteira Principal", page_icon="📊", layout="wide")
apply_style()
db.init_db()
user_email = login_gate()
sidebar_user_box()

from export import dataframes_to_excel_bytes
...
st.title("Carteira Principal")

col_titulo, col_download = st.columns([5, 1])
with col_download:
    excel_bytes = dataframes_to_excel_bytes({
        "Ativos": pd.DataFrame(db.get_ativos(user_email)),
        "Renda Fixa": pd.DataFrame(db.get_renda_fixa(user_email)),
    })
    st.download_button(
        "Baixar (Excel)", data=excel_bytes,
        file_name="carteira_principal.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
tab_acoes_fiis, tab_renda_fixa = st.tabs(["Ações e FIIs", "Renda Fixa"])

# =========================================================
# ABA: AÇÕES E FIIs
# =========================================================
with tab_acoes_fiis:
    st.subheader("Cadastro de ativos")
    st.caption("Preencha ticker, tipo, setor, quantidade, preço médio, preço teto e o dividendo pago nos últimos 12 meses por cota/ação. O resto é calculado automaticamente.")

    ativos = db.get_ativos(user_email)
    df_edit = pd.DataFrame(ativos) if ativos else pd.DataFrame(
        columns=["ticker", "tipo", "setor", "quantidade", "preco_medio", "preco_teto", "dividendo_anual"]
    )
    if not df_edit.empty:
        df_edit = df_edit[["ticker", "tipo", "setor", "quantidade", "preco_medio", "preco_teto", "dividendo_anual"]]

    col_tabela, col_excluir = st.columns([4, 1])

    with col_tabela:
        edited = st.data_editor(
            df_edit,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "ticker": st.column_config.TextColumn("Ativo", required=True, help="Ex: PETR4, MXRF11"),
                "tipo": st.column_config.SelectboxColumn("Tipo", options=["Ação", "FII"], required=True),
                "setor": st.column_config.TextColumn("Setor", help="Ex: Bancos, Energia Elétrica, Mineração..."),
                "quantidade": st.column_config.NumberColumn("Quant.", min_value=0, step=1, required=True),
                "preco_medio": st.column_config.NumberColumn("Preço médio", min_value=0.0, format="R$ %.2f", required=True),
                "preco_teto": st.column_config.NumberColumn("Preço teto", min_value=0.0, format="R$ %.2f"),
                "dividendo_anual": st.column_config.NumberColumn("Div Unit 12m", min_value=0.0, format="R$ %.2f"),
            },
            key="editor_ativos",
        )

        if st.button("Salvar ativos", type="primary"):
            lista = []
            for _, row in edited.iterrows():
                if pd.isna(row.get("ticker")) or str(row.get("ticker")).strip() == "":
                    continue
                lista.append({
                    "ticker": str(row["ticker"]).strip(),
                    "tipo": row.get("tipo") or "Ação",
                    "setor": row.get("setor") or "",
                    "quantidade": float(row.get("quantidade") or 0),
                    "preco_medio": float(row.get("preco_medio") or 0),
                    "preco_teto": float(row["preco_teto"]) if not pd.isna(row.get("preco_teto")) else None,
                    "dividendo_anual": float(row["dividendo_anual"]) if not pd.isna(row.get("dividendo_anual")) else 0,
                })
            db.replace_ativos(user_email, lista)
            st.success("Ativos salvos!")
            st.rerun()

    with col_excluir:
        st.markdown("**Excluir ativo**")
        if ativos:
            ticker_selecionado = st.selectbox(
                "Selecione o ativo",
                options=[a["ticker"] for a in ativos],
                label_visibility="collapsed",
                key="select_del_ativo",
            )
            if st.button("Excluir", use_container_width=True):
                alvo = next(a for a in ativos if a["ticker"] == ticker_selecionado)
                db.delete_ativo(user_email, alvo["id"])
                st.success(f"{ticker_selecionado} excluído!")
                st.rerun()

    st.divider()
    st.subheader("Resumo da carteira")

    ativos = db.get_ativos(user_email)
    if not ativos:
        st.info("Cadastre seus ativos acima para ver os cálculos.")
    else:
        tickers = [a["ticker"] for a in ativos]

        if st.button("🔄 Atualizar cotações"):
            get_prices.clear()

        with st.spinner("Buscando cotações atuais..."):
            precos = get_prices(tickers)

        sem_cotacao = [t for t in tickers if precos.get(t.upper()) is None]
        if sem_cotacao:
            st.warning(
                f"Não consegui buscar a cotação atual de: **{', '.join(sem_cotacao)}**. "
                "Eles ficam com o preço médio como valor atual (valorização/margem zeradas) até a próxima tentativa. "
                "Possíveis causas: ticker digitado errado, ativo pouco líquido, ou o Yahoo Finance limitou "
                "temporariamente as requisições (nesse caso, espere 1-2 minutos e clique em '🔄 Atualizar cotações')."
            )

        linhas = []
        for a in ativos:
            preco_atual = precos.get(a["ticker"].upper())
            valor_investido = a["quantidade"] * a["preco_medio"]
            valor_atual = a["quantidade"] * preco_atual if preco_atual else valor_investido
            valorizacao_pct = (
                ((preco_atual - a["preco_medio"]) / a["preco_medio"]) * 100
                if preco_atual and a["preco_medio"] else 0
            )
            margem_pct = (
                ((a["preco_teto"] - (preco_atual or a["preco_medio"])) / a["preco_teto"]) * 100
                if a["preco_teto"] else None
            )
            yoc = (
                (a["dividendo_anual"] / a["preco_medio"]) * 100
                if a["dividendo_anual"] and a["preco_medio"] else 0
            )
            yoc_m = yoc / 12
            linhas.append({
                "Tipo": a["tipo"], "Ativos": a["ticker"], "Setor": a["setor"] or "—", "Quant.": a["quantidade"],
                "Preço médio": a["preco_medio"], "Valor Investido": valor_investido,
                "Preço atual": preco_atual or a["preco_medio"],
                "Valor atual": valor_atual, "Valorização": valorizacao_pct,
                "Preço teto": a["preco_teto"], "Margem": margem_pct,
                "Div Unit 12m": a["dividendo_anual"], "YoC": yoc, "YoC m": yoc_m,
            })

        df = pd.DataFrame(linhas)
        total_valor_atual = df["Valor atual"].sum()
        df["Posição"] = df["Valor atual"] / total_valor_atual * 100

        cols_order = ["Ativos", "Setor", "Quant.", "Preço médio", "Valor Investido", "Posição",
                      "Preço atual", "Valor atual", "Valorização", "Preço teto", "Margem",
                      "Div Unit 12m", "YoC", "YoC m"]

        formatos = {
            "Quant.": "{:.0f}", "Preço médio": "R$ {:.2f}", "Valor Investido": "R$ {:.2f}",
            "Posição": "{:.2f}%", "Preço atual": "R$ {:.2f}", "Valor atual": "R$ {:.2f}",
            "Valorização": "{:+.2f}%", "Preço teto": "R$ {:.2f}", "Margem": "{:+.2f}%",
            "Div Unit 12m": "R$ {:.2f}", "YoC": "{:.2f}%", "YoC m": "{:.2f}%",
        }

        df_acoes = df[df["Tipo"] == "Ação"][cols_order]
        df_fiis = df[df["Tipo"] == "FII"][cols_order]

        if not df_acoes.empty:
            st.markdown("**Ações**")
            st.dataframe(tabela_carteira(df_acoes, formatos), use_container_width=True, hide_index=True)
        if not df_fiis.empty:
            st.markdown("**FIIs**")
            st.dataframe(tabela_carteira(df_fiis, formatos), use_container_width=True, hide_index=True)

        col1, col2, col3, col4 = st.columns(4)
        total_acoes = df.loc[df["Tipo"] == "Ação", "Valor atual"].sum()
        total_fiis = df.loc[df["Tipo"] == "FII", "Valor atual"].sum()
        media_yoc = df["YoC"].mean()
        col1.metric("Total em Ações", f"R$ {total_acoes:,.2f}")
        col2.metric("Total em FIIs", f"R$ {total_fiis:,.2f}")
        col3.metric("Total Ações + FIIs", f"R$ {(total_acoes + total_fiis):,.2f}")
        col4.metric("Média YoC", f"{media_yoc:.2f}%")
        

# =========================================================
# ABA: RENDA FIXA
# =========================================================
with tab_renda_fixa:
    st.subheader("Cadastro de renda fixa")

    rf = db.get_renda_fixa(user_email)
    df_rf = pd.DataFrame(rf) if rf else pd.DataFrame(
        columns=["nome", "categoria", "valor_investido", "taxa", "data_aplicacao"]
    )
    if not df_rf.empty:
        df_rf = df_rf[["nome", "categoria", "valor_investido", "taxa", "data_aplicacao"]]

    edited_rf = st.data_editor(
        df_rf,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "nome": st.column_config.TextColumn("Nome/Instituição", required=True),
            "categoria": st.column_config.SelectboxColumn("Categoria", options=["CDI", "FGTS", "Outro"], required=True),
            "valor_investido": st.column_config.NumberColumn("Valor investido", min_value=0.0, format="R$ %.2f", required=True),
            "taxa": st.column_config.TextColumn("Taxa", help="Ex: 110% do CDI, IPCA + 6%"),
            "data_aplicacao": st.column_config.TextColumn("Data aplicação", help="AAAA-MM-DD"),
        },
        key="editor_rf",
    )

    if st.button("💾 Salvar renda fixa", type="primary"):
        lista = []
        for _, row in edited_rf.iterrows():
            if pd.isna(row.get("nome")) or str(row.get("nome")).strip() == "":
                continue
            lista.append({
                "nome": str(row["nome"]).strip(),
                "categoria": row.get("categoria") or "Outro",
                "valor_investido": float(row.get("valor_investido") or 0),
                "taxa": row.get("taxa") or "",
                "data_aplicacao": row.get("data_aplicacao") or str(date.today()),
            })
        db.replace_renda_fixa(user_email, lista)
        st.success("Renda fixa salva!")
        st.rerun()

    rf = db.get_renda_fixa(user_email)
    total_rf = sum(r["valor_investido"] for r in rf) if rf else 0
    st.metric("Total em Renda Fixa", f"R$ {total_rf:,.2f}")
