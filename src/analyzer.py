import pandas as pd
import numpy as np

def compute_pairwise_overlap(df_a: pd.DataFrame, df_b: pd.DataFrame, name_a: str = "Fund A", name_b: str = "Fund B") -> dict:
    """
    Computes count overlap, directional weight overlap, and sum-of-min symmetric overlap.
    """
    # Merge on ticker identifier
    merged = pd.merge(
        df_a, df_b, 
        on="ticker", 
        how="outer", 
        suffixes=('_a', '_b')
    )
    
    merged['weight_a'] = merged['weight_a'].fillna(0.0)
    merged['weight_b'] = merged['weight_b'].fillna(0.0)
    
    # Resolve descriptive asset names
    merged['name'] = merged['name_a'].combine_first(merged['name_b'])
    
    # 1. Overlap by Count
    set_a = set(df_a['ticker'])
    set_b = set(df_b['ticker'])
    shared_tickers = set_a.intersection(set_b)
    
    count_overlap_a = len(shared_tickers) / len(set_a) if len(set_a) > 0 else 0
    count_overlap_b = len(shared_tickers) / len(set_b) if len(set_b) > 0 else 0
    
    # 2. Directional Weight Overlap
    # How much of Fund A's total weight is present in Fund B?
    directional_a_in_b = merged[merged['ticker'].isin(shared_tickers)]['weight_a'].sum()
    directional_b_in_a = merged[merged['ticker'].isin(shared_tickers)]['weight_b'].sum()
    
    # 3. Sum-of-Min Overlap (Symmetric 0 to 100% portfolio allocation duplication)
    merged['min_weight'] = np.minimum(merged['weight_a'], merged['weight_b'])
    sum_of_min = merged['min_weight'].sum()
    
    # Generate shared holdings breakdown table
    shared_df = merged[merged['ticker'].isin(shared_tickers)][['ticker', 'name', 'weight_a', 'weight_b']]
    shared_df = shared_df.rename(columns={'weight_a': f'Weight in {name_a}', 'weight_b': f'Weight in {name_b}'})
    shared_df['Overlap Allocation (Min)'] = np.minimum(shared_df[f'Weight in {name_a}'], shared_df[f'Weight in {name_b}'])
    shared_df = shared_df.sort_values(by=f'Weight in {name_a}', ascending=False)
    
    metrics = {
        "shared_count": len(shared_tickers),
        "total_count_a": len(set_a),
        "total_count_b": len(set_b),
        "count_overlap_a": count_overlap_a,
        "count_overlap_b": count_overlap_b,
        "directional_a_in_b": directional_a_in_b,
        "directional_b_in_a": directional_b_in_a,
        "sum_of_min": sum_of_min,
        "shared_holdings_df": shared_df
    }
    
    return metrics
