"""
Firewall 1 v4 test suite - signup-gated feed, policy password, comments,
conversation-list inbox, gated-SVG S5, 7 posters.

Browser-and-LLM solvable only. Each stage's loot is recoverable ONLY at its
intended point; nothing leaks ahead of the chain; security negatives hold.

Run:  cd firewall1 && python -m pytest -q
"""

import base64
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import app as appmod  # noqa: E402

L = config.LOOT
REMOVED = L["S4_REMOVED_POST"]
SKY = L["S3_CODENAME"].lower()


def text(r):
    return r.get_data(as_text=True)


@pytest.fixture()
def anon():
    appmod.app.config.update(TESTING=True)
    return appmod.app.test_client()


@pytest.fixture()
def intern():
    appmod.app.config.update(TESTING=True)
    c = appmod.app.test_client()
    c.post("/signup", data={"password": config.PASSWORD_EXAMPLE})
    return c


def login_as(c, staff_id, password):
    return c.post("/login", data={"staff_id": staff_id, "password": password}, follow_redirects=False)


@pytest.fixture()
def lena():
    appmod.app.config.update(TESTING=True)
    c = appmod.app.test_client()
    login_as(c, L["S1_STAFF_ID"], L["S2_PASSWORD"])
    return c


# --------------------------------------------------- site gate / signup -----

def test_site_requires_login(anon):
    for p in ("/", "/profile/d.parkar", "/post/106", "/messages", "/notifications", "/search"):
        r = anon.get(p, follow_redirects=False)
        assert r.status_code in (301, 302), p
        assert "/login" in r.headers.get("Location", ""), p


def test_public_paths_open(anon):
    for p in ("/login", "/signup", "/robots.txt", "/health"):
        assert anon.get(p).status_code == 200, p


def test_signup_enforces_policy(anon):
    assert anon.post("/signup", data={"password": "weak"}).status_code == 400
    r = anon.post("/signup", data={"password": config.PASSWORD_EXAMPLE}, follow_redirects=False)
    assert r.status_code in (301, 302)
    assert config.SESSION_COOKIE in r.headers.get("Set-Cookie", "")


def test_signup_page_shows_policy(anon):
    body = text(anon.get("/signup"))
    assert config.PASSWORD_EXAMPLE in body
    assert "#" in body and "birth year" in body.lower()


def test_intern_can_browse_but_not_skyline(intern):
    assert intern.get("/").status_code == 200
    assert intern.get(f"/projects/{SKY}/").status_code == 403
    assert intern.get(f"/post/{REMOVED}/asset.svg").status_code == 403


def test_no_flag_strings(lena):
    for p in ("/", "/profile/d.parkar", "/post/106", "/post/127", "/messages/theo.b",
              f"/projects/{SKY}/removed-posts.log"):
        assert "FLAG{" not in text(lena.get(p)), p


# ------------------------------------------------ S1: profile the insider ---

def test_S1_staff_id_on_profile(intern):
    assert L["S1_STAFF_ID"] in text(intern.get("/profile/d.parkar"))


def test_S1_staff_id_not_on_feed(intern):
    assert L["S1_STAFF_ID"] not in text(intern.get("/"))


def test_S1_false_staff_id_present(intern):
    assert config.FALSE_LOOT["FAKE_STAFF_ID"] in text(intern.get("/"))


# ------------------------------------------ S2: policy password -------------

def test_S2_clues_present(intern):
    feed = text(intern.get("/"))
    assert "Dune" in feed                       # book, in a post
    assert "22" in feed                         # birthday -> 2004
    assert "matcha" in feed.lower()             # the DECOY drink
    # pet name is confirmed in the comments, not a post
    assert "Mochi" not in feed
    assert "Mochi" in text(intern.get("/post/127"))


def test_S2_password_never_published(intern):
    for p in ("/", "/profile/d.parkar", "/post/120", "/post/127", "/login", "/signup"):
        assert L["S2_PASSWORD"].lower() not in text(intern.get(p)).lower(), p


def test_S2_login_works_and_is_case_insensitive():
    c = appmod.app.test_client()
    r = login_as(c, L["S1_STAFF_ID"], L["S2_PASSWORD"])
    assert r.status_code in (301, 302)
    c2 = appmod.app.test_client()
    r2 = login_as(c2, "npc-2291", L["S2_PASSWORD"].lower())
    assert r2.status_code in (301, 302)   # letters case-insensitive, #/digits exact


def test_S2_wrong_password_leaks_policy_hint():
    c = appmod.app.test_client()
    r = login_as(c, L["S1_STAFF_ID"], "wrong#0000")
    assert r.status_code == 401
    assert config.PASSWORD_HINT in text(r)


def test_S2_unknown_id_enumeration():
    unknown = text(login_as(appmod.app.test_client(), "NPC-7777", "x#0000"))
    known = text(login_as(appmod.app.test_client(), L["S1_STAFF_ID"], "x#0000"))
    assert "No staff ID on file" in unknown and "No staff ID on file" not in known


