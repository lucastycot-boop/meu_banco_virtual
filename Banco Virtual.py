import streamlit as st
import pandas as pd
import json
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Configuração do Layout do Aplicativo
st.set_page_config(page_title="Apex Banco Digital", page_icon="🔱", layout="wide")

# Atualização automática a cada 3 segundos para sincronizar dados entre telas
st_autorefresh(interval=3000, key="datarefresh")

# --- CONEXÃO COM O STORAGE PERMANENTE DO STREAMLIT ---
# Inicializa a conexão interna de armazenamento seguro
try:
    conn = st.connection("storage", type="stlite")
except Exception:
    # Fallback caso o componente local precise de suporte
    conn = None

def carregar_dados_permanentes(chave, dados_iniciais):
    """Carrega os dados guardados na nuvem estável do Streamlit"""
    if conn and chave in conn:
        try:
            texto_salvo = conn[chave]
            return pd.read_json(texto_salvo, orient="records")
        except:
            pass
    return pd.DataFrame(dados_iniciais)

def salvar_dados_permanentes(chave, df):
    """Grava as alterações na nuvem estável para resistir ao Reboot"""
    if conn:
        texto_json = df.to_json(orient="records")
        conn[chave] = texto_json

# --- CARREGAMENTO DO BANCO DE DADOS (RESISTENTE A REBOOT) ---
df_contas = carregar_dados_permanentes("banco_contas", [{"usuario": "Lucas", "senha": "1702", "role": "desenvolvedor", "limite_emprestimo": 5000.0}])
df_transacoes = carregar_dados_permanentes("banco_transacoes", columns=["id", "usuario", "data", "mes_ano", "tipo", "area", "valor"])
df_emprestimos = carregar_dados_permanentes("banco_emprestimos", columns=["id", "usuario", "data", "valor_puro", "total_com_juros", "parcelas", "divida_restante"])

# Garante que as colunas essenciais existam caso venham vazias
if df_transacoes.empty:
    df_transacoes = pd.DataFrame(columns=["id", "usuario", "data", "mes_ano", "tipo", "area", "valor"])
if df_emprestimos.empty:
    df_emprestimos = pd.DataFrame(columns=["id", "usuario", "data", "valor_puro", "total_com_juros", "parcelas", "divida_restante"])

# Função auxiliar para manipulação de meses nas parcelas
def adicionar_meses(data_base, meses):
    ano = data_base.year + (data_base.month + meses - 1) // 12
    mes = (data_base.month + meses - 1) % 12 + 1
    dia = min(data_base.day, [31, 29 if ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1])
    return datetime(ano, mes, dia)

