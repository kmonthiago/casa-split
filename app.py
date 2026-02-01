import json
import streamlit as st
from datetime import date, datetime, timedelta
import os

from db import (
    init_db,
    add_expense,
    list_expenses_month,
    upsert_default_users,
    get_users,
    add_settlement,
    get_settlement,
)
from logic import compute_month_summary

st.set_page_config(page_title="Casa Split", layout="centered")

# ===== GERENCIAMENTO DE CATEGORIAS =====
CATEGORIAS_FILE = "categorias.json"

def carregar_categorias():
    """Carrega categorias do arquivo ou retorna padrão"""
    if os.path.exists(CATEGORIAS_FILE):
        try:
            with open(CATEGORIAS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return get_categorias_padrao()
    return get_categorias_padrao()

def get_categorias_padrao():
    """Retorna categorias padrão"""
    return ["Outro"]

def salvar_categorias(categorias):
    """Salva categorias em arquivo JSON"""
    with open(CATEGORIAS_FILE, 'w', encoding='utf-8') as f:
        json.dump(categorias, f, ensure_ascii=False, indent=2)

def adicionar_categoria_personalizada(nova_categoria):
    """Adiciona uma nova categoria personalizada"""
    categorias = carregar_categorias()
    if nova_categoria not in categorias and nova_categoria.strip():
        categorias.append(nova_categoria)
        salvar_categorias(categorias)
        return True
    return False

init_db()
upsert_default_users(user_a_name="Thiago", user_b_name="Marina")
users = get_users()
user_a = users[0]  # Thiago
user_b = users[1]  # Marina

st.sidebar.title("Casa Split")
page = st.sidebar.radio("Menu", ["Adicionar gasto", "Resumo do mês", "Fechamento", "Configurações"])

DEFAULT_SPLIT = (0.5, 0.5)

def last_n_months(n):
    """Retorna lista dos últimos n meses em formato YYYY-MM."""
    from datetime import datetime, timedelta
    months = []
    today = datetime.today()
    for i in range(n):
        first_day_of_month = today.replace(day=1) - timedelta(days=i*30)
        months.append(first_day_of_month.strftime("%Y-%m"))
    return sorted(set(months), reverse=True)



if page == "Adicionar gasto":
    st.header("Adicionar gasto")
    st.markdown("Preencha os detalhes do gasto abaixo:")
    st.divider()

    col1, col2 = st.columns([2, 1])
    with col1:
        amount = st.number_input("💰 Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
    with col2:
        spent_at = st.date_input("📅 Data", value=date.today())

    payer = st.selectbox("👤 Quem pagou?", [user_a["name"], user_b["name"]])
    
    # Carregar categorias dinâmicas
    categorias = carregar_categorias()
    category = st.selectbox("📁 Categoria", categorias)
    
    # Se "Outro" for selecionado, pedir especificação
    categoria_usada = category
    if category == "Outro":
        st.warning("ℹ️ Especifique qual é a categoria:")
        categoria_customizada = st.text_input(
            "Qual categoria?",
            placeholder="ex: Restaurante, Viagem, Farmácia, Eletrônicos...",
            key="categoria_customizada_input"
        )
        if categoria_customizada.strip():
            categoria_usada = categoria_customizada
            # Adicionar automaticamente à lista de categorias
            if adicionar_categoria_personalizada(categoria_customizada):
                st.success(f"✨ Categoria '{categoria_customizada}' adicionada!")
    
    description = st.text_input("📝 Descrição (opcional)", placeholder="ex: Angeloni - limpeza")

    st.markdown("### Como dividir este gasto?")
    
    # Inicializar split padrão
    if "edit_split" not in st.session_state:
        st.session_state.edit_split = False
    if "split_mode_temp" not in st.session_state:
        st.session_state.split_mode_temp = "percentage"
    if "split_a_pct_temp" not in st.session_state:
        st.session_state.split_a_pct_temp = 50
    
    # Display do split com botão de edição
    col_split_display, col_split_edit = st.columns([3, 1])
    
    with col_split_display:
        current_split_a_pct = st.session_state.get("split_a_pct_temp", 50)
        current_split_b_pct = 100 - current_split_a_pct
        st.markdown(f"**💰 Divisão: {int(current_split_a_pct)}% / {int(current_split_b_pct)}%**")
    
    with col_split_edit:
        if st.button("✏️ Editar", use_container_width=True):
            st.session_state.edit_split = not st.session_state.edit_split
    
    # Se estiver em modo edição
    if st.session_state.edit_split:
        st.divider()
        st.markdown("#### Editar divisão:")
        
        edit_mode = st.radio(
            "Escolha como editar:",
            ["📊 Por percentual", "💵 Por valor"],
            horizontal=True,
            key="edit_split_mode"
        )
        
        if edit_mode == "📊 Por percentual":
            split_a_pct = st.slider(
                f"{user_a['name']} (%)",
                min_value=0,
                max_value=100,
                value=st.session_state.split_a_pct_temp,
                step=1,
                key="slider_split_a"
            )
            split_b_pct = 100 - split_a_pct
            st.caption(f"{user_b['name']}: {split_b_pct}%")
            st.session_state.split_a_pct_temp = split_a_pct
        else:
            col_val1, col_val2 = st.columns(2)
            with col_val1:
                amount_a = st.number_input(
                    f"Valor {user_a['name']} (R$)",
                    min_value=0.0,
                    step=0.01,
                    key="amount_a_split"
                )
            with col_val2:
                amount_b = st.number_input(
                    f"Valor {user_b['name']} (R$)",
                    min_value=0.0,
                    step=0.01,
                    key="amount_b_split"
                )
            
            total_split = amount_a + amount_b
            if total_split > 0:
                split_a_pct = int((amount_a / total_split) * 100)
                split_b_pct = 100 - split_a_pct
                st.session_state.split_a_pct_temp = split_a_pct
                st.caption(f"Divisão: {split_a_pct}% / {split_b_pct}%")
            else:
                st.warning("⚠️ Insira valores maiores que zero")
                split_a_pct = 50
                split_b_pct = 50
        
        st.divider()
        if st.button("✅ Confirmar divisão", use_container_width=True):
            st.session_state.edit_split = False
            st.success("✨ Divisão atualizada!")
    
    # Aplicar split final
    split_a = st.session_state.split_a_pct_temp / 100.0
    split_b = (100 - st.session_state.split_a_pct_temp) / 100.0

    st.divider()
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])

    with col_btn1:
        if st.button("✅ Salvar gasto", use_container_width=True):
            if amount <= 0:
                st.error("O valor deve ser maior que zero.")
            elif category == "Outro" and categoria_usada == "Outro":
                st.error("❌ Especifique a categoria (não pode ser apenas 'Outro').")
            else:
                split_json = json.dumps({str(user_a["id"]): split_a, str(user_b["id"]): split_b})
                payer_id = user_a["id"] if payer == user_a["name"] else user_b["id"]
                add_expense(
                    amount_cents=int(round(amount * 100)),
                    payer_user_id=payer_id,
                    category=categoria_usada,
                    description=description.strip() or categoria_usada,
                    spent_at=str(spent_at),
                    split_json=split_json
                )
                st.success("✨ Gasto salvo com sucesso!")
                st.balloons()

    with col_btn3:
        split_display = f"{int(split_a*100)}/{int(split_b*100)}"
        st.caption(f"📊 Preview: R$ {amount:.2f} | {categoria_usada if categoria_usada != 'Outro' else category} | {split_display}")

