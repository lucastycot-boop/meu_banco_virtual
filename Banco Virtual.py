import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Meu Banco Digital", page_icon="💰", layout="centered")

# Função auxiliar para avançar os meses nas datas de vencimento
def adicionar_meses(data_base, meses):
    ano = data_base.year + (data_base.month + meses - 1) // 12
    mes = (data_base.month + meses - 1) % 12 + 1
    dia = min(data_base.day, [31, 29 if ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1])
    return datetime(ano, mes, dia)

def meu_banco_digital():
    st.title("💰 Banco Pessoal - Online 24h")

    # 1. CONEXÃO COM O GOOGLE SHEETS
    # Usamos o st.connection para fazer a ponte com a planilha
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Lê os dados em tempo real da planilha
        df = conn.read(ttl="0d") 
    except Exception as e:
        st.error("Erro ao conectar à planilha. Verifique se configurou os Secrets no Streamlit Cloud.")
        st.stop()

    # Inicializa variáveis de controle na memória apenas para o login do usuário atual
    if "logado" not in st.session_state:
        st.session_state.logado = False
    if "usuario_atual" not in st.session_state:
        st.session_state.usuario_atual = None
    if "limite_padrao_novos_usuarios" not in st.session_state:
        st.session_state.limite_padrao_novos_usuarios = 2000.0

    # 2. TELA DE ACESSO (LOGIN E CADASTRO)
    if not st.session_state.logado:
        st.subheader("🔒 Controle de Acesso")
        aba_login, aba_cadastro = st.tabs(["Entrar", "Criar Nova Conta"])
        
        with aba_login:
            usuario_input = st.text_input("Usuário", key="login_user")
            senha_input = st.text_input("Senha", type="password", key="login_pass")
            
            if st.button("Entrar", use_container_width=True):
                # Procura o usuário na coluna 'usuario' da planilha
                user_rows = df[df["usuario"] == usuario_input]
                
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
                elif novo_usuario in df["usuario"].values:
                    st.error("Esse usuário já existe! Escolha outro nome.")
                elif nova_senha != confirma_senha:
                    st.error("As senhas não coincidem!")
                else:
                    # Cria uma nova linha para a planilha
                    nova_linha = pd.DataFrame([{
                        "usuario": novo_usuario,
                        "senha": nova_senha,
                        "role": "usuario",
                        "ganhos": 0.0,
                        "gastos": 0.0,
                        "limite_emprestimo": float(st.session_state.limite_padrao_novos_usuarios),
                        "divida_emprestimo": 0.0
                    }])
                    
                    # Junta com os dados antigos e salva de volta no Google Sheets
                    df_atualizado = pd.concat([df, nova_linha], ignore_index=True)
                    conn.update(data=df_atualizado)
                    st.success(f"Conta criada com sucesso! Carregando...")
                    st.rerun()

    # 3. PAINEL DO BANCO (APÓS LOGIN)
    else:
        user = st.session_state.usuario_atual
        
        # Pega a linha do usuário logado direto dos dados atualizados da planilha
        linha_user = df[df["usuario"] == user].index[0]
        dados_user = df.loc[linha_user]

        st.markdown(f"### Olá, **{user}**!")
        
        if st.sidebar.button("Sair do Sistema"):
            st.session_state.logado = False
            st.session_state.usuario_atual = None
            st.rerun()

        # --- VISÃO DO DESENVOLVEDOR ---
        if dados_user["role"] == "desenvolvedor":
            st.sidebar.markdown("---")
            st.sidebar.subheader("🛠️ Modo Desenvolvedor")
            
            novo_limite_config = st.sidebar.number_input("Limite para Novos Cadastros (R$)", min_value=0.0, value=float(st.session_state.limite_padrao_novos_usuarios), step=100.0)
            st.session_state.limite_padrao_novos_usuarios = novo_limite_config
            
            ver_painel = st.sidebar.checkbox("Monitorar Contas", value=False)
            if ver_painel:
                st.header("🖥️ Painel Geral (Dev)")
                
                # Exibe a planilha formatada como tabela para o Dev monitorar
                st.dataframe(df)
                
                # FORMULÁRIO DE ABATIMENTO DE DÍVIDA
                usuarios_com_divida = df[df["divida_emprestimo"] > 0]["usuario"].tolist()
                
                st.subheader("🧮 Registrar Recebimento de Empréstimo")
                if usuarios_com_divida:
                    col_dev1, col_dev2 = st.columns(2)
                    with col_dev1:
                        user_pagando = st.selectbox("Qual cliente está pagando?", usuarios_com_divida)
                    with col_dev2:
                        idx_cliente = df[df["usuario"] == user_pagando].index[0]
                        divida_maxima = float(df.loc[idx_cliente, "divida_emprestimo"])
                        valor_pago = st.number_input(f"Valor (Máx R$ {divida_maxima:.2f})", min_value=0.0, max_value=divida_maxima, step=10.0)
                    
                    if st.button("Confirmar Abatimento", type="secondary"):
                        if valor_pago > 0:
                            # Atualiza os dados na tabela local
                            df.loc[idx_cliente, "divida_emprestimo"] -= valor_pago
                            df.loc[idx_cliente, "limite_emprestimo"] += (valor_pago / 1.05)
                            
                            # Salva a tabela inteira atualizada no Google Sheets
                            conn.update(data=df)
                            st.success(f"✅ R$ {valor_pago:.2f} abatidos da dívida de {user_pagando}!")
                            st.rerun()
                else:
                    st.info("Nenhum cliente possui dívidas ativas no momento.")
                st.divider()

        # --- SEÇÃO FINANCEIRA DO USUÁRIO ---
        ganhos = float(dados_user["ganhos"])
        gastos = float(dados_user["gastos"])
        divida = float(dados_user["divida_emprestimo"])
        limite = float(dados_user["limite_emprestimo"])
        saldo_atual = ganhos - gastos
        
        col_s1, col_s2 = st.columns(2)
        col_s1.metric(label="Saldo Atual Disponível", value=f"R$ {saldo_atual:,.2f}")
        if divida > 0:
            col_s2.metric(label="⚠️ Dívida de Empréstimo", value=f"R$ {divida:,.2f}", delta="Com 5% juros/parc.")
        else:
            col_s2.metric(label="👍 Situação de Empréstimo", value="Sem dívidas")

        col1, col2 = st.columns(2)
        col1.metric(label="📈 Total de Ganhos", value=f"R$ {ganhos:,.2f}")
        col2.metric(label="📉 Total de Gastos", value=f"R$ -{gastos:,.2f}", delta_color="inverse")

        st.divider()

        # --- FORMULÁRIOS PARA ADICIONAR DINHEIRO/GASTOS ---
        st.subheader("💵 Nova Movimentação")
        col_ganho, col_gasto = st.columns(2)
        
        with col_ganho:
            st.markdown("### Registrar Entrada")
            valor_ganho = st.number_input("Valor do Ganho (R$)", min_value=0.0, step=10.0, key="add_ganho")
            if st.button("Confirmar Depósito"):
                if valor_ganho > 0:
                    df.loc[linha_user, "ganhos"] += valor_ganho
                    conn.update(data=df)
                    st.success(f"R$ {valor_ganho:.2f} adicionados!")
                    st.rerun()

        with col_gasto:
            st.markdown("### Registrar Saída")
            valor_gasto = st.number_input("Valor do Gasto (R$)", min_value=0.0, step=10.0, key="add_gasto")
            if st.button("Confirmar Gasto"):
                if valor_gasto > 0:
                    df.loc[linha_user, "gastos"] += valor_gasto
                    conn.update(data=df)
                    st.success(f"Gasto de R$ {valor_gasto:.2f} registrado!")
                    st.rerun()

        st.divider()

        # --- SEÇÃO: SIMULADOR DE EMPRÉSTIMO PARCELADO ---
        st.subheader("🏦 Simulador de Empréstimo Parcelado")
        st.write(f"Seu limite disponível: **R$ {limite:,.2f}**")
        
        col_emp1, col_emp2 = st.columns(2)
        with col_emp1:
            valor_solicitado = st.number_input("Valor do Empréstimo (R$)", min_value=0.0, max_value=max(0.0, limite), step=50.0, key="simular_emp")
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
            
            if st.button("Contratar Empréstimo", type="primary"):
                df.loc[linha_user, "ganhos"] += valor_solicitado
                df.loc[linha_user, "divida_emprestimo"] += total_a_pagar
                df.loc[linha_user, "limite_emprestimo"] -= valor_solicitado
                
                conn.update(data=df)
                st.success("🎉 Empréstimo contratado com sucesso!")
                st.rerun()

if __name__ == '__main__':
    meu_banco_digital()
