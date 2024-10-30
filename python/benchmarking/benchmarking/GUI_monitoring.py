import streamlit as st
from price_collector import PriceCollector
from datetime import datetime
import time
from scipy import stats
import plotly.graph_objects as go

# Configure the page
st.set_page_config(
    page_title="Crypto Price Monitor",
    page_icon="📈",
    layout="wide"
)

def create_price_chart(history, selected_pair):
    """Create price comparison chart for selected pair"""
    times = []
    pragma_prices = []
    pyth_prices = []
    
    for entry in history:
        times.append(datetime.fromtimestamp(entry['timestamp']))
        pragma_prices.append(entry['pragma_prices'].get(selected_pair))
        pyth_prices.append(entry['pyth_prices'].get(selected_pair))

    fig = go.Figure()
    
    # Add Pragma prices
    fig.add_trace(go.Scatter(
        x=times,
        y=pragma_prices,
        name='Pragma',
        line=dict(color='green', width=2)
    ))
    
    # Add Pyth prices
    fig.add_trace(go.Scatter(
        x=times,
        y=pyth_prices,
        name='Pyth',
        line=dict(color='red', width=2)
    ))
    
    fig.update_layout(
        title=f'{selected_pair} Price Comparison',
        xaxis_title='Time',
        yaxis_title='Price (USD)',
        height=500,
        template='plotly_dark',
        hovermode='x unified'
    )
    
    return fig

def calculate_metrics(price_history, pair):
    """Calculate Spearman correlation and MSE for a specific pair"""
    pragma_prices = []
    pyth_prices = []
    for entry in price_history:
        pragma_price = entry['pragma_prices'].get(pair)
        pyth_price = entry['pyth_prices'].get(pair)
        
        if pragma_price and pyth_price:
            pragma_prices.append(pragma_price)
            pyth_prices.append(pyth_price)
    
    # Calculate MSE
    mse = None
    if pragma_prices and pyth_prices:
        squared_diff = [(p1 - p2) ** 2 for p1, p2 in zip(pragma_prices, pyth_prices)]
        mse = sum(squared_diff) / len(squared_diff)
    
    # Calculate Spearman
    correlation = None
    p_value = None
    if len(pragma_prices) > 1:
        if len(set(pragma_prices)) > 1 and len(set(pyth_prices)) > 1:
            correlation, p_value = stats.spearmanr(pragma_prices, pyth_prices)
    
    return correlation, p_value, mse, len(pragma_prices)

def print_price_update(price_entry, price_history):
    if not price_entry:
        return
    data_per_pair = {}
        
    print("\nNew price update:")
    print(f"Timestamp: {time.ctime(price_entry['timestamp'])}")
    
    pragma_prices = price_entry.get('pragma_prices', {})
    pyth_prices = price_entry.get('pyth_prices', {})
    
    for pair in sorted(pragma_prices.keys()):
        pragma_price = pragma_prices[pair]
        pyth_price = pyth_prices.get(pair)
        
        correlation, p_value, mse, n = calculate_metrics(price_history, pair)
        
        if pyth_price:
            delta = ((pragma_price - pyth_price) * 100) / pragma_price
            metrics = []
            if correlation is not None:
                metrics.append(f"Spearman: {correlation:.3f}")
            if mse is not None:
                metrics.append(f"MSE: {mse:.6f}")
            metrics_str = f", {', '.join(metrics)}" if metrics else ""
            print(pair)
            print(f"{pair} => Pragma: ${pragma_price:,.2f}, Pyth: ${pyth_price:,.2f}, Delta: {delta:+.2f}%{metrics_str}")
            data_per_pair[pair] = {"Pragma": pragma_price, "Pyth": pyth_price, "Delta" : delta, "MSE" : mse, "Spearman": correlation }
        else:
            print(f"{pair} => Pragma: ${pragma_price:,.2f}, Pyth: No data, Delta: Cannot calculate")
    return data_per_pair

# Initialize the collector in session state if it doesn't exist
if 'collector' not in st.session_state:
    st.session_state.collector = PriceCollector()
    st.session_state.collector.start()
    print("Price collector initialized and started")  # Debug print

def main():
    st.title("Real-time Crypto Price Monitor")
    
    # Create header row with refresh button and status
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button('🔄 Refresh Data'):
            print("\nRefreshing data...")
            st.rerun()
    with col2:
        st.write("Status: Running" if st.session_state.collector.running else "Status: Stopped")
    with col3:
        history = st.session_state.collector.get_history()
        st.write(f"History entries: {len(history)}")
    
    # Add separator
    st.divider()
    
    # Rest of the app
    if history and len(history) > 0:
        latest = history[-1]
        
        # Pair selection
        # Add this near the beginning of your if history block, before the selectbox
        if 'selected_pair' not in st.session_state:
            st.session_state.selected_pair = sorted(latest['pragma_prices'].keys())[0]
        
        available_pairs = sorted(latest['pragma_prices'].keys())
        selected_pair = st.selectbox(
            "Select Trading Pair",
            available_pairs,
            index=available_pairs.index(st.session_state.selected_pair)
        )
        st.session_state.selected_pair = selected_pair
        
        # Create two columns for layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Display price chart
            fig = create_price_chart(history, selected_pair)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Display metrics for selected pair
            metrics = print_price_update(latest, history)
            if metrics and selected_pair in metrics:
                pair_metrics = metrics[selected_pair]
                st.markdown(f"### Current Metrics for {selected_pair}")
                st.write(f"Pragma: ${pair_metrics['Pragma']:,.2f}")
                st.write(f"Pyth: ${pair_metrics['Pyth']:,.2f}")
                st.write(f"Delta: {pair_metrics['Delta']:+.2f}%")
                if pair_metrics['MSE'] is not None:
                    st.write(f"MSE: {pair_metrics['MSE']:.6f}")
                if pair_metrics['Spearman'] is not None:
                    st.write(f"Spearman: {pair_metrics['Spearman']:.3f}")
        
        # Display full data at the bottom if needed
        if st.checkbox("Show Raw Data"):
            st.markdown("### Raw Data")
            st.write("Latest data:", latest)
    else:
        st.write("Waiting for data...")
    time.sleep(10)
    st.rerun()


if __name__ == "__main__":
    main()