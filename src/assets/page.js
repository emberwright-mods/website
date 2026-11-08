// The full page: the small block drawings of the tools, and the copy button of the SHA-256.
(function () {
  "use strict";

  // ---------- Tool drawings (isometric blocks on a canvas) ----------
  function proj(x, y, z) { return [(x - y), (x + y) * 0.5 - z]; }
  var STYLES = {
    ground: { top: "#262c47", left: "#191e33", right: "#1f253d", stroke: "rgba(120,130,170,0.18)" },
    stone:  { top: "#cbbda3", left: "#8f826f", right: "#a99a83", stroke: "rgba(40,30,20,0.35)" },
    gold:   { top: "#e2b65a", left: "#a9822f", right: "#c29a45", stroke: "rgba(60,40,10,0.35)" },
    gray:   { top: "#7b8098", left: "#4d5168", right: "#61657d", stroke: "rgba(20,20,30,0.35)" },
    holo:   { top: "rgba(120,200,255,0.22)", left: "rgba(120,200,255,0.12)", right: "rgba(120,200,255,0.17)", stroke: "rgba(160,220,255,0.95)" }
  };
  function face(ctx, pts, fill, s) {
    ctx.beginPath();
    pts.forEach(function (pt, i) {
      var p = proj(pt[0], pt[1], pt[2]);
      var X = s.ox + p[0] * s.a, Y = s.oy + p[1] * s.a;
      if (i === 0) ctx.moveTo(X, Y); else ctx.lineTo(X, Y);
    });
    ctx.closePath();
    ctx.fillStyle = fill; ctx.fill();
  }
  function cube(ctx, c, s) {
    var st = STYLES[c.k], x = c.x, y = c.y, z = c.z;
    var faces = [
      [[x, y + 1, z], [x + 1, y + 1, z], [x + 1, y + 1, z + 1], [x, y + 1, z + 1]],
      [[x + 1, y, z], [x + 1, y + 1, z], [x + 1, y + 1, z + 1], [x + 1, y, z + 1]],
      [[x, y, z + 1], [x + 1, y, z + 1], [x + 1, y + 1, z + 1], [x, y + 1, z + 1]]
    ];
    ctx.lineWidth = Math.max(1, s.a * 0.06);
    ctx.lineJoin = "round";
    faces.forEach(function (f, i) {
      face(ctx, f, i === 0 ? st.left : i === 1 ? st.right : st.top, s);
      ctx.strokeStyle = st.stroke; ctx.stroke();
    });
  }
  function draw(canvas, cubes) {
    var r = canvas.getBoundingClientRect();
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var W = Math.max(1, Math.round(r.width * dpr)), H = Math.max(1, Math.round(r.height * dpr));
    canvas.width = W; canvas.height = H;
    var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    cubes.forEach(function (c) {
      [[0,0,0],[1,0,0],[0,1,0],[1,1,0],[0,0,1],[1,0,1],[0,1,1],[1,1,1]].forEach(function (d) {
        var p = proj(c.x + d[0], c.y + d[1], c.z + d[2]);
        minX = Math.min(minX, p[0]); maxX = Math.max(maxX, p[0]); minY = Math.min(minY, p[1]); maxY = Math.max(maxY, p[1]);
      });
    });
    var pad = 0.1;
    var a = Math.min(W * (1 - 2 * pad) / (maxX - minX), H * (1 - 2 * pad) / (maxY - minY));
    var s = { a: a, ox: (W - (maxX - minX) * a) / 2 - minX * a, oy: (H - (maxY - minY) * a) / 2 - minY * a };
    var ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, W, H);
    cubes.slice().sort(function (p, q) { return (p.x + p.y + p.z) - (q.x + q.y + q.z) || p.z - q.z; })
      .forEach(function (c) { cube(ctx, c, s); });
  }
  var TOOLS = {
    line: function () { var c = []; for (var i = 0; i < 6; i++) c.push({ x: i, y: 0, z: Math.floor(i * 0.6), k: "gold" }); return c; },
    wall: function () {
      var c = [], run = [[0, 2], [1, 2], [2, 2], [3, 2], [3, 1], [3, 0]];
      for (var x = 0; x < 4; x++) for (var y = 0; y < 3; y++) c.push({ x: x, y: y, z: -1, k: "ground" });
      run.forEach(function (p) { for (var z = 0; z < 3; z++) c.push({ x: p[0], y: p[1], z: z, k: z < 2 ? "gold" : "holo" }); });
      return c;
    },
    floor: function () { var c = []; for (var x = 0; x < 5; x++) for (var y = 0; y < 4; y++) c.push({ x: x, y: y, z: 0, k: "gold" }); return c; },
    volume: function () { var c = []; for (var x = 0; x < 4; x++) for (var y = 0; y < 3; y++) for (var z = 0; z < 2; z++) c.push({ x: x, y: y, z: z, k: "gold" }); return c; },
    stack: function () { var c = [{ x: 0, y: 0, z: 0, k: "gray" }, { x: 1, y: 0, z: 0, k: "gray" }, { x: 0, y: 1, z: 0, k: "gray" }]; for (var z = 1; z < 5; z++) c.push({ x: 0, y: 0, z: z, k: z < 4 ? "gold" : "holo" }); return c; },
    material: function () {
      var c = [], gold = { "1,1": 1, "2,1": 1, "1,2": 1, "2,2": 1, "3,2": 1, "2,3": 1 };
      for (var x = 0; x < 5; x++) for (var y = 0; y < 5; y++) c.push({ x: x, y: y, z: 0, k: gold[x + "," + y] ? "gold" : (x === 4 || y === 0 ? "gray" : "stone") });
      return c;
    }
  };
  function drawTools() {
    document.querySelectorAll("canvas[data-tool]").forEach(function (cv) {
      var make = TOOLS[cv.getAttribute("data-tool")];
      if (make && cv.getContext) draw(cv, make());
    });
  }
  drawTools();
  var timer;
  window.addEventListener("resize", function () { clearTimeout(timer); timer = setTimeout(drawTools, 120); });

  // ---------- Copy the SHA-256 ----------
  var copy = document.getElementById("copy-sha");
  if (copy) {
    var label = copy.textContent;
    copy.addEventListener("click", function () {
      var code = document.getElementById("sha");
      function select() {
        var range = document.createRange(); range.selectNodeContents(code);
        var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(range);
        copy.textContent = copy.dataset.selected;
      }
      try {
        navigator.clipboard.writeText(code.textContent).then(function () { copy.textContent = copy.dataset.copied; }, select);
      } catch (e) { select(); }
      setTimeout(function () { copy.textContent = label; }, 2000);
    });
  }
})();
