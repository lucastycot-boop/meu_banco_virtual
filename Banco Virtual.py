import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Meu Banco Digital", page_icon="💰", layout="centered")

DB_FILE = Path(__file__).with_name("banco.db")

# Banco de dados SQLite persistente
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS contas (
                usuario TEXT PRIMARY KEY,
                senha TEXT NOT NULL,
                role TEXT NOT NULL,
                ganhos REAL NOT NULL DEFAULT 0.0,
                gastos REAL NOT NULL DEFAULT 0.0,
                limite_emprestimo REAL NOT NULL DEFAULT 2000.0,
                divida_emprestimo REAL NOT NULL DEFAULT 0.0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                tipo TEXT NOT NULL,
                valor REAL NOT NULL,
                descricao TEXT,
                data_hora TEXT NOT NULL,
                FOREIGN KEY(usuario) REFERENCES contas(usuario)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS emprestimos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                data_hora TEXT NOT NULL,
                valor_puro REAL NOT NULL,
                total_com_juros REAL NOT NULL,
                parcelas INTEGER NOT NULL,
                divida_restante REAL NOT NULL,
                FOREIGN KEY(usuario) REFERENCES contas(usuario)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS emprestimos_pagos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                data_hora TEXT NOT NULL,
                valor_puro REAL NOT NULL,
                total_com_juros REAL NOT NULL,
                parcelas INTEGER NOT NULL,
                divida_restante REAL NOT NULL,
                data_pagamento TEXT NOT NULL,
                valor_pago REAL NOT NULL,
                FOREIGN KEY(usuario) REFERENCES contas(usuario)
            )
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO contas (usuario, senha, role, ganhos, gastos, limite_emprestimo, divida_emprestimo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("Lucas", "1702", "desenvolvedor", 0.0, 0.0, 5000.0, 0.0),
        )

def fetch_user(usuario):
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM contas WHERE usuario = ?", (usuario,)).fetchone()
    return dict(row) if row else None

def fetch_all_users():
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM contas ORDER BY usuario").fetchall()
    return [dict(row) for row in rows]

def authenticate_user(usuario, senha):
    dados = fetch_user(usuario)
    return dados is not None and dados["senha"] == senha

def create_user_in_db(usuario, senha, role, limite_emprestimo):
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO contas (usuario, senha, role, ganhos, gastos, limite_emprestimo, divida_emprestimo) VALUES (?, ?, ?, 0.0, 0.0, ?, 0.0)",
            (usuario, senha, role, limite_emprestimo),
        )
    add_transaction(usuario, "cadastro", 0.0, "Criação de conta")

def update_user_in_db(usuario, **fields):
    assignments = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [usuario]
    with get_db_connection() as conn:
        conn.execute(f"UPDATE contas SET {assignments} WHERE usuario = ?", values)

def add_transaction(usuario, tipo, valor, descricao):
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO transacoes (usuario, tipo, valor, descricao, data_hora) VALUES (?, ?, ?, ?, ?)",
            (usuario, tipo, valor, descricao, datetime.now().isoformat()),
        )

def create_loan_in_db(usuario, valor_puro, total_com_juros, parcelas):
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO emprestimos (usuario, data_hora, valor_puro, total_com_juros, parcelas, divida_restante) VALUES (?, ?, ?, ?, ?, ?)",
            (usuario, datetime.now().isoformat(), valor_puro, total_com_juros, parcelas, total_com_juros),
        )

def fetch_users_df():
    with get_db_connection() as conn:
        rows = conn.execute("SELECT usuario, role, ganhos, gastos, limite_emprestimo, divida_emprestimo FROM contas ORDER BY usuario").fetchall()
    if not rows:
        return pd.DataFrame(columns=["usuario", "role", "ganhos", "gastos", "limite_emprestimo", "divida_emprestimo"])
    return pd.DataFrame([dict(row) for row in rows])

def fetch_transactions_df(usuario=None):
    sql = "SELECT * FROM transacoes"
    params = ()
    if usuario:
        sql += " WHERE usuario = ?"
        params = (usuario,)
    with get_db_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    if not rows:
        return pd.DataFrame(columns=["id", "usuario", "tipo", "valor", "descricao", "data_hora"])
    return pd.DataFrame([dict(row) for row in rows])

