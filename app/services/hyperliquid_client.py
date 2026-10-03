import asyncio
import time
import traceback
from typing import Any, Dict

import requests

from app.config import API_BACKOFF_SECONDS, API_RETRY_ATTEMPTS, HTTP_TIMEOUT_SECONDS, HL_URL, logger
from app.exceptions import HyperliquidAPIError

DEX_CACHE: Dict[str, str] = {}


def hl(payload: Dict[str, Any], retries: int = API_RETRY_ATTEMPTS):
    """HTTP call with a small retry policy for transient API failures."""
    last_exc = None

    for attempt in range(retries):
        try:
            response = requests.post(HL_URL, json=payload, timeout=HTTP_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            logger.warning("Hyperliquid request failed (attempt %s/%s): %s", attempt + 1, retries, exc)
            if attempt < retries - 1:
                time.sleep(API_BACKOFF_SECONDS * (2 ** attempt))
                continue

    raise HyperliquidAPIError(f"Hyperliquid request failed: {last_exc}") from last_exc


async def ask(payload: Dict[str, Any]):
    return await asyncio.to_thread(hl, payload)


async def resolve_dex(market: str):
    """Return the dex name for Entropy markets."""
    if market != "entropy":
        return ""

    if "entropy" not in DEX_CACHE:
        name = "io"
        try:
            dexes = await ask({"type": "perpDexs"})
            for dex in dexes:
                if dex and "entropy" in (
                    f"{dex.get('name', '')} {dex.get('fullName', '')}".lower()
                ):
                    name = dex.get("name") or name
                    break
        except Exception:
            logger.exception("Dex lookup failed; using fallback Entropy dex")
        DEX_CACHE["entropy"] = name

    return DEX_CACHE["entropy"]
