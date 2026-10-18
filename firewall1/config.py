"""
NPC Inc - "NPC Pulse" internal social feed
Hack-A-PI - Firewall 1 (OSINT / Information-Disclosure recon stage)

This firewall is a pentest reconnaissance exercise, not a flag hunt. Players
exploit information disclosure on a company social feed and the submitted answer
is the real intel they recover (a staff ID, a password, a codename, a host, a
path, a code). No FLAG{...} strings anywhere.

CONNECTED CHAIN - each loot is the literal key to the next stage:
  S1  staff ID .......... NPC-2291 is Dani's login USERNAME
  S2  password .......... MochiDune#2004 (profiled from her posts) LOGS YOU IN
  S3  codename .......... SKYLINE (seen only in her inbox once logged in) is the
                          PROJECT FOLDER name -> /projects/skyline/
  S4  removed post ...... removed-posts.log lists her "deleted" posts; the trolls
                          are really gone, #106 is UNLISTED and STILL LIVE
  S5  portal path ....... open /post/106 (as Dani) -> base64 -> /internal-portal,
                          which UNLOCKS F2
  S6  setup code ........ bonus, hidden in a poster SVG

All loot values are read from the environment so they rotate per event without
touching code or content. An unset/empty value falls back to the default.
"""

import os

COMPANY = "NPC Inc"
SITE_NAME = "NPC Pulse"

# Firewall 2 handoff facts. These are the REAL values F2 uses; the end of the
# F1 chain discloses the portal path so recon (F1) pivots cleanly into
# exploitation (F2). Keep consistent with the frozen F2 build.
BUILD = "npc-portal@2.3.1"
PORTAL_PATH = "/internal-portal"


def _val(env_name: str, default: str) -> str:
    return os.environ.get(env_name) or default


# ---- Loot: the real intel players recover and submit to CTFd ----------------
# S5 (PORTAL_PATH) is the token that unlocks Firewall 2.
LOOT = {
    "S1_STAFF_ID": _val("LOOT_S1", "NPC-2291"),                      # on Dani's profile -> username
    "S2_PASSWORD": _val("LOOT_S2", "MochiDune#2004"),                # profiled from posts+comments -> login
    "S3_CODENAME": _val("LOOT_S3", "SKYLINE"),                       # in her inbox -> folder name
    "S4_REMOVED_POST": _val("LOOT_S4", "106"),                       # the "deleted" post still live
    "S5_PORTAL_PATH": PORTAL_PATH,                                   # base64 in /post/106's SVG -> unlocks F2
    "S6_SETUP_CODE": _val("LOOT_S6", "npc-setup-override-7731"),     # bonus, in a poster SVG
}

# Dani's password follows the company policy below. Her pieces, scattered across
# the feed and the comments (the matcha drink is a DECOY, not in the password):
#   pet  = Mochi   (she agrees to it in a comment)
#   book = Dune    (one of her posts)
#   year = 2004    (her birthday post: "turned 22")
#   symbol = #     (fixed by policy, right before the year)
# => MochiDune#2004

# The password policy shown on the signup page (interns set one too). It states
# only the SHAPE, not the recipe: two words, then #, then a 4-digit year. The
# "which two words" (pet + book, with matcha as a decoy) is never disclosed by
# the system; players recover it from the feed and the in-character banter. The
# example uses unrelated values so it never gives Dani's away.
PASSWORD_POLICY = ("at least 8 characters: two words that matter to you, "
                   "then # and your 4-digit birth year")
PASSWORD_EXAMPLE = "BingoNarnia#1998"
# Shape every password (interns' and Dani's) must match. Used to validate signup.
PASSWORD_PATTERN = r"^[A-Za-z]{2,}#\d{4}$"

# ---- Decoys (CTFd rejects these; documented so volunteers know) -------------
FALSE_LOOT = {
    "FAKE_STAFF_ID": "NPC-0001",                 # CEO's joke post
    "FAKE_PORTAL_PATH": "/employee-dashboard",   # Theo's "back in my day" post (also a S5 SVG decoy)
    "KIOSK_USER": "NPC-1001",                    # sticky-note creds: real login, useless account
    "KIOSK_PASS": "Welcome123!",
    "EXPIRED_PASS": "sunshine2004",              # Dani's old password: near miss, "expired"
    # Buried in post 106's SVG manifest (S5). Only /internal-portal is real;
    # these are plausible-but-wrong paths/hosts in the same file and must be
    # rejected. "/employee-dashboard" (above) is also one of the SVG decoys.
    "SVG_DECOY_CLIENT": "/client-portal-old",
    "SVG_DECOY_LEGACY": "/legacy-sso-portal",
    "SVG_DECOY_STG_HOST": "portal-stg.npc.internal",
    "SVG_DECOY_ADMIN": "/portal-admin-v2",
}

# Password hint disclosed when a VALID staff ID is given with the wrong password
# (a realistic "legacy self-service hint" info-disclosure bug). It echoes ONLY
# the shape, same as the signup policy: two words, then #, then a 4-digit year.
# It never names the categories (pet/book) or Dani's values.
PASSWORD_HINT = "word word # yyyy"

# ---- Login / session --------------------------------------------------------
# F1 runs its OWN signed-cookie session, INDEPENDENT of Firewall 2. This key is
# never served to the client (F1 is a credential-recovery challenge, not a
# cookie-forging one), so F2's leaked signing trick cannot be used to skip the
# F1 login. Rotatable; a fresh random key per boot also works if unset.
SESSION_KEY = _val("F1_SESSION_KEY", "npc-pulse-f1-sess-9e2c1a")
SESSION_COOKIE = "pulse_session"

# Credential table: staff_id (canonical) -> account. "role" drives access.
#   dani  -> full insider access (inbox + /projects/skyline/)
#   kiosk -> logs in, but a dead-end shared account (teaches: valid != useful)
ACCOUNTS = {
    LOOT["S1_STAFF_ID"].replace(" ", "").upper(): {
        "password": LOOT["S2_PASSWORD"],
        "expired_password": FALSE_LOOT["EXPIRED_PASS"],
        "role": "dani",
        "username": "d.parkar",
        "display": "Dani Parkar",
    },
    FALSE_LOOT["KIOSK_USER"].replace(" ", "").upper(): {
        "password": FALSE_LOOT["KIOSK_PASS"],
        "expired_password": None,
        "role": "kiosk",
        "username": "floor2.kiosk",
        "display": "Floor 2 Kiosk (shared)",
    },
}

# ---- Network. Default 5000 so it never clashes with Firewall 2 (host :80). --
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))
