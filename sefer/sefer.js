// The digital edition: reading settings, search, source notes, and "read and listen" with the recording.
(function () {
  "use strict";
  var root = document.documentElement;
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private mode */ } }
  };

  // ---- reading settings ---------------------------------------------------------------------
  var theme = store.get("sefer-theme");
  if (theme) root.dataset.theme = theme;
  var fs = parseFloat(store.get("sefer-fs")) || 0;
  function applyFs() { if (fs) root.style.setProperty("--fs", fs + "px"); }
  applyFs();
  function baseFs() { return parseFloat(getComputedStyle(root).getPropertyValue("--fs")) || 21; }
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-act]");
    if (!b) return;
    var act = b.dataset.act;
    if (act === "bigger" || act === "smaller") {
      fs = Math.max(15, Math.min(30, baseFs() + (act === "bigger" ? 1.5 : -1.5)));
      applyFs(); store.set("sefer-fs", fs);
    } else if (act === "theme") {
      var dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
      root.dataset.theme = dark ? "light" : "dark"; store.set("sefer-theme", root.dataset.theme);
    } else if (act === "search") {
      toggleSearch();
    }
  });

  // ---- search (niqqud is ignored) ----------------------------------------------------------
  var panel = document.getElementById("search"), input = document.getElementById("q"), list = document.getElementById("results");
  var index = null;
  var plain = function (s) {
    return s.replace(/[֑-ׇ]/g, function (c) { return c === "־" ? " " : ""; })
            .replace(/[״"׳']/g, "").replace(/\s+/g, " ");
  };
  function toggleSearch(force) {
    var open = force !== undefined ? force : !panel.classList.contains("open");
    panel.classList.toggle("open", open);
    if (open) { input.focus(); load(); }
  }
  function load() {
    if (index) return;
    fetch(document.body.dataset.root + "search.json").then(function (r) { return r.json(); }).then(function (j) { index = j; run(); })
      .catch(function () { list.innerHTML = '<li class="none">החיפוש אינו זמין כרגע.</li>'; });
  }
  function esc(s) { return s.replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function run() {
    var q = plain(input.value).trim();
    if (!index || q.length < 2) { list.innerHTML = ""; return; }
    var out = [], n = 0;
    for (var i = 0; i < index.length && n < 60; i++) {
      var p = index[i], at = p.x.indexOf(q);
      if (at < 0) continue;
      n++;
      var a = Math.max(0, at - 60), b = Math.min(p.x.length, at + q.length + 80);
      var snip = (a ? "…" : "") + esc(p.x.slice(a, at)) + "<mark>" + esc(p.x.slice(at, at + q.length)) + "</mark>" + esc(p.x.slice(at + q.length, b)) + (b < p.x.length ? "…" : "");
      out.push('<li><a href="' + document.body.dataset.root + p.d + ".html#p" + p.i + '"><span class="where">' + esc(p.h) + "</span>" + snip + "</a></li>");
    }
    list.innerHTML = out.length ? out.join("") : '<li class="none">לא נמצא.</li>';
  }
  if (input) {
    input.addEventListener("input", run);
    input.addEventListener("keydown", function (e) { if (e.key === "Escape") toggleSearch(false); });
  }

  // ---- source notes ---------------------------------------------------------------------------
  document.addEventListener("click", function (e) {
    var b = e.target.closest(".fn>button");
    document.querySelectorAll(".fn.open").forEach(function (f) { if (!b || f !== b.parentNode) { f.classList.remove("open"); f.firstChild.setAttribute("aria-expanded", "false"); } });
    if (b) {
      var open = !b.parentNode.classList.contains("open");
      b.parentNode.classList.toggle("open", open);
      b.setAttribute("aria-expanded", String(open));
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") document.querySelectorAll(".fn.open").forEach(function (f) { f.classList.remove("open"); });
  });

  // ---- arriving at a paragraph from search ----------------------------------------------------
  function flash() {
    var m = location.hash.match(/^#p(\d+)$/);
    if (!m) return;
    var p = document.getElementById("p" + m[1]);
    if (p) { p.classList.remove("flash"); void p.offsetWidth; p.classList.add("flash"); }
  }
  window.addEventListener("hashchange", flash);
  flash();

  // ---- read and listen ------------------------------------------------------------------------
  var video = document.querySelector(".video");
  if (!video) return;
  var slot = document.querySelector(".video-slot");
  var text = document.querySelector(".text");
  var follow = document.getElementById("follow");
  var paras = Array.prototype.slice.call(text.querySelectorAll("[data-t]"));
  var times = paras.map(function (p) { return +p.dataset.t; });
  var player = null, pending = null, current = null, timer = null, userScrolled = 0;

  function loadApi(cb) {
    if (window.YT && window.YT.Player) return cb();
    var prev = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = function () { if (prev) prev(); cb(); };
    var s = document.createElement("script");
    s.src = "https://www.youtube.com/iframe_api";
    document.head.appendChild(s);
  }
  function play(sec) {
    if (player && player.seekTo) { player.seekTo(sec, true); player.playVideo(); return; }
    pending = sec;
    if (video.querySelector(".yt")) return;  // the player is being created
    var holder = document.createElement("div");
    holder.className = "yt";
    video.appendChild(holder);
    loadApi(function () {
      player = new YT.Player(holder, {
        videoId: video.dataset.id,
        playerVars: { start: Math.floor(pending || 0), autoplay: 1, rel: 0, playsinline: 1 },
        events: {
          onReady: function () { video.querySelector(".poster").remove(); player.playVideo(); },
          onStateChange: function (e) { (e.data === 1 ? start : stop)(); }
        }
      });
    });
  }
  function start() { text.classList.add("playing"); if (!timer) timer = setInterval(tick, 400); }
  function stop() { text.classList.remove("playing"); clearInterval(timer); timer = null; }
  function tick() {
    if (!player || !player.getCurrentTime) return;
    var t = player.getCurrentTime(), k = -1;
    for (var i = 0; i < times.length; i++) { if (times[i] <= t + 0.5) k = i; else break; }
    var p = k >= 0 ? paras[k] : null;
    if (p === current) return;
    if (current) current.classList.remove("now");
    current = p;
    if (!p) return;
    p.classList.add("now");
    if (follow && follow.checked && Date.now() - userScrolled > 4000) p.scrollIntoView({ block: "center", behavior: "smooth" });
  }
  ["wheel", "touchmove"].forEach(function (ev) { window.addEventListener(ev, function () { userScrolled = Date.now(); }, { passive: true }); });

  video.querySelector(".poster").addEventListener("click", function () { play(0); });
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-seek]");
    if (!b) return;
    e.preventDefault();
    play(+b.dataset.seek);
  });

  // while playing, the recording follows the reader as a small window
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(function (en) {
      var out = !en[0].isIntersecting && en[0].boundingClientRect.top < 0;
      var mini = out && !!player;
      video.classList.toggle("mini", mini);
      slot.classList.toggle("on", mini);
    }, { threshold: 0 }).observe(document.querySelector(".video-anchor"));  // a marker just below the video's place
  }
})();
