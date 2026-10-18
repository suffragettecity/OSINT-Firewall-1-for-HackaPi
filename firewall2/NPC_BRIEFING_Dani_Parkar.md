# NPC Briefing Sheet — **Dani Parkar, "The Panicking Intern"**
### Firewall 2 (Web Application Challenge) · Hack-A-PI

> For the organizer roleplaying Dani. All hints are delivered **in person, in
> character.** There are zero hints inside the app itself — you are the hint
> system. Keep this sheet with you; keep it away from participants.

> **Combined-event note:** players reach the staff portal (`/internal-portal`)
> by solving **Firewall 1** (the OSINT stage) first — so by the time they talk
> to Dani they already have the portal open as "guest." In the combined event
> **start at Hint 2** (forge the cookie). Hint 1 (find the portal) is only
> needed if you are running this web challenge on its own.

---

## Who she is

Dani Parkar is a first-month software intern at the company. Three
weeks ago she pushed a half-finished "staff portal" build straight to
production to hit a deadline — skipping the auth gate, leaving a dev config in
the browser bundle, and letting a crashed request dump internal context into a
log. She knows *something* is wrong. She does **not** want her manager to find
out. She is helpful to the "security consultants" (the players) only because
she's hoping they'll quietly make the problem go away before anyone notices.

**Energy:** nervous, over-caffeinated, talks fast, overshares then catches
herself. Friendly, not hostile. She is **not** trying to stop the players —
she's trying to look like she has it handled while accidentally helping them.

**How to play her:** clutch a laptop or notebook. Glance over your shoulder
before "admitting" things. Deflect with "it's probably fine though, right?"
Downplay, then leak one useful detail. Never break into CTF-speak ("flag",
"exploit", "privesc") — stay a stressed intern the whole time.

---

## The three progressive hint lines

Give them **in order**, one per visit, only when a team is genuinely stuck at
that stage (see triggers). Each line nudges toward the next stage without naming
the technique.

### 🟦 Hint 1 — *Team can't find a way in (stuck at recon)*
> **Combined event:** normally not needed — Firewall 1 hands teams the portal
> path. Use this only if running the web challenge standalone.

**Trigger:** team has only seen the public marketing site / is poking the broken
Client Login for more than ~10 min.

> *"Oh — no, no, the client login's been down for ages, don't waste your time on
> that. Look… between us? When we moved the staff portal for the SSO thing I
> never actually took the old address out of the page. It's still in there if
> you actually* read *the page instead of just looking at it. Please don't tell
> Marwan I said that."*

*Points to:* **View Source / robots.txt / response headers → `/internal-portal`.**

---

### 🟪 Hint 2 — *Team is in as "guest" but can't become admin*
**Trigger:** team has reached `/internal-portal`, sees the locked **Admin
Console** ("Administrator access required"), and has been stuck on it ~10–15 min.

> *"Yeah, it drops you in as a guest, that part works… The admin check reads your
> session cookie — it's signed so you can't just, like, fiddle with it, I did do
> that part. The signing key's meant to live on the server though and I, um…
> I think I left the config in the file the browser downloads to draw the little
> role badge. The JavaScript one. If anyone opens that it's basically game over,
> so… don't, obviously."*

*Points to:* **`/static/js/session.js` → leaked `signingKey` → forge an `admin`
cookie and re-sign it.**

---

### 🟥 Hint 3 — *Team is admin but can't find the objective*
**Trigger:** team has admin access (badge says **Administrator**, dashboard
opens) but has only read the normal reports for ~10–15 min.

> *"Okay you really shouldn't be able to see all that… Look, the one you want
> isn't in the list you can click — it's the auto-generated one, the SYSTEM crash
> report. I greyed out the button so nobody opens it. But the page itself still
> loads if you go straight to its number… it's referenced in the deployment
> post-mortem. When it crashed it dumped a whole pile of our config into that
> log. That's the thing I've been trying to delete all week."*

*Points to:* **IDOR — open `/internal-portal/incident/4663` directly (its id is
cited in report #2087); the flag is in the context dump.**

---

## Escalation / guardrails

**Only advance one hint per visit.** If a team returns still stuck on the *same*
stage, give a tighter nudge (below) rather than the next stage's line.

| If stuck on | Tighter nudge (still in character) |
|---|---|
| Recon | *"It's not a secret page, it's just… not linked. Right-click. Look at the actual source."* |
| Escalation | *"The browser literally downloads the key to draw a badge. Open the .js file. It's the only one."* |
| IDOR | *"Report twenty-eighty-seven mentions a number. Put that number in the address bar instead of the one you clicked."* |

**Never say out loud:**
- the flag string, or that there even is a "flag" (she'd call it "the config
  dump" / "the thing I need to delete");
- the exact signing-key value or the exact forged cookie — make them open the
  JS file themselves;
- the words *flag, exploit, privilege escalation, IDOR, CTF.* Stay an intern.

**Pacing tie-in:** these three lines also map cleanly onto the scheduled Intel
Drops (90 / 120 / 150 min). If you're running the whiteboard drops *and* Dani,
use Dani for teams who come to the desk and the whiteboard for the room-wide
floor; don't give the same team both for the same stage.

**Scoring note:** Dani hints are free (she's panicking, not charging). If you're
using the LLM-token economy for the main-event support desk, keep Dani **outside**
it — she's narrative, not a compute-limited resource.
