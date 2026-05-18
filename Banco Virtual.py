import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Meu Banco Digital", page_icon="💰", layout="centered")

# Nome do arquivo de texto que vai guardar os dados no GitHub
ARQUIVO_BANCO = "banco_dados_virtual.csv"

# Função para inicializar o banco de dados se o arquivo não existir
def carregar_dados():
    if os.path.exists(ARQUIVO_BANCO):
        return pd.read_csv(ARQUIVO_BANCO)
    else:
        # Se o arquivo não existir, cria o primeiro com a sua conta Dev
        dados_iniciais = pd.DataFrame([{
            "usuario": "Lucas",
            "senha": "1702",
            "role": "desenvolvedor",
            "ganhos": 0.0,
            "gastos": 0.0,
            "limite_emprestimo": 5000.0,
            "divida_emprestimo": 0.0
        }])
        dados_iniciais.to_csv(ARQUIVO_BANCO, index=False)
        return dados_iniciais

def salvar_dados(df):
    df.to_csv(ARQUIVO_BANCO, index=False)

# Função auxiliar para as datas
def adicionar_meses(data_base, meses):
    ano = data_base.year + (data_base.month + meses - 1) // 12
    mes = (data_base.month + meses - 1) % 12 + 1
    dia = min(data_base.day, [31, 29 if ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1])
    return datetime(ano, mes, dia)

