from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class Position:
    coin: str
    side: str
    leverage: int
    roe: float
    pnl: float
    entry: float
    exit_px: float
    exit_label: str = "MARK"
    details: List[tuple[str, str]] = field(default_factory=list)


@dataclass
class Portfolio:
    account_value: float
    upnl: float
    margin_used: float
    withdrawable: float
    exposure: float
    positions: List[dict[str, Any]] = field(default_factory=list)


@dataclass
class Volume:
    vol_24h: float
    vol_7d: float
    vol_30d: float
    daily: List[float]
    trades: int
    fees: float


@dataclass
class WalletStats:
    upnl: float
    vol24: float
    vol7: float
    vol30: float
    trades24: int
    trades7: int
    trades30: int
