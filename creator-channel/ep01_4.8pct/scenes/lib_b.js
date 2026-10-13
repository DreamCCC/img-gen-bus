// B 站横版共用绘制库：字体、纸纹、12 帧/秒手绘标注、小人方阵、字幕。所有随机都走 hash/rng，保证逐帧确定。
const W = 1920, H = 1080;
const cv = document.getElementById('c'), ctx = cv.getContext('2d');

const F = { hand: '"WenKai"', serif: '"NSerif"', sans: '"NSans"', num: '"Barlow"', mono: '"Plex", "NSerif"' };
const C = {
  warmDesk: '#2a2018', warmDark: '#1d1712', warmPaper: '#ece1c8', warmInk: '#2b2520', amber: '#f0c06a', pen: '#c8452f',
  coolDesk: '#1b222b', coolPaper: '#e9ecea', coolInk: '#1e252c',
  bg: '#f2efe7', ink: '#1f2328', mute: '#d9d4c8', red: '#d2412a',
};

const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const prog = (t, a, b) => clamp((t - a) / (b - a));
const lerp = (a, b, u) => a + (b - a) * u;
const easeOut = (x) => 1 - Math.pow(1 - x, 3);
const easeIO = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const easeBack = (x) => { const c = 1.7; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
const ap = (t, t0, d = 0.5) => easeOut(prog(t, t0, t0 + d));
function hash(a, b = 0) { const h = Math.sin(a * 127.1 + b * 311.7) * 43758.5453; return h - Math.floor(h); }
function rng(seed) { return () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let x = Math.imul(seed ^ (seed >>> 15), 1 | seed); x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x; return ((x ^ (x >>> 14)) >>> 0) / 4294967296; }; }
const step12 = (t) => Math.floor(t * 12);

function off(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return [c, c.getContext('2d')]; }
function makeGrain(seed) {
  const [c, g] = off(512, 512), img = g.createImageData(512, 512), r = rng(seed);
  for (let i = 0; i < img.data.length; i += 4) { const v = r() * 255; img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255; }
  g.putImageData(img, 0, 0); return c;
}
function makePaper(base, seed) {
  const [c, g] = off(1024, 1024), r = rng(seed);
  g.fillStyle = base; g.fillRect(0, 0, 1024, 1024);
  for (let i = 0; i < 26; i++) {
    const x = r() * 1024, y = r() * 1024, rad = 80 + r() * 260, gr = g.createRadialGradient(x, y, 0, x, y, rad);
    gr.addColorStop(0, `rgba(120,90,50,${0.03 + r() * 0.04})`); gr.addColorStop(1, 'rgba(120,90,50,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 1024, 1024);
  }
  for (let i = 0; i < 2600; i++) {
    const x = r() * 1024, y = r() * 1024, a = r() * Math.PI, l = 3 + r() * 12;
    g.strokeStyle = `rgba(${r() < 0.5 ? '90,70,40' : '255,255,255'},${0.05 + r() * 0.08})`; g.lineWidth = 0.6;
    g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(a) * l, y + Math.sin(a) * l); g.stroke();
  }
  return c;
}
function makeDesk(base, grainCol, seed) {
  const [c, g] = off(W, H), r = rng(seed);
  g.fillStyle = base; g.fillRect(0, 0, W, H);
  for (let i = 0; i < 260; i++) {
    const y0 = r() * H, amp = 4 + r() * 14, fr = 0.002 + r() * 0.004, ph = r() * 9;
    g.strokeStyle = `rgba(${grainCol},${0.025 + r() * 0.05})`; g.lineWidth = 0.8 + r() * 2.2;
    g.beginPath();
    for (let x = 0; x <= W; x += 16) { const y = y0 + Math.sin(x * fr + ph) * amp + Math.sin(x * fr * 3.1 + ph) * amp * 0.3; x ? g.lineTo(x, y) : g.moveTo(x, y); }
    g.stroke();
  }
  const v = g.createRadialGradient(W * 0.5, H * 0.45, H * 0.2, W * 0.5, H * 0.5, H * 1.05);
  v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,0.55)');
  g.fillStyle = v; g.fillRect(0, 0, W, H);
  return c;
}
const HATCH = {};
function hatch(col, gap = 9, lw = 3) {
  const k = col + gap + lw;
  if (!HATCH[k]) {
    const [c, g] = off(gap * 4, gap * 4);
    g.strokeStyle = col; g.lineWidth = lw;
    for (let i = -4; i < 8; i++) { g.beginPath(); g.moveTo(i * gap, gap * 4); g.lineTo(i * gap + gap * 4, 0); g.stroke(); }
    HATCH[k] = ctx.createPattern(c, 'repeat');
  }
  return HATCH[k];
}

