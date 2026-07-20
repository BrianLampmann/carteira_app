"""
Monta o menu lateral manualmente com st.page_link, em vez de depender da
navegação automática do Streamlit (que sempre mostra todas as páginas da
pasta pages/ para todo mundo, sem exceção). Isso permite esconder páginas
administrativas de quem não deveria vê-las.

Requer client.showSidebarNavigation = false no .streamlit/config.toml.
"""
import streamlit as st

from admin_config import EMAILS_ADMIN

PAGINAS_PUBLICAS = [
    ("Início.py", "Início"),
    ("pages/1_Carteira_Principal.py", "Carteira Principal"),
    ("pages/2_Exposição_da_Carteira.py", "Exposição da Carteira"),
    ("pages/3_Crescimento_e_Aportes.py", "Crescimento e Aportes"),
    ("pages/4_Metas.py", "Metas"),
    ("pages/5_Contabilidade_Mensal.py", "Contabilidade Mensal"),
    ("pages/6_Notícias_e_Fatos_Relevantes.py", "Notícias e Fatos Relevantes"),
    ("pages/8_Alertas.py", "Alertas"),
]

PAGINAS_ADMIN = [
    ("pages/7_Admin_Importar_SQL.py", "Admin - Importar SQL"),
]


def render_sidebar_nav(user_email):
    with st.sidebar:
        for caminho, rotulo in PAGINAS_PUBLICAS:
            st.page_link(caminho, label=rotulo)
        if user_email in EMAILS_ADMIN:
            for caminho, rotulo in PAGINAS_ADMIN:
                st.page_link(caminho, label=rotulo)