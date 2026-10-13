// 2D 层：时间工具、图片与视频帧、HUD、档案卡、字幕
export const W = 1920, H = 1080, FPS = 30;
export const TINT = { red: '#ff5a2a', blue: '#6fa8ff', yellow: '#ffc46a' };
export const SIMCOL = [TINT.red, TINT.blue, TINT.yellow];   // 模拟里的 0/1/2 号星
export const COL = { hud: '#bfe3ff', hudDim: 'rgba(191,227,255,0.35)', white: '#f2f0ea', grey: '#8a919c', gold: '#e2c27a', paper: '#e9e1cf', ink: '#2b241b', red: '#ff4a3a' };
export const F = { ui: '"PingFang SC", sans-serif', serif: '"Songti SC", serif', mono: 'Menlo, monospace', num: '"DIN Condensed", "DIN Alternate", sans-serif', latin: '"Baskerville", "Times New Roman", serif' };

export const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
export const lerp = (a, b, t) => a + (b - a) * t;
export const prog = (t, a, b) => (b <= a ? (t >= a ? 1 : 0) : clamp((t - a) / (b - a)));
export const smooth = (x) => x * x * (3 - 2 * x);
export const easeInOut = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
export const easeOut = (x) => 1 - Math.pow(1 - x, 3);
export const easeIn = (x) => x * x * x;
export const fade = (t, a, b, fi = 0.3, fo = 0.3) => (fi > 0 ? prog(t, a, a + fi) : t >= a ? 1 : 0) * (fo > 0 ? 1 - prog(t, b - fo, b) : t < b ? 1 : 0);
export const mk = (w, h) => Object.assign(document.createElement('canvas'), { width: w, height: h });
export function rng(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// 单调三次插值（不过冲），keys = [[x, y], ...] 按 x 升序
export function mono(keys) {
  const n = keys.length, x = keys.map((k) => k[0]), y = keys.map((k) => k[1]);
  const d = [], m = new Array(n).fill(0);
  for (let i = 0; i < n - 1; i++) d.push((y[i + 1] - y[i]) / (x[i + 1] - x[i]));
  m[0] = d[0]; m[n - 1] = d[n - 2];
  for (let i = 1; i < n - 1; i++) m[i] = d[i - 1] * d[i] <= 0 ? 0 : (d[i - 1] + d[i]) / 2;
  for (let i = 0; i < n - 1; i++) {
    if (d[i] === 0) { m[i] = m[i + 1] = 0; continue; }
    const a = m[i] / d[i], b = m[i + 1] / d[i], s = a * a + b * b;
    if (s > 9) { const k = 3 / Math.sqrt(s); m[i] = k * a * d[i]; m[i + 1] = k * b * d[i]; }
  }
  return (t) => {
    if (t <= x[0]) return y[0];
    if (t >= x[n - 1]) return y[n - 1];
    let i = 0;
    while (t > x[i + 1]) i++;
    const h = x[i + 1] - x[i], u = (t - x[i]) / h, u2 = u * u, u3 = u2 * u;
    return (2 * u3 - 3 * u2 + 1) * y[i] + (u3 - 2 * u2 + u) * h * m[i] + (-2 * u3 + 3 * u2) * y[i + 1] + (u3 - u2) * h * m[i + 1];
  };
}
// 关键帧平滑插值（每段 smoothstep，停在关键帧上），值可以是数或数组
export function keys(ks, ease = smooth) {
  return (t) => {
    if (t <= ks[0][0]) return ks[0][1];
    for (let i = 0; i < ks.length - 1; i++) {
      const [t0, v0] = ks[i], [t1, v1] = ks[i + 1];
      if (t <= t1) {
        const u = ease(prog(t, t0, t1));
        return Array.isArray(v0) ? v0.map((x, k) => lerp(x, v1[k], u)) : lerp(v0, v1, u);
      }
    }
    return ks[ks.length - 1][1];
  };
}

// ---------- 时间轴 ----------
export let FILM = null, VO = {};
export function setFilm(f) { FILM = f; f.vo.forEach((v) => { VO[v.id] = v; v.str = v.chars.map((c) => c[0]).join(''); }); }
export const T = (id) => VO[id].t;
export const TE = (id) => VO[id].t + VO[id].dur;
// 某句里某个词的开始（或结束）时刻；k 为第几次出现
export function at(id, ph, end = false, k = 0) {
  const v = VO[id];
  let i = -1;
  for (let j = 0; j <= k; j++) i = v.str.indexOf(ph, i + 1);
  if (i < 0) { console.log(`at(): "${ph}" 不在 ${id}`); return v.t; }
  return end ? v.chars[i + ph.length - 1][2] : v.chars[i][1];
}
export const M = (name) => FILM.marks[name];

// ---------- 图片 / 视频帧 ----------
const cache = new Map();
export function img(src) {
  if (!cache.has(src)) {
    const im = new Image();
    im.src = src;
    cache.set(src, im.decode().then(() => im).catch(() => { console.log('img fail ' + src); return null; }));
    if (cache.size > 400) cache.delete(cache.keys().next().value);
  }
  return cache.get(src);
}
export let CLIPS = {};
export function setClips(m) { CLIPS = m; }
const pad = (k) => String(k).padStart(5, '0');
export async function clip(name, lt) {
  const m = CLIPS[name];
  if (!m) return null;
  const k = clamp(Math.floor(lt * FPS + 1e-4), 0, m.n - 1);
  if (k + 1 < m.n) img(`/scenes/clips/${name}/${pad(k + 1)}.jpg`);
  return img(`/scenes/clips/${name}/${pad(k)}.jpg`);
}

// ---------- 绘制 ----------
export function Ctx(ctx) {
  const g = {};
  g.ctx = ctx;
  g.text = (s, x, y, o = {}) => {
    const { size = 40, font = F.ui, weight = '500', color = COL.white, align = 'center', a = 1, spacing = 0, base = 'middle', shadow = 0, stroke = 0 } = o;
    if (a <= 0) return 0;
    ctx.save();
    ctx.globalAlpha *= a;
    ctx.font = `${weight} ${size}px ${font}`;
    ctx.textAlign = align; ctx.textBaseline = base;
    ctx.letterSpacing = `${spacing}px`;
    if (shadow) { ctx.shadowColor = 'rgba(0,0,0,0.85)'; ctx.shadowBlur = shadow; }
    if (stroke) { ctx.strokeStyle = 'rgba(0,0,0,0.6)'; ctx.lineWidth = stroke; ctx.lineJoin = 'round'; ctx.strokeText(s, x, y); }
    ctx.fillStyle = color;
    ctx.fillText(s, x, y);
    const w = ctx.measureText(s).width;
    ctx.restore();
    return w;
  };
  g.measure = (s, size, font = F.ui, weight = '500', spacing = 0) => {
    ctx.save(); ctx.font = `${weight} ${size}px ${font}`; ctx.letterSpacing = `${spacing}px`;
    const w = ctx.measureText(s).width; ctx.restore(); return w;
  };
  g.line = (x0, y0, x1, y1, o = {}) => {
    const { color = COL.hud, w = 1.5, a = 1, dash = null } = o;
    if (a <= 0) return;
    ctx.save(); ctx.globalAlpha *= a; ctx.strokeStyle = color; ctx.lineWidth = w;
    if (dash) ctx.setLineDash(dash);
    ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke(); ctx.restore();
  };
  g.poly = (pts, o = {}) => {
    const { color = COL.hud, w = 1.5, a = 1, close = false, fill = null } = o;
    if (a <= 0 || pts.length < 2) return;
    ctx.save(); ctx.globalAlpha *= a; ctx.strokeStyle = color; ctx.lineWidth = w; ctx.lineJoin = 'round';
    ctx.beginPath(); ctx.moveTo(...pts[0]); for (let i = 1; i < pts.length; i++) ctx.lineTo(...pts[i]);
    if (close) ctx.closePath();
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    ctx.stroke(); ctx.restore();
  };
  g.rect = (x, y, w, h, o = {}) => {
    const { color = COL.hud, lw = 1.5, a = 1, fill = null } = o;
    if (a <= 0) return;
    ctx.save(); ctx.globalAlpha *= a;
    if (fill) { ctx.fillStyle = fill; ctx.fillRect(x, y, w, h); }
    if (lw) { ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.strokeRect(x, y, w, h); }
    ctx.restore();
  };
  // 角标框：四个直角，p 为描线进度（按 12 帧/秒步进）
  g.brackets = (x, y, w, h, o = {}) => {
    const { color = COL.hud, lw = 1.5, a = 1, p = 1, len = 18 } = o;
    if (a <= 0 || p <= 0) return;
    const q = Math.floor(p * 6) / 6, l = len * clamp(q * 1.2);
    ctx.save(); ctx.globalAlpha *= a; ctx.strokeStyle = color; ctx.lineWidth = lw;
    const k = lerp(1.6, 1, easeOut(q)), cx = x + w / 2, cy = y + h / 2, ww = w * k, hh = h * k;
    const x0 = cx - ww / 2, y0 = cy - hh / 2, x1 = cx + ww / 2, y1 = cy + hh / 2;
    ctx.beginPath();
    ctx.moveTo(x0, y0 + l); ctx.lineTo(x0, y0); ctx.lineTo(x0 + l, y0);
    ctx.moveTo(x1 - l, y0); ctx.lineTo(x1, y0); ctx.lineTo(x1, y0 + l);
    ctx.moveTo(x1, y1 - l); ctx.lineTo(x1, y1); ctx.lineTo(x1 - l, y1);
    ctx.moveTo(x0 + l, y1); ctx.lineTo(x0, y1); ctx.lineTo(x0, y1 - l);
    ctx.stroke(); ctx.restore();
  };
  // 目标标注：方括号锁定 + 引线 + 标签。p = 出现进度 0..1
  g.tag = (x, y, label, o = {}) => {
    const { p = 1, a = 1, r = 26, dx = 70, dy = -60, color = COL.hud, size = 34, sub = null, subColor = COL.grey } = o;
    if (p <= 0 || a <= 0) return;
    const q = Math.floor(p * 12) / 12;
    g.brackets(x - r, y - r, 2 * r, 2 * r, { p: q * 2, a, color });
    const lp = clamp(q * 2 - 0.6);
    if (lp > 0) {
      const ex = x + Math.sign(dx) * r * 0.7, ey = y + Math.sign(dy) * r * 0.7;
      const mx = x + dx, my = y + dy;
      g.poly([[ex, ey], [lerp(ex, mx, lp), lerp(ey, my, lp)]], { color, w: 1.2, a });
      if (lp >= 1) {
        const tw = g.measure(label, size);
        const hx = mx + Math.sign(dx) * (tw + 24) * clamp(q * 2 - 1.2) * 1.25;
        g.line(mx, my, hx, my, { color, w: 1.2, a });
        const al = Math.sign(dx) > 0 ? 'left' : 'right';
        const tp = clamp((q - 0.65) * 4);
        g.text(label, mx + Math.sign(dx) * 12, my - size * 0.62, { size, color, align: al, a: a * tp, shadow: 8 });
        if (sub) g.text(sub, mx + Math.sign(dx) * 12, my + size * 0.6, { size: size * 0.66, color: subColor, align: al, a: a * tp, font: F.mono, weight: '400', shadow: 6 });
      }
    }
  };
  // 底部字幕
  g.sub = (s, a = 1) => {
    if (!s || a <= 0) return;
    const str = s.replace(/[，、：；]/g, ' ').replace(/[。！？…]+$/g, '').replace(/“|”/g, '"');
    g.text(str, W / 2, H - 92, { size: 46, weight: '500', color: '#fbfaf6', a, shadow: 14, stroke: 4, spacing: 1 });
  };
  // 覆盖式画图（cover），可带缩放和偏移
  g.cover = (im, o = {}) => {
    if (!im) return;
    const { s = 1, x = 0.5, y = 0.5, a = 1, filter = null, box = [0, 0, W, H] } = o;
    const [bx, by, bw, bh] = box;
    const k = Math.max(bw / im.width, bh / im.height) * s;
    const w = im.width * k, h = im.height * k;
    ctx.save();
    ctx.globalAlpha *= a;
    if (filter) ctx.filter = filter;
    ctx.beginPath(); ctx.rect(bx, by, bw, bh); ctx.clip();
    ctx.drawImage(im, bx + (bw - w) * x, by + (bh - h) * y, w, h);
    ctx.restore();
  };
  // 档案相片卡：细白边、底部名字与年份
  g.photo = (im, cx, cy, h, o = {}) => {
    if (!im) return;
    const { a = 1, name = '', years = '', note = '', rot = 0, s = 1, filter = 'grayscale(0.25) sepia(0.25) contrast(1.05) brightness(0.95)', credit = '' } = o;
    if (a <= 0) return;
    const ih = h * s, iw = (im.width / im.height) * ih;
    const pad = 14, capH = name ? 92 : 0;
    ctx.save();
    ctx.globalAlpha *= a;
    ctx.translate(cx, cy); ctx.rotate(rot);
    ctx.shadowColor = 'rgba(0,0,0,0.7)'; ctx.shadowBlur = 50; ctx.shadowOffsetY = 18;
    ctx.fillStyle = '#ece6d8';
    ctx.fillRect(-iw / 2 - pad, -ih / 2 - pad, iw + 2 * pad, ih + 2 * pad + capH);
    ctx.shadowColor = 'transparent';
    ctx.filter = filter;
    ctx.drawImage(im, -iw / 2, -ih / 2, iw, ih);
    ctx.filter = 'none';
    if (name) {
      ctx.fillStyle = '#2a241c'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
      ctx.font = `600 34px ${F.serif}`; ctx.fillText(name, -iw / 2, ih / 2 + pad + 34);
      ctx.font = `400 22px ${F.mono}`; ctx.fillStyle = '#6b6152'; ctx.fillText(years, -iw / 2, ih / 2 + pad + 72);
      if (note) { ctx.textAlign = 'right'; ctx.font = `400 22px ${F.ui}`; ctx.fillText(note, iw / 2, ih / 2 + pad + 72); }
    }
    if (credit) { ctx.textAlign = 'right'; ctx.font = `400 15px ${F.ui}`; ctx.fillStyle = 'rgba(40,36,28,0.6)'; ctx.fillText(credit, iw / 2, ih / 2 + pad + capH - 6); }
    ctx.restore();
  };
  // 打字效果：按字逐个出现（t0 起，每字 dt 秒）
  g.typed = (s, t, t0, dt) => s.slice(0, clamp(Math.floor((t - t0) / dt), 0, s.length));
  return g;
}

// 胶片颗粒与暗角（给 2D 卡片层用，让它和宇宙层质感一致）
export function makeFilm() {
  const grain = [];
  const r = rng(7);
  for (let k = 0; k < 4; k++) {
    const g = mk(512, 512), gx = g.getContext('2d');
    const id = gx.createImageData(512, 512);
    for (let i = 0; i < id.data.length; i += 4) { const v = r() * 255; id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 14; }
    gx.putImageData(id, 0, 0);
    grain.push(g);
  }
  const vig = mk(W, H);
  {
    const v = vig.getContext('2d');
    const g = v.createRadialGradient(W / 2, H / 2, H * 0.4, W / 2, H / 2, H * 1.05);
    g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,0.7)');
    v.fillStyle = g; v.fillRect(0, 0, W, H);
  }
  return { grain, vig };
}