const TEX = {}, IMG = {};
function loadImg(k, src) { return new Promise((res, rej) => { const im = new Image(); im.onload = () => { IMG[k] = im; res(); }; im.onerror = rej; im.src = src; }); }
async function libReady(images = {}) {
  const specs = ['700 40px NSerif', '400 40px NSerif', '700 40px NSans', '400 40px NSans', '40px WenKai', '40px Barlow', '40px Plex'];
  await Promise.all(specs.map((s) => document.fonts.load(s, '高考录取率一九七七年部长 0123456789%')));
  await Promise.all(Object.entries(images).map(([k, v]) => loadImg(k, v)));
  TEX.grain = [1, 2, 3, 4].map(makeGrain);
  TEX.paperWarm = makePaper(C.warmPaper, 11);
  TEX.paperNews = makePaper('#e4dccb', 12);
  TEX.paperCool = makePaper(C.coolPaper, 13);
  TEX.sticky = makePaper('#f1dc84', 14);
  TEX.paperCard = makePaper('#f3ecd9', 15);
  TEX.deskWarm = makeDesk(C.warmDesk, '10,6,3', 21);
  TEX.deskCool = makeDesk(C.coolDesk, '0,4,10', 22);
}

function text(s, x, y, { size = 40, font = F.sans, weight = 400, color = '#fff', align = 'left', base = 'alphabetic', alpha = 1, spacing = 0 } = {}) {
  if (alpha <= 0) return;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.font = `${weight} ${size}px ${font}`; ctx.fillStyle = color;
  ctx.textAlign = align; ctx.textBaseline = base; if (spacing) ctx.letterSpacing = spacing + 'px';
  ctx.fillText(s, x, y); ctx.restore();
}
function measure(s, size, font = F.sans, weight = 400) { ctx.save(); ctx.font = `${weight} ${size}px ${font}`; const w = ctx.measureText(s).width; ctx.restore(); return w; }
// 打字机：按每秒 cps 个字显示
function typed(s, t, t0, cps = 10) { return [...s].slice(0, Math.max(0, Math.floor((t - t0) * cps))).join(''); }
function wrap(s, maxW, font) {
  ctx.save(); ctx.font = font; const lines = []; let cur = '', xs = [], x = 0;
  for (const ch of s) {
    const w = ctx.measureText(ch).width;
    if (x + w > maxW && cur) { lines.push({ s: cur, xs, w: x }); cur = ''; xs = []; x = 0; }
    xs.push(x); cur += ch; x += w;
  }
  if (cur) lines.push({ s: cur, xs, w: x });
  ctx.restore(); return lines;
}
function paragraph(s, x, y, maxW, { size = 30, lh = 52, font = F.serif, weight = 400, color = '#222', indent = 2 } = {}) {
  const f = `${weight} ${size}px ${font}`, pad = '\u3000'.repeat(indent);
  const lines = wrap(pad + s, maxW, f);
  ctx.save(); ctx.font = f; ctx.fillStyle = color; ctx.textBaseline = 'alphabetic';
  lines.forEach((l, i) => ctx.fillText(l.s, x, y + i * lh)); ctx.restore();
  return { lines, x, y, lh, size, end: y + lines.length * lh };
}
function locate(p, word) {
  for (let i = 0; i < p.lines.length; i++) {
    const k = p.lines[i].s.indexOf(word);
    if (k >= 0) {
      const xs = p.lines[i].xs, x0 = p.x + xs[k], x1 = k + word.length < xs.length ? p.x + xs[k + word.length] : p.x + p.lines[i].w;
      return { x0, x1, cy: p.y + i * p.lh - p.size * 0.36, h: p.size * 1.25 };
    }
  }
}
function paper(tex, x, y, w, h, rot, draw, { shadow = 0.5 } = {}) {
  ctx.save(); ctx.translate(x + w / 2, y + h / 2); ctx.rotate(rot); ctx.translate(-w / 2, -h / 2);
  ctx.save(); ctx.shadowColor = `rgba(0,0,0,${shadow})`; ctx.shadowBlur = 40; ctx.shadowOffsetX = 10; ctx.shadowOffsetY = 18;
  ctx.fillStyle = ctx.createPattern(tex, 'repeat'); ctx.fillRect(0, 0, w, h); ctx.restore();
  const eg = ctx.createLinearGradient(0, 0, w, h); eg.addColorStop(0, 'rgba(255,255,255,0.05)'); eg.addColorStop(1, 'rgba(80,50,20,0.08)');
  ctx.fillStyle = eg; ctx.fillRect(0, 0, w, h);
  draw && draw(w, h); ctx.restore();
}

