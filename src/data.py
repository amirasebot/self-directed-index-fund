from concurrent.futures import ThreadPoolExecutor
from io import StringIO

import certifi
import pandas as pd
import requests
import yfinance as yf


PERFORMANCE_PERIODS = {
    "perf_1y": pd.DateOffset(years=1),
    "perf_3y": pd.DateOffset(years=3),
    "perf_5y": pd.DateOffset(years=5),
    "perf_10y": pd.DateOffset(years=10),
}


def get_sp500():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    response = requests.get(
        url,
        timeout=30,
        verify=certifi.where(),
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            )
        },
    )
    response.raise_for_status()
    table = pd.read_html(StringIO(response.text))[0]
    return table[["Symbol", "Security", "GICS Sector", "GICS Sub-Industry"]]


def _compute_period_return(close_prices, offset):
    if close_prices.empty:
        return None

    latest_price = float(close_prices.iloc[-1])
    latest_date = close_prices.index[-1]
    target_date = latest_date - offset
    candidates = close_prices[close_prices.index >= target_date]
    if candidates.empty:
        return None

    base_price = float(candidates.iloc[0])
    if base_price <= 0:
        return None

    return (latest_price / base_price) - 1


def _compute_life_return(close_prices):
    if close_prices.empty:
        return None

    valid_prices = close_prices[close_prices > 0]
    if valid_prices.empty:
        return None

    first_price = float(valid_prices.iloc[0])
    latest_price = float(valid_prices.iloc[-1])
    return (latest_price / first_price) - 1


def _fetch_symbol_metrics(ticker):
    metrics = {
        "market_cap": 0,
        "perf_1y": None,
        "perf_3y": None,
        "perf_5y": None,
        "perf_10y": None,
        "perf_life": None,
    }

    try:
        symbol = yf.Ticker(ticker)
        info = symbol.info
        metrics["market_cap"] = info.get("marketCap", 0) or 0
    except Exception:
        metrics["market_cap"] = 0

    try:
        history = symbol.history(period="max", auto_adjust=True)
        if history.empty:
            return metrics

        close_prices = history["Close"].dropna()
        close_prices.index = close_prices.index.tz_localize(None)
        if close_prices.empty:
            return metrics

        for column, offset in PERFORMANCE_PERIODS.items():
            metrics[column] = _compute_period_return(close_prices, offset)
        metrics["perf_life"] = _compute_life_return(close_prices)
    except Exception:
        return metrics

    return metrics


def add_market_cap(df):
    symbols = df["Symbol"].tolist()
    max_workers = min(32, max(1, len(symbols)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        rows = list(executor.map(_fetch_symbol_metrics, symbols))

    metrics_df = pd.DataFrame(rows)
    result = df.copy().reset_index(drop=True)
    for column in metrics_df.columns:
        result[column] = metrics_df[column]
    return result
