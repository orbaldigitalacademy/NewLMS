"""
FX conversion and IP-based currency localization router.

Endpoints
---------
GET /api/fx/localize?base=NGN
    Detect the visitor's country and currency from their IP address, then
    return the FX rate from the base currency to the detected currency.

GET /api/fx/rate?base=NGN&to=USD
    Return the current FX rate between two supported currencies.

GET /api/fx/currencies
    Return the curated list of currencies supported by the frontend selector.

External services
-----------------
IP geolocation:
    https://ipapi.co

Foreign exchange rates:
    https://open.er-api.com

No API keys are required for these endpoints.

Important
---------
Localized prices should normally be treated as display estimates only.
The authoritative course price and payment amount should continue to come
from the database in the LMS base currency, such as NGN.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, status

logger = logging.getLogger(__name__)

# Because this router already includes /api, mount it with:
#
#     app.include_router(fx_router)
#
# Do not add prefix="/api" again when mounting it.
fx_router = APIRouter(prefix="/api/fx", tags=["fx"])


# =============================================================================
# Configuration
# =============================================================================

RATE_TTL_SECONDS = 60 * 60
GEO_TTL_SECONDS = 24 * 60 * 60

FX_REQUEST_TIMEOUT = 8.0
GEO_REQUEST_TIMEOUT = 6.0

MAX_GEO_CACHE_ENTRIES = 5_000

DEFAULT_BASE_CURRENCY = "NGN"
DEFAULT_LOCALE = "en-NG"

CURRENCY_CODE_PATTERN = re.compile(r"^[A-Z]{3}$")


# =============================================================================
# Supported currencies
# =============================================================================

CURATED_CURRENCIES: list[dict[str, str]] = [
    {
        "code": "NGN",
        "name": "Nigerian Naira",
        "symbol": "₦",
        "default_locale": "en-NG",
    },
    {
        "code": "USD",
        "name": "US Dollar",
        "symbol": "$",
        "default_locale": "en-US",
    },
    {
        "code": "EUR",
        "name": "Euro",
        "symbol": "€",
        "default_locale": "en-IE",
    },
    {
        "code": "GBP",
        "name": "British Pound",
        "symbol": "£",
        "default_locale": "en-GB",
    },
    {
        "code": "CAD",
        "name": "Canadian Dollar",
        "symbol": "$",
        "default_locale": "en-CA",
    },
    {
        "code": "AUD",
        "name": "Australian Dollar",
        "symbol": "$",
        "default_locale": "en-AU",
    },
    {
        "code": "INR",
        "name": "Indian Rupee",
        "symbol": "₹",
        "default_locale": "en-IN",
    },
    {
        "code": "ZAR",
        "name": "South African Rand",
        "symbol": "R",
        "default_locale": "en-ZA",
    },
    {
        "code": "KES",
        "name": "Kenyan Shilling",
        "symbol": "KSh",
        "default_locale": "en-KE",
    },
    {
        "code": "GHS",
        "name": "Ghanaian Cedi",
        "symbol": "₵",
        "default_locale": "en-GH",
    },
    {
        "code": "UGX",
        "name": "Ugandan Shilling",
        "symbol": "USh",
        "default_locale": "en-UG",
    },
    {
        "code": "TZS",
        "name": "Tanzanian Shilling",
        "symbol": "TSh",
        "default_locale": "en-TZ",
    },
    {
        "code": "XOF",
        "name": "West African CFA Franc",
        "symbol": "CFA",
        "default_locale": "fr-SN",
    },
    {
        "code": "XAF",
        "name": "Central African CFA Franc",
        "symbol": "FCFA",
        "default_locale": "fr-CM",
    },
    {
        "code": "EGP",
        "name": "Egyptian Pound",
        "symbol": "E£",
        "default_locale": "ar-EG",
    },
    {
        "code": "MAD",
        "name": "Moroccan Dirham",
        "symbol": "DH",
        "default_locale": "ar-MA",
    },
    {
        "code": "AED",
        "name": "UAE Dirham",
        "symbol": "AED",
        "default_locale": "ar-AE",
    },
    {
        "code": "SAR",
        "name": "Saudi Riyal",
        "symbol": "SAR",
        "default_locale": "ar-SA",
    },
    {
        "code": "JPY",
        "name": "Japanese Yen",
        "symbol": "¥",
        "default_locale": "ja-JP",
    },
    {
        "code": "CNY",
        "name": "Chinese Yuan",
        "symbol": "¥",
        "default_locale": "zh-CN",
    },
    {
        "code": "SGD",
        "name": "Singapore Dollar",
        "symbol": "$",
        "default_locale": "en-SG",
    },
    {
        "code": "HKD",
        "name": "Hong Kong Dollar",
        "symbol": "$",
        "default_locale": "en-HK",
    },
    {
        "code": "CHF",
        "name": "Swiss Franc",
        "symbol": "CHF",
        "default_locale": "de-CH",
    },
    {
        "code": "SEK",
        "name": "Swedish Krona",
        "symbol": "kr",
        "default_locale": "sv-SE",
    },
    {
        "code": "NOK",
        "name": "Norwegian Krone",
        "symbol": "kr",
        "default_locale": "nb-NO",
    },
    {
        "code": "DKK",
        "name": "Danish Krone",
        "symbol": "kr",
        "default_locale": "da-DK",
    },
    {
        "code": "BRL",
        "name": "Brazilian Real",
        "symbol": "R$",
        "default_locale": "pt-BR",
    },
    {
        "code": "MXN",
        "name": "Mexican Peso",
        "symbol": "$",
        "default_locale": "es-MX",
    },
    {
        "code": "TRY",
        "name": "Turkish Lira",
        "symbol": "₺",
        "default_locale": "tr-TR",
    },
]

SUPPORTED_CURRENCIES = {
    currency["code"] for currency in CURATED_CURRENCIES
}

CURRENCY_METADATA = {
    currency["code"]: currency for currency in CURATED_CURRENCIES
}


# =============================================================================
# In-process caches
# =============================================================================

# "BASE:TARGET" -> (rate, expiry timestamp)
_rate_cache: dict[str, tuple[float, float]] = {}

# "BASE" -> (all rates, expiry timestamp)
_all_rates_cache: dict[str, tuple[dict[str, float], float]] = {}

# "IP" -> (geolocation result, expiry timestamp)
_geo_cache: dict[str, tuple[dict[str, Any], float]] = {}

# Prevent multiple simultaneous requests from fetching the same information.
_rates_lock = asyncio.Lock()
_geo_lock = asyncio.Lock()


# =============================================================================
# Validation and normalization helpers
# =============================================================================

def _normalize_currency(
    value: str,
    *,
    field_name: str,
    require_curated: bool = True,
) -> str:
    """
    Normalize and validate an ISO-style three-letter currency code.
    """
    code = value.strip().upper()

    if not CURRENCY_CODE_PATTERN.fullmatch(code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} currency code.",
        )

    if require_curated and code not in SUPPORTED_CURRENCIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported {field_name} currency: {code}.",
        )

    return code


def _normalize_locale(value: str | None) -> str | None:
    """
    Convert locale values such as en_US to en-US.
    """
    if not value:
        return None

    first_locale = value.split(",")[0].strip()

    if not first_locale:
        return None

    return first_locale.replace("_", "-")


def _default_locale_for_currency(currency: str) -> str:
    """
    Return the configured default locale for a supported currency.
    """
    metadata = CURRENCY_METADATA.get(currency, {})

    return metadata.get("default_locale", DEFAULT_LOCALE)


def _currency_symbol(currency: str) -> str:
    """
    Return the configured display symbol for a supported currency.
    """
    metadata = CURRENCY_METADATA.get(currency, {})

    return metadata.get("symbol", currency)


# =============================================================================
# IP helpers
# =============================================================================

def _valid_ip(value: str | None) -> str | None:
    """
    Return a normalized IP address or None when invalid.
    """
    if not value:
        return None

    candidate = value.strip()

    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def _client_ip(request: Request) -> str | None:
    """
    Best-effort client IP extraction.

    Reverse proxies may add one or more of these headers. Every extracted
    value is validated before it is used.

    The order prioritizes common platform-controlled client-IP headers.
    """
    candidates: list[str | None] = [
        request.headers.get("cf-connecting-ip"),
        request.headers.get("true-client-ip"),
        request.headers.get("x-real-ip"),
    ]

    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        # X-Forwarded-For may contain:
        # client, proxy-1, proxy-2
        #
        # The leftmost valid value is normally the original client.
        forwarded_candidates = [
            item.strip()
            for item in forwarded_for.split(",")
            if item.strip()
        ]

        candidates.extend(forwarded_candidates)

    if request.client:
        candidates.append(request.client.host)

    for candidate in candidates:
        valid = _valid_ip(candidate)

        if valid:
            return valid

    return None


def _is_non_public_ip(ip: str) -> bool:
    """
    Return True for private, loopback, reserved, multicast, link-local,
    or otherwise non-global addresses.
    """
    try:
        address = ipaddress.ip_address(ip)

        return not address.is_global
    except ValueError:
        return True


# =============================================================================
# Cache helpers
# =============================================================================

def _remove_expired_cache_entries() -> None:
    """
    Remove expired items from all in-process caches.
    """
    now = time.time()

    expired_rate_keys = [
        key
        for key, (_, expires_at) in _rate_cache.items()
        if expires_at <= now
    ]

    for key in expired_rate_keys:
        _rate_cache.pop(key, None)

    expired_all_rate_keys = [
        key
        for key, (_, expires_at) in _all_rates_cache.items()
        if expires_at <= now
    ]

    for key in expired_all_rate_keys:
        _all_rates_cache.pop(key, None)

    expired_geo_keys = [
        key
        for key, (_, expires_at) in _geo_cache.items()
        if expires_at <= now
    ]

    for key in expired_geo_keys:
        _geo_cache.pop(key, None)


def _trim_geo_cache() -> None:
    """
    Prevent the IP geolocation cache from growing indefinitely.
    """
    if len(_geo_cache) <= MAX_GEO_CACHE_ENTRIES:
        return

    sorted_entries = sorted(
        _geo_cache.items(),
        key=lambda item: item[1][1],
    )

    entries_to_remove = len(_geo_cache) - MAX_GEO_CACHE_ENTRIES

    for ip, _ in sorted_entries[:entries_to_remove]:
        _geo_cache.pop(ip, None)


# =============================================================================
# FX service
# =============================================================================

async def _fetch_all_rates(base: str) -> dict[str, float]:
    """
    Return all available rates for a base currency.

    Fresh values are cached for one hour. If the external service fails and
    an expired cached response exists, the expired response is used as a
    stale fallback.
    """
    now = time.time()
    cached = _all_rates_cache.get(base)

    if cached and cached[1] > now:
        return cached[0]

    async with _rates_lock:
        # Another request may have populated the cache while this request
        # waited for the lock.
        now = time.time()
        cached = _all_rates_cache.get(base)

        if cached and cached[1] > now:
            return cached[0]

        url = f"https://open.er-api.com/v6/latest/{base}"

        try:
            async with httpx.AsyncClient(
                timeout=FX_REQUEST_TIMEOUT,
                follow_redirects=True,
            ) as client:
                response = await client.get(
                    url,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "OrbalAcademy-LMS/1.0",
                    },
                )

                response.raise_for_status()
                payload = response.json()

        except (
            httpx.HTTPError,
            ValueError,
            TypeError,
        ) as exc:
            logger.warning(
                "FX rate request failed for base=%s: %s",
                base,
                exc,
            )

            if cached:
                logger.warning(
                    "Using stale FX cache for base=%s",
                    base,
                )

                return cached[0]

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The currency conversion service is temporarily unavailable.",
            ) from exc

        if not isinstance(payload, dict):
            if cached:
                return cached[0]

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The currency conversion service returned an invalid response.",
            )

        result_status = payload.get("result")

        if result_status and result_status != "success":
            logger.warning(
                "FX provider returned unsuccessful result for base=%s: %s",
                base,
                result_status,
            )

            if cached:
                return cached[0]

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The currency conversion service could not process the request.",
            )

        raw_rates = payload.get("rates")

        if not isinstance(raw_rates, dict) or not raw_rates:
            if cached:
                return cached[0]

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The currency conversion service returned no exchange rates.",
            )

        clean_rates: dict[str, float] = {}

        for currency_code, raw_rate in raw_rates.items():
            if not isinstance(currency_code, str):
                continue

            normalized_code = currency_code.strip().upper()

            if not CURRENCY_CODE_PATTERN.fullmatch(normalized_code):
                continue

            if isinstance(raw_rate, bool):
                continue

            if isinstance(raw_rate, (int, float)) and raw_rate > 0:
                clean_rates[normalized_code] = float(raw_rate)

        if not clean_rates:
            if cached:
                return cached[0]

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="No valid exchange rates were returned.",
            )

        # Ensure the base currency always converts to itself.
        clean_rates[base] = 1.0

        _all_rates_cache[base] = (
            clean_rates,
            now + RATE_TTL_SECONDS,
        )

        return clean_rates


async def _get_exchange_rate(
    base: str,
    target: str,
) -> tuple[float, bool]:
    """
    Return an exchange rate and whether the individual rate cache was used.
    """
    if base == target:
        return 1.0, False

    cache_key = f"{base}:{target}"
    now = time.time()
    cached = _rate_cache.get(cache_key)

    if cached and cached[1] > now:
        return cached[0], True

    rates = await _fetch_all_rates(base)
    rate = rates.get(target)

    if (
        isinstance(rate, bool)
        or not isinstance(rate, (int, float))
        or rate <= 0
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No FX rate is available for {base} to {target}.",
        )

    normalized_rate = float(rate)

    _rate_cache[cache_key] = (
        normalized_rate,
        now + RATE_TTL_SECONDS,
    )

    return normalized_rate, False


# =============================================================================
# Geolocation service
# =============================================================================

async def _fetch_geo(ip: str) -> dict[str, Any]:
    """
    Retrieve country, currency, and locale information for a public IP.

    Results are cached for 24 hours. Errors return an empty dictionary so
    localization can safely fall back to the LMS base currency.
    """
    now = time.time()
    cached = _geo_cache.get(ip)

    if cached and cached[1] > now:
        return cached[0]

    async with _geo_lock:
        now = time.time()
        cached = _geo_cache.get(ip)

        if cached and cached[1] > now:
            return cached[0]

        url = f"https://ipapi.co/{ip}/json/"

        try:
            async with httpx.AsyncClient(
                timeout=GEO_REQUEST_TIMEOUT,
                follow_redirects=True,
            ) as client:
                response = await client.get(
                    url,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "OrbalAcademy-LMS/1.0",
                    },
                )

                response.raise_for_status()
                payload = response.json()

        except (
            httpx.HTTPError,
            ValueError,
            TypeError,
        ) as exc:
            logger.info(
                "IP geolocation failed for ip=%s: %s",
                ip,
                exc,
            )

            if cached:
                return cached[0]

            return {}

        if not isinstance(payload, dict):
            return cached[0] if cached else {}

        if payload.get("error"):
            logger.info(
                "IP geolocation provider rejected ip=%s: %s",
                ip,
                payload.get("reason") or payload.get("message"),
            )

            return cached[0] if cached else {}

        country_code = payload.get("country_code")
        country_name = payload.get("country_name")
        currency = payload.get("currency")
        languages = payload.get("languages")

        normalized_country_code = (
            str(country_code).strip().upper()
            if country_code
            else None
        )

        normalized_currency = (
            str(currency).strip().upper()
            if currency
            else None
        )

        # A detected currency outside the curated list is retained in the
        # raw result, but /localize will safely fall back to the base currency.
        result: dict[str, Any] = {
            "country_code": normalized_country_code,
            "country_name": (
                str(country_name).strip()
                if country_name
                else None
            ),
            "currency": normalized_currency,
            "languages": (
                str(languages).strip()
                if languages
                else None
            ),
        }

        _geo_cache[ip] = (
            result,
            now + GEO_TTL_SECONDS,
        )

        _trim_geo_cache()

        return result


# =============================================================================
# API endpoints
# =============================================================================

@fx_router.get("/currencies")
async def list_currencies() -> dict[str, Any]:
    """
    Return currencies available in the frontend currency selector.
    """
    return {
        "base_currency": DEFAULT_BASE_CURRENCY,
        "currencies": CURATED_CURRENCIES,
        "count": len(CURATED_CURRENCIES),
    }


@fx_router.get("/rate")
async def get_rate(
    base: str = Query(
        default=DEFAULT_BASE_CURRENCY,
        min_length=3,
        max_length=3,
        description="The course-price base currency.",
    ),
    to: str = Query(
        default="USD",
        min_length=3,
        max_length=3,
        description="The target display currency.",
    ),
) -> dict[str, Any]:
    """
    Return the exchange rate from one supported currency to another.
    """
    normalized_base = _normalize_currency(
        base,
        field_name="base",
    )

    normalized_target = _normalize_currency(
        to,
        field_name="target",
    )

    rate, cached = await _get_exchange_rate(
        normalized_base,
        normalized_target,
    )

    _remove_expired_cache_entries()

    return {
        "base": normalized_base,
        "target": normalized_target,
        "rate": rate,
        "cached": cached,
        "base_symbol": _currency_symbol(normalized_base),
        "target_symbol": _currency_symbol(normalized_target),
        "locale": _default_locale_for_currency(normalized_target),
        "expires_in_seconds": RATE_TTL_SECONDS,
    }


@fx_router.get("/localize")
async def localize(
    request: Request,
    base: str = Query(
        default=DEFAULT_BASE_CURRENCY,
        min_length=3,
        max_length=3,
        description="The currency in which course prices are stored.",
    ),
) -> dict[str, Any]:
    """
    Detect the visitor's local currency and return its exchange rate.

    When geolocation or exchange-rate retrieval fails, the response falls
    back to the base currency with a rate of 1.0.
    """
    normalized_base = _normalize_currency(
        base,
        field_name="base",
    )

    client_ip = _client_ip(request)

    geo: dict[str, Any] = {}

    if client_ip and not _is_non_public_ip(client_ip):
        geo = await _fetch_geo(client_ip)

    detected_currency_raw = geo.get("currency")

    detected_currency = (
        str(detected_currency_raw).strip().upper()
        if detected_currency_raw
        else normalized_base
    )

    country_code = geo.get("country_code")
    country_name = geo.get("country_name")

    detected_locale = _normalize_locale(
        geo.get("languages")
    )

    # Use the detected currency only when it is in the curated list.
    if detected_currency not in SUPPORTED_CURRENCIES:
        logger.info(
            "Detected unsupported currency=%s; falling back to base=%s",
            detected_currency,
            normalized_base,
        )

        detected_currency = normalized_base

    locale = (
        detected_locale
        or _default_locale_for_currency(detected_currency)
    )

    source = "geo" if geo else "fallback"

    if detected_currency == normalized_base:
        _remove_expired_cache_entries()

        return {
            "base": normalized_base,
            "detected_currency": normalized_base,
            "country_code": country_code,
            "country_name": country_name,
            "locale": locale,
            "rate": 1.0,
            "source": source,
            "base_symbol": _currency_symbol(normalized_base),
            "currency_symbol": _currency_symbol(normalized_base),
            "is_converted": False,
            "is_estimate": False,
            "fallback_used": not bool(geo),
            "expires_in_seconds": RATE_TTL_SECONDS,
        }

    try:
        rate, _ = await _get_exchange_rate(
            normalized_base,
            detected_currency,
        )

        fallback_used = False
        used_currency = detected_currency

    except HTTPException as exc:
        logger.warning(
            "Could not localize currency from %s to %s: %s",
            normalized_base,
            detected_currency,
            exc.detail,
        )

        rate = 1.0
        used_currency = normalized_base
        locale = _default_locale_for_currency(normalized_base)
        source = "fallback"
        fallback_used = True

    _remove_expired_cache_entries()

    return {
        "base": normalized_base,
        "detected_currency": used_currency,
        "country_code": country_code,
        "country_name": country_name,
        "locale": locale,
        "rate": rate,
        "source": source,
        "base_symbol": _currency_symbol(normalized_base),
        "currency_symbol": _currency_symbol(used_currency),
        "is_converted": used_currency != normalized_base,
        "is_estimate": used_currency != normalized_base,
        "fallback_used": fallback_used,
        "expires_in_seconds": RATE_TTL_SECONDS,
    }
