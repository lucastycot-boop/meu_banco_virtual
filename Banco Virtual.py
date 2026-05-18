import streamlit as st
import pandas as pd
import sqlite3
import os

# 1. Configuração de Layout
st.set_page_config(
    page_title="Apex Banco Digital", 
    page_icon="🔱", 
    layout="wide"
)

DB_NAME = "banco_dados.db"

# 2. Funções do Banco de Dados Real (SQLite)
def conectar_banco():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Cria a tabela real se ela não existir no servidor
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contas (
            usuario TEXT PRIMARY KEY,
            senha TEXT,
            role TEXT,
            ganhos REAL,
            gastos REAL,
            limite_emprestimo REAL,
            divida_emprestimo REAL
        )
    ''')
    conn.commit()
    return conn

def inicializar_admin():
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contas WHERE usuario = 'Lucas'")
    if cursor.fetchone() is None:
        cursor.execute('''
            INSERT INTO contas (usuario, senha, role, ganhos, gastos, limite_emprestimo, divida_emprestimo)
            VALUES ('Lucas', '1702', 'desenvolvedor', 0.0, 0.0, 5000.0, 0.0)
        ''')
        conn.commit()
    conn.close()

def carregar_dados():
    conn = conectar_banco()
    df = pd.read_sql_query("SELECT * FROM contas", conn)
    conn.close()
    return df

def cadastrar_usuario(usuario, senha):
    conn = conectar_banco()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO contas (usuario, senha, role, ganhos, gastos, limite_emprestimo, divida_emprestimo)
            VALUES (?, ?, 'usuario', 0.0, 0.0, 2000.0, 0.0)
        ''', (usuario, senha))
        conn.commit()
        sucesso = True
    except sqlite3.IntegrityError:
        sucesso = False
    conn.close()
    return sucesso

def atualizar_movimentacao(usuario, tipo, valor):
    conn = conectar_banco()
    cursor = conn.cursor()
    if tipo == "ganho":
        cursor.execute("UPDATE contas SET ganhos = ganhos + ? WHERE usuario = ?", (valor, usuario))
    elif tipo == "gasto":
        cursor.execute("UPDATE contas SET gastos = gastos + ? WHERE usuario = ?", (valor, usuario))
    conn.commit()
    conn.close()

# Inicializa a estrutura física do banco
inicializar_admin()

def meu_banco_digital():
    st.title("🔱 Apex | Sistema Bancário Inteligente")

    if "logado" not in st.session_state: 
        st.session_state.logado = False
    if "usuario_atual" not in st.session_state: 
        st.session_state.usuario_atual = None

    df_banco = carregar_dados()

    # --- TELA 1: LOGIN E CADASTRO ---
    if not st.session_state.logado:
        col_cen, col_box, col_dir = st.columns([1, 2, 1])
        with col_box:
            with st.container(border=True):
                st.subheader("🔒 Controle de Acesso")
                aba_login, aba_cadastro = st.tabs(["🔑 Entrar", "📝 Criar Nova Conta"])
                
                with aba_login:
                    u_input = st.text_input("Usuário", key="login_u").strip()
                    s_input = st.text_input("Senha", type="password", key="login_s").strip()
                    if st.button("Acessar Banco", use_container_width=True, type="primary"):
                        user_rows = df_banco[df_banco["usuario"] == u_input]
                        if not user_rows.empty and str(user_rows.iloc[0]["senha"]) == s_input:
                            st.session_state.logado = True
                            st.session_state.usuario_atual = u_input
                            st.rerun()
                        else:
                            st.error("Usuário ou senha incorretos!")
                            
                with aba_cadastro:
                    n_user = st.text_input("Nome de Usuário", key="cad_u").strip()
                    n_pass = st.text_input("Senha de Acesso", type="password", key="cad_s").strip()
                    c_pass = st.text_input("Confirme a Senha", type="password", key="cad_cp").strip()
                    if st.button("Cadastrar no Sistema", use_container_width=True):
                        if not n_user or not n_pass:
                            st.warning("Preencha todos os campos!")
                        elif n_pass != c_pass:
                            st.error("As senhas não batem!")
                        else:
                            if cadastrar_usuario(n_user, n_pass):
                                st.success("Conta criada! Vá para a aba 'Entrar'.")
                            else:
                                st.error("Este usuário já existe!")
        return

    # --- TELA 2: PAINEL INTERNO ---
    user = st.session_state.usuario_atual
    user_data = df_banco[df_banco["usuario"] == user].iloc[0]

    with st.sidebar:
        st.markdown(f"👤 Usuário: **{user}**")
        st.markdown(f"🏷️ Perfil: `{user_data['role']}`")
        st.divider()
        if st.button("🚪 Desconectar", type="destructive", use_container_width=True):
            st.session_state.logado = False
            st.session_state.usuario_atual = None
            st.rerun()

    # ROTA DO ADMINISTRADOR
    if user_data["role"] == "desenvolvedor":
        st.header("🛠️ Painel de Controle Admin")
        st.markdown("##### Todos os Clientes Cadastrados no Banco de Dados:")
        st.dataframe(df_banco, use_container_width=True)

    # ROTA DO CLIENTE
    else:
        st.header(f"👋 Bem-vindo, {user}!")
        saldo = float(user_data["ganhos"]) - float(user_data["gastos"])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🟢 SALDO ATUAL", f"R$ {saldo:,.2f}")
        with col2:
            st.metric("🔴 DÍVIDA", f"R$ {float(user_data['divida_emprestimo']):,.2f}")
        with col3:
            st.metric("🔵 LINHA DE CRÉDITO", f"R$ {float(user_data['limite_emprestimo']):,.2f}")

        st.divider()
        st.markdown("#### 💸 Movimentar Conta")
        c_ganho, c_gasto = st.columns(2)
        
        with c_ganho:
            with st.container(border=True):
                st.markdown("##### Receber PIX")
                v_ganho = st.number_input("Valor (R$)", min_value=0.0, step=50.0, key="v_g")
                if st.button("Confirmar Entrada"):
                    if v_ganho > 0:
                        atualizar_movimentacao(user, "ganho", v_ganho)
                        st.success("Valor recebido!")
                        st.rerun()
                        
        with c_gasto:
            with st.container(border=True):
                st.markdown("##### Pagar / Gastar")
                v_gasto = st.number_input("Valor (R$)", min_value=0.0, step=50.0, key="v_p")
                if st.button("Confirmar Pagamento"):
                    if v_gasto > 0:
                        atualizar_movimentacao(user, "gasto", v_gasto)
                        st.success("Pagamento realizado!")
                        st.rerun()

if __name__ == '__main__':
    meu_banco_digital()
