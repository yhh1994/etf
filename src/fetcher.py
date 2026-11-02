
import os
import pandas as pd
from edgar import set_identity, Company

# SEC identity
set_identity(os.getenv(
    "EDGAR_IDENTITY",
    "ETFOverlapAnalyst research@example.com"
))

DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../data")
)
os.makedirs(DATA_DIR, exist_ok=True)


def fetch_etf_holdings(ticker: str) -> pd.DataFrame:
    """
    Fetch the latest SEC N-PORT filing and return standardized holdings.

    Missing ticker identifiers are retained as NA so that the analyzer
    can exclude them from equity overlap calculations.
    """

    ticker = ticker.upper().strip()
    cache_file = os.path.join(
        DATA_DIR, f"{ticker}_holdings.parquet"
    )

    try:
        print(f"[*] Fetching SEC N-PORT data for {ticker}...")

        company = Company(ticker)
        filings = company.get_filings(form="NPORT-P")

        if not filings:
            raise ValueError(f"No N-PORT filings found for {ticker}")

        latest_filing = filings[0]
        fund_obj = latest_filing.obj()
        df = fund_obj.investment_data()

        if df is None or df.empty:
            raise ValueError(f"Empty investment data for {ticker}")

        print(f"[{ticker}] Original columns: {df.columns.tolist()}")
        print(f"[{ticker}] Original rows: {len(df)}")

        # Identify columns explicitly
        columns_lower = {
            col: col.lower().strip()
            for col in df.columns
        }

        ticker_col = next(
            (col for col, name in columns_lower.items()
             if name == "ticker" or name.endswith("_ticker")),
            None
        )

        name_col = next(
            (col for col, name in columns_lower.items()
             if name in ("name", "issuer_name", "investment_name")),
            None
        )

        weight_col = next(
            (col for col, name in columns_lower.items()
             if name in ("pct_value", "weight", "portfolio_weight")),
            None
        )

        if weight_col is None:
            raise ValueError(
                f"Cannot identify weight column. "
                f"Available columns: {df.columns.tolist()}"
            )

        clean_df = pd.DataFrame()

        clean_df["ticker"] = (
            df[ticker_col] if ticker_col else pd.NA
        )

        clean_df["name"] = (
            df[name_col] if name_col else pd.NA
        )

        clean_df["weight"] = pd.to_numeric(
            df[weight_col], errors="coerce"
        )

        # Normalize ticker strings without replacing missing values
        clean_df["ticker"] = (
            clean_df["ticker"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        invalid_tickers = ["", "NAN", "NONE", "NULL", "N/A", "-"]
        clean_df.loc[
            clean_df["ticker"].isin(invalid_tickers), "ticker"
        ] = pd.NA

        # Remove invalid weights; analyzer handles zero weights
        clean_df["weight"] = clean_df["weight"].replace(
            [float("inf"), float("-inf")], pd.NA
        )

        clean_df = clean_df.dropna(subset=["weight"])
        clean_df = clean_df[clean_df["weight"] > 0].copy()

        # N-PORT percentage weights may be fractions or percentages.
        # Inspect the total before deciding whether conversion is needed.
        weight_sum = clean_df["weight"].sum()

        if weight_sum > 2.0:
            clean_df["weight"] /= 100.0

        print(
            f"[{ticker}] Valid rows: {len(clean_df)}, "
            f"missing tickers: {clean_df['ticker'].isna().sum()}, "
            f"weight sum: {clean_df['weight'].sum():.4f}"
        )

        clean_df.to_parquet(cache_file, index=False)

        return clean_df

    except Exception as e:
        print(
            f"[!] Error pulling via EDGAR for {ticker}: {e}. "
            "Checking local cache..."
        )

        if os.path.exists(cache_file):
            print(f"[{ticker}] Using cached holdings.")
            return pd.read_parquet(cache_file)

        raise RuntimeError(
            f"Could not retrieve holdings for {ticker} "
            "from SEC or cache."
        ) from e
