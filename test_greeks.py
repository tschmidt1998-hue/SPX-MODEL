import pytest
import pandas as pd
import numpy as np
from src.engine.greeks import DealerBook, Greeks

@pytest.fixture
def sample_option_data():
    # Create a sample DataFrame
    strikes = [4000, 4050, 4100, 4150, 4200]
    expiry = pd.Timestamp.now() + pd.Timedelta(days=30)
    data = []
    for k in strikes:
        data.append({
            'strike': k,
            'type': 'call',
            'expiry': expiry,
            'iv': 0.2,
            'open_interest': 1000,
            'buy_to_open': 100,
            'sell_to_open': 50
        })
        data.append({
            'strike': k,
            'type': 'put',
            'expiry': expiry,
            'iv': 0.2,
            'open_interest': 1000,
            'buy_to_open': 50,
            'sell_to_open': 100
        })
    return pd.DataFrame(data)

def test_calculate_gamma():
    # Test Black-Scholes Gamma calculation
    S = 100
    K = 100
    T = 1.0
    r = 0.05
    sigma = 0.2
    gamma = Greeks.calculate_gamma(S, K, T, r, sigma)
    assert gamma > 0
    assert np.isclose(gamma, 0.0188, atol=0.001) # Approx value

def test_dealer_book_inventory(sample_option_data):
    book = DealerBook(sample_option_data, spot_price=4100)
    book.estimate_inventory()
    
    # Check inventory logic
    # Call: Buy=100, Sell=50 -> Net Buy = 50 -> Dealer Short (-1)
    call_row = book.data[(book.data['strike'] == 4000) & (book.data['type'] == 'call')].iloc[0]
    assert call_row['dealer_position'] == -1
    
    # Put: Buy=50, Sell=100 -> Net Buy = -50 -> Dealer Long (1)
    put_row = book.data[(book.data['strike'] == 4000) & (book.data['type'] == 'put')].iloc[0]
    assert put_row['dealer_position'] == 1

def test_calculate_greeks(sample_option_data):
    book = DealerBook(sample_option_data, spot_price=4100)
    book.calculate_greeks()
    
    assert 'GEX' in book.data.columns
    assert 'net_vanna' in book.data.columns
    assert 'net_charm' in book.data.columns
    
    # Check GEX values are computed
    assert not book.data['GEX'].isnull().any()

def test_gamma_flip(sample_option_data):
    # Manipulate data to ensure a flip
    # Low strikes: Negative GEX (Dealer Short Calls, Long Puts)
    # High strikes: Positive GEX (Dealer Long Calls, Short Puts)
    
    # Let's force dealer position
    book = DealerBook(sample_option_data, spot_price=4100)
    book.estimate_inventory()
    book.calculate_greeks()
    
    # Manually set GEX to create a flip
    # Strike 4000: -100
    # Strike 4050: -50
    # Strike 4100: +50
    # Strike 4150: +100
    
    # Note: 'get_gex_by_strike' sums up GEX for call and put at same strike.
    
    # Let's mock the GEX column directly for testing find_gamma_flip_strike logic
    # We need to preserve the dataframe structure but change values
    
    # Create a simplified DataFrame for testing logic
    df = pd.DataFrame({
        'strike': [4000, 4050, 4100, 4150, 4200],
        'GEX': [-100, -50, 60, 100, 100]
    })
    
    # Mock the method get_gex_by_strike on the instance or subclass
    # Or just use the logic directly.
    # But let's try to adjust the data in the book.
    # We can just assign to book.data['GEX'] but we need to match strikes.
    
    # Easier: Just use the method logic
    gex_by_strike = df.set_index('strike')['GEX']
    cumsum = gex_by_strike.cumsum()
    # -100, -150, -90, 10, 110
    # Crosses zero between 4100 (-90) and 4150 (10).
    # Logic should return 4150.
    
    # Let's see how I implemented it:
    # crossings = np.where(diffs != 0)[0]
    # idx = crossings[0] -> index before flip.
    # return gex_by_strike.index[idx + 1]
    
    # Let's verify with the actual class method
    # We'll create a dummy book with this data
    book.data = df
    flip = book.find_gamma_flip_strike()
    
    # Cumsum: [-100, -150, -90, 10, 110]
    # Signs: [-1, -1, -1, 1, 1]
    # Diff: [0, 0, 2, 0]
    # Non-zero at index 2 (which corresponds to transition from 2nd to 3rd element of diff, i.e. index 2 to 3 of original?)
    # np.diff(signs)[2] is signs[3] - signs[2] = 1 - (-1) = 2.
    # crossings = [2]
    # idx = 2.
    # index[idx+1] = index[3] = 4150.
    
    assert flip == 4150
