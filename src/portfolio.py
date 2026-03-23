def generate_orders(target, current):
    orders = []

    for _, row in target.iterrows():
        symbol = row["Symbol"]
        target_weight = row["weight"]
        current_weight = current.get(symbol, 0)

        diff = target_weight - current_weight

        if abs(diff) > 0.001:
            orders.append(
                {
                    "symbol": symbol,
                    "action": "buy" if diff > 0 else "sell",
                    "weight_diff": diff,
                }
            )

    return orders
