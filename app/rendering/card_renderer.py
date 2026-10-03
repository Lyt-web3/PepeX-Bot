import io
import random

import discord

import card

from app.config import MASCOT_PATH, THEME


def render_card(fn, filename, tag, owner_name=None, wallet_address=None, **kwargs):
    buf = io.BytesIO()
    theme = random.choice(list(card.THEMES)) if THEME == "random" else THEME
    fn(
        path=buf,
        theme=theme,
        mascot_path=MASCOT_PATH,
        tag=tag,
        owner_name=owner_name,
        wallet_address=wallet_address,
        **kwargs,
    )
    buf.seek(0)
    return discord.File(buf, filename=filename)
