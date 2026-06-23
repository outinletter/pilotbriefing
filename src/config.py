import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    aviationstack_api_key: str = os.getenv("AVIATIONSTACK_API_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./ops_briefing.db")
    ops_intel_autostart: bool = os.getenv("OPS_INTEL_AUTOSTART", "1") == "1"
    ops_intel_interval_hours: int = int(os.getenv("OPS_INTEL_INTERVAL_HOURS", "24"))
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")


settings = Settings()