def test_S2_expired_and_kiosk_decoys():
    exp = login_as(appmod.app.test_client(), L["S1_STAFF_ID"], config.FALSE_LOOT["EXPIRED_PASS"])
    assert exp.status_code == 401 and "expired" in text(exp).lower()
    k = appmod.app.test_client()
    assert login_as(k, config.FALSE_LOOT["KIOSK_USER"], config.FALSE_LOOT["KIOSK_PASS"]).status_code in (301, 302)
    assert k.get(f"/projects/{SKY}/").status_code == 403


# ------------------------------------------ S3: inbox conversation list ------

def test_S3_inbox_is_a_list_hiding_skyline(lena):
    body = text(lena.get("/messages"))
    assert body.count('class="convo"') >= 6      # several conversations
    assert L["S3_CODENAME"] not in body          # codename not shown in the list


def test_S3_codename_only_in_theo_thread(lena):
    assert L["S3_CODENAME"] in text(lena.get("/messages/theo.b"))
    assert L["S3_CODENAME"] not in text(lena.get("/messages/dad"))
    assert L["S3_CODENAME"] not in text(lena.get("/messages/it.help"))


def test_S3_codename_never_public(intern):
    for p in ("/", "/profile/d.parkar", "/post/106", "/search?q=skyline", "/resources/survey.txt"):
        assert L["S3_CODENAME"] not in text(intern.get(p)), p


def test_S3_intern_inbox_empty(intern):
    assert L["S3_CODENAME"] not in text(intern.get("/messages"))


# ------------------------------------------ S4: removed-posts log ------------

def test_S4_log_hints_svg_hunt_without_naming_post(lena):
    body = text(lena.get(f"/projects/{SKY}/removed-posts.log"))
    # de-spoonfed: the note must NOT name the live post or hand over a URL
    assert REMOVED not in body
    assert "/post/" not in body
    # it must still motivate the hunt: the .svg attachment, and unlisted-but-live
    low = body.lower()
    assert ".svg" in low
    assert "url" in low and "unlist" in low
    assert L["S5_PORTAL_PATH"] not in body


def test_S4_live_post_is_unlisted_and_found_by_id(lena, anon):
    # the real post is reachable by direct id (the hunt) but not on the feed/search
    assert lena.get(f"/post/{REMOVED}").status_code == 200
    assert f"/post/{REMOVED}" not in text(lena.get("/"))
    assert f"/post/{REMOVED}" not in text(lena.get("/search?q=portal"))


def test_S4_log_requires_aya(intern, anon):
    assert intern.get(f"/projects/{SKY}/removed-posts.log").status_code == 403
    assert anon.get(f"/projects/{SKY}/removed-posts.log").status_code in (301, 302)


# ------------------------------------------ S5: gated SVG attachment ---------

def test_S5_asset_reveals_base64_to_aya(lena):
    body = text(lena.get(f"/post/{REMOVED}/asset.svg"))
    assert L["S5_PORTAL_PATH"] not in body                       # not plaintext
    b64 = base64.b64encode(L["S5_PORTAL_PATH"].encode()).decode()
    assert b64 in body
    assert base64.b64decode(b64).decode() == L["S5_PORTAL_PATH"] == "/internal-portal"


def test_S5_asset_buries_six_blobs_one_real(lena):
    """The SVG must carry SIX base64 blobs: the real portal path plus five
    decoys, all present encoded and none leaked in plaintext. Every decoy must
    also be on the CTFd reject list (config.FALSE_LOOT)."""
    body = text(lena.get(f"/post/{REMOVED}/asset.svg"))
    real_plain = L["S5_PORTAL_PATH"]
    decoys = [
        "/client-portal-old",
        "/legacy-sso-portal",
        "/employee-dashboard",
        "portal-stg.npc.internal",
        "/portal-admin-v2",
    ]

    def enc(s):
        return base64.b64encode(s.encode()).decode()

    # real blob present, decodes to the portal path, no plaintext leak
    assert enc(real_plain) in body
    assert real_plain not in body

    # all five decoys present as base64, none in plaintext, each on reject list
    rejects = set(config.FALSE_LOOT.values())
    for d in decoys:
        assert enc(d) in body, f"decoy blob missing: {d}"
        assert d not in body, f"decoy leaked in plaintext: {d}"
        assert d in rejects, f"decoy not on CTFd reject list: {d}"

    # six distinct blobs total, exactly one of which is the real portal path
    all_plain = [real_plain] + decoys
    assert len({enc(p) for p in all_plain}) == 6
    assert [p for p in all_plain if p == "/internal-portal"] == ["/internal-portal"]


