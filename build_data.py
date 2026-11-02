import os
import json
import pandas as pd
import math
import numpy as np
from src.fetcher import fetch_etf_holdings
from src.analyzer import compute_pairwise_overlap

WATCHLIST = ["VUG", "VOO", "SCHD", "QQQ", "SPMO"]

def clean_json(obj):
    """Convert NaN and Infinity to JSON-compatible null values."""
    if isinstance(obj, dict):
        return {k: clean_json(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [clean_json(v) for v in obj]

    if isinstance(obj, (float, np.floating)):
        return float(obj) if math.isfinite(float(obj)) else None

    if isinstance(obj, np.integer):
        return int(obj)

    return obj

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

    output = clean_json(output)

    with open("etf_data.json", "w") as f:
        json.dump(output, f, indent=2, allow_nan=False)
    
    print("[+] Successfully generated valid JSON.")

if __name__ == "__main__":
    build_static_json()
