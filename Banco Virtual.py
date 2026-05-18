import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Meu Banco Digital", page_icon="💰", layout="wide")

# Arquivos de banco de dados locais
ARQUIVO_CONTAS = "banco_contas.csv"
ARQUIVO_TRANSACOES = "banco_transacoes.csv"
ARQUIVO_EMPRESTIMOS = "banco_emprestimos.csv"

# --- SISTEMA DE ARQUIVOS (BANCO DE DADOS) ---
def inicializar_bancos():
    if not os.path.exists(ARQUIVO_CONTAS):
        pd.DataFrame([{
            "usuario": "Lucas", "senha": "1702", "role": "desenvolvedor", "limite_emprestimo": 5000.0
        }]).to_csv(ARQUIVO_CONTAS, index=False)
        
    if not os.path.exists(ARQUIVO_TRANSACOES):
        pd.DataFrame(columns=["id", "usuario", "data", "mes_ano", "tipo", "area", "valor"]).to_csv(ARQUIVO_TRANSACOES, index=False)
        
    if not os.path.exists(ARQUIVO_EMPRESTIMOS):
        pd.DataFrame(columns=["id", "usuario", "data", "valor_puro", "total_com_juros", "parcelas", "divida_restante"]).to_csv(ARQUIVO_EMPRESTIMOS, index=False)

inicializar_bancos()

def carregar_contas(): return pd.read_csv(ARQUIVO_CONTAS)
def salvar_contas(df): df.to_csv(ARQUIVO_CONTAS, index=False)
def carregar_transacoes(): return pd.read_csv(ARQUIVO_TRANSACOES)
def salvar_transacoes(df): df.to_csv(ARQUIVO_TRANSACOES, index=False)
def carregar_emprestimos(): return pd.read_csv(ARQUIVO_EMPRESTIMOS)
def salvar_emprestimos(df): df.to_csv(ARQUIVO_EMPRESTIMOS, index=False)

# Auxiliar para datas
def adicionar_meses(data_base, meses):
    ano = data_base.year + (data_base.month + meses - 1) // 12
    mes = (data_base.month + meses - 1) % 12 + 1
    dia = min(data_base.day, [31, 29 if ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1])
    return datetime(ano, mes, dia)

