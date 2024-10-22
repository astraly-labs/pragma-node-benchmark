import WebSocket from 'ws';

const websocketUrl = 'wss://ws.dev.pragma.build/node/v1/data/subscribe';
const subscriptionMessage = {
  msg_type: 'subscribe',
  pairs: ['BTC/USD', 'ETH/USD:MARK']
};

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

    ws.on('message', (data: WebSocket.Data) => {
      const processingStart = performance.now();
      try {
        const parsedData = JSON.parse(data.toString());
        messageCount++;
        
        // Uncomment the next line if you want to see each parsed message
        // console.log('Received data:', parsedData);

        // Print performance metrics every 1000 messages
        if (messageCount % 1000 === 0) {
          const currentTime = Date.now();
          const elapsedSeconds = (currentTime - startTime) / 1000;
          const messagesPerSecond = messageCount / elapsedSeconds;
          const avgProcessingTime = totalProcessingTime / messageCount;
          
          console.log(`Processed ${messageCount} messages in ${elapsedSeconds.toFixed(2)} seconds`);
          console.log(`Average processing time: ${avgProcessingTime.toFixed(3)} ms`);
          console.log(`Messages per second: ${messagesPerSecond.toFixed(2)}`);
          console.log('---');
        }
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