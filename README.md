# Quant Research System

A full-stack quantitative research and trading system designed to attribute S&P 500 price action to mechanical hedging flows (GEX, VEX, CEX) and systematic rebalancing.

## Features

- **Data Ingestion**: Connectors for Polygon.io (Option Chains, Trades) and Interactive Brokers (Futures Tick Data).
- **Core Engine**: Calculates Dealer Inventory, GEX (Gamma Exposure), Vanna, Charm, and detects the "Gamma Flip" strike.
- **Analytics**: SVAR (Structural Vector Autoregression) for Impulse Response analysis and Regime Switching models.
- **Dashboard**: Interactive Streamlit UI for real-time microstructure analysis.

## Setup & Installation

### Prerequisites

- Python 3.10+
- [Interactive Brokers TWS or Gateway](https://www.interactivebrokers.com/en/trading/tws.php) (for Futures data)
- Polygon.io API Key (for Options data)

### Installation

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd quant-research-system
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

### Configuration

#### Polygon.io
Set your API key as an environment variable:
```bash
export POLYGON_API_KEY="your_api_key_here"
```

#### Interactive Brokers
1. Open TWS or IB Gateway.
2. Go to **File > Global Configuration > API > Settings**.
3. Ensure "Enable ActiveX and Socket Clients" is checked.
4. Note the **Socket Port** (default 7496 for TWS, 7497 for Paper TWS/Gateway).
5. The system defaults to `127.0.0.1:7497`. To change this, update `src/dashboard/app.py` or `src/connectors/ibkr.py`.

## Usage

### Running the Dashboard

```bash
streamlit run src/dashboard/app.py
```

### Mock Mode
If API keys are not provided or IBKR is not connected, the system will automatically fallback to **Mock Mode**, generating synthetic data for demonstration purposes.

### Running Tests

```bash
pytest tests/
```

## Directory Structure

- `src/connectors`: Clients for Polygon and IBKR.
- `src/engine`: Core Greek calculations (`DealerBook`).
- `src/analytics`: Statistical models (`SVARModel`, `RegimeSwitchingModel`).
- `src/dashboard`: Streamlit frontend.
- `tests`: Unit tests.

## License
MIT
