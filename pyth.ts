const pythUrl = 'https://hermes.pyth.network/v2/updates/price/stream?ids[]=0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43';

interface PythResponse {
  parsed: any[];
}

async function benchmarkPythDataProcessing() {
  const startTime = Date.now();
  let messageCount = 0;
  let totalProcessingTime = 0;

  try {
    const response = await fetch(pythUrl);

    if (!response.body) {
      throw new Error('No response body');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      let newlineIndex;
      while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
        const line = buffer.slice(0, newlineIndex);
        buffer = buffer.slice(newlineIndex + 1);

        if (line.trim().startsWith('data:')) {
          const processingStart = performance.now();
          try {
            const jsonData = JSON.parse(line.slice(5)) as PythResponse;
            if (jsonData.parsed && Array.isArray(jsonData.parsed)) {
              messageCount++;
              // Uncomment the next line if you want to see each parsed message
            //   console.log(JSON.stringify(jsonData.parsed, null, 2));
            }
          } catch (error) {
            console.error('Error parsing JSON:', error);
          }
          const processingEnd = performance.now();
          totalProcessingTime += processingEnd - processingStart;
        }

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
      }
    }
  } catch (error) {
    console.error('Error fetching data:', error);
  }
}

benchmarkPythDataProcessing();