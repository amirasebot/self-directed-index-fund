EXCLUDE_SECTORS = ["Financials"]

EXCLUDE_KEYWORDS = [
    "casino",
    "gambling",
    "betting",
    "resort casino",
    "alcohol",
    "financial",
    "hotel",
    "restaurant",
    "insurance",
    "pork",
]


def filter_companies(df):
    df = df[~df["GICS Sector"].isin(EXCLUDE_SECTORS)]

    mask = df["GICS Sub-Industry"].str.lower().apply(
        lambda x: any(k in x for k in EXCLUDE_KEYWORDS)
    )
    df = df[~mask]

    return df
