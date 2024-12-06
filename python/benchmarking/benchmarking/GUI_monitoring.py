import streamlit as st
from price_collector import PriceCollector
from datetime import datetime
import time
from scipy import stats
import plotly.graph_objects as go

CURRENT_ENV = 'local'

PUBLISHER_SIGNATURES = {
    "0x624EBFB99865079BD58CFCFB925B6F5CE940D6F6E41E118B8A72B7163FB435C": "Pragma",
    "0x04e2863fd0ff85803eef98ce5dd8272ab21c6595537269a2cd855a10ebcc18cc": "Fourleaf",
    "0x0279fde026e3e6cceacb9c263fece0c8d66a8f59e8448f3da5a1968976841c62": "Avnu",
    "0x009d84fae6d6a8eff16f7729e755a9084896352cae5d7f0518f43da98ff4d903": "Flowdesk"
}


COLOR_PER_PUBLISHER = {
    "Pragma" : 'yellow',
    "Fourleaf" : 'orange',
    "Avnu" : 'blue',
    "Flowdesk" : 'white'
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
    publisher_prices = {}
    pyth_prices = []
    stork_prices = []
    
    for entry in history:
        times.append(datetime.fromtimestamp(entry['timestamp']))
        pragma_price = entry['pragma_prices'].get(selected_pair)
        pragma_prices.append(pragma_price["price"])
        for price_by_src in pragma_price["component"]:
            if PUBLISHER_SIGNATURES[price_by_src] not in publisher_prices:
                publisher_prices[PUBLISHER_SIGNATURES[price_by_src]] = []
            publisher_prices[PUBLISHER_SIGNATURES[price_by_src]].append(pragma_price["component"][price_by_src])

        pyth_prices.append(entry['pyth_prices'].get(selected_pair))
        stork_prices.append(entry['stork_prices'].get(selected_pair))

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

    fig.add_trace(go.Scatter(
        x=times,
        y=stork_prices,
        name='Stork',
        line=dict(color='purple', width=2)
    ))

    for source in publisher_prices:
        fig.add_trace(go.Scatter(
            x=times,
            y=publisher_prices[source],
            name=source,
            line=dict(color=COLOR_PER_PUBLISHER[source], width=2)
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
    stork_prices = []
    
    for entry in price_history:
        pragma_data = entry['pragma_prices'].get(pair)
        if pragma_data and isinstance(pragma_data, dict) and "price" in pragma_data:
            pragma_price = pragma_data.get('price')
        else:
            continue  # Skip if no valid pragma price
            
        pyth_price = entry['pyth_prices'].get(pair)
        stork_price = entry['stork_prices'].get(pair)
        
        if pragma_price is not None:
            # Only append prices when we have matching pairs
            if pyth_price is not None:
                pragma_prices.append(pragma_price)
                pyth_prices.append(pyth_price)
            if stork_price is not None:
                if len(pragma_prices) < len(pyth_prices):
                    pragma_prices.append(pragma_price)
                stork_prices.append(stork_price)
    
    metrics = {}
    
    # Calculate Pyth metrics
    if len(pragma_prices) > 1 and len(pyth_prices) > 1:
        pyth_mse = sum([(p1 - p2) ** 2 for p1, p2 in zip(pragma_prices[:len(pyth_prices)], pyth_prices)]) / len(pyth_prices)
        if len(set(pragma_prices[:len(pyth_prices)])) > 1 and len(set(pyth_prices)) > 1:
            pyth_correlation, _ = stats.spearmanr(pragma_prices[:len(pyth_prices)], pyth_prices)
        else:
            pyth_correlation = None
        metrics['pyth'] = {'mse': pyth_mse, 'correlation': pyth_correlation}
    
    # Calculate Stork metrics
    if len(pragma_prices) > 1 and len(stork_prices) > 1:
        min_len = min(len(pragma_prices), len(stork_prices))
        stork_mse = sum([(p1 - p2) ** 2 for p1, p2 in zip(pragma_prices[:min_len], stork_prices[:min_len])]) / min_len
        if len(set(pragma_prices[:min_len])) > 1 and len(set(stork_prices[:min_len])) > 1:
            stork_correlation, _ = stats.spearmanr(pragma_prices[:min_len], stork_prices[:min_len])
        else:
            stork_correlation = None
        metrics['stork'] = {'mse': stork_mse, 'correlation': stork_correlation}
    
    return metrics

def print_price_update(price_entry, price_history):
    if not price_entry:
        return
    data_per_pair = {}
    
    pragma_prices = price_entry.get('pragma_prices', {})
    pyth_prices = price_entry.get('pyth_prices', {})
    stork_prices = price_entry.get('stork_prices', {})
    
    for pair in sorted(pragma_prices.keys()):
        pragma_data = pragma_prices[pair]
        if isinstance(pragma_data, dict) and "price" in pragma_data:
            pragma_price = pragma_data["price"]
        else:
            pragma_price = pragma_data
            
        pyth_price = pyth_prices.get(pair)
        stork_price = stork_prices.get(pair)
        
        metrics = calculate_metrics(price_history, pair)
        
        data_per_pair[pair] = {
            "Pragma": pragma_price,
            "Pyth": pyth_price,
            "Stork": stork_price
        }
        
        if metrics.get('pyth'):
            data_per_pair[pair].update({
                "Pyth_MSE": metrics['pyth']['mse'],
                "Pyth_Correlation": metrics['pyth']['correlation']
            })
        
        if metrics.get('stork'):
            data_per_pair[pair].update({
                "Stork_MSE": metrics['stork']['mse'],
                "Stork_Correlation": metrics['stork']['correlation']
            })
    
    return data_per_pair


if 'collector' not in st.session_state:
    st.session_state.collector = PriceCollector(env=CURRENT_ENV)
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
            metrics = calculate_metrics(history, selected_pair)
            if metrics:
                st.markdown(f"### Current Metrics for {selected_pair}")
                
                latest_pragma = latest['pragma_prices'][selected_pair]["price"]
                latest_pyth = latest['pyth_prices'].get(selected_pair)
                latest_stork = latest['stork_prices'].get(selected_pair)
                
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("#### Pragma")
                    st.markdown(f"<h2>${latest_pragma:,.2f}</h2>", unsafe_allow_html=True)

                with col2:
                    st.markdown("#### Pyth")
                    if latest_pyth:
                        pyth_delta = ((latest_pyth - latest_pragma) * 100) / latest_pragma
                        st.markdown(f"<h2>${latest_pyth:,.2f}</h2>", unsafe_allow_html=True)
                        st.markdown(f"<p style='color: {'red' if pyth_delta < 0 else 'green'}'>{pyth_delta:+.2f}%</p>", unsafe_allow_html=True)
                    else:
                        st.markdown("No data")

                with col3:
                    st.markdown("#### Stork")
                    if latest_stork:
                        stork_delta = ((latest_stork - latest_pragma) * 100) / latest_pragma
                        st.markdown(f"<h2>${latest_stork:,.2f}</h2>", unsafe_allow_html=True)
                        st.markdown(f"<p style='color: {'red' if stork_delta < 0 else 'green'}'>{stork_delta:+.2f}%</p>", unsafe_allow_html=True)
                    else:
                        st.markdown("No data")
                
                st.divider()
                st.markdown("### Statistical Metrics")
                
                col1, col2 = st.columns(2)
                with col1:
                    if 'pyth' in metrics:
                        st.metric("Pyth MSE", f"{metrics['pyth']['mse']:.6f}")
                        if metrics['pyth']['correlation'] is not None:
                            st.metric("Pyth Correlation", f"{metrics['pyth']['correlation']:.3f}")
                        else:
                            st.metric("Pyth Correlation", "N/A")
                with col2:
                    if 'stork' in metrics:
                        st.metric("Stork MSE", f"{metrics['stork']['mse']:.6f}")
                        if metrics['stork']['correlation'] is not None:
                            st.metric("Stork Correlation", f"{metrics['stork']['correlation']:.3f}")
                        else:
                            st.metric("Stork Correlation", "N/A")
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