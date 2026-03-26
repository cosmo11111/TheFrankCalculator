import streamlit as st
import pandas as pd
import time

# ── CONFIG ─────────────────────────────────────────────────

st.set_page_config(
    layout="wide",
    page_title="ASX Dividend Tool",
    page_icon="📊"
)

# ── CSS ────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }

.block-container {
    padding: 2rem 2.5rem 2rem;
    max-width: 1200px;
}

.page-header {
    display:flex;
    align-items:baseline;
    gap:12px;
    margin-bottom:2rem;
    padding-bottom:1.25rem;
    border-bottom:1px solid #f0f0f0;
}

.page-header h1 {
    font-size:20px;
    font-weight:600;
    color:#111;
    margin:0;
}

.status-pill {
    display:inline-flex;
    align-items:center;
    gap:5px;
    font-size:11px;
    color:#999;
    background:#f5f5f5;
    border-radius:20px;
    padding:3px 10px;
}

.status-dot {
    width:6px;
    height:6px;
    border-radius:50%;
    background:#22c55e;
}

.summary-row {
    display:grid;
    grid-template-columns:repeat(5,1fr);
    gap:12px;
    margin-bottom:1.75rem;
}

.summary-card {
    background:#fafafa;
    border:1px solid #f0f0f0;
    border-radius:10px;
    padding:16px 18px;
}

.summary-card .label {
    font-size:11px;
    color:#999;
    text-transform:uppercase;
}

.summary-card .value {
    font-size:22px;
    font-weight:600;
}

.summary-card .green {
    color:#166534;
}

.badge {
    font-size:11px;
    padding:2px 8px;
    border-radius:20px;
}

