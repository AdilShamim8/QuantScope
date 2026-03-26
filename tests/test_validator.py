import pytest
from core.validator import clean_symbol, clean_symbols, ValidationError


class TestSymbol:
    def test_valid(self):
        assert clean_symbol("aapl") == "AAPL"

    def test_suffix(self):
        assert clean_symbol("7203.t") == "7203.T"

    def test_empty(self):
        with pytest.raises(ValidationError):
            clean_symbol("")

    def test_injection(self):
        with pytest.raises(ValidationError):
            clean_symbol("AAPL; DROP TABLE")

    def test_too_long(self):
        with pytest.raises(ValidationError):
            clean_symbol("A" * 20)


class TestList:
    def test_basic(self):
        ok, bad = clean_symbols(["AAPL", "MSFT"])
        assert ok == ["AAPL", "MSFT"] and bad == []

    def test_rejects(self):
        ok, bad = clean_symbols(["AAPL", "!!!"])
        assert ok == ["AAPL"] and "!!!" in bad

    def test_empty(self):
        with pytest.raises(ValidationError):
            clean_symbols([])