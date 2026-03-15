"""Currency exchange rate utilities.

Fetches daily exchange rates from a public API, caches them for the current
UTC day, and provides conversion helpers.  Falls back to cached data when
the network is unavailable.

Cache location: ``runtime/cache/exchange_rates.json``
"""

import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CACHE_DIR = _PROJECT_ROOT / "runtime" / "cache"
_CACHE_FILE = _CACHE_DIR / "exchange_rates.json"

_API_URL = "https://open.er-api.com/v6/latest/USD"

_mem_cache: Optional[Dict] = None


def _utc_date_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_cache() -> Optional[Dict]:
    global _mem_cache
    if _mem_cache:
        return _mem_cache
    if _CACHE_FILE.exists():
        try:
            with open(_CACHE_FILE, encoding="utf-8") as f:
                data = json.load(f)
            _mem_cache = data
            return data
        except Exception:
            return None
    return None


def _save_cache(data: Dict):
    global _mem_cache
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    _mem_cache = data


def _fetch_rates() -> Optional[Dict]:
    """Fetch rates from open.er-api.com (free, no key required)."""
    try:
        req = urllib.request.Request(_API_URL, headers={"User-Agent": "AITerminalTools/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        if raw.get("result") != "success":
            return None
        return raw.get("rates", {})
    except Exception:
        return None


def get_rates(force_refresh: bool = False) -> Dict[str, float]:
    """Return a dict of currency → USD exchange rates.

    Fetches from the network at most once per UTC day.  On failure, returns
    the most recent cached rates.  If no cache exists either, returns a
    minimal fallback with CNY≈7.25.

    Args:
        force_refresh: If True, bypass the daily cache and fetch fresh rates.

    Returns:
        ``{"USD": 1.0, "CNY": 7.25, ...}``
    """
    today = _utc_date_str()
    cached = _load_cache()

    if cached and cached.get("date") == today and not force_refresh:
        return cached.get("rates", {})

    rates = _fetch_rates()
    if rates:
        payload = {"date": today, "timestamp": time.time(), "rates": rates}
        _save_cache(payload)
        return rates

    if cached and cached.get("rates"):
        return cached["rates"]

    return {"USD": 1.0, "CNY": 7.25, "EUR": 0.92, "GBP": 0.79, "JPY": 149.5}


def to_usd(amount: float, currency: str, rates: Optional[Dict] = None) -> float:
    """Convert *amount* in *currency* to USD.

    Args:
        amount: The monetary amount.
        currency: ISO 4217 code (e.g. ``"CNY"``, ``"EUR"``).
        rates: Optional pre-fetched rates dict.  If ``None``, calls
               :func:`get_rates`.

    Returns:
        The equivalent USD amount.
    """
    currency = currency.upper()
    if currency == "USD":
        return amount
    if rates is None:
        rates = get_rates()
    rate = rates.get(currency)
    if not rate:
        return amount
    return amount / rate


def get_rate(currency: str, rates: Optional[Dict] = None) -> float:
    """Return how many units of *currency* equal 1 USD.

    Returns ``1.0`` if the currency is unknown.
    """
    currency = currency.upper()
    if currency == "USD":
        return 1.0
    if rates is None:
        rates = get_rates()
    return rates.get(currency, 1.0)


def convert(amount: float, from_currency: str, to_currency: str,
            rates: Optional[Dict] = None) -> float:
    """Convert *amount* from one currency to another."""
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    if from_currency == to_currency:
        return amount
    if rates is None:
        rates = get_rates()
    usd = to_usd(amount, from_currency, rates)
    to_rate = rates.get(to_currency, 1.0)
    return usd * to_rate


_CURRENCY_PRECISION: Dict[str, int] = {
    "BTC": 8, "ETH": 6,
    "USD": 2, "EUR": 2, "GBP": 2, "CNY": 2, "AUD": 2, "CAD": 2,
    "CHF": 2, "SGD": 2, "NZD": 2, "HKD": 2, "SEK": 2, "NOK": 2,
    "DKK": 2, "MXN": 2, "BRL": 2, "ZAR": 2, "INR": 2, "THB": 2,
    "MYR": 2, "PHP": 2, "PLN": 2, "CZK": 2, "HUF": 0,
    "JPY": 0, "KRW": 0, "TWD": 0, "CLP": 0, "ISK": 0,
    "IDR": -1, "VND": -1, "IRR": -1, "LAK": -1, "UGX": -1,
    "MMK": -1, "GNF": -1, "PYG": -1,
}

_CURRENCY_SYMBOLS: Dict[str, str] = {
    "USD": "$", "EUR": "\u20ac", "GBP": "\u00a3", "JPY": "\u00a5",
    "CNY": "\u00a5", "KRW": "\u20a9", "INR": "\u20b9", "RUB": "\u20bd",
    "THB": "\u0e3f", "BRL": "R$", "TRY": "\u20ba", "PLN": "z\u0142",
    "CZK": "K\u010d", "SEK": "kr", "NOK": "kr", "DKK": "kr",
    "HKD": "HK$", "SGD": "S$", "AUD": "A$", "CAD": "C$", "NZD": "NZ$",
    "CHF": "CHF", "ZAR": "R", "MXN": "MX$", "MYR": "RM",
    "IDR": "Rp", "PHP": "\u20b1", "VND": "\u20ab", "TWD": "NT$",
    "BTC": "\u20bf", "ETH": "\u039e",
}

_CURRENCY_NAMES: Dict[str, str] = {
    "USD": "US Dollar", "EUR": "Euro", "GBP": "British Pound",
    "JPY": "Japanese Yen", "CNY": "Chinese Yuan", "KRW": "Korean Won",
    "INR": "Indian Rupee", "RUB": "Russian Ruble", "BRL": "Brazilian Real",
    "CAD": "Canadian Dollar", "AUD": "Australian Dollar", "CHF": "Swiss Franc",
    "HKD": "Hong Kong Dollar", "SGD": "Singapore Dollar", "TWD": "Taiwan Dollar",
    "THB": "Thai Baht", "MXN": "Mexican Peso", "SEK": "Swedish Krona",
    "NOK": "Norwegian Krone", "DKK": "Danish Krone", "PLN": "Polish Zloty",
    "CZK": "Czech Koruna", "HUF": "Hungarian Forint", "TRY": "Turkish Lira",
    "ZAR": "South African Rand", "NZD": "New Zealand Dollar",
    "MYR": "Malaysian Ringgit", "PHP": "Philippine Peso",
    "IDR": "Indonesian Rupiah", "VND": "Vietnamese Dong",
    "BTC": "Bitcoin", "ETH": "Ethereum",
}


def get_precision(currency: str) -> int:
    """Return the display decimal precision for a currency.

    Positive: digits after decimal point (e.g. 2 → ``$1.23``).
    Zero: no decimals (e.g. ``¥123``).
    Negative: round to powers of 10 (e.g. −1 → ``Rp 12,340``).
    """
    return _CURRENCY_PRECISION.get(currency.upper(), 2)


def get_symbol(currency: str) -> str:
    """Return the symbol for a currency (e.g. ``"$"``, ``"¥"``)."""
    return _CURRENCY_SYMBOLS.get(currency.upper(), currency.upper())


def get_currency_name(currency: str) -> str:
    """Return the English name for a currency code."""
    return _CURRENCY_NAMES.get(currency.upper(), currency.upper())


def format_price(amount: float, currency: str) -> str:
    """Format a monetary amount with appropriate precision and symbol.

    Examples::

        >>> format_price(1.2345, "USD")
        '$1.23'
        >>> format_price(149.5, "JPY")
        '¥150'
        >>> format_price(15600, "IDR")
        'Rp15,600'
    """
    currency = currency.upper()
    sym = get_symbol(currency)
    prec = get_precision(currency)
    if prec < 0:
        factor = 10 ** (-prec)
        rounded = round(amount / factor) * factor
        return f"{sym}{rounded:,.0f}"
    return f"{sym}{amount:,.{prec}f}"


def list_currencies(rates: Optional[Dict] = None) -> list:
    """Return a list of available currency info dicts, sorted by code.

    Each dict: ``{"code": "USD", "name": "US Dollar", "symbol": "$", "precision": 2}``
    """
    if rates is None:
        rates = get_rates()
    result = []
    for code in sorted(rates.keys()):
        result.append({
            "code": code,
            "name": get_currency_name(code),
            "symbol": get_symbol(code),
            "precision": get_precision(code),
        })
    return result
