import aiohttp
import json
import time
from typing import Dict, List, Optional
from urllib.parse import urlencode

PYTH_URL_BASE = 'https://hermes.pyth.network/v2/updates/price/stream'

PAIR_SIGNATURES = {
    "e62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43": "BTCUSD",
    "ff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace": "ETHUSD",
    "ef0d8b6fda2ceba41da15d4095d1da392a0d2f8ed0c6c7bc0f4cfac8c280b56d": "SOLUSD",
    "2f95862b045670cd22bee3114c39763a4a08beeb663b145d283c31d7d1101c4f": "BNBUSD",
    "6e3f3fa8253588df9326580180233eb791e03b443a3ba7a1d892e73874e19a54": "LTCUSD",
    "8ac0c70fff57e9aefdf5edf44b51d62c2d433653cbb2cf5cc06bb115af04d221": "LINKUSD",
    "93da3352f9f1d105fdfe4971cfa80e9dd777bfc5d0f683ebb6e1294b92137bb7": "AVAXUSD",
    "ffd11c5a1cfd42f80afb2df4d9f264c15f956d68153335374ec10722edd70472": "POLUSD",
    "ec5d399846a9209f3fe5881d70aae9268c94339ff9817e8d18ff19fa05eea1c8": "XRPUSD",
    "dcef50dd0a4cd2dcc17e45df1676dcb336a11a61c69df7a0299b0150c672d25c": "DOGEUSD",
    "d69731a2e74ac1ce884fc3890f7ee324b6deb66147055249568869ed700882e4": "PEPEUSD",
    "2b9ab1e972a281585084148ba1389800799bd4be63b957507db1349314e47445": "AAVEUSD",
    "67aed5a24fdad045475e7195c98a98aea119c763f272d4523f5bac93a4f33c2b": "TRXUSD",
    "23d7315113f5b1d3ba7a83604c44b94d79f4fd69af77f804fc7f920a6dc65744": "SUIUSD",
    "4ca4beeca86f0d164160323817a4e42b10010a724c2217c6ee41b54cd4cc61fc": "WIFUSD",
    "09f7c1d7dfbb7df2b8fe3d3d87ee94a2259d212da4f30c1f0540d066dfa44723": "TIAUSD",
    "8963217838ab4cf5cadc172203c1f0b763fbaa45f346d8ee50ba994bbcac3026": "TONUSD",
    "c63e2a7f37a04e5e614c07238bedb25dcc38927fba8fe890597a593c0b2fa4ad": "LDOUSD",
    "3fa4252848f9f0a1480be62745a4629d9eb1322aebab8a791e344b3b9c1adcf5": "ARBUSD",
    "385f64d993f7b77d8182ed5003d97c60aa3361f3cecfe711544d2d59165e9bdf": "OPUSD",
    "193c739db502aadcef37c2589738b1e37bdb257d58cf1ab3c7ebc8e6df4e3ec0": "ORDIUSD",
    "b43660a5f790c69354b0729a5ef9d50d68f1df92107540210b9cccba1f947cc2": "JTOUSD",
    "0a0408d619e9380abad35060f9192039ed5042fa6f82301d0e48bb52be830996": "JUPUSD",
    "78d185a741d07edb3412b09008b7c5cfb9bbbd7d568bf00ba737b456ba171501": "UNIUSD",
    "d6f83dfeaff95d596ddec26af2ee32f391c206a183b161b7980821860eeef2f5": "OKBUSD",
    "b00b60f88b03a6a625a8d1c048c3f66653edf217439983d037e7222c4e612819": "ATOMUSD",
    "c415de8d2eba7db216527dff4b60e8f3a5311c740dadb233e13e12547e226750": "NEARUSD",
    "40440d18fb5ad809e2825ce7dfc035cfa57135c13062a04addafe0c7f54425e0": "SATSUSD",
    "d40472610abe56d36d065a0cf889fc8f1dd9f3b7f2a478231a5fc6df07ea5ce3": "ONDOUSD"
}

async def retrieve_pyth_prices() -> Optional[Dict[str, float]]:
    """
    Retrieves real-time price data from Pyth Network for various cryptocurrency pairs.
    
    Returns:
        Dict[str, float]: A dictionary mapping trading pairs to their current prices,
                         or None if an error occurs
    """
    price_map = {}
    start_time = time.time()
    message_count = 0
    total_processing_time = 0

    try:
        # Construct query parameters
        params = []
        for hash_id in PAIR_SIGNATURES.keys():
            params.append(('ids[]', hash_id))
        
        query_string = urlencode(params)
        pyth_url = f"{PYTH_URL_BASE}?{query_string}"

        async with aiohttp.ClientSession() as session:
            async with session.get(pyth_url) as response:
                if not response.ok:
                    raise aiohttp.ClientError(f"HTTP {response.status}: {response.reason}")

                buffer = ""
                async for chunk in response.content:
                    buffer += chunk.decode('utf-8')
                    
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        
                        if line.strip().startswith('data:'):
                            processing_start = time.perf_counter()
                            try:
                                json_data = json.loads(line[5:])
                                
                                if json_data.get('parsed') and isinstance(json_data['parsed'], list):
                                    message_count += 1
                                    
                                    for prices in json_data['parsed']:
                                        pair_id = PAIR_SIGNATURES.get(prices['id'])
                                        if pair_id:
                                            price = int(prices['price']['price']) * (10 ** int(prices['price']['expo']))
                                            price_map[pair_id] = price
                                    
                                    # Return as soon as we get the first complete set of prices
                                    return price_map
                                    
                            except json.JSONDecodeError as e:
                                print(f'Error parsing JSON: {e}')
                                
                            processing_end = time.perf_counter()
                            total_processing_time += processing_end - processing_start

    except Exception as e:
        print(f'Error fetching data: {e}')
        return None
    
if __name__ == "__main__":
    import asyncio
    
    async def main():
        prices = await retrieve_pyth_prices()
        if prices:
            print("\nCurrent Pyth prices:")
            for pair, price in prices.items():
                print(f"{pair}: ${price:,.2f}")
        else:
            print("Failed to retrieve Pyth prices")

    asyncio.run(main())
