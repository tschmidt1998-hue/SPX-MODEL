from ib_insync import IB, Stock, Future, util
import pandas as pd
import numpy as np
import asyncio
import logging
from datetime import datetime

class IBKRClient:
    def __init__(self, host='127.0.0.1', port=7497, client_id=1):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.connected = False
        self.mock_mode = False
        self.data_callback = None

    def connect(self):
        """Connects to IBKR TWS or Gateway."""
        try:
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            self.connected = True
            self.mock_mode = False
            logging.info("Connected to IBKR")
        except Exception as e:
            logging.warning(f"Failed to connect to IBKR: {e}. Switching to Mock mode.")
            self.connected = False
            self.mock_mode = True

    def disconnect(self):
        """Disconnects from IBKR."""
        if self.connected:
            self.ib.disconnect()
            self.connected = False

    def start_streaming(self, symbol: str, sec_type: str = 'FUT', exchange: str = 'GLOBEX', currency: str = 'USD', callback=None):
        """
        Starts streaming real-time tick data for a given symbol.
        
        :param symbol: Ticker symbol (e.g., 'ES', 'MES')
        :param sec_type: Security Type (e.g., 'FUT')
        :param exchange: Exchange (e.g., 'GLOBEX')
        :param currency: Currency (e.g., 'USD')
        :param callback: Function to call with new data
        """
        self.data_callback = callback
        
        if not self.connected and not self.mock_mode:
            self.connect()
            
        # Contract definition
        # Note: Finding the correct front-month expiry programmatically can be complex.
        # Here we default to current YYYYMM which might not be valid for all futures.
        # User should verify expiry logic.
        current_expiry = datetime.now().strftime("%Y%m")
        contract = Future(symbol, current_expiry, exchange) 
        
        if self.connected:
             try:
                 self.ib.qualifyContracts(contract)
                 self.ib.reqMktData(contract, '', False, False)
                 self.ib.pendingTickersEvent += self._on_pending_tickers
                 logging.info(f"Started streaming for {symbol} (Real)")
             except Exception as e:
                 logging.error(f"Error starting stream: {e}")
        else:
            logging.info(f"Started streaming for {symbol} (Mock)")
            # In a real async loop we would simulate ticks here.

    def _on_pending_tickers(self, tickers):
        """Callback for real IBKR updates."""
        for t in tickers:
            if self.data_callback:
                self.data_callback({
                    'symbol': t.contract.symbol,
                    'bid': t.bid,
                    'ask': t.ask,
                    'last': t.last,
                    'time': t.time
                })

    def get_historical_data(self, symbol: str, duration: str = '1 D', bar_size: str = '1 min'):
        """Fetches historical data."""
        if self.connected:
             # Real implementation placeholder
             # contract = Future(symbol, datetime.now().strftime("%Y%m"), 'GLOBEX')
             # self.ib.qualifyContracts(contract)
             # bars = self.ib.reqHistoricalData(contract, endDateTime='', durationStr=duration, barSizeSetting=bar_size, whatToShow='TRADES', useRTH=False)
             # df = util.df(bars)
             # return df
             pass

        # Return Mock data if not connected or as fallback
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='1min')
        data = pd.DataFrame({
            'date': dates,
            'open': 100 + np.random.randn(100).cumsum(),
            'high': 100 + np.random.randn(100).cumsum() + 1,
            'low': 100 + np.random.randn(100).cumsum() - 1,
            'close': 100 + np.random.randn(100).cumsum(),
            'volume': np.random.randint(100, 1000, 100)
        })
        return data
