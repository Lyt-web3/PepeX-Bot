import asyncio
import logging
import time
from typing import Optional

import card
import discord

from app.config import logger
from app.database import get_linked_wallet
from app.exceptions import HyperliquidAPIError, MarketValidationError, WalletValidationError
from app.rendering.card_renderer import render_card
from app.services.card_service import (
    demo_portfolio_for_market,
    demo_position_for_market,
    demo_volume_for_market,
)
from app.services.hyperliquid_client import ask, resolve_dex
from app.services.wallet_service import (
    fetch_fills,
    pick_position,
    portfolio_card_args,
    position_card_args,
    state_payload,
    volume_card_args,
)
from app.utils import in_market, normalize_market, validate_wallet_input


async def check_wallet(interaction, wallet):
    if wallet is None:
        wallet = get_linked_wallet(interaction.user.id)
        if wallet:
            return wallet
        await interaction.response.send_message(
            "No wallet is linked to your Discord account. Use `/link wallet:<address>` first.",
            ephemeral=True,
        )
        return None

    try:
        return validate_wallet_input(wallet)
    except WalletValidationError as exc:
        logger.warning("Wallet validation failed for %s: %s", interaction.user.id, exc)
        await interaction.response.send_message(str(exc), ephemeral=True)
        return None


async def pnl_card(interaction: discord.Interaction, wallet: Optional[str] = None, coin: Optional[str] = None, market: str = "hl"):
    try:
        market = normalize_market(market)
        wallet = await check_wallet(interaction, wallet)
        if wallet is None:
            return

        await interaction.response.defer()

        if wallet.lower() == "demo":
            args = demo_position_for_market(market)
        else:
            dex = await resolve_dex(market)
            state = await ask(state_payload(wallet, dex))
            pos = pick_position(state, coin)
            if pos is None:
                where = "Entropy" if market == "entropy" else "Hyperliquid"
                await interaction.followup.send(
                    f"No open positions found for that wallet on {where}. Try `/pnl demo` to preview the card."
                )
                return
            args = position_card_args(pos)

        await interaction.followup.send(
            file=render_card(
                card.make_card,
                "pnl.png",
                "ENTROPY" if market == "entropy" else "",
                getattr(interaction.user, "display_name", None) or interaction.user.name,
                wallet,
                **args,
            )
        )
    except (HyperliquidAPIError, MarketValidationError) as exc:
        logger.exception("PNL card failed")
        if interaction.response.is_done():
            await interaction.followup.send("Hyperliquid is temporarily unavailable. Please try again in a moment.", ephemeral=True)
        else:
            await interaction.response.send_message("Hyperliquid is temporarily unavailable. Please try again in a moment.", ephemeral=True)


async def portfolio_card(interaction: discord.Interaction, wallet: Optional[str] = None, market: str = "hl"):
    try:
        market = normalize_market(market)
        wallet = await check_wallet(interaction, wallet)
        if wallet is None:
            return

        await interaction.response.defer()

        if wallet.lower() == "demo":
            args = demo_portfolio_for_market(market)
        else:
            dex = await resolve_dex(market)
            state = await ask(state_payload(wallet, dex))
            args = portfolio_card_args(state)

        await interaction.followup.send(
            file=render_card(
                card.make_portfolio_card,
                "portfolio.png",
                "ENTROPY" if market == "entropy" else "",
                getattr(interaction.user, "display_name", None) or interaction.user.name,
                wallet,
                **args,
            )
        )
    except (HyperliquidAPIError, MarketValidationError) as exc:
        logger.exception("Portfolio card failed")
        if interaction.response.is_done():
            await interaction.followup.send("Hyperliquid is temporarily unavailable. Please try again in a moment.", ephemeral=True)
        else:
            await interaction.response.send_message("Hyperliquid is temporarily unavailable. Please try again in a moment.", ephemeral=True)


async def volume_card(interaction: discord.Interaction, wallet: Optional[str] = None, market: str = "hl"):
    try:
        market = normalize_market(market)
        wallet = await check_wallet(interaction, wallet)
        if wallet is None:
            return

        await interaction.response.defer()

        if wallet.lower() == "demo":
            args = demo_volume_for_market(market)
        else:
            dex = await resolve_dex(market)
            now_ms = int(time.time() * 1000)
            fills = await asyncio.to_thread(fetch_fills, wallet, now_ms - 30 * 24 * 60 * 60 * 1000)
            args = volume_card_args([f for f in fills if in_market(f, dex)], now_ms)

        await interaction.followup.send(
            file=render_card(
                card.make_volume_card,
                "volume.png",
                "ENTROPY" if market == "entropy" else "",
                getattr(interaction.user, "display_name", None) or interaction.user.name,
                wallet,
                **args,
            )
        )
    except (HyperliquidAPIError, MarketValidationError) as exc:
        logger.exception("Volume card failed")
        if interaction.response.is_done():
            await interaction.followup.send("Hyperliquid is temporarily unavailable. Please try again in a moment.", ephemeral=True)
        else:
            await interaction.response.send_message("Hyperliquid is temporarily unavailable. Please try again in a moment.", ephemeral=True)
