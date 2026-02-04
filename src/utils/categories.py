from typing import List
from src.database import get_categories, add_category, upsert_default_categories

def get_categorias_padrao() -> List[str]:
    """Returns default categories names (proxied from DB/logic)."""
    return ["Outro", "Mercado", "Contas", "Transporte", "Casa", "Pets"]

def carregar_categorias() -> List[str]:
    """Loads categories from the database."""
    return get_categories()

def salvar_categorias(categorias: List[str]) -> None:
    """Saves categories (stubbed since we add individually)."""
    # In the new DB approach, we usually add categories one by one.
    # This function is kept for compatibility with the reset button.
    # We could implement a full sync if needed, but for now we'll just ensure defaults.
    upsert_default_categories()

def adicionar_categoria_personalizada(nova_categoria: str) -> bool:
    """Adds a new custom category to the database."""
    if nova_categoria.strip():
        add_category(nova_categoria.strip())
        return True
    return False
