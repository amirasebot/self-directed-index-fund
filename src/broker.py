import os

import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest


API_KEY = os.getenv("ALPACA_API_KEY")
SECRET = os.getenv("ALPACA_SECRET_KEY")
PAPER = os.getenv("ALPACA_PAPER", "true").lower() == "true"

api = TradingClient(API_KEY, SECRET, paper=PAPER)


def get_price(symbol):
    history = yf.Ticker(symbol).history(period="1d")
    if history.empty:
        raise ValueError(f"No price data available for {symbol}")
    return float(history["Close"].iloc[-1])


def execute_orders(orders, portfolio_value):
    for o in orders:
        dollar_amount = abs(o["weight_diff"]) * portfolio_value
        qty = int(dollar_amount / get_price(o["symbol"]))

        if qty > 0:
            side = OrderSide.BUY if o["action"] == "buy" else OrderSide.SELL
            order = MarketOrderRequest(
                symbol=o["symbol"],
                qty=qty,
                side=side,
                time_in_force=TimeInForce.DAY,
            )
            api.submit_order(order_data=order)
