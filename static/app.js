const $ = (id) => document.getElementById(id);
const state = { threadId: null, personas: {}, seenIntel: new Set() };

const KIND_LABELS = {
  btc_wallet: "Bitcoin wallet", eth_wallet: "Ethereum wallet", tron_wallet: "TRON/USDT wallet",
  iban: "IBAN", bank_account: "Bank account", routing_number: "Routing number", email: "Email",
  url: "Website", domain: "Domain", phone: "Phone", cashtag: "Cash App tag",
  name: "Claimed name", organization: "Claimed organization", payment_method: "Payment method",
};

async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  return res.headers.get("content-type")?.includes("json") ? res.json() : res.text();
}

const esc = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function highlight(text, intel) {
  let html = esc(text);
  for (const { value } of intel) {
    const v = esc(value);
    if (v.length > 3) html = html.split(v).join(`<mark>${v}</mark>`);
  }
  return html;
}

async function refreshStats() {
  const s = await api("/api/stats");
  $("s-min").textContent = s.minutes_wasted;
  $("s-threads").textContent = s.threads_engaged;
  $("s-msgs").textContent = s.scammer_messages;
  $("s-pay").textContent = s.payment_destinations;
  $("s-intel").textContent = s.intel_items;
}

async function refreshThreads() {
  const threads = await api("/api/threads");
  $("thread-list").innerHTML = threads.map((t) => `
    <li data-id="${t.id}" class="${t.id === state.threadId ? "active" : ""}">
      <div class="t-subject">${esc(t.subject || "(no subject)")}</div>
      <div class="t-meta">
        <span class="badge ${t.status}">${t.status.replace("_", " ")}</span>
        ${t.mode === "sim" ? '<span class="badge">sim</span>' : ""}
        <span>${t.message_count} msgs · ${Math.round(t.minutes_wasted)} min</span>
      </div>
    </li>`).join("") || '<li class="muted">No threads yet</li>';
  document.querySelectorAll("#thread-list li[data-id]").forEach((li) =>
    li.addEventListener("click", () => openThread(Number(li.dataset.id))));
}

function renderThread(t) {
  state.threadId = t.id;
  $("empty").hidden = true;
  $("convo-view").hidden = false;
  const persona = state.personas[t.persona_id] || { name: "Bot" };
  $("c-subject").textContent = t.subject || "(no subject)";
  $("c-meta").textContent = `From ${t.sender} · ${t.scam_type.replace(/_/g, " ")} · playing ${persona.name}, ${persona.age} · ${t.minutes_wasted} scammer-min wasted`;

  const active = t.status === "engaged";
  $("sim-btn").hidden = $("auto-btn").hidden = !(active && t.mode === "sim");
  $("reply-form").hidden = !(active && t.mode !== "sim");
  $("approve-btn").hidden = t.status !== "needs_review";
  $("stop-btn").hidden = !active;

  $("messages").innerHTML = t.messages.map((m) => `
    <div class="msg ${m.role}">
      <div class="who"><span>${m.role === "scammer" ? "🦹 Scammer" : "🎣 " + esc(persona.name)}</span>
      ${m.effort_min ? `<span>~${m.effort_min} min of their time</span>` : ""}</div><div>${m.role === "scammer" ? highlight(m.body, t.intel) : esc(m.body)}</div></div>`).join("") +
    (t.status === "ignored" ? '<p class="muted">Not confident this is a scam, so the bot did not reply.</p>' : "") +
    (t.status === "needs_review" ? '<p class="muted">Likely a scam, waiting for a human to approve before replying.</p>' : "");
  $("messages").scrollTop = $("messages").scrollHeight;

  const pct = Math.round(t.confidence * 100);
  $("score").innerHTML = `<span class="score-num">${pct}%</span> <span class="muted">scam confidence</span>
    <div class="meter"><div style="width:${pct}%"></div></div>`;
  $("reasons").innerHTML = t.reasons.map((r) => `<li>${esc(r)}</li>`).join("") || '<li class="muted">No signals</li>';

  $("intel").innerHTML = t.intel.length ? t.intel.map((i) => {
    const key = `${t.id}|${i.kind}|${i.value}`;
    const fresh = !state.seenIntel.has(key);
    state.seenIntel.add(key);
    return `<li class="${fresh ? "fresh" : ""}"><span class="kind">${KIND_LABELS[i.kind] || i.kind}</span>${esc(i.value)}</li>`;
  }).join("") : '<li class="muted">Nothing yet</li>';
}

async function openThread(id) {
  renderThread(await api(`/api/threads/${id}`));
  refreshThreads();
}

function busy(on) {
  document.querySelectorAll(".actions button, .reply-form button, .demo-buttons button").forEach((b) => (b.disabled = on));
  const existing = document.querySelector(".typing");
  if (on && !existing) $("messages").insertAdjacentHTML("beforeend", '<div class="typing">typing…</div>');
  if (!on && existing) existing.remove();
}

async function run(fn) {
  busy(true);
  try {
    const out = await fn();
    if (out?.thread) renderThread(out.thread);
  } catch (e) {
    alert(e.message);
  } finally {
    busy(false);
    refreshThreads();
    refreshStats();
  }
}

const simulate = () => run(() => api(`/api/threads/${state.threadId}/simulate`, { method: "POST" }));

async function init() {
  const [status, samples, personas] = await Promise.all([api("/api/status"), api("/api/samples"), api("/api/personas")]);
  state.personas = personas;
  $("mode").textContent = `${status.llm ? "AI: " + status.llm.split("/").pop() : "Offline fallback mode"} · inbox: ${status.inbox_mode}`;
  $("demo-buttons").innerHTML = samples.map((s) =>
    `<button data-id="${s.id}">Demo: ${esc(s.scam_type.replace(/_/g, " "))}</button>`).join("");
  document.querySelectorAll("#demo-buttons button").forEach((b) =>
    b.addEventListener("click", () => run(() => api(`/api/demo/${b.dataset.id}`, { method: "POST" }))));

  $("new-btn").onclick = () => $("new-dialog").showModal();
  $("n-cancel").onclick = () => $("new-dialog").close();
  $("new-form").onsubmit = (e) => {
    e.preventDefault();
    const body = { sender: $("n-sender").value || "unknown@unknown", subject: $("n-subject").value, body: $("n-body").value };
    $("new-dialog").close();
    $("new-form").reset();
    run(() => api("/api/inbound", { method: "POST", body: JSON.stringify(body) }));
  };
  $("reply-form").onsubmit = (e) => {
    e.preventDefault();
    const body = $("reply-input").value.trim();
    if (!body) return;
    $("reply-input").value = "";
    run(() => api(`/api/threads/${state.threadId}/scammer`, { method: "POST", body: JSON.stringify({ body }) }));
  };
  $("sim-btn").onclick = simulate;
  $("auto-btn").onclick = async () => { for (let i = 0; i < 4 && !$("sim-btn").hidden; i++) await simulate(); };
  $("approve-btn").onclick = () => run(() => api(`/api/threads/${state.threadId}/approve`, { method: "POST" }));
  $("stop-btn").onclick = () => run(async () => ({ thread: await api(`/api/threads/${state.threadId}/stop`, { method: "POST" }) }));
  $("report-btn").onclick = async () => {
    $("report-text").textContent = await api(`/api/threads/${state.threadId}/report`);
    $("report-dialog").showModal();
  };
  $("copy-report").onclick = () => navigator.clipboard.writeText($("report-text").textContent);
  $("close-report").onclick = () => $("report-dialog").close();

  refreshThreads();
  refreshStats();
}

init();
