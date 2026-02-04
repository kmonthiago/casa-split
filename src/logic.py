import json
from typing import Dict, List, Any, Tuple

def compute_month_summary(expenses: List[Dict[str, Any]], user_a: Dict[str, Any], user_b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes the summary of expenses for a month.
    
    Args:
        expenses: List of expense dictionaries.
        user_a: Dictionary with user A information (id, name).
        user_b: Dictionary with user B information (id, name).
        
    Returns:
        A dictionary containing total, paid amounts, quotas, balances and suggestions.
    """
    a_id, b_id = str(user_a["id"]), str(user_b["id"])
    paid_a = paid_b = 0.0
    quota_a = quota_b = 0.0
    total = 0.0

    for e in expenses:
        amount = float(e["amount"])
        total += amount
        payer = str(e["payer_user_id"])
        
        try:
            split = json.loads(e["split_json"])
        except (json.JSONDecodeError, TypeError):
            split = {a_id: 0.5, b_id: 0.5}
            
        sa = float(split.get(a_id, 0.5))
        sb = float(split.get(b_id, 0.5))

        quota_a += amount * sa
        quota_b += amount * sb

        if payer == a_id:
            paid_a += amount
        elif payer == b_id:
            paid_b += amount

    bal_a = paid_a - quota_a
    bal_b = paid_b - quota_b

    if bal_a > 0:
        suggestion = f"Para equalizar: Pix de R$ {bal_a:.2f} de {user_b['name']} para {user_a['name']}."
        settle = (user_b["id"], user_a["id"], bal_a)
    elif bal_b > 0:
        suggestion = f"Para equalizar: Pix de R$ {bal_b:.2f} de {user_a['name']} para {user_b['name']}."
        settle = (user_a["id"], user_b["id"], bal_b)
    else:
        suggestion = "Perfeito: não há nada a acertar neste mês."
        settle = (user_a["id"], user_b["id"], 0.0)

    return {
        "total": total,
        "paid_a": paid_a, "paid_b": paid_b,
        "quota_a": quota_a, "quota_b": quota_b,
        "bal_a": bal_a, "bal_b": bal_b,
        "suggestion": suggestion,
        "settle_from_to_amount": settle
    }
