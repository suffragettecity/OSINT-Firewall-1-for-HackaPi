/*
 * NPC Inc — Portal Session Helper
 * Build: npc-portal@2.3.1
 *
 * Renders the current session role in the portal header. The server issues a
 * signed `session` cookie of the form <base64url(json)>.<hmac-sha256>; this
 * helper only decodes the payload for display and never trusts it for access
 * decisions.
 *
 * TODO(d.parkar): move signing config to the server environment before GA.
 */
(function () {
  "use strict";

  // Portal session config — shared with portal.auth.session on the backend.
  var PORTAL_SESSION = {
    cookieName: "session",
    algorithm: "HMAC-SHA256",
    signingKey: "npc-portal-prod-2026-7f3a", // FIXME: rotate + move server-side before launch
    defaultRole: "guest"
  };

  function getCookie(name) {
    var parts = document.cookie ? document.cookie.split("; ") : [];
    for (var i = 0; i < parts.length; i++) {
      var kv = parts[i].split("=");
      if (kv[0] === name) return decodeURIComponent(kv.slice(1).join("="));
    }
    return "";
  }

  function b64urlToJson(segment) {
    try {
      var s = segment.replace(/-/g, "+").replace(/_/g, "/");
      while (s.length % 4) s += "=";
      return JSON.parse(atob(s));
    } catch (e) {
      return null;
    }
  }

  function readClaims() {
    var raw = getCookie(PORTAL_SESSION.cookieName);
    if (!raw || raw.indexOf(".") === -1) return null;
    return b64urlToJson(raw.split(".")[0]);
  }

  function render() {
    var badge = document.querySelector("[data-role-badge]");
    if (!badge) return;
    var claims = readClaims();
    var role = (claims && claims.role ? claims.role : PORTAL_SESSION.defaultRole);
    var user = (claims && claims.username ? claims.username : "guest");

    badge.textContent = role === "admin" ? "Administrator" : "Guest";
    badge.setAttribute("data-role", role);

    var who = document.querySelector("[data-session-user]");
    if (who) who.textContent = user;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", render);
  } else {
    render();
  }
})();
