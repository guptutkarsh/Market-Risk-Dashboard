# Portfolio Market Risk Dashboard — VaR, Expected Shortfall & Stress Testing

End-to-end market-risk engine on a **real, live multi-asset portfolio** (~₹53.7L, 31 positions across Indian equities, gold, an international-equity ETF, silver, REITs and an InvIT). Quantifies downside risk three ways, validates the model by backtesting, and stress-tests it against historical and hypothetical crises — framed in **Basel III / FRTB** language.

> Built as a learning project to demonstrate practical market-risk modelling: VaR methodology trade-offs, the limits of the normal assumption, and the gap between a normal trading day (VaR) and a crisis (stress testing).

---

## Headline results

| Measure | Value | Read |
|---|---|---|
| Book value | ₹53.7L | market value, not cost |
| Annualised volatility | 14.2% | full book, common window |
| Daily return skew / excess kurtosis | −0.48 / +4.63 | left-skewed, **fat-tailed** |
| Jarque–Bera normality | rejected (p ≈ 3e-92) | returns are **not** normal |
| Average pairwise correlation | 0.20 | genuine diversification |
| **1-day 99% VaR (historical)** | **₹1.47L** | the headline risk number |
| 1-day 99% VaR (parametric / normal) | ₹1.06L | understates by ~28% |
| 1-day 99% Expected Shortfall | ₹1.89L | avg loss beyond VaR |
| **GFC-style stress loss** | **−₹10.1L (−18.8%)** | ≈ **7× the 99% VaR** |
| COVID-2020 historical drawdown | −26.6% | peak-to-trough, Mar-2020 |

---

## What this project demonstrates

- **Three VaR methods, compared** — Historical Simulation, Parametric (variance–covariance), Monte Carlo (multivariate normal **and** Student-t), with a written rationale for when each applies.
- **Expected Shortfall (CVaR)** — because Basel III / FRTB moved the regulatory measure from VaR to ES.
- **Backtesting** — rolling out-of-sample VaR, **Kupiec POF** test, and the **Basel traffic-light** framework.
- **Stress testing** — historical replay (COVID-2020) + hypothetical scenarios (GFC-style, RBI rate shock) + **correlation-breakdown** analysis.
- **Multi-asset risk** — gold as a measurable diversifier, including how that hedge degrades in a crisis.

---

## 1. Portfolio construction

- Source: real Zerodha holdings (`data/holdings.csv`), 43 broker lines collapsed to 31 risk positions.
- **Proxy mapping by shared risk factor:** 12 SGB tranches → one gold position proxied by `GOLDBEES.NS` (gold spot is the common factor); REIT/InvIT/ETF mapped to their listed tickers.
- **Two universes (hybrid design):**
  - **FULL** — all 31 assets on their common window (≈1.8 yr, capped by the shortest-history asset). The main VaR universe = the actual current book.
  - **LONG sleeve** — assets with pre-2019 history, reweighted to sum to 1. Covers COVID-2020 → used for stress testing. A representative approximation of the book (drops recent IPOs).
- Mutual funds excluded by design — equity MFs overlap existing equity/Nasdaq factors (look-through limitation), so they add no new risk factor.

## 2. Return & distribution analysis

Daily simple returns; common window via `dropna(how="any")`. The book's return distribution is **left-skewed (−0.48)** and **fat-tailed (excess kurtosis 4.63)**; Jarque–Bera rejects normality decisively. This is the empirical basis for preferring historical/ES measures over a pure normal VaR.

## 3. Value at Risk & Expected Shortfall (1-day)

| Method | 95% VaR | 99% VaR |
|---|---|---|
| Historical simulation | ₹77.4k | **₹1.47L** |
| Parametric (normal) | ₹73.0k | ₹1.06L |
| Monte Carlo (normal) | ≈ parametric | ≈ parametric |
| Monte Carlo (Student-t, df=5) | — | ↑ toward historical |

**Expected Shortfall (99%): ₹1.89L historical vs ₹1.22L normal.**

