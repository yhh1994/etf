import os
import pandas as pd
from edgar import set_identity, Company

# SEC identity
set_identity(os.getenv(
    "EDGAR_IDENTITY",
    "ETFOverlapAnalyst research@example.com"
))

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_etf_holdings(ticker: str) -> pd.DataFrame:
    """
    Fetches the latest official SEC Form N-PORT filing for a given ETF ticker 
    and returns a standardized DataFrame containing holdings, tickers, and weights.
    """
    cache_file = os.path.join(DATA_DIR, f"{ticker.upper()}_holdings.parquet")
    
    try:
        print(f"[*] Fetching SEC N-PORT data for {ticker.upper()}...")
        company = Company(ticker)
        filings = company.get_filings(form="NPORT-P")
        
        if not filings:
            raise ValueError(f"No N-PORT filings found for {ticker}")
            
        # Parse the most recent filing object
        latest_filing = filings[0]
        fund_obj = latest_filing.obj()
        
        # Extract holdings dataframe via edgartools helper
        df = fund_obj.investment_data()
        
        # Standardize columns required for overlap analysis
        # Expected columns from edgartools: name, ticker, value_usd, pct_value
        standard_cols = {}
        for col in df.columns:
            if 'ticker' in col.lower():
                standard_cols[col] = 'ticker'
            elif 'name' in col.lower():
                standard_cols[col] = 'name'
            elif 'pct' in col.lower() or 'weight' in col.lower():
                standard_cols[col] = 'weight'
            elif 'value' in col.lower():
                standard_cols[col] = 'value'
                
        df = df.rename(columns=standard_cols)
        
        # Clean and coerce types
        if 'ticker' not in df.columns:
            df['ticker'] = df['name'] # Fallback identifier if ticker is missing
            
        df['weight'] = pd.to_numeric(df['weight'], errors='coerce').fillna(0.0)
        
        # Normalization check: N-PORT weights are occasionally stored as fractions or raw percentages
        if df['weight'].sum() > 2.0: 
            df['weight'] = df['weight'] / 100.0
            
        # Select and save subset
        clean_df = df[['ticker', 'name', 'weight']].copy()
        clean_df.to_parquet(cache_file)
        return clean_df

    except Exception as e:
        print(f"[!] Error pulling via EDGAR for {ticker}: {e}. Checking local cache...")
        if os.path.exists(cache_file):
            return pd.read_parquet(cache_file)
        raise RuntimeError(f"Could not retrieve holdings for {ticker} from SEC or cache.") from e
