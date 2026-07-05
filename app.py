import streamlit as st
from db import init_db
from auth import login_gate, sidebar_user_box
from style import apply_style

st.set_page_config(page_title="Minha Carteira", page_icon="💰", layout="wide")
apply_style()
init_db()

user_email = login_gate()
sidebar_user_box()

st.title("💰 Controle de Investimentos")
st.markdown(f"Bem-vindo(a), **{user_email}**! 👋")

st.markdown(
    """
Use o menu à esquerda para navegar:

- **📊 Carteira Principal** — cadastro de ativos e renda fixa, com todos os cálculos
  (valor investido, posição, valorização, preço teto, margem, dividendos, YoC).
- **🥧 Exposição da Carteira** — gráficos de pizza e barras.
- **📈 Crescimento e Aportes** — evolução patrimonial e proventos recebidos.
- **🎯 Metas** — metas de patrimônio, reserva de emergência e progresso do ano.
- **🧾 Contabilidade Mensal** — receitas e despesas mês a mês, com sobras $/% e médias.
- **📰 Notícias e Fatos Relevantes** — últimas notícias de cada ativo da sua carteira.

Seus dados são só seus: cada e-mail enxerga apenas a própria carteira.
"""
)