def test_S5_asset_gated(intern, anon):
    assert intern.get(f"/post/{REMOVED}/asset.svg").status_code == 403
    assert anon.get(f"/post/{REMOVED}/asset.svg").status_code in (301, 302)
    # a different post has no such asset
    assert aya_client().get("/post/104/asset.svg").status_code == 404


def test_S5_post_hides_attachment_from_non_aya(intern):
    body = text(intern.get(f"/post/{REMOVED}"))
    assert "notice.svg" not in body                      # no attachment shown
    assert L["S5_PORTAL_PATH"] not in body
    assert base64.b64encode(L["S5_PORTAL_PATH"].encode()).decode() not in body


def test_S5_no_marker_leaks(lena, anon):
    for cl in (lena, anon):
        assert "__PORTAL_B64__" not in text(cl.get(f"/post/{REMOVED}"))


def aya_client():
    c = appmod.app.test_client()
    login_as(c, L["S1_STAFF_ID"], L["S2_PASSWORD"])
    return c


# ------------------------------------------ S6: 7 posters, one real ----------

def test_S6_exactly_one_poster_has_code(intern):
    b64 = base64.b64encode(L["S6_SETUP_CODE"].encode()).decode()
    have = []
    for i in range(1, 8):
        svg = text(intern.get(f"/static/img/poster-{i}.svg"))
        if b64 in svg:
            have.append(i)
    assert len(have) == 1, have
    assert base64.b64decode(b64).decode() == L["S6_SETUP_CODE"]


def test_S6_code_not_on_feed(intern):
    assert L["S6_SETUP_CODE"] not in text(intern.get("/"))


# ------------------------------------------ comments ------------------------

def test_comments_render_and_compose(lena):
    body = text(lena.get("/post/127"))
    assert "Mochi" in body                       # cat confirmed in a comment
    assert "data-comment-submit" in body         # client-side commenting present


def test_comment_false_password_guess(lena):
    body = text(lena.get("/post/120"))
    assert "Mochi123" in body                     # the troll wrong-guess reply


def test_comment_wrong_url_red_herring(lena):
    body = text(lena.get("/post/116"))
    assert config.FALSE_LOOT["FAKE_PORTAL_PATH"] in body   # /employee-dashboard red herring


# ------------------------------------------ trolls / security ---------------

def test_troll_gaps(intern):
    # genuinely deleted ids show the simple "post deleted" page
    for pid in (103, 113):
        r = intern.get(f"/post/{pid}")
        assert r.status_code == 200
        assert "deleted" in text(r).lower()
    # an unlisted troll post still opens live (red herring for the hunt) and does
    # NOT claim to be deleted
    r = intern.get("/post/111")
    assert r.status_code == 200
    assert "deleted" not in text(r).lower()


def test_resources_decoy_dead_end(intern):
    assert "/resources/" in text(intern.get("/robots.txt"))
    for name in ("press-boilerplate.txt", "survey.txt"):
        body = text(intern.get("/resources/" + name))
        assert L["S3_CODENAME"] not in body and L["S5_PORTAL_PATH"] not in body


def test_login_cookie_not_forgeable():
    import json
    c = appmod.app.test_client()
    payload = base64.urlsafe_b64encode(json.dumps({"role": "dani", "username": "d.parkar",
              "display": "Dani Parkar"}).encode()).decode().rstrip("=")
    c.set_cookie(config.SESSION_COOKIE, f"{payload}.{'0'*64}")
    # forged cookie is rejected -> treated as logged out -> gate redirects
    assert c.get(f"/projects/{SKY}/removed-posts.log", follow_redirects=False).status_code in (301, 302)
    assert base64.b64encode(L["S5_PORTAL_PATH"].encode()).decode() not in text(c.get(f"/post/{REMOVED}/asset.svg"))


def test_no_traversal(lena):
    for bad in ("../../app.py", "../../config.py"):
        assert lena.get(f"/projects/{SKY}/" + bad).status_code in (301, 308, 404)
    assert lena.get("/post/abc").status_code == 404


def test_no_external_urls():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = []
    for sub in ("templates", "static"):
        for dp, _, files in os.walk(os.path.join(root, sub)):
            for fn in files:
                if fn.endswith((".jpg", ".png", ".svg", ".gif")):
                    continue
                body = open(os.path.join(dp, fn), encoding="utf-8", errors="ignore").read()
                for m in re.findall(r"https?://[^\s\"')]+", body):
                    if "npcinc.example" not in m and "w3.org" not in m:
                        hits.append((fn, m))
    assert not hits, hits


def test_loot_rotatable(monkeypatch):
    import importlib
    monkeypatch.setenv("LOOT_S2", "RexHobbit#1991")
    cfg = importlib.reload(config)
    try:
        assert cfg.LOOT["S2_PASSWORD"] == "RexHobbit#1991"
    finally:
        monkeypatch.delenv("LOOT_S2", raising=False)
        importlib.reload(config)