// 12 帧/秒步进的手绘标注
function handEllipse(cx, cy, rx, ry, t, p, { color = C.pen, lw = 4, seed = 1 } = {}) {
  if (p <= 0) return;
  const s = step12(t), n = 64, a0 = -2.4 + hash(seed, 9) * 0.4, sweep = Math.PI * 2 * 1.12;
  ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.beginPath();
  const m = Math.max(2, Math.floor(n * p));
  for (let i = 0; i <= m; i++) {
    const u = i / n, a = a0 + sweep * u, j = 1 + (hash(seed + i, s) - 0.5) * 0.05 + u * 0.06;
    const x = cx + Math.cos(a) * rx * j, y = cy + Math.sin(a) * ry * j + Math.sin(u * 7 + seed) * 2;
    i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  }
  ctx.stroke(); ctx.restore();
}
function handLine(x0, y0, x1, y1, t, p, { color = C.pen, lw = 4, seed = 3, bow = 6 } = {}) {
  if (p <= 0) return;
  const s = step12(t), n = 24, m = Math.max(1, Math.floor(n * p));
  ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.lineCap = 'round'; ctx.beginPath();
  for (let i = 0; i <= m; i++) {
    const u = i / n, x = x0 + (x1 - x0) * u, y = y0 + (y1 - y0) * u + Math.sin(u * Math.PI) * bow + (hash(seed + i, s) - 0.5) * 2.2;
    i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  }
  ctx.stroke(); ctx.restore();
}
function handArrow(x0, y0, x1, y1, t, p, opt = {}) {
  handLine(x0, y0, x1, y1, t, p, { bow: -14, ...opt });
  if (p < 1) return;
  const a = Math.atan2(y1 - y0, x1 - x0), L = 22;
  for (const d of [2.6, -2.6]) handLine(x1, y1, x1 + Math.cos(a + d) * L, y1 + Math.sin(a + d) * L, t, 1, { ...opt, bow: 0, seed: (opt.seed || 3) + d * 10 });
}
function handCheck(x, y, s, t, p, opt = {}) {
  handLine(x, y, x + s * 0.35, y + s * 0.4, t, clamp(p * 2), { bow: 0, ...opt });
  handLine(x + s * 0.35, y + s * 0.4, x + s, y - s * 0.5, t, clamp(p * 2 - 1), { bow: 0, ...opt, seed: (opt.seed || 3) + 5 });
}
// 手绘大括号（水平，开口向下）
function handBracket(x0, x1, y, t, p, opt = {}) {
  const m = (x0 + x1) / 2;
  handLine(x0, y + 14, x0 + 10, y, t, clamp(p * 4), { bow: 0, ...opt });
  handLine(x0 + 10, y, m - 12, y, t, clamp(p * 4 - 1), { bow: 0, ...opt, seed: 51 });
  handLine(m - 12, y, m, y - 14, t, clamp(p * 4 - 2), { bow: 0, ...opt, seed: 52 });
  handLine(m, y - 14, m + 12, y, t, clamp(p * 4 - 2), { bow: 0, ...opt, seed: 53 });
  handLine(m + 12, y, x1 - 10, y, t, clamp(p * 4 - 2), { bow: 0, ...opt, seed: 54 });
  handLine(x1 - 10, y, x1, y + 14, t, clamp(p * 4 - 3), { bow: 0, ...opt, seed: 55 });
}

