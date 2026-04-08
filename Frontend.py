import streamlit as st
import pandas as pd
import uuid
from streamlit_javascript import st_javascript

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="ASX Dividend Tool", page_icon="📊")

# --- CUSTOM CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

/* Global & Layout */
html, body, .block-container { font-family: 'Inter', sans-serif !important; }
.block-container { padding: 0rem 2.5rem 2rem !important; max-width: 1200px; }
#MainMenu, footer, header { visibility: hidden; }

/* Sidebar Styling for Mobile Hamburger */
[data-testid="stSidebar"] { background-color: #fafafa; border-right: 1px solid #f0f0f0; }
[data-testid="stSidebar"] .stMarkdown h3 { font-size: 18px; font-weight: 600; margin-bottom: 1rem; }

/* Existing Styles... (keeping your original CSS for cards and tables) */
.page-header { display: flex; align-items: baseline; gap: 12px; margin-bottom: 2rem; padding-bottom: 1.25rem; border-bottom: 1px solid #f0f0f0; }
.summary-card { background: #fafafa; border: 1px solid #f0f0f0; border-radius: 10px; padding: 16px 18px; }
.summary-card .label { font-size: 11px; font-weight: 500; color: #999; text-transform: uppercase; margin-bottom: 6px; }
.summary-card .value { font-size: 22px; font-weight: 600; color: #111; }
.mobile-summary { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 1rem; }
.mobile-summary .card { background: #fafafa; border: 1px solid #f0f0f0; border-radius: 10px; padding: 14px 16px; }
.mobile-summary .label { font-size: 11px; font-weight: 500; color: #999; text-transform: uppercase; }
.mobile-summary .value { font-size: 20px; font-weight: 600; color: #111; }

/* The Toggle/Button styling from your prompt */
button[key^="lnk_assumptions"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    color: #aaa !important;
    font-size: 11px !important;
}
</style>
""", unsafe_allow_html=True)

# ── DATA & HELPERS ──
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQXUiVcziu72OkPGE8Wy5xhelPIXJTMs0Z1oBtqQbZ-_RS5qNOAt9q5sr23I7ejAqXrQRuKZiwy6gFi/pub?gid=1786895027&single=true&output=csv"
TAX_ENVIRONMENTS = {
    "Marginal rate — 32.5%": 0.325, 
    "Pension phase — 0%": 0.0, 
    "Super accumulation — 15%": 0.15, 
    "Marginal rate — 18%": 0.18, 
    "Marginal rate — 37%": 0.37, 
    "Top marginal — 47%": 0.47
}

width = st_javascript("window.innerWidth")
is_mobile = width < 800 if width else False

def fmt_aud(n): return f"${n:,.0f}" if n else "—"
def fmt_aud2(n): return f"${n:,.2f}" if n else "—"
def fmt_pct(n): return f"{n:.2f}%" if n is not None else "—"

@st.dialog("Tax Assumptions")
def show_assumptions():
    st.markdown("### Australian Tax Logic")
    st.markdown("- **Corporate Tax:** Fixed at **30%**.\n- **Medicare Levy:** Included in marginal rates.")
    if st.button("Close"): st.rerun()

@st.cache_data(ttl=3600)
def load_master_data():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        df.columns = df.columns.str.strip()
        df['Ticker'] = df['Ticker'].astype(str).str.upper().str.replace('.AX', '', regex=False).str.strip()
        return {row['Ticker']: {
            "name": row.get('Company Name', row['Ticker']),
            "price": float(row.get('Price', 0)),
            "yield": float(row.get('Dividend Yield (%)', 0)),
            "franking": float(pd.to_numeric(str(row.get('Franking Rate (%)', '0')).replace('%',''), errors='coerce') or 0)
        } for _, row in df.iterrows()}
    except: return {}

MASTER_DATA = load_master_data()

# ── SESSION STATE ──
if 'holdings' not in st.session_state:
    st.session_state.holdings = [
        {"ticker": "CBA", "units": 296.0, "custom_p": 0.0, "custom_y": 0.0, "id": str(uuid.uuid4())},
        {"ticker": "ANZ", "units": 1386.0, "custom_p": 0.0, "custom_y": 0.0, "id": str(uuid.uuid4())},
    ]

# ── TOOLBAR LOGIC (Adaptive) ──
if is_mobile:
    with st.sidebar:
        st.markdown("### Settings")
        is_gross_view = st.toggle("Grossed-up Yield", key="m_gross")
        is_edit_mode = st.toggle("Price & Yield Override", key="m_manual")
        selected_env = st.selectbox("Tax Environment", list(TAX_ENVIRONMENTS.keys()))
        tax_rate = TAX_ENVIRONMENTS[selected_env]
        if st.button("How to Use", use_container_width=True):
            st.session_state.guide_step = "welcome"
            st.rerun()
else:
    col_g, col_m, col_h, col_t = st.columns([1.5, 1.5, 1, 1.5])
    is_gross_view = col_g.toggle("Grossed-up Yield", key="d_gross")
    is_edit_mode = col_m.toggle("Manual Override", key="d_manual")
    if col_h.button("How to Use"): st.session_state.guide_step = "welcome"; st.rerun()
    selected_env = col_t.selectbox("Tax", list(TAX_ENVIRONMENTS.keys()), label_visibility="collapsed")
    tax_rate = TAX_ENVIRONMENTS[selected_env]

# ── CALCULATIONS ──
computed = []
t_val = t_cash = t_frank = 0

for h in st.session_state.holdings:
    data = MASTER_DATA.get(h['ticker'].upper())
    p = h['custom_p'] if (is_edit_mode and h['custom_p'] > 0) else (data['price'] if data else 0)
    y = h['custom_y'] if (is_edit_mode and h['custom_y'] > 0) else (data['yield'] if data else 0)
    f = data['franking'] if data else 0
    
    val = p * h['units']
    cash = val * (y / 100)
    frank = cash * (f / 100) * (30/70)
    
    t_val += val; t_cash += cash; t_frank += frank
    computed.append({"val": val, "cash": cash, "gross": cash + frank, "p": p, "y": y, "f": f})

t_gross = t_cash + t_frank
portfolio_yld = ((t_gross if is_gross_view else t_cash) / t_val * 100) if t_val else 0
post_tax = t_gross * (1 - tax_rate)

# ── MOBILE UI ──
if is_mobile:
    st.markdown(f"""
    <div class="mobile-summary">
        <div class="card"><div class="label">Value</div><div class="value">{fmt_aud(t_val)}</div></div>
        <div class="card"><div class="label">Income</div><div class="value">{fmt_aud(t_gross if is_gross_view else t_cash)}</div></div>
        <div class="card"><div class="label">Yield</div><div class="value">{fmt_pct(portfolio_yld)}</div></div>
        <div class="card"><div class="label">Post-Tax</div><div class="value">{fmt_aud(post_tax)}</div></div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("+ Add New Holding", use_container_width=True):
        st.session_state.holdings.append({"ticker": "", "units": 0, "custom_p": 0.0, "custom_y": 0.0, "id": str(uuid.uuid4())})
        st.rerun()

    for i, h in enumerate(st.session_state.holdings):
        c = computed[i]
        label = f"**{h['ticker'] or 'New'} | {fmt_aud(c['val'])} | {fmt_pct(c['y'])}**"
        with st.expander(label):
            h['ticker'] = st.selectbox("Ticker", [""] + list(MASTER_DATA.keys()), 
                                     index=([""] + list(MASTER_DATA.keys())).index(h['ticker']) if h['ticker'] in MASTER_DATA else 0,
                                     key=f"m_t_{h['id']}")
            h['units'] = st.number_input("Units", value=float(h['units']), key=f"m_u_{h['id']}")
            
            if is_edit_mode:
                h['custom_p'] = st.number_input("Price Override", value=float(h['custom_p']), key=f"m_cp_{h['id']}")
                h['custom_y'] = st.number_input("Yield Override", value=float(h['custom_y']), key=f"m_cy_{h['id']}")
            
            if st.button("🗑️ Remove", key=f"del_{h['id']}", use_container_width=True):
                st.session_state.holdings.pop(i)
                st.rerun()

    # The Assumption Link (Fixed for Mobile)
    st.markdown("---")
    if st.button("View calculation assumptions", key="lnk_assumptions_mob"):
        show_assumptions()

# ── DESKTOP UI ──
else:
    # ── SUMMARY ──
    st.markdown(f"""<div class="summary-row">
        <div class="summary-card"><div class="label">Portfolio Value</div><div class="value">{fmt_aud(t_val)}</div></div>
        <div class="summary-card"><div class="label">Annual Income</div><div class="value green">{fmt_aud(t_gross if is_gross_view else t_cash)}</div></div>
        <div class="summary-card"><div class="label">Portfolio Yield</div><div class="value green">{fmt_pct((t_gross/t_val*100) if is_gross_view and t_val else (t_cash/t_val*100) if t_val else 0)}</div></div>
        <div class="summary-card"><div class="label">Franking</div><div class="value">{fmt_aud(t_frank)}</div></div>
        <div class="summary-card"><div class="label">Post-Tax</div><div class="value">{fmt_aud(post_tax)}</div></div>
    </div>""", unsafe_allow_html=True)
    
    # ── TABLE ──
    yield_head = "Gross Yield" if is_gross_view else "Yield"
    inc_head = "Gross Inc." if is_gross_view else "Annual Inc."
    
    st.markdown(f"""
    <div class="tbl-header">
        <span>Ticker</span>
        <span>Company</span>
        <span>Units</span>
        <span class="r">Price {info_icon('Price generated each day at 10:30am AEST from Yahoo Finance. ')}</span>
        <span class="r">Value</span>
        <span class="r">{yield_head} {info_icon('Dividend yield generated from Yahoo Finance and is the Forward dividend yield. Usually the latest dividend is annualized and is represented as the dividend / share price')}</span>
        <span class="r">{inc_head} {info_icon('Annual Income is the total value of the holding multiplied by the yield.')}</span>
        <span class="r">Franking {info_icon('The extent to which an entity has allocated franking credits to a frankable distribution is referred to as the franking percentage.')}</span>
        <span></span>
    </div>
    """, unsafe_allow_html=True)
        
    to_del = None
    
    for i, h in enumerate(st.session_state.holdings):
            c, data, rid = computed[i], MASTER_DATA.get(h['ticker'].upper().strip()), h['id']
            cols = st.columns([1.2, 1.8, 0.7, 0.9, 1.0, 0.9, 1.1, 0.9, 0.6])
        
            with cols[0]: # Ticker
                opts = [""] + sorted(MASTER_DATA.keys())
                new_t = st.selectbox("T", opts, index=opts.index(h['ticker']) if h['ticker'] in opts else 0, key=f"t_{rid}", label_visibility="collapsed")
                if new_t != h['ticker']: st.session_state.holdings[i]['ticker'] = new_t; st.rerun()
        
            with cols[2]: # Units
                new_u = st.number_input("U", value=float(h['units']), key=f"u_{rid}", format="%g", label_visibility="collapsed")
                if new_u != h['units']: st.session_state.holdings[i]['units'] = new_u; st.rerun()
        
            with cols[3]: # Price
                if is_edit_mode:
                    new_p = st.number_input("P", value=float(c['p']), key=f"p_{rid}", format="%g", label_visibility="collapsed")
                    if new_p != h['custom_p']: st.session_state.holdings[i]['custom_p'] = new_p; st.rerun()
                else: st.markdown(f'<div style="text-align:right;padding-top:9px;">{fmt_aud2(c["p"])}</div>', unsafe_allow_html=True)
        
            with cols[5]: # Yield
                if is_edit_mode:
                    new_y = st.number_input("Y", value=float(c['y']), key=f"y_{rid}", format="%g", label_visibility="collapsed")
                    if new_y != h['custom_y']: st.session_state.holdings[i]['custom_y'] = new_y; st.rerun()
                else:
                    y_val = (c['gross']/c['val']*100) if is_gross_view and c['val'] else c['y']
                    st.markdown(f'<div style="text-align:right;padding-top:9px;color:{"#166534" if is_gross_view else "#666"};">{fmt_pct(y_val)}</div>', unsafe_allow_html=True)
        
            # Static Columns
            with cols[1]: st.markdown(f'<div style="color:#666;padding-top:9px;">{data["name"] if data else "—"}</div>', unsafe_allow_html=True)
            with cols[4]: st.markdown(f'<div style="font-weight:600;text-align:right;padding-top:9px;">{fmt_aud(c["val"])}</div>', unsafe_allow_html=True)
            with cols[6]: st.markdown(f'<div style="font-weight:600;text-align:right;padding-top:9px;">{fmt_aud(c["gross"] if is_gross_view else c["cash"])}</div>', unsafe_allow_html=True)
            with cols[7]: st.markdown(f'<div style="text-align:right;padding-top:9px;">{franking_badge(c["f"])}</div>', unsafe_allow_html=True)
            with cols[8]: 
                if st.button("✕", key=f"d_{rid}"): to_del = i
        
    if to_del is not None: st.session_state.holdings.pop(to_del); st.rerun()
        
    # 1. The Add Button (STAYS AS A REGULAR BUTTON)
    if st.button("+ Add Holding", use_container_width=True, key="add_new_final"):
        st.session_state.holdings.append({"ticker": "", "units": 0.0, "custom_p": 0.0, "custom_y": 0.0, "id": str(uuid.uuid4())})
        st.rerun()
    
    # 2. The Subtle Link Row
    if not st.session_state.get("guide_step"):
        if st.button("Calculation assumptions", key="lnk_assumptions"):
            show_assumptions()


