import streamlit as st
import pandas as pd
import uuid

# --- CONFIG ---
st.set_page_config(
    layout="wide",
    page_title="ASX Dividend Tool",
    page_icon="📊"
)

# --- CUSTOM CSS ---
st.markdown("""
<style>
/* ── Global ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 2.5rem 2rem; max-width: 1200px; }
.page-header { display: flex; align-items: baseline; gap: 12px; margin-bottom: 2rem; padding-bottom: 1.25rem; border-bottom: 1px solid #f0f0f0; }
.page-header h1 { font-size: 20px; font-weight: 600; color: #111; margin: 0; }
.page-header span { font-size: 13px; color: #999; }
.summary-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 1.75rem; }
.summary-card { background: #fafafa; border: 1px solid #f0f0f0; border-radius: 10px; padding: 16px 18px; }
.summary-card .label { font-size: 11px; font-weight: 500; color: #999; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
.summary-card .value { font-size: 22px; font-weight: 600; color: #111; line-height: 1.2; }
.summary-card .value.green { color: #166534; }
.summary-card .sub { font-size: 11px; color: #aaa; margin-top: 4px; }
.tbl-header { display: grid; grid-template-columns: 1.2fr 1.8fr 0.8fr 0.8fr 1fr 0.8fr 1fr 0.8fr 0.4fr; gap: 0; padding: 0 12px 8px; margin-bottom: 10px; border-bottom: 1px solid #e5e5e5; }
.tbl-header span { font-size: 11px; font-weight: 500; color: #999; text-transform: uppercase; letter-spacing: 0.05em; }
.tbl-header span.r { text-align: right; }
.badge { display: inline-block; font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 20px; }
.badge.full { background: #dcfce7; color: #166534; }
.badge.partial { background: #fef3c7; color: #92400e; }
.badge.none { background: #f1f5f9; color: #64748b; }

/* Input Styling */
div[data-testid="stNumberInput"] label, div[data-testid="stTextInput"] label, div[data-testid="stSelectbox"] label { display: none !important; }
div[data-testid="stNumberInput"] button { display: none !important; }
div[data-testid="stNumberInput"] > div, div[data-testid="stSelectbox"] > div { border: none !important; box-shadow: none !important; background: transparent !important; }
div[data-testid="stNumberInput"] input, div[data-testid="stSelectbox"] div[data-baseweb="select"] { 
    font-size: 13px !important; border-radius: 6px !important; border: 1px solid #e5e5e5 !important; background: #fff !important; 
}
/* Hide Selectbox Arrow for Autocomplete feel */
div[data-testid="stSelectbox"] svg[handle="arrow"] { display: none !important; }

div[data-testid="stButton"] button { font-size: 13px !important; border-radius: 7px !important; border: 1px solid #e5e5e5 !important; background: #fff !important; }
.add-btn div[data-testid="stButton"] button { width: 100%; background: #fafafa !important; border: 1px dashed #d5d5d5 !important; color: #777 !important; padding: 10px !important; }
section[data-testid="stSidebar"] { background: #fafafa; border-right: 1px solid #f0f0f0; }
.footer { font-size: 11px; color: #bbb; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #f0f0f0; }
</style>
""", unsafe_allow_html=True)

# ── DATA SOURCES ──
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQXUiVcziu72OkPGE8Wy5xhelPIXJTMs0Z1oBtqQbZ-_RS5qNOAt9q5sr23I7ejAqXrQRuKZiwy6gFi/pub?gid=1786895027&single=true&output=csv"

TAX_ENVIRONMENTS = {
    "Pension phase (0%)": 0.00,
    "Super accumulation (15%)": 0.15,
    "Marginal rate — 19%": 0.19,
    "Marginal rate — 32.5%": 0.325,
    "Marginal rate — 37%": 0.37,
    "Top marginal (47%)": 0.47,
}

# ── HELPERS ──
def fmt_aud(n): return f"${n:,.0f}" if n and n != 0 else "—"
def fmt_aud2(n): return f"${n:,.2f}" if n and n != 0 else "—"
def fmt_pct(n): return f"{n:.2f}%" if n is not None else "—"

