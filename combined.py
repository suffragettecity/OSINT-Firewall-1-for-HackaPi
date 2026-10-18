"""
Hack-A-PI - Firewall 1 + Firewall 2, served as ONE site on ONE port.

A player browses the social feed (Firewall 1). The OSINT chain hands them the
path /internal-portal. On this combined server that path transparently serves
the staff portal (Firewall 2), so the site "becomes" F2 at exactly that point -
no second server, no second address.

HOW IT WORKS (and why it does not touch either app):
F1 and F2 are two separate, unmodified Flask apps. Both claim "/", "/login",
"/static", etc., so they cannot share one URL root inside one Flask app. Instead
this is a tiny WSGI dispatcher: it looks at the request path and hands the whole
request to F2 for the portal and F2's own assets, and to F1 for everything else.
Neither app's code or routes change; F2 stays frozen.

  /internal-portal, /internal-portal/...   -> Firewall 2 (staff portal)
  /services, /about                        -> Firewall 2 (its corporate pages)
  /static/css/app.css                      -> Firewall 2 (its Tailwind build)
  /static/js/session.js                    -> Firewall 2 (leaks the signing key)
  /static/img/favicon.svg                  -> Firewall 2 (its favicon)
  everything else (feed, login, /projects…) -> Firewall 1

F2 also defines "/" and "/login", and so does F1 (the feed and the F1 login).
Those two paths are routed by context: the Referer when it names a known F1 or
F2 page, and otherwise a dispatcher-set "which site am I in" cookie (so even a
click from F2's own landing page, whose Referer is just "/", stays in F2). A
first/direct hit with neither signal defaults to F1, the entry point.

The two apps use different session cookie names (F1: pulse_session, F2: session),
so their logins never collide.

Run (dev/event):  python combined.py        # waitress, Flask-style LAN banner
Default port 5000 (override with PORT).
"""

import importlib.util
import os
import socket
import sys
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))


def _load_app(folder: str, modname: str):
    """Import <folder>/app.py as `modname`, with <folder> on sys.path first so
    the app's own intra-package imports (e.g. F1's `import config`) resolve."""
    folder_abs = os.path.join(HERE, folder)
    sys.path.insert(0, folder_abs)
    spec = importlib.util.spec_from_file_location(modname, os.path.join(folder_abs, "app.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[modname] = module
    spec.loader.exec_module(module)
    return module.app


# Load Firewall 1 first (it puts its own folder on sys.path for `import config`),
# then Firewall 2 (self-contained).
f1_app = _load_app("firewall-1-osint", "f1_app_module")
f2_app = _load_app("firewall-2-web", "f2_app_module")


# Paths handled by Firewall 2. A path goes to F2 if it is the portal (or under
# it) or one of F2's own static assets; otherwise Firewall 1 handles it.
_F2_PORTAL_PREFIX = "/internal-portal"
# F2-only pages that do NOT collide with any F1 route, so the dispatcher can
# hand them straight to F2.
_F2_PAGES = frozenset({
    "/services",
    "/about",
})
_F2_STATIC = frozenset({
    "/static/css/app.css",
    "/static/js/session.js",
    "/static/img/favicon.svg",
    "/static/img/favicon.png",
})
# Paths that BOTH apps define. Ownership is decided per request: by the Referer
# when it points at a known F1 or F2 page, and otherwise by a dispatcher-set
# "which site am I in" cookie (default F1). This keeps F2's "Home" / logo /
# "Client Login" inside F2 even when clicked from F2's own landing page, while
# F1's feed and login keep these paths by default.
_F2_SHARED = frozenset({
    "/",
    "/login",
})


def _path_owned_by_f2(path: str) -> bool:
    """True for paths only Firewall 2 serves (portal, its pages, its assets)."""
    if path == _F2_PORTAL_PREFIX or path.startswith(_F2_PORTAL_PREFIX + "/"):
        return True
    return path in _F2_PAGES or path in _F2_STATIC


_SITE_COOKIE = "npc_site"   # dispatcher-only; records which app the visitor is in


def _referer_target(environ):
    """Which app the request was triggered FROM, by its same-host Referer:
    'f2', 'f1', or None when the Referer itself is a shared/ambiguous path
    (or missing, or cross-host)."""
    ref = environ.get("HTTP_REFERER", "")
    if not ref:
        return None
    try:
        u = urlsplit(ref)
    except ValueError:
        return None
    host = environ.get("HTTP_HOST", "")
    if u.netloc and host and u.netloc != host:
        return None                      # external referer - do not trust
    p = u.path or "/"
    if _path_owned_by_f2(p):
        return "f2"
    if p not in _F2_SHARED:
        return "f1"                      # an F1-only page
    return None                          # referer is itself "/" or "/login"


def _site_cookie(environ):
    """The dispatcher's remembered site ('f1'/'f2') from a previous response."""
    for part in environ.get("HTTP_COOKIE", "").split(";"):
        k, _, v = part.strip().partition("=")
        if k == _SITE_COOKIE and v in ("f1", "f2"):
            return v
    return None


def _resolve_target(environ, path: str) -> str:
    """Pick the app for this request. F2/F1-only paths are unambiguous. For the
    shared "/" and "/login" we go by the Referer; when that is also ambiguous we
    fall back to the remembered site cookie, defaulting to F1 (the entry point)."""
    if _path_owned_by_f2(path):
        return "f2"
    if path not in _F2_SHARED:
        return "f1"
    return _referer_target(environ) or _site_cookie(environ) or "f1"


def application(environ, start_response):
    path = environ.get("PATH_INFO", "") or "/"
    target = _resolve_target(environ, path)

    def _start(status, headers, exc_info=None):
        if not path.startswith("/static/"):          # never touch the site cookie on assets
            # Remember the site so a later click from a shared page ("/", "/login")
            # whose Referer is itself ambiguous still resolves the same way.
            headers = list(headers) + [
                ("Set-Cookie", f"{_SITE_COOKIE}={target}; Path=/; SameSite=Lax")
            ]
        return start_response(status, headers, exc_info)

    app = f2_app if target == "f2" else f1_app
    return app(environ, _start)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def _lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except OSError:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except OSError:
            ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def _banner(port: int):
    lines = [
        " * NPC Pulse + Staff Portal - Hack-A-PI (Firewall 1 -> 2, combined)",
        " * Running on all addresses (0.0.0.0)",
        f" * Running on http://127.0.0.1:{port}",
        f" * Running on http://{_lan_ip()}:{port}",
        " * Feed is here; /internal-portal is Firewall 2 on the same address.",
        "Press CTRL+C to quit",
    ]
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    host = os.environ.get("HOST", "0.0.0.0")
    _banner(port)
    try:
        from waitress import serve
        serve(application, host=host, port=port, threads=8)
    except ImportError:
        # Dev fallback: run F1's Flask dev server wrapped by the dispatcher.
        from werkzeug.serving import run_simple
        run_simple(host, port, application, threaded=True)
