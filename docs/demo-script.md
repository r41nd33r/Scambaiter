# Demo video script (~3 min)

**0:00–0:30 · Problem**
"AI made scams cheap. One scammer can now send thousands of convincing messages. Spam filters block them, but that costs the scammer nothing; they just move on to the next person, often someone's grandparent."

**0:30–0:50 · Idea**
"Scambaiter flips it: instead of ignoring scams, an AI persona answers them, wastes the scammer's time, and gets them to reveal where the money goes."

**0:50–2:10 · Live demo**
1. Click **Demo: prize lottery**. Point at the right panel: 94% confidence, the reasons (gift cards, upfront fee, secrecy). "These come from explainable rules plus an LLM, so we can show *why*."
2. Show Margaret's first reply. "She's 78, polite, and can never quite manage to pay."
3. Click **Auto-run 4 turns**. Narrate as the scammer gets frustrated: the wallet, phone number and website get highlighted in yellow and appear under **Intel collected**.
4. Point at the stats bar: scammer minutes wasted, payment destinations captured.
5. Click **Report**: "This is ready to file with the FTC or FBI IC3."
6. Quick cut: paste a real scam via **+ New scam** to show it works on new input. Then paste a normal email and show it's **ignored**.

**2:10–2:40 · How it's built + safety**
Show the architecture diagram from the README. "A safety guard checks every outgoing message: no links, no numbers, never breaks cover. If the model slips, it's regenerated or replaced with a safe template."

**2:40–3:00 · Impact**
"Every minute a scammer spends on Margaret is a minute they're not spending on a real victim, and every wallet we capture can be reported and frozen."
