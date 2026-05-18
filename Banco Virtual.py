import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

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

# Função auxiliar para avançar os meses nas datas de vencimento
def adicionar_meses(data_base, meses):
    ano = data_base.year + (data_base.month + meses - 1) // 12
    mes = (data_base.month + meses - 1) % 12 + 1
    dia = min(data_base.day, [31, 29 if ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1])
    return datetime(ano, mes, dia)

def meu_banco_digital():
    init_database()

    if "limite_padrao_novos_usuarios" not in st.session_state:
        st.session_state.limite_padrao_novos_usuarios = 2000.0

    if "logado" not in st.session_state:
        st.session_state.logado = False
    if "usuario_atual" not in st.session_state:
        st.session_state.usuario_atual = None

    # 2. TELA DE ACESSO (LOGIN E CADASTRO)
    if not st.session_state.logado:
        st.title("🔒 Banco Pessoal - Controle de Acesso")
        aba_login, aba_cadastro = st.tabs(["Entrar", "Criar Nova Conta"])
        
        with aba_login:
            usuario_input = st.text_input("Usuário", key="login_user")
            senha_input = st.text_input("Senha", type="password", key="login_pass")
            if st.button("Entrar", use_container_width=True):
                if authenticate_user(usuario_input, senha_input):
                    st.session_state.logado = True
                    st.session_state.usuario_atual = usuario_input
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos!")
        
        with aba_cadastro:
            novo_usuario = st.text_input("Escolha um Nome de Usuário", key="cad_user")
            nova_senha = st.text_input("Escolha uma Senha", type="password", key="cad_pass")
            confirma_senha = st.text_input("Confirme a Senha", type="password", key="cad_conf_pass")
            if st.button("Criar Minha Conta", use_container_width=True):
                if not novo_usuario or not nova_senha:
                    st.warning("Preencha todos os campos!")
                elif fetch_user(novo_usuario):
                    st.error("Esse usuário já existe! Escolha outro nome.")
                elif nova_senha != confirma_senha:
                    st.error("As senhas não coincidem!")
                else:
                    limite_inicial = st.session_state.limite_padrao_novos_usuarios
                    create_user_in_db(novo_usuario, nova_senha, "usuario", limite_inicial)
                    st.success(f"Conta criada com sucesso com limite de R$ {limite_inicial:,.2f}!")

    # 3. PAINEL DO BANCO (APÓS LOGIN)
    else:
        user = st.session_state.usuario_atual
        dados_user = fetch_user(user)

        st.title(f"💰 Olá, {user}!")
        
        if st.sidebar.button("Sair do Sistema"):
            st.session_state.logado = False
            st.session_state.usuario_atual = None
            st.rerun()

        # --- VISÃO DO DESENVOLVEDOR ---
        if dados_user["role"] == "desenvolvedor":
            st.sidebar.markdown("---")
            st.sidebar.subheader("🛠️ Modo Desenvolvedor")
            novo_limite_config = st.sidebar.number_input("Limite para Novos Cadastros (R$)", min_value=0.0, value=st.session_state.limite_padrao_novos_usuarios, step=100.0)
            st.session_state.limite_padrao_novos_usuarios = novo_limite_config
            
            ver_painel = st.sidebar.checkbox("Monitorar Contas", value=True)
            if ver_painel:
                st.header("🖥️ Painel Geral (Dev)")
                
                # Tabela de monitoramento
                lista_contas = []
                usuarios_com_divida = [] # Lista auxiliar para o formulário de abatimento
                contas = fetch_all_users()
                
                if contas:
                    for dados in contas:
                        lista_contas.append({
                            "Usuário": dados['usuario'],
                            "Saldo": f"R$ {dados['ganhos'] - dados['gastos']:,.2f}",
                            "Ganhos": f"R$ {dados['ganhos']:,.2f}",
                            "Gastos": f"R$ {dados['gastos']:,.2f}",
                            "Limite Emprést.": f"R$ {dados['limite_emprestimo']:,.2f}",
                            "Dívida Atual": f"R$ {dados['divida_emprestimo']:,.2f}"
                        })
                        if dados['divida_emprestimo'] > 0:
                            usuarios_com_divida.append(dados['usuario'])
                    st.table(lista_contas)
                else:
                    st.info("Nenhuma conta cadastrada ainda.")
                
                # NOVO: FORMULÁRIO DE ABATIMENTO DE DÍVIDA (Apenas visível se alguém dever)
                st.subheader("🧮 Registrar Recebimento de Empréstimo")
                if usuarios_com_divida:
                    col_dev1, col_dev2 = st.columns(2)
                    with col_dev1:
                        user_pagando = st.selectbox("Qual cliente está pagando?", usuarios_com_divida)
                    with col_dev2:
                        cliente_atual = fetch_user(user_pagando)
                        divida_maxima = cliente_atual['divida_emprestimo']
                        valor_pago = st.number_input(f"Valor Pago por {user_pagando} (Máx R$ {divida_maxima:.2f})", min_value=0.0, max_value=divida_maxima, step=10.0, key="valor_pago")
                    
                    if st.button("Confirmar Abatimento", type="secondary", key="confirmar_abatimento"):
                        if valor_pago > 0:
                            valor_proporcional_sem_juros = valor_pago / 1.05
                            update_user_in_db(
                                user_pagando,
                                divida_emprestimo=cliente_atual['divida_emprestimo'] - valor_pago,
                                limite_emprestimo=cliente_atual['limite_emprestimo'] + valor_proporcional_sem_juros,
                            )
                            add_transaction(user_pagando, "pagamento_emprestimo", valor_pago, "Abatimento de dívida")
                            st.success(f"✅ Sucesso! R$ {valor_pago:.2f} foram abatidos da dívida de {user_pagando}.")
                            st.rerun()
                else:
                    st.info("Nenhum cliente possui dívidas ativas no momento.")
                    
                st.divider()

        # --- SEÇÃO FINANCEIRA DO USUÁRIO ---
        saldo_atual = dados_user["ganhos"] - dados_user["gastos"]
        
        col_s1, col_s2 = st.columns(2)
        col_s1.metric(label="Saldo Atual Disponível", value=f"R$ {saldo_atual:,.2f}")
        if dados_user["divida_emprestimo"] > 0:
            col_s2.metric(label="⚠️ Dívida de Empréstimo", value=f"R$ {dados_user['divida_emprestimo']:,.2f}", delta="Com 5% juros/parc.")
        else:
            col_s2.metric(label="👍 Situação de Empréstimo", value="Sem dívidas")

        col1, col2 = st.columns(2)
        col1.metric(label="📈 Total de Ganhos", value=f"R$ {dados_user['ganhos']:,.2f}")
        col2.metric(label="📉 Total de Gastos", value=f"R$ -{dados_user['gastos']:,.2f}", delta_color="inverse")

        st.divider()

        # --- FORMULÁRIOS PARA ADICIONAR DINHEIRO/GASTOS ---
        st.subheader("💵 Nova Movimentação")
        col_ganho, col_gasto = st.columns(2)
        
        with col_ganho:
            st.markdown("### Registrar Entrada")
            valor_ganho = st.number_input("Valor do Ganho (R$)", min_value=0.0, step=10.0, key="add_ganho")
            if st.button("Confirmar Depósito", key="confirmar_deposito"):
                if valor_ganho > 0:
                    update_user_in_db(user, ganhos=dados_user['ganhos'] + valor_ganho)
                    add_transaction(user, "deposito", valor_ganho, "Depósito de entrada")
                    st.success(f"R$ {valor_ganho:.2f} adicionados!")
                    st.rerun()

        with col_gasto:
            st.markdown("### Registrar Saída")
            valor_gasto = st.number_input("Valor do Gasto (R$)", min_value=0.0, step=10.0, key="add_gasto")
            if st.button("Confirmar Gasto", key="confirmar_gasto"):
                if valor_gasto > 0:
                    update_user_in_db(user, gastos=dados_user['gastos'] + valor_gasto)
                    add_transaction(user, "gasto", valor_gasto, "Registro de gasto")
                    st.success(f"Gasto de R$ {valor_gasto:.2f} registrado!")
                    st.rerun()

        st.divider()

        # --- SEÇÃO: SIMULADOR DE EMPRÉSTIMO PARCELADO ---
        st.subheader("🏦 Simulador de Empréstimo Parcelado")
        st.write(f"Seu limite disponível: **R$ {dados_user['limite_emprestimo']:,.2f}**")
        
        col_emp1, col_emp2 = st.columns(2)
        with col_emp1:
            valor_solicitado = st.number_input("Valor do Empréstimo (R$)", min_value=0.0, max_value=max(0.0, dados_user["limite_emprestimo"]), step=50.0, key="simular_emp")
        with col_emp2:
            qtd_parcelas = st.number_input("Quantidade de Parcelas (Máx 12x)", min_value=1, max_value=12, value=1, step=1)
        
        if valor_solicitado > 0:
            valor_base_parcela = valor_solicitado / qtd_parcelas
            valor_parcela_com_juros = valor_base_parcela * 1.05
            total_a_pagar = valor_parcela_com_juros * qtd_parcelas
            
            st.info(f"### 📊 Cronograma de Pagamento (Juros: 5% por parcela)")
            
            data_atual = datetime.now()
            cronograma = []
            for i in range(1, qtd_parcelas + 1):
                data_vencimento = adicionar_meses(data_atual, i)
                data_formatada = data_vencimento.strftime("%d/%m/%Y")
                cronograma.append({"Parcela": f"{i}x", "Vencimento": data_formatada, "Valor": f"R$ {valor_parcela_com_juros:,.2f}"})
            
            st.table(cronograma)
            st.warning(f"**Resumo do Contrato:** Você recebe **R$ {valor_solicitado:,.2f}** hoje e paga um total de **R$ {total_a_pagar:,.2f}**.")
            
            if st.button("Contratar Empréstimo", type="primary", key="contratar_emprestimo"):
                update_user_in_db(
                    user,
                    ganhos=dados_user['ganhos'] + valor_solicitado,
                    divida_emprestimo=dados_user['divida_emprestimo'] + total_a_pagar,
                    limite_emprestimo=dados_user['limite_emprestimo'] - valor_solicitado,
                )
                add_transaction(user, "emprestimo", valor_solicitado, f"Empréstimo contratado em {qtd_parcelas}x")
                st.success("🎉 Empréstimo contratado com sucesso!")
                st.rerun()

if __name__ == '__main__':
    import sys
    from streamlit.web import cli as stcli
    if not st.runtime.exists():
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
    else:
        meu_banco_digital()
