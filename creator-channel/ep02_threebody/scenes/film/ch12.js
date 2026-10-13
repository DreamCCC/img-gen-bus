// 第一章（两个天体为什么好算）+ 第二章（一百年，只找到两个特例）
import { W, H, COL, F, TINT, SIMCOL, clamp, lerp, prog, smooth, easeOut, easeInOut, fade, keys, mono, at, T, TE, M, clip, img, rng } from './lib.js';
import { OP, FD, TROJ, samp, wp, frameOf, orbitCam, starsOf, trailsOf, ellipse, kepler } from './sim.js';
import { kit } from './common.js';

export function ch12Shots(env) {
  const { g, space, ctx } = env;
  const K = kit(env);
  const A = OP.A;
  const SUN = '#ffd890';
  const photo = {};
  const ph = async (n) => (photo[n] = photo[n] || (await img(`/assets/photos/${n}`)));
  const wan = (name, o = {}) => async (lt) => { const im = await clip(name, lt); g.cover(im, { s: (o.s0 ?? 1.02) + lt * (o.zoom ?? 0.008) }); };

  // ---------- 牛顿书房 + 画像 ----------
  async function newton(lt, t) {
    await wan('W06', { zoom: 0.006 })(lt);
    const a = fade(t, at('A02', '牛顿') - 0.3, TE('A02') + 0.2, 0.5, 0.4);
    if (a > 0) {
      ctx.save(); ctx.globalAlpha *= a * 0.55; ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H); ctx.restore();
      g.photo(await ph('newton.jpg'), 1320, 460, 500, { a, name: '艾萨克·牛顿', years: '1643 – 1727', note: '英国', rot: 0.02, s: 1 + 0.004 * lt });
      g.text('1687', 560, 380, { size: 150, font: F.num, color: COL.gold, a: a * prog(t, T('A02'), T('A02') + 0.4), weight: '600' });
      g.text('《自然哲学的数学原理》', 560, 500, { size: 44, font: F.serif, color: '#f4efe4', a: a * prog(t, at('A02', '自然'), at('A02', '自然') + 0.5), weight: '600', shadow: 12 });
    }
  }

  // ---------- 三种圆锥曲线依次划过太阳 ----------
  const conicPt = (kind, u) => {
    // u: -1..1 时间参数（近日点在 u=0）
    if (kind === 0) return ellipse(1.5, 0.6, u * 0.5 + 0.5, 0);
    if (kind === 1) {      // 抛物线，Barker 方程：D + D³/3 = τ
      const tau = u * 3.2; let D = tau;
      for (let i = 0; i < 20; i++) D -= (D + D * D * D / 3 - tau) / (1 + D * D);
      const th = 2 * Math.atan(D), p = 1.0, r = p / (1 + Math.cos(th));
      const rot = 2.1;
      const x = r * Math.cos(th), y = r * Math.sin(th);
      return [x * Math.cos(rot) - y * Math.sin(rot), 0, -(x * Math.sin(rot) + y * Math.cos(rot))];
    }
    const e = 1.7, a = 0.6, M = u * 6; let Hh = Math.asinh(M / e);
    for (let i = 0; i < 30; i++) Hh -= (e * Math.sinh(Hh) - Hh - M) / (e * Math.cosh(Hh) - 1);
    const x = a * (e - Math.cosh(Hh)), y = a * Math.sqrt(e * e - 1) * Math.sinh(Hh);
    const rot = -2.1;
    return [x * Math.cos(rot) - y * Math.sin(rot), 0, -(x * Math.sin(rot) + y * Math.cos(rot))];
  };
  function conics(lt, t) {
    const cam = orbitCam([0, 0, 0.3], 5.6, 0.95 - 0.01 * lt, 0.2 + 0.015 * lt);
    const ks = [at('A03', '椭圆'), at('A03', '抛物线'), at('A03', '双曲线')];
    const trails = [], planets = [], cols = ['#8fc4ff', '#b6f0c8', '#ffb38a'];
    const heads = [];
    ks.forEach((k0, i) => {
      const p = prog(t, k0 - 0.3, k0 + 1.6);
      if (p <= 0) return;
      const n = 300, pts = new Float32Array(n * 3);
      const u1 = lerp(-1, 1, easeInOut(p));
      for (let j = 0; j < n; j++) pts.set(conicPt(i, lerp(-1, u1, j / (n - 1))), 3 * j);
      trails.push({ pts, col: cols[i], a: 1.0, w: 2.6, fade: 0.4 });
      const hp = conicPt(i, u1);
      planets.push({ type: ['earth', 'moon', 'rock'][i], p: hp, r: 0.04, light: [0, 0, 0] });
      heads.push([i, hp, p]);
    });
    const proj = K.draw3d({ t, cam, stars: [{ p: [0, 0, 0], col: SUN, r: 0.1, glow: 0.42, glowRef: 5 }], trails, planets, dust: { a: 0.3 } });
    const names = ['椭圆', '抛物线', '双曲线'];
    heads.forEach(([i, hp]) => {
      const [x, y] = proj(conicPt(i, i === 0 ? -0.55 : -0.75));
      g.text(names[i], x, y - 30, { size: 38, color: cols[i], a: fade(t, ks[i] - 0.2, TE('A03') + 0.6, 0.3, 0.4), shadow: 10 });
    });
    const two = fade(t, at('A03', '两个天体') - 0.2, at('A03', '椭圆') - 0.1, 0.3, 0.3);
    if (two > 0) g.text('只有两个天体  ·  只有万有引力', W / 2, 140, { size: 36, color: COL.hud, a: two });
  }

  // ---------- 守恒量读数 + 锁 ----------
  const P2 = 3.0, A2 = 1.5, E2 = 0.5;
  function conserved(lt, t) {
    const phs = (t - T('A04')) / P2;
    const pe = ellipse(A2, E2, phs + 0.5);
    const cam = orbitCam([0.5, 0, 0.1], 5.8, 0.7, 0.35 + 0.012 * lt);
    const n = 400, pts = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) pts.set(ellipse(A2, E2, i / (n - 1)), 3 * i);
    const proj = K.draw3d({ t, cam, stars: [{ p: [0, 0, 0], col: SUN, r: 0.1, glow: 0.42, glowRef: 5 }], planets: [{ type: 'earth', p: pe, r: 0.05, light: [0, 0, 0] }], trails: [{ pts, col: '#8fc4ff', a: 0.55, w: 1.4, fade: 0 }], dust: { a: 0.3 } });
    const r = Math.hypot(pe[0], pe[2]), v = Math.sqrt(2 / r - 1 / A2);
    const x = 1180, y0 = 330;
    const ra = fade(t, at('A05', '不管怎么转'), TE('A06') + 0.6, 0.4, 0.4);
    g.rect(x - 40, y0 - 70, 640, 360, { fill: 'rgba(2,6,12,0.55)', color: COL.hud, lw: 1, a: ra * 0.8 });
    K.readout(x, y0, '距离', r.toFixed(3), '在变', { a: ra });
    K.readout(x, y0 + 60, '速度', v.toFixed(3), '在变', { a: ra });
    const e1 = prog(t, at('A05', '总能量') - 0.1, at('A05', '总能量') + 0.4);
    const e2 = prog(t, at('A05', '角动量') - 0.1, at('A05', '角动量') + 0.4);
    K.readout(x, y0 + 140, '总能量', (-1 / (2 * A2)).toFixed(3), '不变', { a: ra * e1, valColor: COL.gold });
    K.readout(x, y0 + 200, '角动量', Math.sqrt(A2 * (1 - E2 * E2)).toFixed(3), '不变', { a: ra * e2, valColor: COL.gold });
    const l1 = prog(t, at('A06', '线索') - 0.1, at('A06', '线索') + 0.25), l2 = prog(t, at('A06', '锁死') - 0.15, at('A06', '锁死') + 0.15);
    K.lock(x - 70, y0 + 140, 36, { p: Math.max(l1, l2 * 0), a: ra * e1 * clamp(l1 * 3) });
    K.lock(x - 70, y0 + 200, 36, { p: l2, a: ra * e2 * clamp(l2 * 3 + l1) });
    const [ex, ey] = proj(pe);
    g.tag(ex, ey, '地球', { p: prog(t, T('A04'), T('A04') + 0.7), a: fade(t, T('A04'), TE('A06'), 0.3, 0.3), color: '#8fc4ff', dx: -80, dy: -70, r: 18 });
    const q = fade(t, at('A06', '锁死') + 0.1, TE('A06') + 0.6, 0.3, 0.4);
    if (q > 0) g.text('答案被锁死：轨道只能是这一个椭圆', W / 2, 140, { size: 36, color: COL.gold, a: q });
  }

  // ---------- 解析解：时间滑块 ----------
  function slider(lt, t) {
    const jump = [at('A07', '把时间代进去'), at('A07', '把时间代进去') + 0.8, at('A07', '任何时刻'), at('A07', '任何时刻') + 0.7];
    const years = [0, 1000, 25, 100000];
    let k = 0; for (let i = 0; i < jump.length; i++) if (t >= jump[i]) k = i + 1;
    const yr = k === 0 ? 0 : years[k - 1];
    const phs = k === 0 ? (t - T('A07')) / P2 : yr * 0.3712 + 0.15;
    const pe = ellipse(A2, E2, phs + 0.5);
    const cam = orbitCam([0.5, 0, 0.1], 5.8, 0.7, 0.35 + 0.012 * (t - T('A04')));
    const n = 400, pts = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) pts.set(ellipse(A2, E2, i / (n - 1)), 3 * i);
    const proj = K.draw3d({ t, cam, stars: [{ p: [0, 0, 0], col: SUN, r: 0.1, glow: 0.42, glowRef: 5 }], planets: [{ type: 'earth', p: pe, r: 0.05, light: [0, 0, 0] }], trails: [{ pts, col: '#8fc4ff', a: 0.55, w: 1.4, fade: 0 }], dust: { a: 0.3 } });
    const [ex, ey] = proj(pe);
    const fl = k > 0 ? 1 - prog(t, jump[k - 1], jump[k - 1] + 0.35) : 0;
    if (fl > 0) { ctx.save(); ctx.globalAlpha *= fl; ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(ex, ey, 20 + 60 * (1 - fl), 0, 7); ctx.stroke(); ctx.restore(); }
    const sa = fade(t, at('A07', '公式') - 0.2, TE('A08') + 0.5, 0.3, 0.4);
    const x0 = 360, x1 = 1560, y = 860;
    g.line(x0, y, x1, y, { color: COL.hud, w: 1.5, a: sa * 0.7 });
    for (let i = 0; i <= 10; i++) g.line(lerp(x0, x1, i / 10), y - 8, lerp(x0, x1, i / 10), y + 8, { color: COL.hud, w: 1, a: sa * 0.5 });
    const hx = lerp(x0, x1, [0, 0.55, 0.12, 0.97][Math.max(0, k - 1)] * (k > 0 ? 1 : 0));
    g.rect(hx - 9, y - 22, 18, 44, { fill: '#fff', lw: 0, a: sa });
    g.text(k === 0 ? '今天' : `${yr.toLocaleString('en-US')} 年后`, hx, y - 50, { size: 30, color: '#fff', a: sa, font: F.ui });
    g.text('时间', x0 - 30, y, { size: 26, color: COL.grey, a: sa, align: 'right', weight: '400' });
    g.text('地球位置 = 公式( 时间 )', W / 2, 150, { size: 46, color: '#fff', a: sa, font: F.serif, weight: '600' });
    const an = prog(t, at('A08', '解析解') - 0.1, at('A08', '解析解') + 0.4) * fade(t, 0, TE('A08') + 0.5, 0, 0.4);
    if (an > 0) {
      g.brackets(W / 2 - 300, 100, 600, 100, { p: an });
      g.text('解析解', W / 2, 232, { size: 40, color: COL.gold, a: an });
    }
  }

  // ---------- 日、地、月 ----------
  function sem(lt, t) {
    const Re = 2.4, Rm = 0.42;
    const th = 0.25 + lt * 0.11, tm = lt * 1.3;
    const pe = [Re * Math.cos(th), 0, -Re * Math.sin(th)];
    const pm = [pe[0] + Rm * Math.cos(tm), 0, pe[2] - Rm * Math.sin(tm)];
    const n = 500, ptsE = new Float32Array(n * 3), ptsM = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const tt = lt - 6 + (6 * i) / (n - 1);
      const a = 0.25 + tt * 0.11, b = tt * 1.3;
      const e = [Re * Math.cos(a), 0, -Re * Math.sin(a)];
      ptsE.set(e, 3 * i);
      ptsM.set([e[0] + Rm * Math.cos(b), 0, e[2] - Rm * Math.sin(b)], 3 * i);
    }
    const cam = orbitCam([pe[0] * 0.8, 0, pe[2] * 0.8], 3.0, 0.6, -0.6 + 0.02 * lt);
    const proj = K.draw3d({
      t, cam, stars: [{ p: [0, 0, 0], col: SUN, r: 0.12, glow: 0.42, glowRef: 5 }],
      planets: [{ type: 'earth', p: pe, r: 0.07, light: [0, 0, 0] }, { type: 'moon', p: pm, r: 0.025, light: [0, 0, 0] }],
      trails: [{ pts: ptsE, col: '#8fc4ff', a: 0.5, w: 1.4 }, { pts: ptsM, col: '#d8d8d8', a: 0.75, w: 1.5 }], dust: { a: 0.3 },
    });
    const [sx, sy] = proj([0, 0, 0]), [ex, ey] = proj(pe), [mx, my] = proj(pm);
    const a = fade(t, T('A10'), TE('A10') + 0.3, 0.3, 0.4);
    g.tag(mx, my, '月亮', { p: prog(t, T('A10'), T('A10') + 0.6), a, color: '#e6e6e6', dx: 80, dy: -80, r: 16 });
    const f = prog(t, at('A10', '地球'), at('A10', '地球') + 0.4), f2 = prog(t, at('A10', '太阳'), at('A10', '太阳') + 0.4);
    const toE = Math.atan2(ey - my, ex - mx), toS = Math.atan2(sy - my, sx - mx);
    if (f > 0) K.arrow(mx, my, mx + Math.cos(toE) * 70 * f, my + Math.sin(toE) * 70 * f, { color: '#8fc4ff', a });
    if (f2 > 0) K.arrow(mx, my, mx + Math.cos(toS) * 150 * f2, my + Math.sin(toS) * 150 * f2, { color: SUN, a });
    if (f2 > 0) g.text('太阳拉月亮的力，大约是地球的 2 倍', W / 2, 140, { size: 32, color: COL.hud, a: a * f2 });
    const n3 = prog(t, at('A10', '三体问题') - 0.1, at('A10', '三体问题') + 0.4);
    if (n3 > 0) g.text('太阳 + 地球 + 月亮 = 三体', W / 2, 200, { size: 40, color: '#fff', a: a * n3 });
    const qa = fade(t, T('A11') + 0.6, TE('A11') + 0.5, 0.5, 0.4);
    if (qa > 0) {
      ctx.save(); ctx.globalAlpha *= qa * 0.55; ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H); ctx.restore();
      K.quote(['“我的头只有研究月亮的时候', '疼过。”'], '— 牛顿，据同时代人的记述', W / 2, 420, { a: qa, p: prog(t, T('A11') + 0.6, T('A11') + 2.0) });
    }
  }

  // ---------- 第二章：名单 ----------
  function names(lt, t) {
    const s = 10 + lt * 0.6, q = samp(A, s);
    const f = frameOf(A, s, [0, 1, 2], 4, 2);
    K.draw3d({ t, cam: orbitCam(f.c, f.R * 4.4 + 2.6, 0.5, 0.5 + 0.02 * lt), stars: starsOf(q), trails: trailsOf(A, s, 6, { a: 0.5 }), dust: { a: 0.8 }, exposure: 0.75 });
    const L = [['欧拉', '1707–1783'], ['拉格朗日', '1736–1813'], ['拉普拉斯', '1749–1827'], ['雅可比', '1804–1851'], ['庞加莱', '1854–1912']];
    const a = fade(t, at('B01', '数学家') - 0.6, T('B02') + 0.4, 0.3, 0.5);
    L.forEach(([n, y], i) => {
      const p = prog(t, at('B01', '数学家') - 0.6 + i * 0.25, at('B01', '数学家') + i * 0.25);
      g.text(n, 300 + i * 330, H / 2 - 20, { size: 54, font: F.serif, weight: '700', color: '#f4efe4', a: a * p, shadow: 14 });
      g.text(y, 300 + i * 330, H / 2 + 40, { size: 22, font: F.mono, color: COL.grey, a: a * p, weight: '400' });
    });
    const b = fade(t, T('B02'), TE('B02') + 0.3, 0.3, 0.3);
    if (b > 0) {
      g.text('通用公式', W / 2 - 260, H / 2, { size: 64, font: F.serif, weight: '700', color: '#9aa0a8', a: b });
      g.line(W / 2 - 400, H / 2, W / 2 - 120, H / 2, { color: COL.red, w: 4, a: b * prog(t, T('B02') + 0.3, T('B02') + 0.7) });
      g.text('特殊情况？', W / 2 + 260, H / 2, { size: 64, font: F.serif, weight: '700', color: COL.gold, a: b * prog(t, at('B02', '特殊'), at('B02', '特殊') + 0.4) });
    }
  }

  // ---------- 欧拉共线解 ----------
  // 三颗等质量星：中间一颗不动，两边相距 1，角速度 √1.25
  const euler = (lt) => { const w = Math.sqrt(1.25) * 0.9, a = lt * w; return [[-Math.cos(a), 0, Math.sin(a)], [0, 0, 0], [Math.cos(a), 0, -Math.sin(a)]]; };
  async function eulerShot(lt, t) {
    const L = at('B03', '一条直线') - 0.4;
    const run = Math.max(0, t - L);
    const P = euler(run);
    const n = 300, tr = [0, 2].map((j) => { const pts = new Float32Array(n * 3); for (let i = 0; i < n; i++) pts.set(euler(Math.max(0, run - 3 + (3 * i) / (n - 1)))[j], 3 * i); return { pts, col: SIMCOL[j], a: 0.7, w: 1.6 }; });
    const proj = K.draw3d({ t, cam: orbitCam([0, 0, 0], 5.2, 0.75, 0.3 + 0.01 * lt), stars: P.map((p, j) => ({ p, col: SIMCOL[j], r: 0.045 })), trails: run > 0 ? tr : [], dust: { a: 0.7 } });
    const S = P.map(proj);
    const la = prog(t, L, L + 0.6);
    if (la > 0) {
      const dx = S[2][0] - S[0][0], dy = S[2][1] - S[0][1];
      g.line(S[0][0] - dx * 0.25, S[0][1] - dy * 0.25, S[2][0] + dx * 0.25, S[2][1] + dy * 0.25, { color: COL.hud, w: 1.2, a: la * 0.7, dash: [10, 8] });
      g.text('一条直线', W / 2, 150, { size: 40, color: COL.hud, a: la * fade(t, 0, TE('B03') + 0.6, 0, 0.4) });
      g.text('队形永远不变', W / 2, 205, { size: 28, color: COL.grey, a: prog(t, at('B03', '永远'), at('B03', '永远') + 0.4) * fade(t, 0, TE('B03') + 0.6, 0, 0.4), weight: '400' });
    }
    const ca = fade(t, at('B03', '欧拉') - 0.3, L + 0.6, 0.4, 0.5);
    if (ca > 0) {
      g.photo(await ph('euler.jpg'), 560, 470, 520, { a: ca, name: '莱昂哈德·欧拉', years: '1707 – 1783', note: '瑞士', rot: -0.02 });
      g.text('1767', 1320, 470, { size: 150, font: F.num, color: COL.gold, a: ca, weight: '600' });
      g.text('第一种特例', 1320, 580, { size: 34, color: '#fff', a: ca });
    }
  }

  // ---------- 拉格朗日三角形 → 开场实验 → 散 → 铅笔 ----------
  const lag = (lt) => { const w = Math.sqrt(3) * 0.5, a = lt * w; return [90, 210, 330].map((d) => { const u = (d * Math.PI) / 180 + a; return [Math.cos(u) / Math.sqrt(3), 0, -Math.sin(u) / Math.sqrt(3)]; }); };
  async function lagrangeShot(lt, t) {
    const L = at('B04', '等边三角形') - 0.4;
    const tOpen = T('B05'), tBreak = T('B06') - 0.3;
    let P, trails = [];
    if (t < tOpen) {
      const run = Math.max(0, t - L);
      P = lag(run);
      const n = 300;
      trails = run > 0 ? [0, 1, 2].map((j) => { const pts = new Float32Array(n * 3); for (let i = 0; i < n; i++) pts.set(lag(Math.max(0, run - 3 + (3 * i) / (n - 1)))[j], 3 * i); return { pts, col: SIMCOL[j], a: 0.7, w: 1.6 }; }) : [];
    } else {
      const s = t < tBreak ? 0 : Math.min(9, (t - tBreak) * 1.6);
      const q = samp(A, s);
      P = [0, 1, 2].map((j) => wp(q, j));
      trails = s > 0 ? trailsOf(A, s, 3.5, { a: 0.75 }) : [];
    }
    const fr = t < tOpen ? { c: [0, 0, 0], R: 0.6 } : frameOf(A, t < tBreak ? 0 : Math.min(9, (t - tBreak) * 1.6), [0, 1, 2], 3, 1);
    const proj = K.draw3d({ t, cam: orbitCam(fr.c, fr.R * 4.4 + 2.2, 0.8, 0.4 + 0.01 * lt), stars: P.map((p, j) => ({ p, col: SIMCOL[j], r: 0.045 })), trails, dust: { a: 0.7 } });
    const S = P.map(proj);
    const la = prog(t, L, L + 0.6) * (1 - prog(t, tBreak, tBreak + 0.3));
    if (la > 0) g.poly([S[0], S[1], S[2], S[0]].map((v) => [v[0], v[1]]), { color: COL.hud, w: 1.2, a: la * 0.7 });
    const tl = fade(t, L, TE('B04') + 0.3, 0.4, 0.3);
    if (tl > 0) g.text('等边三角形 · 永远保持', W / 2, 150, { size: 40, color: COL.hud, a: tl });
    const op = fade(t, tOpen, tBreak + 1.6, 0.3, 0.4);
    if (op > 0) g.text('= 开场实验的起点', W / 2, 150, { size: 40, color: '#fff', a: op });
    const ca = fade(t, at('B04', '拉格朗日') - 0.3, L + 0.6, 0.4, 0.5);
    if (ca > 0) {
      g.photo(await ph('lagrange.jpg'), 560, 470, 520, { a: ca, name: '约瑟夫-路易·拉格朗日', years: '1736 – 1813', note: '意大利 / 法国', rot: 0.02 });
      g.text('1772', 1320, 470, { size: 150, font: F.num, color: COL.gold, a: ca, weight: '600' });
      g.text('第二种特例', 1320, 580, { size: 34, color: '#fff', a: ca });
    }
    const un = fade(t, at('B07', '不稳定') - 0.1, at('B07', '铅笔') - 0.3, 0.2, 0.3);
    if (un > 0) {
      const cx = (S[0][0] + S[1][0] + S[2][0]) / 3, cy = (S[0][1] + S[1][1] + S[2][1]) / 3;
      g.tag(cx, cy, '不稳定', { p: prog(t, at('B07', '不稳定') - 0.1, at('B07', '不稳定') + 0.5), a: un, color: COL.red, r: 40, dx: 130, dy: -120 });
    }
  }
  // 铅笔：θ'' = (3g / 2L) sin θ，碰一下后倒下
  function pencil(lt, t) {
    const tn = at('B07', '碰一下') + 0.15;
    let th = 0;
    if (t > tn) {
      let w = 0.35; th = 0.01;
      const dt = 1 / 240, k = 22;
      for (let x = tn; x < t; x += dt) { w += k * Math.sin(th) * dt; th += w * dt; if (th > Math.PI / 2 - 0.035) { th = Math.PI / 2 - 0.035; w = -w * 0.25; } }
    }
    const cam = { pos: [3.1 * Math.sin(0.5 + lt * 0.05), 1.15, 3.1 * Math.cos(0.5 + lt * 0.05)], look: [0.15, 0.35, 0], fov: 30 };
    K.draw3d({ t, cam, desk: { theta: th }, sky: 0.0, exposure: 1.0, bloom: 0.25, ana: 0 });
    const a = fade(t, at('B07', '理论上'), TE('B07') + 0.3, 0.3, 0.3);
    g.text(t < tn ? '理论上：立得住' : '碰一下：倒', W / 2, 140, { size: 40, color: t < tn ? COL.hud : COL.red, a });
  }

  // ---------- 太阳、木星、小行星：稳定的三角形 ----------
  const RJ = 2.2;
  const jAng = (t) => 0.4 + (t - T('B08')) * 0.18;
  function sunJup(lt, t) {
    const a = jAng(t);
    const pj = [RJ * Math.cos(a), 0, -RJ * Math.sin(a)];
    const pa = [RJ * Math.cos(a + Math.PI / 3), 0, -RJ * Math.sin(a + Math.PI / 3)];
    const n = 400, orb = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { const u = (i / (n - 1)) * Math.PI * 2; orb.set([RJ * Math.cos(u), 0, -RJ * Math.sin(u)], 3 * i); }
    const cam = orbitCam([0.6, 0, -0.6], 6.8, 0.85, -0.3 + 0.012 * lt);
    const proj = K.draw3d({
      t, cam, stars: [{ p: [0, 0, 0], col: SUN, r: 0.14, glow: 0.42, glowRef: 7 }],
      planets: [{ type: 'jupiter', p: pj, r: 0.11, light: [0, 0, 0] }, { type: 'rock', p: pa, r: 0.022, light: [0, 0, 0] }],
      thins: [{ pts: orb, col: '#8aa0c0', a: 0.35 }], dust: { a: 0.3 },
    });
    const S = proj([0, 0, 0]), J = proj(pj), Ast = proj(pa);
    const ma = fade(t, at('B08', '轻重'), TE('B10') + 0.3, 0.3, 0.3);
    g.tag(S[0], S[1], '太阳', { p: prog(t, at('B08', '轻重'), at('B08', '轻重') + 0.6), a: ma, color: SUN, dx: -100, dy: -90, sub: '质量 1', r: 34 });
    g.tag(J[0], J[1], '木星', { p: prog(t, at('B08', '轻重') + 0.2, at('B08', '轻重') + 0.8), a: ma, color: '#e8c9a0', dx: 90, dy: 80, sub: '约 1/1000', r: 24 });
    g.tag(Ast[0], Ast[1], '小行星', { p: prog(t, at('B09', '小行星'), at('B09', '小行星') + 0.6), a: ma, color: '#cfd8ff', dx: 90, dy: -90, sub: '几乎为 0', r: 18 });
    const tri = prog(t, at('B09', '三角形') - 0.2, at('B09', '三角形') + 0.6) * ma;
    if (tri > 0) g.poly([S, J, Ast, S].map((v) => [v[0], v[1]]), { color: COL.hud, w: 1.2, a: tri * 0.7 });
    const st = fade(t, at('B08', '很稳') - 0.1, T('B09') + 1.2, 0.2, 0.4);
    if (st > 0) g.text('轻重差得很远 → 三角形很稳', W / 2, 140, { size: 38, color: COL.gold, a: st });
    const pr = fade(t, T('B10'), TE('B10') + 0.3, 0.3, 0.3);
    if (pr > 0) g.text('1772 年 · 纸上的预言', W / 2, 140, { size: 38, color: '#fff', a: pr });
  }

  // ---------- 天文台 + 沃尔夫 ----------
  async function wolf(lt, t) {
    await wan('W08', { zoom: 0.005 })(lt);
    const a = fade(t, at('B11', '马克斯') - 0.3, TE('B11') + 0.3, 0.4, 0.4);
    if (a > 0) {
      ctx.save(); ctx.globalAlpha *= a * 0.5; ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H); ctx.restore();
      g.photo(await ph('wolf.jpg'), 1400, 460, 470, { a, name: '马克斯·沃尔夫', years: '1863 – 1932', note: '德国天文学家', rot: 0.025 });
    }
    const y = fade(t, T('B11'), TE('B11') + 0.3, 0.3, 0.4);
    g.text('1906', 560, 400, { size: 150, font: F.num, color: COL.gold, a: y, weight: '600' });
    const n = prog(t, at('B11', '阿喀琉斯') - 0.2, at('B11', '阿喀琉斯') + 0.4);
    g.text('发现小行星 588 阿喀琉斯', 560, 510, { size: 40, color: '#fff', a: y * n, shadow: 12 });
  }

  // ---------- 特洛伊小行星群（限制性三体真实积分） ----------
  const TR = FD.trojans;
  const keep = [];
  for (let i = 0; i < TR.n; i++) {
    let ok = true;
    for (let f = 0; f < TR.frames; f += 7) { const x = TROJ[(f * TR.n + i) * 2], y = TROJ[(f * TR.n + i) * 2 + 1]; const r = Math.hypot(x, y); if (r < 0.9 || r > 1.1) { ok = false; break; } }
    if (ok) keep.push(i);
  }
  const order = keep.map((i) => [i, rng(i)()]).sort((a, b) => a[1] - b[1]).map((x) => x[0]);
  const cloudPos = new Float32Array(order.length * 3);
  function trojans(lt, t) {
    const per = (t - T('B12') + 6) * 0.35;                 // 旋转系里的帧号（每帧 = 1/10 木星周期）
    const f = clamp(per, 0, TR.frames - 1.001), i0 = Math.floor(f), u = f - i0;
    const ang = jAng(t);
    const c = Math.cos(ang), s = Math.sin(ang);
    const nShow = Math.floor(lerp(12, order.length, easeInOut(prog(t, T('B12') + 0.4, at('B12', '上万颗') + 0.3))));
    for (let k = 0; k < nShow; k++) {
      const i = order[k];
      const a0 = (i0 * TR.n + i) * 2, a1 = ((i0 + 1) * TR.n + i) * 2;
      const x = lerp(TROJ[a0], TROJ[a1], u) * RJ, y = lerp(TROJ[a0 + 1], TROJ[a1 + 1], u) * RJ;
      cloudPos[3 * k] = x * c - y * s; cloudPos[3 * k + 1] = 0; cloudPos[3 * k + 2] = -(x * s + y * c);
    }
    const pj = [RJ * Math.cos(ang), 0, -RJ * Math.sin(ang)];
    const n = 400, orb = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { const uu = (i / (n - 1)) * Math.PI * 2; orb.set([RJ * Math.cos(uu), 0, -RJ * Math.sin(uu)], 3 * i); }
    const d = lerp(4.5, 9.5, easeInOut(prog(t, T('B12'), TE('B12'))));
    const cam = orbitCam([0.2, 0, -0.2], d, lerp(0.7, 1.05, prog(t, T('B12'), TE('B12'))), -0.3 + 0.012 * (t - T('B08')));
    const proj = K.draw3d({ t, cam, stars: [{ p: [0, 0, 0], col: SUN, r: 0.08, glow: 0.3, glowRef: 9 }], planets: [{ type: 'jupiter', p: pj, r: 0.11, light: [0, 0, 0] }], thins: [{ pts: orb, col: '#8aa0c0', a: 0.3 }], cloud: { pos: cloudPos, n: nShow, col: '#cfdcff', size: lerp(4.5, 3.0, prog(t, T('B12'), TE('B12'))), a: 1.3 }, dust: { a: 0.2 } });
    const a = fade(t, at('B12', '前后') - 0.2, TE('B12') + 0.6, 0.3, 0.4);
    const L4 = proj([RJ * Math.cos(ang + Math.PI / 3), 0, -RJ * Math.sin(ang + Math.PI / 3)]), L5 = proj([RJ * Math.cos(ang - Math.PI / 3), 0, -RJ * Math.sin(ang - Math.PI / 3)]);
    g.tag(L4[0], L4[1], '木星前方 60°', { p: prog(t, at('B12', '前后') - 0.2, at('B12', '前后') + 0.5), a, r: 60, dx: 110, dy: -100 });
    g.tag(L5[0], L5[1], '木星后方 60°', { p: prog(t, at('B12', '前后') + 0.1, at('B12', '前后') + 0.8), a, r: 60, dx: 110, dy: 100 });
    g.text(`${nShow.toLocaleString('en-US')} 颗`, W - 120, 120, { size: 44, font: F.mono, color: '#fff', a: fade(t, T('B12'), TE('B12') + 0.6, 0.3, 0.4), align: 'right', weight: '400' });
    g.text('示意：已知的木星特洛伊小行星有 1 万多颗', W - 120, 168, { size: 22, color: COL.grey, a: a, align: 'right', weight: '400' });
  }

  // ---------- 布伦斯：18 个数，10 条线索 ----------
  const DIAL_COLS = ['x', 'y', 'z', 'vx', 'vy', 'vz'];
  const LOCKED = [0, 1, 2, 3, 4, 5, 7, 9, 13, 16];         // 10 把锁（示意，对应 1 能量 + 3 动量 + 3 角动量 + 3 质心）
  function bruns(lt, t) {
    K.bg(t, { sky: 0.5 });
    const nc = fade(t, T('B14') - 0.1, TE('B15') - 0.2, 0.4, 0.4);
    if (nc > 0) {
      K.nameCard('海因里希·布伦斯', '1848 – 1919', '德国数学家', 640, H / 2 - 20, { a: nc, p: prog(t, at('B14', '布伦斯') - 0.2, at('B14', '布伦斯') + 0.8) });
      g.text('1887', 1380, H / 2 - 20, { size: 150, font: F.num, color: COL.gold, a: nc * prog(t, T('B14'), T('B14') + 0.4), weight: '600' });
    }
    const cl = fade(t, T('B15'), T('B16') + 0.3, 0.3, 0.3);
    if (cl > 0) {
      K.lock(W / 2 - 160, H / 2, 70, { a: cl, p: 1 }); K.lock(W / 2 + 160, H / 2, 70, { a: cl, p: 1 });
      g.text('总能量', W / 2 - 160, H / 2 + 90, { size: 30, color: COL.gold, a: cl }); g.text('角动量', W / 2 + 160, H / 2 + 90, { size: 30, color: COL.gold, a: cl });
    }
    const da = fade(t, T('B16'), TE('B19') + 0.5, 0.4, 0.5);
    if (da <= 0) return;
    const x0 = 640, y0 = 330, dx = 150, dy = 170, r = 52;
    const rows = [at('B16', '三个数说清位置'), at('B16', '三个数说清速度'), at('B16', '十八个数')];
    const lockT = (k) => lerp(at('B17', '十个') - 0.6, at('B17', '十个') + 1.6, k / 9);
    let nLock = 0;
    for (let row = 0; row < 3; row++) {
      g.text(['红星', '蓝星', '黄星'][row], x0 - 120, y0 + row * dy, { size: 32, color: SIMCOL[row], a: da * prog(t, T('B16'), T('B16') + 0.5), align: 'right' });
      for (let col = 0; col < 6; col++) {
        const idx = row * 6 + col;
        const app = col < 3 ? prog(t, rows[0] - 0.2 + col * 0.08 + row * 0.12, rows[0] + 0.3 + col * 0.08 + row * 0.12) : prog(t, rows[1] - 0.2 + (col - 3) * 0.08 + row * 0.12, rows[1] + 0.3 + (col - 3) * 0.08 + row * 0.12);
        const li = LOCKED.indexOf(idx);
        const lp = li >= 0 ? prog(t, lockT(li), lockT(li) + 0.25) : 0;
        const tt = li >= 0 ? Math.min(t, lockT(li)) : t;
        const ang = rng(idx + 9)() * 6.28 + tt * (1.2 + 1.7 * rng(idx + 3)());
        const x = x0 + col * dx, y = y0 + row * dy;
        K.dial(x, y, r, ang, { a: da * app, locked: lp >= 1, color: lp >= 1 ? COL.gold : COL.hud });
        if (row === 0) g.text(DIAL_COLS[col], x, y0 - r - 30, { size: 24, font: F.mono, color: COL.grey, a: da * app, weight: '400' });
        if (li >= 0 && lp > 0) { K.lock(x + r * 0.75, y + r * 0.75, 30, { p: lp, a: da }); nLock++; }
      }
    }
    g.text('位置', x0 + dx, y0 - r - 70, { size: 26, color: COL.hud, a: da * prog(t, rows[0], rows[0] + 0.4) });
    g.text('速度', x0 + 4 * dx, y0 - r - 70, { size: 26, color: COL.hud, a: da * prog(t, rows[1], rows[1] + 0.4) });
    const cnt = prog(t, rows[2] - 0.1, rows[2] + 0.3);
    g.text('18 个数', 1660, y0 + dy - 40, { size: 56, font: F.ui, color: '#fff', a: da * cnt });
    const lk = prog(t, at('B17', '十个') - 0.6, at('B17', '十个') + 1.8);
    g.text(`${nLock} 条线索`, 1660, y0 + dy + 40, { size: 46, font: F.ui, color: COL.gold, a: da * clamp(lk * 4) });
    const ex = prog(t, at('B18', '锁不住') - 0.2, at('B18', '锁不住') + 0.4);
    if (ex > 0) g.text('剩下 8 个锁不住', 1660, y0 + dy + 110, { size: 34, color: COL.red, a: da * ex });
    const no = prog(t, at('B19', '走不通') - 0.4, at('B19', '走不通') + 0.2);
    if (no > 0) {
      ctx.save(); ctx.globalAlpha *= da * no * 0.6; ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H); ctx.restore();
      g.text('通用公式', W / 2, H / 2 - 20, { size: 96, font: F.serif, weight: '700', color: '#c8c8cc', a: da * no });
      g.line(W / 2 - 240, H / 2 - 20, W / 2 + 240, H / 2 - 20, { color: COL.red, w: 6, a: da * prog(t, at('B19', '走不通'), at('B19', '走不通') + 0.3) });
      g.text('此路不通', W / 2, H / 2 + 90, { size: 36, color: COL.red, a: da * no });
    }
    g.text('示意：10 条 = 能量 1 + 动量 3 + 角动量 3 + 质心运动 3', W / 2, H - 170, { size: 22, color: COL.grey, a: da * clamp(lk * 3) * (1 - no), weight: '400' });
  }

  return [
    { a: M('ch1_end') - 0.2, b: TE('A02') + 0.4, fi: 0.4, fo: 0.4, draw: newton },
    { a: TE('A02') + 0.1, b: TE('A03') + 0.7, fi: 0.4, fo: 0.4, draw: conics },
    { a: TE('A03') + 0.4, b: T('A07') + 0.1, fi: 0.4, fo: 0.0, draw: conserved },
    { a: T('A07'), b: TE('A08') + 0.6, fi: 0.0, fo: 0.4, draw: slider },
    { a: T('A09') - 0.6, b: T('A10') + 0.3, fi: 0.3, fo: 0.4, draw: wan('W07', { zoom: 0.01 }) },
    { a: T('A10') - 0.1, b: M('pre_ch2') + 0.5, fi: 0.4, fo: 0.6, draw: sem },
    { a: M('ch2_end') - 0.2, b: at('B03', '欧拉') - 0.1, fi: 0.4, fo: 0.4, draw: names },
    { a: at('B03', '欧拉') - 0.4, b: T('B04') - 0.1, fi: 0.4, fo: 0.4, draw: eulerShot },
    { a: T('B04') - 0.4, b: at('B07', '铅笔') - 0.1, fi: 0.4, fo: 0.3, draw: lagrangeShot },
    { a: at('B07', '铅笔') - 0.3, b: TE('B07') + 0.5, fi: 0.3, fo: 0.4, draw: pencil },
    { a: TE('B07') + 0.2, b: T('B11') + 0.1, fi: 0.4, fo: 0.4, draw: sunJup },
    { a: T('B11') - 0.2, b: T('B12') + 0.1, fi: 0.4, fo: 0.4, draw: wolf },
    { a: T('B12') - 0.2, b: T('B13') + 0.9, fi: 0.4, fo: 0.8, draw: trojans },
    { a: T('B14') - 0.6, b: M('pre_ch3') + 0.6, fi: 0.5, fo: 0.6, draw: bruns },
  ];
}
