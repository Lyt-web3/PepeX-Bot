import logging
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("pepex")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
HL_URL = "https://api.hyperliquid.xyz/info"
THEME = "neon"
MASCOT_PATH = str(BASE_DIR / "mascot.png")
DB_PATH = str(BASE_DIR / "bot.db")
DAY_MS = 24 * 60 * 60 * 1000
HTTP_TIMEOUT_SECONDS = 15
API_RETRY_ATTEMPTS = 3
API_BACKOFF_SECONDS = 0.5

MARKET_CHOICES = {
    "hl": "Hyperliquid",
    "entropy": "Entropy",
}
