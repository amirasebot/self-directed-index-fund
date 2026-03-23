import re


CLASS_SUFFIX_PATTERNS = [
    re.compile(r"\s+class\s+[a-z0-9-]+$", re.IGNORECASE),
    re.compile(r"\s+\(class\s+[a-z0-9-]+\)$", re.IGNORECASE),
]


def normalize_company_name(name):
    if not isinstance(name, str):
        return ""
    normalized = name.strip()
    for pattern in CLASS_SUFFIX_PATTERNS:
        normalized = pattern.sub("", normalized).strip()
    return normalized


def compute_weights(df):
    result = df.copy()
    result["company_name"] = result["Security"].apply(normalize_company_name)
    result["class_count"] = result.groupby("company_name")["Symbol"].transform("nunique")

    # Class tickers often report the same full-company market cap; use the
    # company-level average before splitting weight across share classes.
    company_market_cap = result.groupby("company_name")["market_cap"].transform("mean")
    total_market_cap = company_market_cap.drop_duplicates().sum()

    if total_market_cap <= 0:
        result["weight"] = 0.0
        return result

    result["company_weight"] = company_market_cap / total_market_cap
    result["weight"] = result["company_weight"] / result["class_count"]
    return result
