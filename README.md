# Portfolio Market Risk Dashboard — VaR, Expected Shortfall & Stress Testing

End-to-end market-risk engine on a **real, live multi-asset portfolio** (₹53.7L, 32 risk positions across Indian equities, gold, an international-equity ETF, silver, REITs and an InvIT). Quantifies downside risk three ways, validates the model by backtesting, and stress-tests it against historical and hypothetical crises — framed in **Basel III / FRTB** language.

> Built as a learning project to demonstrate practical market-risk modelling: VaR methodology trade-offs, the limits of the normal assumption, and the gap between a normal trading day (VaR) and a crisis (stress testing).

---

## Headline results

| Measure | Value | Read |
|---|---|---|
| Book value | ₹53.66L | market value, not cost |
| Positions | 32 risk positions | collapsed from 43 broker lines |
| Annualised volatility | 14.2% | full book, common window (12.9% long sleeve) |
| Worst single day | −4.8% | full book (−7.4% long sleeve, Mar-2020) |
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
- **Conditional volatility** — EWMA (RiskMetrics) and GARCH(1,1)-t for volatility clustering and reactive VaR.
- **Interactive front-end** — Streamlit app with live confidence-level / method controls (`app.py`).

---

## 1. Portfolio construction

- Source: real Zerodha holdings (`data/holdings.csv`), 43 broker lines collapsed to **32 risk positions**.
- **Proxy mapping by shared risk factor:** 12 SGB tranches → one gold position proxied by `GOLDBEES.NS` (gold spot is the common factor); REIT/InvIT/ETF mapped to their listed tickers.
- **Asset-class mix by weight:** Equity 42.5% · Gold 27.6% · REIT 12.1% · IntlEquity 7.8% ·
  InvIT 7.4% · Silver 2.6%.
- **Two universes (hybrid design):**
  - **FULL** — all 32 assets on their common window (≈1.8 yr, capped by the shortest-history asset). The main VaR universe = the actual current book.
  - **LONG sleeve** — the **25 assets** with pre-2019 history, reweighted to sum to 1, covering
    **80% of book value** over 2,091 days from Jan-2018. Covers COVID-2020 → used for stress
    testing. Drops seven recent listings (BIRET, NXST, SILVERBEES, HNDFDS, INDIAMART, INTERARCH,
    EPIGRAL).
- Mutual funds excluded by design — equity MFs overlap existing equity/Nasdaq factors (look-through limitation), so they add no new risk factor.

### Data quality (what the price feed actually needed)

Live vendor data is not clean, and the VaR is only as good as the return series underneath it:

- **Listing-history repair.** Two holdings showed absurdly short NSE histories (SIKA from
  2026-04-20, WAAREERTL from 2025-04-09). Both trade on BSE with history back to 2018, so the
  series were **swapped to the `.BO` feed** — but only where BSE started >6 months earlier. Five
  others (BIRET, NXST, SILVERBEES, INTERARCH, EPIGRAL) checked out as genuine recent IPOs and
  were left alone. Without this check the common window would have been ~2 months, not 452 days.
- **Impossible returns.** 11 single-day moves exceeded ±30% — beyond the 20% circuit limit, so
  they are data errors, not market events (e.g. GOLDBEES −99% then +9,900% on consecutive days
  in Dec-2019, a split not adjusted in the feed). These were masked to flat.
- **Spike repair.** A rolling-median filter flagged prints more than 2× or less than 0.5× their
  21-day neighbourhood: GOLDBEES 2, MON100 2, INDIAMART 1, WAAREERTL 1.
- **Gap filling.** `ffill(limit=5)` only — enough to bridge holidays and halts, not enough to
  invent a price through a long suspension.
- `auto_adjust=True` throughout: unadjusted prices produce phantom return spikes on ex-dividend
  and split dates, which would inflate the tail the whole project is trying to measure.

## 2. Return & distribution analysis

Daily simple returns; common window via `dropna(how="any")`. The book's return distribution is **left-skewed (−0.48)** and **fat-tailed (excess kurtosis 4.63)**; Jarque–Bera rejects normality decisively. This is the empirical basis for preferring historical/ES measures over a pure normal VaR.

## 3. Value at Risk & Expected Shortfall (1-day)

| Method | 95% VaR | 99% VaR | 99% ES |
|---|---|---|---|
| Historical simulation | ₹77.4k | **₹1.47L** | **₹1.89L** |
| Parametric (normal) | ₹73.0k | ₹1.06L | ₹1.22L |
| Monte Carlo, normal (100k draws) | ₹72.8k | ₹1.06L | ₹1.22L |
| Monte Carlo, Student-t df=5 (100k draws) | ₹68.7k | ₹1.19L | ₹1.61L |

Expected Shortfall at 95%: ₹1.17L historical vs ₹93.1k normal.

**Monte Carlo is the control experiment.** Drawing 100k days from a multivariate *normal*
reproduces the parametric answer almost exactly (₹1.06L vs ₹1.06L) — proof that the 99% gap is
**not** a small-sample artefact, since 100,000 simulated days did not close it. Swapping the
marginal to Student-t with df = 5, holding the covariance matched, moves 99% VaR to ₹1.19L and
99% ES to ₹1.61L. Same sample size, same correlations, only the tail shape changed. The
simulated portfolio σ ties to the real book at 0.894% vs 0.896% daily, so the engine is
calibrated before its tail is trusted.

> **Key finding:** at the 99% level the normal model captures only ~72% of the true tail loss — it under-books by ~₹41k (VaR) and ~₹67k (ES). The Monte Carlo Student-t engine reproduces the fat tail by construction, confirming the gap is a distribution-shape effect, not a sampling artefact.

