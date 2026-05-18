import streamlit as st
import sqlite3
from sqlite3 import Connection
from datetime import datetime
import pandas as pd
import hashlib
from typing import Optional, Dict, List

# -------------------------
# Configuração
# -------------------------
st.set_page_config(page_title="Apex Banco Digital", page_icon="🔱", layout="wide")
DB_FILE = "apex_bank.db"
DEFAULT_ADMIN = {"username": "admin", "password": "1702", "role": "desenvolvedor", "limite": 5000.0}

# -------------------------
# Utilitários de Banco
# -------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def get_conn() -> Connection:
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'usuario',
        limite_emprestimo REAL NOT NULL DEFAULT 2000.0,
        created_at TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        mes_ano TEXT NOT NULL,
        tipo TEXT NOT NULL,
        categoria TEXT NOT NULL,
        valor REAL NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        valor_puro REAL NOT NULL,
        total_com_juros REAL NOT NULL,
        parcelas INTEGER NOT NULL,
        divida_restante REAL NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    conn.commit()

    # garante admin padrão
    cur.execute("SELECT id FROM users WHERE username = ?", (DEFAULT_ADMIN["username"],))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users (username, password_hash, role, limite_emprestimo, created_at) VALUES (?, ?, ?, ?, ?)",
            (DEFAULT_ADMIN["username"], hash_password(DEFAULT_ADMIN["password"]), DEFAULT_ADMIN["role"], DEFAULT_ADMIN["limite"], datetime.now().isoformat())
        )
        conn.commit()
    conn.close()

# -------------------------
# Operações CRUD
# -------------------------
def create_user(username: str, password: str, limite: float = 2000.0, role: str = "usuario") -> bool:
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password_hash, role, limite_emprestimo, created_at) VALUES (?, ?, ?, ?, ?)",
            (username.strip(), hash_password(password), role, float(limite), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception:
        return False

def authenticate(username: str, password: str) -> Optional[Dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role, limite_emprestimo FROM users WHERE username = ? AND password_hash = ?",
                (username.strip(), hash_password(password)))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"id": row["id"], "username": row["username"], "role": row["role"], "limite_emprestimo": float(row["limite_emprestimo"])}
    return None

def get_user_by_username(username: str) -> Optional[Dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role, limite_emprestimo FROM users WHERE username = ?", (username.strip(),))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"id": row["id"], "username": row["username"], "role": row["role"], "limite_emprestimo": float(row["limite_emprestimo"])}
    return None

def list_clients() -> List[Dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role, limite_emprestimo, created_at FROM users WHERE LOWER(role) != 'desenvolvedor' ORDER BY username")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r["id"], "username": r["username"], "role": r["role"], "limite_emprestimo": float(r["limite_emprestimo"]), "created_at": r["created_at"]} for r in rows]

def list_all_users_df() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT id, username, role, limite_emprestimo, created_at FROM users ORDER BY id", conn)
    conn.close()
    return df

def add_transaction(user_id: int, tipo: str, categoria: str, valor: float):
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.now()
    cur.execute(
        "INSERT INTO transactions (user_id, date, mes_ano, tipo, categoria, valor) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, now.strftime("%d/%m/%Y"), now.strftime("%m/%Y"), tipo, categoria.strip(), float(valor))
    )
    conn.commit()
    conn.close()

def get_transactions_for_user(user_id: int) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT date, tipo, categoria, valor FROM transactions WHERE user_id = ? ORDER BY rowid DESC", conn, params=(user_id,))
    conn.close()
    return df

def add_loan(user_id: int, valor_puro: float, parcelas: int, taxa_mensal: float = 0.05):
    total = float(valor_puro) * ((1 + taxa_mensal) ** parcelas)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO loans (user_id, date, valor_puro, total_com_juros, parcelas, divida_restante) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, datetime.now().strftime("%d/%m/%Y"), float(valor_puro), float(total), int(parcelas), float(total))
    )
    conn.commit()
    conn.close()

def get_loans_for_user(user_id: int) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT date, valor_puro, total_com_juros, parcelas, divida_restante FROM loans WHERE user_id = ? ORDER BY rowid DESC", conn, params=(user_id,))
    conn.close()
    return df

def update_user_limit(user_id: int, novo_limite: float):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET limite_emprestimo = ? WHERE id = ?", (float(novo_limite), user_id))
    conn.commit()
    conn.close()