def franking_badge(pct):
    if pct >= 100: return '<span class="badge full">100%</span>'
    if pct <= 0: return '<span class="badge none">0%</span>'
    return f'<span class="badge partial">{pct:.0f}%</span>'

# ── DATA FETCHING ──
@st.cache_data(ttl=3600)
def load_master_data():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        df.columns = df.columns.str.strip()
        df['Ticker'] = df['Ticker'].astype(str).str.upper().str.replace('.AX', '', regex=False).str.strip()
        
        if 'Franking Rate (%)' in df.columns:
            df['Franking_Clean'] = df['Franking Rate (%)'].astype(str).str.replace('%', '', regex=False)
            df['Franking_Clean'] = pd.to_numeric(df['Franking_Clean'], errors='coerce').fillna(0)
        else:
            df['Franking_Clean'] = 0

        master_dict = {}
        for _, row in df.iterrows():
            master_dict[row['Ticker']] = {
                "name": row.get('Company Name', row['Ticker']),
                "price": float(row.get('Price', 0)),
                "yield": float(row.get('Dividend Yield (%)', 0)),
                "franking": float(row['Franking_Clean'])
            }
        return master_dict
    except Exception as e:
        st.error(f"Error loading sheet: {e}")
        return {}

MASTER_DATA = load_master_data()

# ── SESSION STATE ──
if 'holdings' not in st.session_state:
    st.session_state.holdings = [
        {"ticker": "CBA", "units": 289.0, "id": str(uuid.uuid4())},
        {"ticker": "MQG", "units": 249.0, "id": str(uuid.uuid4())},
        {"ticker": "ANZ", "units": 1368.0, "id": str(uuid.uuid4())},
    ]

# ── SIDEBAR ──
with st.sidebar:
    st.markdown('<div style="font-size:15px;font-weight:600;color:#111;margin-bottom:4px;">Settings</div>', unsafe_allow_html=True)
    selected_env = st.selectbox("Tax environment", list(TAX_ENVIRONMENTS.keys()), key="tax_env_sidebar")
    tax_rate = TAX_ENVIRONMENTS[selected_env]
    if st.button("Refresh data from Sheet"):
        st.cache_data.clear()
        st.rerun()

# ── CALCULATION LOGIC ──
computed = []
total_val = total_cash = total_franking = total_gross = 0

for h in st.session_state.holdings:
    ticker_clean = h['ticker'].upper().strip()
    data = MASTER_DATA.get(ticker_clean)
    row_val = row_cash = row_frank = row_gross = 0
    
    if data and h['units'] > 0:
        row_val   = data['price'] * h['units']
        row_cash  = row_val * (data['yield'] / 100)
        row_frank = row_cash * (data['franking'] / 100) * (30 / 70)
        row_gross = row_cash + row_frank
        
        total_val      += row_val
        total_cash     += row_cash
        total_franking += row_frank
        total_gross    += row_gross

    computed.append({
        "ticker": h['ticker'], "data": data, "val": row_val, 
        "cash": row_cash, "frank": row_frank, "gross": row_gross
    })

portfolio_yld = (total_cash / total_val * 100) if total_val else 0
portfolio_gross_yld = (total_gross / total_val * 100) if total_val else 0
tax_liability = (total_cash + total_franking) * tax_rate
post_tax      = (total_cash + total_franking) - tax_liability

# ── UI HEADER ──
st.markdown('<div class="page-header"><h1>ASX Dividend Calculator</h1><span>Database Connected</span></div>', unsafe_allow_html=True)

# ── TOGGLE & SUMMARY ──
col_title, col_toggle = st.columns([3, 1])
with col_toggle:
    is_gross_view = st.toggle("Show Grossed-up (Pre-tax)", value=False)

display_inc = total_gross if is_gross_view else total_cash
display_yld = portfolio_gross_yld if is_gross_view else portfolio_yld
yield_label = "Gross Yield" if is_gross_view else "Yield"
income_label = "Gross Inc." if is_gross_view else "Annual Inc."

