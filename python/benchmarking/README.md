# Pragma Node Benchmarking Tool 🚀

A comprehensive tool for monitoring and benchmarking Pragma Oracle Node performance against other price feeds (Pyth, Stork).

## System Requirements 🖥️

- Python >=3.10
- GMP (GNU Multiple Precision Arithmetic Library)
  - On macOS: `brew install gmp`
  - On Ubuntu/Debian: `sudo apt-get install libgmp-dev`
  - On Fedora/RHEL: `sudo dnf install gmp-devel`

## Features ✨

- **Real-time Price Monitoring**: Concurrent tracking of prices from multiple sources
  - Pragma Oracle Node
  - Pyth Network
  - Stork Network

- **Statistical Analysis** 📊
  - Mean Square Error (MSE)
  - Spearman Correlation
  - Price Delta Calculations
  - Latency Metrics (mean, median, quartiles)

- **Multiple Interfaces**
  - Interactive GUI Dashboard (Streamlit)
  - CLI Monitoring
  - Automated Tests

## Quick Start 🏃‍♂️

1. Clone the repository:
```bash
git clone https://github.com/your-repo/pragma-node-benchmark
cd pragma-node-benchmark/python/benchmarking
```

2. Install uv (if not already installed):
```bash
pip install uv
```

3. Create virtual environment and install dependencies:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

4. Run the GUI dashboard:
```bash
streamlit run benchmarking/GUI_monitoring.py
```

## Architecture 🏗️
The tool is built around the `PriceCollector` class which manages three concurrent price feeds:

                  ┌─────────────────┐
                  │  PriceCollector │
                  └────────┬────────┘
                          │
            ┌────────────┴─────────────┐
            │                          │
    ┌───────┴────────┐        ┌───────┴────────┐
    │  Pragma Feed   │        │   Other Feeds   │
    │  (WebSocket)   │        │   (REST/HTTP)   │
    └───────┬────────┘        └───────┬────────┘
            │                          │
    ┌───────┴────────┐        ┌───────┴────────┐
    │  Price History │        │ Statistical     │
    │  & Metrics     │        │ Analysis        │
    └────────────────┘        └────────────────┘

## Configuration 🔧
Environment settings can be configured in the `price_collector.py`:

```python
# Environment configurations
ENVIRONMENTS = {
    'local': 'ws://localhost:3000/node/v1/data/subscribe',
    'dev': 'wss://ws.dev.pragma.build/node/v1/data/subscribe',
    'prod': 'wss://ws.pragma.build/node/v1/data/subscribe'
}
```


## Contributing 🤝

1. Fork the repository

2. Create your feature branch (`git checkout -b feature/amazing-feature`)

3. Commit your changes (`git commit -m 'Add some amazing feature'`)

4. Push to the branch (`git push origin feature/amazing-feature`)

5. Open a Pull Request

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.

---
Made with ❤️ by Pragma