> **Key finding:** at the 99% level the normal model captures only ~72% of the true tail loss — it under-books by ~₹41k (VaR) and ~₹67k (ES). The Monte Carlo Student-t engine reproduces the fat tail by construction, confirming the gap is a distribution-shape effect, not a sampling artefact.

## 4. Backtesting (203-day out-of-sample, rolling 250-day VaR)

- 95% VaR: 16 breaches (7.9% vs 5% expected). **Kupiec POF passes** (p = 0.08) — but only just.
- 99% VaR: 4 breaches → **Basel yellow zone** (4.9 per 250 days).
- **Breaches cluster** (Jan–Mar 2026). Kupiec tests the *count*, not the *timing*; the clustering would fail a **Christoffersen** independence/conditional-coverage test — i.e. the VaR reacts too slowly to a volatility-regime change (a known weakness of historical VaR; EWMA/GARCH weighting addresses it).

> Honest verdict: the model is *count-honest but timing-clustered and mildly fat-tail-leaky* — consistent with the measured excess kurtosis.

## 5. Stress testing

| Scenario | Portfolio P&L | In rupees |
|---|---|---|
| GFC-style equity crash | −18.8% | −₹10.1L |
| COVID-style shock (hypothetical) | −16.6% | −₹8.9L |
| RBI rate-hike shock | −6.7% | −₹3.6L |
| **COVID-2020 (historical replay)** | **−15.2%** | **−₹8.2L** |
| COVID-2020 max drawdown | −26.6% | (peak-to-trough, 23-Mar-2020) |

- The hypothetical COVID shock (−16.6%) cross-validates against the historical replay (−15.2%) — the judgment-based shock vector was well calibrated.
- **GFC-style loss ≈ 7× the 1-day 99% VaR** — the core argument for stress testing alongside VaR.
- 2008 GFC is not replayable historically (price data starts 2018) → covered via the hypothetical scenario. *(Documented limitation.)*

### Correlation breakdown
Average pairwise correlation rises from **0.10 (calm) → 0.34 (crisis)** — diversification weakens by ~3.5× exactly when it is needed. **Gold–equity correlation flips from −0.14 (calm) to +0.15 (COVID)** — a *fair-weather* hedge: it protects in normal times and mild stress, but degrades in an acute liquidity crisis (the March-2020 "dash for cash"). The hedge still cushioned the full scenario, but imperfectly.

---

## Limitations & production notes (model-risk governance)

- SGBs proxied by a gold ETF (illiquid underlyings) — justified by shared risk factor.
- LONG sleeve reweights to a representative subset; rupee stress figures assume the book behaves like its long-history sleeve (excludes post-2019 IPOs).
- 99% VaR on ~1.8 yr is defined by only ~4–5 worst days → a thin, unstable tail estimate; ES and stress testing compensate.
- Single-day horizon; Basel 10-day VaR would scale by √10 (independence assumption).
- Open enhancements: Christoffersen independence test; EWMA/GARCH time-varying volatility; Streamlit interactive front-end.

## Repository structure

```
market-risk-dashboard/
├── data/
│   ├── holdings.csv          # source broker holdings (reproducible)
│   ├── positions.csv         # collapsed positions + weights
│   ├── asset_returns.csv     # daily returns panel
│   ├── portfolio_full.csv    # full-book daily return series
│   └── portfolio_long.csv    # long-sleeve daily return series
├── notebooks/
│   └── 01_portfolio_returns.ipynb
├── output/
│   └── risk_dashboard.png    # 6-panel summary dashboard
└── README.md
```

## How to run

```bash
pip install pandas numpy scipy matplotlib yfinance
```
Open `notebooks/01_portfolio_returns.ipynb` and run top-to-bottom. Prices are pulled live from yfinance; `data/holdings.csv` makes the portfolio reproducible without a broker login.

---

## Methodology references

Basel III / FRTB (Expected Shortfall, traffic-light backtesting) · Kupiec (1995) proportion-of-failures test · Christoffersen (1998) conditional coverage · RiskMetrics (parametric VaR).

*Educational project. Not investment advice. Portfolio figures are illustrative of methodology.*
