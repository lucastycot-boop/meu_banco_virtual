import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import tempfile

# Arquivos
ARQUIVO_CONTAS = "banco_contas.json"
ARQUIVO_TRANSACOES = "banco_transacoes.json"
ARQUIVO_EMPRESTIMOS = "banco_emprestimos.json"

# ---------- Funções de Persistência Seguras ----------
def salvar_dados_locais(arquivo: str, df: pd.DataFrame):
    """Salva DataFrame em JSON de forma atômica e segura."""
    try:
        dados = df.to_dict(orient="records")
        dirpath = os.path.dirname(os.path.abspath(arquivo)) or "."
        with tempfile.NamedTemporaryFile("w", delete=False, dir=dirpath, encoding="utf-8") as tmp:
            json.dump(dados, tmp, ensure_ascii=False, indent=4)
            tmp_name = tmp.name
        os.replace(tmp_name, arquivo)
    except Exception as e:
        st.error(f"Erro ao salvar {arquivo}: {e}")

def carregar_dados_locais(arquivo: str, dados_iniciais):
    """Carrega JSON para DataFrame; se falhar, recria com dados iniciais."""
    if os.path.exists(arquivo):
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
            df = pd.DataFrame(dados)
            # Garantir colunas mínimas para evitar KeyError depois
            if df.empty:
                return pd.DataFrame(dados_iniciais)
            return df
        except Exception as e:
            st.warning(f"Atenção: arquivo {arquivo} corrompido ou inválido. Recriando. ({e})")
    # cria arquivo novo com dados iniciais
    df = pd.DataFrame(dados_iniciais)
    salvar_dados_locais(arquivo, df)
    return df

# ---------- Inicialização do session_state ----------
if "df_contas" not in st.session_state:
    st.session_state.df_contas = carregar_dados_locais(ARQUIVO_CONTAS, [
        {"usuario": "Lucas", "senha": "1702", "role": "desenvolvedor", "limite_emprestimo": 5000.0}
    ])
# garantir colunas e tipos
if st.session_state.df_contas is None or st.session_state.df_contas.empty:
    st.session_state.df_contas = pd.DataFrame([{"usuario": "Lucas", "senha": "1702", "role": "desenvolvedor", "limite_emprestimo": 5000.0}])

if "df_transacoes" not in st.session_state:
    st.session_state.df_transacoes = carregar_dados_locais(ARQUIVO_TRANSACOES, [])
    if st.session_state.df_transacoes.empty:
        st.session_state.df_transacoes = pd.DataFrame(columns=["id", "usuario", "data", "mes_ano", "tipo", "area", "valor"])

if "df_emprestimos" not in st.session_state:
    st.session_state.df_emprestimos = carregar_dados_locais(ARQUIVO_EMPRESTIMOS, [])
    if st.session_state.df_emprestimos.empty:
        st.session_state.df_emprestimos = pd.DataFrame(columns=["id", "usuario", "data", "valor_puro", "total_com_juros", "parcelas", "divida_restante"])

# valores padrão de sessão
st.session_state.setdefault("logado", False)
st.session_state.setdefault("usuario_atual", None)
st.session_state.setdefault("limite_padrao", 2000.0)

# ---------- Funções utilitárias ----------
def next_id(df: pd.DataFrame, col: str = "id") -> int:
    if col in df.columns and not df.empty:
        try:
            return int(df[col].max()) + 1
        except Exception:
            return int(pd.to_numeric(df[col], errors="coerce").max(skipna=True) or 0) + 1
    return 1

def usuario_existe(df: pd.DataFrame, usuario: str) -> bool:
    return usuario.strip().lower() in df["usuario"].astype(str).str.strip().str.lower().values

