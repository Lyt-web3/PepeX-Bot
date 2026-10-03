from app.utils import clean_coin


def demo_position_for_market(market):
    if market == "entropy":
        return {
            "coin": "SNDK",
            "side": "LONG",
            "leverage": 5,
            "roe": 11.19,
            "pnl": 318.0,
            "entry": 118.40,
            "exit_px": 121.05,
            "exit_label": "MARK",
            "details": [
                ("SIZE", "120 SNDK"),
                ("POSITION VALUE", "$14.53K"),
                ("LIQ PRICE", "97.80"),
            ],
        }
    return {
        "coin": "BTC",
        "side": "LONG",
        "leverage": 20,
        "roe": 10.27,
        "pnl": 1280.50,
        "entry": 64250.0,
        "exit_px": 64580.0,
        "exit_label": "MARK",
        "details": [
            ("SIZE", "0.52 BTC"),
            ("POSITION VALUE", "$33.58K"),
            ("LIQ PRICE", "61,310.00"),
        ],
    }


def demo_portfolio_for_market(market):
    if market == "entropy":
        return {
            "account_value": 6420.80,
            "upnl": 318.0,
            "margin_used": 2905.20,
            "withdrawable": 3515.60,
            "exposure": 14526.0,
            "positions": [
                {"coin": "SNDK", "side": "LONG", "lev": 5, "value": 14526.0, "pnl": 318.0}
            ],
        }
    return {
        "account_value": 48210.55,
        "upnl": 1083.95,
        "margin_used": 3120.40,
        "withdrawable": 44800.10,
        "exposure": 60940.0,
        "positions": [
            {"coin": "BTC", "side": "LONG", "lev": 20, "value": 33580.0, "pnl": 1280.50},
            {"coin": "ETH", "side": "SHORT", "lev": 10, "value": 18240.0, "pnl": -412.30},
            {"coin": "SOL", "side": "LONG", "lev": 5, "value": 9120.0, "pnl": 215.75},
        ],
    }


def demo_volume_for_market(market):
    if market == "entropy":
        return {
            "vol_24h": 186_400.0,
            "vol_7d": 912_000.0,
            "vol_30d": 2_340_000.0,
            "daily": [88e3, 142e3, 61e3, 175e3, 120e3, 148e3, 186.4e3],
            "trades": 34,
            "fees": 19.60,
        }
    return {
        "vol_24h": 1.24e6,
        "vol_7d": 8.9e6,
        "vol_30d": 31.2e6,
        "daily": [0.9e6, 1.4e6, 0.7e6, 1.8e6, 1.1e6, 1.5e6, 1.24e6],
        "trades": 128,
        "fees": 412.70,
    }
