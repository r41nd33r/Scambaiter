# Devpost submission text (copy-paste)

## Project name
Scambaiter

## Elevator pitch (tagline)
An AI agent that answers scam emails as a gullible grandma, wasting scammers' time and collecting the wallets and phone numbers needed to shut them down.

## Track
AI + Cybersecurity

## Built with
python, fastapi, sqlite, featherless-ai, qwen, openai-sdk, imap, smtp, javascript, html, css

---

## About the project

### Inspiration
AI made scams cheap. One scammer can now send thousands of convincing, personalized messages, and older adults lose the most per victim. Spam filters block messages, but blocking costs the scammer nothing: they just move on to the next person. We wanted to flip that: make scammers *pay* for every message with the one thing they can't scale, which is their time.

### What it does
Scambaiter is an AI agent that lives in a burner email inbox. When a scam arrives, it:
1. **Detects** it with explainable rules (gift cards, fake urgency, secrecy, lookalike domains like `paypa1`) combined with an LLM verdict. Normal email is ignored.
2. **Engages** it as a believable persona matched to the scam: Margaret (78, retired librarian) for lottery scams, Dave (eager investor) for crypto, Gloria (lonely widow) for romance, Kevin (busy bakery owner) for fake invoices.
3. **Stalls** with a rotating set of tactics: the store was closed, she lost the sticky note, her grandson is visiting. Each reply is steered to make the scammer reveal **where the money goes**.
4. **Extracts intel**: Bitcoin/Ethereum/TRON wallets, bank accounts, IBANs, phone numbers, websites, Cash App tags, claimed names and organizations.
5. **Reports**: one click builds a report ready to file with the FTC or FBI IC3, with all intel and the full transcript.

A live dashboard shows estimated scammer-minutes wasted, payment destinations captured, and every conversation.

### How we built it
- **Backend:** Python + FastAPI, SQLite.
- **AI:** Qwen 2.5 72B via Featherless (OpenAI-compatible API) for scam classification, persona replies, a simulated adversarial scammer for testing, and identity extraction.
- **Detection:** a noisy-OR over 16 weighted rules plus link analysis (lookalike brands, IP links, shorteners, high-abuse TLDs), blended 60/40 with the LLM score. Explainable, and the rules can't be prompt-injected.
- **Agent loop:** each turn the persona gets a stall tactic and an *intel goal*: the most valuable thing we haven't extracted yet (payment destination, then phone, website, name).
- **Safety guard:** every outgoing reply is checked in code: no links, no email addresses, no long numbers, never admits being an AI, never hostile. Failing replies are regenerated, then replaced with safe templates.
- **Live email:** IMAP polling + SMTP replies on a burner Gmail.
- **Tests:** 21 pytest tests including an end-to-end conversation and a check that every fallback reply passes the safety filter.

### Challenges we ran into
- Keeping the persona believable while guaranteeing it never leaks anything that looks like real data. We solved it with a hard code-level filter instead of trusting the prompt.
- Demoing without waiting for a real scammer to reply, so we built a second AI agent that plays the scammer.
- Avoiding false engagement: the bot must never reply to a real person, so it has a confidence threshold, human approval for borderline cases, and skips automated senders.

### Accomplishments that we're proud of
- A fully working loop on real email: a scam lands in Gmail and the AI replies automatically within seconds.
- Explainable detection: every verdict lists *why*.
- Intel the authorities can actually act on, not just a chatbot.

### What we learned
Building agents is mostly about guardrails: the LLM does the creative part, and deterministic code makes sure it stays safe, in character and on goal.

### Ethics
Only confirmed scams are engaged. The bot never sends real or realistic personal data, never threatens or hacks back, and intel goes only to authorities. Personas are fictional, and voice/phone is out of scope because of call-recording consent laws.

### What's next for Scambaiter
- One-click forwarding address for anyone (Agentboxd inboxes)
- Shared intel across users: the same wallet in 50 threads is a priority takedown
- Auto-reporting to wallet blocklists and domain registrars
- Voice persona for phone scams
