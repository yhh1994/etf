import os
import json
from src.fetcher import fetch_etf_holdings
from src.analyzer import compute_pairwise_overlap

# Define your watchlist of popular ETFs to pre-calculate
WATCHLIST = ["VUG", "VOO", "SCHD", "QQQ", "IVV"]

def generate_static_data():
    holdings_cache = {}
    
    # 1. Fetch and cache individual ETF holdings
    for ticker in WATCHLIST:
        try:
            df = fetch_etf_holdings(ticker)
            holdings_cache[ticker] = df.to_dict(orient="records")
        except Exception as e:
            print(f"Skipping {ticker}: {e}")
            
    # 2. Pre-compute common pairwise combinations
    comparisons = {}
    tickers = list(holdings_cache.keys())
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            t1, t2 = tickers[i], tickers[j]
            df_a = pd.DataFrame(holdings_cache[t1])
            df_b = pd.DataFrame(holdings_cache[t2])
            
            metrics = compute_pairwise_overlap(df_a, df_b, name_a=t1, name_b=t2)
            # Drop heavy dataframes from JSON if needed, keep summary metrics & shared table
            comparisons[f"{t1}_vs_{t2}"] = {
                "sum_of_min": metrics["sum_of_min"],
                "directional_a_in_b": metrics["directional_a_in_b"],
                "directional_b_in_a": metrics["directional_b_in_a"],
                "shared_count": metrics["shared_count"],
                "shared_holdings": metrics["shared_holdings_df"].to_dict(orient="records")
            }

    output = {
        "watchlist": WATCHLIST,
        "comparisons": comparisons
    }
    
    with open("etf_data.json", "w") as f:
        json.dump(output, f)

if __name__ == "__main__":
    import pandas as pd
    generate_static_data()
