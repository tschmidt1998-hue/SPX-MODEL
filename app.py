import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, time

# Add src to path if needed (though typically running as python -m streamlit ... handles it, or relative imports)
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.connectors.polygon import PolygonClient
from src.connectors.ibkr import IBKRClient
from src.engine.greeks import DealerBook

st.set_page_config(page_title="Quant Research System", layout="wide")

st.title("Microstructure Dashboard")

# --- Sidebar ---
st.sidebar.header("Configuration")
api_status_container = st.sidebar.container()

# API Status
poly_client = PolygonClient()
ibkr_client = IBKRClient()

with api_status_container:
    st.subheader("API Status")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Polygon", "Connected" if poly_client.client else "Mock Mode")
    with col2:
        st.metric("IBKR", "Connected" if ibkr_client.connected else "Mock Mode")

# Date Picker
selected_date = st.sidebar.date_input("Select Date", datetime.now())

# --- Data Loading ---
@st.cache_data
def load_data(date_val):
    # Fetch Option Chain
    chain = poly_client.get_option_chain("SPX", date_str=str(date_val))
    
    # Get Spot Price (Mock or Fetch)
    spot_price = 4100.0 # Mock
    
    # Initialize Dealer Book
    book = DealerBook(chain, spot_price=spot_price)
    book.estimate_inventory()
    book.calculate_greeks()
    
    return book

try:
    book = load_data(selected_date)
    spot_price = book.spot_price
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# --- Main Panel A: The Landscape (GEX) ---
st.header("Panel A: The Landscape (GEX)")

gex_by_strike = book.get_gex_by_strike()
gamma_flip = book.find_gamma_flip_strike()

# Create DataFrame for Plotly
gex_df = gex_by_strike.reset_index()
gex_df.columns = ['Strike', 'GEX']

# Color logic: Highlight Gamma Flip
colors = ['red' if s == gamma_flip else 'blue' for s in gex_df['Strike']]
if gamma_flip:
    # Maybe highlight the bar closest to flip?
    # Or just use a vertical line.
    pass

fig_gex = px.bar(gex_df, x='Strike', y='GEX', title=f"Net GEX by Strike (Flip: {gamma_flip})")
fig_gex.update_traces(marker_color='blue')

if gamma_flip:
    fig_gex.add_vline(x=gamma_flip, line_width=3, line_dash="dash", line_color="red", annotation_text="Gamma Flip")

st.plotly_chart(fig_gex, use_container_width=True)

# --- Main Panel B: The Clock (Intraday) ---
st.header("Panel B: The Clock")

col_b1, col_b2 = st.columns([3, 1])

with col_b1:
    # Mock Intraday Data
    times = pd.date_range(start="09:30", end="16:00", freq="1min")
    n_points = len(times)
    
    # Actual Price (Random Walk)
    actual_price = spot_price + np.random.randn(n_points).cumsum()
    
    # Theoretical Hedging Vector (Ghost Line)
    # Assume Charm Drift causes a bias
    net_charm = book.data['net_charm'].sum() if 'net_charm' in book.data else 0
    # Charm implies delta change per day. 
    # Hedging flow = - Delta Change.
    # If Delta decreases (Charm negative), Dealer buys back?
    # Let's mock a drift component
    charm_drift = np.linspace(0, net_charm * 0.01, n_points) # Arbitrary scaling
    theoretical_price = actual_price + charm_drift 
    
    df_clock = pd.DataFrame({
        'Time': times,
        'Actual Price': actual_price,
        'Theoretical (Charm Adj)': theoretical_price
    })
    
    fig_clock = px.line(df_clock, x='Time', y=['Actual Price', 'Theoretical (Charm Adj)'], 
                        title="Price vs Theoretical Hedging Vector")
    st.plotly_chart(fig_clock, use_container_width=True)

with col_b2:
    st.metric("Net GEX ($B)", f"{book.get_total_gex()/1e9:.2f}")
    st.metric("Net Charm", f"{net_charm:.2f}")
    st.metric("Gamma Flip", f"{gamma_flip}")


# --- Main Panel C: Systematic ---
st.header("Panel C: Systematic Indicators")

col_c1, col_c2, col_c3 = st.columns(3)

with col_c1:
    # Vol Control Exposure
    # Mock: Inverse of VIX (IV)
    avg_iv = book.data['iv'].mean()
    vol_exposure = 1.0 / avg_iv if avg_iv > 0 else 0
    st.metric("Vol-Control Exposure", f"{vol_exposure:.2f}%")
    st.progress(min(vol_exposure, 1.0))

with col_c2:
    # CTA Stop Loss
    # Mock: Some moving average level
    stop_loss_level = spot_price * 0.95
    st.metric("CTA Stop-Loss Level", f"{stop_loss_level:.0f}")
    st.metric("Distance to Stop", f"{(spot_price - stop_loss_level):.0f} pts")

with col_c3:
    # Regime
    regime = "Long Gamma" if spot_price > (gamma_flip or 0) else "Short Gamma"
    st.metric("Current Regime", regime, delta_color="normal" if regime == "Long Gamma" else "inverse")

st.markdown("---")
st.caption("Quant Research System v0.1.0")
