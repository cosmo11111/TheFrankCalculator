import streamlit as st
import pandas as pd
 
# --- CONFIG ---
st.set_page_config(
    layout="wide",
    page_title="ASX Dividend Tool",
    page_icon="📊"
)
 
# --- CUSTOM CSS ---
st.markdown("""
<style>
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
.tbl-header { display: grid; grid-template-columns: 100px 1fr 110px 110px 120px 90px 120px 100px 36px; gap: 0; padding: 0 12px 8px; border-bottom: 1px solid #e5e5e5; }
.tbl-header span { font-size: 11px; font-weight: 500; color: #999; text-transform: uppercase; letter-spacing: 0.05em; }
.tbl-header span.r { text-align: right; }
.badge { display: inline-block; font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 20px; }
.badge.full { background: #dcfce7; color: #166534; }
.badge.partial { background: #fef3c7; color: #92400e; }
.badge.none { background: #f1f5f9; color: #64748b; }
div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input { font-size: 13px !important; border-radius: 6px !important; border: 1px solid #e5e5e5 !important; padding: 6px 10px !important; background: #fff !important; }
div[data-testid="stTextInput"] label, div[data-testid="stNumberInput"] label { display: none !important; }
div[data-testid="stNumberInput"] button { display: none !important; }
div[data-testid="stButton"] button { font-size: 13px !important; border-radius: 7px !important; border: 1px solid #e5e5e5 !important; background: #fff !important; padding: 6px 14px !important; }
.del-btn div[data-testid="stButton"] button { color: #ccc !important; border-color: transparent !important; font-size: 18px !important; padding: 2px 8px !important; }
.del-btn div[data-testid="stButton"] button:hover { color: #ef4444 !important; background: #fef2f2 !important; }
.add-btn div[data-testid="stButton"] button { width: 100%; background: #fafafa !important; border: 1px dashed #d5d5d5 !important; color: #777 !important; padding: 10px !important; }
section[data-testid="stSidebar"] { background: #fafafa; border-right: 1px solid #f0f0f0; }
.status-pill { display: inline-flex; align-items: center; gap: 5px; font-size: 11px; color: #999; background: #f5f5f5; border-radius: 20px; padding: 3px 10px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: #22c55e; }
.footer { font-size: 11px; color: #bbb; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #f0f0f0; }
</style>
""", unsafe_allow_html=True)
 
# ── DATA SOURCES ──────────────────────────────────────────────────────────────
 
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQXUiVcziu72OkPGE8Wy5xhelPIXJTMs0Z1oBtqQbZ-_RS5qNOAt9q5sr23I7ejAqXrQRuKZiwy6gFi/pub?gid=0&single=true&output=csv"
 
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
    if pct <= 0:   return '<span class="badge none">0%</span>'
    return f'<span class="badge partial">{pct:.0f}%</span>'
 
# ── CACHED DATA ───────────────────────────────────────────────────────────────
 
@st.cache_data(ttl=3600)
def load_master_data():
    try:
        import requests, io
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-AU,en;q=0.9",
        }
        session = requests.Session()
        r = session.get(SHEET_CSV_URL, headers=headers, allow_redirects=True)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = df.columns.str.strip()
        df['Ticker'] = df['Ticker'].astype(str).str.upper().str.replace('.AX', '', regex=False).str.strip()
        if 'Franking Rate (%)' in df.columns:
            df['Franking_Clean'] = pd.to_numeric(
                df['Franking Rate (%)'].astype(str).str.replace('%', '', regex=False),
                errors='coerce'
            ).fillna(0)
        else:
            df['Franking_Clean'] = 0
        master_dict = {}
        for _, row in df.iterrows():
            master_dict[row['Ticker']] = {
                "name":     row.get('Company Name', row['Ticker']),
                "price":    float(row.get('Price', 0)),
                "yield":    float(row.get('Dividend Yield (%)', 0)),
                "franking": float(row['Franking_Clean'])
            }
        return master_dict
    except Exception as e:
        st.error(f"Error loading sheet: {e}")
        return {}
 
