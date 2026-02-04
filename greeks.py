import numpy as np
import pandas as pd
from scipy.stats import norm

class Greeks:
    @staticmethod
    def d1(S, K, T, r, sigma):
        return (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))

    @staticmethod
    def d2(S, K, T, r, sigma):
        return Greeks.d1(S, K, T, r, sigma) - sigma * np.sqrt(T)

    @staticmethod
    def calculate_gamma(S, K, T, r, sigma):
        """Calculates Gamma for an option."""
        if T <= 0:
            return 0.0
        d1 = Greeks.d1(S, K, T, r, sigma)
        return norm.pdf(d1) / (S * sigma * np.sqrt(T))

    @staticmethod
    def calculate_delta(S, K, T, r, sigma, option_type='call'):
        """Calculates Delta for an option."""
        if T <= 0:
            return 0.0
        d1 = Greeks.d1(S, K, T, r, sigma)
        if option_type == 'call':
            return norm.cdf(d1)
        else:
            return norm.cdf(d1) - 1

    @staticmethod
    def calculate_vanna(S, K, T, r, sigma, option_type='call'):
        """
        Calculates Vanna: Sensitivity of Delta to a change in IV.
        d(Delta)/d(sigma)
        """
        if T <= 0:
            return 0.0
        d1 = Greeks.d1(S, K, T, r, sigma)
        d2 = Greeks.d2(S, K, T, r, sigma)
        return -norm.pdf(d1) * d2 / sigma

    @staticmethod
    def calculate_charm(S, K, T, r, sigma, option_type='call'):
        """
        Calculates Charm: Sensitivity of Delta to time decay.
        -d(Delta)/d(T)
        """
        if T <= 0:
            return 0.0
        d1 = Greeks.d1(S, K, T, r, sigma)
        d2 = Greeks.d2(S, K, T, r, sigma)
        
        term1 = norm.pdf(d1) * (r / (sigma * np.sqrt(T)) - d2 / (2 * T))
        
        if option_type == 'call':
            return -term1
        else:
            return -term1 + r * np.exp(-r * T)

