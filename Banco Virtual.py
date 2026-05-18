import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. Configuração do Layout
st.set_page_config(
    page_title="Apex Banco Digital", 
    page_icon="🔱", 
    layout="wide"
)

# 2. Conexão com o Google Sheets (Banco de Dados na Nuvem)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    conn = None

def carregar_dados_nuvem(aba, lista_inicial):
    if conn:
        try:
            df = conn.read(worksheet=aba)
            if df.empty:
                return pd.DataFrame(columns=lista_inicial)
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=lista_inicial)

def salvar_dados_nuvem(aba, df):
    if conn:
        try:
            df_salvar = df.dropna(how='all')
            conn.update(worksheet=aba, data=df_salvar)
        except Exception as e:
            st.error(f"Erro ao salvar na nuvem: {e}")

# 3. Sincronização Inicial Inteligente
if "df_contas" not in st.session_state:
    st.session_state.df_contas = carregar_dados_nuvem("contas", ["usuario", "senha", "role", "limite_emprestimo"])
    if st.session_state.df_contas.empty:
        st.session_state.df_contas = pd.DataFrame([{"usuario": "Lucas", "senha": "1702", "role": "desenvolvedor", "limite_emprestimo": 5000.0}])

if "df_transacoes" not in st.session_state:
    st.session_state.df_transacoes = carregar_dados_nuvem("transacoes", ["id", "usuario", "data", "mes_ano", "tipo", "area", "valor"])

if "df_emprestimos" not in st.session_state:
    st.session_state.df_emprestimos = carregar_dados_nuvem("emprestimos", ["id", "usuario", "data", "valor_puro", "total_com_juros", "parcelas", "divida_restante"])


