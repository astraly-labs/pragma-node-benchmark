import streamlit as st
from price_collector import PriceCollector
from datetime import datetime
import time
from scipy import stats
import plotly.graph_objects as go

PUBLISHER_SIGNATURES = {
    "0x624ebfb99865079bd58cfcfb925b6f5ce940d6f6e41e118b8a72b7163fb435c": "Pragma",
    "0x04e2863fd0ff85803eef98ce5dd8272ab21c6595537269a2cd855a10ebcc18cc": "Fourleaf",
    "0x0279fde026e3e6cceacb9c263fece0c8d66a8f59e8448f3da5a1968976841c62": "Avnu",
    "0x009d84fae6d6a8eff16f7729e755a9084896352cae5d7f0518f43da98ff4d903": "Flowdesk"
}

st.set_page_config(
    page_title="Websocket Monitoring",
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
    
    fig.add_trace(go.Scatter(
        x=times,
        y=pragma_prices,
        name='Pragma',
        line=dict(color='green', width=2)
    ))
    
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


if 'collector' not in st.session_state:
    st.session_state.collector = PriceCollector()
    st.session_state.collector.start()
    print("Price collector initialized and started")  # Debug print

def main():
    st.title("Websocket Monitoring")
    
    # Header
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
    
    st.divider()
    
    # Body
    if history and len(history) > 0:
        latest = history[-1]
        
        # Pair selection
        if 'selected_pair' not in st.session_state:
            st.session_state.selected_pair = sorted(latest['pragma_prices'].keys())[0]
        
        available_pairs = sorted(latest['pragma_prices'].keys())
        selected_pair = st.selectbox(
            "Select Trading Pair",
            available_pairs,
            index=available_pairs.index(st.session_state.selected_pair)
        )
        st.session_state.selected_pair = selected_pair
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig = create_price_chart(history, selected_pair)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            metrics = print_price_update(latest, history)
            if metrics and selected_pair in metrics:
                pair_metrics = metrics[selected_pair]
                st.markdown(f"### Current Metrics for {selected_pair}")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric(f"Pragma:", f"${pair_metrics['Pragma']:,.2f}")
                with col2:
                    st.metric(f"Pyth:",f"${pair_metrics['Pyth']:,.2f}")
                
                col3,col4,col5 = st.columns(3)
                with col3:
                    st.metric(f"Delta:", f"{pair_metrics['Delta']:+.2f}%")
                with col4:
                    if pair_metrics['MSE'] is not None:
                        st.metric(f"MSE:", f"{pair_metrics['MSE']:.6f}")
                with col5:
                    if pair_metrics['Spearman'] is not None:
                        st.metric(f"Spearman:", f"{pair_metrics['Spearman']:.3f}")
            global_metrics = st.session_state.collector.get_latency_metrics()
            if global_metrics:
                st.markdown("### Websocket Metrics")
                col1, col2 = st.columns(2)
                empty_message_amount = st.session_state.collector.get_empty_message()
    
                with col1:
                    st.metric("Mean Latency", f"{global_metrics['mean']:.2f} ms")
                    st.metric("Q1 (25th percentile)", f"{global_metrics['q1']:.2f} ms")
                    st.metric("90th percentile", f"{global_metrics['p90']:.2f} ms")
                    st.metric("empty message", f"{empty_message_amount}")
                    
                with col2:
                    st.metric("Median Latency", f"{global_metrics['median']:.2f} ms")
                    st.metric("Q3 (75th percentile)", f"{global_metrics['q3']:.2f} ms")
                    st.metric("99th percentile", f"{global_metrics['p99']:.2f} ms")
                    st.metric("missed slot", f"{st.session_state.collector.calculate_missed_slots()['global']['ratio']:.2f}%")
                
                
        
        if st.checkbox("Show Raw Data"):
            st.markdown("### Raw Data")
            st.write("Latest data:", latest)
    else:
        st.write("Waiting for data...")
    time.sleep(10)
    print(st.session_state.collector.calculate_missed_slots())
    st.rerun()


if __name__ == "__main__":
    main()