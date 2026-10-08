"""Guardrail on everything the bot sends. The LLM is told the rules; this enforces them."""
import re

BLOCKED_PHRASES = [
    "as an ai", "language model", "i am an ai", "i'm an ai", "i am a bot", "i'm a bot",
    "scambait", "scam bait", "wasting your time", "i know this is a scam", "you are a scammer",
    "report you", "reported you", "i will hack", "kill", "die",
]


def check(text: str) -> list[str]:
    """Returns a list of problems; empty means safe to send."""
    problems = []
    lowered = text.lower()
    if re.search(r"https?://|www\.", lowered):
        problems.append("contains a link")
    if re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text):
        problems.append("contains an email address")
    if re.search(r"\d(?:[\s-]?\d){5,}", text):
        problems.append("contains a long number (could look like account/card data)")
    for phrase in BLOCKED_PHRASES:
        if re.search(rf"\b{re.escape(phrase)}\b", lowered):
            problems.append(f"breaks cover or is hostile: '{phrase}'")
    if len(text.split()) > 220:
        problems.append("too long")
    return problems


def clean(text: str) -> str:
    """Strip artifacts LLMs add around an email body."""
    text = re.sub(r"^\s*subject:.*\n", "", text, flags=re.I)
    text = text.strip().strip('"').strip()
    return text
