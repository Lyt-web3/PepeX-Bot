# PepeX Bot

A Discord bot for generating Hyperliquid and Entropy trading cards.

## Structure

- app/bot.py - bot entry point
- app/commands - slash command handlers
- app/services - Hyperliquid and business logic
- app/rendering - card rendering
- app/database.py - wallet persistence
- app/config.py - environment settings

## Setup

1. Create a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and add your Discord token.
4. Run: `python main.py`

## Notes

This is a production-friendly layout for the current bot, separating command handling, services, rendering, and storage.
Wallets must be associated with Hyperliquid before they can be linked or used to generate cards. Unassociated addresses receive `THIS ADDRESS IS NOT ASSOCIATED WITH HYPERLIQUID`.
Unlinking deletes the wallet-to-Discord association from the database. The bot does not persist card or trading-history data; an unlinked account is excluded from linked-wallet leaderboards until linked again.