function person(x, y, s, fill) {
  ctx.fillStyle = fill; ctx.beginPath(); ctx.arc(x, y - s * 0.28, s * 0.17, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.moveTo(x - s * 0.3, y + s * 0.36);
  ctx.quadraticCurveTo(x - s * 0.32, y - s * 0.06, x, y - s * 0.07);
  ctx.quadraticCurveTo(x + s * 0.32, y - s * 0.06, x + s * 0.3, y + s * 0.36); ctx.closePath(); ctx.fill();
}
// 小人方阵：layers = [{to: 累计格数, fill}]，按顺序从左到右逐格填充，支持小数格
function dotGrid(x, y, cols, rows, cell, s, base, layers) {
  const n = cols * rows;
  for (let i = 0; i < n; i++) {
    const cx = x + (i % cols) * cell + cell / 2, cy = y + Math.floor(i / cols) * cell + cell / 2;
    person(cx, cy, s, base);
    let from = 0;
    for (const L of layers) {
      const a = clamp(L.to - i) , f = clamp(from - i);
      if (a > f) {
        ctx.save(); ctx.beginPath(); ctx.rect(cx - s / 2 + s * f, cy - s / 2, s * (a - f) + 0.5, s); ctx.clip();
        if (L.alpha !== undefined) ctx.globalAlpha = L.alpha;
        person(cx, cy, s, L.fill); ctx.restore();
      }
      from = Math.max(from, L.to);
    }
  }
}
function gridCell(x, y, cols, cell, i) { return [x + (i % cols) * cell + cell / 2, y + Math.floor(i / cols) * cell + cell / 2]; }

// 铺满画面的图片 + 慢推：focus 为图内归一化焦点，z 为缩放
function cover(img, z = 1, fx = 0.5, fy = 0.5) {
  const s = Math.max(W / img.width, H / img.height) * z, w = img.width * s, h = img.height * s;
  const x = clamp(W / 2 - fx * w, W - w, 0), y = clamp(H / 2 - fy * h, H - h, 0);
  ctx.drawImage(img, x, y, w, h);
}
function grade(tint, vig = 0.45) {
  if (tint) { ctx.fillStyle = tint; ctx.fillRect(0, 0, W, H); }
  const v = ctx.createRadialGradient(W / 2, H * 0.48, H * 0.3, W / 2, H / 2, H * 1.0);
  v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, `rgba(0,0,0,${vig})`); ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
}
function grain(t, amt) {
  if (!amt) return;
  ctx.save(); ctx.globalAlpha = amt; ctx.globalCompositeOperation = 'overlay';
  ctx.fillStyle = ctx.createPattern(TEX.grain[Math.floor(t * 30) % 4], 'repeat'); ctx.fillRect(0, 0, W, H); ctx.restore();
}
function camera(z, fx, fy, draw, tx = fx, ty = fy) {
  ctx.save(); ctx.translate(tx, ty); ctx.scale(z, z); ctx.translate(-fx, -fy); draw(); ctx.restore();
}
function black(a) { if (a > 0) { ctx.fillStyle = `rgba(0,0,0,${a})`; ctx.fillRect(0, 0, W, H); } }
function sourceTag(s, color = 'rgba(255,255,255,0.55)') { text(s, 60, 62, { size: 22, color, font: F.sans }); }

function subtitle(s, { light = false } = {}) {
  if (!s) return;
  ctx.save(); ctx.font = `700 44px ${F.sans}`; const w = ctx.measureText(s).width + 56;
  ctx.fillStyle = light ? 'rgba(20,22,26,0.78)' : 'rgba(0,0,0,0.55)';
  const x = (W - w) / 2, y = 958; ctx.beginPath(); ctx.roundRect(x, y, w, 70, 10); ctx.fill();
  ctx.fillStyle = '#fff'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(s, W / 2, y + 37); ctx.restore();
}
// 把一句旁白切成字幕块（每块不超过 maxLen 字，在标点处断），按字数分配时长
function subChunks(v, maxLen = 22) {
  const len = (s) => s.replace(/\s/g, '').length;
  const hard = v.text.match(/[^。；？！]+[。；？！”]*/g) || [v.text], chunks = [];
  for (const seg of hard) {
    if (len(seg) <= maxLen) { chunks.push(seg); continue; }
    let cur = '';
    for (const p of seg.match(/[^，：]+[，：“]*/g)) {
      if (cur && len(cur + p) > maxLen) { chunks.push(cur); cur = p; } else cur += p;
    }
    if (cur) chunks.push(cur);
  }
  const tot = chunks.reduce((a, s) => a + len(s), 0);
  let t = v.t;
  return chunks.map((s) => { const d = v.dur * len(s) / tot, c = { a: t, b: t + d, s: s.replace(/[，。；：“]+$/, '') }; t += d; return c; });
}