def meu_banco_digital():
    st.title("💰 Banco Pessoal - Online 24h")

    # Carrega os dados salvos no arquivo local
    df = carregar_dados()

    # Inicializa variáveis de controle de login
    if "logado" not in st.session_state:
        st.session_state.logado = False
    if "usuario_atual" not in st.session_state:
        st.session_state.usuario_atual = None
    if "limite_padrao_novos_usuarios" not in st.session_state:
        st.session_state.limite_padrao_novos_usuarios = 2000.0

    # TELA DE ACESSO
    if not st.session_state.logado:
        st.subheader("🔒 Controle de Acesso")
        aba_login, aba_cadastro = st.tabs(["Entrar", "Criar Nova Conta"])
        
        with aba_login:
            usuario_input = st.text_input("Usuário", key="login_user")
            senha_input = st.text_input("Senha", type="password", key="login_pass")
            
            if st.button("Entrar", use_container_width=True):
                user_rows = df[df["usuario"].astype(str) == str(usuario_input)]
                
                if not user_rows.empty and str(user_rows.iloc[0]["senha"]) == str(senha_input):
                    st.session_state.logado = True
                    st.session_state.usuario_atual = usuario_input
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
                elif novo_usuario in df["usuario"].astype(str).values:
                    st.error("Esse usuário já existe! Escolha outro nome.")
                elif nova_senha != confirma_senha:
                    st.error("As senhas não coincidem!")
                else:
                    nova_linha = pd.DataFrame([{
                        "usuario": novo_usuario,
                        "senha": nova_senha,
                        "role": "usuario",
                        "ganhos": 0.0,
                        "gastos": 0.0,
                        "limite_emprestimo": float(st.session_state.limite_padrao_novos_usuarios),
                        "divida_emprestimo": 0.0
                    }])
                    
                    df_atualizado = pd.concat([df, nova_linha], ignore_index=True)
                    salvar_dados(df_atualizado)
                    st.success(f"Conta criada com sucesso! Entre na aba 'Entrar' para acessar.")
                    st.rerun()

    # PAINEL DO BANCO
    else:
        user = st.session_state.usuario_atual
        linha_user = df[df["usuario"].astype(str) == str(user)].index[0]
        dados_user = df.loc[linha_user]

        st.markdown(f"### Olá, **{user}**!")
        
        if st.sidebar.button("Sair do Sistema"):
            st.session_state.logado = False
            st.session_state.usuario_atual = None
            st.rerun()

        # MODO DEV
        if dados_user["role"] == "desenvolvedor":
            st.sidebar.markdown("---")
            st.sidebar.subheader("🛠️ Modo Desenvolvedor")
            
            novo_limite_config = st.sidebar.number_input("Limite para Novos Cadastros (R$)", min_value=0.0, value=float(st.session_state.limite_padrao_novos_usuarios), step=100.0)
            st.session_state.limite_padrao_novos_usuarios = novo_limite_config
            
            ver_painel = st.sidebar.checkbox("Monitorar Contas", value=False)
            if ver_painel:
                st.header("🖥️ Painel Geral (Dev)")
                st.dataframe(df)
                
                usuarios_com_divida = df[df["divida_emprestimo"] > 0]["usuario"].tolist()
                st.subheader("🧮 Registrar Recebimento")
                if usuarios_com_divida:
                    col_dev1, col_dev2 = st.columns(2)
                    with col_dev1:
                        user_pagando = st.selectbox("Qual cliente está pagando?", usuarios_com_divida)
                    with col_dev2:
                        idx_cliente = df[df["usuario"] == user_pagando].index[0]
                        divida_maxima = float(df.loc[idx_cliente, "divida_emprestimo"])
                        valor_pago = st.number_input(f"Valor (Máx R$ {divida_maxima:.2f})", min_value=0.0, max_value=divida_maxima, step=10.0)
                    
                    if st.button("Confirmar Abatimento"):
                        if valor_pago > 0:
                            df.loc[idx_cliente, "divida_emprestimo"] -= valor_pago
                            df.loc[idx_cliente, "limite_emprestimo"] += (valor_pago / 1.05)
                            salvar_dados(df)
                            st.success(f"✅ R$ {valor_pago:.2f} abatidos!")
                            st.rerun()
                else:
                    st.info("Nenhum cliente possui dívidas ativas.")
                st.divider()

        # SEÇÃO FINANCEIRA
        ganhos = float(dados_user["ganhos"])
        gastos = float(dados_user["gastos"])
        divida = float(dados_user["divida_emprestimo"])
        limite = float(dados_user["limite_emprestimo"])
        saldo_atual = ganhos - gastos
        
        col_s1, col_s2 = st.columns(2)
        col_s1.metric(label="Saldo Atual Disponível", value=f"R$ {saldo_atual:,.2f}")
        if divida > 0:
            col_s2.metric(label="⚠️ Dívida de Empréstimo", value=f"R$ {divida:,.2f}")
        else:
            col_s2.metric(label="👍 Situação de Empréstimo", value="Sem dívidas")

        st.divider()

        # MOVIMENTAÇÕES
        st.subheader("💵 Nova Movimentação")
        col_ganho, col_gasto = st.columns(2)
        
        with col_ganho:
            valor_ganho = st.number_input("Valor do Ganho (R$)", min_value=0.0, step=10.0, key="add_ganho")
            if st.button("Confirmar Depósito"):
                if valor_ganho > 0:
                    df.loc[linha_user, "ganhos"] += valor_ganho
                    salvar_dados(df)
                    st.success("Depósito efetuado!")
                    st.rerun()

        with col_gasto:
            valor_gasto = st.number_input("Valor do Gasto (R$)", min_value=0.0, step=10.0, key="add_gasto")
            if st.button("Confirmar Gasto"):
                if valor_gasto > 0:
                    df.loc[linha_user, "gastos"] += valor_gasto
                    salvar_dados(df)
                    st.success("Gasto registrado!")
                    st.rerun()

        st.divider()

        # EMPRÉSTIMOS
        st.subheader("🏦 Simulador de Empréstimo Parcelado")
        st.write(f"Seu limite disponível: **R$ {limite:,.2f}**")
        
        col_emp1, col_emp2 = st.columns(2)
        with col_emp1:
            valor_solicitado = st.number_input("Valor (R$)", min_value=0.0, max_value=max(0.0, limite), step=50.0)
        with col_emp2:
            qtd_parcelas = st.number_input("Parcelas (Máx 12x)", min_value=1, max_value=12, value=1, step=1)
        
        if valor_solicitado > 0:
            valor_base_parcela = valor_solicitado / qtd_parcelas
            valor_parcela_com_juros = valor_base_parcela * 1.05
            total_a_pagar = valor_parcela_com_juros * qtd_parcelas
            
            cronograma = []
            data_atual = datetime.now()
            for i in range(1, qtd_parcelas + 1):
                cronograma.append({
                    "Parcela": f"{i}x",
                    "Vencimento": adicionar_meses(data_atual, i).strftime("%d/%m/%Y"),
                    "Valor": f"R$ {valor_parcela_com_juros:,.2f}"
                })
            st.table(cronograma)
            
            if st.button("Contratar Empréstimo", type="primary"):
                df.loc[linha_user, "ganhos"] += valor_solicitado
                df.loc[linha_user, "divida_emprestimo"] += total_a_pagar
                df.loc[linha_user, "limite_emprestimo"] -= valor_solicitado
                salvar_dados(df)
                st.success("🎉 Empréstimo contratado!")
                st.rerun()

if __name__ == '__main__':
    meu_banco_digital()
