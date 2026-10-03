import asyncio
import io
import os
import time
import traceback
import random
from typing import Optional

import discord
import requests
import sqlite3
from discord import app_commands
from dotenv import load_dotenv

import card

# Paths are built from this file's location, so the bot finds .env and mascot.png
# no matter which folder the terminal is standing in.
BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, ".env"))
TOKEN = os.getenv("DISCORD_TOKEN")

HL_URL = "https://api.hyperliquid.xyz/info"
THEME = "random"  # random, neon, gold, violet or frost
MASCOT = os.path.join(BASE, "mascot.png")
DAY_MS = 24 * 60 * 60 * 1000
DB_PATH = os.path.join(BASE, "bot.db")

# ---------- demo data, so you can test cards without a funded wallet ----------

DEMO_POSITION = dict(
    coin="BTC", side="LONG", leverage=20, roe=10.27, pnl=1280.50, entry=64250.0, exit_px=64580.0,
    exit_label="MARK",
    details=[("SIZE", "0.52 BTC"), ("POSITION VALUE", "$33.58K"), ("LIQ PRICE", "61,310.00")],
)
DEMO_POSITION_ENTROPY = dict(
    coin="SNDK", side="LONG", leverage=5, roe=11.19, pnl=318.0, entry=118.40, exit_px=121.05,
    exit_label="MARK",
    details=[("SIZE", "120 SNDK"), ("POSITION VALUE", "$14.53K"), ("LIQ PRICE", "97.80")],
)
DEMO_PORTFOLIO = dict(
    account_value=48210.55, upnl=1083.95, margin_used=3120.40, withdrawable=44800.10, exposure=60940.0,
    positions=[
        {"coin": "BTC", "side": "LONG", "lev": 20, "value": 33580.0, "pnl": 1280.50},
        {"coin": "ETH", "side": "SHORT", "lev": 10, "value": 18240.0, "pnl": -412.30},
        {"coin": "SOL", "side": "LONG", "lev": 5, "value": 9120.0, "pnl": 215.75},
    ],
)
DEMO_PORTFOLIO_ENTROPY = dict(
    account_value=6420.80, upnl=318.0, margin_used=2905.20, withdrawable=3515.60, exposure=14526.0,
    positions=[{"coin": "SNDK", "side": "LONG", "lev": 5, "value": 14526.0, "pnl": 318.0}],
)
DEMO_VOLUME = dict(
    vol_24h=1.24e6, vol_7d=8.9e6, vol_30d=31.2e6,
    daily=[0.9e6, 1.4e6, 0.7e6, 1.8e6, 1.1e6, 1.5e6, 1.24e6], trades=128, fees=412.70,
)
DEMO_VOLUME_ENTROPY = dict(
    vol_24h=186_400.0, vol_7d=912_000.0, vol_30d=2_340_000.0,
    daily=[88e3, 142e3, 61e3, 175e3, 120e3, 148e3, 186.4e3], trades=34, fees=19.60,
)

MARKET_CHOICES = [
    app_commands.Choice(name="Hyperliquid", value="hl"),
    app_commands.Choice(name="Entropy", value="entropy"),
]
ENTROPY_FALLBACK_DEX = "io"  # Entropy's HIP-3 dex name, used if the lookup below finds nothing
_dex_cache = {}


# ---------- talking to Hyperliquid ----------

