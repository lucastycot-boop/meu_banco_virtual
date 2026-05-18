import streamlit as st
import pandas as pd
from datetime import datetime

# 1. Configuração Básica de Layout
st.set_page_config(
    page_title="Apex Banco Digital", 
    page_icon="🔱", 
    layout="wide"
)

# 2. Ponte de Dados Permanente
try:
    conn = st.connection("storage", type="stlite")
except Exception:
    conn = None

def carregar_dados_permanentes(chave, lista_inicial):
    if conn and chave in conn:
        try:
            texto_salvo = conn[chave]
            return pd.read_json(texto_salvo, orient="records")
        except:
            pass
    return pd.DataFrame(lista_inicial)

def salvar_dados_permanentes(chave, df):
    if conn:
        try:
            texto_json = df.to_json(orient="records")
            conn[chave] = texto_json
        except:
            pass

# 3. Inicialização dos Bancos de Dados
df_contas = carregar_dados_permanentes("banco_contas", [{"usuario": "Lucas", "senha": "1702", "role": "desenvolvedor", "limite_emprestimo": 5000.0}])

df_transacoes = carregar_dados_permanentes("banco_transacoes", [])
if df_transacoes.empty:
    df_transacoes = pd.DataFrame(columns=["id", "usuario", "data", "mes_ano", "tipo", "area", "valor"])

df_emprestimos = carregar_dados_permanentes("banco_emprestimos", [])
if df_emprestimos.empty:
    df_emprestimos = pd.DataFrame(columns=["id", "usuario", "data", "valor_puro", "total_com_juros", "parcelas", "divida_restante"])

