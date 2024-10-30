import json
import asyncio
from pyth import retrieve_pyth_prices
import websockets
import time
from typing import Dict, List

WEBSOCKET_URL = 'wss://ws.dev.pragma.build/node/v1/data/subscribe'
SUBSCRIPTION_MESSAGE = {
    'msg_type': 'subscribe',
    'pairs': ['BTC/USD', 'ETH/USD', 'SOL/USD', 'BNB/USD']
}

# Global array to store historical price data
price_history: List[Dict] = []

def decode_short_string(felt: str) -> str:
    felt_int = int(felt, 16) if felt.startswith('0x') else int(felt)
    bytes_str = felt_int.to_bytes((felt_int.bit_length() + 7) // 8, byteorder='big')
    return bytes_str.decode('ascii')

def format_price(price_str: str) -> float:
    price_length = len(price_str)
    whole_part = price_str[:price_length - 8]
    decimal_part = price_str[price_length - 8:]
    return float(f"{whole_part}.{decimal_part}")

def convert_pyth_format(pyth_prices: Dict[str, float]) -> Dict[str, float]:
    """
    Convert Pyth price format (BTCUSD) to Pragma format (BTC/USD)
    """
    converted_prices = {}
    for pair, price in pyth_prices.items():
        # Convert BTCUSD to BTC/USD format
        formatted_pair = f"{pair[:-3]}/{pair[-3:]}"
        converted_prices[formatted_pair] = price
    return converted_prices

async def update_price_history(pragma_prices: Dict[str, float]) -> None:
    """
    Update the global price history with new price data from both sources
    """
    try:
        # Get Pyth prices
        pyth_raw_prices = await retrieve_pyth_prices()
        if pyth_raw_prices:
            pyth_prices = convert_pyth_format(pyth_raw_prices)
            
            # Create history entry with both price sources
            price_entry = {
                'timestamp': time.time(),
                'pragma_prices': pragma_prices.copy(),
                'pyth_prices': pyth_prices
            }
            
            price_history.append(price_entry)
            
            # Print latest entry for monitoring
            print(f"\nNew price entry : {price_entry}")
            for pair in pragma_prices.keys():
                pragma_price = pragma_prices.get(pair)
                pyth_price = pyth_prices.get(pair)
                if pragma_price and pyth_price:
                    delta = ((pragma_price - pyth_price) * 100) / pragma_price
                    print(f"{pair}: Pragma={pragma_price:.2f}, Pyth={pyth_price:.2f}, Δ={delta:.2f}%")
            print(f"History length: {len(price_history)}\n")
            
    except Exception as e:
        print(f'Error updating price history: {e}')

async def websocket_client():
    current_pragma_prices: Dict[str, float] = {}
    
    while True:
        try:
            async with websockets.connect(WEBSOCKET_URL) as websocket:
                print("WebSocket connection established")
                await websocket.send(json.dumps(SUBSCRIPTION_MESSAGE))
                
                while True:
                    message = await websocket.recv()
                    try:
                        parsed_data = json.loads(message)
                        prices_updated = False
                        
                        for price_data in parsed_data['oracle_prices']:
                            pair = decode_short_string(price_data['global_asset_id'])
                            price = format_price(price_data['median_price'])
                            current_pragma_prices[pair] = price
                            prices_updated = True
                        
                        if prices_updated:
                            await update_price_history(current_pragma_prices)
                            
                    except Exception as e:
                        print(f'Error processing message: {e}')
                    
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"WebSocket error: {e}")
            await asyncio.sleep(5)

# Utility functions
def get_price_history() -> List[Dict]:
    """
    Return the complete price history
    """
    return price_history

def get_latest_prices() -> Dict:
    """
    Return the most recent prices from both sources
    """
    if price_history:
        return price_history[-1]
    return {'pragma_prices': {}, 'pyth_prices': {}}

def get_price_deltas() -> Dict[str, float]:
    """
    Calculate current price deltas between Pragma and Pyth
    """
    if not price_history:
        return {}
    
    latest = price_history[-1]
    deltas = {}
    
    for pair in latest['pragma_prices'].keys():
        pragma_price = latest['pragma_prices'].get(pair)
        pyth_price = latest['pyth_prices'].get(pair)
        
        if pragma_price and pyth_price:
            delta = ((pragma_price - pyth_price) * 100) / pragma_price
            deltas[pair] = delta
            
    return deltas

if __name__ == "__main__":
    try:
        asyncio.run(websocket_client())
    except KeyboardInterrupt:
        print("\nApplication terminated by user")
        print(f"Final history length: {len(price_history)}")