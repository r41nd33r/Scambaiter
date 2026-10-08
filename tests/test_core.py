import os

os.environ["MOCK_LLM"] = "1"  # tests never call a real model

import pytest

from app import classifier, config, intel, safety, simulator, store


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    config.DB_PATH = tmp_path / "test.db"
    store.reset_connection()
    yield
    store.reset_connection()


# --- classifier ---

@pytest.mark.parametrize("sample", simulator.SAMPLES, ids=lambda s: s["id"])
def test_samples_are_flagged(sample):
    out = classifier.classify(sample["sender"], sample["subject"], sample["body"])
    assert out["is_scam"], out
    assert out["reasons"]


def test_normal_email_is_not_flagged():
    out = classifier.classify("prof@illinois.edu", "CS 124 MP due Friday",
                              "Hi all, reminder that the MP is due Friday at 11:59pm. See you in lecture.")
    assert not out["is_scam"]


def test_lookalike_domain_detected():
    reasons = [r for r, _ in classifier.link_signals("go to https://paypa1-secure.xyz/login now")]
    assert any("paypal" in r for r in reasons)
    assert any(".xyz" in r for r in reasons)


def test_real_brand_and_innocent_hosts_not_flagged():
    assert not classifier.link_signals("https://www.paypal.com/signin")
    assert not classifier.link_signals("https://pineapple.com/recipes")


# --- intel ---

def test_extracts_wallets_phone_site():
    d = simulator.fake_details(1)
    text = f"Send to {d['wallet']} or call {d['phone']}. Portal: https://{d['site']}/pay . Wire to account {d['account']}"
    kinds = {k for k, _ in intel.extract(text)}
    assert {"btc_wallet", "phone", "url", "bank_account"} <= kinds


def test_extract_eth_and_cashtag_and_email():
    found = dict(intel.extract("pay $ScamKing99 or 0x" + "a1" * 20 + " email me at boss@fraud.example"))
    assert found["cashtag"] == "$ScamKing99"
    assert found["eth_wallet"].startswith("0x")
    assert found["email"] == "boss@fraud.example"
    assert "domain" not in found  # domain inside the email isn't double-counted


def test_dollar_amount_is_not_cashtag():
    assert not [v for k, v in intel.extract("the fee is $250 today") if k == "cashtag"]


def test_next_target_priority():
    assert "payment" in intel.next_target(set())
    assert intel.next_target({"btc_wallet"}) == "a direct phone number"
    assert intel.next_target({"btc_wallet", "phone", "url", "name"}) is None


# --- safety ---

@pytest.mark.parametrize("bad", [
    "As an AI I cannot do that.",
    "Sure, my card is 4111 1111 1111 1111",
    "Visit https://example.com",
    "Email me at margaret@gmail.com",
    "I know this is a scam.",
])
def test_safety_blocks(bad):
    assert safety.check(bad)


def test_safety_allows_normal_reply():
    assert not safety.check("Oh dear, the store was closed! Could you tell me again where the money goes? God bless, Margaret")


def test_fallback_replies_are_always_safe():
    from app.baiter import fallback_reply
    from app.personas import PERSONAS
    for pid, p in PERSONAS.items():
        for turn in range(10):
            for _, _, target in intel.WANTED + [(None, None, None)]:
                assert not safety.check(fallback_reply(p, turn, target)), (pid, turn)


# --- end-to-end through the API ---

def test_api_demo_flow():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        r = client.post("/api/demo/lottery").json()
        tid = r["thread_id"]
        assert r["reply"] and r["thread"]["status"] == "engaged"
        for _ in range(4):
            assert client.post(f"/api/threads/{tid}/simulate").status_code == 200
        t = client.get(f"/api/threads/{tid}").json()
        assert len(t["messages"]) == 10
        assert t["minutes_wasted"] > 0
        kinds = {i["kind"] for i in t["intel"]}
        assert {"btc_wallet", "phone"} <= kinds and kinds & {"url", "domain"}

        stats = client.get("/api/stats").json()
        assert stats["payment_destinations"] >= 1

        report = client.get(f"/api/threads/{tid}/report").text
        assert "SIMULATION" in report and "Bitcoin wallet" in report

        client.post(f"/api/threads/{tid}/stop")
        assert client.post(f"/api/threads/{tid}/simulate").status_code == 409


def test_api_ignores_normal_email():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        r = client.post("/api/inbound", json={"sender": "mom@family.com", "subject": "dinner",
                                              "body": "Are you coming home for dinner Sunday?"}).json()
        assert r["reply"] is None and r["thread"]["status"] == "ignored"
