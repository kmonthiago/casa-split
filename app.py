import os
import json
import streamlit as st
from datetime import date

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
from parser import parse_quick_input

st.set_page_config(page_title="Casa Split", layout="centered")

APP_PASSWORD = os.getenv("APP_PASSWORD", "")

def require_password():
    if not APP_PASSWORD:
        return True  # se não definir senha, não bloqueia

    if st.session_state.get("auth_ok"):
        return True

    pw = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if pw == APP_PASSWORD:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()

def last_n_months(n=12):
    d = date.today().replace(day=1)
    months = []
    for _ in range(n):
        months.append(f"{d.year}-{d.month:02d}")
        if d.month == 1:
            d = d.replace(year=d.year - 1, month=12)
        else:
            d = d.replace(month=d.month - 1)
    return months

require_password()

init_db()
upsert_default_users(user_a_name="Thiago", user_b_name="Marina")
users = get_users()
user_a = users[0]  # Thiago
user_b = users[1]  # Marina

st.sidebar.title("Casa Split")
page = st.sidebar.radio("Menu", ["Adicionar gasto", "Resumo do mês", "Fechamento", "Configurações"])

DEFAULT_SPLIT = (0.5, 0.5)

if page == "Adicionar gasto":
    st.header("Adicionar gasto")

    st.subheader("Entrada rápida (linguagem natural)")
    quick = st.text_input("Digite o gasto", placeholder="mercado 327,90 angeloni hoje 60/40 eu paguei")

    col1, col2 = st.columns([1, 1])

    if col1.button("Interpretar"):
        parsed = parse_quick_input(
            quick,
            user_a_name=user_a["name"],
            user_b_name=user_b["name"],
            default_split=DEFAULT_SPLIT
        )
        if not parsed:
            st.warning("Não consegui interpretar. Inclua um valor, ex: 'mercado 127,90 hoje eu paguei'.")
        st.session_state["parsed"] = parsed

    parsed = st.session_state.get("parsed")
    if parsed is None and quick.strip():
        st.caption("Dica: inclua um valor numérico (ex: 127,90) e opcionalmente categoria (mercado, luz, condominio).")

    if parsed:
        st.info(
            f"Preview: R$ {parsed['amount']:.2f} | {parsed['category']} | Pagador: {parsed['payer']} | "
            f"Split: {int(parsed['split_a']*100)}/{int(parsed['split_b']*100)} | Data: {parsed['spent_at']} | "
            f"{parsed['description']}"
        )
        if col2.button("Salvar (preview)"):
            split_json = json.dumps({str(user_a["id"]): parsed["split_a"], str(user_b["id"]): parsed["split_b"]})
            payer_id = user_a["id"] if parsed["payer"] == user_a["name"] else user_b["id"]
            add_expense(
                amount_cents=int(round(parsed["amount"] * 100)),
                payer_user_id=payer_id,
                category=parsed["category"],
                description=parsed["description"],
                spent_at=parsed["spent_at"],
                split_json=split_json
            )
            st.success("Gasto salvo.")
            st.session_state["parsed"] = None

    st.divider()
    st.subheader("Formulário manual")

    amount = st.number_input("Valor (R$)", min_value=0.0, step=1.0, format="%.2f")
    payer = st.selectbox("Pagador", [user_a["name"], user_b["name"]])
    category = st.selectbox("Categoria", ["Moradia", "Contas", "Mercado", "Casa", "Móveis & Eletro", "Pets", "Transporte", "Outros"])
    split_mode = st.radio("Split", ["50/50", "60/40", "70/30", "Personalizado"], horizontal=True)

    if split_mode == "50/50":
        split_a, split_b = 0.5, 0.5
    elif split_mode == "60/40":
        split_a, split_b = 0.6, 0.4
    elif split_mode == "70/30":
        split_a, split_b = 0.7, 0.3
    else:
        split_a_pct = st.number_input(f"{user_a['name']} (%)", min_value=0, max_value=100, value=50)
        split_b_pct = 100 - split_a_pct
        split_a, split_b = split_a_pct/100.0, split_b_pct/100.0
        st.caption(f"{user_b['name']} (%) = {int(split_b*100)}")

    spent_at = st.date_input("Data do gasto", value=date.today())
    description = st.text_input("Descrição", placeholder="ex: Angeloni / materiais limpeza")

    colA, colB = st.columns([1, 1])
    if colA.button("Salvar"):
        split_json = json.dumps({str(user_a["id"]): split_a, str(user_b["id"]): split_b})
        payer_id = user_a["id"] if payer == user_a["name"] else user_b["id"]
        add_expense(
            amount_cents=int(round(amount * 100)),
            payer_user_id=payer_id,
            category=category,
            description=description.strip(),
            spent_at=str(spent_at),
            split_json=split_json
        )
        st.success("Gasto salvo.")

elif page == "Resumo do mês":
    st.header("Resumo do mês")
    month = st.selectbox("Mês", last_n_months(12), index=0)
    expenses = list_expenses_month(month)

    summary = compute_month_summary(expenses, user_a, user_b)
    st.metric("Total do mês", f"R$ {summary['total']:.2f}")

    st.write(f"{user_a['name']} pagou: R$ {summary['paid_a']:.2f}")
    st.write(f"{user_b['name']} pagou: R$ {summary['paid_b']:.2f}")

    st.divider()
    st.subheader("Saldo")
    st.write(f"{user_a['name']} deveria pagar: R$ {summary['quota_a']:.2f} | Saldo: R$ {summary['bal_a']:.2f}")
    st.write(f"{user_b['name']} deveria pagar: R$ {summary['quota_b']:.2f} | Saldo: R$ {summary['bal_b']:.2f}")

    st.success(summary["suggestion"])

    st.divider()
    st.subheader("Gastos do mês")
    st.dataframe(expenses, use_container_width=True)

elif page == "Fechamento":
    st.header("Fechamento")
    month = st.selectbox("Mês", last_n_months(12), index=0)

    expenses = list_expenses_month(month)
    summary = compute_month_summary(expenses, user_a, user_b)
    st.info(summary["suggestion"])

    existing = get_settlement(month)
    if existing and existing["paid_at"]:
        st.success(f"Mês já fechado em {existing['paid_at']}.")
    else:
        if st.button("Marcar como pago"):
            from_id, to_id, amount = summary["settle_from_to_amount"]
            if amount > 0:
                add_settlement(month, from_id, to_id, int(round(amount * 100)))
                st.success("Fechamento registrado.")
            else:
                st.success("Nada a acertar neste mês.")

else:
    st.header("Configurações (mini)")
    st.write("Usuários fixos: Thiago e Marina")
    st.write("Split padrão: 50/50")
    st.write("Categorias: padrão do MVP")