def meu_banco_digital():
    global df_contas, df_transacoes, df_emprestimos
    
    st.title("🔱 Apex | Sistema Bancário Inteligente")

    # Inicialização segura de variáveis de sessão
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
                            df_contas = pd.concat([df_contas, nova_c], ignore_index=True)
                            salvar_dados_permanentes("banco_contas", df_contas)
                            st.success("Conta criada! Vá para a aba Entrar.")
        return

    # --- TELA 2: PAINEL RESTRITO (LOGADO) ---
    user = st.session_state.usuario_atual
    dados_user = df_contas[df_contas["usuario"] == user].iloc[0]

    # Cabeçalho Principal com perfil e botão de desconexão (Sem type="destructive")
    c_perfil, c_logout = st.columns([5, 1])
    with c_perfil:
        st.markdown(f"👤 Conectado como: **{user}**")
    with c_logout:
        if st.button("🚪 Sair do Sistema", use_container_width=True, key="btn_logout_linear_topo"):
            st.session_state.logado = False
            st.session_state.usuario_atual = None
            st.rerun()

    st.divider()

    # Divisão de rotas limpa entre Administrador e Cliente Comum
    if dados_user["role"] == "desenvolvedor":
        st.sidebar.success("⚡ Administrador Ativo")
        st.header("🛠️ Painel de Controle Admin")
        
        tab_usuarios, tab_transacoes_adm, tab_emprestimos_adm = st.tabs(["👥 Gerenciar Clientes", "📊 Extrato Geral", "🏦 Créditos Ativos"])
        
        with tab_usuarios:
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
                        salvar_dados_permanentes("banco_contas", df_contas)
                        st.success("Limite modificado com sucesso!")
                else:
                    st.info("Nenhum cliente cadastrado.")
            
            st.markdown("<br>", unsafe_html=True)
            with st.container(border=True):
                st.markdown("#### ❌ Excluir Conta de Cliente")
                if lista_clientes:
                    user_excluir = st.selectbox("Selecione a conta para deletar:", lista_clientes, key="sel_u_excluir")
                    # Removido o type="destructive" daqui também!
                    if st.button("Confirmar Exclusão Definitiva", key="btn_deletar_conta_adm"):
                        df_contas = df_contas[df_contas["usuario"] != user_excluir].reset_index(drop=True)
                        df_transacoes = df_transacoes[df_transacoes["usuario"] != user_excluir].reset_index(drop=True)
                        df_emprestimos = df_emprestimos[df_emprestimos["usuario"] != user_excluir].reset_index(drop=True)
                        salvar_dados_permanentes("banco_contas", df_contas)
                        salvar_dados_permanentes("banco_transacoes", df_transacoes)
                        salvar_dados_permanentes("banco_emprestimos", df_emprestimos)
                        st.success("Conta removida!")
                        st.rerun()

        with tab_transacoes_adm:
            st.dataframe(df_transacoes, use_container_width=True)

        with tab_emprestimos_adm:
            st.dataframe(df_emprestimos, use_container_width=True)

    else:
        # --- PAINEL DO CLIENTE ---
        t_user = df_transacoes[df_transacoes["usuario"] == user] if not df_transacoes.empty else pd.DataFrame()
        ganhos_totais = t_user[t_user["tipo"] == "Ganho"]["valor"].sum() if not t_user.empty else 0.0
        gastos_totais = t_user[t_user["tipo"] == "Gasto"]["valor"].sum() if not t_user.empty else 0.0
        
        e_user = df_emprestimos[df_emprestimos["usuario"] == user] if not df_emprestimos.empty else pd.DataFrame()
        total_recebido_emprestimo = e_user["valor_puro"].sum() if not e_user.empty else 0.0
        divida_atual = e_user["divida_restante"].sum() if not e_user.empty else 0.0
        
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
                            df_transacoes = pd.concat([df_transacoes, nova_t], ignore_index=True)
                            salvar_dados_permanentes("banco_transacoes", df_transacoes)
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
                            df_transacoes = pd.concat([df_transacoes, nova_t], ignore_index=True)
                            salvar_dados_permanentes("banco_transacoes", df_transacoes)
                            st.success("Gasto computado!")
                            st.rerun()

        with tab_analytics:
            st.subheader("📊 Valores Agrupados Inteligentes")
            if not t_user.empty:
                cg1, cg2 = st.columns(2)
                with cg1:
                    st.markdown("##### Total de Ganhos por Área")
                    df_g = t_user[t_user["tipo"] == "Ganho"]
                    if not df_g.empty:
                        st.table(df_g.groupby("area")["valor"].sum().reset_index().rename(columns={"area": "Categoria", "valor": "Soma (R$)"}))
                    else:
                        st.info("Sem entradas.")
                with cg2:
                    st.markdown("##### Total de Gastos por Área")
                    df_p = t_user[t_user["tipo"] == "Gasto"]
                    if not df_p.empty:
                        st.table(df_p.groupby("area")["valor"].sum().reset_index().rename(columns={"area": "Categoria", "valor": "Soma (R$)"}))
                    else:
                        st.info("Sem gastos.")
                st.divider()
                st.markdown("##### Extrato Completo Linha por Linha")
                st.dataframe(t_user[["data", "tipo", "area", "valor"]], use_container_width=True)
            else:
                st.info("Nenhuma movimentação para exibir.")

        with tab_credito:
            st.subheader("🏛️ Crédito sob Medida Apex")
            st.write(f"Limite Disponível: **R$ {max(0.0, limite_disponivel):,.2f}**")
            
            with st.container(border=True):
                cc1, cc2 = st.columns(2)
                with cc1:
                    v_sol = st.number_input("Valor Solicitado:", min_value=0.0, max_value=max(0.0, limite_disponivel), step=50.0)
                with cc2:
                    p_sol = st.number_input("Meses para pagar:", min_value=1, max_value=12, value=1)
                    
                if v_sol > 0:
                    total_juros = float(v_sol * ((1 + 0.05) ** p_sol))
                    st.warning(f"Simulação: {p_sol}x de R$ {(total_juros/p_sol):,.2f} | Total final: R$ {total_juros:,.2f}")
                    
                    if st.button("Contratar Empréstimo", type="primary", use_container_width=True, key="btn_pegar_emprestimo_cli"):
                        n_id_emp = int(df_emprestimos["id"].max() + 1) if not df_emprestimos.empty else 1
                        novo_emp = pd.DataFrame([{
                            "id": n_id_emp, "usuario": user, "data": datetime.now().strftime("%d/%m/%Y"),
                            "valor_puro": v_sol, "total_com_juros": total_juros, "parcelas": int(p_sol), "divida_restante": total_juros
                        }])
                        df_emprestimos = pd.concat([df_emprestimos, novo_emp], ignore_index=True)
                        salvar_dados_permanentes("banco_emprestimos", df_emprestimos)
                        st.success("Crédito liberado em conta!")
                        st.rerun()

if __name__ == '__main__':
    meu_banco_digital()
