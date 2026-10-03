import time
from typing import Any, Dict, Optional

from app.services.hyperliquid_client import ask, hl, resolve_dex
from app.utils import clean_coin, fmt_size, in_market

DAY_MS = 24 * 60 * 60 * 1000


def state_payload(wallet, dex):
    payload = {"type": "clearinghouseState", "user": wallet}
    if dex:
        payload["dex"] = dex
    return payload


def pick_position(state, coin=None):
    items = [a["position"] for a in state.get("assetPositions", [])]
    if coin:
        items = [
            p for p in items if clean_coin(p["coin"]).upper() == clean_coin(coin.strip()).upper()
        ]
    if not items:
        return None
    return max(items, key=lambda p: abs(float(p["unrealizedPnl"])))


def position_card_args(p):
    szi = float(p["szi"])
    size = abs(szi)
    value = float(p["positionValue"])
    liq = p.get("liquidationPx")
    name = clean_coin(p["coin"])
    return dict(
        coin=name,
        side="LONG" if szi > 0 else "SHORT",
        leverage=p.get("leverage", {}).get("value", 1),
        roe=float(p.get("returnOnEquity", 0)) * 100,
        pnl=float(p["unrealizedPnl"]),
        entry=float(p["entryPx"]),
        exit_px=value / size if size else float(p["entryPx"]),
        exit_label="MARK",
        details=[
            ("SIZE", f"{fmt_size(size)} {name}"),
            ("POSITION VALUE", f"${value:,.2f}"),
            ("LIQ PRICE", f"{liq:,.2f}" if liq else "N/A"),
        ],
    )


def portfolio_card_args(state):
    ms = state["marginSummary"]
    positions = []
    for a in state.get("assetPositions", []):
        p = a["position"]
        positions.append(
            dict(
                coin=clean_coin(p["coin"]),
                side="LONG" if float(p["szi"]) > 0 else "SHORT",
                lev=p.get("leverage", {}).get("value", 1),
                value=float(p["positionValue"]),
                pnl=float(p["unrealizedPnl"]),
            )
        )
    positions.sort(key=lambda x: x["value"], reverse=True)
    return dict(
        account_value=float(ms["accountValue"]),
        upnl=sum(x["pnl"] for x in positions),
        margin_used=float(ms["totalMarginUsed"]),
        withdrawable=float(state.get("withdrawable", 0)),
        exposure=float(ms["totalNtlPos"]),
        positions=positions,
    )


def fill_key(f):
    return f.get("tid") or (f["time"], f["px"], f["sz"], f.get("oid"))


def fetch_fills(wallet, start_ms):
    fills = []
    seen = set()

    for _ in range(5):
        page = hl({
            "type": "userFillsByTime",
            "user": wallet,
            "startTime": start_ms,
        })

        for f in page:
            k = fill_key(f)
            if k not in seen:
                seen.add(k)
                fills.append(f)

        if len(page) < 2000:
            break

        start_ms = max(f["time"] for f in page)

    return fills


def volume_card_args(fills, now_ms):
    def notional(f):
        return float(f["px"]) * float(f["sz"])

    def window(start, end):
        return [f for f in fills if start <= f["time"] < end]

    daily = [
        sum(notional(f) for f in window(now_ms - (i + 1) * DAY_MS, now_ms - i * DAY_MS))
        for i in range(6, -1, -1)
    ]
    last_day = window(now_ms - DAY_MS, now_ms + 1)
    return dict(
        vol_24h=daily[-1],
        vol_7d=sum(daily),
        vol_30d=sum(notional(f) for f in fills),
        daily=daily,
        trades=len(last_day),
        fees=sum(float(f.get("fee", 0)) for f in last_day),
    )


def entropy_wallet_stats(wallet, dex, now_ms):
    state = hl(state_payload(wallet, dex))
    ms = state.get("marginSummary", {})
    upnl = float(ms.get("unrealizedPnl", 0))
    fills = fetch_fills(wallet, now_ms - 30 * DAY_MS)
    fills = [f for f in fills if in_market(f, dex)]

    def vol(start):
        return sum(float(f["px"]) * float(f["sz"]) for f in fills if f["time"] >= start)

    return {
        "upnl": upnl,
        "vol24": vol(now_ms - DAY_MS),
        "vol7": vol(now_ms - 7 * DAY_MS),
        "vol30": vol(now_ms - 30 * DAY_MS),
        "trades24": sum(f["time"] >= now_ms - DAY_MS for f in fills),
        "trades7": sum(f["time"] >= now_ms - 7 * DAY_MS for f in fills),
        "trades30": len(fills),
    }
