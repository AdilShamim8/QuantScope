from core.query_parser import parse


class TestTickers:
    def test_comma(self):
        assert parse("AAPL, MSFT").symbols == ["AAPL", "MSFT"]

    def test_space(self):
        assert parse("AAPL MSFT NVDA").symbols == ["AAPL", "MSFT", "NVDA"]

    def test_suffix(self):
        r = parse("7203.T, VOD.L")
        assert "7203.T" in r.symbols
        assert "VOD.L" in r.symbols

    def test_dedup(self):
        assert parse("AAPL, AAPL").symbols == ["AAPL"]


class TestNatural:
    def test_apple(self):
        r = parse("analyze Apple stock")
        assert "AAPL" in r.symbols and r.is_nl

    def test_compare(self):
        r = parse("compare Tesla and Nvidia")
        assert "TSLA" in r.symbols and "NVDA" in r.symbols
        assert r.intent == "compare"

    def test_buy(self):
        r = parse("should I buy Apple?")
        assert "AAPL" in r.symbols
        assert r.intent == "investment_question"

    def test_toyota(self):
        assert "7203.T" in parse("How is Toyota?").symbols

    def test_reliance(self):
        assert "RELIANCE.NS" in parse("Tell me about Reliance").symbols

    def test_samsung(self):
        assert "005930.KS" in parse("Samsung stock").symbols

    def test_empty(self):
        assert parse("").symbols == []

    def test_nonsense(self):
        assert parse("weather is nice").symbols == []

    def test_preserves(self):
        assert parse("Buy Tesla?").query == "Buy Tesla?"