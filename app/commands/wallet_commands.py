import discord
from discord import app_commands

from app.config import logger
from app.database import create_linked_wallet, get_linked_wallet, remove_linked_wallet
from app.exceptions import HyperliquidAPIError, WalletNotAssociatedError, WalletValidationError
from app.services.hyperliquid_client import ensure_hyperliquid_wallet
from app.utils import short_wallet, validate_wallet_input


async def link_wallet(interaction: discord.Interaction, wallet: str):
    try:
        value = validate_wallet_input(wallet)
    except WalletValidationError as exc:
        logger.warning("Wallet validation failed for %s: %s", interaction.user.id, exc)
        await interaction.response.send_message(str(exc), ephemeral=True)
        return

    if get_linked_wallet(interaction.user.id):
        await interaction.response.send_message(
            "A wallet is already linked to this account. Use `/unlink` before linking another wallet.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)
    try:
        await ensure_hyperliquid_wallet(value)
    except WalletNotAssociatedError as exc:
        await interaction.followup.send(str(exc), ephemeral=True)
        return
    except HyperliquidAPIError:
        logger.exception("Hyperliquid wallet verification failed")
        await interaction.followup.send(
            "Hyperliquid is temporarily unavailable. Please try again in a moment.",
            ephemeral=True,
        )
        return

    if not create_linked_wallet(interaction.user.id, value):
        await interaction.followup.send(
            "A wallet is already linked to this account. Use `/unlink` before linking another wallet.",
            ephemeral=True,
        )
        return

    await interaction.followup.send(
        f"Wallet linked: `{short_wallet(value)}`",
        ephemeral=True,
    )


async def show_linked_wallet(interaction: discord.Interaction):
    wallet = get_linked_wallet(interaction.user.id)
    if not wallet:
        await interaction.response.send_message(
            "No wallet linked. Use `/link wallet:<address>`.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        f"Your linked wallet: `{short_wallet(wallet)}`",
        ephemeral=True,
    )


async def unlink_wallet(interaction: discord.Interaction):
    if get_linked_wallet(interaction.user.id):
        remove_linked_wallet(interaction.user.id)
        await interaction.response.send_message(
            "Your wallet has been unlinked.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            "You don't have a linked wallet.",
            ephemeral=True,
        )
