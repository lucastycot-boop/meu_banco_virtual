import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Banco Digital", page_icon="💳", layout="wide")

# -------------------------
# Dados em memória
# -------------------------
if "usuarios" not in st.session_state:
    st.session_state.usuarios = {"admin": {"senha": "1702", "role": "admin", "limite": 5000}}
if "logado" not in st.session_state:
    st.session_state.logado = None
if "transacoes" not in st.session_state:
    st.session_state.transacoes = []
if "emprestimos" not in st.session_state:
    st.session_state.emprestimos = []

# -------------------------
# Login / Cadastro
# -------------------------
if not st.session_state.logado:
    aba1, aba2 = st.tabs(["Entrar", "Cadastrar"])
    with aba1:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Login"):
            if u in st.session_state.usuarios and st.session_state.usuarios[u]["senha"] == p:
                st.session_state.logado = u
                st.experimental_rerun()
            else:
                st.error("Usuário ou senha inválidos.")
    with aba2:
        u = st.text_input("Novo usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Cadastrar"):
            if u in st.session_state.usuarios:
                st.error("Usuário já existe.")
            else:
                st.session_state.usuarios[u] = {"senha": p, "role": "cliente", "limite": 2000}
                st.success("Conta criada! Faça login.")
else:
    user = st.session_state.logado
    role = st.session_state.usuarios[user]["role"]
    st.sidebar.write(f"👤 {user} ({role})")
    if st.sidebar.button("Sair"):
        st.session_state.logado = None
        st.experimental_rerun()

    # -------------------------
    # Painel Admin
    # -------------------------
    if role == "admin":
        st.header("Painel do Administrador")
        df_users = pd.DataFrame([
            {"Usuário": u, "Role": d["role"], "Limite": d["limite"]}
            for u, d in st.session_state.usuarios.items()
        ])
        st.dataframe(df_users)

    # -------------------------
    # Painel Cliente
    # -------------------------
    else:
        st.header("Painel do Cliente")

        # Resumo financeiro
        ganhos = sum(t["valor"] for t in st.session_state.transacoes if t["user"] == user and t["tipo"] == "ganho")
        gastos = sum(t["valor"] for t in st.session_state.transacoes if t["user"] == user and t["tipo"] == "gasto")
        emprestimos = sum(e["valor"] for e in st.session_state.emprestimos if e["user"] == user)
        divida = sum(e["divida"] for e in st.session_state.emprestimos if e["user"] == user)
        saldo = ganhos - gastos + emprestimos
        limite_disp = st.session_state.usuarios[user]["limite"] - emprestimos

        c1, c2, c3 = st.columns(3)
        c1.metric("Saldo", f"R$ {saldo:,.2f}")
        c2.metric("Dívida", f"R$ {divida:,.2f}")
        c3.metric("Limite disponível", f"R$ {limite_disp:,.2f}")

        st.divider()

        # Nova transação
        st.subheader("Nova Transação")
        tipo = st.selectbox("Tipo", ["ganho", "gasto"])
        cat = st.text_input("Categoria")
        val = st.number_input("Valor", min_value=0.0, step=10.0)
        if st.button("Registrar"):
            st.session_state.transacoes.append({
                "user": user,
                "data": datetime.now().strftime("%d/%m/%Y"),
                "tipo": tipo,
                "categoria": cat,
                "valor": val
            })
            st.success("Transação registrada.")

        # Empréstimo
        st.subheader("Solicitar Empréstimo")
        v = st.number_input("Valor solicitado", min_value=0.0, max_value=limite_disp, step=100.0)
        parc = st.slider("Parcelas", 1, 12, 1)
        if st.button("Contratar"):
            total = v * ((1+0.05)**parc)
            st.session_state.emprestimos.append({
                "user": user,
                "data": datetime.now().strftime("%d/%m/%Y"),
                "valor": v,
                "total": total,
                "parcelas": parc,
                "divida": total
            })
            st.success("Empréstimo contratado.")

        # Extrato
        st.subheader("Extrato")
        df_tx = pd.DataFrame([t for t in st.session_state.transacoes if t["user"] == user])
        st.dataframe(df_tx)

        st.subheader("Empréstimos")
        df_loans = pd.DataFrame([e for e in st.session_state.emprestimos if e["user"] == user])
        st.dataframe(df_loans)