# Estilização visual em CSS para o modo Dark Premium
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #00ffcc; font-weight: bold; }
    div[data-testid="stMetricLabel"] { font-size: 14px; color: #a3a8b4; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_html=True)

def meu_banco_digital():
    global df_contas, df_transacoes, df_emprestimos
    st.title("🔱 Apex | Sistema Bancário Inteligente")

    if "logado" not in st.session_state: st.session_state.logado = False
    if "usuario_atual" not in st.session_state: st.session_state.usuario_atual = None
    if "limite_padrao" not in st.session_state: st.session_state.limite_padrao = 2000.0

    # --- TELA DE ACESSO (LOGIN / CADASTRO) ---
    if not st.session_state.logado:
        col_cen, col_box, col_dir = st.columns([1, 2, 1])
        with col_box:
            with st.container(border=True):
                st.subheader("🔒 Área de Autenticação")
                aba_login, aba_cadastro = st.tabs(["🔑 Acessar Conta", "📝 Abrir Nova Conta"])
                
                with aba_login:
                    u_input = st.text_input("Usuário", key="l_user")
                    s_input = st.text_input("Senha", type="password", key="l_pass")
                    if st.button("Entrar no Sistema", use_container_width=True, type="primary"):
                        rows = df_contas[df_contas["usuario"].astype(str).str.strip() == str(u_input).strip()]
                        if not rows.empty and str(rows.iloc[0]["senha"]) == str(s_input):
                            st.session_state.logado = True
                            st.session_state.usuario_atual = u_input
                            st.rerun()
                        else:
                            st.error("Usuário ou senha incorretos!")
                            
                with aba_cadastro:
                    n_user = st.text_input("Escolha um Usuário", key="c_user")
                    n_pass = st.text_input("Crie uma Senha", type="password", key="c_pass")
                    c_pass = st.text_input("Confirme a Senha", type="password", key="c_cpass")
                    if st.button("Finalizar Cadastro", use_container_width=True):
                        if not n_user or not n_pass: st.warning("Preencha todos os campos!")
                        elif n_user in df_contas["usuario"].astype(str).values: st.error("Este usuário já existe!")
                        elif n_pass != c_pass: st.error("As senhas não coincidem!")
                        else:
                            nova_c = pd.DataFrame([{"usuario": n_user, "senha": n_pass, "role": "usuario", "limite_emprestimo": float(st.session_state.limite_padrao)}])
                            df_contas = pd.concat([df_contas, nova_c], ignore_index=True)
                            salvar_dados_permanentes("banco_contas", df_contas)
                            st.success("Conta criada! Vá para a aba de Acesso.")
        return

    # CONFIGURAÇÃO DO USUÁRIO CONECTADO
    user = st.session_state.usuario_atual
    dados_user = df_contas[df_contas["usuario"] == user].iloc[0]

    # BARRA LATERAL
    st.sidebar.markdown(f"### 🚪 Operador: **{user}**")
    if st.sidebar.button("Sair do Sistema", type="destructive", use_container_width=True):
        st.session_state.logado = False
        st.session_state.usuario_atual = None
        st.rerun()

    # --- TELA GESTÃO DEV (MODO ADMINISTRADOR) ---
    if dados_user["role"] == "desenvolvedor":
        st.sidebar.success("⚡ Modo Administrador Ativo")
        st.header("🛠️ Central Administrativa de Controle")
        
        tab_usuarios, tab_transacoes_adm, tab_emprestimos_adm = st.tabs(["👥 Clientes Cadastrados", "📊 Auditoria de Caixa", "🏦 Painel de Crédito"])
        
        with tab_usuarios:
            st.subheader("Base de Clientes")
            st.dataframe(df_contas, use_container_width=True)
            
            with st.container(border=True):
                st.markdown("#### ⚙️ Ajuste Rápido de Limite de Empréstimo")
                lista_clientes = df_contas[df_contas["role"] != "desenvolvedor"]["usuario"].tolist()
                if lista_clientes:
                    u_limite = st.selectbox("Selecione o Cliente:", lista_clientes, key="sel_u_limite")
                    idx_u = df_contas[df_contas["usuario"] == u_limite].index[0]
                    limite_actual = float(df_contas.loc[idx_u, "limite_emprestimo"])
                    
                    novo_limite = st.number_input(f"Novo Limite (Atual: R$ {limite_actual:.2f}):", min_value=0.0, step=100.0, value=limite_actual)
                    if st.button("⚡ Aplicar Limite Instantaneamente", key="btn_limite", type="primary"):
                        df_contas.loc[idx_u, "limite_emprestimo"] = novo_limite
                        salvar_dados_permanentes("banco_contas", df_contas)
                        st.success(f"O limite de {u_limite} mudou para R$ {novo_limite:.2f}!")
                else:
                    st.info("Nenhum cliente cadastrado.")
            
            st.markdown("<br>", unsafe_html=True)
            with st.container(border=True):
                st.markdown("#### ❌ Encerrar Conta")
                if lista_clientes:
                    user_excluir = st.selectbox("Selecione o alvo:", lista_clientes, key="sel_u_excluir")
                    if st.button("Apagar Registro de Conta permanentemente", type="destructive"):
                        df_contas = df_contas[df_contas["usuario"] != user_excluir].reset_index(drop=True)
                        df_transacoes = df_transacoes[df_transacoes["usuario"] != user_excluir].reset_index(drop=True)
                        df_emprestimos = df_emprestimos[df_emprestimos["usuario"] != user_excluir].reset_index(drop=True)
                        salvar_dados_permanentes("banco_contas", df_contas)
                        salvar_dados_permanentes("banco_transacoes", df_transacoes)
                        salvar_dados_permanentes("banco_emprestimos", df_emprestimos)
                        st.success("Conta removida com sucesso!")
                        st.rerun()

        with tab_transacoes_adm:
            st.subheader("Histórico Geral do Sistema")
            st.dataframe(df_transacoes, use_container_width=True)

        with tab_emprestimos_adm:
            st.subheader("Contratos de Financiamento")
            st.dataframe(df_emprestimos, use_container_width=True)
        return

    # --- TELA DO CLIENTE (PAINEL PREMIUM) ---
    t_user = df_transacoes[df_transacoes["usuario"] == user] if not df_transacoes.empty else pd.DataFrame()
    ganhos_totais = t_user[t_user["tipo"] == "Ganho"]["valor"].sum() if not t_user.empty else 0.0
    gastos_totais = t_user[t_user["tipo"] == "Gasto"]["valor"].sum() if not t_user.empty else 0.0
    
    e_user = df_emprestimos[df_emprestimos["usuario"] == user] if not df_emprestimos.empty else pd.DataFrame()
    total_recebido_emprestimo = e_user["valor_puro"].sum() if not e_user.empty else 0.0
    divida_atual = e_user["divida_restante"].sum() if not e_user.empty else 0.0
    
    saldo_real = (ganhos_totais + total_recebido_emprestimo) - gastos_totais
    limite_disponivel = float(dados_user["limite_emprestimo"]) - total_recebido_emprestimo

    st.markdown(f"### 👋 Bem-vindo de volta, **{user}**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.metric("🟢 SALDO EM CONTA", f"R$ {saldo_real:,.2f}")
    with col2:
        with st.container(border=True):
            st.metric("🔴 DÍVIDAS ATIVAS", f"R$ {divida_atual:,.2f}")
    with col3:
        with st.container(border=True):
            st.metric("🔵 LIMITE DE CRÉDITO", f"R$ {max(0.0, limite_disponivel):,.2f}")

    st.divider()

    tab_movimentar, tab_analytics, tab_credito = st.tabs(["💸 Novo Lançamento", "📊 Resumo de Gastos por Área", "🏛️ Linha de Crédito"])

    with tab_movimentar:
        st.subheader("O que você deseja registrar agora?")
        c_ganho, c_gasto = st.columns(2)
        
        with c_ganho:
            with st.container(border=True):
                st.markdown("#### 📈 Registrar Recebimento / Ganho")
                area_ganho = st.text_input("Classificação (Ex: Salário, Vendas, Pix)", key="a_ganho").strip().capitalize()
                val_ganho = st.number_input("Valor (R$)", min_value=0.0, step=10.0, key="v_ganho")
                if st.button("Confirmar Entrada de Capital", use_container_width=True):
                    if val_ganho > 0 and area_ganho:
                        novo_id = int(df_transacoes["id"].max() + 1) if not df_transacoes.empty else 1
                        nova_t = pd.DataFrame([{
                            "id": novo_id, "usuario": user, "data": datetime.now().strftime("%d/%m/%Y"),
                            "mes_ano": datetime.now().strftime("%m/%Y"), "tipo": "Ganho", "area": area_ganho, "valor": val_ganho
                        }])
                        df_transacoes = pd.concat([df_transacoes, nova_t], ignore_index=True)
                        salvar_dados_permanentes("banco_transacoes", df_transacoes)
                        st.success("Entrada salva com sucesso!")
                        st.rerun()

        with c_gasto:
            with st.container(border=True):
                st.markdown("#### 📉 Registrar Pagamento / Gasto")
                area_gasto = st.text_input("Classificação (Ex: Roupa, Comida, Lazer)", key="a_gasto").strip().capitalize()
                val_gasto = st.number_input("Valor (R$)", min_value=0.0, step=10.0, key="v_gasto")
                if st.button("Confirmar Saída de Capital", use_container_width=True):
                    if val_gasto > 0 and area_gasto:
                        novo_id = int(df_transacoes["id"].max() + 1) if not df_transacoes.empty else 1
                        nova_t = pd.DataFrame([{
                            "id": novo_id, "usuario": user, "data": datetime.now().strftime("%d/%m/%Y"),
                            "mes_ano": datetime.now().strftime("%m/%Y"), "tipo": "Gasto", "area": area_gasto, "valor": val_gasto
                        }])
                        df_transacoes = pd.concat([df_transacoes, nova_t], ignore_index=True)
                        salvar_dados_permanentes("banco_transacoes", df_transacoes)
                        st.success("Gasto computado com sucesso!")
                        st.rerun()

    with tab_analytics:
        st.subheader("📊 Seus Valores Organizados por Classificação")
        
        if not t_user.empty:
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.markdown("#### 💸 Ganhos Totais Agrupados")
                df_ganhos = t_user[t_user["tipo"] == "Ganho"]
                if not df_ganhos.empty:
                    df_ganhos_agrupado = df_ganhos.groupby("area")["valor"].sum().reset_index()
                    df_ganhos_agrupado.columns = ["Classificação / Categoria", "Total Acumulado (R$)"]
                    st.table(df_ganhos_agrupado)
                else:
                    st.info("Nenhum ganho lançado.")

            with col_g2:
                st.markdown("#### 🛒 Gastos Totais Agrupados")
                df_gastos = t_user[t_user["tipo"] == "Gasto"]
                if not df_gastos.empty:
                    df_gastos_agrupado = df_gastos.groupby("area")["valor"].sum().reset_index()
                    df_gastos_agrupado.columns = ["Classificação / Categoria", "Total Gasto (R$)"]
                    st.table(df_gastos_agrupado)
                else:
                    st.info("Nenhum gasto lançado.")
                    
            st.divider()
            st.markdown("#### 🗒️ Linha do Tempo de Extrato (Individual)")
            st.dataframe(t_user[["data", "tipo", "area", "valor"]], use_container_width=True)
        else:
            st.info("Nenhuma movimentação realizada ainda nesta conta.")

    with tab_credito:
        st.subheader("🏛️ Simulador de Empréstimo Pessoal")
        st.write(f"Crédito Pré-Aprovado Disponível: **R$ {max(0.0, limite_disponivel):,.2f}**")
        
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                v_solicitado = st.number_input("Valor do Empréstimo (R$)", min_value=0.0, max_value=max(0.0, limite_disponivel), step=50.0)
            with c2:
                p_solicitadas = st.number_input("Quantidade de Parcelas:", min_value=1, max_value=12, value=1)
                
            if v_solicitado > 0:
                t_pagar = float(v_solicitado * ((1 + 0.05) ** p_solicitadas))
                v_parcela = t_pagar / p_solicitadas
                
                st.info(f"📊 **Resumo do Contrato:** {p_solicitadas}x de R$ {v_parcela:,.2f} | Total Pago no Fim: R$ {t_pagar:,.2f} (Juros de 5% p/ parcela)")
                
                if st.button("Confirmar e Pegar Crédito", type="primary", use_container_width=True):
                    novo_id_emp = int(df_emprestimos["id"].max() + 1) if not df_emprestimos.empty else 1
                    novo_emp = pd.DataFrame([{
                        "id": novo_id_emp, "usuario": user, "data": datetime.now().strftime("%d/%m/%Y"),
                        "valor_puro": v_solicitado, "total_com_juros": t_pagar, "parcelas": int(p_solicitadas), "divida_restante": t_pagar
                    }])
                    df_emprestimos = pd.concat([df_emprestimos, novo_emp], ignore_index=True)
                    salvar_dados_permanentes("banco_emprestimos", df_emprestimos)
                    st.success("Dinheiro enviado para sua conta com sucesso!")
                    st.rerun()

if __name__ == '__main__':
    meu_banco_digital()
