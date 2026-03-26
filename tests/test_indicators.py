import numpy as np
import pandas as pd
from core import indicators


class TestRSI:
    def test_range(self, prices_df):
        r = indicators.rsi(prices_df["Close"]).dropna()
        assert r.min() >= 0 and r.max() <= 100

    def test_up(self):
        assert indicators.rsi(pd.Series(range(100, 200)), 14).iloc[-1] > 90

    def test_down(self):
        assert indicators.rsi(pd.Series(range(200, 100, -1)), 14).iloc[-1] < 10


class TestMACD:
    def test_three(self, prices_df):
        assert len(indicators.macd(prices_df["Close"])) == 3

    def test_hist(self, prices_df):
        ml, ms, mh = indicators.macd(prices_df["Close"])
        np.testing.assert_array_almost_equal(
            (ml - ms).dropna().values[-50:], mh.dropna().values[-50:])


class TestAnalyze:
    def test_keys(self, prices_df):
        r = indicators.analyze("TEST", prices_df)
        assert r is not None
        for k in ["symbol", "price", "rsi", "composite_score", "signals", "returns"]:
            assert k in r

    def test_score_range(self, prices_df):
        r = indicators.analyze("TEST", prices_df)
        assert -5 <= r["composite_score"] <= 5

    def test_short_data(self):
        df = pd.DataFrame({"Open": [100]*50, "High": [101]*50,
                           "Low": [99]*50, "Close": [100]*50, "Volume": [1e6]*50})
        assert indicators.analyze("X", df) is None