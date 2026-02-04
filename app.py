import json
import streamlit as st
from datetime import date
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Internal imports from the new structure
from src.database import (
    init_db,
    add_expense,
    list_expenses_month,
    upsert_default_users,
    upsert_default_categories,
    get_users,
    add_settlement,
    get_settlement,
    update_expense,
    delete_expense,
    update_category,
    delete_category,
)
from src.logic import compute_month_summary
from src.utils.categories import (
    carregar_categorias, 
    adicionar_categoria_personalizada, 
    get_categorias_padrao, 
    salvar_categorias
)
from src.ui.common import last_n_months, apply_custom_css

# Page Config
st.set_page_config(page_title="Casa Split", page_icon="🏠", layout="centered")
apply_custom_css()

# Initialization
init_db()
upsert_default_users(user_a_name="Thiago", user_b_name="Marina")
upsert_default_categories()
users = get_users()
user_a = users[0]
user_b = users[1]

# Sidebar
st.sidebar.title("🏠 Casa Split")
page = st.sidebar.radio("Menu", ["Adicionar gasto", "Resumo do mês", "Fechamento", "Configurações"])

# Main Pages
if page == "Adicionar gasto":
    st.header("➕ Adicionar Gasto")
    
    # MANUAL FORM ---

    # --- MANUAL FORM ---
    col1, col2 = st.columns([2, 1])
    with col1:
        amount = st.number_input("💰 Valor (R$)", min_value=0.0, step=0.01, format="%.2f", key="amount", value=None)
    with col2:
        spent_at = st.date_input("📅 Data", value=date.today(), key="spent_at")

    # Default to user_b (Marina) if available
    default_payer_idx = 1 if len(users) > 1 and users[1]["name"] == "Marina" else 0
    payer = st.selectbox("👤 Quem pagou?", [u["name"] for u in users], index=default_payer_idx, key="payer")
    
    categorias = carregar_categorias()
    if "category" not in st.session_state or st.session_state.category not in categorias:
        st.session_state.category = categorias[0]
        
    category = st.selectbox("📁 Categoria", categorias, key="category")
    
    # Custom category logic
    categoria_usada = category
    if category == "Outro":
        categoria_customizada = st.text_input(
            "Qual categoria?",
            placeholder="ex: Restaurante, Viagem...",
            key="categoria_customizada_input"
        )
        if categoria_customizada.strip():
            categoria_usada = categoria_customizada

    description = st.text_input("📝 Descrição (opcional)", placeholder="ex: Compra no Angeloni", key="description")

    # Discrete Split Selection
    custom_split = st.checkbox("Personalizar divisão (padrão 50/50)", key="custom_split_check")
    
    if custom_split:
        if "split_a_pct" not in st.session_state:
            st.session_state.split_a_pct = 50
        
        split_a_pct = st.slider(f"{user_a['name']} (%)", 0, 100, st.session_state.split_a_pct)
        st.session_state.split_a_pct = split_a_pct
        split_b_pct = 100 - split_a_pct
        st.caption(f"{user_b['name']}: {split_b_pct}%")
        
        split_a = split_a_pct / 100.0
        split_b = split_b_pct / 100.0
    else:
        split_a = 0.5
        split_b = 0.5
    
    if st.button("✅ Salvar Gasto", use_container_width=True, type="primary"):
        if amount is None or amount <= 0:
            st.error("O valor deve ser maior que zero.")
        else:
            split_json = json.dumps({str(user_a["id"]): split_a, str(user_b["id"]): split_b})
            payer_id = user_a["id"] if payer == user_a["name"] else user_b["id"]
            
            # If custom category, add it to the list
            if category == "Outro" and categoria_usada != "Outro":
                adicionar_categoria_personalizada(categoria_usada)
            
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

