import streamlit as st
import pandas as pd
import uuid

# ── CONFIG ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="ASX Dividend Tool", page_icon="📊")

# ── DATA SOURCE ────────────────────────────────────────
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQXUiVcziu72OkPGE8Wy5xhelPIXJTMs0Z1oBtqQbZ-_RS5qNOAt9q5sr23I7ejAqXrQRuKZiwy6gFi/pub?gid=942242974&single=true&output=csv"

# ── HELPERS ───────────────────────────────────────────
def fmt_aud(n): return f"${n:,.0f}" if n else "—"
def fmt_aud2(n): return f"${n:,.2f}" if n else "—"
def fmt_pct(n): return f"{n:.2f}%" if n else "—"

def franking_badge(pct):
    if pct >= 100: return "100%"
    if pct <= 0: return "0%"
    return f"{pct:.0f}%"

# ── LOAD DATA ─────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        df.columns = df.columns.str.strip()

        df['Ticker'] = df['Ticker'].astype(str).str.upper().str.replace('.AX', '', regex=False)

        df['Franking'] = (
            df.get('Franking Rate (%)', 0)
            .astype(str)
            .str.replace('%', '', regex=False)
        )
        df['Franking'] = pd.to_numeric(df['Franking'], errors='coerce').fillna(0)

        data = {}
        for _, r in df.iterrows():
            data[r['Ticker']] = {
                "name": r.get('Company Name', r['Ticker']),
                "price": float(r.get('Price', 0)),
                "yield": float(r.get('Dividend Yield (%)', 0)),
                "franking": float(r['Franking'])
            }
        return data
    except:
        st.warning("⚠️ Data not loading (check sheet link)")
        return {}

DATA = load_data()

# ── SESSION STATE ─────────────────────────────────────
if "holdings" not in st.session_state:
    st.session_state.holdings = [
        {"id": str(uuid.uuid4()), "ticker": "CBA", "units": 100},
        {"id": str(uuid.uuid4()), "ticker": "VAS", "units": 200},
    ]

# ── HEADER ────────────────────────────────────────────
st.title("ASX Dividend Calculator")

# ── TABLE HEADER ──────────────────────────────────────
header = st.columns([1,2,1,1,1,1,1,1,0.5])
cols = ["Ticker","Company","Units","Price","Value","Yield","Income","Franking",""]

for col, label in zip(header, cols):
    col.markdown(f"**{label}**")

st.divider()

# ── CALCULATIONS ──────────────────────────────────────
total_value = 0
total_income = 0
total_franking = 0

delete_index = None

for i, h in enumerate(st.session_state.holdings):
    row = st.columns([1,2,1,1,1,1,1,1,0.5])

    ticker = row[0].text_input(
        "", value=h["ticker"], key=f"t_{h['id']}"
    ).upper().strip()

    units = row[2].number_input(
        "", value=float(h["units"]), key=f"u_{h['id']}", step=1.0
    )

    # update state
    h["ticker"] = ticker
    h["units"] = units

    data = DATA.get(ticker)

    if data:
        value = data["price"] * units
        income = value * data["yield"] / 100
        franking = income * data["franking"] / 100 * (30/70)

        total_value += value
        total_income += income
        total_franking += franking

        row[1].write(data["name"])
        row[3].write(fmt_aud2(data["price"]))
        row[4].write(fmt_aud(value))
        row[5].write(fmt_pct(data["yield"]))
        row[6].write(fmt_aud(income))
        row[7].write(franking_badge(data["franking"]))
    else:
        row[1].write("—")
        row[3].write("—")
        row[4].write("—")
        row[5].write("—")
        row[6].write("—")
        row[7].write("—")

    # DELETE BUTTON (perfect alignment)
    if row[8].button("×", key=f"d_{h['id']}"):
        delete_index = i

    st.divider()

# ── DELETE ROW ────────────────────────────────────────
if delete_index is not None:
    st.session_state.holdings.pop(delete_index)
    st.rerun()

# ── ADD BUTTON ────────────────────────────────────────
if st.button("+ Add holding", use_container_width=True):
    st.session_state.holdings.append({
        "id": str(uuid.uuid4()),
        "ticker": "",
        "units": 0
    })
    st.rerun()

# ── SUMMARY ───────────────────────────────────────────
st.divider()

yield_pct = (total_income / total_value * 100) if total_value else 0

col1, col2, col3 = st.columns(3)

col1.metric("Portfolio Value", fmt_aud(total_value))
col2.metric("Annual Income", fmt_aud(total_income))
col3.metric("Yield", fmt_pct(yield_pct))
