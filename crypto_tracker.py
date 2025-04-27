import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
import time

# Set page config
st.set_page_config(
    page_title="Crypto Price Tracker",
    page_icon="📈",
    layout="wide"
)

# App title and description
st.title("Cryptocurrency Price Tracker")
st.markdown("Track live prices and historical returns for cryptocurrencies")

# Function to get cryptocurrency data from CoinGecko API
@st.cache_data(ttl=300)  # Cache data for 5 minutes
def get_crypto_data(crypto_ids):
    url = f"https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'ids': ','.join(crypto_ids),
        'order': 'market_cap_desc',
        'per_page': 100,
        'page': 1,
        'sparkline': False,
        'price_change_percentage': '1h,24h,7d,30d'
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error fetching data: {response.status_code}")
        return []

# Function to get historical data for a specific coin
@st.cache_data(ttl=3600)  # Cache data for 1 hour
def get_historical_data(crypto_id, days):
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart"
    params = {
        'vs_currency': 'usd',
        'days': days,
        'interval': 'daily' if days > 1 else 'hourly'
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error fetching historical data: {response.status_code}")
        return {'prices': []}

# Available cryptocurrencies
available_cryptos = {
    'bitcoin': 'Bitcoin (BTC)',
    'ethereum': 'Ethereum (ETH)',
    'binancecoin': 'Binance Coin (BNB)',
    'ripple': 'XRP (XRP)',
    'cardano': 'Cardano (ADA)',
    'solana': 'Solana (SOL)',
    'polkadot': 'Polkadot (DOT)',
    'dogecoin': 'Dogecoin (DOGE)',
    'avalanche-2': 'Avalanche (AVAX)',
    'chainlink': 'Chainlink (LINK)'
}

# Sidebar for cryptocurrency selection
st.sidebar.title("Settings")
selected_cryptos = st.sidebar.multiselect(
    "Select cryptocurrencies to track",
    options=list(available_cryptos.keys()),
    default=['bitcoin', 'ethereum', 'solana'],
    format_func=lambda x: available_cryptos[x]
)

# Refresh interval
refresh_interval = st.sidebar.slider(
    "Auto-refresh interval (seconds)",
    min_value=30,
    max_value=300,
    value=60,
    step=30
)

# Auto-refresh checkbox
auto_refresh = st.sidebar.checkbox("Enable auto-refresh", value=True)

# Manual refresh button
if st.sidebar.button("Refresh Data Now"):
    st.experimental_rerun()

# Check if any cryptocurrencies are selected
if not selected_cryptos:
    st.warning("Please select at least one cryptocurrency from the sidebar.")
    st.stop()

# Get current data for selected cryptocurrencies
crypto_data = get_crypto_data(selected_cryptos)

# Create a DataFrame for current prices and returns
if crypto_data:
    df = pd.DataFrame(crypto_data)
    df = df[['id', 'name', 'symbol', 'current_price', 'price_change_percentage_24h', 
             'price_change_percentage_7d_in_currency', 'price_change_percentage_30d_in_currency',
             'market_cap', 'total_volume']]
    
    # Rename columns for clarity
    df.columns = ['ID', 'Name', 'Symbol', 'Current Price (USD)', '24h Change (%)', 
                  '7d Change (%)', '30d Change (%)', 'Market Cap (USD)', 'Volume (USD)']
    
    # Format the DataFrame
    df['Current Price (USD)'] = df['Current Price (USD)'].apply(lambda x: f"${x:,.2f}")
    df['Market Cap (USD)'] = df['Market Cap (USD)'].apply(lambda x: f"${x:,.0f}")
    df['Volume (USD)'] = df['Volume (USD)'].apply(lambda x: f"${x:,.0f}")
    
    # Create a function to format percentage cells with colors
    def color_percent(val):
        try:
            val = float(val)
            color = 'green' if val >= 0 else 'red'
            return f'color: {color}'
        except:
            return ''
    
    # Display current prices and returns in a table
    st.subheader("Current Prices and Returns")
    
    # Apply styling to the DataFrame
    styled_df = df.style.applymap(color_percent, subset=['24h Change (%)', '7d Change (%)', '30d Change (%)'])
    st.dataframe(styled_df, use_container_width=True)
    
    # Display individual cryptocurrency details
    st.subheader("Detailed Analysis")
    
    # Create tabs for each selected cryptocurrency
    tabs = st.tabs([available_cryptos[crypto] for crypto in selected_cryptos])
    
    for i, crypto_id in enumerate(selected_cryptos):
        with tabs[i]:
            col1, col2 = st.columns([1, 2])
            
            # Get the current crypto data
            crypto = next((c for c in crypto_data if c['id'] == crypto_id), None)
            
            if crypto:
                with col1:
                    st.image(crypto['image'], width=64)
                    st.metric(
                        label=f"{crypto['name']} ({crypto['symbol'].upper()})",
                        value=f"${crypto['current_price']:,.2f}",
                        delta=f"{crypto['price_change_percentage_24h']:.2f}%"
                    )
                    
                    st.markdown("### Returns")
                    returns_data = {
                        "Period": ["24 Hours", "7 Days", "30 Days"],
                        "Return (%)": [
                            crypto['price_change_percentage_24h'],
                            crypto['price_change_percentage_7d_in_currency'],
                            crypto['price_change_percentage_30d_in_currency']
                        ]
                    }
                    returns_df = pd.DataFrame(returns_data)
                    
                    # Create a bar chart for returns
                    fig = px.bar(
                        returns_df,
                        x="Period",
                        y="Return (%)",
                        color="Return (%)",
                        color_continuous_scale=["red", "green"],
                        range_color=[-max(abs(returns_df["Return (%)"])), max(abs(returns_df["Return (%)"]))],
                        text="Return (%)"
                    )
                    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
                    fig.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Get historical data for price chart
                    hist_data = get_historical_data(crypto_id, 30)
                    
                    if hist_data and 'prices' in hist_data:
                        # Create DataFrame from historical data
                        hist_df = pd.DataFrame(hist_data['prices'], columns=['timestamp', 'price'])
                        hist_df['date'] = pd.to_datetime(hist_df['timestamp'], unit='ms')
                        
                        # Create price chart
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=hist_df['date'],
                            y=hist_df['price'],
                            mode='lines',
                            name=crypto['name'],
                            line=dict(color='royalblue', width=2)
                        ))
                        
                        # Add range selector buttons
                        fig.update_layout(
                            title=f"{crypto['name']} Price (Last 30 Days)",
                            xaxis=dict(
                                rangeselector=dict(
                                    buttons=list([
                                        dict(count=1, label="1d", step="day", stepmode="backward"),
                                        dict(count=7, label="1w", step="day", stepmode="backward"),
                                        dict(count=1, label="1m", step="month", stepmode="backward"),
                                        dict(step="all")
                                    ])
                                ),
                                rangeslider=dict(visible=True),
                                type="date"
                            ),
                            yaxis=dict(title="Price (USD)"),
                            height=400
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.error("Could not load historical data for this cryptocurrency.")

# Add auto-refresh functionality
if auto_refresh:
    st.markdown(f"<small>Data will refresh every {refresh_interval} seconds. Last updated: {datetime.now().strftime('%H:%M:%S')}</small>", unsafe_allow_html=True)
    time.sleep(refresh_interval)
    st.experimental_rerun()