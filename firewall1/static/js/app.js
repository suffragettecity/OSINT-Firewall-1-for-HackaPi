// NPC Pulse - progressive enhancement only. No external calls.
// The site is fully functional without JS; this just adds life. Composing a
// post is client-side only: it appears in YOUR feed, is never sent to the
// server, and vanishes on refresh. (Keeps the challenge state clean.)
(function () {
  "use strict";

  // "/" focuses search, like the real thing.
  document.addEventListener("keydown", function (e) {
    if (e.key === "/" && document.activeElement.tagName !== "INPUT" &&
        document.activeElement.tagName !== "TEXTAREA") {
      var box = document.querySelector(".searchbox input");
      if (box) { e.preventDefault(); box.focus(); }
    }
  });

  // Like / retweet toggles with a little pop. Wires any subtree (so freshly
  // composed posts get working buttons too).
  function wireToggles(root) {
    (root || document).querySelectorAll("[data-like],[data-rt]").forEach(function (btn) {
      if (btn._wired) return;
      btn._wired = true;
      btn.addEventListener("click", function () {
        var span = btn.querySelector("span[data-n]");
        if (!span) return;
        var n = parseInt(span.getAttribute("data-n"), 10) || 0;
        var on = btn.classList.toggle("on");
        span.textContent = on ? n + 1 : n;
        span.classList.remove("pop"); void span.offsetWidth; span.classList.add("pop");
      });
    });
  }
  wireToggles(document);

  // Follow buttons toggle.
  document.querySelectorAll("[data-follow]").forEach(function (b) {
    b.addEventListener("click", function () {
      var on = !b.classList.toggle("off");
      b.textContent = on ? "Following" : "Follow";
    });
  });

  // Compose focus from the sidebar "Post" button.
  document.querySelectorAll("[data-compose-focus]").forEach(function (b) {
    b.addEventListener("click", function () {
      var ta = document.querySelector("[data-compose]");
      if (ta) ta.focus();
    });
  });

  // Relative timestamps ("2d", "4h"), keeping the full date as a tooltip.
  function rel(tsStr) {
    var t = new Date(tsStr.replace(" ", "T"));
    if (isNaN(t)) return null;
    var s = Math.floor((Date.now() - t.getTime()) / 1000);
    if (s < 60) return s + "s";
    if (s < 3600) return Math.floor(s / 60) + "m";
    if (s < 86400) return Math.floor(s / 3600) + "h";
    if (s < 2592000) return Math.floor(s / 86400) + "d";
    return Math.floor(s / 2592000) + "mo";
  }
  function applyRel(root) {
    (root || document).querySelectorAll("[data-ts]").forEach(function (el) {
      var r = rel(el.getAttribute("data-ts"));
      if (r) { el.title = el.getAttribute("data-ts"); el.textContent = "· " + r; }
    });
  }
  applyRel(document);

  // ---- Composer (client-side only, ephemeral) -----------------------------
  var ta = document.querySelector("[data-compose]");
  if (ta) {
    var countEl = document.querySelector("[data-count]");
    var submit = document.querySelector("[data-compose-submit]");
    var feed = document.querySelector("[data-feed]");
    var imgBtn = document.querySelector("[data-compose-image]");
    var fileIn = document.querySelector("[data-compose-file]");
    var preview = document.querySelector("[data-compose-preview]");
    var previewImg = document.querySelector("[data-compose-preview-img]");
    var clearBtn = document.querySelector("[data-compose-preview-clear]");
    var pendingURL = null;

    function updateCount() {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 220) + "px";
      var left = 280 - ta.value.length;
      if (countEl) {
        countEl.textContent = String(left);
        countEl.classList.toggle("low", left <= 20);
      }
    }
    ta.addEventListener("input", updateCount);

    if (imgBtn && fileIn) {
      imgBtn.addEventListener("click", function () { fileIn.click(); });
      fileIn.addEventListener("change", function () {
        var f = fileIn.files && fileIn.files[0];
        if (!f) return;
        if (pendingURL) URL.revokeObjectURL(pendingURL);
        pendingURL = URL.createObjectURL(f);
        previewImg.src = pendingURL;
        if (preview) preview.classList.add("show");
      });
    }
    function clearImage() {
      if (pendingURL) { URL.revokeObjectURL(pendingURL); pendingURL = null; }
      if (fileIn) fileIn.value = "";
      if (preview) preview.classList.remove("show");
      if (previewImg) previewImg.removeAttribute("src");
    }
    if (clearBtn) clearBtn.addEventListener("click", clearImage);

    function el(tag, cls, text) {
      var e = document.createElement(tag);
      if (cls) e.className = cls;
      if (text != null) e.textContent = text;   // textContent -> no injection
      return e;
    }
    function actionBtn(cls, svg, n, dataAttr) {
      var b = el("button", "act " + cls);
      b.type = "button";
      if (dataAttr) b.setAttribute(dataAttr, "");
      b.innerHTML = svg;
      var s = el("span", null, String(n));
      if (dataAttr) s.setAttribute("data-n", String(n));
      b.appendChild(s);
      return b;
    }

    function addPost() {
      var body = ta.value.trim();
      if (!body && !pendingURL) return;

      var art = el("article", "post");
      var av = el("span", "avatar", "Y");
      av.style.background = "#2563eb";
      art.appendChild(av);

      var main = el("div", "post-main");
      var head = el("div", "post-head");
      head.appendChild(el("span", "name", "You"));
      head.appendChild(el("span", "handle", "@you"));
      var ts = el("span", "ts", "· now");
      head.appendChild(ts);
      main.appendChild(head);

      if (body) main.appendChild(el("div", "post-body", body));

      if (pendingURL) {
        var im = el("img", "post-img");
        im.src = pendingURL;
        im.alt = "attached media";
        main.appendChild(im);
        pendingURL = null;  // ownership moves to the rendered post
      }

      var actions = el("div", "actions");
      actions.appendChild(actionBtn("reply",
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>', 0));
      actions.appendChild(actionBtn("rt",
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>', 0, "data-rt"));
      actions.appendChild(actionBtn("like",
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1a5.5 5.5 0 1 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8z"/></svg>', 0, "data-like"));
      main.appendChild(actions);
      art.appendChild(main);

      if (feed) feed.insertBefore(art, feed.firstChild);
      wireToggles(art);

      ta.value = "";
      updateCount();
      clearImage();
      ta.focus();
    }

    if (submit) submit.addEventListener("click", addPost);
    ta.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); addPost(); }
    });
    updateCount();
  }
})();

// ---- Comment composer (client-side only, ephemeral) ----------------------
(function () {
  "use strict";
  var input = document.querySelector("[data-comment-input]");
  if (!input) return;
  var countEl = document.querySelector("[data-comment-count]");
  var submit = document.querySelector("[data-comment-submit]");
  var list = document.querySelector("[data-comments]");
  var emptyMsg = document.querySelector("[data-comment-empty]");

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function count() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 160) + "px";
    if (countEl) countEl.textContent = String(280 - input.value.length);
  }
  input.addEventListener("input", count);

  function add() {
    var body = input.value.trim();
    if (!body) return;
    if (emptyMsg) emptyMsg.remove();
    var c = el("div", "comment");
    var av = el("span", "avatar", "Y"); av.style.background = "#2563eb";
    c.appendChild(av);
    var main = el("div", "comment-main");
    var head = el("div", "comment-head");
    head.appendChild(el("span", "name", "You"));
    head.appendChild(el("span", "handle", "@you"));
    head.appendChild(el("span", "ts", "· now"));
    main.appendChild(head);
    main.appendChild(el("div", "comment-body", body));   // textContent -> no injection
    c.appendChild(main);
    if (list) list.appendChild(c);
    input.value = ""; count(); input.focus();
  }
  if (submit) submit.addEventListener("click", add);
  input.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); add(); }
  });
  count();
})();