elif page == "Resumo do mês":
    st.header("📊 Resumo do Mês")
    month = st.selectbox("📅 Selecione o mês", last_n_months(12), index=0)
    expenses = list_expenses_month(month)

    summary = compute_month_summary(expenses, user_a, user_b)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 Total", f"R$ {summary['total']:.2f}")
    with col2:
        st.metric(f"💳 {user_a['name']}", f"R$ {summary['paid_a']:.2f}")
    with col3:
        st.metric(f"💳 {user_b['name']}", f"R$ {summary['paid_b']:.2f}")

    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**{user_a['name']}**\n\nSaldo: R$ {summary['bal_a']:.2f}")
    with c2:
        st.info(f"**{user_b['name']}**\n\nSaldo: R$ {summary['bal_b']:.2f}")

    st.success(f"💡 {summary['suggestion']}")

    st.subheader("📋 Detalhes dos Gastos")
    if not expenses:
        st.info("Nenhum gasto registrado.")
    else:
        for i, exp in enumerate(expenses):
            # Split handling
            try:
                split = json.loads(exp["split_json"])
                s_a = float(split.get(str(user_a["id"]), 0.5))
                s_b = float(split.get(str(user_b["id"]), 0.5))
            except:
                s_a = s_b = 0.5
            p_a = exp["amount"] * s_a
            p_b = exp["amount"] * s_b
            payer_full = user_a["name"] if exp["payer_user_id"] == user_a["id"] else user_b["name"]
            date_short = exp['spent_at'][5:]

            # --- UNIFIED VIEW ---
            # Single row structure for both desktop and mobile
            cols = st.columns([0.8, 1.2, 1.2, 2.3, 1.2, 1.5, 0.5])
            
            # Use 'write' for simple text to allow Streamlit's natural re-flowing
            cols[0].write(f"**{date_short}**")
            cols[1].write(f"R${exp['amount']:.2f}")
            cols[2].write(f"`{exp['category'][:10]}`")
            cols[3].write(f"{exp['description'][:30]}")
            cols[4].write(f"**{payer_full}**")
            cols[5].write(f"<small>T:{p_a:.1f} M:{p_b:.1f}</small>", unsafe_allow_html=True)
            
            with cols[6]:
                if st.button("📝", key=f"edit_{exp['id']}"):
                    st.session_state.editing_id = exp["id"]
                    st.session_state.edit_amount = exp["amount"]
                    st.session_state.edit_date = date.fromisoformat(exp["spent_at"])
                    st.session_state.edit_category = exp["category"]
                    st.session_state.edit_payer = payer_full
                    st.session_state.edit_description = exp["description"]
                    st.session_state.edit_split = split
                    st.rerun()
            
            st.divider()

        # Modal-like section for editing
        if "editing_id" in st.session_state:
            st.divider()
            st.subheader(f"✏️ Editar Gasto #{st.session_state.editing_id}")
            with st.form("edit_form"):
                new_amount = st.number_input("Valor (R$)", value=float(st.session_state.edit_amount) if st.session_state.edit_amount else None, step=0.01)
                new_date = st.date_input("Data", value=st.session_state.edit_date)
                new_payer = st.selectbox("Quem pagou?", [u["name"] for u in users], 
                                        index=0 if st.session_state.edit_payer == user_a["name"] else 1)
                
                categorias = carregar_categorias()
                cat_index = categorias.index(st.session_state.edit_category) if st.session_state.edit_category in categorias else 0
                new_category = st.selectbox("Categoria", categorias, index=cat_index, key="edit_category_select")
                
                # Custom category logic in edit
                final_category = new_category
                if new_category == "Outro":
                    custom_cat_edit = st.text_input("Qual categoria?", placeholder="Nome da nova categoria", key="edit_custom_cat")
                    if custom_cat_edit.strip():
                        final_category = custom_cat_edit.strip()

                new_description = st.text_input("Descrição", value=st.session_state.edit_description)
                
                # Split management in edit
                current_split_a = int(st.session_state.edit_split.get(str(user_a["id"]), 0.5) * 100)
                custom_split_edit = st.checkbox("Personalizar divisão (padrão 50/50)", value=(current_split_a != 50), key="custom_split_edit_check")
                
                if custom_split_edit:
                    split_a_pct_edit = st.slider(f"{user_a['name']} (%)", 0, 100, current_split_a)
                else:
                    split_a_pct_edit = 50

                col_save, col_del, col_cancel = st.columns([1.5, 1.5, 1])
                if col_save.form_submit_button("Salvar Alterações", use_container_width=True):
                    split_json = json.dumps({
                        str(user_a["id"]): split_a_pct_edit / 100.0,
                        str(user_b["id"]): (100 - split_a_pct_edit) / 100.0
                    })
                    payer_id = user_a["id"] if new_payer == user_a["name"] else user_b["name"]
                    
                    # Add custom category if needed
                    if new_category == "Outro" and final_category != "Outro":
                        adicionar_categoria_personalizada(final_category)

                    update_expense(
                        st.session_state.editing_id,
                        int(round(new_amount * 100)) if new_amount else 0,
                        payer_id,
                        final_category,
                        new_description,
                        str(new_date),
                        split_json
                    )
                    del st.session_state.editing_id
                    st.success("Atualizado!")
                    st.rerun()
                
                if col_del.form_submit_button("🗑️ Excluir Gasto", use_container_width=True):
                    from src.database import delete_expense
                    delete_expense(st.session_state.editing_id)
                    del st.session_state.editing_id
                    st.rerun()
                
                if col_cancel.form_submit_button("Cancelar", use_container_width=True):
                    del st.session_state.editing_id
                    st.rerun()

