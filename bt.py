from backtesting import Backtest, Strategy
import talib
import pandas as pd

# Load data
df = pd.read_csv('combined_ohlc_data.csv', parse_dates=['Date'], index_col='Date')


# Define custom indicators
def MACD(close, n1, n2, ns):
    macd, macdsignal, macdhist = talib.MACD(close, fastperiod=n1, slowperiod=n2, signalperiod=ns)
    return macd, macdsignal


def STOCH(high, low, close):
    slowk, slowd = talib.STOCH(high, low, close, fastk_period=14, slowk_period=12, slowk_matype=0, slowd_period=3,
                               slowd_matype=0)
    return slowk, slowd


def VWAP(hi, lo, cls, vol):
    VWAP = (((hi + lo + cls) / 3) * vol).cumsum() / vol.cumsum()
    return VWAP


def atr(high, low, close):
    atr = talib.ATR(high, low, close, 7)
    return atr


# Calculate indicators
df["EMA_Slow"] = talib.EMA(df.Close, 50)
df["EMA_Fast"] = talib.EMA(df.Close, 30)
df['ATR'] = talib.ATR(df.High, df.Low, df.Close, 7)

bband = talib.BBANDS(df.Close, timeperiod=15, nbdevup=1.5, nbdevdn=2, matype=0)
bband_df = pd.DataFrame({
    'Upper_BB': bband[0],
    'Middle_BB': bband[1],
    'Lower_BB': bband[2]
}, index=df.index)
df = df.join(bband_df)


# Function for EMA crossover signal
def emasignal(close, current_index, backcandles=6):
    start_index = max(0, current_index - backcandles)
    slow_ema = close["EMA_Slow"][start_index:current_index]
    fast_ema = close["EMA_Fast"][start_index:current_index]
    signal = 0
    if all(f > s for f, s in zip(fast_ema, slow_ema)):
        signal = 1
    elif all(s > f for f, s in zip(fast_ema, slow_ema)):
        signal = 2
    return signal


# Function for the combined signals
def total_signal(df, current_candle, backcandles):
    if (emasignal(df, current_candle, backcandles) == 2 and df.Close[current_candle] <= df['Lower_BB'][current_candle]):
        return 2
    if (emasignal(df, current_candle, backcandles) == 1 and df.Close[current_candle] >= df['Upper_BB'][current_candle]):
        return 1
    else:
        return 0


df["EMABBSignal"] = [total_signal(df, i, 6) for i in range(len(df))]


# Define the strategy
class Main(Strategy):
    slcoef = 43  # Reduced risk per trade
    TPSLRatio = 1.5  # Adjusted risk-to-reward ratio
    limit = 66
    size = 50000

    def init(self):
        self.emabbsignal = self.I(lambda: df.EMABBSignal)
        self.RSI = self.I(talib.RSI, self.data.Close, 14)
        self.ATR = self.I(atr, self.data.High, self.data.Low, self.data.Close)
        self.macd, self.macd_signal = self.I(MACD, self.data.Close, 12, 26, 9)

    def next(self):
        slatr = self.slcoef * self.data.ATR[-1]
        TPSLRatio = self.TPSLRatio

        # Buying conditions
        if self.emabbsignal[-1] == 2 and len(self.trades) == 0 and self.RSI[-1] < self.limit and self.macd[-1] > \
                self.macd_signal[-1]:
            sl1 = self.data.Close[-1] - slatr
            tp1 = self.data.Close[-1] + slatr * TPSLRatio
            self.buy(sl=sl1, tp=tp1)

        # Selling conditions
        elif self.emabbsignal[-1] == 1 and len(self.trades) == 0 and self.RSI[-1] > self.limit and self.macd[-1] < \
                self.macd_signal[-1]:
            sl2 = self.data.Close[-1] + slatr
            tp2 = self.data.Close[-1] - slatr * TPSLRatio
            self.sell(sl=sl2, tp=tp2)


# Run the backtest with optimization
if __name__ == '__main__':
    bt = Backtest(df, Main, cash=50_000)
    #stats = bt.optimize(TPSLRatio=[i for i in range(1, 10)], maximize='Return [%]')
    stats=bt.run()
    bt.plot()
    print(stats)

