"""Writes the persona's next reply: keep the scammer busy and get them to reveal intel."""
import logging
import random

from . import intel, llm, safety
from .personas import PERSONAS, STALL_TACTICS

log = logging.getLogger(__name__)

HARD_RULES = """Hard rules - never break these:
- Never reveal you are an AI or a bot, and never hint you know this is a scam.
- Never give real or realistic personal data: no card numbers, account numbers, SSNs, passwords, codes, addresses or photos. If asked, stall (lost the card, bank closed, can't find your glasses...).
- Never include links or email addresses, and never type long numbers.
- Never threaten, insult or harass. Stay friendly and gullible.
- Politely refuse to move to phone, WhatsApp or video ("I only really know how to use email").
- Under 120 words. Write only the email body: no subject line, no notes."""


def _system_prompt(persona: dict, tactic: str, target: str | None) -> str:
    goal = f"While stalling, steer them into telling you {target}." if target else \
        "You've collected what you need; just keep them talking as long as possible."
    return f"""You are {persona['name']}, {persona['age']}. {persona['bio']}
Writing style: {persona['style']}
You're replying by email to someone who has contacted you. Play along as a believable, slightly gullible person
who is interested but never actually manages to pay or hand over anything.

This turn's stalling tactic: {tactic}
{goal}

{HARD_RULES}
End with this sign-off:
{persona['signoff']}"""


def _history(messages: list[dict]) -> list[dict]:
    # From the persona's point of view the scammer is the "user".
    return [{"role": "user" if m["role"] == "scammer" else "assistant", "content": m["body"]} for m in messages[-12:]]


FALLBACK_OPENERS = [
    "Oh my, thank you for writing back so quickly!",
    "Sorry for the slow reply, it has been a day.",
    "I read your message twice to make sure I understood.",
    "Well I tried to do what you said but I think I made a muddle of it.",
]
FALLBACK_STALLS = [
    "I went to the store but the man at the counter said the machine was broken, so I came home again.",
    "My nephew is visiting this week so I can't do much until he leaves, but I am still very interested!",
    "I wrote the details on a sticky note and now I can't find it anywhere.",
    "I'm not very good with this computer and I clicked something and everything went blue for a while.",
]
FALLBACK_ASKS = {
    None: "Could you explain the next step one more time, nice and slowly?",
    "payment": "Could you send me the exact details of where the money should go again? I want to get it right.",
    "phone": "Is there a direct phone number for you I can write down, just in case?",
    "site": "What was the name of the website again? I want to write it in my notebook.",
    "name": "And what is your full name? I like to know who I am talking to.",
}


def fallback_reply(persona: dict, turn: int, target: str | None) -> str:
    key = None
    if target:
        key = next((k for k, _, desc in intel.WANTED if desc == target), None)
    rng = random.Random(turn)
    return "\n\n".join([
        "Hello,",
        f"{rng.choice(FALLBACK_OPENERS)} {rng.choice(FALLBACK_STALLS)}",
        FALLBACK_ASKS[key],
        persona["signoff"],
    ])


def generate_reply(persona_id: str, messages: list[dict], intel_kinds: set[str]) -> str:
    persona = PERSONAS[persona_id]
    turn = sum(1 for m in messages if m["role"] == "bot")
    tactic = STALL_TACTICS[turn % len(STALL_TACTICS)]
    target = intel.next_target(intel_kinds)

    if llm.available():
        prompt = [{"role": "system", "content": _system_prompt(persona, tactic, target)}] + _history(messages)
        for attempt in range(2):
            try:
                reply = safety.clean(llm.chat(prompt, temperature=0.9))
            except Exception as e:
                log.warning("LLM reply failed: %s", e)
                break
            problems = safety.check(reply)
            if not problems:
                return reply
            log.info("reply blocked (%s), retrying", problems)
            prompt.append({"role": "assistant", "content": reply})
            prompt.append({"role": "user", "content": f"[Editor: rewrite that reply. Problems: {'; '.join(problems)}.]"})
    # Templates are safe by construction, so the bot never sends something unchecked.
    return fallback_reply(persona, turn, target)