def fetch_loans_df(usuario=None):
    sql = "SELECT * FROM emprestimos"
    params = ()
    if usuario:
        sql += " WHERE usuario = ?"
        params = (usuario,)
    with get_db_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    if not rows:
        return pd.DataFrame(columns=["id", "usuario", "data_hora", "valor_puro", "total_com_juros", "parcelas", "divida_restante"])
    return pd.DataFrame([dict(row) for row in rows])

def fetch_paid_loans_df(usuario=None):
    sql = "SELECT * FROM emprestimos_pagos"
    params = ()
    if usuario:
        sql += " WHERE usuario = ?"
        params = (usuario,)
    with get_db_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    if not rows:
        return pd.DataFrame(columns=["id", "usuario", "data_hora", "valor_puro", "total_com_juros", "parcelas", "divida_restante", "data_pagamento", "valor_pago"])
    return pd.DataFrame([dict(row) for row in rows])

def delete_user(usuario):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM transacoes WHERE usuario = ?", (usuario,))
        conn.execute("DELETE FROM emprestimos WHERE usuario = ?", (usuario,))
        conn.execute("DELETE FROM emprestimos_pagos WHERE usuario = ?", (usuario,))
        conn.execute("DELETE FROM contas WHERE usuario = ?", (usuario,))

def delete_transaction(transacao_id):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM transacoes WHERE id = ?", (transacao_id,))

def reverse_developer_interest(valor_juros):
    if valor_juros <= 0:
        return
    with get_db_connection() as conn:
        dev = conn.execute("SELECT * FROM contas WHERE role = 'desenvolvedor' LIMIT 1").fetchone()
        if not dev:
            return
        novo_ganhos = max(0.0, dev["ganhos"] - valor_juros)
        conn.execute("UPDATE contas SET ganhos = ? WHERE usuario = ?", (novo_ganhos, dev["usuario"]))
        dev_tx = conn.execute(
            "SELECT id FROM transacoes WHERE usuario = ? AND tipo = 'Ganho' AND valor = ? AND descricao = 'Juros de Empréstimo' ORDER BY data_hora DESC LIMIT 1",
            (dev["usuario"], valor_juros),
        ).fetchone()
        if dev_tx:
            conn.execute("DELETE FROM transacoes WHERE id = ?", (dev_tx["id"],))

def cancel_loan(loan_id):
    with get_db_connection() as conn:
        loan = conn.execute("SELECT * FROM emprestimos WHERE id = ?", (loan_id,)).fetchone()
        if not loan:
            return False

        usuario = loan["usuario"]
        valor_puro = loan["valor_puro"]
        total_com_juros = loan["total_com_juros"]

        cliente = conn.execute("SELECT * FROM contas WHERE usuario = ?", (usuario,)).fetchone()
        if cliente:
            novo_ganhos = cliente["ganhos"] - valor_puro
            novo_divida = max(0.0, cliente["divida_emprestimo"] - total_com_juros)
            novo_limite = cliente["limite_emprestimo"] + valor_puro
            conn.execute(
                "UPDATE contas SET ganhos = ?, divida_emprestimo = ?, limite_emprestimo = ? WHERE usuario = ?",
                (novo_ganhos, novo_divida, novo_limite, usuario),
            )
            loan_tx = conn.execute(
                "SELECT id FROM transacoes WHERE usuario = ? AND tipo = 'Empréstimo' AND valor = ? ORDER BY data_hora DESC LIMIT 1",
                (usuario, valor_puro),
            ).fetchone()
            if loan_tx:
                conn.execute("DELETE FROM transacoes WHERE id = ?", (loan_tx["id"],))

        juros_aplicados = total_com_juros - valor_puro
        reverse_developer_interest(juros_aplicados)
        conn.execute("DELETE FROM emprestimos WHERE id = ?", (loan_id,))
    return True