# ── SESSION STATE ─────────────────────────────────────────────────────────────
# Each holding gets a stable numeric ID that never changes, even after deletes.
# Widget keys are built from this ID (e.g. "t_3"), not from list index.
# This prevents Streamlit from mapping the wrong widget value to the wrong row.
 
if 'holdings' not in st.session_state:
    st.session_state.holdings = [
        {"id": 1, "ticker": "CBA", "units": 100},
        {"id": 2, "ticker": "VAS", "units": 200},
        {"id": 3, "ticker": "TLS", "units": 500},
    ]
 
if 'next_id' not in st.session_state:
    st.session_state.next_id = 4
 
# Migration: add stable id to any old holdings that are missing it
# This handles the transition from the old format (no id) to the new format
for i, h in enumerate(st.session_state.holdings):
    if 'id' not in h:
        h['id'] = st.session_state.next_id
        st.session_state.next_id += 1
 
# ── LOAD DATA ─────────────────────────────────────────────────────────────────
 
MASTER_DATA = load_master_data()
 
# ── SIDEBAR ───────────────────────────────────────────────────────────────────
 
with st.sidebar:
    st.markdown('<div style="font-size:15px;font-weight:600;color:#111;margin-bottom:4px;">Settings</div>', unsafe_allow_html=True)
    selected_env = st.selectbox("Tax environment", list(TAX_ENVIRONMENTS.keys()))
    tax_rate = TAX_ENVIRONMENTS[selected_env]
 
    if st.button("Refresh data from Sheet"):
        st.cache_data.clear()
        st.rerun()
 
    st.markdown(f"""
    <div style="margin-top:2rem;padding-top:1rem;border-top:1px solid #eee;">
        <div style="font-size:11px;color:#bbb;">Database Status</div>
        <div style="font-size:12px;color:#777;margin-top:3px;">{len(MASTER_DATA)} stocks available</div>
    </div>
    """, unsafe_allow_html=True)
 
# ── HEADER ────────────────────────────────────────────────────────────────────
 
st.markdown(f"""
<div class="page-header">
    <h1>ASX Dividend Calculator</h1>
    <span class="status-pill"><span class="status-dot"></span> Database Connected</span>
</div>
""", unsafe_allow_html=True)
 
# ── SYNC WIDGET STATE → HOLDINGS ──────────────────────────────────────────────
# Read the latest widget values back into holdings BEFORE computing.
# This must happen before any calculation so that edits made in the current
# render cycle are reflected immediately rather than one cycle behind.
 
for h in st.session_state.holdings:
    rid = h['id']
    if f"t_{rid}" in st.session_state:
        h['ticker'] = st.session_state[f"t_{rid}"].upper().strip()
    if f"u_{rid}" in st.session_state:
        h['units'] = float(st.session_state[f"u_{rid}"])
 
# ── COMPUTE TOTALS ────────────────────────────────────────────────────────────
 
computed = []
total_val = total_cash = total_franking = 0
 
for h in st.session_state.holdings:
    ticker_clean = h['ticker'].replace('.AX', '').upper().strip()
    data = MASTER_DATA.get(ticker_clean)
    row_val = row_cash = row_frank = 0
    if data and h['units'] > 0:
        row_val   = data['price'] * h['units']
        row_cash  = row_val * (data['yield'] / 100)
        row_frank = row_cash * (data['franking'] / 100) * (30 / 70)
        total_val      += row_val
        total_cash     += row_cash
        total_franking += row_frank
    computed.append({"data": data, "val": row_val, "cash": row_cash, "frank": row_frank})
 
gross_income  = total_cash + total_franking
tax_liability = gross_income * tax_rate
post_tax      = gross_income - tax_liability
portfolio_yld = (total_cash / total_val * 100) if total_val else 0
 
# ── SUMMARY CARDS ─────────────────────────────────────────────────────────────
 
