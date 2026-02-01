import re
from datetime import date, timedelta

CATEGORY_KEYWORDS = {
    "Mercado": ["mercado", "supermercado", "angeloni", "giassi", "condor", "hortifruti"],
    "Contas": ["luz", "celesc", "água", "agua", "internet", "vivo", "claro", "gás", "gas"],
    "Moradia": ["condominio", "condomínio", "iptu", "taxa lixo", "seguro"],
    "Casa": ["limpeza", "manutenção", "manutencao", "conserto", "lâmpada", "lampada", "chaveiro", "ferragem"],
    "Móveis & Eletro": ["sofa", "sofá", "cama", "cadeira", "mesa", "geladeira", "microondas", "móvel", "movel", "eletro"],
    "Transporte": ["gasolina", "combustível", "combustivel", "uber", "99"],
    "Pets": ["pet", "ração", "racao", "veterinário", "veterinario", "banho", "tosa"],
}

def parse_amount(text: str):
    m = re.search(r"(\d{1,3}(\.\d{3})*(,\d{2})|\d+(,\d{2})|\d+(\.\d{2}))", text)
    if not m:
        return None
    raw = m.group(1)
    raw = raw.replace(".", "").replace(",", ".")
    return float(raw)

def parse_split(text: str, default_split):
    m = re.search(r"(\d{1,2})\s*/\s*(\d{1,2})", text)
    if not m:
        return default_split
    a = int(m.group(1))
    b = int(m.group(2))
    s = a + b
    if s == 0:
        return default_split
    return (a / s, b / s)

def parse_date(text: str):
    t = text.lower()
    if "hoje" in t:
        return date.today()
    if "ontem" in t:
        return date.today() - timedelta(days=1)
    m = re.search(r"(\d{1,2})/(\d{1,2})(/(\d{2,4}))?", t)
    if m:
        d = int(m.group(1)); mo = int(m.group(2))
        y = int(m.group(4)) if m.group(4) else date.today().year
        if y < 100:
            y += 2000
        return date(y, mo, d)
    return date.today()

def parse_payer(text: str, user_a_name: str, user_b_name: str):
    t = text.lower()
    if "eu" in t:
        return user_a_name
    if "ela" in t:
        return user_b_name
    if user_a_name.lower() in t:
        return user_a_name
    if user_b_name.lower() in t:
        return user_b_name
    return user_a_name

def detect_category(text: str):
    t = text.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if kw in t:
                return cat
    return "Outros"

def clean_description(text: str):
    t = re.sub(r"(\d{1,3}(\.\d{3})*(,\d{2})|\d+(,\d{2})|\d+(\.\d{2}))", "", text)
    t = re.sub(r"(\d{1,2}\s*/\s*\d{1,2})", "", t)
    t = t.replace("hoje", "").replace("ontem", "")
    return " ".join(t.split()).strip()

def parse_quick_input(text: str, user_a_name: str, user_b_name: str, default_split=(0.5, 0.5)):
    if not text or not text.strip():
        return None

    amount = parse_amount(text)
    if amount is None:
        return None

    split_a, split_b = parse_split(text, default_split)
    spent_at = parse_date(text)
    payer = parse_payer(text, user_a_name, user_b_name)
    category = detect_category(text)
    description = clean_description(text) or category

    return {
        "amount": amount,
        "split_a": split_a,
        "split_b": split_b,
        "spent_at": str(spent_at),
        "payer": payer,
        "category": category,
        "description": description
    }

