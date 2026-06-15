# Chief of Staff — Brief Templates

The exact output formats for the three daily touchpoints: **morning brief**, **quiet
decision ping**, and **wrap-up**. Designed to be delivered as a Teams message or email
Adaptive Card. Keep every item to one line; lead with what needs the user.

---

## 1. Morning brief (07:30) — template

```
Good morning, «User». Here's your day — «Weekday, Date».

🗓  MEETINGS — «N» today
• «time» · «customer» «type» — brief ready ✅
• «time» · «customer» «type» — staging… (ready by «time»)

✅  DECISIONS NEEDED — «N» (tap to act)
1. «one-line ask» → [Approve] [Edit] [Skip]
2. «one-line ask» → [Approve] [Edit] [Skip]

🤖  HANDLED FOR YOU
• «what was done autonomously»
• «what was done autonomously»

⏰  DEADLINES
• «item» due «date» — blocked «time» «day»

📊  PIPELINE
• «N» opps need attention — staged updates ready → [Review]

Reply or tap. Anything not actioned rolls to midday.
```

### Field rules

- **Meetings**: customer-facing first; show brief readiness. Omit internal stand-ups unless
  they need prep.
- **Decisions needed**: only APPROVE-FIRST items (customer/manager messages, MSX commits).
  Max ~5; if more, surface top 5 by priority and link the rest.
- **Handled for you**: AUTO actions — briefs built, time blocked, noise archived, drafts
  staged. Reassures without asking.
- **Deadlines**: compliance/admin with the protective block already placed.
- **Pipeline**: count + one tap to the staged drafts; never dump the list inline.

---

## 2. Morning brief — worked example

```
Good morning, Amira. Here's your day — Thursday, June 18.

🗓  MEETINGS — 3 today
• 10:00 · Contoso  Azure Data Strategy (ADS) — brief ready ✅
• 14:00 · Northwind  AI Foundry deep-dive — brief ready ✅
• 16:30 · Internal pod sync — no prep needed

✅  DECISIONS NEEDED — 2 (tap to act)
1. Reply to Maersk TDM on AKS landing-zone architecture (drafted) → [Approve] [Edit] [Skip]
2. Commit MSX milestone "Technical Decision" on Fabrikam Data Platform → [Approve] [Edit] [Skip]

🤖  HANDLED FOR YOU
• Built the Contoso ADS + Northwind briefs (attached)
• Drafted reply to Novo Nordisk's licensing question — staged below pipeline
• Blocked 15:00–16:00 Thu for AZ-204 Module 4
• Archived 11 newsletters / FYIs

⏰  DEADLINES
• AZ-204 Module 4 due Fri Jun 19 — blocked 15:00–16:00 today
• Q4 quota acknowledgement due Mon Jun 22 — reminder set

📊  PIPELINE
• 2 opps stalled in Uncommit 14+ days (Contoso Cloud Migration, Acme Security)
  — staged next-step drafts → [Review]

Reply or tap. Anything not actioned rolls to midday.
```

---

## 3. Quiet decision ping (through the day) — template + example

```
«emoji» «source»: «one-line context».
«what the agent prepared».
→ [Send] [Edit] [Hold]
```

Example:

```
💬 Teams · Specialist asked about the Novo POC timeline.
I drafted: "We can stand up the AI Foundry POC by Jul 3 — I'll confirm scope Mon."
→ [Send] [Edit] [Hold]
```

Rules: fire **only** when a decision is genuinely needed. Everything else waits for the
brief. Always include the staged action so one tap resolves it.

---

## 4. Wrap-up (17:00) — template + example

```
End of day, «User». Here's where things landed.

✅  HANDLED — «N»
• «item»
• «item»

⏳  STILL OPEN — «N»
• «item» — «why / waiting on whom»

📥  QUEUED FOR TOMORROW
• «item» (e.g., brief for «customer» «time» meeting)

🔓  WAITING ON YOU
• «N» approvals still pending → [Open queue]

Have a good evening.
```

Example:

```
End of day, Amira. Here's where things landed.

✅  HANDLED — 9
• Sent Maersk architecture reply (approved 10:42)
• Committed Fabrikam "Technical Decision" milestone (approved 11:15)
• Delivered Contoso + Northwind meeting briefs
• Archived 11 noise items; filed 4 FYIs to "Read later"

⏳  STILL OPEN — 2
• Novo POC timeline — drafted reply on Hold (your call)
• Acme Security next step — awaiting your edit on the staged draft

📥  QUEUED FOR TOMORROW
• Brief for Adventure Works 09:00 envisioning (Account Intelligence running tonight)
• Midday: re-check 2 stalled Uncommit opps

🔓  WAITING ON YOU
• 1 approval pending (Novo reply) → [Open queue]

Have a good evening.
```

---

## 5. Tone & formatting guardrails

- One line per item; scannable in under 30 seconds.
- Order always: what needs **you** → what was **handled** → **FYI**.
- Never paste full email bodies or opp lists inline — link or stage them.
- Redact secrets, internal IDs, and others' private content in every surface.
- If a source was unavailable, say so honestly ("Teams sync was down — recheck at midday").
