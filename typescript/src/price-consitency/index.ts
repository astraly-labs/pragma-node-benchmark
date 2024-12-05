import { shortString } from 'starknet';
import WebSocket from 'ws';
import {retrievePythPrices} from "./pyth";

const websocketUrl = 'wss://ws.dev.pragma.build/node/v1/data/subscribe';
const subscriptionMessage = {
  msg_type: 'subscribe',
  pairs: ['BTC/USD', 'ETH/USD', 'SOL/USD', 'BNB/USD']
};

// pairs: ['BTC/USD', 'ETH/USD', 'SOL/USD', 'BNB/USD', 'LTC/USD', 'LINK/USD', 'AVAX/USD', 'MATIC/USD', 'XRP/USD', 'DOGE/USD', '1000PEPE/USD', 'AAVE/USD', 'TRX/USD', 'SUI/USD', 'WIF/USD', 'TIA/USD', 'TON/USD', 'LDO/USD', 'ARB/USD', 'OP/USD', 'ORDI/USD', 'JTO/USD', 'JUP/USD', 'UNI/USD', 'OKB/USD', 'ATOM/USD', 'NEAR/USD', '1000SATS/USD', 'ONDO/USD']


const priceMap = new Map<string, number>();

function formatPrice(priceStr: string): number {
  const priceLength = priceStr.length;
  const wholePart = priceStr.slice(0, priceLength - 8);
  const decimalPart = priceStr.slice(priceLength - 8);
  const formattedPrice = parseFloat(`${wholePart}.${decimalPart}`);
  return formattedPrice;
}
function benchmarkWebSocket() {
  const startTime = Date.now();
  let messageCount = 0;
  let totalProcessingTime = 0;

  function connectWebSocket() {
    const ws = new WebSocket(websocketUrl);

    ws.on('open', () => {
      console.log('WebSocket connection established');
      ws.send(JSON.stringify(subscriptionMessage));
    });

    ws.on('message', async (data: WebSocket.Data) => {
      const processingStart = performance.now();
      try {
        const parsedData = JSON.parse(data.toString());
        messageCount++;
        
        parsedData.oracle_prices.forEach((price: {
          global_asset_id: string;
          median_price: string;
        }) => {
            priceMap.set(shortString.decodeShortString(price.global_asset_id), formatPrice(price.median_price));
        });
        let pythMap = await retrievePythPrices();

        priceMap.forEach((price,pair) => {
          let pythPrice = pythMap?.get(pair);
          if (pythPrice) {
            console.log(`${pair} => pragma price : ${price}, pyth price : ${pythPrice}, delta is ${(((price - pythPrice)*100)/price).toFixed(2)} %`);
          } else {
            throw(`no pyth price for ${pair}`);
          }
        });

        console.log("");
      } catch (error) {
        console.error('Error parsing received data:', error);
      }
      const processingEnd = performance.now();
      totalProcessingTime += processingEnd - processingStart;
    });

    ws.on('error', (error) => {
      console.error('WebSocket error:', error);
    });

    ws.on('close', (code: number, reason: string) => {
      console.log(`WebSocket connection closed. Code: ${code}, Reason: ${reason}`);
      console.log('Attempting to reconnect in 5 seconds...');
      setTimeout(connectWebSocket, 5000);
    });
  }

  connectWebSocket();
}

benchmarkWebSocket();
