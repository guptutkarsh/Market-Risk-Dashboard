"""
Portfolio Market Risk Dashboard — interactive Streamlit front-end.

Run:  streamlit run app.py
Reads the CSVs in ./data (reproducible, no broker login needed).
"""
import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt
from pathlib import Path

st.set_page_config(page_title="Market Risk Dashboard", layout="wide")
DATA = Path(__file__).parent / "data"


@st.cache_data
def load_data():
    pos = pd.read_csv(DATA / "positions.csv")
    pf = pd.read_csv(DATA / "portfolio_full.csv", index_col=0, parse_dates=True)
    ar = pd.read_csv(DATA / "asset_returns.csv", index_col=0, parse_dates=True)
    return pos, pf["full"].dropna(), ar


positions, r, asset_ret = load_data()
V = positions["mkt_value"].sum()
mu, sigma = r.mean(), r.std()

# ----------------------------------------------------------------- header
st.title("📉 Portfolio Market Risk Dashboard")
st.caption(
    f"Real multi-asset book · ₹{V:,.0f} · {len(r)} trading days "
    f"({r.index.min().date()} → {r.index.max().date()})"
)

# ----------------------------------------------------------------- sidebar
st.sidebar.header("Parameters")
conf = st.sidebar.select_slider("Confidence level", options=[0.90, 0.95, 0.99], value=0.99)
method = st.sidebar.radio("VaR method", ["Historical", "Parametric", "Monte Carlo"])
alpha = 1 - conf


# ----------------------------------------------------------------- VaR / ES
def var_es(method, alpha):
    if method == "Historical":
        q = r.quantile(alpha)
        return -q, -r[r <= q].mean()
    if method == "Parametric":
        z = norm.ppf(alpha)
        v = -(mu + z * sigma)
        es = -(mu - sigma * norm.pdf(z) / alpha)
        return v, es
    # Monte Carlo (multivariate normal on the asset covariance)
    rs = asset_ret.dropna(how="any")
    w = positions.set_index("yf_ticker")["weight"].reindex(rs.columns).fillna(0).values
    w = w / w.sum()
    rng = np.random.default_rng(42)
    sims = rng.multivariate_normal(rs.mean().values, rs.cov().values, 50_000) @ w
    q = np.quantile(sims, alpha)
    return -q, -sims[sims <= q].mean()


v, es = var_es(method, alpha)
c1, c2, c3 = st.columns(3)
c1.metric(f"{conf:.0%} VaR (1-day)", f"₹{v * V:,.0f}", f"{v:.2%}")
c2.metric(f"{conf:.0%} Expected Shortfall", f"₹{es * V:,.0f}", f"{es:.2%}")
c3.metric("Annualised volatility", f"{sigma * np.sqrt(252):.1%}")

st.divider()
left, right = st.columns(2)

# ----------------------------------------------------------------- distribution
with left:
    st.subheader("Daily returns vs normal")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(r, bins=60, density=True, alpha=0.6, color="steelblue")
    xs = np.linspace(r.min(), r.max(), 200)
    ax.plot(xs, norm.pdf(xs, mu, sigma), "r-", lw=2, label="normal fit")
    ax.axvline(r.quantile(alpha), color="k", ls="--", label=f"{conf:.0%} VaR")
    ax.legend()
    st.pyplot(fig)
    st.caption(
        f"Skew {r.skew():.2f}, excess kurtosis {r.kurt():.2f} — "
        "fat tails the normal curve misses."
    )

# ----------------------------------------------------------------- correlation
with right:
    st.subheader("Asset correlation")
    corr = asset_ret.dropna(how="any").corr()
    avg = corr.values[np.triu_indices(len(corr), k=1)].mean()
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    im = ax2.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax2.set_xticks([])
    ax2.set_yticks([])
    fig2.colorbar(im, ax=ax2, fraction=0.046)
    st.pyplot(fig2)
    st.caption(f"Average pairwise correlation {avg:.2f} — diversification benefit.")

st.divider()

# ----------------------------------------------------------------- stress
st.subheader("Stress scenarios (long-history sleeve)")
cls = positions.set_index("yf_ticker")["asset_class"]
w_full = positions.set_index("yf_ticker")["weight"]
first = asset_ret.apply(lambda c: c.first_valid_index())
long_assets = [
    t for t in asset_ret.columns
    if t in w_full.index and first[t] is not None
    and first[t] <= pd.Timestamp("2019-01-01")
]
w_long = w_full.reindex(long_assets)
w_long = w_long / w_long.sum()

scenarios = {
    "GFC-style equity crash": {"Equity": -0.40, "IntlEquity": -0.35, "REIT": -0.30,
                               "InvIT": -0.20, "Gold": 0.15, "Silver": -0.10},
    "COVID-style shock": {"Equity": -0.30, "IntlEquity": -0.25, "REIT": -0.25,
                          "InvIT": -0.20, "Gold": 0.05, "Silver": -0.15},
    "RBI rate-hike shock": {"Equity": -0.07, "IntlEquity": -0.03, "REIT": -0.15,
                            "InvIT": -0.15, "Gold": -0.05, "Silver": -0.05},
}
rows = []
worst_pnl = 0.0
for name, shock in scenarios.items():
    pnl = sum(w_long[t] * shock.get(cls.get(t, "Equity"), -0.30) for t in w_long.index)
    worst_pnl = min(worst_pnl, pnl)
    rows.append({"Scenario": name, "P&L %": f"{pnl:.1%}", "P&L ₹": f"₹{pnl * V:,.0f}"})
st.table(pd.DataFrame(rows))
st.caption(f"Worst scenario ≈ {abs(worst_pnl) / v:.0f}× the {conf:.0%} VaR — "
           "the gap stress testing exists to catch.")
