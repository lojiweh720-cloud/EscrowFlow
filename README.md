# EscrowFlow

A Streamlit demo for a Solana-inspired escrow workflow.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Open [share.streamlit.io](https://share.streamlit.io/).
2. Sign in with GitHub.
3. Select repository `lojiweh720-cloud/EscrowFlow`.
4. Select branch `main`.
5. Set the main file to `app.py`.
6. Deploy.
7. In **App settings → Secrets**, add:

```toml
PLATFORM_WALLET = "your_treasury_wallet"
```

The app currently uses SQLite for demonstration. Streamlit Community Cloud storage is not suitable for durable production financial records, and this app does not submit real blockchain transactions. Before handling funds, add a persistent database, authentication, on-chain deposit verification, server-side authorization, and a real Solana escrow program.
