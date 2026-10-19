# NPC Briefing Sheet — Firewall 3 Hint Ladder
### Directory Exploration & Forensics Challenge · Hack-A-PI

> For whichever organizer or exec is staffing Firewall 3 support. All hints
> are delivered **in person, in character** — no hints exist inside the
> container itself. Keep this sheet with you; keep it away from
> participants.

---

## Framing

By the time a team reaches Firewall 3, they've already SSH'd into "a server"
using credentials recovered from Firewall 2. There's no new NPC character
required here — Aya Nocari's earlier briefing (Firewall 1) already
established the "panicking intern who left a mess behind" narrative, and
this is the continuation of that same mess, just found deeper in the
filesystem. If an NPC is staffing this desk, they can stay in Aya's voice,
or hand off to a plain "SOC analyst" persona if a different person is
covering it.

**Energy, if continuing as Aya:** same as before — nervous, talks fast,
doesn't want to say the word "flag" or "exploit" out loud. She knows the
server has "more of this kind of stuff" buried in it and is hoping the team
cleans it up quietly.

---

## The three progressive hint lines

Give them **in order**, one per visit, only when a team is genuinely stuck
(see triggers). Each nudges toward the next stage without naming the exact
command.

### 🟦 Hint 1 — *Team is in the shell but can't find anything (stuck on directory exploration)*
**Trigger:** team has been running plain `ls` around the home directory for
~10 minutes without branching into `/srv`, `/var`, `/opt`.

> *"There's... a lot of junk on this thing, honestly. Old backups nobody
> cleaned up. If you're looking for something that actually belongs to a
> real person instead of just some generic config file, you might have
> better luck searching by who technically owns it instead of just
> scrolling through folders."*

*Points to:* **`find / -user aya` or similar ownership-based search,
instead of manual browsing.**

---

### 🟪 Hint 2 — *Team found the file but can't get past it (stuck on forensics)*
**Trigger:** team has located `.timesheet_aya.jpg`, maybe even opened it as
an image, but hasn't tried reading it as raw data.

> *"That's just a photo though, right? I mean... it should just be a photo.
> Unless someone was in a hurry and tacked something onto the end of it
> without thinking. You don't have to look at it — you could just look at
> what's actually inside it."*

*Points to:* **`file` to confirm it's still a JPEG, then `strings` to read
the raw bytes, revealing the leaked password line.**

---

### 🟥 Hint 3 — *Team has a password but doesn't know what to do with it*
**Trigger:** team has decoded something from the JPEG but hasn't tried
elevating privileges with it.

> *"Okay, if you found a password on this box, it's probably not for
> logging in again — you're already in. Think about what *else* you can do
> once you're already logged in, if you suddenly had someone else's
> password."*

*Points to:* **`su -` with the decoded password, escalating to root.**

---

## Escalation / guardrails

**Only advance one hint per visit.** If a team returns still stuck on the
*same* stage, give a tighter nudge rather than the next stage's line.

| If stuck on | Tighter nudge |
|---|---|
| Directory exploration | *"`find` has a flag for searching by file owner. Look it up."* |
| Forensics | *"Run `strings` on the file. Not open it — `strings` it."* |
| Escalation | *"The command is `su`. You already have a username. Now you have a password too."* |

**Never say out loud:**
- the flag strings, or that there even is a "flag";
- the literal command syntax verbatim (guide toward the tool, not the exact
  invocation);
- the words *flag, exploit, privilege escalation, root, CTF* if staying in
  Aya's character — she'd say "admin access" or "the higher-up account"
  instead.

**Scoring note:** same as Firewall 1's Aya hints — free, not drawn from any
LLM-token economy, since this is in-person narrative support rather than a
compute-limited resource.

---

## Notes specific to Firewall 3

- **Each team's container is isolated**, so if two teams are stuck on the
  same stage at the same time, there's no risk of one team's progress
  leaking to another via a shared hint — feel free to reuse the same hint
  language back-to-back for different teams without any cross-contamination
  concern.
- **If a team claims `su` "isn't working"**, the most common real cause is
  running the command non-interactively (e.g. through a scripted SSH
  one-liner rather than an open interactive session) — this is a support
  question, not a hint, so it's fine to just tell them directly: *"Make sure
  you're in a normal open terminal session, not running it as a single
  remote command."*
- **If a team asks about the optional third challenge** (malware cleanup),
  only mention it if that challenge is actually enabled for this event run
  — check with the tech lead whether `FLAG_C` was set during provisioning
  before promising it exists.
