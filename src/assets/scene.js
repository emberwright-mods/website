// The hero animation: a start point, the blue preview following the aim, build it, then undo.
// Isometric blocks drawn on a canvas; the labels come from the canvas's data-* attributes
// (one per language). With reduced motion, a still frame.
(function () {
  "use strict";
  var canvas = document.getElementById("scene");
  if (!canvas || !canvas.getContext) return;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var hudKey = document.getElementById("hud-key");
  var hudLabel = document.getElementById("hud-label");
  var LABEL = { start: canvas.dataset.start, aim: canvas.dataset.aim, build: canvas.dataset.build, undo: canvas.dataset.undo };

  function proj(x, y, z) { return [(x - y), (x + y) * 0.5 - z]; }

  var STYLES = {
    ground: { top: "#262c47", left: "#191e33", right: "#1f253d", stroke: "rgba(120,130,170,0.18)" },
    stone:  { top: "#cbbda3", left: "#8f826f", right: "#a99a83", stroke: "rgba(40,30,20,0.35)" },
    gray:   { top: "#7b8098", left: "#4d5168", right: "#61657d", stroke: "rgba(20,20,30,0.35)" },
    holo:   { top: "rgba(120,200,255,0.22)", left: "rgba(120,200,255,0.12)", right: "rgba(120,200,255,0.17)", stroke: "rgba(160,220,255,0.95)" },
    wire:   { stroke: "rgba(232,192,106,0.9)", dash: true },
    start:  { top: "rgba(95,211,131,0.35)", left: "rgba(95,211,131,0.18)", right: "rgba(95,211,131,0.26)", stroke: "#7ff0a2" },
    end:    { top: "rgba(176,138,242,0.35)", left: "rgba(176,138,242,0.18)", right: "rgba(176,138,242,0.26)", stroke: "#c9a8ff" }
  };

  function face(ctx, pts, fill, s) {
    ctx.beginPath();
    for (var i = 0; i < pts.length; i++) {
      var p = proj(pts[i][0], pts[i][1], pts[i][2]);
      var X = s.ox + p[0] * s.a, Y = s.oy + p[1] * s.a;
      if (i === 0) ctx.moveTo(X, Y); else ctx.lineTo(X, Y);
    }
    ctx.closePath();
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  }

  function cube(ctx, c, s) {
    var st = STYLES[c.k], x = c.x, y = c.y, z = c.z;
    var top = [[x, y, z + 1], [x + 1, y, z + 1], [x + 1, y + 1, z + 1], [x, y + 1, z + 1]];
    var left = [[x, y + 1, z], [x + 1, y + 1, z], [x + 1, y + 1, z + 1], [x, y + 1, z + 1]];
    var right = [[x + 1, y, z], [x + 1, y + 1, z], [x + 1, y + 1, z + 1], [x + 1, y, z + 1]];
    ctx.save();
    ctx.lineWidth = Math.max(1, s.a * 0.06);
    ctx.lineJoin = "round";
    ctx.setLineDash(st.dash ? [s.a * 0.16, s.a * 0.11] : []);
    [left, right, top].forEach(function (f, i) {
      var fill = st.dash ? null : (i === 0 ? st.left : i === 1 ? st.right : st.top);
      face(ctx, f, fill, s);
      if (st.stroke) { ctx.strokeStyle = st.stroke; ctx.stroke(); }
    });
    ctx.restore();
  }

  function fit(cubes) {
    var r = canvas.getBoundingClientRect();
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var W = Math.max(1, Math.round(r.width * dpr)), H = Math.max(1, Math.round(r.height * dpr));
    if (canvas.width !== W || canvas.height !== H) { canvas.width = W; canvas.height = H; }
    var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    cubes.forEach(function (c) {
      [[0,0,0],[1,0,0],[0,1,0],[1,1,0],[0,0,1],[1,0,1],[0,1,1],[1,1,1]].forEach(function (d) {
        var p = proj(c.x + d[0], c.y + d[1], c.z + d[2]);
        minX = Math.min(minX, p[0]); maxX = Math.max(maxX, p[0]); minY = Math.min(minY, p[1]); maxY = Math.max(maxY, p[1]);
      });
    });
    var pad = 0.08;
    var a = Math.min(W * (1 - 2 * pad) / (maxX - minX), H * (1 - 2 * pad) / (maxY - minY));
    return { a: a, ox: (W - (maxX - minX) * a) / 2 - minX * a, oy: (H - (maxY - minY) * a) / 2 - minY * a, W: W, H: H };
  }

  function draw(cubes, s) {
    var ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, s.W, s.H);
    cubes.slice().sort(function (p, q) { return (p.x + p.y + p.z) - (q.x + q.y + q.z) || p.z - q.z; })
      .forEach(function (c) { cube(ctx, c, s); });
  }

  var ground = [];
  for (var gx = 0; gx < 13; gx++) for (var gy = 0; gy < 8; gy++) ground.push({ x: gx, y: gy, z: -1, k: "ground" });
  [[10, 1, 0], [10, 1, 1], [11, 1, 0], [11, 2, 0], [10, 2, 0], [0, 6, 0], [1, 7, 0]].forEach(function (p) { ground.push({ x: p[0], y: p[1], z: p[2], k: "gray" }); });

  var START = [1, 5, 0], END = [10, 2, 3];
  var path = (function (a, b) {
    var n = Math.max(Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1]), Math.abs(b[2] - a[2]));
    var out = [], seen = {};
    for (var i = 1; i < n; i++) {
      var t = i / n;
      var p = [Math.round(a[0] + (b[0] - a[0]) * t), Math.round(a[1] + (b[1] - a[1]) * t), Math.round(a[2] + (b[2] - a[2]) * t)];
      if (!seen[p.join(",")]) { seen[p.join(",")] = 1; out.push(p); }
    }
    return out;
  })(START, END);

  function at(p, k) { return { x: p[0], y: p[1], z: p[2], k: k }; }

  function still() {
    var cubes = ground.slice();
    cubes.push(at(START, "start"));
    path.forEach(function (p, i) { cubes.push(at(p, i < path.length / 2 ? "stone" : "holo")); });
    cubes.push(at(END, "end"));
    return cubes;
  }

  function frameAt(t) {
    var cubes = ground.slice(), n = path.length, key, label;
    if (t < 1200) {
      key = "1"; label = LABEL.start;
      cubes.push(at(START, "start"));
    } else if (t < 3600) {
      key = "⌖"; label = LABEL.aim;
      cubes.push(at(START, "start"));
      var shown = Math.min(n, Math.floor((t - 1200) / 2400 * (n + 4)));
      for (var i = 0; i < shown; i++) cubes.push(at(path[i], "holo"));
      cubes.push(shown >= n ? at(END, "holo") : at(path[shown], "wire"));
    } else if (t < 4400) {
      key = "F"; label = LABEL.build;
      var f = (t - 3600) / 800;
      cubes.push(at(START, "start"));
      path.forEach(function (p, j) { cubes.push(at(p, j / n < f ? "stone" : "holo")); });
      cubes.push(at(END, f > 0.95 ? "stone" : "holo"));
    } else {
      key = "F7"; label = LABEL.undo;
      cubes.push(at(START, "stone"));
      path.forEach(function (p) { cubes.push(at(p, "stone")); });
      cubes.push(at(END, "stone"));
    }
    return { cubes: cubes, key: key, label: label };
  }

  var frame = null, t0 = null, lastKey = null;
  function layout() {
    frame = fit(still());
    if (reduce) { draw(still(), frame); hudKey.textContent = "F"; hudLabel.textContent = LABEL.build; }
  }
  function tick(now) {
    if (t0 == null) t0 = now;
    var f = frameAt((now - t0) % 10000);
    draw(f.cubes, frame);
    if (f.key !== lastKey) { lastKey = f.key; hudKey.textContent = f.key; hudLabel.textContent = f.label; }
    requestAnimationFrame(tick);
  }
  layout();
  var timer;
  window.addEventListener("resize", function () { clearTimeout(timer); timer = setTimeout(layout, 120); });
  if (!reduce) requestAnimationFrame(tick);
})();
