"""Core flow: inbound scam -> classify -> pick persona -> reply; scammer replies -> extract intel -> reply."""
from . import baiter, classifier, config, intel, simulator, store
from .personas import pick_persona

ACTIVE = "engaged"


class ThreadClosed(Exception):
    pass


def estimate_effort(scammer_body: str, prev_bot_body: str) -> float:
    """Rough scammer-minutes per message: read our reply (~200 wpm) + type theirs (~40 wpm) + 1 min overhead."""
    return round(1 + len(scammer_body.split()) / 40 + len(prev_bot_body.split()) / 200, 2)


def _record_intel(thread_id: int, body: str):
    # A value already captured under one kind (e.g. an account number) shouldn't reappear as another (a "phone").
    seen = {i["value"] for i in store.get_thread(thread_id)["intel"]}
    items = []
    for kind, value in intel.extract(body) + intel.extract_identities(body):
        if value not in seen:
            seen.add(value)
            items.append((kind, value))
    store.add_intel(thread_id, items)


def _bot_turn(thread_id: int) -> str:
    t = store.get_thread(thread_id)
    reply = baiter.generate_reply(t["persona_id"], t["messages"], {i["kind"] for i in t["intel"]})
    store.add_message(thread_id, "bot", reply)
    return reply


def handle_inbound(sender: str, subject: str, body: str, mode: str = "manual") -> tuple[int, str | None]:
    """Returns (thread_id, bot reply or None if the bot didn't engage)."""
    if mode == "imap":
        existing = store.find_thread_by_sender(sender)
        if existing:
            return existing, handle_scammer_reply(existing, body)

    result = classifier.classify(sender, subject, body)
    if not result["is_scam"]:
        status = "ignored"
    elif mode == "imap" and result["confidence"] < config.AUTO_SEND_THRESHOLD:
        status = "needs_review"  # likely a scam, but a human confirms before we reply to a possibly-real person
    else:
        status = ACTIVE

    persona_id = pick_persona(result["scam_type"])
    thread_id = store.create_thread(sender, subject, result, persona_id, status, mode)
    store.add_message(thread_id, "scammer", body)
    if status == "ignored":
        return thread_id, None
    _record_intel(thread_id, body)
    return thread_id, (_bot_turn(thread_id) if status == ACTIVE else None)


def handle_scammer_reply(thread_id: int, body: str) -> str | None:
    t = store.get_thread(thread_id)
    if t is None or t["status"] in ("stopped", "ignored"):
        raise ThreadClosed(f"thread {thread_id} is not active")
    prev_bot = next((m["body"] for m in reversed(t["messages"]) if m["role"] == "bot"), "")
    store.add_message(thread_id, "scammer", body, estimate_effort(body, prev_bot))
    _record_intel(thread_id, body)
    return _bot_turn(thread_id) if t["status"] == ACTIVE else None


def approve(thread_id: int) -> str:
    store.set_status(thread_id, ACTIVE)
    return _bot_turn(thread_id)


def simulate_turn(thread_id: int) -> tuple[str, str | None]:
    t = store.get_thread(thread_id)
    if t is None or t["status"] != ACTIVE:
        raise ThreadClosed(f"thread {thread_id} is not active")
    scam_msg = simulator.scammer_reply(t["scam_type"], t["messages"], seed=thread_id)
    return scam_msg, handle_scammer_reply(thread_id, scam_msg)


def start_demo(sample_id: str) -> tuple[int, str | None]:
    sample = next(s for s in simulator.SAMPLES if s["id"] == sample_id)
    return handle_inbound(sample["sender"], sample["subject"], sample["body"], mode="sim")