def delete_user(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

# -------------------------
# Inicialização
# -------------------------
init_db()

# -------------------------
# Estado da sessão
# -------------------------
st.session_state.setdefault("logado", False)
st.session_state.setdefault("user", None)

# -------------------------
# Interface
# -------------------------
def login_register_ui():
    st.subheader("🔒 Acesso ao Apex")
    tabs = st.tabs(["🔑 Entrar", "📝 Criar Conta"])
    with tabs[0]:
        user = st.text_input("Usuário", key="login_user")
        pwd = st.text_input("Senha", type="password", key="login_pass")
        if st.button("Entrar", key="btn_login"):
            if not user or not pwd:
                st.warning("Preencha usuário e senha.")
            else:
                auth = authenticate(user, pwd)
                if auth:
                    st.session_state.logado = True
                    st.session_state.user = auth
                    st.experimental_rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
    with tabs[1]:
        new_user = st.text_input("Nome de usuário", key="reg_user")
        new_pass = st.text_input("Senha", type="password", key="reg_pass")
        new_pass2 = st.text_input("Confirme a senha", type="password", key="reg_pass2")
        if st.button("Criar Conta", key="btn_create"):
            if not new_user or not new_pass:
                st.warning("Preencha todos os campos.")
            elif new_pass != new_pass2:
                st.error("As senhas não coincidem.")
            elif get_user_by_username(new_user):
                st.error("Usuário já existe.")
            else:
                ok = create_user(new_user, new_pass)
                if ok:
                    st.success("Conta criada com sucesso. Faça login.")
                else:
                    st.error("Erro ao criar conta. Tente outro nome.")

def admin_ui(user_info: Dict):
    st.sidebar.success("⚡ Administrador")
    st.header("🛠️ Painel Administrador")
    tabs = st.tabs(["👥 Usuários", "📊 Transações", "🏦 Empréstimos"])
    with tabs[0]:
        st.markdown("#### Todos os usuários")
        df_users = list_all_users_df()
        st.dataframe(df_users, use_container_width=True)

        st.markdown("#### Alterar limite de cliente")
        clients = list_clients()
        if clients:
            options = {c["username"]: c["id"] for c in clients}
            sel = st.selectbox("Selecione cliente", list(options.keys()))
            sel_id = options[sel]
            cur_lim = next((c["limite_emprestimo"] for c in clients if c["id"] == sel_id), 0.0)
            novo = st.number_input("Novo limite (R$)", min_value=0.0, value=float(cur_lim), step=100.0)
            if st.button("Aplicar limite"):
                update_user_limit(sel_id, novo)
                st.success("Limite atualizado.")
        else:
            st.info("Nenhum cliente cadastrado.")

        st.markdown("#### Excluir cliente")
        if clients:
            options2 = {c["username"]: c["id"] for c in clients}
            sel2 = st.selectbox("Selecionar para excluir", list(options2.keys()), key="del_select")
            confirm = st.checkbox("Confirmo exclusão permanente", key="del_confirm")
            if st.button("Excluir cliente") and confirm:
                delete_user(options2[sel2])
                st.success("Cliente excluído.")
        else:
            st.info("Nenhum cliente para excluir.")

    with tabs[1]:
        st.markdown("#### Todas as transações")
        conn = get_conn()
        df_tx = pd.read_sql_query("""
            SELECT t.id, u.username as usuario, t.date, t.tipo, t.categoria, t.valor
            FROM transactions t JOIN users u ON t.user_id = u.id
            ORDER BY t.id DESC
        """, conn)
        conn.close()
        st.dataframe(df_tx, use_container_width=True)

    with tabs[2]:
        st.markdown("#### Empréstimos ativos")
        conn = get_conn()
        df_loans = pd.read_sql_query("""
            SELECT l.id, u.username as usuario, l.date, l.valor_puro, l.total_com_juros, l.parcelas, l.divida_restante
            FROM loans l JOIN users u ON l.user_id = u.id
            ORDER BY l.id DESC
        """, conn)
        conn.close()
        st.dataframe(df_loans, use_container_width=True)

def client_ui(user_info: Dict):
    st.header(f"👋 Olá, {user_info['username']}")
    user_id = user_info["id"]

    tx_df = get_transactions_for_user(user_id)
    loans_df = get_loans_for_user(user_id)
    ganhos = tx_df[tx_df["tipo"] == "Ganho"]["valor"].sum() if not tx_df.empty else 0.0
    gastos = tx_df[tx_df["tipo"] == "Gasto"]["valor"].sum() if not tx_df.empty else 0.0
    total_emprestimos = loans_df["valor_puro"].sum() if not loans_df.empty else 0.0
    divida = loans_df["divida_restante"].sum() if not loans_df.empty else 0.0
    saldo = (ganhos + total_emprestimos) - gastos
    limite_disponivel = float(user_info.get("limite_emprestimo", 0.0)) - total_emprestimos

    c1, c2, c3 = st.columns(3)
    c1.metric("🟢 Saldo Disponível", f"R$ {saldo:,.2f}")
    c2.metric("🔴 Dívida Consolidada", f"R$ {divida:,.2f}")
    c3.metric("🔵 Linha de Crédito", f"R$ {max(0.0, limite_disponivel):,.2f}")

    st.divider()
    tabs = st.tabs(["💸 Nova Transação", "📊 Resumo", "🏛️ Empréstimos"])
    with tabs[0]:
        st.markdown("#### Registrar Ganho")
        cat_g = st.text_input("Categoria (Ex: Salário)", key="cat_ganho")
        val_g = st.number_input("Valor (R$)", min_value=0.0, step=1.0, key="val_ganho")
        if st.button("Registrar Ganho"):
            if val_g > 0 and cat_g.strip():
                add_transaction(user_id, "Ganho", cat_g, val_g)
                st.success("Ganho registrado.")
            else:
                st.warning("Preencha categoria e valor válido.")

        st.markdown("#### Registrar Gasto")
        cat_p = st.text_input("Categoria (Ex: Alimentação)", key="cat_gasto")
        val_p = st.number_input("Valor (R$)", min_value=0.0, step=1.0, key="val_gasto")
        if st.button("Registrar Gasto"):
            if val_p > 0 and cat_p.strip():
                add_transaction(user_id, "Gasto", cat_p, val_p)
                st.success("Gasto registrado.")
            else:
                st.warning("Preencha categoria e valor válido.")

    with tabs[1]:
        st.markdown("#### Extrato por Categoria")
        if not tx_df.empty:
            ganhos_df = tx_df[tx_df["tipo"] == "Ganho"].groupby("categoria")["valor"].sum().reset_index().rename(columns={"categoria":"Categoria","valor":"Total (R$)"})
            gastos_df = tx_df[tx_df["tipo"] == "Gasto"].groupby("categoria")["valor"].sum().reset_index().rename(columns={"categoria":"Categoria","valor":"Total (R$)"})
            colA, colB = st.columns(2)
            with colA:
                st.markdown("##### Ganhos")
                st.dataframe(ganhos_df, use_container_width=True)
            with colB:
                st.markdown("##### Gastos")
                st.dataframe(gastos_df, use_container_width=True)
            st.markdown("##### Extrato completo")
            st.dataframe(tx_df, use_container_width=True)
        else:
            st.info("Nenhuma movimentação registrada.")

    with tabs[2]:
        st.markdown("#### Solicitar Empréstimo")
        st.write(f"Limite disponível: **R$ {max(0.0, limite_disponivel):,.2f}**")
        v_sol = st.number_input("Valor solicitado (R$)", min_value=0.0, max_value=max(0.0, limite_disponivel), step=50.0, key="loan_val")
        parcelas = st.slider("Parcelas (meses)", 1, 12, 1, key="loan_parc")
        if st.button("Simular Empréstimo"):
            taxa = 0.05
            total = float(v_sol) * ((1 + taxa) ** parcelas)
            st.info(f"Total com juros (5% a.m.): R$ {total:,.2f} — {parcelas}x de R$ {total/parcelas:,.2f}")
        if st.button("Contratar Empréstimo"):
            if v_sol > 0 and v_sol <= limite_disponivel:
                add_loan(user_id, v_sol, parcelas)
                st.success("Empréstimo contratado.")
            else:
                st.error("Valor inválido ou acima do limite disponível.")

    st.divider()
    st.markdown("#### Seus empréstimos")
    if not loans_df.empty:
        st.dataframe(loans_df, use_container_width=True)
    else:
        st.info("Sem contratos de empréstimo ativos.")

# -------------------------
# Fluxo principal
# -------------------------
def main():
    st.title("🔱 Apex Banco Digital")
    if not st.session_state.logado:
        login_register_ui()
        return

    user_info = st.session_state.user
    st.sidebar.markdown(f"👤 **{user_info['username']}**")
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.session_state.user = None
        st.experimental_rerun()

    if user_info["role"].strip().lower() == "desenvolvedor":
        admin_ui(user_info)
    else:
        client_ui(user_info)

if __name__ == "__main__":
    main()