def hl(payload):
    r = requests.post(HL_URL, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()


async def ask(payload):
    # requests is slow and blocking, so run it off the bot's main loop
    return await asyncio.to_thread(hl, payload)


async def wallet_is_associated(wallet):
    result = await ask({"type": "userRole", "user": wallet})
    if not isinstance(result, dict) or not isinstance(result.get("role"), str):
        raise ValueError(f"Unexpected Hyperliquid userRole response: {result!r}")
    return result["role"].lower() != "missing"


async def resolve_dex(market):
    """Hyperliquid's own markets use an empty dex name. Entropy is a HIP-3 dex, so we look up its name."""
    if market != "entropy":
        return ""
    if "entropy" not in _dex_cache:
        name = ENTROPY_FALLBACK_DEX
        try:
            for d in await ask({"type": "perpDexs"}):
                if d and "entropy" in f"{d.get('name', '')} {d.get('fullName', '')}".lower():
                    name = d["name"]
                    break
        except Exception:
            traceback.print_exc()  # lookup failed, so stick with the fallback name
        _dex_cache["entropy"] = name
    return _dex_cache["entropy"]


def state_payload(wallet, dex):
    payload = {"type": "clearinghouseState", "user": wallet}
    if dex:
        payload["dex"] = dex
    return payload


def clean_coin(coin):
    return coin.split(":", 1)[-1]  # HIP-3 coins arrive as "io:SNDK"; cards show just "SNDK"


def in_market(fill, dex):
    coin = fill.get("coin", "")
    return coin.startswith(dex + ":") if dex else ":" not in coin


def is_wallet(text):
    return len(text) == 42 and text.startswith("0x") and all(c in "0123456789abcdefABCDEF" for c in text[2:])


def fill_key(f):
    return f.get("tid") or (f["time"], f["px"], f["sz"], f.get("oid"))


def fetch_fills(wallet, start_ms):
    """Every fill since start_ms. Hyperliquid returns at most 2000 per call, so we page forward."""
    fills, seen = [], set()
    for _ in range(5):
        page = hl({"type": "userFillsByTime", "user": wallet, "startTime": start_ms})
        for f in page:
            k = fill_key(f)
            if k not in seen:
                seen.add(k)
                fills.append(f)
        if len(page) < 2000:
            break
        start_ms = max(f["time"] for f in page)
    return fills


# ---------- turning raw API data into card inputs ----------

def fmt_size(x):
    return f"{x:,.4f}".rstrip("0").rstrip(".") or "0"


def pick_position(state, coin=None):
    items = [a["position"] for a in state.get("assetPositions", [])]
    if coin:
        items = [p for p in items if clean_coin(p["coin"]).upper() == clean_coin(coin.strip()).upper()]
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
        roe=float(p.get("returnOnEquity", 0)) * 100,  # the API sends 0.07 for 7%
        pnl=float(p["unrealizedPnl"]),
        entry=float(p["entryPx"]),
        exit_px=value / size if size else float(p["entryPx"]),  # current mark price
        exit_label="MARK",
        details=[
            ("SIZE", f"{fmt_size(size)} {name}"),
            ("POSITION VALUE", card.usd(value)),
            ("LIQ PRICE", card.px(float(liq)) if liq else "N/A"),
        ],
    )


def portfolio_card_args(state):
    ms = state["marginSummary"]
    positions = []
    for a in state.get("assetPositions", []):
        p = a["position"]
        positions.append(dict(
            coin=clean_coin(p["coin"]),
            side="LONG" if float(p["szi"]) > 0 else "SHORT",
            lev=p.get("leverage", {}).get("value", 1),
            value=float(p["positionValue"]),
            pnl=float(p["unrealizedPnl"]),
        ))
    positions.sort(key=lambda x: x["value"], reverse=True)
    return dict(
        account_value=float(ms["accountValue"]),
        upnl=sum(x["pnl"] for x in positions),
        margin_used=float(ms["totalMarginUsed"]),
        withdrawable=float(state.get("withdrawable", 0)),
        exposure=float(ms["totalNtlPos"]),
        positions=positions,
    )


def volume_card_args(fills, now_ms):
    def notional(f):
        return float(f["px"]) * float(f["sz"])

    def window(start, end):
        return [f for f in fills if start <= f["time"] < end]

    # seven rolling 24-hour windows, oldest first. The last one is the 24h figure.
    daily = [sum(notional(f) for f in window(now_ms - (i + 1) * DAY_MS, now_ms - i * DAY_MS))
             for i in range(6, -1, -1)]
    last_day = window(now_ms - DAY_MS, now_ms + 1)
    return dict(
        vol_24h=daily[-1],
        vol_7d=sum(daily),
        vol_30d=sum(notional(f) for f in fills),
        daily=daily,
        trades=len(last_day),
        fees=sum(float(f.get("fee", 0)) for f in last_day),
    )


# ---------- sending cards ----------

