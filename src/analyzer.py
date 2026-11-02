
import pandas as pd
import numpy as np



def _prepare_holdings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare holdings for equity overlap analysis.

    - Remove missing or invalid ticker identifiers.
    - Exclude cash equivalents and money-market instruments.
    - Remove invalid or non-positive weights.
    - Aggregate duplicate tickers.
    - Normalize weights to sum to 1.
    """

    required = {"ticker", "name", "weight"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.copy()
    original_count = len(df)

    # Clean ticker identifiers
    df["ticker"] = (
        df["ticker"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    invalid_tickers = ["", "NAN", "NONE", "NULL", "N/A", "-"]
    df.loc[df["ticker"].isin(invalid_tickers), "ticker"] = pd.NA

    # Ignore unidentified positions
    df = df.dropna(subset=["ticker"]).copy()

    # Exclude cash-like instruments
    cash_pattern = (
        r"money market|market liquidity|cash equivalent|"
        r"cash and cash equivalents|repurchase agreement|"
        r"cash collateral"
    )

    df = df[
        ~df["name"].fillna("").str.contains(
            cash_pattern, case=False, regex=True
        )
    ].copy()

    # Convert weights to numeric
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    df["weight"] = df["weight"].replace(
        [np.inf, -np.inf], np.nan
    )

    df = df.dropna(subset=["weight"])
    df = df[df["weight"] > 0].copy()

    # Aggregate duplicate tickers
    holdings = (
        df.groupby("ticker", as_index=False)
        .agg(
            name=("name", "first"),
            weight=("weight", "sum")
        )
    )

    total_weight = holdings["weight"].sum()

    if not np.isfinite(total_weight) or total_weight <= 0:
        print("\n[WARNING] No valid holdings after preprocessing.")
        print(f"Original rows: {original_count}")
        print(f"Rows remaining: {len(df)}")
        print("Original data sample:")
        print(df.head(10).to_string())
        raise ValueError("No valid positive holdings weights.")

    # Normalize identifiable equity holdings to 100%
    holdings["weight"] /= total_weight

    return holdings



def compute_pairwise_overlap(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    name_a: str = "Fund A",
    name_b: str = "Fund B"
) -> dict:
    """
    Calculate equity holdings overlap between two ETFs.

    Sum-of-min:
        sum(min(weight_A, weight_B)) over shared securities.

    Directional A:
        Percentage of Fund A's equity portfolio invested
        in securities also held by Fund B.

    Directional B:
        Percentage of Fund B's equity portfolio invested
        in securities also held by Fund A.
    """

    a = _prepare_holdings(df_a)
    b = _prepare_holdings(df_b)

    # Each ticker must occur only once per ETF
    assert a["ticker"].is_unique
    assert b["ticker"].is_unique

    # Inner join: only securities held by both ETFs
    shared = pd.merge(
        a,
        b,
        on="ticker",
        how="inner",
        suffixes=("_a", "_b"),
        validate="one_to_one"
    )

    # Calculate overlap contribution
    shared["min_weight"] = np.minimum(
        shared["weight_a"],
        shared["weight_b"]
    )

    sum_of_min = shared["min_weight"].sum()

    # Directional coverage
    directional_a_in_b = shared["weight_a"].sum()
    directional_b_in_a = shared["weight_b"].sum()

    # Shared holdings table
    shared_df = pd.DataFrame({
        "ticker": shared["ticker"],
        "name": shared["name_a"].combine_first(
            shared["name_b"]
        ),
        f"Weight in {name_a}": shared["weight_a"],
        f"Weight in {name_b}": shared["weight_b"],
        "Overlap Allocation (Min)": shared["min_weight"]
    })

    shared_df = shared_df.sort_values(
        "Overlap Allocation (Min)",
        ascending=False
    ).reset_index(drop=True)

    # Sanity checks
    assert 0 <= sum_of_min <= 1 + 1e-9
    assert 0 <= directional_a_in_b <= 1 + 1e-9
    assert 0 <= directional_b_in_a <= 1 + 1e-9

    return {
        "shared_count": len(shared),
        "total_count_a": len(a),
        "total_count_b": len(b),
        "count_overlap_a": (
            len(shared) / len(a) if len(a) else 0
        ),
        "count_overlap_b": (
            len(shared) / len(b) if len(b) else 0
        ),
        "directional_a_in_b": float(directional_a_in_b),
        "directional_b_in_a": float(directional_b_in_a),
        "sum_of_min": float(sum_of_min),
        "shared_holdings_df": shared_df
    }
