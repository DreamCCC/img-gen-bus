// Oblique perspective NBA court on a 2D canvas, shared by the tracking scenes (c4, c7).
// Units are feet: origin center court, x along the length (attacking hoop at +x), y across, z up.
// Camera = { eye:[x,y,z], target:[x,y,z], fov (deg, vertical), center:[sx,sy] (screen point the target lands on) }.
(function () {
  'use strict';

  const D = {
    HALF_L: 47, HALF_W: 25, HOOP_X: 41.75, RIM_R: 0.75, RIM_Z: 10,
    ARC_R: 23.75, CORNER_Y: 22, PAINT_HW: 8, PAINT_L: 19, FT_R: 6, RA_R: 4,
    BOARD_X: 43, BOARD_HW: 3, BOARD_Z0: 9.5, BOARD_Z1: 13, CENTER_R: 6, CENTER_R2: 2,
  };
  const C = {
    navy: '#0A1428', red: '#C8102E', blue: '#1D428A', blueHi: '#3D7BFF', silver: '#C4CED4', white: '#F4F6F8',
    green: '#2BD67B', neg: '#FF3B3B', nyk: '#F58426', nykBlue: '#006BB6', sas: '#C4CED4', rim: '#FF6A1A',
  };

  const cl = (x) => Math.min(1, Math.max(0, x));
  const eo = (x) => 1 - Math.pow(1 - cl(x), 3);
  const eio = (x) => { x = cl(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
  const back = (x, k = 1.8) => { x = cl(x) - 1; return 1 + x * x * ((k + 1) * x + k); };
  const lerp = (a, b, t) => a + (b - a) * t;
  const lerp3 = (a, b, t) => [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)];
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
  const dot3 = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const norm = (a) => { const l = Math.hypot(a[0], a[1], a[2]); return [a[0] / l, a[1] / l, a[2] / l]; };
  const hash = (i) => { const s = Math.sin(i * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); };
  const rgba = (hex, a) => {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
  };

  function camLerp(a, b, t) {
    return {
      eye: lerp3(a.eye, b.eye, t), target: lerp3(a.target, b.target, t), fov: lerp(a.fov, b.fov, t),
      center: [lerp(a.center[0], b.center[0], t), lerp(a.center[1], b.center[1], t)],
    };
  }

  // polyline helpers (screen space)
  function lengths(pts) {
    const len = [0];
    for (let i = 1; i < pts.length; i++) len.push(len[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    return len;
  }
  function tracePartial(ctx, pts, frac) {
    const len = lengths(pts), want = len[len.length - 1] * frac;
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) {
      if (len[i] <= want) ctx.lineTo(pts[i][0], pts[i][1]);
      else {
        const f = (want - len[i - 1]) / Math.max(1e-6, len[i] - len[i - 1]);
        ctx.lineTo(lerp(pts[i - 1][0], pts[i][0], f), lerp(pts[i - 1][1], pts[i][1], f));
        return [lerp(pts[i - 1][0], pts[i][0], f), lerp(pts[i - 1][1], pts[i][1], f)];
      }
    }
    return pts[pts.length - 1];
  }
  function glowStroke(ctx, pts, color, width, { alpha = 1, frac = 1, dash = null, dashOffset = 0, glow = 1, cap = 'round' } = {}) {
    if (frac <= 0 || alpha <= 0 || pts.length < 2) return;
    ctx.save();
    ctx.lineCap = cap; ctx.lineJoin = 'round';
    if (dash) { ctx.setLineDash(dash); ctx.lineDashOffset = dashOffset; }
    const passes = glow ? [[width * 4.5, 0.12 * glow], [width * 2.2, 0.3 * glow], [width, 1]] : [[width, 1]];
    for (const [w, a] of passes) {
      ctx.strokeStyle = color; ctx.globalAlpha = alpha * a; ctx.lineWidth = w;
      ctx.beginPath(); tracePartial(ctx, pts, frac); ctx.stroke();
    }
    ctx.restore();
  }

  function circlePts(cx, cy, r, z = 0, n = 72, a0 = 0, a1 = Math.PI * 2) {
    const out = [];
    for (let i = 0; i <= n; i++) {
      const a = lerp(a0, a1, i / n);
      out.push([cx + r * Math.cos(a), cy + r * Math.sin(a), z]);
    }
    return out;
  }
  function seg(a, b, n = 8) {
    const out = [];
    for (let i = 0; i <= n; i++) out.push(lerp3(a, b, i / n));
    return out;
  }

  // Court markings for one end (sx = +1 right hoop, -1 left hoop), all on the floor.
  function endLines(sx) {
    const L = [], hx = sx * D.HOOP_X, bx = sx * D.HALF_L, fx = sx * (D.HALF_L - D.PAINT_L);
    const s = (a, b, n) => L.push({ pts: seg([a[0], a[1], 0], [b[0], b[1], 0], n) });
    // paint
    s([bx, -D.PAINT_HW], [fx, -D.PAINT_HW], 10); s([fx, -D.PAINT_HW], [fx, D.PAINT_HW], 8); s([fx, D.PAINT_HW], [bx, D.PAINT_HW], 10);
    // lane blocks / hash marks
    for (const d of [7, 8, 11, 14]) for (const yy of [-1, 1]) {
      const x = sx * (D.HALF_L - d);
      s([x, yy * D.PAINT_HW], [x, yy * (D.PAINT_HW + 0.66)], 1);
    }
    // FT circle: outer half solid, inner half dashed
    const a0 = sx > 0 ? Math.PI / 2 : -Math.PI / 2;
    L.push({ pts: circlePts(fx, 0, D.FT_R, 0, 40, a0, a0 + Math.PI) });
    L.push({ pts: circlePts(fx, 0, D.FT_R, 0, 40, a0 + Math.PI, a0 + Math.PI * 2), dash: true });
    // restricted area
    L.push({ pts: [[hx + sx * 1.25, D.RA_R, 0], ...circlePts(hx, 0, D.RA_R, 0, 32, a0, a0 + Math.PI), [hx + sx * 1.25, -D.RA_R, 0]] });
    // 3pt line
    const th = Math.asin(D.CORNER_Y / D.ARC_R), xc = hx - sx * D.ARC_R * Math.cos(th);
    const arc = sx > 0 ? circlePts(hx, 0, D.ARC_R, 0, 80, Math.PI - th, Math.PI + th) : circlePts(hx, 0, D.ARC_R, 0, 80, -th, th);
    const top = sx > 0 ? D.CORNER_Y : -D.CORNER_Y;
    L.push({ pts: [...seg([bx, top, 0], [xc, top, 0], 6), ...arc, ...seg([xc, -top, 0], [bx, -top, 0], 6)] });
    // coaching-box hash marks (28 ft from baseline, 3 ft in from sideline)
    for (const yy of [-1, 1]) s([sx * (D.HALF_L - 28), yy * D.HALF_W], [sx * (D.HALF_L - 28), yy * (D.HALF_W - 3)], 2);
    return L;
  }
  function courtLines() {
    const L = [];
    const W2 = D.HALF_W, L2 = D.HALF_L;
    L.push({ pts: [...seg([-L2, -W2, 0], [L2, -W2, 0], 40), ...seg([L2, -W2, 0], [L2, W2, 0], 20), ...seg([L2, W2, 0], [-L2, W2, 0], 40), ...seg([-L2, W2, 0], [-L2, -W2, 0], 20)] });
    L.push({ pts: seg([0, -W2, 0], [0, W2, 0], 20) });
    L.push({ pts: circlePts(0, 0, D.CENTER_R, 0, 64) });
    L.push({ pts: circlePts(0, 0, D.CENTER_R2, 0, 32) });
    return L.concat(endLines(1), endLines(-1));
  }

  class Court {
    constructor(ctx, camera) {
      this.ctx = ctx;
      this.W = ctx.canvas.width; this.H = ctx.canvas.height;
      this.layer = document.createElement('canvas');
      this.layer.width = this.W; this.layer.height = this.H;
      this.lctx = this.layer.getContext('2d');
      this.lines = courtLines();
      this.setCamera(camera);
    }

    setCamera(cam) {
      this.cam = cam;
      const f = norm(sub(cam.target, cam.eye));
      const r = norm(cross(f, [0, 0, 1]));
      this.f = f; this.r = r; this.u = cross(r, f);
      this.focal = (this.H / 2) / Math.tan((cam.fov * Math.PI / 180) / 2);
      this.cx = cam.center ? cam.center[0] : this.W / 2;
      this.cy = cam.center ? cam.center[1] : this.H / 2;
    }

    // -> [sx, sy, depth, px-per-ft]
    project(p) {
      const d = sub([p[0], p[1], p[2] || 0], this.cam.eye);
      const zc = Math.max(0.1, dot3(d, this.f));
      const s = this.focal / zc;
      return [this.cx + dot3(d, this.r) * s, this.cy - dot3(d, this.u) * s, zc, s];
    }
    P(pts) { return pts.map((p) => this.project(p)); }
    depth(x, y, z = 0) { return dot3(sub([x, y, z], this.cam.eye), this.f); }

    // Affine approximation of the floor plane around (x, y, z) -> lets canvas gradients/circles be painted "on the floor".
    floorTransform(x, y, z = 0, r = 1) {
      const p0 = this.project([x, y, z]);
      const ax = this.project([x + r, y, z]), bx = this.project([x - r, y, z]);
      const ay = this.project([x, y + r, z]), by = this.project([x, y - r, z]);
      return [(ax[0] - bx[0]) / (2 * r), (ax[1] - bx[1]) / (2 * r), (ay[0] - by[0]) / (2 * r), (ay[1] - by[1]) / (2 * r), p0[0], p0[1]];
    }
    floorGlow(x, y, r, color, alpha, { z = 0, inner = 0, comp = 'lighter', stops = null } = {}) {
      if (alpha <= 0) return;
      const ctx = this.ctx;
      ctx.save();
      ctx.globalCompositeOperation = comp;
      ctx.globalAlpha = alpha;
      ctx.transform(...this.floorTransform(x, y, z, r));
      const g = ctx.createRadialGradient(0, 0, inner, 0, 0, r);
      for (const [o, a] of (stops || [[0, 1], [0.45, 0.45], [1, 0]])) g.addColorStop(o, rgba(color, a));
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
    }

    floorPoly() {
      const m = 4;
      return this.P([[-D.HALF_L - m, -D.HALF_W - m, 0], [D.HALF_L + m, -D.HALF_W - m, 0], [D.HALF_L + m, D.HALF_W + m, 0], [-D.HALF_L - m, D.HALF_W + m, 0]]);
    }
    clipFloor(ctx = this.ctx) {
      const q = this.P([[-D.HALF_L - 6, -D.HALF_W - 6, 0], [D.HALF_L + 6, -D.HALF_W - 6, 0], [D.HALF_L + 6, D.HALF_W + 6, 0], [-D.HALF_L - 6, D.HALF_W + 6, 0]]);
      ctx.beginPath(); q.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]))); ctx.closePath(); ctx.clip();
    }

    // Floor + tints + grid + glowing lines + reflection of the hoop. draw = line draw-on fraction.
    drawFloor(t, { alpha = 1, draw = 1, leftFade = [0, 260] } = {}) {
      const ctx = this.ctx;
      ctx.save();
      ctx.globalAlpha = alpha;
      const near = this.project([20, -D.HALF_W - 4, 0]), far = this.project([20, D.HALF_W + 4, 0]);
      // apron + court slab
      const fp = this.floorPoly();
      const g = ctx.createLinearGradient(0, far[1], 0, near[1]);
      g.addColorStop(0, 'rgba(10,22,44,0.55)'); g.addColorStop(1, 'rgba(18,38,74,0.92)');
      ctx.fillStyle = g;
      ctx.beginPath(); fp.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]))); ctx.closePath(); ctx.fill();
      const cp = this.P([[-D.HALF_L, -D.HALF_W, 0], [D.HALF_L, -D.HALF_W, 0], [D.HALF_L, D.HALF_W, 0], [-D.HALF_L, D.HALF_W, 0]]);
      const g2 = ctx.createLinearGradient(0, far[1], 0, near[1]);
      g2.addColorStop(0, 'rgba(16,34,66,0.7)'); g2.addColorStop(1, 'rgba(24,52,98,0.95)');
      ctx.fillStyle = g2;
      ctx.beginPath(); cp.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]))); ctx.closePath(); ctx.fill();
      ctx.save();
      this.clipFloor();
      // 3pt-area + paint tints
      for (const sx of [1, -1]) {
        const th = Math.asin(D.CORNER_Y / D.ARC_R), hx = sx * D.HOOP_X, bx = sx * D.HALF_L;
        const arc = sx > 0 ? circlePts(hx, 0, D.ARC_R, 0, 60, Math.PI - th, Math.PI + th) : circlePts(hx, 0, D.ARC_R, 0, 60, -th, th);
        const poly = this.P([[bx, sx * D.CORNER_Y, 0], ...arc, [bx, -sx * D.CORNER_Y, 0]]);
        ctx.fillStyle = 'rgba(29,66,138,0.16)';
        ctx.beginPath(); poly.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]))); ctx.closePath(); ctx.fill();
        const fx = sx * (D.HALF_L - D.PAINT_L);
        const pp = this.P([[bx, -D.PAINT_HW, 0], [fx, -D.PAINT_HW, 0], [fx, D.PAINT_HW, 0], [bx, D.PAINT_HW, 0]]);
        ctx.fillStyle = 'rgba(29,66,138,0.32)';
        ctx.beginPath(); pp.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]))); ctx.closePath(); ctx.fill();
      }
      // spotlight on the attacking end + slow sheen
      this.floorGlow(D.HOOP_X - 10, 0, 34, '#3D7BFF', 0.22);
      const sx0 = ((t * 140) % 2600) - 700;
      const sh = ctx.createLinearGradient(sx0, 0, sx0 + 520, this.H);
      sh.addColorStop(0, 'rgba(160,200,255,0)'); sh.addColorStop(0.5, 'rgba(160,200,255,0.05)'); sh.addColorStop(1, 'rgba(160,200,255,0)');
      ctx.fillStyle = sh; ctx.fillRect(0, 0, this.W, this.H);
      // floor grid (2 ft)
      ctx.strokeStyle = 'rgba(150,190,255,0.05)'; ctx.lineWidth = 1;
      ctx.beginPath();
      for (let x = -46; x <= 46; x += 2) { const a = this.project([x, -D.HALF_W, 0]), b = this.project([x, D.HALF_W, 0]); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); }
      for (let y = -24; y <= 24; y += 2) { const a = this.project([-D.HALF_L, y, 0]), b = this.project([D.HALF_L, y, 0]); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); }
      ctx.stroke();
      // rim light pooled on the floor under each hoop
      for (const sx of [1, -1]) this.floorGlow(sx * D.HOOP_X, 0, 6, C.rim, 0.12);
      ctx.restore();
      ctx.restore();

      // lines -> offscreen layer, depth-faded, then glow + crisp composite
      const l = this.lctx;
      l.setTransform(1, 0, 0, 1, 0, 0);
      l.globalCompositeOperation = 'source-over';
      l.clearRect(0, 0, this.W, this.H);
      l.lineCap = 'round'; l.lineJoin = 'round';
      l.strokeStyle = '#DCE8FF';
      for (const ln of this.lines) {
        const pts = this.P(ln.pts);
        const s = pts[Math.floor(pts.length / 2)][3];
        l.lineWidth = Math.max(1.2, Math.min(3.6, s * 0.17));
        l.setLineDash(ln.dash ? [10, 9] : []);
        l.beginPath(); tracePartial(l, pts, draw); l.stroke();
      }
      l.setLineDash([]);
      l.globalCompositeOperation = 'destination-in';
      const mg = l.createLinearGradient(0, far[1], 0, near[1]);
      mg.addColorStop(0, 'rgba(0,0,0,0.38)'); mg.addColorStop(1, 'rgba(0,0,0,1)');
      l.fillStyle = mg; l.fillRect(0, 0, this.W, this.H);
      if (leftFade) {
        const lg = l.createLinearGradient(leftFade[0], 0, leftFade[1], 0);
        lg.addColorStop(0, 'rgba(0,0,0,0)'); lg.addColorStop(1, 'rgba(0,0,0,1)');
        l.fillStyle = lg; l.fillRect(0, 0, this.W, this.H);
      }
      ctx.save();
      ctx.globalAlpha = alpha * 0.85;
      ctx.globalCompositeOperation = 'lighter';
      ctx.filter = 'blur(7px)';
      ctx.drawImage(this.layer, 0, 0);
      ctx.filter = 'none';
      ctx.globalAlpha = alpha * 0.9;
      ctx.globalCompositeOperation = 'source-over';
      ctx.drawImage(this.layer, 0, 0);
      ctx.restore();
    }

    // backboard, rim, net (mirror=true draws the floor reflection)
    drawHoop({ alpha = 1, mirror = false, rimColor = C.rim, glow = 1 } = {}) {
      if (alpha <= 0) return;
      const ctx = this.ctx, m = mirror ? -1 : 1;
      const Z = (z) => z * m;
      const bx = D.BOARD_X, hx = D.HOOP_X;
      ctx.save();
      ctx.globalAlpha *= alpha;
      // stanchion arm + post
      const post = this.P([[bx + 0.3, 0, Z(11.2)], [D.HALF_L + 2.5, 0, Z(11.2)], [D.HALF_L + 4, 0, Z(9)], [D.HALF_L + 4, 0, 0]]);
      glowStroke(ctx, post, '#8FA6C8', 3, { alpha: 0.45, glow: 0.4 });
      // board
      const bq = this.P([[bx, -D.BOARD_HW, Z(D.BOARD_Z0)], [bx, D.BOARD_HW, Z(D.BOARD_Z0)], [bx, D.BOARD_HW, Z(D.BOARD_Z1)], [bx, -D.BOARD_HW, Z(D.BOARD_Z1)]]);
      ctx.fillStyle = 'rgba(180,210,255,0.10)';
      ctx.beginPath(); bq.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]))); ctx.closePath(); ctx.fill();
      glowStroke(ctx, [...bq, bq[0]], '#E8F0FF', 2.4, { glow: 0.8 * glow });
      const iq = this.P([[bx, -1, Z(10)], [bx, 1, Z(10)], [bx, 1, Z(11.5)], [bx, -1, Z(11.5)], [bx, -1, Z(10)]]);
      glowStroke(ctx, iq, '#E8F0FF', 1.8, { glow: 0.5 * glow, alpha: 0.9 });
      // rim arm
      glowStroke(ctx, this.P([[bx, 0, Z(10)], [hx + D.RIM_R, 0, Z(10)]]), rimColor, 2.6, { glow: 0.6 * glow });
      // net
      ctx.save();
      ctx.strokeStyle = 'rgba(235,242,255,0.5)'; ctx.lineWidth = 1.1;
      ctx.beginPath();
      for (let i = 0; i < 12; i++) {
        const a = (i / 12) * Math.PI * 2, b = a + Math.PI / 6;
        const p = this.project([hx + D.RIM_R * Math.cos(a), D.RIM_R * Math.sin(a), Z(10)]);
        const q = this.project([hx + 0.45 * Math.cos(b), 0.45 * Math.sin(b), Z(8.6)]);
        ctx.moveTo(p[0], p[1]); ctx.lineTo(q[0], q[1]);
      }
      const bot = this.P(circlePts(hx, 0, 0.45, Z(8.6), 24));
      bot.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])));
      ctx.stroke();
      ctx.restore();
      // rim
      glowStroke(ctx, this.P(circlePts(hx, 0, D.RIM_R, Z(10), 40)), rimColor, 3.2, { glow: 1.1 * glow });
      ctx.restore();
    }

    // ---- floor overlays

    circle(cx, cy, r, { color = C.white, width = 3, dash = null, dashOffset = 0, alpha = 1, frac = 1, a0 = 0, fill = null, fillAlpha = 0.15, glow = 1, n = 96 } = {}) {
      const pts = this.P(circlePts(cx, cy, r, 0, n, a0, a0 + Math.PI * 2));
      if (fill && frac >= 1) {
        const ctx = this.ctx;
        ctx.save(); ctx.globalAlpha = alpha * fillAlpha; ctx.fillStyle = fill;
        ctx.beginPath(); pts.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]))); ctx.fill(); ctx.restore();
      }
      glowStroke(this.ctx, pts, color, width, { alpha, frac, dash, dashOffset, glow });
      return pts;
    }

    // pts in feet on the floor; arrow head painted on the floor. Returns the screen tip point.
    path(ptsFt, { color = C.white, width = 4, dash = null, dashOffset = 0, alpha = 1, frac = 1, arrow = false, head = 2.4, glow = 1, sub = 6 } = {}) {
      if (frac <= 0 || alpha <= 0) return null;
      const dense = [];
      for (let i = 1; i < ptsFt.length; i++) {
        const a = [...ptsFt[i - 1], 0].slice(0, 3), b = [...ptsFt[i], 0].slice(0, 3);
        for (let k = i === 1 ? 0 : 1; k <= sub; k++) dense.push(lerp3(a, b, k / sub));
      }
      // cut the line short of the head so the tip stays sharp
      let tipFt = null;
      if (arrow) {
        const lenFt = [0];
        for (let i = 1; i < dense.length; i++) lenFt.push(lenFt[i - 1] + Math.hypot(dense[i][0] - dense[i - 1][0], dense[i][1] - dense[i - 1][1]));
        const want = lenFt[lenFt.length - 1] * frac;
        let j = 1;
        while (j < dense.length - 1 && lenFt[j] < want) j++;
        const f = (want - lenFt[j - 1]) / Math.max(1e-6, lenFt[j] - lenFt[j - 1]);
        tipFt = lerp3(dense[j - 1], dense[j], cl(f));
        const dir = norm([dense[j][0] - dense[j - 1][0], dense[j][1] - dense[j - 1][1], 0]);
        const trimmed = dense.slice(0, j).concat([[tipFt[0] - dir[0] * head * 0.6, tipFt[1] - dir[1] * head * 0.6, 0]]);
        glowStroke(this.ctx, this.P(trimmed), color, width, { alpha, dash, dashOffset, glow });
        const nx = -dir[1], ny = dir[0];
        const tri = this.P([
          [tipFt[0] + dir[0] * 0.2, tipFt[1] + dir[1] * 0.2, 0],
          [tipFt[0] - dir[0] * head + nx * head * 0.55, tipFt[1] - dir[1] * head + ny * head * 0.55, 0],
          [tipFt[0] - dir[0] * head * 0.72, tipFt[1] - dir[1] * head * 0.72, 0],
          [tipFt[0] - dir[0] * head - nx * head * 0.55, tipFt[1] - dir[1] * head - ny * head * 0.55, 0],
        ]);
        const ctx = this.ctx;
        ctx.save();
        ctx.globalAlpha = alpha * cl(frac * 8);
        ctx.shadowColor = color; ctx.shadowBlur = 18;
        ctx.fillStyle = color;
        ctx.beginPath(); tri.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]))); ctx.closePath(); ctx.fill();
        ctx.restore();
        return this.project(tipFt);
      }
      const P = this.P(dense);
      glowStroke(this.ctx, P, color, width, { alpha, frac, dash, dashOffset, glow });
      const len = lengths(P), want = len[len.length - 1] * frac;
      let i = 1;
      while (i < P.length - 1 && len[i] < want) i++;
      const f = (want - len[i - 1]) / Math.max(1e-6, len[i] - len[i - 1]);
      return [lerp(P[i - 1][0], P[i][0], cl(f)), lerp(P[i - 1][1], P[i][1], cl(f))];
    }

    // glowing "rim protection zone": floor disc + soft wall
    zone(cx, cy, r, { color = '#3D7BFF', alpha = 1, wall = 2.6, grow = 1, pulse = 0, edge = 1 } = {}) {
      if (alpha <= 0 || grow <= 0) return;
      const ctx = this.ctx, R = r * grow;
      this.floorGlow(cx, cy, R, color, 0.55 * alpha, { stops: [[0, 0.35], [0.7, 0.55], [0.93, 0.9], [1, 0]] });
      const rings = [0.33, 0.66];
      for (const k of rings) this.circle(cx, cy, R * k, { color, width: 1.3, alpha: 0.35 * alpha, glow: 0 });
      if (pulse > 0) this.circle(cx, cy, R * (0.2 + 0.8 * pulse), { color, width: 2, alpha: alpha * 0.6 * (1 - pulse), glow: 0.5 });
      // wall: hull of floor ring + raised ring, vertical gradient
      const lo = this.P(circlePts(cx, cy, R, 0, 64)), hi = this.P(circlePts(cx, cy, R, wall, 64));
      const ys = lo.map((p) => p[1]);
      let iMin = 0, iMax = 0;
      lo.forEach((p, i) => { if (p[0] < lo[iMin][0]) iMin = i; if (p[0] > lo[iMax][0]) iMax = i; });
      const front = [];
      for (let i = iMin; ; i = (i + 1) % lo.length) {
        front.push(i);
        if (i === iMax) break;
      }
      const frontNear = front.reduce((s, i) => s + lo[i][1], 0) / front.length;
      const backSide = [];
      for (let i = iMax; ; i = (i + 1) % lo.length) { backSide.push(i); if (i === iMin) break; }
      const nearIdx = frontNear >= backSide.reduce((s, i) => s + lo[i][1], 0) / backSide.length ? front : backSide;
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      const top = Math.min(...hi.map((p) => p[1])), bottom = Math.max(...ys);
      const g = ctx.createLinearGradient(0, bottom, 0, top);
      g.addColorStop(0, rgba(color, 0.3 * alpha)); g.addColorStop(1, rgba(color, 0));
      ctx.fillStyle = g;
      ctx.beginPath();
      nearIdx.forEach((i, k) => (k ? ctx.lineTo(lo[i][0], lo[i][1]) : ctx.moveTo(lo[i][0], lo[i][1])));
      for (let k = nearIdx.length - 1; k >= 0; k--) ctx.lineTo(hi[nearIdx[k]][0], hi[nearIdx[k]][1]);
      ctx.closePath(); ctx.fill();
      ctx.restore();
      glowStroke(ctx, lo, color, 3.2, { alpha: alpha * edge, glow: 1.2 });
      glowStroke(ctx, hi, color, 1.2, { alpha: alpha * 0.35 * edge, glow: 0 });
    }

    // player dot on the floor. Returns screen anchor.
    dot(x, y, { color = C.white, ring = null, r = 1.25, alpha = 1, pop = 1, hollow = false, hot = 0, pulse = -1 } = {}) {
      if (alpha <= 0 || pop <= 0) return this.project([x, y, 0]);
      const ctx = this.ctx, R = r * pop;
      this.floorGlow(x, y, R * (2.6 + hot * 1.4), color, (0.45 + 0.5 * hot) * alpha);
      if (pulse >= 0 && pulse <= 1) this.circle(x, y, R * (1.5 + 3.5 * pulse), { color, width: 2.5, alpha: alpha * (1 - pulse), glow: 0.8, n: 48 });
      const disc = this.P(circlePts(x, y, R, 0, 40));
      ctx.save();
      ctx.globalAlpha = alpha;
      if (!hollow) {
        ctx.save();
        ctx.transform(...this.floorTransform(x, y, 0, R));
        const g = ctx.createRadialGradient(-R * 0.2, -R * 0.2, 0, 0, 0, R);
        g.addColorStop(0, '#FFFFFF'); g.addColorStop(0.35, color); g.addColorStop(1, color);
        ctx.fillStyle = g;
        ctx.beginPath(); ctx.arc(0, 0, R, 0, Math.PI * 2); ctx.fill();
        ctx.restore();
      }
      ctx.restore();
      glowStroke(ctx, disc, hollow ? color : '#FFFFFF', hollow ? 2.5 : 1.6, { alpha: alpha * (hollow ? 1 : 0.85), glow: hollow ? 0.6 : 0, dash: hollow ? [6, 5] : null });
      glowStroke(ctx, this.P(circlePts(x, y, R * 1.6, 0, 48)), ring || color, 2.2, { alpha: alpha * 0.85, glow: 0.7 });
      if (hot > 0) glowStroke(ctx, this.P(circlePts(x, y, R * 2.2, 0, 48)), '#FFFFFF', 2.4, { alpha: alpha * hot, glow: 1 });
      return this.project([x, y, 0]);
    }

    // screen-facing name plate on a stem. Returns [sx, sy] of the plate's top-center.
    label(x, y, text, { color = C.white, alpha = 1, scale = 1, stem = 6.5, dx = 0, dy = 0, hi = 0, sub = null, textColor = null, pop = 1 } = {}) {
      if (alpha <= 0) return null;
      const ctx = this.ctx;
      const a = this.project([x, y, 0.2]), b = this.project([x, y, stem]);
      const k = scale * Math.min(1.15, Math.max(0.72, b[3] / 15));
      ctx.save();
      ctx.globalAlpha = alpha;
      const sg = ctx.createLinearGradient(0, a[1], 0, b[1]);
      sg.addColorStop(0, 'rgba(255,255,255,0)'); sg.addColorStop(1, 'rgba(255,255,255,0.75)');
      ctx.strokeStyle = sg; ctx.lineWidth = 1.6;
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0] + dx * 0.25, b[1] + dy * 0.25); ctx.stroke();
      const px = b[0] + dx, py = b[1] + dy;
      ctx.translate(px, py);
      ctx.scale(k * pop, k * pop);
      ctx.font = 'italic 800 28px BC';
      ctx.letterSpacing = '1px';
      const tw = ctx.measureText(text).width;
      const w = tw + 34, h = 36;
      ctx.fillStyle = hi > 0 ? color : 'rgba(6,12,26,0.86)';
      ctx.beginPath();
      ctx.moveTo(-w / 2 + 7, -h); ctx.lineTo(w / 2 + 7, -h); ctx.lineTo(w / 2 - 7, 0); ctx.lineTo(-w / 2 - 7, 0); ctx.closePath();
      if (hi > 0) { ctx.shadowColor = color; ctx.shadowBlur = 26 * hi; }
      ctx.fill();
      ctx.shadowBlur = 0;
      if (hi <= 0) { ctx.fillStyle = color; ctx.fillRect(-w / 2 - 2, -h, 6, h); }
      ctx.fillStyle = textColor || (hi > 0 ? '#0A1428' : '#FFFFFF');
      ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
      ctx.fillText(text, 4, -9);
      if (sub) {
        ctx.font = '600 15px IN';
        ctx.letterSpacing = '2px';
        ctx.fillStyle = 'rgba(220,230,245,0.9)';
        ctx.fillText(sub, 0, -h - 8);
      }
      ctx.restore();
      return [px, py - h * k * pop];
    }
  }

  // ---- backdrop: navy -> black radial, fine grid, faint particles
  function backdrop(ctx, t, W = 1920, H = 1080) {
    const g = ctx.createRadialGradient(W * 0.5, H * 0.42, 0, W * 0.5, H * 0.42, W * 0.78);
    g.addColorStop(0, '#11224A'); g.addColorStop(0.45, '#0A1428'); g.addColorStop(1, '#010205');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.save();
    ctx.strokeStyle = 'rgba(140,180,255,0.045)'; ctx.lineWidth = 1;
    ctx.beginPath();
    for (let x = 0; x <= W; x += 48) { ctx.moveTo(x + 0.5, 0); ctx.lineTo(x + 0.5, H); }
    for (let y = 0; y <= H; y += 48) { ctx.moveTo(0, y + 0.5); ctx.lineTo(W, y + 0.5); }
    ctx.stroke();
    for (let i = 0; i < 90; i++) {
      const sp = 6 + hash(i + 3) * 18;
      const x = (hash(i) * W + t * sp * (hash(i + 7) - 0.5) * 2 + W) % W;
      const y = (hash(i + 1) * H - t * sp + H * 4) % H;
      const a = (0.08 + 0.25 * hash(i + 2)) * (0.6 + 0.4 * Math.sin(t * (1 + hash(i + 5) * 3) + i));
      ctx.fillStyle = `rgba(170,200,255,${a})`;
      ctx.beginPath(); ctx.arc(x, y, 0.8 + hash(i + 4) * 1.8, 0, Math.PI * 2); ctx.fill();
    }
    ctx.restore();
  }
  function vignette(ctx, W = 1920, H = 1080) {
    const v = ctx.createRadialGradient(W / 2, H * 0.45, H * 0.45, W / 2, H * 0.45, H * 1.05);
    v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,0.6)');
    ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
  }

  async function loadFonts(base = '../assets/fonts/') {
    const list = [
      ['BC', 'BarlowCondensed-Medium', 500, 'normal'], ['BC', 'BarlowCondensed-SemiBold', 600, 'normal'], ['BC', 'BarlowCondensed-Bold', 700, 'normal'],
      ['BC', 'BarlowCondensed-ExtraBold', 800, 'normal'], ['BC', 'BarlowCondensed-Black', 900, 'normal'], ['BC', 'BarlowCondensed-BoldItalic', 700, 'italic'],
      ['BC', 'BarlowCondensed-ExtraBoldItalic', 800, 'italic'], ['BC', 'BarlowCondensed-ExtraBoldItalic', 900, 'italic'],
      ['IN', 'Inter-Medium', 500, 'normal'], ['IN', 'Inter-SemiBold', 600, 'normal'], ['IN', 'Inter-Bold', 700, 'normal'],
    ];
    for (const [fam, file, w, st] of list) {
      const f = new FontFace(fam, `url(${base}${file}.ttf)`, { weight: String(w), style: st });
      document.fonts.add(await f.load());
    }
  }

  window.Court3D = { Court, D, C, camLerp, backdrop, vignette, loadFonts, glowStroke, circlePts, rgba, ease: { cl, eo, eio, back, lerp, hash } };
})();
