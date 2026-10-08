import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, inbox, llm, report, service, simulator, store
from .personas import PERSONAS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("scambaiter")
STATIC = config.ROOT / "static"


async def poll_inbox():
    """Live mode: check the burner inbox, engage scams, send replies."""
    while True:
        try:
            for mail in await asyncio.to_thread(inbox.fetch_new):
                thread_id, reply = await asyncio.to_thread(
                    service.handle_inbound, mail["sender"], mail["subject"], mail["body"], "imap")
                if reply:
                    await asyncio.to_thread(inbox.send, mail["sender"], mail["subject"], reply, mail["message_id"])
                log.info("processed mail from %s -> thread %s (replied=%s)", mail["sender"], thread_id, bool(reply))
        except Exception:
            log.exception("inbox poll failed")
        await asyncio.sleep(config.POLL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.conn()
    task = asyncio.create_task(poll_inbox()) if config.INBOX_MODE == "imap" else None
    log.info("Scambaiter up | LLM: %s | inbox: %s",
             config.LLM_MODEL if llm.available() else "offline fallback", config.INBOX_MODE)
    yield
    if task:
        task.cancel()


app = FastAPI(title="Scambaiter", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class Inbound(BaseModel):
    sender: str = Field(default="unknown@unknown", max_length=320)
    subject: str = Field(default="", max_length=500)
    body: str = Field(min_length=1, max_length=20000)


class ScammerReply(BaseModel):
    body: str = Field(min_length=1, max_length=20000)


def _thread_or_404(thread_id: int) -> dict:
    t = store.get_thread(thread_id)
    if not t:
        raise HTTPException(404, "thread not found")
    return t


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/status")
def status():
    return {"llm": config.LLM_MODEL if llm.available() else None, "inbox_mode": config.INBOX_MODE,
            "threshold": config.SCAM_THRESHOLD}


@app.get("/api/samples")
def samples():
    return [{k: s[k] for k in ("id", "scam_type", "sender", "subject", "body")} for s in simulator.SAMPLES]


@app.get("/api/personas")
def personas():
    return PERSONAS


@app.get("/api/stats")
def stats():
    return store.stats()


@app.get("/api/threads")
def threads():
    return store.list_threads()


@app.get("/api/threads/{thread_id}")
def thread(thread_id: int):
    return _thread_or_404(thread_id)


@app.post("/api/inbound")
def inbound(msg: Inbound):
    """Manual mode: paste a scam you received. Copy the bot's reply back to the scammer from your burner account."""
    thread_id, reply = service.handle_inbound(msg.sender, msg.subject, msg.body, mode="manual")
    return {"thread_id": thread_id, "reply": reply, "thread": store.get_thread(thread_id)}


@app.post("/api/threads/{thread_id}/scammer")
def scammer_reply(thread_id: int, msg: ScammerReply):
    _thread_or_404(thread_id)
    try:
        reply = service.handle_scammer_reply(thread_id, msg.body)
    except service.ThreadClosed as e:
        raise HTTPException(409, str(e))
    return {"reply": reply, "thread": store.get_thread(thread_id)}


@app.post("/api/threads/{thread_id}/simulate")
def simulate(thread_id: int):
    _thread_or_404(thread_id)
    try:
        scam_msg, reply = service.simulate_turn(thread_id)
    except service.ThreadClosed as e:
        raise HTTPException(409, str(e))
    return {"scammer": scam_msg, "reply": reply, "thread": store.get_thread(thread_id)}


@app.post("/api/threads/{thread_id}/approve")
def approve(thread_id: int):
    t = _thread_or_404(thread_id)
    if t["status"] != "needs_review":
        raise HTTPException(409, "thread is not awaiting review")
    reply = service.approve(thread_id)
    if t["mode"] == "imap":
        inbox.send(t["sender"], t["subject"], reply)
    return {"reply": reply, "thread": store.get_thread(thread_id)}


@app.post("/api/threads/{thread_id}/stop")
def stop(thread_id: int):
    _thread_or_404(thread_id)
    store.set_status(thread_id, "stopped")
    return store.get_thread(thread_id)


@app.post("/api/demo/{sample_id}")
def demo(sample_id: str):
    if sample_id not in {s["id"] for s in simulator.SAMPLES}:
        raise HTTPException(404, "unknown sample")
    thread_id, reply = service.start_demo(sample_id)
    return {"thread_id": thread_id, "reply": reply, "thread": store.get_thread(thread_id)}


@app.get("/api/threads/{thread_id}/report", response_class=PlainTextResponse)
def thread_report(thread_id: int):
    return report.build(_thread_or_404(thread_id))
