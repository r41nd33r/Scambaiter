"""Turns a thread into a report a user can file with the FTC / IC3 or send to a domain/wallet abuse desk."""
from .intel import LABELS

REPORT_TO = [
    "FTC: https://reportfraud.ftc.gov",
    "FBI IC3 (internet crime, crypto): https://www.ic3.gov",
    "Phishing emails: forward to reportphishing@apwg.org",
    "Domains: the registrar's abuse contact (look up via WHOIS)",
]


def build(thread: dict) -> str:
    lines = [
        f"SCAM REPORT - thread #{thread['id']}",
        "=" * 48,
        f"First contact:   {thread['created_at']}",
        f"Sender:          {thread['sender']}",
        f"Subject:         {thread['subject']}",
        f"Scam type:       {thread['scam_type'].replace('_', ' ')}",
        f"Confidence:      {thread['confidence']:.0%}",
        f"Messages:        {len(thread['messages'])}",
        f"Est. scammer time wasted: {thread['minutes_wasted']} min",
        "",
        "WHY IT WAS FLAGGED",
        *[f"  - {r}" for r in thread["reasons"]],
        "",
        "INTEL COLLECTED (provided by the scammer)",
    ]
    if thread["intel"]:
        lines += [f"  - {LABELS.get(i['kind'], i['kind'])}: {i['value']}" for i in thread["intel"]]
    else:
        lines.append("  (none yet)")
    if thread["mode"] == "sim":
        lines += ["", "NOTE: this thread is a SIMULATION - intel above is fake and must not be reported."]
    lines += ["", "WHERE TO REPORT", *[f"  - {r}" for r in REPORT_TO], "", "TRANSCRIPT", "-" * 48]
    for m in thread["messages"]:
        who = "SCAMMER" if m["role"] == "scammer" else "BAIT PERSONA"
        lines += [f"[{m['created_at']}] {who}:", m["body"], ""]
    return "\n".join(lines)
