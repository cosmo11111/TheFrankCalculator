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
.tbl-header { display: grid; grid-template-columns: 1fr 1.8fr 0.9fr 0.9fr 1fr 0.75fr 1fr 0.85fr 0.6fr; gap: 0; padding: 0 12px 8px; margin-bottom: 10px; border-bottom: 1px solid #e5e5e5; }
.tbl-header span { font-size: 11px; font-weight: 500; color: #999; text-transform: uppercase; letter-spacing: 0.05em; }
.tbl-header span.r { text-align: right; }
.badge { display: inline-block; font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 20px; }
.badge.full { background: #dcfce7; color: #166534; }
.badge.partial { background: #fef3c7; color: #92400e; }
.badge.none { background: #f1f5f9; color: #64748b; }
div[data-testid="stNumberInput"] label { display: none !important; }
div[data-testid="stNumberInput"] button { display: none !important; }
div[data-testid="stNumberInput"] > div { border: none !important; box-shadow: none !important; background: transparent !important; }
div[data-testid="stNumberInput"] input { font-size: 13px !important; border-radius: 6px !important; border: 1px solid #e5e5e5 !important; padding: 6px 10px !important; background: #fff !important; }
div[data-testid="stTextInput"] label { display: none !important; }
div[data-testid="stTextInput"] input { font-size: 13px !important; border-radius: 6px !important; border: 1px solid #e5e5e5 !important; padding: 6px 10px !important; background: #fff !important; }
div[data-testid="stButton"] button { font-size: 13px !important; border-radius: 7px !important; border: 1px solid #e5e5e5 !important; background: #fff !important; padding: 6px 14px !important; }
div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stHorizontalBlock"]) { gap: 0.2rem !important; }
/* Hides the dropdown arrow in selectboxes */
div[data-testid="stSelectbox"] svg[handle="arrow"] {
    display: none !important;
}

/* Adjusts padding so the text doesn't look off-center without the arrow */
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    padding-right: 10px !important;
}
.add-btn div[data-testid="stButton"] button { width: 100%; background: #fafafa !important; border: 1px dashed #d5d5d5 !important; color: #777 !important; padding: 10px !important; }
section[data-testid="stSidebar"] { background: #fafafa; border-right: 1px solid #f0f0f0; }
.status-pill { display: inline-flex; align-items: center; gap: 5px; font-size: 11px; color: #999; background: #f5f5f5; border-radius: 20px; padding: 3px 10px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: #22c55e; }
.footer { font-size: 11px; color: #bbb; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #f0f0f0; }
</style>
""", unsafe_allow_html=True)

# ── DATA SOURCES ─────────────────────────────────────────────────────────────

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQXUiVcziu72OkPGE8Wy5xhelPIXJTMs0Z1oBtqQbZ-_RS5qNOAt9q5sr23I7ejAqXrQRuKZiwy6gFi/pub?gid=1786895027&single=true&output=csv"

TAX_ENVIRONMENTS = {
    "Pension phase (0%)": 0.00,
    "Super accumulation (15%)": 0.15,
    "Marginal rate — 19%": 0.19,
    "Marginal rate — 32.5%": 0.325,
    "Marginal rate — 37%": 0.37,
    "Top marginal (47%)": 0.47,
}

# ── HELPERS ───────────────────────────────────────────────────────────────────

def fmt_aud(n): return f"${n:,.0f}" if n and n != 0 else "—"
def fmt_aud2(n): return f"${n:,.2f}" if n and n != 0 else "—"
def fmt_pct(n): return f"{n:.2f}%" if n is not None else "—"

def franking_badge(pct):
    if pct >= 100: return '<span class="badge full">100%</span>'
    if pct <= 0: return '<span class="badge none">0%</span>'
    return f'<span class="badge partial">{pct:.0f}%</span>'

# ── CACHED DATA FETCHERS ──────────────────────────────────────────────────────

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

# ── SESSION STATE ─────────────────────────────────────────────────────────────

if 'holdings' not in st.session_state:
    st.session_state.holdings = [
        {"ticker": "CBA", "units": 100.0, "id": str(uuid.uuid4())},
        {"ticker": "MQG", "units": 200.0, "id": str(uuid.uuid4())},
        {"ticker": "TLS", "units": 500.0, "id": str(uuid.uuid4())},
    ]

# ── SIDEBAR ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div style="font-size:15px;font-weight:600;color:#111;margin-bottom:4px;">Settings</div>', unsafe_allow_html=True)
    selected_env = st.selectbox("Tax environment", list(TAX_ENVIRONMENTS.keys()))
    tax_rate = TAX_ENVIRONMENTS[selected_env]

    if st.button("Refresh data from Sheet"):
        st.cache_data.clear()
        st.rerun()

# ── CALCULATION LOGIC ─────────────────────────────────────────────────────────

computed = []
total_val = total_cash = total_franking = 0

# We calculate based on what is CURRENTLY in session state
for h in st.session_state.holdings:
    ticker_clean = h['ticker'].upper().strip().replace('.AX', '')
    data = MASTER_DATA.get(ticker_clean)

    row_val = row_cash = row_frank = 0
    if data and h['units'] > 0:
        row_val   = data['price'] * h['units']
        row_cash  = row_val * (data['yield'] / 100)
        row_frank = row_cash * (data['franking'] / 100) * (30 / 70)
        
        total_val      += row_val
        total_cash     += row_cash
        total_franking += row_frank

    computed.append({
        "ticker": h['ticker'],
        "data": data,
        "val": row_val,
        "cash": row_cash,
        "frank": row_frank,
    })

gross_income  = total_cash + total_franking
tax_liability = gross_income * tax_rate
post_tax      = gross_income - tax_liability
portfolio_yld = (total_cash / total_val * 100) if total_val else 0

# ── HEADER & SUMMARY ─────────────────────────────────────────────────────────

st.markdown(f"""
<div class="page-header">
    <h1>ASX Dividend Calculator</h1>
    <span class="status-pill"><span class="status-dot"></span> Database Connected</span>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="summary-row">
  <div class="summary-card"><div class="label">Portfolio value</div><div class="value">{fmt_aud(total_val)}</div></div>
  <div class="summary-card"><div class="label">Annual income</div><div class="value green">{fmt_aud(total_cash)}</div><div class="sub">Cash dividends</div></div>
  <div class="summary-card"><div class="label">Portfolio yield</div><div class="value green">{fmt_pct(portfolio_yld)}</div></div>
  <div class="summary-card"><div class="label">Franking credits</div><div class="value">{fmt_aud(total_franking)}</div><div class="sub">Grossed-up: {fmt_aud(gross_income)}</div></div>
  <div class="summary-card"><div class="label">Post-tax income</div><div class="value">{fmt_aud(post_tax)}</div><div class="sub">{selected_env}</div></div>
</div>
""", unsafe_allow_html=True)

# ── TABLE ─────────────────────────────────────────────────────────────────────

st.markdown("""<div class="tbl-header" style="display: grid; grid-template-columns: 1fr 1.8fr 0.9fr 0.9fr 1fr 0.75fr 1fr 0.85fr 0.6fr; gap: 0; padding: 0 12px 8px; margin-bottom: 10px; border-bottom: 1px solid #e5e5e5;"><span style="text-align: left;">Ticker</span><span style="text-align: left;">Company</span><span style="text-align: left;">Units</span><span class="r">Price</span><span class="r">Value</span><span class="r">Yield</span><span class="r">Annual income</span><span class="r">Franking</span><span></span></div>""", unsafe_allow_html=True)

# --- PREPARE AUTOCOMPLETE LIST ---
ticker_options = [""] + sorted(MASTER_DATA.keys())

to_delete = None

for i, h in enumerate(st.session_state.holdings):
    c = computed[i]
    data = c['data']
    row_id = h['id']
    
    col_tick, col_name, col_units, col_price, col_val, col_yld, col_inc, col_frank, col_del = st.columns([1, 1.8, 0.9, 0.9, 1, 0.75, 1, 0.85, 0.6])

    with col_tick:
        try:
            current_idx = ticker_options.index(h['ticker'])
        except ValueError:
            current_idx = 0

        new_ticker = st.selectbox(
            "Ticker",
            options=ticker_options,
            index=current_idx,
            key=f"t_{row_id}",
            label_visibility="collapsed"
        )
        
        if new_ticker != h['ticker']:
            st.session_state.holdings[i]['ticker'] = new_ticker
            st.rerun()

    with col_units:
        new_units = st.number_input("Units", value=float(h['units']), key=f"u_{row_id}", min_value=0.0, step=1.0, format="%g", label_visibility="collapsed")
        if new_units != h['units']:
            st.session_state.holdings[i]['units'] = new_units
            st.rerun()

    # Static Data Display
    name_str = data['name'] if data else "—"
    price_str = fmt_aud2(data['price']) if data else "—"
    val_str = fmt_aud(c['val']) if c['val'] else "—"
    yld_str = fmt_pct(data['yield']) if data else "—"
    inc_str = fmt_aud(c['cash']) if c['cash'] else "—"
    frank_badge_html = franking_badge(data['franking']) if data else "—"

    with col_name: st.markdown(f'<div style="font-size:15px;color:#666;padding-top:9px;">{name_str}</div>', unsafe_allow_html=True)
    with col_price: st.markdown(f'<div style="font-size:15px;text-align:right;padding-top:9px;">{price_str}</div>', unsafe_allow_html=True)
    with col_val: st.markdown(f'<div style="font-size:15px;font-weight:600;text-align:right;padding-top:9px;">{val_str}</div>', unsafe_allow_html=True)
    with col_yld: st.markdown(f'<div style="font-size:15px;color:#166534;font-weight:500;text-align:right;padding-top:9px;">{yld_str}</div>', unsafe_allow_html=True)
    with col_inc: st.markdown(f'<div style="font-size:15px;font-weight:600;text-align:right;padding-top:9px;">{inc_str}</div>', unsafe_allow_html=True)
    with col_frank: st.markdown(f'<div style="text-align:right;padding-top:9px;">{frank_badge_html}</div>', unsafe_allow_html=True)

    with col_del:
        if st.button("✕", key=f"d_{row_id}"):
            to_delete = i

if to_delete is not None:
    st.session_state.holdings.pop(to_delete)
    st.rerun()

st.markdown('<div class="add-btn">', unsafe_allow_html=True)
if st.button("+ Add holding", use_container_width=True):
    st.session_state.holdings.append({"ticker": "", "units": 0.0, "id": str(uuid.uuid4())})
    st.rerun()

st.markdown("""<div class="footer">Franking credits calculated at 30% corp tax rate. Data synced from Google Sheet backend. Not financial advice.</div>""", unsafe_allow_html=True)
