# Create Self Directed Index Fund

Build a self-directed index from the S&P 500, refresh the underlying portfolio data, and explore the result in a Streamlit dashboard with dynamic filters and backtests.

## What This Project Does

- pulls the S&P 500 universe
- enriches each symbol with market cap and historical performance
- computes portfolio weights
- splits company weight across multiple share classes when needed
- saves the result to `portfolio.csv`
- serves an interactive dashboard for filtering and backtesting

## Project Flow

```text
S&P 500 source
    ↓
main.py
    ↓
portfolio.csv
    ↓
app.py
    ↓
Streamlit dashboard
```

## Project Structure

```text
custom-index/
├── app.py
├── main.py
├── portfolio.csv
├── requirements.txt
├── README.md
├── config/
├── dags/
├── notebooks/
├── pages/
└── src/
```

## Setup

Create and activate the virtual environment if needed:

```bash
cd /Users/amiribrahim/workspace/github/custom-index
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Refresh Portfolio Data

Use this when you want to regenerate `portfolio.csv` from the latest available data.

```bash
cd /Users/amiribrahim/workspace/github/custom-index
.venv/bin/python main.py
```

What this does:

```text
Fetch S&P 500
    ↓
Pull market cap + returns
    ↓
Compute class-adjusted weights
    ↓
Write portfolio.csv
```

Expected output:

```text
Symbol  Security  ...  company_weight  weight
...
```

After it finishes, the refreshed portfolio will be saved at:

`/Users/amiribrahim/workspace/github/custom-index/portfolio.csv`

## Start the Dashboard Server

Run the Streamlit app:

```bash
cd /Users/amiribrahim/workspace/github/custom-index
.venv/bin/streamlit run app.py
```

Then open the local URL shown by Streamlit, usually:

```text
http://localhost:8501
```

## Dashboard Pages

### Create Self Directed Index Fund

Use this page to:

- start from the full S&P 500
- filter by sector
- filter by sub-industry
- add include filters one at a time
- add exclude filters one at a time
- reset all filters

### Allocation Dashboard

Use this page to:

- test a lump-sum investment
- add monthly or yearly contributions
- backtest over `1Y`, `3Y`, `5Y`, `10Y`, and `Life`

## Typical Workflow

```text
1. Refresh portfolio data with main.py
2. Start Streamlit with app.py
3. Open dashboard in browser
4. Apply filters
5. Review weights and backtest results
```

## Notes

- `portfolio.csv` is the base dataset used by the dashboard
- dashboard inputs are persisted locally in `config/ui_state.json`
- some Yahoo Finance tickers, especially dot-class symbols, may occasionally return incomplete data

