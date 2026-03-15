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
