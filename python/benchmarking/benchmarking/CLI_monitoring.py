import time
from queue import Empty
from price_collector import PriceCollector
from scipy import stats

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
            
            print(f"{pair} => Pragma: ${pragma_price:,.2f}, Pyth: ${pyth_price:,.2f}, Delta: {delta:+.2f}%{metrics_str}")
        else:
            print(f"{pair} => Pragma: ${pragma_price:,.2f}, Pyth: No data, Delta: Cannot calculate")


def main():
    collector = PriceCollector()
    collector.start()
    
    try:
        while True:
            try:
                new_price_entry = collector.update_queue.get(timeout=1)
                if new_price_entry:
                    print_price_update(new_price_entry, collector.get_history())
                    print(f"\nTotal entries in history: {len(collector.get_history())}")
                
            except Empty:
                continue
            except Exception as e:
                print(f"Unexpected error in main loop: {e}")
                
    except KeyboardInterrupt:
        print("\nStopping price collector...")
        collector.stop()
        print("Program terminated")

if __name__ == "__main__":
    main()