def render(fn, filename, tag, owner_name=None, wallet_address=None, **kwargs):
    buf = io.BytesIO()
    theme = random.choice(list(card.THEMES)) if THEME == "random" else THEME
    fn(path=buf, theme=theme, mascot_path=MASCOT, tag=tag,
       owner_name=owner_name, wallet_address=wallet_address, **kwargs)
    buf.seek(0)
    return discord.File(buf, filename=filename)


async def deliver(interaction, fn, filename, market, wallet, **kwargs):
    tag = "ENTROPY" if market == "entropy" else ""

    # Only show Discord display name for the wallet linked to this account
    linked_wallet = get_linked_wallet(interaction.user.id)

    if linked_wallet and linked_wallet.lower() == wallet.lower():
        owner_name = getattr(interaction.user, "display_name", None) or interaction.user.name
    else:
        owner_name = None

    file = await asyncio.to_thread(
        render,
        fn,
        filename,
        tag,
        owner_name,
        wallet,
        **kwargs
    )

    await interaction.followup.send(file=file)


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS linked_wallets (discord_id INTEGER PRIMARY KEY, wallet TEXT NOT NULL)")
        conn.commit()


def set_linked_wallet(discord_id, wallet):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO linked_wallets(discord_id, wallet) VALUES(?, ?) ON CONFLICT(discord_id) DO UPDATE SET wallet=excluded.wallet", (discord_id, wallet))
        conn.commit()


def create_linked_wallet(discord_id, wallet):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO linked_wallets(discord_id, wallet) VALUES(?, ?)",
            (discord_id, wallet),
        )
        conn.commit()
    return cursor.rowcount == 1


def get_linked_wallet(discord_id):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT wallet FROM linked_wallets WHERE discord_id=?", (discord_id,)).fetchone()
    return row[0] if row else None