elif page == "Fechamento":
    st.header("🔐 Fechamento")
    month = st.selectbox("📅 Selecione o mês", last_n_months(12), index=0)
    summary = compute_month_summary(list_expenses_month(month), user_a, user_b)
    
    st.write(f"### Situação de {month}")
    st.markdown(f"> {summary['suggestion']}")

    existing = get_settlement(month)
    if existing and existing["paid_at"]:
        st.success(f"✅ Fechado em {existing['paid_at']}")
    else:
        if st.button("✔️ Confirmar Fechamento", use_container_width=True, type="primary"):
            from_id, to_id, amount = summary["settle_from_to_amount"]
            if amount > 0:
                add_settlement(month, from_id, to_id, int(round(amount * 100)))
                st.success("✨ Fechamento registrado!")
            else:
                st.success("✅ Tudo limpo!")

else: # Configurações
    st.header("⚙️ Configurações")
    st.subheader("📋 Gerenciar Categorias")
    
    categorias = carregar_categorias()
    
    # Add new category
    with st.expander("➕ Adicionar Nova Categoria"):
        new_cat_name = st.text_input("Nome da categoria")
        if st.button("Adicionar"):
            if new_cat_name.strip():
                if adicionar_categoria_personalizada(new_cat_name.strip()):
                    st.success("Categoria adicionada!")
                    st.rerun()
                else:
                    st.warning("Categoria já existe ou inválida.")

    st.divider()

    # List and manage existing categories
    for cat in categorias:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.write(f"• **{cat}**")
            
            # Edit Category
            if col2.button("📝", key=f"edit_cat_{cat}"):
                st.session_state.editing_cat = cat
            
            # Delete Category (protected - defaults shouldn't be deleted easily, but we'll allow it if user wants)
            if col3.button("🗑️", key=f"del_cat_{cat}"):
                delete_category(cat)
                st.success(f"Categoria {cat} removida!")
                st.rerun()
                
    # Edit category form
    if "editing_cat" in st.session_state:
        st.divider()
        st.subheader(f"✏️ Editar Categoria: {st.session_state.editing_cat}")
        with st.form("edit_cat_form"):
            updated_name = st.text_input("Novo nome", value=st.session_state.editing_cat)
            c_save, c_cancel = st.columns(2)
            if c_save.form_submit_button("Salvar"):
                if updated_name.strip() and updated_name != st.session_state.editing_cat:
                    update_category(st.session_state.editing_cat, updated_name.strip())
                    del st.session_state.editing_cat
                    st.success("Categoria atualizada!")
                    st.rerun()
            if c_cancel.form_submit_button("Cancelar"):
                del st.session_state.editing_cat
                st.rerun()

    st.divider()
    if st.button("🔄 Resetar para Padrão (Adiciona as padrões se faltarem)"):
        salvar_categorias(get_categorias_padrao())
        st.rerun()

    st.divider()
    st.caption(f"Casa Split v2.0 | Usuários: {user_a['name']} & {user_b['name']}")
