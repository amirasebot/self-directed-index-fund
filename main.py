from src.data import get_sp500, add_market_cap
from src.weights import compute_weights

df = get_sp500()
df = add_market_cap(df)
df = compute_weights(df)

df.to_csv("portfolio.csv", index=False)
print(df.head())
