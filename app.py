import streamlit as st
import pandas as pd
from src.fetcher import fetch_etf_holdings
from src.analyzer import compute_pairwise_overlap

st.set_page_config(page_title="Official ETF Overlap Analyzer", layout="wide")

st.title("📊 Institutional ETF Overlap Analyzer")
st.markdown("Analyze exact portfolio composition overlap using official monthly **SEC Form N-PORT** filings.")

# Sidebar Controls
st.sidebar.header("Portfolio Selection")
ticker_a = st.sidebar.text_input("First ETF Ticker", value="VUG").upper()
ticker_b = st.sidebar.text_input("Second ETF Ticker", value="VOO").upper()

if st.sidebar.button("Run Overlap Analysis"):
    with st.spinner(f"Querying SEC EDGAR N-PORT filings for {ticker_a} and {ticker_b}..."):
        try:
            df_a = fetch_etf_holdings(ticker_a)
            df_b = fetch_etf_holdings(ticker_b)
            
            metrics = compute_pairwise_overlap(df_a, df_b, name_a=ticker_a, name_b=ticker_b)
            
            # Display High-Level Summary Metrics
            st.subheader(f"Key Overlap Metrics: {ticker_a} vs {ticker_b}")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(label="Sum-of-Min Overlap (Symmetric)", value=f"{metrics['sum_of_min']:.2%}", 
                          help="Exact duplicated capital allocation percentage between both funds.")
            with col2:
                st.metric(label=f"Weight of {ticker_a} found in {ticker_b}", value=f"{metrics['directional_a_in_b']:.2%}")
            with col3:
                st.metric(label=f"Weight of {ticker_b} found in {ticker_a}", value=f"{metrics['directional_b_in_a']:.2%}")
                
            st.markdown("---")
            
            # Secondary Breakdown Metrics
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                st.write(f"**{ticker_a} Holdings Count:** {metrics['total_count_a']:,}")
                st.write(f"**{ticker_b} Holdings Count:** {metrics['total_count_b']:,}")
                st.write(f"**Shared Holdings Count:** {metrics['shared_count']:,}")
            with m_col2:
                st.write(f"**Count Overlap ({ticker_a}'s perspective):** {metrics['count_overlap_a']:.2%}")
                st.write(f"**Count Overlap ({ticker_b}'s perspective):** {metrics['count_overlap_b']:.2%}")

            # Detailed Table of Shared Constituents
            st.subheader("🔍 Shared Constituents Breakdown")
            shared_table = metrics["shared_holdings_df"]
            st.dataframe(shared_table, use_container_width=True)
            
        except Exception as e:
            st.error(f"An error occurred while processing the request: {e}")
else:
    st.info("👈 Enter two ETF tickers in the sidebar and click **Run Overlap Analysis** to begin.")