# --- APLICATIVO PRINCIPAL ---
def meu_banco_digital():
    st.title("💰 Sistema Bancário & Gestão Avançada")

    if "logado" not in st.session_state: st.session_state.logado = False
    if "usuario_atual" not in st.session_state: st.session_state.usuario_atual = None
    if "limite_padrao" not in st.session_state: st.session_state.limite_padrao = 2000.0

    df_contas = carregar_contas()
    df_transacoes = carregar_transacoes()
    df_emprestimos = carregar_emprestimos()

    # TELA DE ACESSO
    if not st.session_state.logado:
        st.subheader("🔒 Controle de Acesso")
        aba_login, aba_cadastro = st.tabs(["Entrar", "Criar Nova Conta"])
        
        with aba_login:
            u_input = st.text_input("Usuário", key="l_user")
            s_input = st.text_input("Senha", type="password", key="l_pass")
            if st.button("Entrar no Banco", use_container_width=True):
                rows = df_contas[df_contas["usuario"].astype(str) == str(u_input)]
                if not rows.empty and str(rows.iloc[0]["senha"]) == str(s_input):
                    st.session_state.logado = True
                    st.session_state.usuario_atual = u_input
                    st.rerun()
                else:
                    st.error("Dados incorretos!")
                    
        with aba_cadastro:
            n_user = st.text_input("Nome de Usuário", key="c_user")
            n_pass = st.text_input("Senha", type="password", key="c_pass")
            c_pass = st.text_input("Confirme a Senha", type="password", key="c_cpass")
            if st.button("Cadastrar", use_container_width=True):
                if not n_user or not n_pass: st.warning("Preencha tudo!")
                elif n_user in df_contas["usuario"].astype(str).values: st.error("Usuário já existe!")
                elif n_pass != c_pass: st.error("Senhas diferentes!")
                else:
                    nova_c = pd.DataFrame([{"usuario": n_user, "senha": n_pass, "role": "usuario", "limite_emprestimo": float(st.session_state.limite_padrao)}])
                    salvar_contas(pd.concat([df_contas, nova_c], ignore_index=True))
                    st.success("Conta Criada! Vá para a aba Entrar.")
                    st.rerun()
        return

    # SESSÃO LOGADA
    user = st.session_state.usuario_atual
    dados_user = df_contas[df_contas["usuario"] == user].iloc[0]

    # BARRA LATERAL
    st.sidebar.markdown(f"### Atendente: **{user}**")
    if st.sidebar.button("Desconectar do Sistema", type="primary"):
        st.session_state.logado = False
        st.session_state.usuario_atual = None
        st.rerun()

    # SEPARAÇÃO DE TELAS: DEV VS USUÁRIO
    if dados_user["role"] == "desenvolvedor":
        st.sidebar.success("⚡ Você está no Modo Desenvolvedor")
        
        st.header("🛠️ Painel de Controle Administrativo (Apenas Dev)")
        
        tab_usuarios, tab_transacoes_adm, tab_emprestimos_adm = st.tabs(["👥 Gerenciar Clientes", "📊 Auditar Transações", "🏦 Controle de Empréstimos"])
        
        with tab_usuarios:
            st.subheader("Contas Cadastradas no Sistema")
            st.dataframe(df_contas, use_container_width=True)
            
            st.subheader("❌ Excluir Conta de Cliente")
            lista_usuarios = df_contas[df_contas["role"] != "desenvolvedor"]["usuario"].tolist()
            if lista_usuarios:
                user_excluir = st.selectbox("Selecione a conta para deletar permanentemente:", lista_usuarios)
                if st.button("Confirmar Exclusão de Conta", type="destructive"):
                    df_contas = df_contas[df_contas["usuario"] != user_excluir]
                    df_transacoes = df_transacoes[df_transacoes["usuario"] != user_excluir]
                    df_emprestimos = df_emprestimos[df_emprestimos["usuario"] != user_excluir]
                    salvar_contas(df_contas)
                    salvar_transacoes(df_transacoes)
                    salvar_emprestimos(df_emprestimos)
                    st.success(f"Conta de {user_excluir} e todo o seu histórico foram apagados!")
                    st.rerun()
            else:
                st.info("Nenhum cliente cadastrado ainda.")

        with tab_transacoes_adm:
            st.subheader("Todas as Movimentações Dinâmicas")
            if not df_transacoes.empty:
                st.dataframe(df_transacoes, use_container_width=True)
                st.subheader("🗑️ Cancelar / Deletar Movimentação Errada")
                id_deletar = st.number_input("Digite o ID exato da transação para apagar:", min_value=0, step=1)
                if st.button("Deletar Registro", type="destructive"):
                    if id_deletar in df_transacoes["id"].values:
                        df_transacoes = df_transacoes[df_transacoes["id"] != id_deletar]
                        salvar_transacoes(df_transacoes)
                        st.success(f"Transação ID {id_deletar} removida com sucesso!")
                        st.rerun()
                    else:
                        st.error("ID não encontrado!")
            else:
                st.info("Nenhuma transação feita no sistema.")

        with tab_emprestimos_adm:
            st.subheader("Contratos de Empréstimos Ativos")
            if not df_emprestimos.empty:
                st.dataframe(df_emprestimos, use_container_width=True)
                
                st.subheader("🧮 Abater Parcelas / Dívidas")
                usuarios_devedores = df_emprestimos[df_emprestimos["divida_restante"] > 0]["usuario"].unique().tolist()
                if usuarios_devedores:
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        u_pago = st.selectbox("Qual cliente realizou o pagamento?", usuarios_devedores)
                    with col_b2:
                        emp_id = st.selectbox("Contrato ID:", df_emprestimos[(df_emprestimos["usuario"] == u_pago) & (df_emprestimos["divida_restante"] > 0)]["id"].tolist())
                        idx_emp = df_emprestimos[df_emprestimos["id"] == emp_id].index[0]
                        valor_maximo = float(df_emprestimos.loc[idx_emp, "divida_restante"])
                        v_recebido = st.number_input(f"Valor Pago (Máx R$ {valor_maximo:.2f}):", min_value=0.0, max_value=valor_maximo, step=10.0)
                    
                    if st.button("Dar Baixa no Pagamento"):
                        if v_recebido > 0:
                            df_emprestimos.loc[idx_emp, "divida_restante"] -= v_recebido
                            salvar_emprestimos(df_emprestimos)
                            st.success(f"Registrado! R$ {v_recebido:.2f} abatidos do contrato ID {emp_id}.")
                            st.rerun()
                else:
                    st.info("Nenhum empréstimo pendente no banco.")
            else:
                st.info("Nenhum contrato assinado até o momento.")
        return

    # TELA EXCLUSIVA DO CLIENTE (Membros comuns)
    # Cálculo em Tempo Real do Saldo Baseado nas Transações
    t_user = df_transacoes[df_transacoes["usuario"] == user]
    ganhos_totais = t_user[t_user["tipo"] == "Ganho"]["valor"].sum()
    gastos_totais = t_user[t_user["tipo"] == "Gasto"]["valor"].sum()
    
    # Empréstimos entram como saldo mas geram dívida separada
    e_user = df_emprestimos[df_emprestimos["usuario"] == user]
    total_recebido_emprestimo = e_user["valor_puro"].sum()
    divida_atual = e_user["divida_restante"].sum()
    
    saldo_real = (ganhos_totais + total_recebido_emprestimo) - gastos_totais
    limite_disponivel = float(dados_user["limite_emprestimo"]) - total_recebido_emprestimo

    # Mostrador de Indicadores de Célula
    st.header(f"🏦 Painel Financeiro — Cliente: {user}")
    m1, m2, m3 = st.columns(3)
    m1.metric("Saldo Real em Conta", f"R$ {saldo_real:,.2f}")
    m2.metric("Total Dívidas de Empréstimos", f"R$ {divida_atual:,.2f}")
    m3.metric("Limite de Crédito para Empréstimo", f"R$ {max(0.0, limite_disponivel):,.2f}")

    st.divider()

    # ABAS DE OPERAÇÃO DO CLIENTE
    tab_movimentar, tab_lucro_mensal, tab_emprestimo_cliente = st.tabs(["💵 Lançar Movimentação", "📊 Extrato de Lucro Mensal", "🏛️ Contratar Empréstimos"])

    with tab_movimentar:
        st.subheader("Registrar Movimentação com Área Personalizada")
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            st.markdown("#### 📈 Lançar Ganho")
            area_ganho = st.text_input("Área/Origem do Ganho (Ex: Salário, Mesada, Venda)", key="a_ganho")
            val_ganho = st.number_input("Valor Recebido (R$)", min_value=0.0, step=10.0, key="v_ganho")
            if st.button("Confirmar Entrada"):
                if val_ganho > 0 and area_ganho:
                    novo_id = int(df_transacoes["id"].max() + 1) if not df_transacoes.empty else 1
                    nova_t = pd.DataFrame([{
                        "id": novo_id, "usuario": user, "data": datetime.now().strftime("%d/%m/%Y"),
                        "mes_ano": datetime.now().strftime("%m/%Y"), "tipo": "Ganho", "area": area_ganho, "valor": val_ganho
                    }])
                    salvar_transacoes(pd.concat([df_transacoes, nova_t], ignore_index=True))
                    st.success("Ganho registrado com sucesso!")
                    st.rerun()

        with col_f2:
            st.markdown("#### 📉 Lançar Gasto")
            area_gasto = st.text_input("Área/Destino do Gasto (Ex: Alimentação, Aluguel, Jogos)", key="a_gasto")
            val_gasto = st.number_input("Valor do Gasto (R$)", min_value=0.0, step=10.0, key="v_gasto")
            if st.button("Confirmar Saída"):
                if val_gasto > 0 and area_gasto:
                    novo_id = int(df_transacoes["id"].max() + 1) if not df_transacoes.empty else 1
                    nova_t = pd.DataFrame([{
                        "id": novo_id, "usuario": user, "data": datetime.now().strftime("%d/%m/%Y"),
                        "mes_ano": datetime.now().strftime("%m/%Y"), "tipo": "Gasto", "area": area_gasto, "valor": val_gasto
                    }])
                    salvar_transacoes(pd.concat([df_transacoes, nova_t], ignore_index=True))
                    st.success("Gasto computado!")
                    st.rerun()

    with tab_lucro_mensal:
        st.subheader("📊 Demonstrativo de Resultados por Mês (Ganhos vs Perdas)")
        if not t_user.empty:
            # Agrupamento matemático inteligente por Mês/Ano
            linhas_mes = []
            for mes em t_user["mes_ano"].unique():
                dados_mes = t_user[t_user["mes_ano"] == mes]
                g_mes = dados_mes[dados_mes["tipo"] == "Ganho"]["valor"].sum()
                p_mes = dados_mes[dados_mes["tipo"] == "Gasto"]["valor"].sum()
                lucro_mes = g_mes - p_mes
                linhas_mes.append({"Mês/Ano": mes, "Ganhos (R$)": g_mes, "Perdas (R$)": p_mes, "Lucro Líquido (R$)": lucro_mes})
            
            df_lucro = pd.DataFrame(linhas_mes)
            st.table(df_lucro)
            
            st.markdown("#### 🗒️ Histórico detalhado de Transações")
            st.dataframe(t_user[["id", "data", "tipo", "area", "valor"]], use_container_width=True)
        else:
            st.info("Nenhuma movimentação realizada neste mês.")

    with tab_emprestimo_cliente:
        st.subheader("🏛️ Solicitação de Crédito Comercial")
        st.write(f"Seu limite operacional de crédito disponível: **R$ {max(0.0, limite_disponivel):,.2f}**")
        
        c1, c2 = st.columns(2)
        with c1:
            v_solicitado = st.number_input("Valor Pretendido (R$)", min_value=0.0, max_value=max(0.0, limite_disponivel), step=50.0)
        with c2:
            p_solicitadas = st.number_input("Prazo de Parcelamento (Meses):", min_value=1, max_value=12, value=1)
            
        if v_solicitado > 0:
            v_parcela = (v_solicitado / p_solicitadas) * 1.05
            t_pagar = v_parcela * p_solicitadas
            
            st.warning(f"**Proposta Comercial:** {p_solicitadas}x de R$ {v_parcela:,.2f} | Total do Contrato: R$ {t_pagar:,.2f}")
            
            cronograma = []
            d_atual = datetime.now()
            for i in range(1, p_solicitadas + 1):
                cronograma.append({"Parcela": f"{i}x", "Vencimento": adicionar_meses(d_atual, i).strftime("%d/%m/%Y"), "Valor": f"R$ {v_parcela:,.2f}"})
            st.table(cronograma)
            
            if st.button("Confirmar e Assinar Contrato", type="primary"):
                novo_id_emp = int(df_emprestimos["id"].max() + 1) if not df_emprestimos.empty else 1
                novo_emp = pd.DataFrame([{
                    "id": novo_id_emp, "usuario": user, "data": datetime.now().strftime("%d/%m/%Y"),
                    "valor_puro": v_solicitado, "total_com_juros": t_pagar, "parcelas": int(p_solicitadas), "divida_restante": t_pagar
                }])
                salvar_emprestimos(pd.concat([df_emprestimos, novo_emp], ignore_index=True))
                st.success("Dinheiro liberado na conta!")
                st.rerun()
                
        st.markdown("#### 📄 Seus Empréstimos Contratados")
        if not e_user.empty:
            st.dataframe(e_user[["id", "data", "valor_puro", "total_com_juros", "parcelas", "divida_restante"]], use_container_width=True)
        else:
            st.info("Você não possui contratos de empréstimo ativos.")

if __name__ == '__main__':
    meu_banco_digital()
