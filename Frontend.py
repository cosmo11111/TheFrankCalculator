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

/* Header & Toolbar */
.page-header { display: flex; align-items: baseline; gap: 12px; margin-bottom: 2rem; padding-bottom: 1.25rem; border-bottom: 1px solid #f0f0f0; }
.page-header h1 { font-size: 20px; font-weight: 600; color: #111; margin: 0; }
.toolbar { margin-bottom: 1rem; }
.toolbar .element-container { padding-bottom: 0 !important; }

/* Summary Cards */
.summary-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 1.75rem; }
.summary-card { background: #fafafa; border: 1px solid #f0f0f0; border-radius: 10px; padding: 16px 18px; }
.summary-card .label { font-size: 11px; font-weight: 500; color: #999; text-transform: uppercase; margin-bottom: 6px; }
.summary-card .value { font-size: 22px; font-weight: 600; color: #111; }
.summary-card .value.green { color: #166534; }
.summary-card .sub { font-size: 11px; color: #aaa; margin-top: 4px; }

/* Mobile Summary */
.mobile-summary { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 1rem; }
.mobile-summary .card { background: #fafafa; border: 1px solid #f0f0f0; border-radius: 10px; padding: 14px 16px; }
.mobile-summary .label { font-size: 11px; font-weight: 500; color: #999; text-transform: uppercase; margin-bottom: 4px; }
.mobile-summary .value { font-size: 20px; font-weight: 600; color: #111; }

/* Table Elements */
.tbl-header { display: grid; grid-template-columns: 1.2fr 1.8fr 0.7fr 0.9fr 1fr 0.9fr 1.1fr 0.9fr 0.6fr; gap: 0; padding: 0 12px 8px; margin-bottom: 10px; border-bottom: 1px solid #e5e5e5; }
.tbl-header span { font-size: 11px; font-weight: 500; color: #999; text-transform: uppercase; }
.tbl-header span.r { text-align: right; }
.badge { display: inline-block; font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 20px; }
.badge.full { background: #dcfce7; color: #166534; }
.badge.none { background: #f1f5f9; color: #64748b; }
.badge.partial { background: #fef3c7; color: #92400e; }

/* Expander Headers */
div[data-testid="stExpanderHeader"] p, div[data-testid="stExpanderHeader"] span, div[data-testid="stExpanderHeader"] { color: #111 !important; }
div[data-testid="stExpanderHeader"] > div:first-child, div[data-testid="stExpanderHeader"] > div:first-child * { color: #111 !important; -webkit-text-fill-color: #111 !important; }
div[data-testid="stExpanderHeader"] .math-inline, div[data-testid="stExpanderHeader"] .language-math, div[data-testid="stExpanderHeader"] .st-emotion-cache-119tkyc, div[data-testid="stExpanderHeader"] .e19xqh4f0 { color: #111 !important; -webkit-text-fill-color: #111 !important; }

/* Widgets & Inputs */
div[data-testid="stSelectbox"] svg[handle="arrow"] { display: none !important; }
div[data-testid="stButton"] button { font-size: 13px !important; border-radius: 7px !important; border: 1px solid #e5e5e5 !important; }
.footer { font-size: 11px; color: #bbb; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #f0f0f0; }

/* Mobile Adjustments */
@media (max-width: 800px) { input, select, textarea { font-size: 16px !important; } }
</style>
""", unsafe_allow_html=True)

# ── DATA SOURCES ──
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQXUiVcziu72OkPGE8Wy5xhelPIXJTMs0Z1oBtqQbZ-_RS5qNOAt9q5sr23I7ejAqXrQRuKZiwy6gFi/pub?gid=1786895027&single=true&output=csv"
TAX_ENVIRONMENTS = {"Marginal rate — 32.5%": 0.325, "Pension phase — 0%": 0.0, "Super accumulation — 15%": 0.15, "Marginal rate — 18%": 0.18, "Marginal rate — 37%": 0.37, "Top marginal — 47%": 0.47}

# Get width from JS
width = st_javascript("window.innerWidth")

# Set a safe default (False) if width is None or not yet loaded
is_mobile = False
if width is not None and isinstance(width, int):
    if width < 800:
        is_mobile = True

# ── HELPERS ──
def fmt_aud(n): return f"${n:,.0f}" if n else "—"
def fmt_aud2(n): return f"${n:,.2f}" if n else "—"
def fmt_pct(n): return f"{n:.2f}%" if n is not None else "—"
def franking_badge(pct):
    if pct >= 100: return '<span class="badge full">100%</span>'
    if pct <= 0: return '<span class="badge none">0%</span>'
    return f'<span class="badge partial">{pct:.0f}%</span>'

def get_csv_data(computed_list, holdings_list, is_gross):
    export_data = []
    for i, h in enumerate(holdings_list):
        c = computed_list[i]
        ticker = h['ticker'].upper().strip()
        
        # Pull company name from MASTER_DATA 
        data = MASTER_DATA.get(ticker)
        company_name = data['name'] if data else "Unknown"
        
        # Determine which yield/income to show based on the toggle [cite: 24, 25]
        display_yield = (c['gross']/c['val']*100) if is_gross and c['val'] else c['y']
        display_income = c['gross'] if is_gross else c['cash']

        export_data.append({
            "Ticker": ticker,
            "Company": company_name,
            "Units": f"{h['units']:,}", 
            "Price": fmt_aud2(c['p']),
            "Value": fmt_aud(c['val']),
            "Yield (%)": fmt_pct(display_yield),
            "Annual Income": fmt_aud(display_income), # Now returns $0 instead of —
            "Franking (%)": f"{c['f']:.0f}%"
        })
    return pd.DataFrame(export_data).to_csv(index=False).encode('utf-8')

# ── DATA FETCHING ──
@st.cache_data(ttl=3600)
def load_master_data():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        df.columns = df.columns.str.strip()
        df['Ticker'] = df['Ticker'].astype(str).str.upper().str.replace('.AX', '', regex=False).str.strip()
        master_dict = {}
        for _, row in df.iterrows():
            f_rate = str(row.get('Franking Rate (%)', '0')).replace('%', '')
            master_dict[row['Ticker']] = {
                "name": row.get('Company Name', row['Ticker']),
                "price": float(row.get('Price', 0)),
                "yield": float(row.get('Dividend Yield (%)', 0)),
                "franking": float(pd.to_numeric(f_rate, errors='coerce') or 0)
            }
        return master_dict
    except: return {}

MASTER_DATA = load_master_data()

# ── SESSION STATE ──
if 'holdings' not in st.session_state:
    st.session_state.holdings = [
        {"ticker": "CBA", "units": 296.0, "custom_p": 0.0, "custom_y": 0.0, "id": str(uuid.uuid4())},
        {"ticker": "ANZ", "units": 1386.0, "custom_p": 0.0, "custom_y": 0.0, "id": str(uuid.uuid4())},
        {"ticker": "MQG", "units": 243.0, "custom_p": 0.0, "custom_y": 0.0, "id": str(uuid.uuid4())},
    ]

# ── TOOLBAR ──
st.markdown('<div class="toolbar-wrapper"><div class="toolbar-inner">', unsafe_allow_html=True)

col_spacer, col_gross, col_manual, col_tax, col_btn = st.columns([3, 0.9, 1, 1.4, 0.5])

with col_gross:
    is_gross_view = st.toggle("Grossed-up", value=False)

with col_manual:
    is_edit_mode = st.toggle("Manual Override", value=False)

with col_tax:
    selected_env = st.selectbox(
        "Tax Environment",
        list(TAX_ENVIRONMENTS.keys()),
        label_visibility="collapsed"
    )
    tax_rate = TAX_ENVIRONMENTS[selected_env]

st.markdown('</div></div>', unsafe_allow_html=True)

# ── CALCULATION LOGIC ──
computed = []
t_val = t_cash = t_frank = t_gross = 0

for h in st.session_state.holdings:
    live_units = st.session_state.get(f"m_u_{h['id']}", h['units'])
    live_ticker = st.session_state.get(f"m_t_{h['id']}", h['ticker'])
    live_custom_p = st.session_state.get(f"m_cp_{h['id']}", h['custom_p'])
    live_custom_y = st.session_state.get(f"m_cy_{h['id']}", h['custom_y'])
    
    data = MASTER_DATA.get(h['ticker'].upper().strip())
    
    # Source Logic
    base_p = live_custom_p if (is_edit_mode and live_custom_p > 0) else (data['price'] if data else 0)
    base_y = live_custom_y if (is_edit_mode and live_custom_y > 0) else (data['yield'] if data else 0)
    base_f = data['franking'] if data else 0

    r_val = base_p * live_units
    r_cash = r_val * (base_y / 100)
    r_frank = r_cash * (base_f / 100) * (30/70)
    r_gross = r_cash + r_frank

    t_val += r_val; t_cash += r_cash; t_frank += r_frank; t_gross += r_gross
    computed.append({"val": r_val, "cash": r_cash, "gross": r_gross, "p": base_p, "y": base_y, "f": base_f, "units": live_units, "ticker": live_ticker})
    
    if t_val > 0:
        portfolio_yld = (t_gross if is_gross_view else t_cash) / t_val * 100
    else:
        portfolio_yld = 0
        
    post_tax = (t_cash + t_frank) * (1 - tax_rate)


# ── DOWNLOAD ──
with col_btn:
    # Prepare the CSV data
    csv = get_csv_data(computed, st.session_state.holdings, is_gross_view)
    
    st.download_button(
        label="📥",
        data=csv,
        file_name="asx_dividend_report.csv",
        mime="text/csv",
        help="Download current view as CSV"
    )

# ----- MOBILE LAYOUT ------
if is_mobile:
    st.markdown(f"""
    <div class="mobile-summary">
        <div class="card">
            <div class="label">Total Value</div>
            <div class="value">{fmt_aud(t_val)}</div>
        </div>
        <div class="card">
            <div class="label">Annual Income</div>
            <div class="value">{fmt_aud(t_gross if is_gross_view else t_cash)}</div>
        </div>
        <div class="card">
            <div class="label">Portfolio Yield</div>
            <div class="value">{fmt_pct(portfolio_yld)}</div>
        </div>
        <div class="card">
            <div class="label">Post-Tax Est.</div>
            <div class="value">{fmt_aud(post_tax)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    
    st.markdown("### Your Holdings")
    
    # 1. THE "ADD" BUTTON (At the top for easy thumb access)
    if st.button("+ Add New Holding", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.holdings.append({
        "ticker": "", "units": 0, "custom_p": 0.0, "custom_y": 0.0, "id": new_id
        })
        st.session_state[f"exp_{new_id}"] = True 
        st.rerun()

    # 2. THE CARDS LOOP
    for i, h in enumerate(st.session_state.holdings):
        # We already did the math at the top! Just grab the result for this specific holding.
        c = computed[i]
        
        # Pull the values we pre-calculated
        live_ticker = c['ticker']
        calc_val = c['val']
        # Determine if we show Gross or Cash income in the header based on the toggle
        calc_inc = c['gross'] if is_gross_view else c['cash']
        base_y = (c['gross'] / c['val'] * 100) if (is_gross_view and c['val'] > 0) else c['y']

        # Format the strings for the expander label
        v_val = fmt_aud(calc_val)
        y_val = f"{base_y:.2f}%"
        i_val = fmt_aud(calc_inc)
        
        # Create the label
        raw_label = f"{live_ticker or 'NEW'} | {v_val} | {y_val} | {i_val}"
        
        def escape_math(text):
            return text.replace("%", r"\%").replace("$", r"\$")
            
        card_label = escape_math(raw_label)
    
        is_expanded = st.session_state.get(f"exp_{h['id']}", False)
        
        with st.expander(f"**{card_label}**", expanded=is_expanded):
            st.markdown(card_label, unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                # Ticker Selector
                ticker_opts = [""] + list(MASTER_DATA.keys())
                curr_idx = ticker_opts.index(h['ticker']) if h['ticker'] in ticker_opts else 0
                h['ticker'] = st.selectbox("Ticker", ticker_opts, index=curr_idx, key=f"m_t_{h['id']}")
            with c2:
                # Units Input
                h['units'] = st.number_input("Units", value=int(h['units']), step=1, key=f"m_u_{h['id']}")

            # --- ROW 2: Price & Franking ---
            c3, c4 = st.columns(2)
            with c3:
                # Price (Show custom if override is on, else show master data price)
                display_p = float(c['p'])
                st.write(f"**Price:** {fmt_aud2(display_p)}")
            with c4:
                # Franking Rate
                st.write(f"**Franking:** {c['f']:.0f}%")

            # --- MANUAL OVERRIDES (Optional) ---
            if is_edit_mode:
                st.divider()
                oc1, oc2 = st.columns(2)
                h['custom_p'] = oc1.number_input("Man. Price", value=float(h['custom_p']), key=f"m_cp_{h['id']}")
                h['custom_y'] = oc2.number_input("Man. Yield", value=float(h['custom_y']), key=f"m_cy_{h['id']}")

            # --- DELETE BUTTON ---
            st.button("🗑️ Remove", key=f"m_del_{h['id']}", on_click=lambda idx=i: st.session_state.holdings.pop(idx), use_container_width=True)


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
    
    st.markdown(f"""<div class="tbl-header">
        <span>Ticker</span><span>Company</span><span>Units</span><span class="r">Price</span><span class="r">Value</span>
        <span class="r">{yield_head}</span><span class="r">{inc_head}</span><span class="r">Franking</span><span></span>
    </div>""", unsafe_allow_html=True)
    
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
    if st.button("+ Add Holding", use_container_width=True):
        st.session_state.holdings.append({"ticker": "", "units": 0.0, "custom_p": 0.0, "custom_y": 0.0, "id": str(uuid.uuid4())})
        st.rerun()
