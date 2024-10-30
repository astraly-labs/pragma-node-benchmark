import json
import asyncio
import websockets
import time
import threading
from queue import Queue, Empty
from typing import Dict, List
from pyth import retrieve_pyth_prices

WEBSOCKET_URL = 'wss://ws.dev.pragma.build/node/v1/data/subscribe'
SUBSCRIPTION_MESSAGE = {
    'msg_type': 'subscribe',
    'pairs': ['BTC/USD', 'ETH/USD', 'SOL/USD', 'BNB/USD']
}

class PriceCollector:
    def __init__(self):
        self.price_history = []
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.update_queue = Queue()

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

    async def update_price_history(self, pragma_prices: Dict[str, float]) -> None:
        try:
            pyth_raw_prices = await retrieve_pyth_prices()
            
            if pyth_raw_prices:
                pyth_prices = {}
                for pair, price in pyth_raw_prices.items():
                    pyth_prices[pair] = price

                price_entry = {
                    'timestamp': time.time(),
                    'pragma_prices': pragma_prices.copy(),
                    'pyth_prices': pyth_prices
                }

                with self.lock:
                    self.price_history.append(price_entry)
                self.update_queue.put(price_entry)

        except Exception as e:
            print(f'Error updating price history: {e}')

    async def websocket_client(self):
        current_pragma_prices: Dict[str, float] = {}
        
        while self.running:
            try:
                async with websockets.connect(WEBSOCKET_URL) as websocket:
                    print("WebSocket connection established")
                    await websocket.send(json.dumps(SUBSCRIPTION_MESSAGE))
                    
                    while self.running:
                        message = await websocket.recv()
                        try:
                            parsed_data = json.loads(message)
                            
                            if 'oracle_prices' not in parsed_data:
                                continue

                            prices_updated = False
                            for price_data in parsed_data['oracle_prices']:
                                if 'global_asset_id' not in price_data or 'median_price' not in price_data:
                                    continue
                                    
                                pair = self.decode_short_string(price_data['global_asset_id'])
                                if not pair:
                                    continue
                                    
                                price = self.format_price(price_data['median_price'])
                                if not price:
                                    continue
                                    
                                current_pragma_prices[pair] = price
                                prices_updated = True
                            
                            if prices_updated:
                                await self.update_price_history(current_pragma_prices)
                                
                        except json.JSONDecodeError as e:
                            print(f'Error parsing JSON message: {e}')
                        except Exception as e:
                            print(f'Error processing message: {e}')
                        
            except websockets.exceptions.ConnectionClosed:
                if self.running:
                    print("Connection closed. Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)
                
            except Exception as e:
                if self.running:
                    print(f"WebSocket error: {e}")
                    await asyncio.sleep(5)

    def run_async_loop(self):
        asyncio.run(self.websocket_client())

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run_async_loop)
            self.thread.start()
            print("Price collector started")

    def stop(self):
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join()
            print("Price collector stopped")

    def get_history(self):
        with self.lock:
            return self.price_history.copy()

def print_price_update(price_entry):
    if not price_entry:
        return
        
    print("\nNew price update:")
    print(f"Timestamp: {time.ctime(price_entry['timestamp'])}")
    
    pragma_prices = price_entry.get('pragma_prices', {})
    pyth_prices = price_entry.get('pyth_prices', {})
    
    for pair in sorted(pragma_prices.keys()):
        pragma_price = pragma_prices[pair]
        pyth_price = pyth_prices.get(pair)
        
        if pyth_price:
            delta = ((pragma_price - pyth_price) * 100) / pragma_price
            print(f"{pair} => Pragma: ${pragma_price:,.2f}, Pyth: ${pyth_price:,.2f}, Delta: {delta:+.2f}%")
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
                    print_price_update(new_price_entry)
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