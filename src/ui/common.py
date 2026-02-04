import streamlit as st
from datetime import datetime, timedelta
from typing import List

def last_n_months(n: int) -> List[str]:
    """Returns a list of the last n months in YYYY-MM format."""
    months = []
    today = datetime.today()
    for i in range(n):
        # Calculation slightly improved for reliability
        first_day_of_current_month = today.replace(day=1)
        target_month_date = first_day_of_current_month - timedelta(days=i*30)
        # Re-ensure it's the first day of that month to avoid issues with month lengths
        target_month_date = target_month_date.replace(day=1)
        months.append(target_month_date.strftime("%Y-%m"))
    return sorted(list(set(months)), reverse=True)

def apply_custom_css():
    """Applies custom CSS for a more premium look."""
    st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        border: 1px solid #f0f0f0;
    }
    [data-testid="stMetricValue"] {
        color: #111827 !important;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        color: #6b7280 !important;
        font-size: 0.9rem;
    }
    
    /* Premium Card for Expenses */
    .stElementContainer:has(.expense-card) {
        margin-bottom: 0px;
    }
    
    /* Button alignment fix */
    .action-btn-col {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        gap: 8px;
    }
    
    .stButton > button {
        border-radius: 8px;
        transition: all 0.2s ease;
        border: 1px solid #e5e7eb;
        background-color: white;
    }
    
    /* Vibrant style for primary buttons (like 'Salvar Gasto') */
    .stButton > button[kind="primary"] {
        background-color: #2563eb !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #1d4ed8 !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
    }
    
    .stButton > button:hover {
        border-color: #3b82f6;
        color: #3b82f6;
        background-color: #f0f7ff;
    }
    
    /* Unified Table Row Styling */
    .expense-table-row {
        border-bottom: 1px solid #f0f0f0;
        padding: 8px 0;
    }
    
    .stButton > button {
        border-radius: 8px;
        transition: all 0.2s ease;
        border: 1px solid #e5e7eb;
        background-color: white;
    }
    
    /* Mobile Card Refinements */
    .mobile-row {
        padding: 5px 0;
        border-bottom: 1px solid #f9fafb;
    }
    .mobile-row:last-child {
        border-bottom: none;
    }
    
    /* Smaller buttons for mobile row */
    .small-action-btn button {
        font-size: 0.7rem !important;
        padding: 0.1rem 0.3rem !important;
        min-height: 24px !important;
        line-height: 1 !important;
    }
    
    /* Scoped Responsive Visibility - Only affects items inside .expense-list-root */
    .desktop-marker, .mobile-marker {
        display: none;
    }

    /* Mobile View ( < 768px ) */
    @media (max-width: 768px) {
        /* Hide Desktop Wrapper inside the list */
        .expense-list-root div[data-testid="stVerticalBlockBorderWrapper"]:has(.desktop-marker) {
            display: none !important;
        }
    }

    /* Desktop View ( > 769px ) */
    @media (min-width: 769px) {
        /* Hide Mobile Wrapper inside the list */
        .expense-list-root div[data-testid="stVerticalBlockBorderWrapper"]:has(.mobile-marker) {
            display: none !important;
        }
    }

    /* Desktop Styling: Remove border to look like raw table */
    .expense-list-root div[data-testid="stVerticalBlockBorderWrapper"]:has(.desktop-marker) {
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        background-color: transparent !important;
    }

    /* Mobile Styling: Card look */
    .expense-list-root div[data-testid="stVerticalBlockBorderWrapper"]:has(.mobile-marker) {
        background-color: white !important;
        padding: 16px !important;
        border-radius: 12px !important;
        border: 1px solid #f0f0f0 !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03) !important;
        margin-bottom: 12px !important;
    }

    /* Compact spacing for mobile cards */
    .expense-list-root div[data-testid="stVerticalBlockBorderWrapper"]:has(.mobile-marker) > div {
        gap: 0px !important;
    }
    
    hr {
        margin-top: 2rem;
        margin-bottom: 2rem;
        border: 0;
        border-top: 1px solid #eee;
    }
    </style>
    """, unsafe_allow_html=True)
