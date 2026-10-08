import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.featherless.ai/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-72B-Instruct")
# No key -> offline fallback mode so the app (and the demo) always runs.
MOCK_LLM = _bool("MOCK_LLM") or not LLM_API_KEY

DB_PATH = Path(os.getenv("DB_PATH", str(ROOT / "data" / "scambaiter.db")))

SCAM_THRESHOLD = float(os.getenv("SCAM_THRESHOLD", "0.7"))
AUTO_SEND_THRESHOLD = float(os.getenv("AUTO_SEND_THRESHOLD", "0.85"))

INBOX_MODE = os.getenv("INBOX_MODE", "manual")  # manual | imap
IMAP_HOST = os.getenv("IMAP_HOST", "")
IMAP_USER = os.getenv("IMAP_USER", "")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "60"))
