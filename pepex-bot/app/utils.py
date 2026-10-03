import re

from app.exceptions import MarketValidationError, WalletValidationError


def is_wallet(text):
    return (
        isinstance(text, str)
        and len(text) == 42
        and text.startswith("0x")
        and all(c in "0123456789abcdefABCDEF" for c in text[2:])
    )


def normalize_market(market):
    if market is None:
        return "hl"
    value = str(market).strip().lower()
    if value in {"hl", "hyperliquid"}:
        return "hl"
    if value in {"entropy", "ent"}:
        return "entropy"
    raise MarketValidationError("Unsupported market. Use Hyperliquid or Entropy.")


def validate_wallet_input(wallet):
    if wallet is None:
        return None
    if str(wallet).strip().lower() == "demo":
        return "demo"
    value = str(wallet).strip()
    if not is_wallet(value):
        raise WalletValidationError(
            "That doesn't look like a wallet address. It should start with 0x and be 42 characters long."
        )
    return value


def short_wallet(wallet):
    if not wallet:
        return ""
    wallet = str(wallet)
    return f"{wallet[:6]}...{wallet[-4:]}"


def money(value):
    value = float(value)
    return f"${value:,.2f}"


def clean_coin(coin):
    if not coin:
        return ""
    return coin.split(":", 1)[-1]


def in_market(fill, dex):
    coin = fill.get("coin", "")
    return coin.startswith(dex + ":") if dex else ":" not in coin


def fmt_size(x):
    return f"{x:,.4f}".rstrip("0").rstrip(".") or "0"