## 4. Backtesting (203-day out-of-sample, rolling 250-day VaR)

- 95% VaR: 16 breaches (7.9% vs 5% expected). **Kupiec POF passes** (p = 0.08) — but only just.
- 99% VaR: 4 breaches → **Basel yellow zone** (4.9 per 250 days).

**Christoffersen tests (count *and* timing):**

| | Kupiec (count) | Independence (clustering) | Cond. coverage |
|---|---|---|---|
| 95% VaR | LR 3.04, p 0.081 | LR 0.44, **p 0.509** | LR 3.48, p 0.176 |
| 99% VaR | LR 1.51, p 0.220 | LR 3.71, **p 0.054** | LR 5.21, p 0.074 |

> The 95% breaches are independent (p = 0.51); the 99% breaches are *borderline*-clustered (p = 0.054), consistent with the visible Mar-2026 bunching. **But with only 4 breaches at 99% the independence test is low-power**, so this is read as suggestive, not conclusive. A longer history (or EWMA/GARCH conditional volatility, which reacts faster to regime shifts) would sharpen the test.

> Honest verdict: the model is *count-honest*; the only timing concern is a low-power, borderline signal at 99%, consistent with the measured excess kurtosis.

## 4b. Conditional volatility (EWMA & GARCH)

The static rolling-250 VaR reacts late ("ghosting": a shock enters the window, VaR cliffs down, then jumps back when it rolls out). Two conditional-volatility models fix this by weighting recent days more heavily:

- **EWMA (RiskMetrics, λ = 0.94)** — reactive variance; the VaR threshold widens in turbulent stretches and tightens in calm, tracking the regime instead of lagging it.
- **GARCH(1,1) with Student-t errors** — α = 0.235, β = 0.672, **persistence α + β = 0.907** (both highly significant) → statistical confirmation of **volatility clustering**. Latest conditional vol 13.3% annualised vs 14.2% unconditional.

> **Lesson surfaced:** reactive volatility and fat tails are *separate* fixes. EWMA paired with a **normal** quantile breached on 16 of 451 days — **3.55% against a 1% target** — so reactive volatility alone does not cover kurtosis. The GARCH fit is specified with Student-t errors for exactly this reason, but the paired *EWMA-t* quantile has not been backtested here; the working conclusion is that a production VaR needs conditional volatility **and** a fat-tailed distribution, and only the first half of that claim is measured in this notebook. *(Open item, §Limitations.)*

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

**A measurement trap worth naming.** Over the full window, gold's correlation to the *equity
basket* is **0.125** — a genuine diversifier — while its correlation to the *portfolio* is
**0.667**. There is no contradiction: gold is 27.6% of the book, so the portfolio is substantially
correlating with itself. Correlation-to-portfolio is inflated by own weight; the clean
diversification read is asset-to-asset.

Average pairwise correlation rises from **0.10 (calm) → 0.34 (crisis)** — diversification weakens by ~3.5× exactly when it is needed. **Gold–equity correlation flips from −0.14 (calm) to +0.15 (COVID)** — a *fair-weather* hedge: it protects in normal times and mild stress, but degrades in an acute liquidity crisis (the March-2020 "dash for cash"). The hedge still cushioned the full scenario, but imperfectly.

---

## Limitations & production notes (model-risk governance)

- SGBs proxied by a gold ETF (illiquid underlyings) — justified by shared risk factor.
- LONG sleeve reweights to a representative subset; rupee stress figures assume the book behaves like its long-history sleeve (excludes post-2019 IPOs).
- 99% VaR on ~1.8 yr is defined by only ~4–5 worst days → a thin, unstable tail estimate; ES and stress testing compensate.
- Single-day horizon; Basel 10-day VaR would scale by √10 (independence assumption).
- **Stress shocks are judgment-based**, not calibrated from a factor model — asset-class shock
  vectors chosen by hand. The COVID cross-check (−16.6% hypothetical vs −15.2% actual) is the
  only calibration evidence offered.
- **GARCH persistence α + β = 0.907** is lower than the 0.95–0.99 typical of equity books,
  reflecting the ~1.8-year sample. The clustering signal is unambiguous; the parameter estimate
  is not precise.
- Open enhancements: backtest an **EWMA/GARCH Student-t** quantile (the fat-tail half of §4b is
  argued but not yet measured); extend history beyond 2018 to make the 99% independence test
  better-powered; add a 10-day horizon and a liquidity-adjusted VaR.

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
│   └── Project 2.ipynb       # full analysis, Sessions 1-7
├── output/
│   └── risk_dashboard.png    # 6-panel summary dashboard
├── app.py                    # interactive Streamlit dashboard
└── README.md
```

## How to run

**Notebook (full analysis):**
```bash
pip install pandas numpy scipy matplotlib yfinance arch
```
Open `notebooks/Project 2.ipynb` and run top-to-bottom. Prices are pulled live from yfinance;
`data/holdings.csv` makes the portfolio reproducible without a broker login. Paths inside the
notebook are absolute Windows paths and need repointing on another machine. Figures are as of the
2026-06-19 data pull; re-running extends the window and will move every number slightly.

**Interactive dashboard:**
```bash
pip install streamlit
streamlit run app.py
```
Sidebar controls (confidence level 90/95/99, VaR method) recompute the VaR, Expected Shortfall, distribution chart and stress table live. Reads the saved CSVs in `data/` — no broker login needed.

---

## Methodology references

Basel III / FRTB (Expected Shortfall, traffic-light backtesting) · Kupiec (1995) proportion-of-failures test · Christoffersen (1998) conditional coverage · RiskMetrics (parametric VaR).

*Educational project. Not investment advice. Portfolio figures are illustrative of methodology.*
