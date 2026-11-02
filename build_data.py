import os
import json
import pandas as pd
from src.fetcher import fetch_etf_holdings
from src.analyzer import compute_pairwise_overlap

WATCHLIST = ["VUG", "VOO", "SCHD", "QQQ", "IVV"]

def build_static_json():
    print("[*] Building static ETF overlap data...")
    holdings_cache = {}
    
    for ticker in WATCHLIST:
        try:
            print(f"Processing {ticker}...")
            df = fetch_etf_holdings(ticker)
            holdings_cache[ticker] = df.to_dict(orient="records")
        except Exception as e:
            print(f"[!] Skipping {ticker}: {e}")
            
    comparisons = {}
    tickers = list(holdings_cache.keys())
    
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            t1, t2 = tickers[i], tickers[j]
            if t1 not in holdings_cache or t2 not in holdings_cache:
                continue
                
            df_a = pd.DataFrame(holdings_cache[t1])
            df_b = pd.DataFrame(holdings_cache[t2])
            
            metrics = compute_pairwise_overlap(df_a, df_b, name_a=t1, name_b=t2)
            
            comparisons[f"{t1}_vs_{t2}"] = {
                "sum_of_min": float(metrics["sum_of_min"]),
                "directional_a_in_b": float(metrics["directional_a_in_b"]),
                "directional_b_in_a": float(metrics["directional_b_in_a"]),
                "shared_count": int(metrics["shared_count"]),
                "total_count_a": int(metrics["total_count_a"]),
                "total_count_b": int(metrics["total_count_b"]),
                "count_overlap_a": float(metrics["count_overlap_a"]),
                "count_overlap_b": float(metrics["count_overlap_b"]),
                "shared_holdings": metrics["shared_holdings_df"].to_dict(orient="records")
            }

    output = {
        "watchlist": list(holdings_cache.keys()),
        "comparisons": comparisons
    }
    
    with open("etf_data.json", "w") as f:
        json.dump(output, f, indent=2)
    print("[*] Generated etf_data.json successfully!")

if __name__ == "__main__":
    build_static_json()
