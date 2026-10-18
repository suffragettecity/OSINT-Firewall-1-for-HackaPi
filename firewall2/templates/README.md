# Firewall 2 - NPC Inc Staff Portal (Web Exploitation)

The web-exploitation firewall for Hack-A-PI. A deliberately broken internal
staff portal for the fictional company **NPC Inc** (build `npc-portal@2.3.1`).
Players reach it from **Firewall 1** (the OSINT stage), which hands them the
path `/internal-portal`; from there they chain three web vulnerabilities to
recover a single flag.

> **This README is a map, not a spoiler.** The full solution, the flag value and
> the forged-cookie proof-of-concept live in `ORGANIZER_FLAGS.md` (organizers
> only - keep it off the participant network). The in-character hint ladder is
> in `NPC_BRIEFING_Dani_Parkar.md`.

## The challenge in one line

Broken access control: a signed session cookie whose signing key is leaked to
the browser, plus an IDOR on the incident-reports endpoint. One flag = the full
chain.

## The three stages (gated - you cannot skip ahead)

1. **Guest session.** Opening `/internal-portal` issues a signed `session`
   cookie with `role=guest`. The Admin Console card is locked
   ("Administrator access required").
2. **Privilege escalation (A05 -> A01).** `/static/js/session.js` leaks the
   HMAC signing key (`npc-portal-prod-2026-7f3a`). Forge a cookie with
   `role=admin`, sign it with that key, set it, and the Admin Console unlocks.
   (The signature *is* checked server-side, so you need the real key - flipping
   the payload alone gets a `403`.)
3. **IDOR (A01).** The admin dashboard lists restricted report **#4663** but
   disables its "View" button. The per-object endpoint
   `/internal-portal/incident/4663` does not re-check the restriction, so
   requesting it directly returns the report - the flag is in its
   runtime-context dump. (Its id is cited in report #2087.)

## Routes

| Path | Purpose |
|---|---|
| `/` `/services` `/about` `/login` | Public NPC Inc corporate site (cover) |
| `/robots.txt` `/health` | Standalone recon / health check |
| `/internal-portal` | Staff portal (issues the guest session) |
| `/internal-portal/admin` | Admin dashboard (requires `role=admin`) |
| `/internal-portal/incident/<id>` | Incident report (the IDOR target) |

## How it runs

- **In the event:** served as part of the combined site via `../combined.py`
  (one process, one address). The dispatcher routes `/internal-portal*` and
  F2's three static assets here; everything else is Firewall 1. Players arrive
  at `/internal-portal` from the F1 OSINT chain, so F2's own recon
  (robots.txt / `X-Powered-By` / an HTML comment) is unused by design.
- **Standalone (dev/testing):** `python app.py` (defaults to port 80; set
  `PORT` to override). All state is in memory - no database, no disk writes -
  so it is safe to restart at any time.

## State & deployment notes

- Incident data is an in-memory dict in `app.py`; the public pages are static
  templates. Nothing players do is persisted, so concurrent teams do not
  collide and a restart resets cleanly.
- The `session` cookie is **intentionally forgeable** (that is the challenge).
  It is unrelated to Firewall 1's own `pulse_session` cookie, so the two logins
  never interfere in the combined site.
- **Rotating the flag:** set the `FLAG` env var (see the F2 repo's
  `.env.example`) - it appears only in report #4663, no rebuild needed. Do not
  change the signing key unless you update it in **both** `app.py` and
  `static/js/session.js` (they must match), and then recompute the PoC cookie
  in `ORGANIZER_FLAGS.md`.

## Lore

The portal was pushed to production by a panicking first-month intern,
**Dani Parkar** (@d.parkar), during an SSO cutover - she skipped the auth gate,
left the signing key in the browser bundle, and let a crashed request dump
internal config into incident log #4663. She is the Firewall 1 insider and the
Firewall 2 NPC.
