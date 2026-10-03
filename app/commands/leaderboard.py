import asyncio
import time

import discord
from discord import app_commands

from app.config import logger
from app.database import get_all_linked_wallets
from app.exceptions import HyperliquidAPIError
from app.services.hyperliquid_client import resolve_dex
from app.services.wallet_service import entropy_wallet_stats
from app.utils import money

LEADERBOARD_METRICS = [
    app_commands.Choice(name="PNL", value="PNL"),
    app_commands.Choice(name="24h Volume", value="24h Volume"),
    app_commands.Choice(name="7d Volume", value="7d Volume"),
    app_commands.Choice(name="30d Volume", value="30d Volume"),
    app_commands.Choice(name="24h Trades", value="24h Trades"),
    app_commands.Choice(name="7d Trades", value="7d Trades"),
    app_commands.Choice(name="30d Trades", value="30d Trades"),
]


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
        "PNL": "upnl",
        "24h Volume": "vol24",
        "7d Volume": "vol7",
        "30d Volume": "vol30",
        "24h Trades": "trades24",
        "7d Trades": "trades7",
        "30d Trades": "trades30",
    }[metric]
    results.sort(key=lambda r: r[2][key], reverse=True)
    return results[:10]


async def leaderboard_command(interaction: discord.Interaction, metric: str = "24h Volume"):
    try:
        await interaction.response.defer()
        rows = await build_entropy_leaderboard(metric)
        embed = discord.Embed(
            title=f"Entropy Leaderboard — {metric}",
            description="Top 10 linked Discord wallets",
            color=discord.Color.blurple(),
        )

        if not rows:
            embed.description = "No linked wallets have usable Entropy data yet."
        else:
            lines = []
            for rank, (discord_id, wallet, stats) in enumerate(rows, 1):
                if metric == "PNL":
                    value = money(stats["upnl"])
                elif metric == "24h Volume":
                    value = money(stats["vol24"])
                elif metric == "7d Volume":
                    value = money(stats["vol7"])
                elif metric == "30d Volume":
                    value = money(stats["vol30"])
                elif metric == "24h Trades":
                    value = f"{stats['trades24']:,}"
                elif metric == "7d Trades":
                    value = f"{stats['trades7']:,}"
                else:
                    value = f"{stats['trades30']:,}"
                lines.append(f"**{rank}.** <@{discord_id}> — **{value}**")
            embed.description = "\n".join(lines)

        embed.set_footer(text="PNL = current unrealized PNL on open Entropy positions. Volume/trades = recent Entropy fills.")
        await interaction.followup.send(embed=embed)
    except HyperliquidAPIError:
        logger.exception("Leaderboard query failed")
        await interaction.followup.send("Entropy data is temporarily unavailable. Please try again in a moment.", ephemeral=True)
