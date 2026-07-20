import streamlit as st
import pandas as pd

import db
from auth import login_gate, sidebar_user_box
from nav import render_sidebar_nav
from style import apply_style
from alerts import TIPOS_LABEL, TIPOS_PRECISA_TICKER

st.set_page_config(page_title="Alertas", page_icon="", layout="wide")
apply_style()
db.init_db()
user_email = login_gate()
render_sidebar_nav(user_email)
sidebar_user_box()

st.title("Alertas")
st.caption("Configure avisos que aparecem em um pop-up quando você faz login, caso alguma condição seja atingida.")

TIPOS_LABEL_INVERSO = {v: k for k, v in TIPOS_LABEL.items()}

UNIDADE_POR_TIPO = {
    "preco_teto": "R$",
    "preco_chao": "R$",
    "variacao_pct_dia": "%",
    "yoc_minimo": "%",
    "concentracao_maxima": "%",
    "meta_patrimonio": "R$",
}


@st.dialog("Confirmar exclusão")
def confirmar_exclusao_alerta(descricao, id_):
    st.write(f"Tem certeza que deseja excluir o alerta **{descricao}**? Essa ação não pode ser desfeita.")
    col1, col2 = st.columns(2)
    if col1.button("Cancelar", use_container_width=True):
        st.rerun()
    if col2.button("Excluir", type="primary", use_container_width=True):
        db.delete_alerta(user_email, id_)
        st.success("Alerta excluído!")
        st.rerun()


ativos = db.get_ativos(user_email)

# =========================================================
# CRIAR NOVO ALERTA
# =========================================================
st.subheader("Criar novo alerta")

col1, col2 = st.columns([2, 2])
with col1:
    tipo_label = st.selectbox("Tipo de alerta", list(TIPOS_LABEL.values()), key="novo_tipo_label")
tipo = TIPOS_LABEL_INVERSO[tipo_label]

ticker_selecionado = None
if tipo in TIPOS_PRECISA_TICKER:
    if not ativos:
        st.info("Cadastre ativos na Carteira Principal antes de criar esse tipo de alerta.")
    else:
        with col2:
            ticker_selecionado = st.selectbox(
                "Ativo", [a["ticker"] for a in ativos], key="novo_ticker"
            )

unidade = UNIDADE_POR_TIPO[tipo]
valor_limite = st.number_input(f"Valor limite ({unidade})", min_value=0.0, format="%.2f", key="novo_valor")

pode_criar = (tipo not in TIPOS_PRECISA_TICKER) or (ticker_selecionado is not None)

if st.button("Adicionar alerta", type="primary", disabled=not pode_criar):
    db.add_alerta(user_email, tipo, ticker_selecionado, valor_limite, ativo=True)
    st.success("Alerta criado!")
    st.rerun()

st.divider()

# =========================================================
# IMPORTAR TETO/CHÃO DO CADASTRO DE ATIVOS
# =========================================================
with st.expander("Importar preço teto/chão já cadastrados nos ativos"):
    st.caption(
        "Cria automaticamente um alerta de Preço teto e/ou Preço chão para cada ativo "
        "que já tem esses valores preenchidos na Carteira Principal."
    )
    if st.button("Importar agora"):
        criados = 0
        for a in ativos:
            if a.get("preco_teto"):
                db.add_alerta(user_email, "preco_teto", a["ticker"], float(a["preco_teto"]), ativo=True)
                criados += 1
            if a.get("preco_chao"):
                db.add_alerta(user_email, "preco_chao", a["ticker"], float(a["preco_chao"]), ativo=True)
                criados += 1
        st.success(f"{criados} alerta(s) importado(s)!")
        st.rerun()

st.divider()

# =========================================================
# MEUS ALERTAS (editar valor/ativo em lote + excluir individualmente)
# =========================================================
st.subheader("Meus alertas")

alertas_existentes = db.get_alertas(user_email)

if not alertas_existentes:
    st.info("Nenhum alerta configurado ainda. Use o formulário acima para criar o primeiro.")
else:
    df_alertas = pd.DataFrame(alertas_existentes)
    df_show = pd.DataFrame({
        "Tipo": df_alertas["tipo"].map(TIPOS_LABEL),
        "Ativo/Escopo": df_alertas["ticker"].fillna("Carteira toda"),
        "Valor limite": df_alertas["valor_limite"],
        "Ativo?": df_alertas["ativo"].astype(bool),
    })

    edited = st.data_editor(
        df_show,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Tipo": st.column_config.TextColumn("Tipo", disabled=True),
            "Ativo/Escopo": st.column_config.TextColumn("Ativo/Escopo", disabled=True),
            "Valor limite": st.column_config.NumberColumn("Valor limite", format="%.2f"),
            "Ativo?": st.column_config.CheckboxColumn("Ativo?"),
        },
        key="editor_alertas",
    )

    if st.button("Salvar alterações", type="primary"):
        for i in range(len(edited)):
            id_ = int(df_alertas.iloc[i]["id"])
            novo_valor = float(edited.iloc[i]["Valor limite"])
            novo_ativo = bool(edited.iloc[i]["Ativo?"])
            db.update_alerta(user_email, id_, novo_valor, novo_ativo)
        st.success("Alertas atualizados!")
        st.rerun()

    st.markdown("**Excluir um alerta**")
    opcoes_exclusao = {
        f"{TIPOS_LABEL[a['tipo']]} - {a['ticker'] or 'Carteira toda'} (limite: {a['valor_limite']:.2f})": a
        for a in alertas_existentes
    }
    col_a, col_b = st.columns([4, 1])
    with col_a:
        escolha = st.selectbox("Selecione", list(opcoes_exclusao.keys()), label_visibility="collapsed")
    with col_b:
        if st.button("Excluir", use_container_width=True):
            alvo = opcoes_exclusao[escolha]
            confirmar_exclusao_alerta(escolha, alvo["id"])

st.divider()

# =========================================================
# HISTÓRICO DE ALERTAS DISPARADOS
# =========================================================
st.subheader("Histórico de alertas disparados")
historico = db.get_alertas_historico(user_email)
if not historico:
    st.caption("Nenhum alerta disparou ainda.")
else:
    df_hist = pd.DataFrame(historico)
    df_hist_show = pd.DataFrame({
        "Data/Hora": df_hist["disparado_em"],
        "Tipo": df_hist["tipo"].map(TIPOS_LABEL),
        "Ativo/Escopo": df_hist["ticker"].fillna("Carteira toda"),
        "Valor no disparo": df_hist["valor_no_disparo"],
        "Limite": df_hist["limite"],
    })
    st.dataframe(df_hist_show, use_container_width=True, hide_index=True)