st.markdown(f"""
<div class="summary-row">
  <div class="summary-card"><div class="label">Portfolio value</div><div class="value">{fmt_aud(total_val)}</div></div>
  <div class="summary-card"><div class="label">Annual income</div><div class="value green">{fmt_aud(total_cash)}</div><div class="sub">Cash dividends</div></div>
  <div class="summary-card"><div class="label">Portfolio yield</div><div class="value green">{fmt_pct(portfolio_yld)}</div></div>
  <div class="summary-card"><div class="label">Franking credits</div><div class="value">{fmt_aud(total_franking)}</div><div class="sub">Grossed-up: {fmt_aud(gross_income)}</div></div>
  <div class="summary-card"><div class="label">Post-tax income</div><div class="value">{fmt_aud(post_tax)}</div><div class="sub">{selected_env}</div></div>
</div>
""", unsafe_allow_html=True)
 
# ── TABLE HEADER ──────────────────────────────────────────────────────────────
 
st.markdown("""
<div class="tbl-header">
  <span>Ticker</span><span>Company</span><span class="r">Units</span>
  <span class="r">Price</span><span class="r">Value</span><span class="r">Yield</span>
  <span class="r">Annual income</span><span class="r">Franking</span><span></span>
</div>
""", unsafe_allow_html=True)
 
# ── HOLDINGS ROWS ─────────────────────────────────────────────────────────────
 
to_delete = None
 
for i, h in enumerate(st.session_state.holdings):
    rid  = h['id']
    c    = computed[i]
    data = c['data']
 
    col_tick, col_name, col_units, col_price, col_val, col_yld, col_inc, col_frank, col_del = st.columns(
        [1, 1.8, 0.9, 0.9, 1, 0.75, 1, 0.85, 0.3]
    )
 
    with col_tick:
        # Key is stable ID-based — survives any reorder or delete
        st.text_input("Ticker", value=h['ticker'], key=f"t_{rid}", placeholder="CBA")
 
    with col_units:
        st.number_input("Units", value=float(h['units']), key=f"u_{rid}", min_value=0.0, step=1.0, format="%g")
 
    with col_name:
        name_str = data['name'] if data else "—"
        st.markdown(f'<div style="font-size:13px;color:#666;padding-top:8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{name_str}</div>', unsafe_allow_html=True)
    with col_price:
        st.markdown(f'<div style="font-size:13px;text-align:right;padding-top:8px;">{fmt_aud2(data["price"]) if data else "—"}</div>', unsafe_allow_html=True)
    with col_val:
        st.markdown(f'<div style="font-size:13px;font-weight:600;text-align:right;padding-top:8px;">{fmt_aud(c["val"]) if c["val"] else "—"}</div>', unsafe_allow_html=True)
    with col_yld:
        st.markdown(f'<div style="font-size:13px;color:#166534;font-weight:500;text-align:right;padding-top:8px;">{fmt_pct(data["yield"]) if data else "—"}</div>', unsafe_allow_html=True)
    with col_inc:
        st.markdown(f'<div style="font-size:13px;font-weight:600;text-align:right;padding-top:8px;">{fmt_aud(c["cash"]) if c["cash"] else "—"}</div>', unsafe_allow_html=True)
    with col_frank:
        st.markdown(f'<div style="text-align:right;padding-top:8px;">{franking_badge(data["franking"]) if data else "—"}</div>', unsafe_allow_html=True)
    with col_del:
        st.markdown('<div class="del-btn">', unsafe_allow_html=True)
        if st.button("×", key=f"d_{rid}"):
            to_delete = rid
        st.markdown('</div>', unsafe_allow_html=True)
 
# Delete by stable ID — never touches list index
if to_delete is not None:
    st.session_state.holdings = [h for h in st.session_state.holdings if h['id'] != to_delete]
    st.rerun()
 
# ── ADD ROW ───────────────────────────────────────────────────────────────────
 
st.markdown('<div class="add-btn">', unsafe_allow_html=True)
if st.button("+ Add holding", use_container_width=True):
    st.session_state.holdings.append({
        "id":     st.session_state.next_id,
        "ticker": "",
        "units":  0
    })
    st.session_state.next_id += 1
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)
 
# ── FOOTER ────────────────────────────────────────────────────────────────────
 
st.markdown("""
<div class="footer">
    Franking credits calculated at 30% corp tax rate.
    Data synced from Google Sheet backend. Not financial advice.
</div>
""", unsafe_allow_html=True)