class DealerBook:
    def __init__(self, data: pd.DataFrame, spot_price: float, risk_free_rate: float = 0.04):
        """
        Initializes the DealerBook.
        
        :param data: DataFrame containing option chain data.
                     Expected columns: ['strike', 'type', 'expiry', 'iv', 'open_interest', 'gamma', 'delta']
                     Optional columns: ['buy_to_open', 'sell_to_open'] for inventory estimation.
        :param spot_price: Current underlying spot price.
        :param risk_free_rate: Risk free rate for calculations.
        """
        self.data = data.copy()
        self.spot_price = spot_price
        self.risk_free_rate = risk_free_rate
        
        # Ensure T (time to expiry) is calculated if not present
        if 'T' not in self.data.columns and 'expiry' in self.data.columns:
             # Assuming expiry is a datetime or string parsable to datetime
             # calculating T in years. 
             # For simplicity, if 'expiry' is just days, we divide by 365
             # If it's a date, we subtract today.
             # We will assume for now it's handled or passed as T.
             # If 'expiry' is present, we try to parse it.
             self.data['expiry'] = pd.to_datetime(self.data['expiry'])
             self.data['T'] = (self.data['expiry'] - pd.Timestamp.now()).dt.days / 365.0
             self.data['T'] = self.data['T'].clip(lower=0.0001) # Avoid division by zero

    def estimate_inventory(self):
        """
        Estimates Dealer Inventory (+1 for Long, -1 for Short).
        If 'buy_to_open' and 'sell_to_open' are present (from Cboe), use them.
        Logic: If Customer Buy > Customer Sell, Dealer is Short (-1).
        
        If not present, we can default to a standard assumption:
        Dealers are typically Short Calls and Short Puts? Or Short Calls, Long Puts?
        Standard naive assumption: Dealers are Short OTM options (selling variance).
        But let's stick to the prompt's instruction about Cboe data.
        If data is missing, we'll assume Dealer is Short (-1) for now as a default exposure to customers buying.
        """
        if 'buy_to_open' in self.data.columns and 'sell_to_open' in self.data.columns:
            # Net Customer Buying = Buy to Open - Sell to Open
            # Dealer Position = - (Net Customer Buying)
            customer_net_buying = self.data['buy_to_open'] - self.data['sell_to_open']
            # If Customer buys more, Dealer is short (-1). 
            # If Customer sells more, Dealer is long (+1).
            self.data['dealer_position'] = np.where(customer_net_buying > 0, -1, 1)
        else:
            # Fallback/Mock: Assume Dealers are Short everywhere (selling to customers)
            self.data['dealer_position'] = -1

    def calculate_greeks(self):
        """
        Calculates GEX, Vanna, Charm for the book.
        """
        # Ensure we have dealer position
        if 'dealer_position' not in self.data.columns:
            self.estimate_inventory()

        # If gamma/iv are not provided, we might need to calculate them, 
        # but usually API provides them. We will use provided columns if available,
        # else calculate.
        
        # GEX Calculation
        # GEX = Gamma * OpenInterest * 100 * Spot^2 * 0.01 * Direction
        # The prompt says: GEX = Gamma * OpenInterest * 100 * Spot^2 * 0.01
        # Factor 100 is for contract multiplier. 0.01 is to normalize percentage move.
        # So GEX represents dollar gamma for 1% move? 
        # Usually Dollar Gamma = 0.5 * Gamma * S^2 * 0.01^2 for PnL?
        # Standard GEX definition: Change in dollar delta per 1% move.
        # = Gamma * S * (0.01 * S) * OI * 100 
        # = Gamma * OI * 100 * S^2 * 0.01. Matches the formula.
        
        if 'gamma' not in self.data.columns:
            # Calculate Gamma
            self.data['gamma'] = self.data.apply(
                lambda row: Greeks.calculate_gamma(
                    self.spot_price, row['strike'], row['T'], self.risk_free_rate, row['iv']
                ), axis=1
            )

        self.data['GEX'] = (
            self.data['gamma'] * 
            self.data['open_interest'] * 
            100 * 
            (self.spot_price ** 2) * 
            0.01 * 
            self.data['dealer_position']
        )

        # Vanna Calculation
        # Sensitivity of Delta to 1% change in IV.
        # We can calculate raw Vanna using Black Scholes formula.
        self.data['vanna'] = self.data.apply(
            lambda row: Greeks.calculate_vanna(
                self.spot_price, row['strike'], row['T'], self.risk_free_rate, row['iv'], row['type']
            ), axis=1
        )
        # Weight by OI and position?
        # Usually we want "Net Vanna Exposure" in dollar terms or similar.
        # Let's compute Net Vanna = Vanna * OI * 100 * dealer_position
        self.data['net_vanna'] = self.data['vanna'] * self.data['open_interest'] * 100 * self.data['dealer_position']

        # Charm Calculation
        # Delta decay over time.
        self.data['charm'] = self.data.apply(
            lambda row: Greeks.calculate_charm(
                self.spot_price, row['strike'], row['T'], self.risk_free_rate, row['iv'], row['type']
            ), axis=1
        )
        self.data['net_charm'] = self.data['charm'] * self.data['open_interest'] * 100 * self.data['dealer_position']

    def get_total_gex(self):
        return self.data['GEX'].sum()

    def get_gex_by_strike(self):
        return self.data.groupby('strike')['GEX'].sum()

    def find_gamma_flip_strike(self):
        """
        Finds the strike where the net GEX sum transitions from negative to positive.
        This usually means we look at the cumulative sum of GEX across strikes.
        Or is it where the GEX at that strike flips sign?
        Usually "Gamma Flip" is the strike level where the TOTAL market gamma flips from positive to negative or vice versa.
        But typically it's defined as the strike where Cumulative GEX crosses zero.
        """
        gex_by_strike = self.get_gex_by_strike().sort_index()
        cumsum_gex = gex_by_strike.cumsum()
        
        # Find where sign changes
        # We are looking for the zero crossing of the CUMULATIVE sum curve? 
        # Or just the point where GEX flips?
        # "Strike where the net GEX sum transitions from negative to positive"
        # This implies Cumulative Sum.
        
        # Let's find the strike where cumsum goes from negative to positive.
        
        # If it never crosses, return None or closest.
        
        # Get signs
        signs = np.sign(cumsum_gex)
        
        # Find indices where sign changes
        diffs = np.diff(signs)
        crossings = np.where(diffs != 0)[0]
        
        if len(crossings) > 0:
            # Return the strike corresponding to the crossing
            # crossings[0] is the index before the flip.
            idx = crossings[0]
            return gex_by_strike.index[idx + 1]
        
        return None
