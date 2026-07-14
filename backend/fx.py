"""FX + geolocation router.

Exposes:
    GET /api/fx/localize?base=NGN
        Detects the caller's country/currency from their IP, fetches a live
        FX rate from `base` -> detected currency, and returns everything in
        one round-trip. Result is cached in-process for 1 hour.

    GET /api/fx/rate?base=NGN&to=USD
        Returns just the FX rate between two currencies (cached 1h).

    GET /api/fx/currencies
        Curated list of currencies for the frontend selector dropdown.

No API keys required. Uses:
    - ipapi.co for IP geolocation
    - open.er-api.com for FX rates
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

fx_router = APIRouter(prefix="/api/fx", tags=["fx"])

# ---------------------------------------------------------------------------
# In-process caches (simple TTL). For multi-instance deployments swap for Redis.
# ---------------------------------------------------------------------------

_RATE_TTL = 60 * 60  # 1 hour
_GEO_TTL = 24 * 60 * 60  # 24 hours

_rate_cache: dict[str, tuple[float, float]] = {}  # key "BASE:TARGET" -> (rate, exp_ts)
_all_rates_cache: dict[str, tuple[dict[str, float], float]] = {}  # base -> (rates, exp_ts)
_geo_cache: dict[str, tuple[dict[str, Any], float]] = {}  # ip -> (payload, exp_ts)


CURATED_CURRENCIES: list[dict[str, str]] = [
    {"code": "NGN", "name": "Nigerian Naira", "symbol": "\u20a6"},
    {"code": "USD", "name": "US Dollar", "symbol": "$"},
    {"code": "EUR", "name": "Euro", "symbol": "\u20ac"},
    {"code": "GBP", "name": "British Pound", "symbol": "\u00a3"},
    {"code": "CAD", "name": "Canadian Dollar", "symbol": "$"},
    {"code": "AUD", "name": "Australian Dollar", "symbol": "$"},
    {"code": "INR", "name": "Indian Rupee", "symbol": "\u20b9"},
    {"code": "ZAR", "name": "South African Rand", "symbol": "R"},
    {"code": "KES", "name": "Kenyan Shilling", "symbol": "KSh"},
    {"code": "GHS", "name": "Ghanaian Cedi", "symbol": "\u20b5"},
    {"code": "UGX", "name": "Ugandan Shilling", "symbol": "USh"},
    {"code": "TZS", "name": "Tanzanian Shilling", "symbol": "TSh"},
    {"code": "XOF", "name": "West African CFA Franc", "symbol": "CFA"},
    {"code": "XAF", "name": "Central African CFA Franc", "symbol": "FCFA"},
    {"code": "EGP", "name": "Egyptian Pound", "symbol": "\u00a3"},
    {"code": "MAD", "name": "Moroccan Dirham", "symbol": "DH"},
    {"code": "AED", "name": "UAE Dirham", "symbol": "AED"},
    {"code": "SAR", "name": "Saudi Riyal", "symbol": "SR"},
    {"code": "JPY", "name": "Japanese Yen", "symbol": "\u00a5"},
    {"code": "CNY", "name": "Chinese Yuan", "symbol": "\u00a5"},
    {"code": "SGD", "name": "Singapore Dollar", "symbol": "$"},
    {"code": "HKD", "name": "Hong Kong Dollar", "symbol": "$"},
    {"code": "CHF", "name": "Swiss Franc", "symbol": "CHF"},
    {"code": "SEK", "name": "Swedish Krona", "symbol": "kr"},
    {"code": "NOK", "name": "Norwegian Krone", "symbol": "kr"},
    {"code": "DKK", "name": "Danish Krone", "symbol": "kr"},
    {"code": "BRL", "name": "Brazilian Real", "symbol": "R$"},
    {"code": "MXN", "name": "Mexican Peso", "symbol": "$"},
    {"code": "TRY", "name": "Turkish Lira", "symbol": "\u20ba"},
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _client_ip(request: Request) -> str | None:
    """Best-effort caller IP extraction, honouring common proxy headers."""
    xff = request.headers.get("x-forwarded-for") or request.headers.get("x-real-ip")
    if xff:
        # X-Forwarded-For can be a comma-separated list; the leftmost is the client.
        ip = xff.split(",")[0].strip()
        if ip:
            return ip
    client = request.client
    return client.host if client else None


async def _fetch_all_rates(base: str) -> dict[str, float]:
    """Return a dict of {currency: rate} with `base` as the base. Cached 1h."""
    now = time.time()
    cached = _all_rates_cache.get(base)
    if cached and cached[1] > now:
        return cached[0]

    url = f"https://open.er-api.com/v6/latest/{base}"
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("FX rate fetch failed for base=%s: %s", base, exc)
        # Return whatever we last had (even if stale), otherwise raise.
        if cached:
            return cached[0]
        raise HTTPException(status_code=502, detail="Failed to fetch FX rates") from exc

    rates = payload.get("rates")
    if not isinstance(rates, dict) or not rates:
        if cached:
            return cached[0]
        raise HTTPException(status_code=502, detail="Malformed FX response")

    _all_rates_cache[base] = (rates, now + _RATE_TTL)
    return rates


async def _fetch_geo(ip: str) -> dict[str, Any]:
    """Fetch geolocation for an IP. Cached 24h.

    Uses ip-api.com (free, keyless, ~45 req/min per public IP). Falls back
    to an empty dict on any error so callers can degrade gracefully.
    """
    now = time.time()
    cached = _geo_cache.get(ip)
    if cached and cached[1] > now:
        return cached[0]

    url = (
        f"http://ip-api.com/json/{ip}"
        "?fields=status,country,countryCode,currency,languages"
    )
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.info("Geo lookup failed for ip=%s: %s", ip, exc)
        return {}

    if not isinstance(payload, dict) or payload.get("status") != "success":
        return {}

    result = {
        "country_code": payload.get("countryCode") or None,
        "country_name": payload.get("country") or None,
        "currency": (payload.get("currency") or "").upper() or None,
        "languages": payload.get("languages") or None,
    }
    _geo_cache[ip] = (result, now + _GEO_TTL)
    return result


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@fx_router.get("/currencies")
async def list_currencies() -> dict[str, Any]:
    """Curated currency list for the frontend selector."""
    return {"currencies": CURATED_CURRENCIES}


@fx_router.get("/rate")
async def get_rate(base: str = "NGN", to: str = "USD") -> dict[str, Any]:
    """Return the FX rate from `base` to `to`. Cached 1h."""
    base = base.upper().strip()
    to = to.upper().strip()

    if base == to:
        return {"base": base, "target": to, "rate": 1.0, "cached": False}

    key = f"{base}:{to}"
    now = time.time()
    cached = _rate_cache.get(key)
    if cached and cached[1] > now:
        return {"base": base, "target": to, "rate": cached[0], "cached": True}

    rates = await _fetch_all_rates(base)
    rate = rates.get(to)
    if not rate or not isinstance(rate, (int, float)) or rate <= 0:
        raise HTTPException(
            status_code=404,
            detail=f"No FX rate available for {base}->{to}",
        )

    _rate_cache[key] = (float(rate), now + _RATE_TTL)
    return {"base": base, "target": to, "rate": float(rate), "cached": False}


@fx_router.get("/localize")
async def localize(request: Request, base: str = "NGN") -> dict[str, Any]:
    """One-shot endpoint: detects caller's currency + returns FX rate."""
    base = base.upper().strip()

    ip = _client_ip(request)
    geo: dict[str, Any] = {}
    if ip and not _is_private_ip(ip):
        geo = await _fetch_geo(ip)

    detected_currency = (geo.get("currency") or base).upper()
    country_code = geo.get("country_code")
    languages = geo.get("languages") or ""
    locale = languages.split(",")[0].replace("_", "-") if languages else None

    # Same currency -> rate 1
    if detected_currency == base:
        return {
            "base": base,
            "detected_currency": base,
            "country_code": country_code,
            "locale": locale,
            "rate": 1.0,
            "source": "geo" if geo else "fallback",
        }

    rate: float = 1.0
    used_currency = detected_currency
    try:
        rates = await _fetch_all_rates(base)
        found = rates.get(detected_currency)
        if found and isinstance(found, (int, float)) and found > 0:
            rate = float(found)
        else:
            # No rate for detected currency -> fall back to base
            used_currency = base
            rate = 1.0
    except HTTPException:
        used_currency = base
        rate = 1.0

    return {
        "base": base,
        "detected_currency": used_currency,
        "country_code": country_code,
        "locale": locale,
        "rate": rate,
        "source": "geo" if geo else "fallback",
    }


def _is_private_ip(ip: str) -> bool:
    """Skip geolocation for LAN / loopback addresses (dev environments)."""
    try:
        import ipaddress

        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return True
