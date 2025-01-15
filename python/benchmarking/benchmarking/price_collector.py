import json
import asyncio
import websockets
import time
import threading
from queue import Queue
from pyth_fetcher import retrieve_pyth_prices
from stork_fetcher import retrieve_stork_prices
import numpy as np

# Environment configurations
ENVIRONMENTS = {
    'local': 'ws://localhost:3000/node/v1/data/subscribe',
    'dev': 'wss://ws.dev.pragma.build/node/v1/data/subscribe',
    'prod': 'wss://ws.pragma.build/node/v1/data/subscribe'
}

DEFAULT_PAIRS = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'BNB/USD']

class PriceCollector:
    def __init__(self, env='local'):
        self.running = False
        self.price_history = []
        self.update_history = []
        self.empty_message_count = 0
        self.lock = asyncio.Lock()
        self.update_queue = Queue()
        self.websocket_url = ENVIRONMENTS[env]
        self.subscription_message = {"msg_type": "subscribe", "pairs": DEFAULT_PAIRS}
        
        # Store latest prices from each source
        self.latest_prices = {
            'pragma': {},
            'pyth': {},
            'stork': {},
            'timestamp': None
        }

    def decode_short_string(self, felt: str) -> str:
        try:
            felt_int = int(felt, 16) if felt.startswith('0x') else int(felt)
            bytes_str = felt_int.to_bytes((felt_int.bit_length() + 7) // 8, byteorder='big')
            return bytes_str.decode('ascii')
        except Exception as e:
            return None

    def format_price(self, price_str: str) -> float:
        try:
            price_length = len(price_str)
            whole_part = price_str[:price_length - 8]
            decimal_part = price_str[price_length - 8:]
            return float(f"{whole_part}.{decimal_part}")
        except Exception as e:
            return None

    async def fetch_pyth_prices(self):
        while self.running:
            try:
                prices = await retrieve_pyth_prices()
                if prices:
                    async with self.lock:
                        self.latest_prices['pyth'] = prices
                        self.latest_prices['timestamp'] = time.time()
                        self._update_price_history()
            except Exception as e:
                print(f"Error fetching Pyth prices: {e}")
            await asyncio.sleep(1)  # Adjust rate limiting as needed

    async def fetch_stork_prices(self):
        while self.running:
            try:
                prices = await retrieve_stork_prices()
                if prices:
                    async with self.lock:
                        self.latest_prices['stork'] = prices
                        self.latest_prices['timestamp'] = time.time()
                        self._update_price_history()
            except Exception as e:
                print(f"Error fetching Stork prices: {e}")
            await asyncio.sleep(1)  # Adjust rate limiting as needed

    async def fetch_pragma_prices(self):
        while self.running:
            try:
                async with websockets.connect(self.websocket_url) as websocket:
                    print(f"WebSocket connection established to {self.websocket_url}")
                    await websocket.send(json.dumps(self.subscription_message))
                    
                    while self.running:
                        message = await websocket.recv()
                        self.update_history.append(time.time())
                        try:
                            parsed_data = json.loads(message)
                            print("\n=== Raw Message ===")
                            print(json.dumps(parsed_data, indent=2))
                            if 'oracle_prices' not in parsed_data:
                                self.empty_message_count += 1
                                continue

                            prices = {}
                            for price_data in parsed_data['oracle_prices']:
                                pair = self.decode_short_string(price_data['global_asset_id'])
                                print(f"\nProcessing pair: {pair}")
                                print(f"Price data: {json.dumps(price_data, indent=2)}")
                                if not pair:
                                    # use previous price
                                    prices[pair] = self.latest_prices['pragma'][pair]
                                    continue
                                
                                price_value = self.format_price(price_data['median_price'])
                                if price_value is None:  # Skip if price is None
                                    # use previous price
                                    prices[pair] = self.latest_prices['pragma'][pair]
                                    continue
                                
                                component_prices = {}
                                print("\nLooking for component prices...")
                                print(f"Available fields: {price_data.keys()}")
                                for cmp in price_data.get('signed_prices', []):
                                    print(f"Processing component: {cmp}")
                                    comp_price = self.format_price(cmp["oracle_price"])
                                    if comp_price is not None:  # Only add valid component prices
                                        component_prices[cmp["signing_key"]] = comp_price
                                
                                print(f"Collected component prices: {component_prices}")
                                prices[pair] = {
                                    "price": price_value,
                                    "component": component_prices
                                }

                            if len(prices.keys()) > 0:  # Only update if we have prices
                                async with self.lock:
                                    self.latest_prices['pragma'] = prices
                                    self.latest_prices['timestamp'] = time.time()
                                    self._update_price_history()

                        except Exception as e:
                            print(f"Error processing Pragma message: {e}")

            except Exception as e:
                print(f"WebSocket error: {e}")
                await asyncio.sleep(5)

    def _update_price_history(self):
        """Create a new price entry from latest prices and add to history"""
        # Only update if we have pragma prices (our primary source)
        if not self.latest_prices['pragma']:
            return

        price_entry = {
            'timestamp': self.latest_prices['timestamp'] or time.time(),
            'pragma_prices': self.latest_prices['pragma'].copy(),
            'pyth_prices': self.latest_prices['pyth'].copy(),
            'stork_prices': self.latest_prices['stork'].copy()
        }
        
        self.price_history.append(price_entry)
        self.update_queue.put(price_entry)

    async def run_all_fetchers(self):
        """Run all price fetchers concurrently"""
        await asyncio.gather(
            self.fetch_pragma_prices(),
            self.fetch_pyth_prices(),
            self.fetch_stork_prices()
        )

    def run_async_loop(self):
        asyncio.run(self.run_all_fetchers())

    def start(self):
        """Start the price collector in a separate thread"""
        if not self.running:
            self.running = True
            self.collector_thread = threading.Thread(target=self.run_async_loop)
            self.collector_thread.daemon = True
            self.collector_thread.start()

    def stop(self):
        if self.running:
            self.running = False
            if self.collector_thread:
                self.collector_thread.join()
            print("Price collector stopped")

    def get_history(self):
        """Thread-safe way to get price history"""
        return self.price_history.copy() if self.price_history else []
    
    def get_empty_message(self):
        return self.empty_message_count
        
    def get_latency_metrics(self):
        timestamps = self.update_history.copy()
        
        if len(timestamps) < 2:
            return None
        
        latency = np.diff(timestamps) * 1000
        
        metrics = {
            'mean': np.mean(latency),
            'median': np.median(latency),
            'q1': np.percentile(latency, 25),
            'q3': np.percentile(latency, 75),
            'p90': np.percentile(latency, 90),
            'p99': np.percentile(latency, 99)
        }
        
        return metrics
    
    def calculate_missed_slots(self):
        history = self.price_history.copy()

        if len(history) < 2:
            return None

        total_slots = len(history) - 1
        missed_per_pair = {}
        global_missed = 0

        pairs = history[0]['pragma_prices'].keys()

        for pair in pairs:
            missed_per_pair[pair] = 0

        for i in range(1, len(history)):
            prev = history[i-1]['pragma_prices']
            curr = history[i]['pragma_prices']
            
            for pair in pairs:
                if pair in prev and pair in curr:
                    if prev[pair] == curr[pair]:
                        missed_per_pair[pair] += 1
            
            all_unchanged = True
            for pair in pairs:
                if pair in prev and pair in curr:
                    if prev[pair] != curr[pair]:
                        all_unchanged = False
                        break
            if all_unchanged:
                global_missed += 1

        ratios = {
            'per_pair': {
                pair: {
                    'missed': missed,
                    'total': total_slots,
                    'ratio': (missed / total_slots) * 100 if total_slots > 0 else 0
                }
                for pair, missed in missed_per_pair.items()
            },
            'global': {
                'missed': global_missed,
                'total': total_slots,
                'ratio': (global_missed / total_slots) * 100 if total_slots > 0 else 0
            }
        }

        return ratios

def main():
    collector = PriceCollector('local')
    print("Starting price collector...")
    try:
        collector.start()
        print("Price collector started successfully")
        print("Press Ctrl+C to stop")
        while True:
            time.sleep(1)
            history = collector.get_history()
            if history:
                latest = history[-1]
                print(latest)
    except KeyboardInterrupt:
        collector.stop()
        print("\nStopped price collection")
        print("Final price history length:", len(collector.get_history()))

if __name__ == "__main__":
    main()

