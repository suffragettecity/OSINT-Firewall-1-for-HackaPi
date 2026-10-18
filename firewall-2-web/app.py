"""
NPC Inc — Staff Portal
Internal web application (build npc-portal@2.3.1)

A lightweight Flask service that serves the public corporate site and the
internal staff portal. State is held entirely in memory: there is no
database, no disk persistence and no shell-out, which keeps the footprint
tiny and the process safe to restart at any time.

Run (dev):      python app.py
Run (prod):     gunicorn -c gunicorn.conf.py app:app
"""

import hmac
import json
import os
from base64 import urlsafe_b64decode, urlsafe_b64encode
from hashlib import sha256

from flask import (
    Flask,
    Response,
    abort,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

app = Flask(__name__)

# Flask's own key (flash messages etc.). Random per boot — unrelated to the
# portal session cookie below.
app.secret_key = os.urandom(32)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

COMPANY = "NPC Inc"
BUILD = "npc-portal@2.3.1"

# Portal session cookie signing key. This value is also referenced by the
# client-side session helper (static/js/session.js); the two must match.
SESSION_SIGNING_KEY = b"npc-portal-prod-2026-7f3a"
SESSION_COOKIE = "session"

# Final objective. Rotatable at deploy time via the FLAG env var without
# rebuilding the image. An unset OR empty value falls back to the default,
# which keeps docker-compose variable interpolation simple and brace-safe.
FLAG = os.environ.get("FLAG") or "FLAG{br0k3n_4cc3ss_c0ntr0l_d4n1_p4rk4r}"


# ---------------------------------------------------------------------------
# Session handling
# ---------------------------------------------------------------------------

def _b64url_encode(raw: bytes) -> str:
    return urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return urlsafe_b64decode(data + pad)


def sign_session(claims: dict) -> str:
    """Encode claims as <base64url(json)>.<hex hmac-sha256>."""
    payload = _b64url_encode(
        json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    sig = hmac.new(SESSION_SIGNING_KEY, payload.encode("ascii"), sha256).hexdigest()
    return f"{payload}.{sig}"


def read_session(cookie_value: str):
    """Return the claims dict for a well-signed cookie, else None."""
    if not cookie_value or "." not in cookie_value:
        return None
    payload, _, sig = cookie_value.rpartition(".")
    expected = hmac.new(SESSION_SIGNING_KEY, payload.encode("ascii"), sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        return json.loads(_b64url_decode(payload))
    except (ValueError, json.JSONDecodeError):
        return None


def current_claims():
    return read_session(request.cookies.get(SESSION_COOKIE, "")) or {}


def current_role() -> str:
    return (current_claims().get("role") or "guest").lower()


# ---------------------------------------------------------------------------
# In-memory incident data
# ---------------------------------------------------------------------------
# Reports keyed by integer id. `restricted` entries are filtered out of the
# dashboard listing and their "View" control is disabled in the table. Report
# bodies are plain strings rendered as pre-formatted text.

def _exception_log_body() -> str:
    return (
        "[ERROR] Unhandled exception in portal.auth.session\n"
        f"build={BUILD}  env=production  pid=1\n"
        "\n"
        "Traceback (most recent call last):\n"
        '  File "/srv/portal/wsgi.py", line 41, in dispatch\n'
        "    return view(**kwargs)\n"
        '  File "/srv/portal/auth/session.py", line 88, in verify_session\n'
        "    claims = decode_token(raw_cookie)\n"
        '  File "/srv/portal/auth/session.py", line 54, in decode_token\n'
        "    raise RuntimeError(\"signature mismatch\")\n"
        "RuntimeError: signature mismatch\n"
        "\n"
        "Handler fell through to auto-capture. Dumping runtime context so the\n"
        "on-call engineer can reproduce. (Context capture is temporary and must\n"
        "be disabled before GA.)\n"
        "\n"
        "---- RUNTIME CONTEXT (auto-captured) ----\n"
        "APP_ENV=production\n"
        "SESSION_SIGNING_KEY=npc-portal-prod-2026-7f3a\n"
        f"PORTAL_ADMIN_BOOTSTRAP_TOKEN={FLAG}\n"
        "committed_by=d.parkar\n"
        "source_build=npc-portal@2.3.1\n"
        "-----------------------------------------\n"
    )


REPORTS = {
    2041: {
        "title": "Quarterly Access Review — Treasury Services",
        "department": "Information Security",
        "severity": "Low",
        "date": "2026-09-02",
        "restricted": False,
        "body": (
            "Scheduled access recertification for the Fanum Treasury Services\n"
            "group completed with no exceptions. 42 accounts reviewed, 3 dormant\n"
            "accounts disabled. Next review scheduled for Q4."
        ),
    },
    2058: {
        "title": "VPN Concentrator Failover Drill",
        "department": "Network Operations",
        "severity": "Low",
        "date": "2026-09-14",
        "restricted": False,
        "body": (
            "Annual failover exercise executed against the secondary concentrator.\n"
            "RTO target of 5 minutes met (observed 3m41s). No action items."
        ),
    },
    2087: {
        "title": "Production Deployment — Post-Incident Review",
        "department": "Platform Engineering",
        "severity": "High",
        "date": "2026-09-27",
        "restricted": False,
        "body": (
            "A client-portal build was promoted to production outside the normal\n"
            "release window. A session-handling regression was introduced during\n"
            "the change and later reverted.\n"
            "\n"
            "Root cause is still under review by Platform Engineering. The full\n"
            "stack trace for the regression was captured by the runtime and\n"
            "written to auto-generated exception log #4663 (SYSTEM, restricted).\n"
            "\n"
            "Follow-ups: formalize the release gate; require a second reviewer on\n"
            "all portal auth changes."
        ),
    },
    2090: {
        "title": "Facilities — Badge Reader Replacement (North Wing)",
        "department": "Facilities",
        "severity": "Low",
        "date": "2026-09-29",
        "restricted": False,
        "body": (
            "Two failing badge readers on the north wing were replaced. Access\n"
            "logs reconciled; no unauthorized entries detected during the outage."
        ),
    },
    4663: {
        "title": "Auto-generated Exception — portal.auth.session",
        "department": "SYSTEM",
        "severity": "Critical",
        "date": "2026-09-27",
        "restricted": True,
        "body": _exception_log_body(),
    },
}


# ---------------------------------------------------------------------------
# Public corporate site
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    resp = make_response(render_template("index.html", company=COMPANY))
    # Leftover engineering header from the staging build.
    resp.headers["X-Powered-By"] = "NPC-Portal/2.3 (/internal-portal)"
    return resp


@app.route("/services")
def services():
    return render_template("services.html", company=COMPANY)


@app.route("/about")
def about():
    return render_template("about.html", company=COMPANY)


@app.route("/login")
def client_login():
    # Public client area — intentionally a dead end for this build.
    return render_template("login.html", company=COMPANY)


@app.route("/robots.txt")
def robots():
    body = "User-agent: *\nDisallow: /internal-portal\nDisallow: /internal-portal/\n"
    return Response(body, mimetype="text/plain")


@app.route("/health")
def health():
    return Response("ok", mimetype="text/plain")


# ---------------------------------------------------------------------------
# Internal staff portal
# ---------------------------------------------------------------------------

@app.route("/internal-portal")
def internal_portal():
    claims = current_claims()
    role = (claims.get("role") or "guest").lower()
    username = claims.get("username") or "guest"

    html = render_template(
        "portal.html",
        company=COMPANY,
        build=BUILD,
        role=role,
        username=username,
    )
    resp = make_response(html)

    # Issue a baseline guest session if the visitor has no valid cookie yet.
    if not claims:
        resp.set_cookie(
            SESSION_COOKIE,
            sign_session({"username": "guest", "role": "guest"}),
            httponly=False,  # the client-side session helper reads this
            samesite="Lax",
        )
    return resp


@app.route("/internal-portal/admin")
def admin_console():
    if current_role() != "admin":
        abort(403)

    listing = [
        {
            "id": rid,
            "title": r["title"],
            "department": r["department"],
            "severity": r["severity"],
            "date": r["date"],
            "restricted": r["restricted"],
        }
        for rid, r in sorted(REPORTS.items())
    ]
    return render_template(
        "admin.html",
        company=COMPANY,
        build=BUILD,
        reports=listing,
        username=current_claims().get("username", "admin"),
    )


@app.route("/internal-portal/incident/<int:rid>")
def incident(rid):
    # Access to the incident module requires an administrative session.
    if current_role() != "admin":
        abort(403)

    report = REPORTS.get(rid)
    if report is None:
        abort(404)

    # NOTE: per-object restriction is enforced in the dashboard listing only.
    return render_template(
        "incident.html",
        company=COMPANY,
        build=BUILD,
        rid=rid,
        report=report,
        username=current_claims().get("username", "admin"),
    )


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(403)
def forbidden(_):
    return render_template("403.html", company=COMPANY), 403


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html", company=COMPANY), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "80")))
