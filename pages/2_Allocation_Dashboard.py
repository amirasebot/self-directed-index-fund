import json
from pathlib import Path

import pandas as pd
import streamlit as st


PORTFOLIO_PATH = Path(__file__).resolve().parents[1] / "portfolio.csv"
BACKTEST_COLUMNS = ["perf_1y", "perf_3y", "perf_5y", "perf_10y", "perf_life"]
BACKTEST_LABELS = {
    "perf_1y": "1Y",
    "perf_3y": "3Y",
    "perf_5y": "5Y",
    "perf_10y": "10Y",
    "perf_life": "Life",
}
PERIOD_YEARS = {
    "perf_1y": 1,
    "perf_3y": 3,
    "perf_5y": 5,
    "perf_10y": 10,
}
FREQUENCY_PERIODS = {
    "Monthly": 12,
    "Yearly": 1,
}
SESSION_STATE_DEFAULTS = {
    "initial_investment": 10000.0,
    "recurring_amount": 0.0,
    "recurring_frequency": "Monthly",
    "allocation_top_n": 15,
    "selected_period": "perf_1y",
}


st.set_page_config(
    page_title="Backtest Self Directed Index Fund",
    page_icon="AD",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(120, 255, 214, 0.18), transparent 30%),
            radial-gradient(circle at top right, rgba(255, 214, 102, 0.16), transparent 34%),
            linear-gradient(180deg, #07131a 0%, #0c1d24 55%, #11252b 100%);
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .hero {
        padding: 1.4rem 1.6rem;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 24px;
        background: linear-gradient(135deg, rgba(10, 27, 34, 0.92), rgba(8, 17, 22, 0.94));
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.28);
        margin-bottom: 1rem;
    }
    .eyebrow {
        letter-spacing: 0.14em;
        text-transform: uppercase;
        font-size: 0.78rem;
        color: #78ffd6;
        margin-bottom: 0.2rem;
    }
    .hero h1 {
        margin: 0;
        font-size: 2.5rem;
        line-height: 1.05;
        color: #f4fffd;
    }
    .hero p {
        margin-top: 0.7rem;
        margin-bottom: 0;
        max-width: 54rem;
        color: #b8d1d2;
        font-size: 1rem;
    }
    .metric-card {
        padding: 1rem 1.1rem;
        border-radius: 20px;
        background: rgba(7, 19, 26, 0.72);
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .metric-label {
        color: #93b6b7;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .metric-value {
        color: #f4fffd;
        font-size: 1.9rem;
        font-weight: 700;
        margin-top: 0.25rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_portfolio(path_str: str, modified_time_ns: int, file_size: int) -> pd.DataFrame:
    df = pd.read_csv(path_str)
    required_defaults = {
        "weight": 0.0,
        "perf_1y": 0.0,
        "perf_3y": 0.0,
        "perf_5y": 0.0,
        "perf_10y": 0.0,
        "perf_life": 0.0,
    }
    for column, default in required_defaults.items():
        if column not in df.columns:
            df[column] = default
    df["weight_pct"] = df["weight"] * 100
    return df.sort_values("weight", ascending=False).reset_index(drop=True)


def _deserialize_query_value(key: str, default):
    value = st.query_params.get(key)
    if value is None:
        return default

    if isinstance(default, int) and not isinstance(default, bool):
        try:
            return int(value)
        except ValueError:
            return default
    if isinstance(default, float):
        try:
            return float(value)
        except ValueError:
            return default
    return str(value)


def initialize_session_state_from_query_params() -> None:
    if st.session_state.get("_allocation_query_state_initialized"):
        return

    for key, default in SESSION_STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = _deserialize_query_value(key, default)
    st.session_state["_allocation_query_state_initialized"] = True


def sync_query_params_from_session_state() -> None:
    for key, default in SESSION_STATE_DEFAULTS.items():
        st.query_params[key] = str(st.session_state.get(key, default))


def _future_value(principal: float, total_return: float, years: int, recurring_payment: float, periods_per_year: int) -> tuple[float, float]:
    growth_factor = max(0.000001, 1 + total_return)
    total_periods = years * periods_per_year
    periodic_rate = growth_factor ** (1 / total_periods) - 1

    principal_value = principal * ((1 + periodic_rate) ** total_periods)
    if recurring_payment <= 0:
        return principal_value, principal

    if abs(periodic_rate) < 1e-9:
        recurring_value = recurring_payment * total_periods
    else:
        recurring_value = recurring_payment * ((((1 + periodic_rate) ** total_periods) - 1) / periodic_rate)

    return principal_value + recurring_value, principal + (recurring_payment * total_periods)


def _build_backtest(
    df: pd.DataFrame,
    initial_investment: float,
    recurring_amount: float,
    recurring_frequency: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    allocatable = df.copy()
    allocatable["allocation_usd"] = (allocatable["weight"] * initial_investment).round(2)
    allocatable["recurring_allocation_usd"] = (allocatable["weight"] * recurring_amount).round(2)
    allocatable = allocatable[(allocatable["allocation_usd"] > 0) | (allocatable["recurring_allocation_usd"] > 0)].copy()

    periods_per_year = FREQUENCY_PERIODS[recurring_frequency]
    totals = []

    for column in BACKTEST_COLUMNS:
        value_column = f"value_{column}"
        contributed_column = f"contributed_{column}"

        if column in PERIOD_YEARS:
            years = PERIOD_YEARS[column]
            values = []
            contributed = []
            for _, row in allocatable.iterrows():
                final_value, total_contributed = _future_value(
                    principal=row["allocation_usd"],
                    total_return=row[column],
                    years=years,
                    recurring_payment=row["recurring_allocation_usd"],
                    periods_per_year=periods_per_year,
                )
                values.append(final_value)
                contributed.append(total_contributed)
            allocatable[value_column] = values
            allocatable[contributed_column] = contributed
        else:
            allocatable[value_column] = allocatable["allocation_usd"] * (1 + allocatable[column].fillna(0))
            allocatable[contributed_column] = allocatable["allocation_usd"]

        total_value = allocatable[value_column].sum()
        total_contributed = allocatable[contributed_column].sum()
        totals.append(
            {
                "Period": BACKTEST_LABELS[column],
                "Total Contributed ($)": total_contributed,
                "Portfolio Value ($)": total_value,
                "Portfolio Return (%)": (((total_value / total_contributed) - 1) * 100) if total_contributed else 0,
            }
        )

    return allocatable, pd.DataFrame(totals)


def _add_display_return_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for column in BACKTEST_COLUMNS:
        result[f"{column}_pct"] = result[column] * 100
    return result


st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">Capital Planner</div>
        <h1>Backtest Self Directed Index</h1>
        <p>
            Backtest a lump sum plus recurring monthly or yearly contributions
            against the portfolio's weighted historical returns.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not PORTFOLIO_PATH.exists():
    st.error("portfolio.csv not found. Run `main.py` first to generate the portfolio.")
    st.stop()

initialize_session_state_from_query_params()

portfolio_stat = PORTFOLIO_PATH.stat()
portfolio = load_portfolio(str(PORTFOLIO_PATH), portfolio_stat.st_mtime_ns, portfolio_stat.st_size)

initial_investment = st.sidebar.number_input(
    "Initial investment ($)",
    min_value=0.0,
    step=500.0,
    key="initial_investment",
)
recurring_amount = st.sidebar.number_input(
    "Recurring contribution ($)",
    min_value=0.0,
    step=100.0,
    key="recurring_amount",
)
recurring_frequency = st.sidebar.selectbox(
    "Contribution frequency",
    list(FREQUENCY_PERIODS.keys()),
    key="recurring_frequency",
)
top_n = st.sidebar.slider("Show top allocations", 5, 50, step=5, key="allocation_top_n")
selected_period = st.sidebar.selectbox(
    "Backtest period",
    BACKTEST_COLUMNS,
    format_func=lambda key: BACKTEST_LABELS[key],
    key="selected_period",
)

allocatable, totals = _build_backtest(
    portfolio,
    initial_investment=initial_investment,
    recurring_amount=recurring_amount,
    recurring_frequency=recurring_frequency,
)
allocatable_display = _add_display_return_columns(allocatable)
top_allocations_display = allocatable_display.head(top_n).copy()
selected_total = totals.loc[totals["Period"] == BACKTEST_LABELS[selected_period]].iloc[0]

if recurring_amount > 0 and selected_period == "perf_life":
    st.info("Recurring contribution math is applied to 1Y, 3Y, 5Y, and 10Y periods. Life uses lump-sum only because the holding period varies by symbol.")

col1, col2, col3, col4 = st.columns(4)
metrics = [
    ("Initial Investment", f"${initial_investment:,.2f}"),
    ("Contributed", f"${selected_total['Total Contributed ($)']:,.2f}"),
    ("Backtest Value", f"${selected_total['Portfolio Value ($)']:,.2f}"),
    ("Backtest Return", f"{selected_total['Portfolio Return (%)']:.2f}%"),
]

for column, (label, value) in zip((col1, col2, col3, col4), metrics):
    column.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

sync_query_params_from_session_state()

st.subheader("Portfolio Backtest Summary")
st.dataframe(
    totals,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Total Contributed ($)": st.column_config.NumberColumn(format="$%.2f"),
        "Portfolio Value ($)": st.column_config.NumberColumn(format="$%.2f"),
        "Portfolio Return (%)": st.column_config.NumberColumn(format="%.2f%%"),
    },
)

left, right = st.columns((1.25, 0.75))

with left:
    st.subheader("Top Dollar Allocations")
    st.dataframe(
        top_allocations_display[
            [
                "Symbol",
                "Security",
                "GICS Sector",
                "weight_pct",
                "allocation_usd",
                "recurring_allocation_usd",
                f"{selected_period}_pct",
                f"value_{selected_period}",
            ]
        ].rename(
            columns={
                "weight_pct": "Weight (%)",
                "allocation_usd": "Initial Allocation ($)",
                "recurring_allocation_usd": f"Recurring {recurring_frequency} ($)",
                f"{selected_period}_pct": f"{BACKTEST_LABELS[selected_period]} Return (%)",
                f"value_{selected_period}": f"{BACKTEST_LABELS[selected_period]} Value ($)",
            }
        ),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Weight (%)": st.column_config.NumberColumn(format="%.3f"),
            "Initial Allocation ($)": st.column_config.NumberColumn(format="$%.2f"),
            f"Recurring {recurring_frequency} ($)": st.column_config.NumberColumn(format="$%.2f"),
            f"{BACKTEST_LABELS[selected_period]} Return (%)": st.column_config.NumberColumn(format="%.2f%%"),
            f"{BACKTEST_LABELS[selected_period]} Value ($)": st.column_config.NumberColumn(format="$%.2f"),
        },
    )

with right:
    st.subheader("Backtested Value by Sector")
    sector_allocations = (
        allocatable.groupby("GICS Sector", dropna=False)[f"value_{selected_period}"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    st.bar_chart(
        sector_allocations,
        x="GICS Sector",
        y=f"value_{selected_period}",
        horizontal=True,
    )

st.subheader("Full Allocation Table")
st.dataframe(
    allocatable_display[
        [
            "Symbol",
            "Security",
            "GICS Sector",
            "GICS Sub-Industry",
            "weight_pct",
            "allocation_usd",
            "recurring_allocation_usd",
            "perf_1y_pct",
            "perf_3y_pct",
            "perf_5y_pct",
            "perf_10y_pct",
            "perf_life_pct",
        ]
    ].rename(
        columns={
            "weight_pct": "Weight (%)",
            "allocation_usd": "Initial Allocation ($)",
            "recurring_allocation_usd": f"Recurring {recurring_frequency} ($)",
            "perf_1y_pct": "1Y Return (%)",
            "perf_3y_pct": "3Y Return (%)",
            "perf_5y_pct": "5Y Return (%)",
            "perf_10y_pct": "10Y Return (%)",
            "perf_life_pct": "Life Return (%)",
        }
    ),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Weight (%)": st.column_config.NumberColumn(format="%.3f"),
        "Initial Allocation ($)": st.column_config.NumberColumn(format="$%.2f"),
        f"Recurring {recurring_frequency} ($)": st.column_config.NumberColumn(format="$%.2f"),
        "1Y Return (%)": st.column_config.NumberColumn(format="%.2f%%"),
        "3Y Return (%)": st.column_config.NumberColumn(format="%.2f%%"),
        "5Y Return (%)": st.column_config.NumberColumn(format="%.2f%%"),
        "10Y Return (%)": st.column_config.NumberColumn(format="%.2f%%"),
        "Life Return (%)": st.column_config.NumberColumn(format="%.2f%%"),
    },
)
