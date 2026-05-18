import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
import pandas as pd

DB_FILE = "meu_banco.db"

# -------------------------
# Funções auxiliares
# -------------------------
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT,
        role TEXT DEFAULT 'cliente',
        limite REAL DEFAULT 2000.0
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS transacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        data TEXT,
        tipo TEXT,
        categoria TEXT,
        valor REAL
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS emprestimos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        data TEXT,
        valor REAL,
        total REAL,
        parcelas INTEGER,
        divida REAL
    )""")
    conn.commit()
    # cria admin se não existir
    cur.execute("SELECT id FROM users WHERE role='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username,password_hash,role,limite) VALUES (?,?,?,?)",
                    ("admin", hash_password("1702"), "admin", 5000))
        conn.commit()
    conn.close()

def autenticar(user, pwd):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id,username,role,limite FROM users WHERE username=? AND password_hash=?",
                (user, hash_password(pwd)))
    row = cur.fetchone()
    conn.close()
    return row

# -------------------------
# Inicialização
# -------------------------
init_db()
st.session_state.setdefault("logado", False)
st.session_state.setdefault("user", None)

# -------------------------
# Interface
# -------------------------
st.title("🔱 Banco Digital Simples")

if not st.session_state.logado:
    aba1, aba2 = st.tabs(["Entrar", "Cadastrar"])
    with aba1:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Login"):
            row = autenticar(u, p)
            if row:
                st.session_state.logado = True
                st.session_state.user = {"id": row[0], "username": row[1], "role": row[2], "limite": row[3]}
                st.experimental_rerun()
            else:
                st.error("Usuário ou senha inválidos.")
    with aba2:
        u = st.text_input("Novo usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Cadastrar"):
            try:
                conn = get_conn()
                conn.execute("INSERT INTO users (username,password_hash) VALUES (?,?)", (u, hash_password(p)))
                conn.commit()
                conn.close()
                st.success("Conta criada! Faça login.")
            except:
                st.error("Usuário já existe.")
else:
    user = st.session_state.user
    st.sidebar.write(f"👤 {user['username']} ({user['role']})")
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.session_state.user = None
        st.experimental_rerun()

    if user["role"] == "admin":
        st.header("Painel do Administrador")
        conn = get_conn()
        df_users = pd.read_sql("SELECT id,username,role,limite FROM users", conn)
        st.dataframe(df_users)
        conn.close()
    else:
        st.header("Painel do Cliente")
        conn = get_conn()
        df_tx = pd.read_sql("SELECT data,tipo,categoria,valor FROM transacoes WHERE user_id=?", conn, params=(user["id"],))
        df_loans = pd.read_sql("SELECT data,valor,total,parcelas,divida FROM emprestimos WHERE user_id=?", conn, params=(user["id"],))
        conn.close()

        ganhos = df_tx[df_tx["tipo"]=="ganho"]["valor"].sum() if not df_tx.empty else 0
        gastos = df_tx[df_tx["tipo"]=="gasto"]["valor"].sum() if not df_tx.empty else 0
        emprestimos = df_loans["valor"].sum() if not df_loans.empty else 0
        divida = df_loans["divida"].sum() if not df_loans.empty else 0
        saldo = ganhos - gastos + emprestimos
        limite_disp = user["limite"] - emprestimos

        c1,c2,c3 = st.columns(3)
        c1.metric("Saldo", f"R$ {saldo:,.2f}")
        c2.metric("Dívida", f"R$ {divida:,.2f}")
        c3.metric("Limite disponível", f"R$ {limite_disp:,.2f}")

        st.subheader("Nova Transação")
        tipo = st.selectbox("Tipo", ["ganho","gasto"])
        cat = st.text_input("Categoria")
        val = st.number_input("Valor", min_value=0.0, step=10.0)
        if st.button("Registrar"):
            conn = get_conn()
            conn.execute("INSERT INTO transacoes (user_id,data,tipo,categoria,valor) VALUES (?,?,?,?,?)",
                         (user["id"], datetime.now().strftime("%d/%m/%Y"), tipo, cat, val))
            conn.commit()
            conn.close()
            st.success("Transação registrada.")

        st.subheader("Solicitar Empréstimo")
        v = st.number_input("Valor solicitado", min_value=0.0, max_value=limite_disp, step=100.0)
        parc = st.slider("Parcelas", 1, 12, 1)
        if st.button("Contratar"):
            total = v * ((1+0.05)**parc)
            conn = get_conn()
            conn.execute("INSERT INTO emprestimos (user_id,data,valor,total,parcelas,divida) VALUES (?,?,?,?,?,?)",
                         (user["id"], datetime.now().strftime("%d/%m/%Y"), v, total, parc, total))
            conn.commit()
            conn.close()
            st.success("Empréstimo contratado.")

        st.subheader("Extrato")
        st.dataframe(df_tx)
        st.subheader("Empréstimos")
        st.dataframe(df_loans)
