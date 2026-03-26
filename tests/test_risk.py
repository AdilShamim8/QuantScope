import numpy as np
import pandas as pd
from core import risk


class TestPosition:
    def test_basic(self):
        r = risk.position_size(10000, 150, 5)
        assert r["shares"] > 0 and r["stop_loss_price"] < 150

    def test_cap(self):
        r = risk.position_size(10000, 10, 0.01)
        assert r["position_value"] <= 1010

    def test_zero_atr(self):
        assert risk.position_size(10000, 150, 0)["shares"] == 0


class TestSharpe:
    def test_positive(self):
        r = pd.Series(np.random.normal(0.001, 0.01, 252))
        assert risk.sharpe(r) > 0

    def test_empty(self):
        assert risk.sharpe(pd.Series(dtype=float)) == 0.0


class TestDrawdown:
    def test_known(self):
        dd, _, _ = risk.max_drawdown(pd.Series([100, 50, 60]))
        assert dd == -50.0

    def test_monotonic(self):
        dd, _, _ = risk.max_drawdown(pd.Series([100, 101, 102]))
        assert dd == 0.0