def pay_loan(loan_id):
    with get_db_connection() as conn:
        loan = conn.execute("SELECT * FROM emprestimos WHERE id = ?", (loan_id,)).fetchone()
        if not loan:
            return False
        usuario = loan["usuario"]
        valor_puro = loan["valor_puro"]
        total_com_juros = loan["total_com_juros"]

        cliente = conn.execute("SELECT * FROM contas WHERE usuario = ?", (usuario,)).fetchone()
        if cliente:
            novo_gastos = cliente["gastos"] + total_com_juros
            nova_divida = max(0.0, cliente["divida_emprestimo"] - total_com_juros)
            novo_limite = cliente["limite_emprestimo"] + valor_puro
            conn.execute(
                "UPDATE contas SET gastos = ?, divida_emprestimo = ?, limite_emprestimo = ? WHERE usuario = ?",
                (novo_gastos, nova_divida, novo_limite, usuario),
            )
        conn.execute(
            "INSERT INTO emprestimos_pagos (usuario, data_hora, valor_puro, total_com_juros, parcelas, divida_restante, data_pagamento, valor_pago) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (usuario, loan["data_hora"], valor_puro, total_com_juros, loan["parcelas"], loan["divida_restante"], datetime.now().isoformat(), total_com_juros),
        )
        conn.execute(
            "INSERT INTO transacoes (usuario, tipo, valor, descricao, data_hora) VALUES (?, ?, ?, ?, ?)",
            (usuario, "Gasto", total_com_juros, f"Pagamento Empréstimo {loan_id}", datetime.now().isoformat()),
        )
        conn.execute("DELETE FROM emprestimos WHERE id = ?", (loan_id,))
    return True

def credit_developer_interest(valor_juros):
    if valor_juros <= 0:
        return
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE contas SET ganhos = ganhos + ? WHERE role = 'desenvolvedor'",
            (valor_juros,)
        )
        conn.execute(
            "INSERT INTO transacoes (usuario, tipo, valor, descricao, data_hora) VALUES (?, ?, ?, ?, ?)",
            ("Lucas", "Ganho", valor_juros, "Juros de Empréstimo", datetime.now().isoformat()),
        )

# Função auxiliar para avançar os meses nas datas de vencimento
def adicionar_meses(data_base, meses):
    ano = data_base.year + (data_base.month + meses - 1) // 12
    mes = (data_base.month + meses - 1) % 12 + 1
    dia = min(data_base.day, [31, 29 if ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1])
    return datetime(ano, mes, dia)

def formatar_data_br(data_iso):
    """Formata data ISO para o padrão brasileiro: DD/MM/YY"""
    try:
        if isinstance(data_iso, str):
            dt = datetime.fromisoformat(data_iso)
        else:
            dt = data_iso
        return dt.strftime("%d/%m/%y")
    except:
        return data_iso

