# Hack-A-PI - Firewall 1 + Firewall 2, one site, one port

This runs the OSINT social feed (**Firewall 1**) and the staff portal
(**Firewall 2**) as a **single website on a single address**. A player browses
the feed, recovers the path `/internal-portal` through the F1 chain, and when
they open it the site becomes the staff portal (F2) - no second server, no
second URL.

## Run

```bash
python3 -m venv venv && . venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python combined.py
```

It prints the addresses to connect to, e.g.:

```
 * NPC Pulse + Staff Portal - Hack-A-PI (Firewall 1 -> 2, combined)
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.0.191:5000
 * Feed is here; /internal-portal is Firewall 2 on the same address.
Press CTRL+C to quit
```

Players open `http://<LAN-IP>:5000/`. Default port **5000** (override with
`PORT`, e.g. `PORT=80 python combined.py`).

## How it is combined (and why F2 is untouched)

F1 and F2 are two separate Flask apps. Both define `/`, `/login`, `/static`,
etc., so they cannot share one URL root inside one Flask app. `combined.py` is a
tiny **WSGI dispatcher** that reads the request path and hands the whole request
to the right app - no code or routes in either app change, and **Firewall 2 stays
frozen**:

| Path | Served by |
|---|---|
| `/internal-portal`, `/internal-portal/...` | Firewall 2 (staff portal) |
| `/static/css/app.css`, `/static/js/session.js`, `/static/img/favicon.svg` | Firewall 2 (its own assets) |
| everything else (feed, `/login`, `/projects/...`, F1 assets) | Firewall 1 |

The two apps use different session cookie names (F1 `pulse_session`, F2
`session`), so their logins never collide, and F1's login cannot be used to
reach F2's admin (and vice versa).

## The full player journey on the one address

1. **F1 (feed):** profile Dani -> `NPC-2291`; feed + comments -> password
   `MochiDune#2004`; log in; inbox -> codename `SKYLINE`; `/projects/skyline/`
   -> `removed-posts.log` warns the attached `.svg` leaks info and that unlisted
   posts still open by URL; enumerate `/post/<id>` to find the still-live one
   (**106**); open it (as Dani) -> base64 in the SVG -> **`/internal-portal`**.
2. **F2 (same site):** open `/internal-portal` -> guest staff portal; read
   `/static/js/session.js` -> leaked signing key; forge an `admin` session
   cookie; open the Admin Console; IDOR into restricted incident **#4663** ->
   the flag `FLAG{...}`.

## CTFd

Score it as before - F1 stages S1-S6 and the F2 flag are unchanged. The only
difference is operational: one process, one address, one `python combined.py`.
F2's flag still rotates via the `FLAG` env var; F1's loot still rotates via its
own `.env` (see `firewall1/.env.example`).

## Layout

```
combined/
|- combined.py            the WSGI dispatcher + run banner (the only new code)
|- requirements.txt       Flask + waitress
|- firewall1/             Firewall 1, unchanged (feed, OSINT chain, its own tests/docs)
|- firewall2/             Firewall 2, verbatim and frozen (corporate site + staff portal)
```

Run Firewall 1's test suite any time with:

```bash
cd firewall1 && python -m pytest -q      # 37 passed
```
