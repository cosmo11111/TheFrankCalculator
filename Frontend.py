import streamlit as st
import pandas as pd
import time

st.set_page_config(layout="wide")

# ── CSS ─────────────────────────────────────────────

st.markdown("""
<style>
.block-container { max-width: 1100px; padding-top: 2rem; }

.row {
    border-bottom: 1px solid #eee;
    padding: 6px 0;
}

.header {
    border-bottom: 1px solid #ddd;
    padding-bottom: 8px;
    margin-bottom: 6px;
    font-size: 11px;
    color: #888;
    text-transform: uppercase;
}

input {
    border: none !important;
    box-shadow: none !important;
}

div[data-testid="stNumberInput"] > div {
    border: none !important;
}

button {
    background: none !important;
    border: none !important;
}

.add-btn button {
    width: 100%;
    border: 1px dashed #ccc !important;
    padding: 10px !important;
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

# ── DATA ─────────────────────────────────────────────

CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQXUiVcziu72OkPGE8Wy5xhelPIXJTMs0Z1oBtqQbZ-_RS5qNOAt9q5sr23I7ejAqXrQRuKZiwy6gFi/pub?gid=942242974&single=true&output=csv"

@st.cache_data
def load():
    df = pd.read_csv(CSV)
    df['Ticker'] = df['Ticker'].str.upper().str.replace(".AX","")
    df['Franking'] = df['Franking Rate (%)'].str.replace("%","").astype(float)
    return {
        r['Ticker']: {
            "name": r['Company Name'],
            "price": r['Price'],
            "yield": r['Dividend Yield (%)'],
            "frank": r['Franking']
        }
        for _, r in df.iterrows()
    }

DB = load()
TICKERS = list(DB.keys())

# ── SESSION ─────────────────────────────────────────

if "rows" not in st.session_state:
    st.session_state.rows = [
        {"id": 1, "t": "CBA", "u": 100},
        {"id": 2, "t": "VAS", "u": 200},
    ]

# ── HEADER ──────────────────────────────────────────

cols = st.columns([1,2,1,1,1,1,1,1,0.3])
headers = ["Ticker","Company","Units","Price","Value","Yield","Income","Franking",""]

for c, h in zip(cols, headers):
    c.markdown(f"<div class='header'>{h}</div>", unsafe_allow_html=True)

# ── HELPERS ─────────────────────────────────────────

def aud(x): return f"${x:,.0f}" if x else "—"
def pct(x): return f"{x:.2f}%" if x else "—"

def badge(f):
    if f >= 100: return "100%"
    if f <= 0: return "0%"
    return f"{f:.0f}%"

# ── ROWS ────────────────────────────────────────────

delete_id = None

for i, r in enumerate(st.session_state.rows):

    data = DB.get(r["t"])

    price = data["price"] if data else 0
    val = price * r["u"]
    inc = val * (data["yield"]/100) if data else 0

    cols = st.columns([1,2,1,1,1,1,1,1,0.3])

    # ── TICKER INPUT WITH AUTOCOMPLETE ──
    with cols[0]:
        t = st.text_input("", value=r["t"], key=f"t_{r['id']}")
        st.session_state.rows[i]["t"] = t.upper()

        # suggestion list
        if t:
            matches = [x for x in TICKERS if x.startswith(t.upper())][:5]
            if matches:
                st.caption(" • ".join(matches))

    # ── NAME ──
    with cols[1]:
        st.write(data["name"] if data else "—")

    # ── UNITS ──
    with cols[2]:
        u = st.number_input("", value=float(r["u"]), step=1.0, key=f"u_{r['id']}")
        st.session_state.rows[i]["u"] = u

    # ── DATA ──
    with cols[3]: st.write(aud(price))
    with cols[4]: st.write(aud(val))
    with cols[5]: st.write(pct(data["yield"]) if data else "—")
    with cols[6]: st.write(aud(inc))
    with cols[7]: st.write(badge(data["frank"]) if data else "—")

    # ── DELETE ──
    with cols[8]:
        if st.button("×", key=f"d_{r['id']}"):
            delete_id = r["id"]

# delete safely
if delete_id:
    st.session_state.rows = [r for r in st.session_state.rows if r["id"] != delete_id]
    st.rerun()

# ── ADD BUTTON ──────────────────────────────────────

st.markdown('<div class="add-btn">', unsafe_allow_html=True)

if st.button("+ Add Holding"):
    st.session_state.rows.append({
        "id": int(time.time()*1000),
        "t": "",
        "u": 0
    })
    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
