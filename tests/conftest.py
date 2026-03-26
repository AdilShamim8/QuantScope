import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def prices_df():
    np.random.seed(42)
    n = 252
    dates = pd.bdate_range("2023-01-03", periods=n)
    ret = np.random.normal(0.0005, 0.02, n)
    close = 150 * np.cumprod(1 + ret)
    return pd.DataFrame({
        "Open": close * (1 + np.random.uniform(-0.01, 0.01, n)),
        "High": close * (1 + np.random.uniform(0, 0.02, n)),
        "Low": close * (1 - np.random.uniform(0, 0.02, n)),
        "Close": close,
        "Volume": np.random.randint(1_000_000, 50_000_000, n),
    }, index=dates)