st.markdown(f"""
<div class="summary-row">
  <div class="summary-card"><div class="label">Portfolio value</div><div class="value">{fmt_aud(total_val)}</div></div>
  <div class="summary-card"><div class="label">Annual income</div><div class="value green">{fmt_aud(display_inc)}</div><div class="sub">{"Incl. Franking" if is_gross_view else "Cash dividends"}</div></div>
  <div class="summary-card"><div class="label">Portfolio yield</div><div class="value green">{fmt_pct(display_yld)}</div></div>
  <div class="summary-card"><div class="label">Franking credits</div><div class="value">{fmt_aud(total_franking)}</div><div class="sub">Total Gross: {fmt_aud(total_gross)}</div></div>
  <div class="summary-card"><div class="label">Post-tax income</div><div class="value">{fmt_aud(post_tax)}</div><div class="sub">{selected_env}</div></div>
</div>
""", unsafe_allow_html=True)

# ── TABLE ──
st.markdown(f"""<div class="tbl-header">
    <span>Ticker</span><span>Company</span><span>Units</span><span class="r">Price</span><span class="r">Value</span>
    <span class="r">{yield_label}</span><span class="r">{income_label}</span><span class="r">Franking</span><span></span>
</div>""", unsafe_allow_html=True)

to_delete = None
for i, h in enumerate(st.session_state.holdings):
    c, data, row_id = computed[i], computed[i]['data'], h['id']
    (c_tick, c_name, c_units, c_price, c_val, c_yld, c_inc, c_frank, c_del) = st.columns([1.2, 1.8, 0.8, 0.8, 1, 0.8, 1, 0.8, 0.4])

    with c_tick:
        options = [""] + sorted(MASTER_DATA.keys())
        idx = options.index(h['ticker']) if h['ticker'] in options else 0
        new_t = st.selectbox("T", options, index=idx, key=f"t_{row_id}")
        if new_t != h['ticker']: 
            st.session_state.holdings[i]['ticker'] = new_t
            st.rerun()

    with c_units:
        new_u = st.number_input("U", value=float(h['units']), key=f"u_{row_id}", step=1.0, format="%g")
        if new_u != h['units']: 
            st.session_state.holdings[i]['units'] = new_u
            st.rerun()

    row_yield = (c['gross'] / c['val'] * 100) if is_gross_view and c['val'] else (data['yield'] if data else 0)
    row_income = c['gross'] if is_gross_view else c['cash']
    y_color = "#166534" if is_gross_view else "#666"

    with c_name: st.markdown(f'<div style="font-size:14px;color:#666;padding-top:9px;">{data["name"] if data else "—"}</div>', unsafe_allow_html=True)
    with c_price: st.markdown(f'<div style="font-size:14px;text-align:right;padding-top:9px;">{fmt_aud2(data["price"]) if data else "—"}</div>', unsafe_allow_html=True)
    with c_val: st.markdown(f'<div style="font-size:14px;font-weight:600;text-align:right;padding-top:9px;">{fmt_aud(c["val"])}</div>', unsafe_allow_html=True)
    with c_yld: st.markdown(f'<div style="font-size:14px;color:{y_color};font-weight:600;text-align:right;padding-top:9px;">{fmt_pct(row_yield)}</div>', unsafe_allow_html=True)
    with c_inc: st.markdown(f'<div style="font-size:14px;font-weight:600;text-align:right;padding-top:9px;">{fmt_aud(row_income)}</div>', unsafe_allow_html=True)
    with c_frank: st.markdown(f'<div style="text-align:right;padding-top:9px;">{franking_badge(data["franking"]) if data else "—"}</div>', unsafe_allow_html=True)
    with c_del:
        if st.button("✕", key=f"d_{row_id}"): to_delete = i

if to_delete is not None:
    st.session_state.holdings.pop(to_delete)
    st.rerun()

st.markdown('<div class="add-btn">', unsafe_allow_html=True)
if st.button("+ Add holding", use_container_width=True):
    st.session_state.holdings.append({"ticker": "", "units": 0.0, "id": str(uuid.uuid4())})
    st.rerun()

st.markdown('<div class="footer">Franking credits calculated at 30% corp tax rate. Data from Google Sheets. Not financial advice.</div>', unsafe_allow_html=True)
