
import os
import json
import urllib.request
import pandas as pd

DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../data")
)
os.makedirs(DATA_DIR, exist_ok=True)

API_URL = "https://tickerinside.com/api/v1/fund/{}.json"


def fetch_etf_holdings(ticker: str) -> pd.DataFrame:
    """
    Fetch ETF holdings from TickerInside.

    Weights from the API are percentages, e.g. 10.2531 means 10.2531%.
    Convert them to fractions for the overlap analyzer.
    """

    ticker = ticker.upper().strip()
    cache_file = os.path.join(
        DATA_DIR, f"{ticker}_holdings.parquet"
    )

    try:
        print(f"[*] Fetching TickerInside data for {ticker}...")

        url = API_URL.format(ticker.lower())

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ETFOverlapCalculator/1.0"
            }
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if payload.get("ticker", "").upper() != ticker:
            raise ValueError(
                f"API returned unexpected ticker: {payload.get('ticker')}"
            )

        holdings = payload.get("holdings")

        if not isinstance(holdings, dict) or not holdings:
            raise ValueError(f"No holdings available for {ticker}")

        # Convert ticker -> percentage weight into a DataFrame
        clean_df = pd.DataFrame([
            {
                "ticker": holding_ticker,
                "name": holding_ticker,
                "weight": float(weight) / 100.0,
                "holdings_as_of": payload.get("holdings_as_of"),
                "source_layer": payload.get("source_layer"),
            }
            for holding_ticker, weight in holdings.items()
        ])

        clean_df["ticker"] = (
            clean_df["ticker"].astype("string").str.strip().str.upper()
        )

        clean_df["weight"] = pd.to_numeric(
            clean_df["weight"], errors="coerce"
        )

        clean_df = clean_df.dropna(subset=["ticker", "weight"])
        clean_df = clean_df[clean_df["weight"] > 0].copy()

        if clean_df.empty:
            raise ValueError(f"No valid holdings for {ticker}")

        holdings_date = payload.get("holdings_as_of")
        source_layer = payload.get("source_layer")

        print(
            f"[{ticker}] Positions: {len(clean_df)}, "
            f"Holdings date: {holdings_date}, "
            f"Source: {source_layer}, "
            f"Weight sum: {clean_df['weight'].sum():.4f}"
        )

        # Save holdings and source metadata
        clean_df.to_parquet(cache_file, index=False)

        return clean_df

    except Exception as e:
        print(
            f"[!] Error fetching TickerInside data for {ticker}: {e}. "
            "Checking local cache..."
        )

        if os.path.exists(cache_file):
            print(f"[{ticker}] Using cached holdings.")
            return pd.read_parquet(cache_file)

        raise RuntimeError(
            f"Could not retrieve holdings for {ticker} "
            "from TickerInside or cache."
        ) from e