def meu_banco_digital():
    df_contas = st.session_state.df_contas
    df_transacoes = st.session_state.df_transacoes
    df_emprestimos = st.session_state.df_emprestimos
    
    st.title("🔱 Apex | Sistema Bancário Inteligente")

    if "logado" not in st.session_state: 
        st.session_state.logado = False
    if "usuario_atual" not in st.session_state: 
        st.session_state.usuario_atual = None
    if "limite_padrao" not in st.session_state: 
        st.session_state.limite_padrao = 2000.0

    # --- TELA 1: ACESSO E LOGON ---
    if not st.session_state.logado:
        col_cen, col_box, col_dir = st.columns([1, 2, 1])
        with col_box:
            with st.container(border=True):
                st.subheader("🔒 Controle de Acesso")
                aba_login, aba_cadastro = st.tabs(["🔑 Entrar", "📝 Criar Nova Conta"])
                
                with aba_login:
                    u_input = st.text_input("Usuário", key="l_user").strip()
                    s_input = st.text_input("Senha", type="password", key="l_pass").strip()
                    if st.button("Acessar Banco", use_container_width=True, type="primary", key="btn_executar_login"):
                        rows = df_contas[df_contas["usuario"].astype(str).str.strip() == str(u_input)]
                        if not rows.empty and str(rows.iloc[0]["senha"]).strip() == str(s_input):
                            st.session_state.logado = True
                            st.session_state.usuario_atual = u_input
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
                        elif n_user in df_contas["usuario"].astype(str).values: 
                            st.error("Este usuário já existe!")
                        elif n_pass != c_pass: 
                            st.error("As senhas não batem!")
                        else:
                            nova_c = pd.DataFrame([{"usuario": n_user, "senha": n_pass, "role": "usuario", "limite_emprestimo": float(st.session_state.limite_padrao)}])
                            st.session_state.df_contas = pd.concat([df_contas, nova_c], ignore_index=True)
                            
                            salvar_dados_nuvem("contas", st.session_state.df_contas)
                            st.success("Conta criada com sucesso! Vá para a aba 'Entrar'.")
        return

    # --- TELA 2: PAINEL RESTRITO ---
    user = st.session_state.usuario_atual
    dados_user = df_contas[df_contas["usuario"] == user].iloc[0]

    c_perfil, c_logout = st.columns([5, 1])
    with c_perfil:
        st.markdown(f"👤 Conectado como: **{user}**")
    with c_logout:
        # CORREÇÃO: Removida a chave estática conflitante do botão de logout
        if st.button("🚪 Sair do Sistema", use_container_width=True):
            st.session_state.logado = False
            st.session_state.usuario_atual = None
            st.rerun()

    st.divider()

    # --- ROTA: ADMINISTRADOR ---
    if dados_user["role"] == "desenvolvedor":
        st.sidebar.success("⚡ Administrador Ativo")
        st.header("🛠️ Painel de Controle Admin")
        
        tab_usuarios, tab_transacoes_adm, tab_emprestimos_adm = st.tabs(["👥 Gerenciar Clientes", "📊 Extrato Geral", "🏦 Créditos Ativos"])
        
        with tab_usuarios:
            st.markdown("##### Todos os Usuários Registrados")
            st.dataframe(df_contas, use_container_width=True)
            
            with st.container(border=True):
                st.markdown("#### ⚙️ Alterar Limite de Crédito")
                lista_clientes = df_contas[df_contas["role"] != "desenvolvedor"]["usuario"].tolist()
                if lista_clientes:
                    u_limite = st.selectbox("Selecione o Cliente:", lista_clientes, key="sel_u_limite")
                    idx_u = df_contas[df_contas["usuario"] == u_limite].index[0]
                    lim_atual = float(df_contas.loc[idx_u, "limite_emprestimo"])
                    
                    novo_limite = st.number_input(f"Novo Limite (Atual: R$ {lim_atual:.2f}):", min_value=0.0, step=100.0, value=lim_atual)
                    if st.button("Aplicar Novo Limite", type="primary", key="btn_mudar_limite_adm"):
                        df_contas.loc[idx_u, "limite_emprestimo"] = novo_limite
                        st.session_state.df_contas = df_contas
                        salvar_dados_nuvem("contas", df_contas)
                        st.success("Limite modificado na nuvem!")
                        st.rerun()
                else:
                    st.info("Nenhum cliente cadastrado.")
            
            # CORREÇÃO: Substituído markdown de quebra de linha por st.html para evitar o TypeError
            st.html("<br>")
            
            with st.container(border=True):
                st.markdown("#### ❌ Excluir Conta de Cliente")
                if lista_clientes:
                    user_excluir = st.selectbox("Selecione a conta para deletar:", lista_clientes, key="sel_u_excluir")
                    if st.button("Confirmar Exclusão Definitiva", key="btn_deletar_conta_adm"):
                        st.session_state.df_contas = df_contas[df_contas["usuario"] != user_excluir].reset_index(drop=True)
                        st.session_state.df_transacoes = df_transacoes[df_transacoes["usuario"] != user_excluir].reset_index(drop=True)
                        st.session_state.df_emprestimos = df_emprestimos[df_emprestimos["usuario"] != user_excluir].reset_index(drop=True)
                        
                        salvar_dados_nuvem("contas", st.session_state.df_contas)
                        salvar_dados_nuvem("transacoes", st.session_state.df_transacoes)
                        salvar_dados_nuvem("emprestimos", st.session_state.df_emprestimos)
                        st.success("Conta removida com sucesso!")
                        st.rerun()

        with tab_transacoes_adm:
            st.dataframe(df_transacoes, use_container_width=True)

        with tab_emprestimos_adm:
            st.dataframe(df_emprestimos, use_container_width=True)

    else:
        # --- ROTA: CLIENTE ---
        t_user = df_transacoes[df_transacoes["usuario"] == user] if not df_transacoes.empty else pd.DataFrame()
        ganhos_totais = pd.to_numeric(t_user[t_user["tipo"] == "Ganho"]["valor"]).sum() if not t_user.empty else 0.0
        gastos_totais = pd.to_numeric(t_user[t_user["tipo"] == "Gasto"]["valor"]).sum() if not t_user.empty else 0.0
        
        e_user = df_emprestimos[df_emprestimos["usuario"] == user] if not df_emprestimos.empty else pd.DataFrame()
        total_recebido_emprestimo = pd.to_numeric(e_user["valor_puro"]).sum() if not e_user.empty else 0.0
        divida_atual = pd.to_numeric(e_user["divida_restante"]).sum() if not e_user.empty else 0.0
        
        saldo_real = (ganhos_totais + total_recebido_emprestimo) - gastos_totais
        limite_disponivel = float(dados_user["limite_emprestimo"]) - total_recebido_emprestimo

        st.markdown(f"### 👋 Olá, **{user}**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            with st.container(border=True):
                st.metric("🟢 SALDO DISPONÍVEL", f"R$ {saldo_real:,.2f}")
        with col2:
            with st.container(border=True):
                st.metric("🔴 DÍVIDA CONSOLIDADA", f"R$ {divida_atual:,.2f}")
        with col3:
            with st.container(border=True):
                st.metric("🔵 LINHA DE CRÉDITO", f"R$ {max(0.0, limite_disponivel):,.2f}")

        st.divider()

        tab_movimentar, tab_analytics, tab_credito = st.tabs(["💸 Nova Transação", "📊 Resumo por Categorias", "🏛️ Empréstimos"])

        with tab_movimentar:
            c_ganho, c_gasto = st.columns(2)
            with c_ganho:
                with st.container(border=True):
                    st.markdown("#### 📈 Lançar Entrada (Ganho/Pix)")
                    area_ganho = st.text_input("Classificação (Ex: Salário, Mesada)", key="a_ganho").strip().capitalize()
                    val_ganho = st.number_input("Valor Recebido (R$)", min_value=0.0, step=10.0, key="v_ganho")
                    if st.button("Registrar Entrada", use_container_width=True, key="btn_salvar_entrada_cli"):
                        if val_ganho > 0 and area_ganho:
                            novo_id = int(df_transacoes["id"].max() + 1) if not df_transacoes.empty else 1
                            nova_t = pd.DataFrame([{
                                "id": novo_id, "usuario": user, "data": datetime.now().strftime("%d/%m/%Y"),
                                "mes_ano": datetime.now().strftime("%m/%Y"), "tipo": "Ganho", "area": area_ganho, "valor": val_ganho
                            }])
                            st.session_state.df_transacoes = pd.concat([df_transacoes, nova_t], ignore_index=True)
                            salvar_dados_nuvem("transacoes", st.session_state.df_transacoes)
                            st.success("Ganho registrado!")
                            st.rerun()

            with c_gasto:
                with st.container(border=True):
                    st.markdown("#### 📉 Lançar Saída (Gasto/Compra)")
                    area_gasto = st.text_input("Classificação (Ex: Roupa, Lanche)", key="a_gasto").strip().capitalize()
                    val_gasto = st.number_input("Valor Gasto (R$)", min_value=0.0, step=10.0, key="v_gasto")
                    if st.button("Registrar Saída", use_container_width=True, key="btn_salvar_saida_cli"):
                        if val_gasto > 0 and area_gasto:
                            novo_id = int(df_transacoes["id"].max() + 1) if not df_transacoes.empty else 1
                            nova_t = pd.DataFrame([{
                                "id": novo_id, "usuario": user, "data": datetime.now().strftime("%d/%m/%Y"),
                                "mes_ano": datetime.now().strftime("%m/%Y"), "tipo": "Gasto", "area": area_gasto, "valor": val_gasto
                            }])
                            st.session_state.df_