# ---------- Interface principal (mantendo estética) ----------
def meu_banco_digital():
    df_contas = st.session_state.df_contas
    df_transacoes = st.session_state.df_transacoes
    df_emprestimos = st.session_state.df_emprestimos

    st.title("🔱 Apex | Sistema Bancário Inteligente")

    # TELA DE LOGIN / CADASTRO
    if not st.session_state.logado:
        col_cen, col_box, col_dir = st.columns([1, 2, 1])
        with col_box:
            with st.container():
                st.subheader("🔒 Controle de Acesso")
                aba_login, aba_cadastro = st.tabs(["🔑 Entrar", "📝 Criar Nova Conta"])

                with aba_login:
                    u_input = st.text_input("Usuário", key="l_user")
                    s_input = st.text_input("Senha", type="password", key="l_pass")
                    if st.button("Acessar Banco", use_container_width=True, type="primary", key="btn_executar_login"):
                        if not u_input or not s_input:
                            st.warning("Preencha usuário e senha.")
                        else:
                            rows = df_contas[df_contas["usuario"].astype(str).str.strip().str.lower() == u_input.strip().lower()]
                            if not rows.empty and str(rows.iloc[0]["senha"]).strip() == str(s_input).strip():
                                st.session_state.logado = True
                                st.session_state.usuario_atual = rows.iloc[0]["usuario"]
                                st.experimental_rerun()
                            else:
                                st.error("Usuário ou senha incorretos!")

                with aba_cadastro:
                    n_user = st.text_input("Nome de Usuário", key="c_user")
                    n_pass = st.text_input("Senha de Acesso", type="password", key="c_pass")
                    c_pass = st.text_input("Confirme a Senha", type="password", key="c_cpass")
                    if st.button("Cadastrar no Sistema", use_container_width=True, key="btn_executar_cadastro"):
                        if not n_user or not n_pass:
                            st.warning("Preencha todos os campos!")
                        elif usuario_existe(df_contas, n_user):
                            st.error("Este usuário já existe!")
                        elif n_pass != c_pass:
                            st.error("As senhas não batem!")
                        else:
                            nova_c = {
                                "usuario": n_user.strip(),
                                "senha": n_pass,
                                "role": "usuario",
                                "limite_emprestimo": float(st.session_state.limite_padrao)
                            }
                            st.session_state.df_contas = pd.concat([df_contas, pd.DataFrame([nova_c])], ignore_index=True)
                            salvar_dados_locais(ARQUIVO_CONTAS, st.session_state.df_contas)
                            st.success("Conta criada com sucesso! Faça login na aba Entrar.")
        return

    # PAINEL RESTRITO
    user = st.session_state.usuario_atual
    # buscar dados do usuário com correspondência exata (preservando case original)
    dados_user_row = st.session_state.df_contas[st.session_state.df_contas["usuario"].astype(str).str.strip() == str(user).strip()]
    if dados_user_row.empty:
        st.error("Usuário não encontrado na base. Faça logout e tente novamente.")
        st.session_state.logado = False
        st.session_state.usuario_atual = None
        return
    dados_user = dados_user_row.iloc[0]

    c_perfil, c_logout = st.columns([5, 1])
    with c_perfil:
        st.markdown(f"👤 Conectado como: **{dados_user['usuario']}**")
    with c_logout:
        if st.button("🚪 Sair do Sistema", use_container_width=True, key="btn_logout_linear_topo"):
            st.session_state.logado = False
            st.session_state.usuario_atual = None
            st.experimental_rerun()

    st.divider()

    # ROTA ADMIN
    if str(dados_user.get("role", "")).strip().lower() == "desenvolvedor":
        st.sidebar.success("⚡ Administrador Ativo")
        st.header("🛠️ Painel de Controle Admin")

        tab_usuarios, tab_transacoes_adm, tab_emprestimos_adm = st.tabs(["👥 Gerenciar Clientes", "📊 Extrato Geral", "🏦 Créditos Ativos"])

        with tab_usuarios:
            st.markdown("##### Todos os Usuários Registrados")
            # mostrar cópia para evitar edição direta
            st.dataframe(st.session_state.df_contas.reset_index(drop=True), use_container_width=True)

            with st.container():
                st.markdown("#### ⚙️ Alterar Limite de Crédito")
                # lista de clientes (filtrar desenvolvedores, case-insensitive)
                mask_clientes = st.session_state.df_contas["role"].astype(str).str.strip().str.lower() != "desenvolvedor"
                lista_clientes = st.session_state.df_contas.loc[mask_clientes, "usuario"].astype(str).tolist()
                if lista_clientes:
                    u_limite = st.selectbox("Selecione o Cliente:", lista_clientes, key="sel_u_limite")
                    idx_u = st.session_state.df_contas[st.session_state.df_contas["usuario"] == u_limite].index[0]
                    lim_atual = float(st.session_state.df_contas.loc[idx_u, "limite_emprestimo"])
                    novo_limite = st.number_input(f"Novo Limite (Atual: R$ {lim_atual:.2f}):", min_value=0.0, step=100.0, value=lim_atual)
                    if st.button("Aplicar Novo Limite", type="primary", key="btn_mudar_limite_adm"):
                        st.session_state.df_contas.loc[idx_u, "limite_emprestimo"] = novo_limite
                        salvar_dados_locais(ARQUIVO_CONTAS, st.session_state.df_contas)
                        st.success("Limite modificado com sucesso!")
                else:
                    st.info("Nenhum cliente cadastrado.")

            with st.container():
                st.markdown("#### ❌ Excluir Conta de Cliente")
                if lista_clientes:
                    user_excluir = st.selectbox("Selecione a conta para deletar:", lista_clientes, key="sel_u_excluir")
                    confirm = st.checkbox("Confirmo exclusão permanente desta conta", key="chk_confirm_delete")
                    if st.button("Confirmar Exclusão Definitiva", key="btn_deletar_conta_adm") and confirm:
                        st.session_state.df_contas = st.session_state.df_contas[st.session_state.df_contas["usuario"] != user_excluir].reset_index(drop=True)
                        st.session_state.df_transacoes = st.session_state.df_transacoes[st.session_state.df_transacoes["usuario"] != user_excluir].reset_index(drop=True)
                        st.session_state.df_emprestimos = st.session_state.df_emprestimos[st.session_state.df_emprestimos["usuario"] != user_excluir].reset_index(drop=True)
                        salvar_dados_locais(ARQUIVO_CONTAS, st.session_state.df_contas)
                        salvar_dados_locais(ARQUIVO_TRANSACOES, st.session_state.df_transacoes)
                        salvar_dados_locais(ARQUIVO_EMPRESTIMOS, st.session_state.df_emprestimos)
                        st.success("Conta removida com sucesso!")
                else:
                    st.info("Nenhum cliente para excluir.")

        with tab_transacoes_adm:
            st.dataframe(st.session_state.df_transacoes.reset_index(drop=True), use_container_width=True)

        with tab_emprestimos_adm:
            st.dataframe(st.session_state.df_emprestimos.reset_index(drop=True), use_container_width=True)

    # ROTA CLIENTE (mantive layout e lógica)
    else:
        t_user = st.session_state.df_transacoes[st.session_state.df_transacoes["usuario"] == user] if not st.session_state.df_transacoes.empty else pd.DataFrame()
        ganhos_totais = t_user[t_user["tipo"] == "Ganho"]["valor"].sum() if not t_user.empty else 0.0
        gastos_totais = t_user[t_user["tipo"] == "Gasto"]["valor"].sum() if not t_user.empty else 0.0

        e_user = st.session_state.df_emprestimos[st.session_state.df_emprestimos["usuario"] == user] if not st.session_state.df_emprestimos.empty else pd.DataFrame()
        total_recebido_emprestimo = e_user["valor_puro"].sum() if not e_user.empty else 0.0
        divida_atual = e_user["divida_restante"].sum() if not e_user.empty else 0.0

        saldo_real = (ganhos_totais + total_recebido_emprestimo) - gastos_totais
        limite_disponivel = float(dados_user["limite_emprestimo"]) - total_recebido_emprestimo

        st.markdown(f"### 👋 Olá, **{user}**")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🟢 SALDO DISPONÍVEL", f"R$ {saldo_real:,.2f}")
        with col2:
            st.metric("🔴 DÍVIDA CONSOLIDADA", f"R$ {divida_atual:,.2f}")
        with col3:
            st.metric("🔵 LINHA DE CRÉDITO", f"R$ {max(0.0, limite_disponivel):,.2f}")

        st.divider()

        tab_movimentar, tab_analytics, tab_credito = st.tabs(["💸 Nova Transação", "📊 Resumo por Categorias", "🏛️ Empréstimos"])

        with tab_movimentar:
            c_ganho, c_gasto = st.columns(2)
            with c_ganho:
                st.markdown("#### 📈 Lançar Entrada (Ganho/Pix)")
                area_ganho = st.text_input("Classificação (Ex: Salário, Mesada)", key="a_ganho").strip().capitalize()
                val_ganho = st.number_input("Valor Recebido (R$)", min_value=0.0, step=10.0, key="v_ganho")
                if st.button("Registrar Entrada", use_container_width=True, key="btn_salvar_entrada_cli"):
                    if val_ganho > 0 and area_ganho:
                        novo_id = next_id(st.session_state.df_transacoes, "id")
                        nova_t = {
                            "id": novo_id,
                            "usuario": user,
                            "data": datetime.now().strftime("%d/%m/%Y"),
                            "mes_ano": datetime.now().strftime("%m/%Y"),
                            "tipo": "Ganho",
                            "area": area_ganho,
                            "valor": float(val_ganho)
                        }
                        st.session_state.df_transacoes = pd.concat([st.session_state.df_transacoes, pd.DataFrame([nova_t])], ignore_index=True)
                        salvar_dados_locais(ARQUIVO_TRANSACOES, st.session_state.df_transacoes)
                        st.success("Ganho registrado!")

            with c_gasto:
                st.markdown("#### 📉 Lançar Saída (Gasto/Compra)")
                area_gasto = st.text_input("Classificação (Ex: Roupa, Lanche)", key="a_gasto").strip().capitalize()
                val_gasto = st.number_input("Valor Gasto (R$)", min_value=0.0, step=10.0, key="v_gasto")
                if st.button("Registrar Saída", use_container_width=True, key="btn_salvar_saida_cli"):
                    if val_gasto > 0 and area_gasto:
                        novo_id = next_id(st.session_state.df_transacoes, "id")
                        nova_t = {
                            "id": novo_id,
                            "usuario": user,
                            "data": datetime.now().strftime("%d/%m/%Y"),
                            "mes_ano": datetime.now().strftime("%m/%Y"),
                            "tipo": "Gasto",
                            "area": area_gasto,
                            "valor": float(val_gasto)
                        }
                        st.session_state.df_transacoes = pd.concat([st.session_state.df_transacoes, pd.DataFrame([nova_t])], ignore_index=True)
                        salvar_dados_locais(ARQUIVO_TRANSACOES, st.session_state.df_transacoes)
                        st.success("Gasto computado!")

        with tab_analytics:
            st.subheader("📊 Valores Agrupados Inteligentemente")
            if not t_user.empty:
                cg1, cg2 = st.columns(2)
                with cg1:
                    st.markdown("##### Total de Ganhos por Área")
                    df_g = t_user[t_user["tipo"] == "Ganho"]
                    if not df_g.empty:
                        st.dataframe(df_g.groupby("area")["valor"].sum().reset_index().rename(columns={"area": "Categoria", "valor": "Soma (R$)"}))
                    else:
                        st.info("Sem entradas.")
                with cg2:
                    st.markdown("##### Total de Gastos por Área")
                    df_p = t_user[t_user["tipo"] == "Gasto"]
                    if not df_p.empty:
                        st.dataframe(df_p.groupby("area")["valor"].sum().reset_index().rename(columns={"area": "Categoria", "valor": "Soma (R$)"}))
                    else:
                        st.info("Sem gastos.")
                st.divider()
                st.markdown("##### Extrato Completo Linha por Linha")
                st.dataframe(t_user[["data", "tipo", "area", "valor"]], use_container_width=True)
            else:
                st.info("Nenhuma movimentação para exibir.")

        with tab_credito:
            st.subheader("🏛️ Crédito sob Medida Apex")
            st.write(f"Limite Disponível para Empréstimo: **R$ {max(0.0, limite_disponivel):,.2f}**")
            with st.container():
                st.markdown("#### 📝 Solicitar Novo Crédito")
                v_sol = st.number_input("Valor Solicitado (R$):", min_value=0.0, max_value=max(0.0, limite_disponivel), step=50.0)
                if v_sol > 0:
                    st.markdown("##### 📊 Tabela de Simulação de Parcelas")
                    dados_simulacao = []
                    for parcelas in range(1, 13):
                        total_juros = float(v_sol * ((1 + 0.05) ** parcelas))
                        valor_parcela = total_juros / parcelas
                        dados_simulacao.append({
                            "Parcelas": f"{parcelas}x",
                            "Valor da Parcela": f"R$ {valor_parcela:,.2f}",
                            "Total com Juros": f"R$ {total_juros:,.2f}"
                        })
                    st.table(pd.DataFrame(dados_simulacao))
                    p_sol = st.number_input("Digite a quantidade de parcelas desejada (1 a 12):", min_value=1, max_value=12, value=1)
                    total_final_escolhido = float(v_sol * ((1 + 0.05) ** p_sol))
                    if st.button("Contratar Empréstimo Apex", type="primary", use_container_width=True, key="btn_pegar_emprestimo_cli"):
                        n_id_emp = next_id(st.session_state.df_emprestimos, "id")
                        novo_emp = {
                            "id": n_id_emp,
                            "usuario": user,
                            "data": datetime.now().strftime("%d/%m/%Y"),
                            "valor_puro": float(v_sol),
                            "total_com_juros": total_final_escolhido,
                            "parcelas": int(p_sol),
                            "divida_restante": total_final_escolhido
                        }
                        st.session_state.df_emprestimos = pd.concat([st.session_state.df_emprestimos, pd.DataFrame([novo_emp])], ignore_index=True)
                        salvar_dados_locais(ARQUIVO_EMPRESTIMOS, st.session_state.df_emprestimos)
                        st.success("Crédito liberado em conta!")

        st.divider()
        st.markdown("#### 📊 Seus Contratos de Empréstimos Ativos")
        if not e_user.empty:
            st.dataframe(
                e_user[["data", "valor_puro", "total_com_juros", "parcelas", "divida_restante"]].rename(columns={
                    "data": "Data de Contratação",
                    "valor_puro": "Valor Recebido (R$)",
                    "total_com_juros": "Total com Juros (R$)",
                    "parcelas": "Prazo (Meses)",
                    "divida_restante": "Dívida Atual (R$)"
                }),
                use_container_width=True
            )
        else:
            st.info("Você não possui contratos de empréstimo ativos no momento.")

if __name__ == "__main__":
    meu_banco_digital()
