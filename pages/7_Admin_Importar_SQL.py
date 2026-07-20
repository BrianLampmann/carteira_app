import streamlit as st

import db
from auth import login_gate, sidebar_user_box
from nav import render_sidebar_nav
from style import apply_style
from admin_config import EMAILS_ADMIN

st.set_page_config(page_title="Admin - Importar SQL", page_icon="", layout="wide")
apply_style()
db.init_db()
user_email = login_gate()
render_sidebar_nav(user_email)
sidebar_user_box()

# Troque pelo(s) e-mail(is) que podem usar esta página. Qualquer outro usuário
# logado não vê nem consegue executar nada aqui.
EMAILS_PERMITIDOS = EMAILS_ADMIN

st.title("Admin - Importar / Executar SQL")

if user_email not in EMAILS_PERMITIDOS:
    st.error("Você não tem permissão para acessar esta página.")
    st.stop()

st.warning(
    "Isso executa SQL diretamente no banco de dados do app. Cuidado: não tem confirmação, "
    "não tem desfazer. Use só scripts em que você confia (ex: os que você mesmo gerou)."
)

sql_text = st.text_area("Cole aqui o script SQL (pode ter vários comandos)", height=350)

col1, col2 = st.columns([1, 4])
with col1:
    executar = st.button("Executar script", type="primary")

if executar:
    if not sql_text.strip():
        st.warning("Cole algum SQL antes de executar.")
    else:
        conn = db.get_conn()
        try:
            conn.executescript(sql_text)
            conn.commit()
            st.success("Script executado com sucesso!")
        except Exception as e:
            st.error(f"Erro ao executar: {type(e).__name__} - {e}")
        finally:
            conn.close()

st.divider()
st.subheader("Consulta rápida (SELECT)")
consulta = st.text_input("Cole um SELECT para conferir dados", value="SELECT * FROM usuarios")
if st.button("Consultar"):
    conn = db.get_conn()
    try:
        cur = conn.execute(consulta)
        colunas = [d[0] for d in cur.description]
        linhas = cur.fetchall()
        import pandas as pd
        st.dataframe(pd.DataFrame(linhas, columns=colunas), use_container_width=True)
    except Exception as e:
        st.error(f"Erro na consulta: {type(e).__name__} - {e}")
    finally:
        conn.close()