import pandas as pd
import numpy as np
import scipy.signal as signal
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

# Load the data
df = pd.read_csv('combined_ohlc_data.csv', parse_dates=['Date'], index_col='Date')


# Strategy to trade based on support and resistance
class SupportResistanceStrategy(Strategy):

    def identify_resistance_levels(self, high_prices, distance=60, prominence=20):
        # Find peaks in the 'high' price data
        peaks, _ = signal.find_peaks(high_prices, distance=distance, prominence=prominence)
        # Use numpy-style indexing instead of iloc
        peak_values = high_prices[peaks].tolist()
        return peaks, peak_values

    def identify_support_levels(self, low_prices, distance=60, prominence=20):
        # Find troughs (peaks of the negative low prices)
        troughs, _ = signal.find_peaks(-low_prices, distance=distance, prominence=prominence)
        # Use numpy-style indexing instead of iloc
        trough_values = low_prices[troughs].tolist()
        return troughs, trough_values

    def is_level_valid(self, current_index, level_index, expiry_period):
        # Check if the level is within the expiry period
        if (current_index - level_index) <= expiry_period:
            return True
        return False

    def merge_levels(self, levels, threshold=20):
        # Sort and merge levels that are within a certain threshold
        levels = sorted(levels)
        merged = []
        current_bin = [levels[0]]

        for i in range(1, len(levels)):
            # If the current level is within the threshold of the last merged level, add it to the current bin
            if levels[i] - current_bin[-1] < threshold:
                current_bin.append(levels[i])
            else:
                # If the level is far from the current bin, add the mean of the current bin to the merged levels
                merged.append(np.mean(current_bin))
                current_bin = [levels[i]]

        # Add the last bin's mean value
        merged.append(np.mean(current_bin))
        return merged

    def init(self):
        # Calculate initial resistance and support levels
        self.resistance_indices, self.resistance_levels = self.identify_resistance_levels(self.data.High, distance=60, prominence=20)
        self.support_indices, self.support_levels = self.identify_support_levels(self.data.Low, distance=60, prominence=20)

        # Merge levels based on threshold
        self.resistance_levels = self.merge_levels(self.resistance_levels, threshold=20)
        self.support_levels = self.merge_levels(self.support_levels, threshold=20)

        # Store Exponential Moving Averages
        self.EMA_Slow = self.I(talib.EMA, self.data.Close, 50)
        self.EMA_Fast = self.I(talib.EMA, self.data.Close, 30)

        # Define how many candles the levels should be valid for
        self.expiry_period = 20

        # Track valid levels within the expiry period
        self.valid_support_levels = []
        self.valid_resistance_levels = []

    def next(self):
        current_price = self.data.Close[-1]
        current_index = len(self.data) - 1  # Current index in the dataframe
        


# Backtest
if __name__ == '__main__':
    bt = Backtest(df, SupportResistanceStrategy, cash=50_000, commission=.002)
    stats = bt.run()

    print(stats)