def meu_banco_digital():
    init_database()
    st.set_page_config(page_title="Banco Ilha do Governador", page_icon="🏦", layout="wide")
    st.title("🏦 Banco | Ilha do Governador")

    if "logado" not in st.session_state:
        st.session_state.logado = False
    if "usuario_atual" not in st.session_state:
        st.session_state.usuario_atual = None
    if "limite_padrao" not in st.session_state:
        st.session_state.limite_padrao = 2000.0

    if not st.session_state.logado:
        col_cen, col_box, col_dir = st.columns([1, 2, 1])
        with col_box:
            st.markdown("### 🔒 Controle de Acesso")
            aba_login, aba_cadastro = st.tabs(["🔑 Entrar", "📝 Criar Nova Conta"])

            with aba_login:
                u_input = st.text_input("Usuário", key="l_user").strip()
                s_input = st.text_input("Senha", type="password", key="l_pass").strip()

                if st.button("Acessar Banco", use_container_width=True, type="primary", key="btn_executar_login"):
                    if authenticate_user(u_input, s_input):
                        st.session_state.logado = True
                        st.session_state.usuario_atual = u_input
                        st.success("Login realizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos!")

            with aba_cadastro:
                n_user = st.text_input("Nome de Usuário", key="c_user").strip()
                n_pass = st.text_input("Senha de Acesso", type="password", key="c_pass").strip()
                c_pass = st.text_input("Confirme a Senha", type="password", key="c_cpass").strip()
                if st.button("Cadastrar no Sistema", use_container_width=True, key="btn_executar_cadastro"):
                    if not n_user or not n_pass:
                        st.warning("Preencha todos os campos!")
                    elif fetch_user(n_user):
                        st.error("Este usuário já existe!")
                    elif n_pass != c_pass:
                        st.error("As senhas não batem!")
                    else:
                        create_user_in_db(n_user, n_pass, "usuario", st.session_state.limite_padrao)
                        st.success("Conta criada com sucesso! Vá para a aba 'Entrar'.")

    # 3. PAINEL DO BANCO (APÓS LOGIN)
    else:
        user = st.session_state.usuario_atual
        dados_user = fetch_user(user)
        df_users = fetch_users_df()
        df_transacoes = fetch_transactions_df()
        df_loans = fetch_loans_df()
        df_paid_loans = fetch_paid_loans_df()
        df_transacoes_user = fetch_transactions_df(user)
        df_loans_user = fetch_loans_df(user)

        st.title(f"💰 Olá, {user}!")
        
        if st.sidebar.button("Sair do Sistema"):
            st.session_state.logado = False
            st.session_state.usuario_atual = None
            st.rerun()

        if dados_user["role"] == "desenvolvedor":
            st.sidebar.success("⚡ Administrador Ativo")
            st.header("🛠️ Painel de Controle Admin")
            saldo_desenvolvedor = dados_user["ganhos"] - dados_user["gastos"]
            st.metric("💼 Saldo do Desenvolvedor", f"R$ {saldo_desenvolvedor:,.2f}")

            tab_usuarios, tab_transacoes_adm, tab_emprestimos_adm = st.tabs(["👥 Gerenciar Clientes", "📊 Extrato Geral", "🏦 Créditos Ativos"])

            with tab_usuarios:
                st.markdown("##### Todos os Usuários Registrados")
                st.dataframe(df_users, use_container_width=True)

                st.markdown("#### ⚙️ Alterar Limite de Crédito")
                lista_clientes = df_users[df_users["role"] != "desenvolvedor"]["usuario"].tolist()
                if lista_clientes:
                    u_limite = st.selectbox("Selecione o Cliente:", lista_clientes, key="sel_u_limite")
                    usuario_linha = fetch_user(u_limite)
                    lim_atual = float(usuario_linha["limite_emprestimo"])
                    novo_limite = st.number_input(f"Novo Limite (Atual: R$ {lim_atual:,.2f}):", min_value=0.0, step=100.0, value=lim_atual, key="novo_limite")
                    if st.button("Aplicar Novo Limite", type="primary", key="btn_mudar_limite_adm"):
                        update_user_in_db(u_limite, limite_emprestimo=novo_limite)
                        st.success("Limite modificado com sucesso!")
                        st.rerun()
                else:
                    st.info("Nenhum cliente cadastrado.")

                st.markdown("#### 🔧 Ajustar Saldo do Desenvolvedor")
                dev_users = df_users[df_users["role"] == "desenvolvedor"]
                if not dev_users.empty:
                    dev_usuario = dev_users.iloc[0]["usuario"]
                    dev_ganhos = float(dev_users.iloc[0]["ganhos"])
                    dev_gastos = float(dev_users.iloc[0]["gastos"])
                    novo_dev_ganhos = st.number_input("Ganhos do Desenvolvedor", min_value=0.0, step=10.0, value=dev_ganhos, key="dev_ganhos")
                    novo_dev_gastos = st.number_input("Gastos do Desenvolvedor", min_value=0.0, step=10.0, value=dev_gastos, key="dev_gastos")
                    if st.button("Aplicar Ajuste de Saldo", key="btn_ajustar_saldo_dev"):
                        update_user_in_db(dev_usuario, ganhos=novo_dev_ganhos, gastos=novo_dev_gastos)
                        st.success("Saldo do desenvolvedor ajustado com sucesso!")
                        st.rerun()
                else:
                    st.warning("Nenhum desenvolvedor cadastrado para ajuste.")

                st.markdown("#### ❌ Excluir Conta de Cliente")
                if lista_clientes:
                    user_excluir = st.selectbox("Selecione a conta para deletar:", lista_clientes, key="sel_u_excluir")
                    if st.button("Confirmar Exclusão Definitiva", key="btn_deletar_conta_adm"):
                        delete_user(user_excluir)
                        st.success("Conta removida de forma permanente!")
                        st.rerun()
                else:
                    st.info("Nenhuma conta disponível para exclusão.")

            with tab_transacoes_adm:
                st.markdown("##### 📋 Extrato Geral do Sistema")
                if not df_transacoes.empty:
                    # Formatar datas
                    df_transacoes_display = df_transacoes.copy()
                    df_transacoes_display["data_hora"] = df_transacoes_display["data_hora"].apply(formatar_data_br)
                    # Reorganizar colunas para melhor visualização
                    df_display = df_transacoes_display[["id", "data_hora", "usuario", "tipo", "descricao", "valor"]].rename(
                        columns={
                            "id": "ID",
                            "data_hora": "Data",
                            "usuario": "Usuário",
                            "tipo": "Tipo",
                            "descricao": "Descrição",
                            "valor": "Valor (R$)"
                        }
                    ).sort_values("Data", ascending=False)
                    st.dataframe(df_display, use_container_width=True)

                    st.markdown("##### 🗑️ Excluir Transação")
                    transacoes_ids = df_transacoes_display["id"].tolist()
                    selecionado_tx = st.selectbox("Selecione o ID da transação:", transacoes_ids, key="sel_tx_adm")
                    if st.button("Excluir Transação", key="btn_excluir_tx_adm"):
                        delete_transaction(selecionado_tx)
                        st.success("Transação excluída com sucesso.")
                        st.rerun()
                else:
                    st.info("Nenhuma transação registrada no sistema.")

            with tab_emprestimos_adm:
                st.markdown("##### 💳 Créditos Ativos do Sistema")
                if not df_loans.empty:
                    # Formatar datas
                    df_loans_display = df_loans.copy()
                    df_loans_display["data_hora"] = df_loans_display["data_hora"].apply(formatar_data_br)
                    # Reorganizar colunas
                    df_display = df_loans_display[["id", "data_hora", "usuario", "valor_puro", "total_com_juros", "parcelas", "divida_restante"]].rename(
                        columns={
                            "id": "ID",
                            "data_hora": "Data Contratação",
                            "usuario": "Usuário",
                            "valor_puro": "Valor Recebido (R$)",
                            "total_com_juros": "Total com Juros (R$)",
                            "parcelas": "Prazo (Meses)",
                            "divida_restante": "Dívida Atual (R$)"
                        }
                    ).sort_values("Data Contratação", ascending=False)
                    st.dataframe(df_display, use_container_width=True)

                    st.markdown("##### ✅ Marcar Empréstimo como Pago")
                    emprestimos_ids = df_loans_display["id"].tolist()
                    selecionado_loan = st.selectbox("Selecione o ID do empréstimo:", emprestimos_ids, key="sel_loan_adm")
                    if st.button("Marcar como Pago", key="btn_pagar_loan_adm"):
                        if pay_loan(selecionado_loan):
                            st.success("Empréstimo marcado como pago. O valor foi debitado do cliente.")
                        else:
                            st.error("Não foi possível processar o pagamento do empréstimo.")
                        st.rerun()

                    if st.button("Cancelar Empréstimo (tornar inexistente)", key="btn_cancelar_loan_adm"):
                        if cancel_loan(selecionado_loan):
                            st.success("Empréstimo cancelado como inexistente. Ajustei saldo do cliente e do desenvolvedor.")
                        else:
                            st.error("Não foi possível cancelar o empréstimo.")
                        st.rerun()
                else:
                    st.info("Nenhum empréstimo ativo no sistema.")

                st.divider()
                st.markdown("##### 📁 Histórico de Empréstimos Pagos")
                if not df_paid_loans.empty:
                    df_paid_display = df_paid_loans.copy()
                    df_paid_display["data_hora"] = df_paid_display["data_hora"].apply(formatar_data_br)
                    df_paid_display["data_pagamento"] = df_paid_display["data_pagamento"].apply(formatar_data_br)
                    df_paid_table = df_paid_display[["data_hora", "data_pagamento", "usuario", "valor_puro", "total_com_juros", "parcelas", "valor_pago"]].rename(
                        columns={
                            "data_hora": "Data Contratação",
                            "data_pagamento": "Data Pagamento",
                            "usuario": "Usuário",
                            "valor_puro": "Valor Recebido (R$)",
                            "total_com_juros": "Total com Juros (R$)",
                            "parcelas": "Prazo (Meses)",
                            "valor_pago": "Valor Pago (R$)"
                        }
                    ).sort_values("Data Pagamento", ascending=False)
                    st.dataframe(df_paid_table, use_container_width=True)
                else:
                    st.info("Nenhum empréstimo pago registrado.")
        else:
            ganhos_totais = pd.to_numeric(df_transacoes_user[df_transacoes_user["tipo"] == "Ganho"]["valor"]).sum() if not df_transacoes_user.empty else 0.0
            gastos_totais = pd.to_numeric(df_transacoes_user[df_transacoes_user["tipo"] == "Gasto"]["valor"]).sum() if not df_transacoes_user.empty else 0.0
            divida_atual = pd.to_numeric(df_loans_user["divida_restante"]).sum() if not df_loans_user.empty else 0.0
            saldo_real = dados_user["ganhos"] - dados_user["gastos"]
            limite_disponivel = max(0.0, dados_user["limite_emprestimo"])

            st.markdown(f"### 👋 Olá, **{user}**")
            col1, col2, col3 = st.columns(3)
            col1.metric("🟢 SALDO DISPONÍVEL", f"R$ {saldo_real:,.2f}")
            col2.metric("🔴 DÍVIDA CONSOLIDADA", f"R$ {divida_atual:,.2f}")
            col3.metric("🔵 LINHA DE CRÉDITO", f"R$ {limite_disponivel:,.2f}")

            st.divider()
            tab_movimentar, tab_analytics, tab_credito = st.tabs(["💸 Nova Transação", "📊 Resumo por Categorias", "🏛️ Empréstimos"])

            with tab_movimentar:
                col_ganho, col_gasto = st.columns(2)
                with col_ganho:
                    st.markdown("#### 📈 Lançar Entrada")
                    area_ganho = st.text_input("Classificação (Ex: Salário, Mesada)", key="a_ganho").strip().capitalize()
                    val_ganho = st.number_input("Valor Recebido (R$)", min_value=0.0, step=10.0, key="v_ganho")
                    if st.button("Registrar Entrada", use_container_width=True, key="btn_salvar_entrada_cli"):
                        if val_ganho > 0 and area_ganho:
                            add_transaction(user, "Ganho", val_ganho, area_ganho)
                            update_user_in_db(user, ganhos=dados_user["ganhos"] + val_ganho)
                            st.success("Ganho registrado com sucesso!")
                            st.rerun()
                        else:
                            st.warning("Informe valor e classificação.")

                with col_gasto:
                    st.markdown("#### 📉 Lançar Saída")
                    area_gasto = st.text_input("Classificação (Ex: Roupa, Lanche)", key="a_gasto").strip().capitalize()
                    val_gasto = st.number_input("Valor Gasto (R$)", min_value=0.0, step=10.0, key="v_gasto")
                    if st.button("Registrar Saída", use_container_width=True, key="btn_salvar_saida_cli"):
                        if val_gasto > 0 and area_gasto:
                            add_transaction(user, "Gasto", val_gasto, area_gasto)
                            update_user_in_db(user, gastos=dados_user["gastos"] + val_gasto)
                            st.success("Gasto registrado com sucesso!")
                            st.rerun()
                        else:
                            st.warning("Informe valor e classificação.")

            with tab_analytics:
                st.subheader("📊 Valores Agrupados")
                if not df_transacoes_user.empty:
                    df_ganhos = df_transacoes_user[df_transacoes_user["tipo"] == "Ganho"]
                    df_gastos = df_transacoes_user[df_transacoes_user["tipo"] == "Gasto"]
                    col_ga1, col_ga2 = st.columns(2)
                    with col_ga1:
                        st.markdown("##### Ganhos por Categoria")
                        if not df_ganhos.empty:
                            st.table(df_ganhos.groupby("descricao")["valor"].sum().reset_index().rename(columns={"descricao": "Categoria", "valor": "Total (R$)"}))
                        else:
                            st.info("Sem entradas registradas.")
                    with col_ga2:
                        st.markdown("##### Gastos por Categoria")
                        if not df_gastos.empty:
                            st.table(df_gastos.groupby("descricao")["valor"].sum().reset_index().rename(columns={"descricao": "Categoria", "valor": "Total (R$)"}))
                        else:
                            st.info("Sem gastos registrados.")
                    st.divider()
                    st.markdown("##### 📋 Extrato Detalhado (Todas as Transações)")
                    # Formatar datas no extrato do usuário
                    df_extrato = df_transacoes_user.copy()
                    df_extrato["data_hora"] = df_extrato["data_hora"].apply(formatar_data_br)
                    df_extrato_display = df_extrato[["data_hora", "tipo", "descricao", "valor"]].rename(
                        columns={
                            "data_hora": "Data",
                            "tipo": "Tipo",
                            "descricao": "Categoria",
                            "valor": "Valor (R$)"
                        }
                    ).sort_values("Data", ascending=False)
                    st.dataframe(df_extrato_display, use_container_width=True)
                else:
                    st.info("Nenhuma movimentação para exibir.")

            with tab_credito:
                st.subheader("🏛️ Crédito Apex")
                st.write(f"Limite disponível: **R$ {limite_disponivel:,.2f}**")
                v_sol = st.number_input("Valor Solicitado (R$):", min_value=0.0, max_value=limite_disponivel, step=50.0, key="v_sol")
                if v_sol > 0:
                    dados_simulacao = []
                    for parcelas in range(1, 13):
                        total_juros = float(v_sol * ((1 + 0.06) ** parcelas))
                        valor_parcela = total_juros / parcelas
                        dados_simulacao.append({
                            "Parcelas": f"{parcelas}x",
                            "Valor da Parcela": f"R$ {valor_parcela:,.2f}",
                            "Total com Juros": f"R$ {total_juros:,.2f}"
                        })
                    st.table(pd.DataFrame(dados_simulacao))
                    p_sol = st.number_input("Parcelas desejadas (1 a 12):", min_value=1, max_value=12, value=1, step=1, key="p_sol")
                    total_final_escolhido = float(v_sol * ((1 + 0.06) ** p_sol))
                    if st.button("Contratar Empréstimo Apex", type="primary", use_container_width=True, key="btn_pegar_emprestimo_cli"):
                        update_user_in_db(
                            user,
                            ganhos=dados_user["ganhos"] + v_sol,
                            divida_emprestimo=dados_user["divida_emprestimo"] + total_final_escolhido,
                            limite_emprestimo=max(0.0, dados_user["limite_emprestimo"] - v_sol),
                        )
                        create_loan_in_db(user, v_sol, total_final_escolhido, int(p_sol))
                        add_transaction(user, "Empréstimo", v_sol, f"Empréstimo em {p_sol}x")
                        juros_aplicados = total_final_escolhido - float(v_sol)
                        credit_developer_interest(juros_aplicados)
                        st.success("Crédito liberado e salvo permanentemente!")
                        st.rerun()

                st.divider()
                st.markdown("#### 📊 Seus Contratos de Empréstimos Ativos")
                if not df_loans_user.empty:
                    df_emprestimos = df_loans_user.copy()
                    df_emprestimos["data_hora"] = df_emprestimos["data_hora"].apply(formatar_data_br)
                    df_emprestimos_display = df_emprestimos[["data_hora", "valor_puro", "total_com_juros", "parcelas", "divida_restante"]].rename(
                        columns={
                            "data_hora": "Data Contratação",
                            "valor_puro": "Valor Recebido (R$)",
                            "total_com_juros": "Total com Juros (R$)",
                            "parcelas": "Prazo (Meses)",
                            "divida_restante": "Dívida Atual (R$)"
                        }
                    ).sort_values("Data Contratação", ascending=False)
                    st.dataframe(df_emprestimos_display, use_container_width=True)
                else:
                    st.info("Você não possui contratos de empréstimo ativos no momento.")

if __name__ == '__main__':
    import sys
    from streamlit.web import cli as stcli
    if not st.runtime.exists():
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
    else:
        meu_banco_digital()