.badge.full { background:#dcfce7; color:#166534; }
.badge.partial { background:#fef3c7; color:#92400e; }
.badge.none { background:#f1f5f9; color:#64748b; }

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {
    border:1px solid #e5e5e5 !important;
    border-radius:6px !important;
    font-size:13px !important;
}

div[data-testid="stNumberInput"] > div {
    border:none !important;
    box-shadow:none !important;
}

div[data-testid="stButton"] button {
    border:none !important;
    background:transparent !important;
    font-size:18px !important;
    color:#ccc !important;
}

div[data-testid="stButton"] button:hover {
    color:#ef4444 !important;
}

.footer {
    font-size:11px;
    color:#bbb;
    margin-top:2rem;
}
</style>
""", unsafe_allow_html=True)

# ── DATA SOURCE ────────────────────────────────────────────

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQXUiVcziu72OkPGE8Wy5xhelPIXJTMs0Z1oBtqQbZ-_RS5qNOAt9q5sr23I7ejAqXrQRuKZiwy6gFi/pub?gid=942242974&single=true&output=csv"

TAX_ENVIRONMENTS = {
    "Pension phase (0%)":0.00,
    "Super accumulation (15%)":0.15,
    "Marginal rate — 19%":0.19,
    "Marginal rate — 32.5%":0.325,
    "Marginal rate — 37%":0.37,
    "Top marginal (47%)":0.47
}

# ── HELPERS ────────────────────────────────────────────────

def fmt_aud(n): return f"${n:,.0f}" if n else "—"
def fmt_aud2(n): return f"${n:,.2f}" if n else "—"
def fmt_pct(n): return f"{n:.2f}%" if n else "—"

def franking_badge(p):
    if p >= 100: return '<span class="badge full">100%</span>'
    if p <= 0: return '<span class="badge none">0%</span>'
    return f'<span class="badge partial">{p:.0f}%</span>'

# ── LOAD DATA ──────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_master_data():
    df = pd.read_csv(SHEET_CSV_URL)
    df.columns = df.columns.str.strip()

    df['Ticker'] = df['Ticker'].str.upper().str.replace(".AX","")

    df['Franking_Clean'] = (
        df['Franking Rate (%)']
        .astype(str)
        .str.replace("%","")
        .astype(float)
    )

    data = {}

    for _,row in df.iterrows():
        data[row['Ticker']] = {
            "name":row.get("Company Name"),
            "price":float(row.get("Price",0)),
            "yield":float(row.get("Dividend Yield (%)",0)),
            "franking":float(row['Franking_Clean'])
        }

    return data

MASTER_DATA = load_master_data()
TICKERS = sorted(list(MASTER_DATA.keys()))

# ── SIDEBAR ────────────────────────────────────────────────

with st.sidebar:

    selected_env = st.selectbox("Tax environment",list(TAX_ENVIRONMENTS.keys()))
    tax_rate = TAX_ENVIRONMENTS[selected_env]

    if st.button("Refresh data"):
        st.cache_data.clear()
        st.rerun()

# ── SESSION STATE ──────────────────────────────────────────

if "holdings" not in st.session_state:

    st.session_state.holdings = [
        {"id":1,"ticker":"CBA","units":100},
        {"id":2,"ticker":"VAS","units":200},
        {"id":3,"ticker":"TLS","units":500}
    ]

# ── HEADER ─────────────────────────────────────────────────

st.markdown("""
<div class="page-header">
<h1>ASX Dividend Calculator</h1>
<span class="status-pill"><span class="status-dot"></span> Database Connected</span>
</div>
""",unsafe_allow_html=True)

# ── COMPUTE PORTFOLIO ──────────────────────────────────────

rows=[]
total_val=0
total_cash=0
total_frank=0

for h in st.session_state.holdings:

    ticker=h["ticker"].upper()
    data=MASTER_DATA.get(ticker)

    val=cash=frank=0

    if data and h["units"]>0:

        val=data["price"]*h["units"]
        cash=val*(data["yield"]/100)
        frank=cash*(data["franking"]/100)*(30/70)

        total_val+=val
        total_cash+=cash
        total_frank+=frank

    rows.append({"data":data,"val":val,"cash":cash,"frank":frank})

gross_income=total_cash+total_frank
post_tax=gross_income-(gross_income*tax_rate)
portfolio_yld=(total_cash/total_val*100) if total_val else 0

# ── SUMMARY ────────────────────────────────────────────────

st.markdown(f"""
<div class="summary-row">
<div class="summary-card"><div class="label">Portfolio value</div><div class="value">{fmt_aud(total_val)}</div></div>
<div class="summary-card"><div class="label">Annual income</div><div class="value green">{fmt_aud(total_cash)}</div></div>
<div class="summary-card"><div class="label">Portfolio yield</div><div class="value green">{fmt_pct(portfolio_yld)}</div></div>
<div class="summary-card"><div class="label">Franking credits</div><div class="value">{fmt_aud(total_frank)}</div></div>
<div class="summary-card"><div class="label">Post tax income</div><div class="value">{fmt_aud(post_tax)}</div></div>
</div>
""",unsafe_allow_html=True)

# ── TABLE ──────────────────────────────────────────────────

to_delete=None

for i,h in enumerate(st.session_state.holdings):

    row_id=h["id"]
    row=rows[i]
    data=row["data"]

    cols=st.columns([1,2,1,1,1,1,1,1,0.4])

    with cols[0]:

        new_ticker=st.selectbox(
            "Ticker",
            [""]+TICKERS,
            index=(TICKERS.index(h["ticker"])+1) if h["ticker"] in TICKERS else 0,
            key=f"t_{row_id}"
        )

        st.session_state.holdings[i]["ticker"]=new_ticker

    with cols[1]:
        st.write(data["name"] if data else "—")

    with cols[2]:

        units=st.number_input(
            "Units",
            value=float(h["units"]),
            step=1.0,
            key=f"u_{row_id}"
        )

        st.session_state.holdings[i]["units"]=units

    with cols[3]:
        st.write(fmt_aud2(data["price"]) if data else "—")

    with cols[4]:
        st.write(fmt_aud(row["val"]))

    with cols[5]:
        st.write(fmt_pct(data["yield"]) if data else "—")

    with cols[6]:
        st.write(fmt_aud(row["cash"]))

    with cols[7]:
        st.markdown(franking_badge(data["franking"]) if data else "—",unsafe_allow_html=True)

    with cols[8]:

        if st.button("×",key=f"d_{row_id}"):

            to_delete=row_id

# delete row safely

if to_delete:

    st.session_state.holdings=[
        h for h in st.session_state.holdings if h["id"]!=to_delete
    ]

    st.rerun()

# ── ADD ROW ────────────────────────────────────────────────

if st.button("+ Add holding",use_container_width=True):

    st.session_state.holdings.append({

        "id":int(time.time()*1000),
        "ticker":"",
        "units":0
    })

    st.rerun()

# ── FOOTER ─────────────────────────────────────────────────

st.markdown("""
<div class="footer">
Franking credits calculated at 30% corporate tax rate. Data sourced from Google Sheet backend.
</div>
""",unsafe_allow_html=True)
