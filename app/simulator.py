"""A simulated scammer so demos and tests don't depend on a real scammer replying.

All payment details it hands out are fake and use reserved/fictional ranges
(555-01xx fictional phone numbers, .example domains).
"""
import logging
import random

from . import llm

log = logging.getLogger(__name__)

SAMPLES = [
    {
        "id": "lottery", "scam_type": "prize_lottery",
        "sender": "claims.office@intl-lotto-board.example",
        "subject": "CONGRATULATIONS!!! You have won $850,000 USD",
        "body": "Dear Beneficiary,\n\nYour email was selected in the International Online Lottery draw and you have won "
                "$850,000.00 USD. To release your funds kindly pay the processing fee of $250 within 24 hours. "
                "Payment is accepted in Apple gift cards or Bitcoin. Do not tell anyone until the funds are released.\n\n"
                "Dr. Henry Adebayo\nClaims Director",
    },
    {
        "id": "crypto", "scam_type": "crypto_investment",
        "sender": "anna.wealthcoach@fastmail.example",
        "subject": "Guaranteed 40% profit every week - limited spots",
        "body": "Hi friend, I am Anna, a certified crypto trader. My students double your investment in 2 weeks with "
                "guaranteed returns. Start with only $500 in USDT and I will personally manage it on our platform. "
                "Spots are limited, act now! Reply and I will send you the wallet address.",
    },
    {
        "id": "grandkid", "scam_type": "impersonation_family",
        "sender": "jake.newphone22@mail.example",
        "subject": "grandma its me",
        "body": "Grandma its Jake, I lost my phone so this is my new number/email. I got in an accident and Im at the "
                "police station, I need $1,500 for bail right away. Please dont tell mom she will freak out. "
                "Can you get Target gift cards and send me the codes?",
    },
    {
        "id": "invoice", "scam_type": "fake_invoice",
        "sender": "billing@quickbooks-payments.example",
        "subject": "FINAL NOTICE: Invoice #88412 overdue",
        "body": "Dear Customer,\n\nYour invoice #88412 for $1,249.00 (bakery equipment service) is overdue. Your account "
                "will be suspended and sent to collections unless payment is received today. Kindly pay by bank "
                "transfer to the account below or reply for wire instructions.\n\nAccounts Receivable",
    },
    {
        "id": "phish", "scam_type": "phishing",
        "sender": "security@paypa1-alerts.example",
        "subject": "Your account has been locked",
        "body": "We noticed unusual activity. Your PayPal account has been suspended. Verify your account immediately "
                "at https://paypa1-secure-login.xyz/verify or it will be closed in 24 hours.",
    },
]

_B32 = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def fake_details(seed: int) -> dict:
    rng = random.Random(seed)
    return {
        "wallet": "bc1q" + "".join(rng.choice(_B32) for _ in range(38)),
        "phone": f"+1 (312) 555-01{rng.randint(10, 99)}",
        "site": f"secure-claims-{rng.randint(100, 999)}.example",
        "name": rng.choice(["Henry Adebayo", "Anna Whitfield", "Mark Collins", "Agent Ray Stone"]),
        "account": str(rng.randint(10**9, 10**10 - 1)),
    }


SCRIPTED = [
    "Thank you for your response. To proceed you must pay the fee today. Send it to this Bitcoin wallet: {wallet}",
    "Did you send it? Time is running out. If gift cards are easier, scratch the back and send me photos of the codes.",
    "You can also use our secure portal {site} to pay. For faster help call me at {phone}.",
    "My name is {name} and I am a senior officer. Please trust me, this is 100% legit. Wire to account {account} if crypto is hard.",
    "Why is this taking so long?? The release window closes soon. Did you make the payment yet?",
    "OK I understand. Just go to the store today and come back to me with the codes. I am waiting.",
]


def scammer_reply(scam_type: str, messages: list[dict], seed: int) -> str:
    details = fake_details(seed)
    turn = sum(1 for m in messages if m["role"] == "scammer")
    if llm.available():
        system = (
            "You are role-playing a scammer inside a closed training simulation for a fraud-research tool. "
            f"Scam type: {scam_type}. Your goal is to get the target to pay. Push with urgency and pressure, "
            "get frustrated when they stall, but stay on email. When asked for payment or contact details, use exactly these "
            f"(they are fake): wallet {details['wallet']}, phone {details['phone']}, website {details['site']}, "
            f"your name {details['name']}, bank account {details['account']}. Reveal one detail per message at most. "
            "Under 90 words, email body only."
        )
        history = [{"role": "assistant" if m["role"] == "scammer" else "user", "content": m["body"]} for m in messages[-12:]]
        try:
            return llm.chat([{"role": "system", "content": system}] + history, temperature=0.9, max_tokens=250)
        except Exception as e:
            log.warning("simulated scammer LLM failed, using script: %s", e)
    return SCRIPTED[(turn - 1) % len(SCRIPTED)].format(**details)