elif page == "Resumo do mês":
    st.header("Resumo do mês")
    month = st.selectbox("📅 Selecione o mês", last_n_months(12), index=0)
    expenses = list_expenses_month(month)

    summary = compute_month_summary(expenses, user_a, user_b)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 Total do mês", f"R$ {summary['total']:.2f}")
    with col2:
        st.metric(f"💳 {user_a['name']}", f"R$ {summary['paid_a']:.2f}")
    with col3:
        st.metric(f"💳 {user_b['name']}", f"R$ {summary['paid_b']:.2f}")

    st.divider()
    st.subheader("💹 Análise de saldo")
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.write(f"**{user_a['name']}**")
        st.write(f"Pagou: R$ {summary['paid_a']:.2f}")
        st.write(f"Deveria pagar: R$ {summary['quota_a']:.2f}")
        st.write(f"**Saldo: R$ {summary['bal_a']:.2f}**")
    
    with col_b:
        st.write(f"**{user_b['name']}**")
        st.write(f"Pagou: R$ {summary['paid_b']:.2f}")
        st.write(f"Deveria pagar: R$ {summary['quota_b']:.2f}")
        st.write(f"**Saldo: R$ {summary['bal_b']:.2f}**")

    st.success(f"✅ {summary['suggestion']}")

    st.divider()
    st.subheader("📋 Gastos do mês")
    if not expenses:
        st.info("Nenhum gasto registrado neste mês.")
    else:
        st.dataframe(expenses, use_container_width=True)

elif page == "Fechamento":
    st.header("🔐 Fechamento do mês")
    month = st.selectbox("📅 Selecione o mês", last_n_months(12), index=0)

    expenses = list_expenses_month(month)
    summary = compute_month_summary(expenses, user_a, user_b)
    
    st.info(f"💡 Sugestão de acerto: {summary['suggestion']}")

    existing = get_settlement(month)
    if existing and existing["paid_at"]:
        st.success(f"✅ Mês já fechado em {existing['paid_at']}.")
    else:
        st.warning("⚠️ Este mês ainda não foi fechado.")
        if st.button("✔️ Marcar como pago", use_container_width=True):
            from_id, to_id, amount = summary["settle_from_to_amount"]
            if amount > 0:
                add_settlement(month, from_id, to_id, int(round(amount * 100)))
                st.success(f"✨ Fechamento registrado! Mês {month} finalizado.")
            else:
                st.success("✅ Nada a acertar neste mês. Mês finalizado!")

else:
    st.header("⚙️ Configurações")
    st.divider()
    
    st.markdown("### 📋 Categorias Disponíveis")
    
    categorias = carregar_categorias()
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Categorias Atuais:**")
        for i, cat in enumerate(categorias, 1):
            st.markdown(f"{i}. {cat}")
    
    with col2:
        st.markdown("**Total:**")
        st.metric("", len(categorias))
        
        if st.button("🔄 Resetar para Padrão", use_container_width=True):
            salvar_categorias(get_categorias_padrao())
            st.success("✅ Categorias resetadas para o padrão!")
            st.rerun()
    
    st.divider()
    st.markdown("### ℹ️ Informações da Aplicação")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**👥 Usuários:** {user_a['name']} e {user_b['name']}")
        st.write(f"**💰 Split padrão:** 50/50")
    with col2:
        st.write(f"**📁 Total de categorias:** {len(categorias)}")
        st.write(f"**📄 Arquivo:** {CATEGORIAS_FILE}")