def remove_linked_wallet(discord_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM linked_wallets WHERE discord_id=?", (discord_id,))
        conn.commit()


def get_all_linked_wallets():
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("SELECT discord_id, wallet FROM linked_wallets").fetchall()


def short_wallet(wallet):
    return f"{wallet[:6]}...{wallet[-4:]}"


def money(value):
    value = float(value)
    return f"${value:,.2f}"


async def check_wallet(interaction, wallet):
    if wallet is None:
        wallet = get_linked_wallet(interaction.user.id)
        if not wallet:
            await interaction.followup.send(
                "No wallet is linked to your Discord account. Use `/link wallet:<address>` first.",
                ephemeral=True
            )
            return None

    wallet = wallet.strip()
    if wallet.lower() == "demo":
        return wallet

    if not is_wallet(wallet):
        await interaction.followup.send(
            "That doesn't look like a wallet address. It should start with 0x and be 42 characters long.",
            ephemeral=True
        )
        return None

    try:
        associated = await wallet_is_associated(wallet)
    except requests.exceptions.RequestException:
        traceback.print_exc()
        await interaction.followup.send(
            "Hyperliquid is temporarily unavailable. Please try again in a moment.",
            ephemeral=True
        )
        return None
    except ValueError as exc:
        print(f"Could not verify Hyperliquid wallet: {exc}")
        await interaction.followup.send(
            "Could not verify this wallet with Hyperliquid. Please try again in a moment.",
            ephemeral=True
        )
        return None

    if not associated:
        await interaction.followup.send(
            "THIS ADDRESS IS NOT ASSOCIATED WITH HYPERLIQUID",
            ephemeral=True
        )
        return None

    return wallet


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


async def build_entropy_leaderboard(metric):
    rows = get_all_linked_wallets()
    now_ms = int(time.time() * 1000)
    dex = await resolve_dex("entropy")
    sem = asyncio.Semaphore(5)
    async def one(discord_id, wallet):
        async with sem:
            try:
                stats = await asyncio.to_thread(entropy_wallet_stats, wallet, dex, now_ms)
                return discord_id, wallet, stats
            except Exception:
                traceback.print_exc()
                return None
    results = [r for r in await asyncio.gather(*(one(i, w) for i, w in rows)) if r]
    key = {
        "PNL": "upnl", "24h Volume": "vol24", "7d Volume": "vol7", "30d Volume": "vol30",
        "24h Trades": "trades24", "7d Trades": "trades7", "30d Trades": "trades30"
    }[metric]
    results.sort(key=lambda r: r[2][key], reverse=True)
    return results[:10]


LEADERBOARD_METRICS = [
    app_commands.Choice(name="PNL", value="PNL"),
    app_commands.Choice(name="24h Volume", value="24h Volume"),
    app_commands.Choice(name="7d Volume", value="7d Volume"),
    app_commands.Choice(name="30d Volume", value="30d Volume"),
    app_commands.Choice(name="24h Trades", value="24h Trades"),
    app_commands.Choice(name="7d Trades", value="7d Trades"),
    app_commands.Choice(name="30d Trades", value="30d Trades"),
]


# ---------- the bot ----------

class PepeBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()


bot = PepeBot()


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.tree.error
async def on_app_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    traceback.print_exception(type(error), error, error.__traceback__)  # full detail for your terminal
    msg = "Something went wrong while building that card. Try again in a moment."
    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except discord.NotFound:
        print("Interaction expired before the error message could be sent.")
    except discord.HTTPException as exc:
        print(f"Could not send error response: {exc}")


@bot.tree.command(name="link", description="Link a Hyperliquid wallet to your Discord account")
@app_commands.describe(wallet="Your Hyperliquid wallet address")
async def link(interaction: discord.Interaction, wallet: str):
    await interaction.response.defer(ephemeral=True)
    wallet = wallet.strip()
    if not is_wallet(wallet):
        await interaction.followup.send(
            "Invalid wallet address. It should start with 0x and be 42 characters long.",
            ephemeral=True
        )
        return

    if get_linked_wallet(interaction.user.id):
        await interaction.followup.send(
            "A wallet is already linked to this account. Use `/unlink` before linking another wallet.",
            ephemeral=True,
        )
        return

    try:
        associated = await wallet_is_associated(wallet)
    except requests.exceptions.RequestException:
        traceback.print_exc()
        await interaction.followup.send(
            "Hyperliquid is temporarily unavailable. Please try linking again in a moment.",
            ephemeral=True,
        )
        return
    except ValueError as exc:
        print(f"Could not verify Hyperliquid wallet: {exc}")
        await interaction.followup.send(
            "Could not verify this wallet with Hyperliquid. Please try again in a moment.",
            ephemeral=True,
        )
        return

    if not associated:
        await interaction.followup.send(
            "THIS ADDRESS IS NOT ASSOCIATED WITH HYPERLIQUID",
            ephemeral=True,
        )
        return

    try:
        linked = create_linked_wallet(interaction.user.id, wallet)
    except sqlite3.Error:
        traceback.print_exc()
        await interaction.followup.send(
            "The wallet could not be saved. Please try again in a moment.",
            ephemeral=True,
        )
        return

    if not linked:
        await interaction.followup.send(
            "A wallet is already linked to this account. Use `/unlink` before linking another wallet.",
            ephemeral=True,
        )
        return

    await interaction.followup.send(
        f"Wallet linked: `{short_wallet(wallet)}`",
        ephemeral=True
    )


@bot.tree.command(name="mywallet", description="Show your linked wallet")
async def mywallet(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    wallet = get_linked_wallet(interaction.user.id)
    if not wallet:
        await interaction.followup.send(
            "No wallet linked. Use `/link wallet:<address>`.",
            ephemeral=True
        )
        return
    await interaction.followup.send(
        f"Your linked wallet: `{short_wallet(wallet)}`",
        ephemeral=True
    )


@bot.tree.command(name="unlink", description="Remove your linked wallet")
async def unlink(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if get_linked_wallet(interaction.user.id):
        remove_linked_wallet(interaction.user.id)
        await interaction.followup.send(
            "Your wallet has been unlinked.",
            ephemeral=True
        )
    else:
        await interaction.followup.send(
            "You don't have a linked wallet.",
            ephemeral=True
        )


@bot.tree.command(name="leaderboard", description="Entropy leaderboard for linked wallets")
@app_commands.describe(metric="How the leaderboard should be ranked")
@app_commands.choices(metric=LEADERBOARD_METRICS)
async def leaderboard(interaction: discord.Interaction, metric: str = "24h Volume"):
    await interaction.response.defer()
    rows = await build_entropy_leaderboard(metric)
    embed = discord.Embed(title=f"Entropy Leaderboard — {metric}", description="Top 10 linked Discord wallets", color=discord.Color.blurple())
    if not rows:
        embed.description = "No linked wallets have usable Entropy data yet."
    else:
        lines = []
        for rank, (discord_id, wallet, stats) in enumerate(rows, 1):
            if metric == "PNL": value = money(stats["upnl"])
            elif metric == "24h Volume": value = money(stats["vol24"])
            elif metric == "7d Volume": value = money(stats["vol7"])
            elif metric == "30d Volume": value = money(stats["vol30"])
            elif metric == "24h Trades": value = f"{stats['trades24']:,}"
            elif metric == "7d Trades": value = f"{stats['trades7']:,}"
            else: value = f"{stats['trades30']:,}"
            lines.append(f"**{rank}.** <@{discord_id}> — **{value}**")
        embed.description = "\n".join(lines)
    embed.set_footer(text="PNL = current unrealized PNL on open Entropy positions. Volume/trades = recent Entropy fills.")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="pnl", description="PNL card for a wallet's open position")
@app_commands.describe(wallet="Optional wallet address, or 'demo' (uses your linked wallet if omitted)", coin="Optional: a specific coin, like BTC",
                       market="Hyperliquid (default) or Entropy")
@app_commands.choices(market=MARKET_CHOICES)
async def pnl(interaction: discord.Interaction, wallet: Optional[str] = None, coin: Optional[str] = None, market: str = "hl"):
    await interaction.response.defer()
    wallet = await check_wallet(interaction, wallet)
    if wallet is None:
        return
    if wallet.lower() == "demo":
        args = DEMO_POSITION_ENTROPY if market == "entropy" else DEMO_POSITION
    else:
        dex = await resolve_dex(market)
        state = await ask(state_payload(wallet, dex))
        pos = pick_position(state, coin)
        if pos is None:
            where = "Entropy" if market == "entropy" else "Hyperliquid"
            await interaction.followup.send(f"No open positions found for that wallet on {where}. Try `/pnl demo` to preview the card.")
            return
        args = position_card_args(pos)
    await deliver(interaction, card.make_card, "pnl.png", market, wallet, **args)


@bot.tree.command(name="portfolio", description="Portfolio card for a wallet")
@app_commands.describe(wallet="Hyperliquid wallet address, or 'demo'", market="Hyperliquid (default) or Entropy")
@app_commands.choices(market=MARKET_CHOICES)
async def portfolio(interaction: discord.Interaction, wallet: Optional[str] = None, market: str = "hl"):
    await interaction.response.defer()
    wallet = await check_wallet(interaction, wallet)
    if wallet is None:
        return
    if wallet.lower() == "demo":
        args = DEMO_PORTFOLIO_ENTROPY if market == "entropy" else DEMO_PORTFOLIO
    else:
        dex = await resolve_dex(market)
        state = await ask(state_payload(wallet, dex))
        args = portfolio_card_args(state)
    await deliver(interaction, card.make_portfolio_card, "portfolio.png", market, wallet, **args)


@bot.tree.command(name="volume", description="Trading volume card for a wallet")
@app_commands.describe(wallet="Hyperliquid wallet address, or 'demo'", market="Hyperliquid (default) or Entropy")
@app_commands.choices(market=MARKET_CHOICES)
async def volume(interaction: discord.Interaction, wallet: Optional[str] = None, market: str = "hl"):
    await interaction.response.defer()
    wallet = await check_wallet(interaction, wallet)
    if wallet is None:
        return
    if wallet.lower() == "demo":
        args = DEMO_VOLUME_ENTROPY if market == "entropy" else DEMO_VOLUME
    else:
        dex = await resolve_dex(market)
        now_ms = int(time.time() * 1000)
        fills = await asyncio.to_thread(fetch_fills, wallet, now_ms - 30 * DAY_MS)
        args = volume_card_args([f for f in fills if in_market(f, dex)], now_ms)
    await deliver(interaction, card.make_volume_card, "volume.png", market, wallet, **args)


if __name__ == "__main__":
    init_db()
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN not found. Check that your .env file is in this folder.")
    bot.run(TOKEN)
