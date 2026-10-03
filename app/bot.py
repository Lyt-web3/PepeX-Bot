import traceback

import discord
from discord import app_commands

from app.commands.card_commands import pnl_card, portfolio_card, volume_card
from app.commands.leaderboard import LEADERBOARD_METRICS, leaderboard_command
from app.commands.wallet_commands import link_wallet, show_linked_wallet, unlink_wallet
from app.config import DISCORD_TOKEN, logger
from app.database import init_db
from app.exceptions import PepexError


class PepeBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()


bot = PepeBot()


@bot.event
async def on_ready():
    logger.info("Logged in as %s", bot.user)


@bot.tree.error
async def on_app_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    logger.exception("Discord command failed: %s", error)

    msg = "Something went wrong while building that card. Please try again in a moment."
    if isinstance(error, PepexError):
        msg = str(error)

    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)


@bot.tree.command(name="link", description="Link a Hyperliquid wallet to your Discord account")
@app_commands.describe(wallet="Your Hyperliquid wallet address")
async def link(interaction: discord.Interaction, wallet: str):
    await link_wallet(interaction, wallet)


@bot.tree.command(name="mywallet", description="Show your linked wallet")
async def mywallet(interaction: discord.Interaction):
    await show_linked_wallet(interaction)


@bot.tree.command(name="unlink", description="Remove your linked wallet")
async def unlink(interaction: discord.Interaction):
    await unlink_wallet(interaction)


@bot.tree.command(name="leaderboard", description="Entropy leaderboard for linked wallets")
@app_commands.describe(metric="How the leaderboard should be ranked")
@app_commands.choices(metric=LEADERBOARD_METRICS)
async def leaderboard(interaction: discord.Interaction, metric: str = "24h Volume"):
    await leaderboard_command(interaction, metric)


@bot.tree.command(name="pnl", description="PNL card for a wallet's open position")
@app_commands.describe(
    wallet="Optional wallet address, or 'demo' (uses your linked wallet if omitted)",
    coin="Optional: a specific coin, like BTC",
    market="Hyperliquid (default) or Entropy",
)
@app_commands.choices(market=[
    app_commands.Choice(name="Hyperliquid", value="hl"),
    app_commands.Choice(name="Entropy", value="entropy"),
])
async def pnl(interaction: discord.Interaction, wallet: str = None, coin: str = None, market: str = "hl"):
    await pnl_card(interaction, wallet, coin, market)


@bot.tree.command(name="portfolio", description="Portfolio card for a wallet")
@app_commands.describe(
    wallet="Hyperliquid wallet address, or 'demo'",
    market="Hyperliquid (default) or Entropy",
)
@app_commands.choices(market=[
    app_commands.Choice(name="Hyperliquid", value="hl"),
    app_commands.Choice(name="Entropy", value="entropy"),
])
async def portfolio(interaction: discord.Interaction, wallet: str = None, market: str = "hl"):
    await portfolio_card(interaction, wallet, market)


@bot.tree.command(name="volume", description="Trading volume card for a wallet")
@app_commands.describe(
    wallet="Hyperliquid wallet address, or 'demo'",
    market="Hyperliquid (default) or Entropy",
)
@app_commands.choices(market=[
    app_commands.Choice(name="Hyperliquid", value="hl"),
    app_commands.Choice(name="Entropy", value="entropy"),
])
async def volume(interaction: discord.Interaction, wallet: str = None, market: str = "hl"):
    await volume_card(interaction, wallet, market)


if __name__ == "__main__":
    init_db()
    if not DISCORD_TOKEN:
        raise SystemExit("DISCORD_TOKEN not found. Check that your .env file is in this folder.")
    bot.run(DISCORD_TOKEN)
