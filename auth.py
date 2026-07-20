import re
import os
import hashlib
import binascii
import streamlit as st

import db


def _is_valid_email(email: str) -> bool:
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or "") is not None


def _hash_password(password: str, salt_hex: str = None):
    salt = os.urandom(16) if salt_hex is None else binascii.unhexlify(salt_hex)
    hash_bytes = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return binascii.hexlify(salt).decode(), binascii.hexlify(hash_bytes).decode()


def _verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    _, computed = _hash_password(password, salt_hex)
    return computed == hash_hex


def login_gate():
    if st.session_state.get("user_email"):
        return st.session_state["user_email"]

    db.init_db()

    st.markdown(
        "<h1 style='text-align:center;'>Controle de Investimentos</h1>",
        unsafe_allow_html=True,
    )

    _, col, _ = st.columns([1, 1.3, 1])
    with col:
        tab_entrar, tab_criar = st.tabs(["Entrar", "Criar conta"])

        with tab_entrar:
            with st.form("login_form"):
                email = st.text_input("E-mail")
                senha = st.text_input("Senha", type="password")
                entrar = st.form_submit_button("Entrar", type="primary", use_container_width=True)
                if entrar:
                    if not _is_valid_email(email):
                        st.error("Digite um e-mail válido.")
                    else:
                        user = db.get_user(email.strip().lower())
                        if not user or not _verify_password(senha, user["salt"], user["senha_hash"]):
                            st.error("E-mail ou senha incorretos.")
                        else:
                            st.session_state["user_email"] = email.strip().lower()
                            st.rerun()

        with tab_criar:
            st.caption("Cada pessoa cria sua própria conta e define sua própria senha.")
            with st.form("signup_form"):
                nome_completo = st.text_input("Nome completo", key="signup_nome")
                novo_email = st.text_input("E-mail", key="signup_email")
                telefone = st.text_input("Telefone/WhatsApp (opcional)", key="signup_telefone")
                perfil_investidor = st.selectbox(
                    "Perfil de investidor",
                    ["Conservador", "Moderado", "Arrojado"],
                    key="signup_perfil",
                )
                objetivo = st.selectbox(
                    "Objetivo principal",
                    ["Reserva de emergência", "Renda passiva", "Aposentadoria",
                     "Crescimento de patrimônio", "Outro"],
                    key="signup_objetivo",
                )
                nova_senha = st.text_input("Crie uma senha", type="password", key="signup_pass")
                confirmar = st.text_input("Confirme a senha", type="password", key="signup_pass2")
                criar = st.form_submit_button("Criar conta", type="primary", use_container_width=True)
                if criar:
                    if not nome_completo.strip():
                        st.error("Digite seu nome completo.")
                    elif not _is_valid_email(novo_email):
                        st.error("Digite um e-mail válido.")
                    elif len(nova_senha) < 6:
                        st.error("A senha precisa ter pelo menos 6 caracteres.")
                    elif nova_senha != confirmar:
                        st.error("As senhas não coincidem.")
                    else:
                        salt, hash_ = _hash_password(nova_senha)
                        ok = db.add_user(
                            novo_email.strip().lower(), salt, hash_,
                            nome_completo=nome_completo.strip(), telefone=telefone.strip(),
                            perfil_investidor=perfil_investidor, objetivo=objetivo,
                        )
                        if ok:
                            st.session_state["user_email"] = novo_email.strip().lower()
                            st.rerun()
                        else:
                            st.error("Já existe uma conta com esse e-mail.")

    st.stop()


def sidebar_user_box():
    email = st.session_state.get("user_email")
    if not email:
        return
    with st.sidebar:
        st.divider()
        st.caption(f"Logado como {email}")
        if st.button("Sair", use_container_width=True):
            del st.session_state["user_email"]
            st.rerun()