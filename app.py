import os
import re
import sqlite3
import uuid
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


APP_TITLE = "EscrowFlow Web3 Gateway"
PLATFORM_WALLET = os.getenv(
    "PLATFORM_WALLET",
    "9n43d6JU2xxyHJbAFeJmevcBoxvuiGgTatDB5JJgeNDX",
)
PLATFORM_FEE_PCT = Decimal("0.01")
LOCKED_STATUS = "Locked in Escrow 🔒"
RELEASED_STATUS = "Released to Vendor ✅"
DB_PATH = Path(os.getenv("ESCROW_DB_PATH", "escrowflow.db"))

st.set_page_config(page_title=APP_TITLE, page_icon="💸", layout="wide")


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def calculate_fees(amount: Decimal) -> tuple[Decimal, Decimal]:
    fee = money(amount * PLATFORM_FEE_PCT)
    return fee, money(amount - fee)


def is_valid_solana_address(address: str) -> bool:
    return bool(address and 32 <= len(address) <= 44 and re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]+", address))


def connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS escrows (
                tx_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                receiver TEXT NOT NULL,
                gross_amount TEXT NOT NULL,
                platform_fee TEXT NOT NULL,
                net_amount TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def create_escrow(title, receiver, gross, fee, net):
    tx_id = f"TX-{uuid.uuid4().hex[:10].upper()}"
    with connection() as conn:
        conn.execute(
            """INSERT INTO escrows
            (tx_id, title, receiver, gross_amount, platform_fee, net_amount, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (tx_id, title, receiver, str(gross), str(fee), str(net), LOCKED_STATUS),
        )
    return tx_id


def get_escrow(tx_id):
    with connection() as conn:
        row = conn.execute("SELECT * FROM escrows WHERE tx_id = ?", (tx_id,)).fetchone()
    return dict(row) if row else None


def list_escrows():
    with connection() as conn:
        rows = conn.execute("SELECT * FROM escrows ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def release_escrow(tx_id):
    with connection() as conn:
        conn.execute("UPDATE escrows SET status = ? WHERE tx_id = ? AND status = ?", (RELEASED_STATUS, tx_id, LOCKED_STATUS))


def released_fees():
    with connection() as conn:
        row = conn.execute("SELECT COALESCE(SUM(CAST(platform_fee AS REAL)), 0) AS total FROM escrows WHERE status = ?", (RELEASED_STATUS,)).fetchone()
    return money(Decimal(str(row["total"])))


init_db()

st.title("💸 EscrowFlow: Web3 Cross-Border P2P Gateway")
st.subheader("Secure Solana-inspired escrow workflow for digital payments")
st.warning("Demo mode: this app persists escrow records in SQLite but does not move real USDC or SOL.")

with st.sidebar:
    st.header("🔑 Platform Rules")
    st.write("**Treasury wallet**")
    st.code(PLATFORM_WALLET)
    st.write(f"**Platform fee:** {PLATFORM_FEE_PCT * 100}%")
    st.caption("Set PLATFORM_WALLET in Streamlit Cloud secrets before production use.")

st.write("### 🌐 Phantom Wallet")
components.html(f"""
<div style="text-align:center;font-family:sans-serif">
<button id="connect" style="background:#512da8;color:#fff;padding:12px 24px;border:0;border-radius:8px;font-weight:bold;cursor:pointer;width:100%">⚡ Connect Phantom Wallet</button>
<p id="status" style="color:#777">Status: Disconnected</p>
</div>
<script>
const button = document.getElementById('connect');
const status = document.getElementById('status');
button.onclick = async () => {{
  const provider = window.solana;
  if (!provider || !provider.isPhantom) {{
    status.textContent = '❌ Phantom not found';
    window.open('https://phantom.app/', '_blank');
    return;
  }}
  try {{
    const response = await provider.connect();
    const key = response.publicKey.toString();
    status.textContent = '✅ Connected: ' + key.slice(0, 6) + '...' + key.slice(-4);
    status.style.color = '#00a86b';
    button.textContent = 'Wallet Connected';
  }} catch (error) {{ status.textContent = '❌ Connection rejected'; }}
}};
</script>
""", height=130)

tab_create, tab_release, tab_ledger = st.tabs(["🆕 Create Escrow", "🔐 Release Funds", "📊 Earnings Ledger"])

with tab_create:
    st.header("Create a Secure Escrow Contract")
    with st.form("create_escrow"):
        title = st.text_input("Project name / course title", placeholder="Financial Coaching Course")
        amount = st.number_input("Amount (USDC)", min_value=1.0, step=0.5, format="%.4f")
        receiver = st.text_input("Vendor Solana wallet address", placeholder="Base58 wallet address").strip()
        submitted = st.form_submit_button("Initiate Escrow Deposit")

    if submitted:
        errors = []
        if not title.strip(): errors.append("Project title is required.")
        if amount <= 0: errors.append("Amount must be greater than zero.")
        if not is_valid_solana_address(receiver): errors.append("Enter a valid Solana wallet address.")
        if errors:
            for error in errors: st.error(f"❌ {error}")
        else:
            gross = Decimal(str(amount))
            fee, net = calculate_fees(gross)
            tx_id = create_escrow(title.strip(), receiver, money(gross), fee, net)
            st.success(f"🎉 Escrow created. Transaction ID: **{tx_id}**")
            st.info("A production version must verify an on-chain deposit before allowing release.")

with tab_release:
    st.header("Release Escrowed Funds")
    tx_id = st.text_input("Escrow transaction ID", placeholder="TX-ABCD1234EF").strip().upper()
    if tx_id:
        tx = get_escrow(tx_id)
        if not tx:
            st.error("❌ Transaction ID not found.")
        else:
            st.write(f"**Project:** {tx['title']}")
            st.write(f"**Vendor:** `{tx['receiver']}`")
            st.write(f"**Payout:** {tx['net_amount']} USDC")
            st.write(f"**Status:** {tx['status']}")
            if tx["status"] == LOCKED_STATUS:
                st.warning("Demo release only changes the local database; no blockchain transfer occurs.")
                if st.button("Confirm & Disburse Funds 🚀", key=f"release_{tx_id}"):
                    release_escrow(tx_id)
                    st.success("✅ Escrow marked as released.")
                    st.rerun()
            else:
                st.success("This escrow has already been released.")

with tab_ledger:
    st.header("📈 Platform Earnings")
    st.metric("Accumulated Profits", f"{released_fees()} USDC")
    records = list_escrows()
    if records:
        st.dataframe(records, use_container_width=True, hide_index=True)
    else:
        st.info("No escrow transactions have been created yet.")
