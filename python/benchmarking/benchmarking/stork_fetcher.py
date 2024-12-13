import aiohttp
from typing import Dict, Optional
from x10.perpetual.trading_client import PerpetualTradingClient
from x10.perpetual.configuration import MAINNET_CONFIG

MARKET_PAIRS = [
    'BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'LTC-USD', 'LINK-USD', 
    'AVAX-USD', 'MATIC-USD', 'XRP-USD', 'DOGE-USD', 'PEPE-USD', 'AAVE-USD',
    'TRX-USD', 'SUI-USD', 'WIF-USD', 'TIA-USD', 'TON-USD', 'LDO-USD',
    'ARB-USD', 'OP-USD', 'ORDI-USD', 'JTO-USD', 'JUP-USD', 'UNI-USD',
    'OKB-USD', 'ATOM-USD', 'NEAR-USD', 'SATS-USD', 'ONDO-USD'
]

async def retrieve_stork_prices() -> Optional[Dict[str, float]]:
    """
    Retrieves real-time price data from Stork Network for various cryptocurrency pairs.
    
    Returns:
        Dict[str, float]: A dictionary mapping trading pairs to their current prices,
                         or None if an error occurs
    """
    price_map = {}

    try:
        # Create a new trading client
        trading_client = PerpetualTradingClient(MAINNET_CONFIG, None)
        try:
            markets = await trading_client.markets_info.get_markets()
            assert markets.data is not None
            markets_cache = {m.name: m for m in markets.data}

            for market_pair in MARKET_PAIRS:
                if market_pair in markets_cache:
                    market = markets_cache[market_pair]
                    if (hasattr(market, 'market_stats') and 
                        market.market_stats is not None and 
                        market.market_stats.mark_price is not None):
                        normalized_pair = market_pair.replace("-", "")
                        price_map[normalized_pair] = float(market.market_stats.index_price)
        finally:
            # Ensure the session is closed
            await trading_client.close()

        return price_map

    except Exception as e:
        print(f'Error fetching data from Stork: {e}')
        return None


if __name__ == "__main__":
    import asyncio
    
    async def main():
        while True:
            prices = await retrieve_stork_prices()
            if prices:
                for pair, price in prices.items():
                    print(f"{pair}: {price}")
            else:
                print("Failed to retrieve prices")

    asyncio.run(main())

