// 第五章（那就一步一步算）+ 第六章（天上真有三体吗）+ 结尾 + 片尾
import { W, H, COL, F, TINT, SIMCOL, clamp, lerp, prog, smooth, easeOut, easeInOut, fade, mono, at, T, TE, M, FILM, clip, img, rng } from './lib.js';
import { OP, FD, samp, wp, frameOf, orbitCam, starsOf, trailsOf, ellipse } from './sim.js';
import { kit } from './common.js';

export function ch56Shots(env) {
  const { g, space, ctx } = env;
  const K = kit(env);
  const A = OP.A;
  const SUN = '#ffd890';
  const photo = {};
  const ph = async (n) => (photo[n] = photo[n] || (await img(`/assets/photos/${n}`)));
  const wan = (name, o = {}) => async (lt) => { const im = await clip(name, lt); g.cover(im, { s: (o.s0 ?? 1.02) + lt * (o.zoom ?? 0.008) }); };
  const dim = (a) => { ctx.save(); ctx.globalAlpha *= a; ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H); ctx.restore(); };
  const year = (s, x, y, a, size = 150) => g.text(s, x, y, { size, font: F.num, color: COL.gold, a, weight: '600' });
  const draw3dAt = (cfg, x, y) => {
    const cv = space.draw(cfg);
    ctx.drawImage(cv, x, y);
    return (p) => { const v = space.project(p); return [v[0] + x, v[1] + y, v[2]]; };
  };
  const ring = (r, n = 360, cx = 0, cz = 0) => { const pts = new Float32Array(n * 3); for (let i = 0; i < n; i++) { const u = (i / (n - 1)) * 6.2832; pts.set([cx + r * Math.cos(u), 0, cz - r * Math.sin(u)], 3 * i); } return pts; };
  const fmt = (n) => Math.round(n).toLocaleString('en-US');

  // ---------- 周期轨道取样（首尾相接，按周期取模） ----------
  const PER = FD.periodic;
  const BOX = {};
  for (const [k, o] of Object.entries(PER)) { let r = 0; for (const q of o.pts) for (const v of q) r = Math.max(r, Math.abs(v)); BOX[k] = r; }
  function psamp(name, s) {
    const o = PER[name], n = o.pts.length - 1;
    const f = ((((s % o.T) + o.T) % o.T) / o.T) * n, i = Math.min(n - 1, Math.floor(f)), u = f - i;
    const a = o.pts[i], b = o.pts[i + 1];
    return a.map((x, k) => x + (b[k] - x) * u);
  }
  const xf = (x, y, o = {}) => { const k = o.k ?? 1, c = Math.cos(o.rot ?? 0), s = Math.sin(o.rot ?? 0); const X = (x * c - y * s) * k, Y = (x * s + y * c) * k; const tl = o.tilt ?? 0; return [X + (o.ox ?? 0), Y * Math.sin(tl) + (o.oy ?? 0), -Y * Math.cos(tl) + (o.oz ?? 0)]; };
  function ptrail(name, s, j, span, n = 300, o = {}) {
    const out = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { const q = psamp(name, s - span + (span * i) / (n - 1)); out.set(xf(q[2 * j], q[2 * j + 1], o), 3 * i); }
    return out;
  }
  const ppos = (name, s, j, o = {}) => { const q = psamp(name, s); return xf(q[2 * j], q[2 * j + 1], o); };

  // ---------- 一步一步算：开场模拟变成离散的小步 ----------
  const S0 = 8;
  const sCont = mono([[M('ch5_end') - 0.2, S0], [T('E03'), S0 + 3.2], [TE('E03'), S0 + 6.4], [T('E04') + 0.6, S0 + 7.2], [TE('E04') + 0.4, S0 + 16]]);
  const stepH = (t) => (t < T('E04') ? 0.32 : 0.32 * Math.pow(0.025, prog(t, T('E04'), TE('E04') - 0.4)));
  const accel = (q, i) => { let ax = 0, ay = 0; for (let j = 0; j < 3; j++) { if (j === i) continue; const dx = q[2 * j] - q[2 * i], dy = q[2 * j + 1] - q[2 * i + 1], r = Math.hypot(dx, dy); ax += dx / r ** 3; ay += dy / r ** 3; } return [ax, ay]; };
  function steps(lt, t) {
    const sc = sCont(t), stepping = t > T('E03') - 0.1, h = stepH(t);
    let sd = sc;
    if (stepping) { const k = sc / h, kf = Math.floor(k); sd = (kf + smooth(clamp((k - kf) / 0.3))) * h; }
    const q = samp(A, sd), f = frameOf(A, sc, [0, 1, 2], 3, 1.5);
    const cam = orbitCam(f.c, f.R * 3.4 + 1.2, 1.18, 0.3 + 0.01 * lt);
    const ta = stepping ? 0.75 * prog(t, T('E04') + 0.3, TE('E04') - 0.6) : 0.75;
    const proj = K.draw3d({ t, cam, stars: starsOf(q, { r: 0.04, glow: 0.8 }).map((o) => ({ ...o, glowRef: f.R * 3.4 + 1.2 })), trails: trailsOf(A, sd, 4, { a: ta }), dust: { a: 0.6 } });
    // 走夜路：只照亮脚下
    const nl = fade(t, at('E02', '走夜路') - 0.2, TE('E02') + 0.3, 0.6, 0.6);
    if (nl > 0) {
      const P = [0, 1, 2].map((j) => proj(wp(q, j)));
      const cx = (P[0][0] + P[1][0] + P[2][0]) / 3, cy = (P[0][1] + P[1][1] + P[2][1]) / 3;
      const gr = ctx.createRadialGradient(cx, cy, 120, cx, cy, 520);
      gr.addColorStop(0, 'rgba(0,0,0,0)'); gr.addColorStop(1, 'rgba(0,0,0,0.92)');
      ctx.save(); ctx.globalAlpha *= nl; ctx.fillStyle = gr; ctx.fillRect(0, 0, W, H); ctx.restore();
      g.text('看不清远处', W / 2, 150, { size: 40, color: COL.grey, a: nl * prog(t, at('E02', '看不清'), at('E02', '看不清') + 0.4) });
      g.text('只看清脚下这一步', W / 2, 210, { size: 46, color: '#fff', a: nl * prog(t, at('E02', '只管'), at('E02', '只管') + 0.4) });
    }
    if (stepping) {
      // 每一步一个小箭头，首尾相连
      const sa = fade(t, T('E03') - 0.1, TE('E04') + 0.4, 0.3, 0.4);
      const N = Math.min(240, Math.floor(3.2 / h)), kf = Math.floor(sc / h);
      for (let j = 0; j < 3; j++) {
        let prev = null;
        for (let i = N; i >= 0; i--) {
          const s1 = (kf - i) * h;
          if (s1 < S0 + 3) continue;
          const p = proj(wp(samp(A, s1), j));
          if (prev) {
            const al = sa * (1 - i / (N + 1)) * (h > 0.05 ? 1 : 0.8);
            if (h > 0.05) K.arrow(prev[0], prev[1], p[0], p[1], { color: SIMCOL[j], w: 2.6, a: al, head: 12 });
            else g.line(prev[0], prev[1], p[0], p[1], { color: SIMCOL[j], w: 2, a: al });
          }
          prev = p;
        }
      }
      // 这一小段里，力当作不变
      const fa = sa * fade(t, at('E03', '假装') - 0.1, at('E03', '再挪一小步') + 0.6, 0.3, 0.4);
      if (fa > 0) {
        const qs = samp(A, Math.floor(sc / h) * h);
        for (let i = 0; i < 3; i++) {
          const [ax, ay] = accel(qs, i), m = Math.hypot(ax, ay), L = 0.25 * clamp(m / 2, 0.5, 1.6);
          const p0 = proj(wp(qs, i)), p1 = proj([qs[2 * i] + (ax / m) * L, 0, -(qs[2 * i + 1] + (ay / m) * L)]);
          K.arrow(p0[0], p0[1], p1[0], p1[1], { color: '#ffffff', w: 2.5, a: fa, head: 13 });
        }
      }
      // 步骤清单
      const L = [['E03', '切成', '① 把时间切成很小的一段'], ['E03', '假装', '② 假装这一段里，力不变'], ['E03', '挪到了哪儿', '③ 算出挪到了哪儿'], ['E03', '重新算力', '④ 按新位置，重新算力'], ['E03', '再挪一小步', '↻ 再挪一小步……']];
      const la = fade(t, T('E03'), T('E04') + 0.6, 0.3, 0.5);
      L.forEach(([id, w, s], i) => {
        const t0 = at(id, w), nx = i + 1 < L.length ? at(L[i + 1][0], L[i + 1][1]) : TE('E03') + 2;
        const on = t >= t0 && t < nx;
        g.text(s, 120, 300 + i * 74, { size: 40, color: on ? COL.gold : '#d8dde6', a: la * prog(t, t0 - 0.1, t0 + 0.3) * (on ? 1 : 0.6), align: 'left', shadow: 10 });
      });
      g.text(`第 ${fmt(Math.max(0, (sc - S0 - 3.2) / h))} 步`, W - 120, 120, { size: 40, font: F.mono, color: COL.hud, a: sa, align: 'right', weight: '400' });
      g.text(`每步 Δt = ${h.toFixed(h > 0.05 ? 2 : 3)}`, W - 120, 175, { size: 28, font: F.mono, color: COL.grey, a: sa, align: 'right', weight: '400' });
      const ea = fade(t, at('E04', '开头') - 0.2, TE('E04') + 0.4, 0.3, 0.4);
      g.text('步子越小，算得越准', W / 2, 150, { size: 44, color: '#fff', a: ea * prog(t, T('E04') + 0.4, T('E04') + 1.0), shadow: 12 });
      g.text('开头那两段模拟，就是这样算出来的', W / 2, 215, { size: 34, color: COL.gold, a: ea * prog(t, at('E04', '开头'), at('E04', '开头') + 0.4), shadow: 12 });
    }
  }

  // ---------- 周期解：转一圈回到原样 ----------
  function periodic(lt, t) {
    const name = 'butterfly2', Tp = PER[name].T, R = BOX[name];
    const s = Math.max(0, (t - T('E05') - 0.2) * (Tp / 4.6));
    const o = { k: 1 };
    const cam = orbitCam([0, 0, 0], R * 4.2 + 0.4, 1.32, 0.2 + 0.02 * lt);
    const span = Math.min(s, Tp);
    const trails = [0, 1, 2].map((j) => ({ pts: ptrail(name, s, j, Math.max(span, 0.01), 400, o), col: SIMCOL[j], a: 0.8, w: 1.8 }));
    const stars = [0, 1, 2].map((j) => ({ p: ppos(name, s, j, o), col: SIMCOL[j], r: 0.04, glow: 0.8, glowRef: R * 4.2 + 0.4 }));
    const proj = K.draw3d({ t, cam, stars, trails, dust: { a: 0.5 } });
    const a = fade(t, T('E05') - 0.2, T('E06') + 0.1, 0.3, 0.3);
    const back = s >= Tp ? fade(t, T('E05') + 0.2 + 4.6, T('E06') + 0.1, 0.15, 0.3) : 0;
    for (let j = 0; j < 3; j++) {
      const p = proj(ppos(name, 0, j, o));
      ctx.save(); ctx.globalAlpha *= a * (0.5 + 0.5 * back); ctx.strokeStyle = SIMCOL[j]; ctx.setLineDash([5, 5]); ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(p[0], p[1], 20 + 8 * back, 0, 7); ctx.stroke(); ctx.restore();
    }
    g.text('出发的位置', proj(ppos(name, 0, 0, o))[0], proj(ppos(name, 0, 0, o))[1] + 52, { size: 24, color: COL.grey, a: a * (1 - back), weight: '400' });
    g.text('转着转着……', W / 2, 140, { size: 40, color: '#fff', a: a * prog(t, at('E05', '转着'), at('E05', '转着') + 0.4) * (1 - back), shadow: 12 });
    g.text('回到原样', W / 2, 140, { size: 44, color: '#fff', a: a * back, shadow: 12 });
    const pa = a * prog(t, at('E05', '周期解') - 0.1, at('E05', '周期解') + 0.4);
    g.text('周期解', W / 2, H - 230, { size: 72, font: F.serif, weight: '700', color: COL.gold, a: pa, shadow: 16 });
  }

  // ---------- 8 字形：长镜头 ----------
  function figure8(lt, t) {
    const name = 'figure8', Tp = PER[name].T;
    const s = (t - T('E06')) * 0.85;
    const o = { k: 1.4 };
    const elev = lerp(0.42, 1.05, smooth(prog(t, T('E06'), T('E08')))), yaw = 0.5 + 0.035 * lt;
    const cam = orbitCam([0, 0, 0], 4.6 - 0.6 * smooth(prog(lt, 0, 10)), elev, yaw, { fov: 34 });
    const full = ptrail(name, 0, 0, Tp, 700, o);
    const ea = prog(t, at('E06', '八字') - 0.2, at('E06', '八字') + 0.6);
    const trails = [0, 1, 2].map((j) => ({ pts: ptrail(name, s, j, Tp * 0.42, 300, o), col: SIMCOL[j], a: 0.9, w: 2.2 }));
    const stars = [0, 1, 2].map((j) => ({ p: ppos(name, s, j, o), col: SIMCOL[j], r: 0.045, glow: 0.8, glowRef: 4 }));
    const proj = K.draw3d({ t, cam, stars, trails, thins: [{ pts: full, col: '#ffffff', a: 0.12 + 0.25 * ea }], dust: { a: 0.7 } });
    const a1 = fade(t, T('E06'), TE('E06') + 0.3, 0.4, 0.4);
    K.nameCard('克里斯·摩尔', '1993 年 · 电脑上找到', '美国物理学家', 130, 210, { a: a1 * prog(t, at('E06', '克里斯') - 0.3, at('E06', '克里斯') + 0.2), p: prog(t, at('E06', '克里斯') - 0.3, at('E06', '克里斯') + 0.8) });
    const ma = a1 * prog(t, at('E06', '一样重') - 0.2, at('E06', '一样重') + 0.3);
    if (ma > 0) for (let j = 0; j < 3; j++) { const p = proj(ppos(name, s, j, o)); g.text('1', p[0] + 26, p[1] - 26, { size: 24, font: F.mono, color: SIMCOL[j], a: ma, weight: '400' }); }
    g.text('三颗星一样重', W - 140, 150, { size: 36, color: '#fff', a: ma, align: 'right', shadow: 10 });
    g.text('沿同一个 8 字追着跑', W - 140, 205, { size: 36, color: '#fff', a: a1 * ea, align: 'right', shadow: 10 });
    g.text('永远不散', W - 140, 268, { size: 48, color: COL.gold, a: a1 * prog(t, at('E06', '永远不散') - 0.1, at('E06', '永远不散') + 0.4), align: 'right', weight: '700', shadow: 12 });
    const a2 = fade(t, T('E07') - 0.2, T('E08') + 0.1, 0.4, 0.3);
    year('2000', 300, 260, a2, 120);
    g.text('两位数学家证明：', 300, 360, { size: 36, color: '#fff', a: a2 * prog(t, at('E07', '两位'), at('E07', '两位') + 0.4), shadow: 10 });
    g.text('这条轨道确实存在', 300, 415, { size: 42, color: COL.gold, a: a2 * prog(t, at('E07', '确实'), at('E07', '确实') + 0.4), weight: '700', shadow: 10 });
    g.text('Chenciner & Montgomery', 300, 470, { size: 26, font: F.latin, color: COL.grey, a: a2 * prog(t, at('E07', '两位'), at('E07', '两位') + 0.4), weight: '400' });
  }

  // ---------- 2013：四格画廊 ----------
  const GAL = [['butterfly', '蝴蝶', 'Butterfly I', '蝴蝶', 1.0], ['moth', '飞蛾', 'Moth I', '飞蛾', 1.6], ['bumblebee', '大黄蜂', 'Bumblebee', '大黄蜂', 5.0], ['yinyang', '阴阳', 'Yin-Yang I', '阴阳', 2.2]];
  const GALPATH = {};
  for (const [name] of GAL) GALPATH[name] = [0, 1, 2].map((j) => ptrail(name, PER[name].T, j, PER[name].T, 2000));
  function gallery(lt, t) {
    K.bg(t, { sky: 0.5 });
    const ia = fade(t, T('E08') - 0.2, at('E08', '蝴蝶') + 0.2, 0.3, 0.5);
    year('2013', W / 2, H / 2 - 120, ia);
    g.text('两位塞尔维亚物理学家', W / 2, H / 2 + 10, { size: 40, color: '#fff', a: ia * prog(t, at('E08', '两位'), at('E08', '两位') + 0.4), shadow: 10 });
    g.text('一下子找到 13 种新轨道', W / 2, H / 2 + 80, { size: 48, color: COL.gold, a: ia * prog(t, at('E08', '十三种'), at('E08', '十三种') + 0.4), weight: '700', shadow: 10 });
    g.text('Šuvakov & Dmitrašinović', W / 2, H / 2 + 145, { size: 26, font: F.latin, color: COL.grey, a: ia * prog(t, at('E08', '两位'), at('E08', '两位') + 0.4), weight: '400' });
    const pw = W / 2, phh = H / 2;
    GAL.forEach(([name, cn, en, w, rate], i) => {
      const t0 = at('E08', w) - 0.15, pa = fade(t, t0, T('E09') + 0.1, 0.35, 0.3);
      if (pa <= 0) return;
      const x = (i % 2) * pw, y = Math.floor(i / 2) * phh, R = BOX[name];
      const s = (t - t0) * rate + PER[name].T * 0.13 * i;
      const cam = orbitCam([0, 0, 0], R * 3.3 + 0.3, 1.45, 0.0, { fov: 32 });
      const trails = [0, 1, 2].map((j) => ({ pts: ptrail(name, s, j, rate * 2.2, 300), col: SIMCOL[j], a: 0.85, w: 1.8 }));
      const stars = [0, 1, 2].map((j) => ({ p: ppos(name, s, j), col: SIMCOL[j], r: 0.035, glow: 0.8, glowRef: R * 3.3 + 0.3 }));
      const thins = GALPATH[name].map((pts, j) => ({ pts, col: SIMCOL[j], a: 0.16 }));
      ctx.save(); ctx.globalAlpha *= pa;
      draw3dAt({ t, cam, stars, trails, thins, dust: null, sky: 0.4, size: [pw, phh], vig: 0.5 }, x, y);
      ctx.restore();
      g.rect(x + 1, y + 1, pw - 2, phh - 2, { color: COL.hud, lw: 1, a: pa * 0.45 });
      g.text(cn, x + 40, y + 58, { size: 44, font: F.serif, weight: '700', color: '#f4efe4', a: pa, align: 'left', shadow: 10 });
      g.text(en, x + 40, y + 108, { size: 24, font: F.latin, color: COL.grey, a: pa, align: 'left', weight: '400' });
    });
  }

  // ---------- 廖世俊团队 + 天河二号 + 计数器 + 轨道光雾 ----------
  const HAZE = (() => {
    const r = rng(11), names = Object.keys(PER), out = [];
    for (let i = 0; i < 110; i++) {
      const name = names[i % names.length], j = Math.floor(r() * 3), n = Math.min(1500, PER[name].pts.length);
      const o = { k: (0.55 + r() * 0.9) / BOX[name], rot: r() * 6.2832, ox: (r() - 0.5) * 4.2, oz: (r() - 0.5) * 2.6 };
      out.push({ name, j, n, o, tilt: (r() - 0.5) * 2.4, col: [TINT.red, TINT.blue, TINT.yellow, '#ffffff', '#bfe3ff'][Math.floor(r() * 5)] });
    }
    return out;
  })();
  const hazePts = (h, tilt) => ptrail(h.name, PER[h.name].T, h.j, PER[h.name].T, h.n, { ...h.o, tilt: Math.PI / 2 - h.tilt * tilt });
  const HZ0 = HAZE.map((h) => hazePts(h, 0));
  const HZ1 = HAZE.map((h) => hazePts(h, 1));
  async function liao(lt, t) {
    const t17 = at('E09', '二零一七年'), t21 = at('E09', '二零二一年'), t25 = at('E09', '二零二五年');
    const nOn = Math.floor(lerp(0, 18, prog(t, t17 - 0.3, t17 + 1.5)) + lerp(0, 70, prog(t, t21, t21 + 2.5)) + lerp(0, 22, prog(t, t25, t25 + 1.5)));
    const tl = smooth(prog(t, t25, t25 + 2.5));
    const thins = [];
    for (let i = 0; i < Math.min(nOn, HAZE.length); i++) thins.push({ pts: tl > 0 ? HZ1[i] : HZ0[i], col: HAZE[i].col, a: 0.14 + 0.1 * (i === nOn - 1) });
    const cam = orbitCam([0, 0, 0], 6.8 - 0.8 * smooth(prog(t, t17, TE('E09'))), lerp(1.2, 0.55, tl), 0.2 + 0.025 * lt);
    K.draw3d({ t, cam, thins, dust: { a: 0.5 }, sky: 0.7, bloom: 1.1 });
    const nc = fade(t, at('E09', '上海') - 0.2, at('E09', '天河') + 0.1, 0.3, 0.3);
    K.nameCard('廖世俊 团队', '上海交通大学', '', W / 2 - 260, H / 2 - 20, { a: nc, p: prog(t, at('E09', '上海') - 0.2, at('E09', '上海') + 0.8) });
    // 天河二号
    const c0 = at('E09', '天河') - 0.1, ca = fade(t, c0, c0 + 3.5, 0.2, 0.3);
    if (ca > 0) {
      const im = await clip('T2', t - c0);
      const w = 1280, h = 720, x = (W - w) / 2, y = (H - h) / 2 - 40;
      ctx.save(); ctx.globalAlpha *= ca;
      g.cover(im, { box: [x, y, w, h], s: 1 + (t - c0) * 0.01 });
      ctx.restore();
      g.rect(x, y, w, h, { color: COL.hud, lw: 1, a: ca * 0.8 });
      g.brackets(x - 10, y - 10, w + 20, h + 20, { p: prog(t, c0, c0 + 0.5), color: COL.hud, len: 26, a: ca });
      g.text('天河二号超级计算机', x, y + h + 34, { size: 26, color: COL.white, align: 'left', a: ca });
      g.text('画面来源：抖音', x + w, y + h + 34, { size: 20, color: COL.grey, align: 'right', weight: '400', a: ca });
    }
    // 计数表
    const ta = fade(t, Math.max(c0 + 3.3, t17 - 0.3), M('pre_ch6') + 1.0, 0.3, 0.6);
    const rows = [[t17, '2017', 695, '族', '三颗星一样重'], [t21, '2021', 135445, '个', '三颗星不一样重'], [t25, '2025', 10059, '个', '立体的']];
    rows.forEach(([t0, y0, n, unit, note], i) => {
      const ra = ta * prog(t, t0 - 0.1, t0 + 0.3);
      if (ra <= 0) return;
      const yy = 330 + i * 150, v = n * easeOut(prog(t, t0, t0 + 1.6));
      g.text(y0, W / 2 - 420, yy, { size: 56, font: F.num, color: COL.gold, a: ra, align: 'left', weight: '600' });
      const nw = g.text(fmt(v), W / 2 + 180, yy, { size: 96, font: F.num, color: '#ffffff', a: ra, align: 'right', weight: '600', shadow: 16 });
      g.text(unit, W / 2 + 200, yy + 10, { size: 40, color: '#fff', a: ra, align: 'left' });
      g.text(note, W / 2 + 270, yy + 10, { size: 32, color: COL.hud, a: ra, align: 'left', weight: '400' });
    });
    g.text('找到的周期解', W / 2 - 420, 230, { size: 30, color: COL.grey, a: ta, align: 'left', weight: '400' });
  }

  // ---------- 半人马座α：真实照片 ----------
  async function alphaPhoto(lt, t) {
    const pa = prog(t, at('F02', '三颗恒星') - 0.6, at('F02', '三颗恒星'));
    // 先是一颗亮星
    if (pa < 1) {
      const d = 46 - 10 * smooth(prog(lt, 0, 6));
      const cam = { pos: [0, 0, d], look: [0, 0, 0], fov: 30 };
      const proj = K.draw3d({ t, cam, stars: [{ p: [0, 0, 0], col: '#fff2dc', r: 0.04, glow: 1.6, glowRef: 40 }], sky: 1.0, dust: null });
      const p = proj([0, 0, 0]), ta = prog(t, at('F02', '半人马座') - 0.2, at('F02', '半人马座') + 0.4) * (1 - pa);
      g.tag(p[0], p[1], '半人马座α', { p: ta, r: 40, dx: 120, dy: -90, sub: '4.37 光年 · 离太阳最近的恒星' });
    }
    if (pa > 0) {
      const im = await ph('potw1635a_hi.jpg');
      const s = 1.04 + 0.006 * (t - at('F02', '三颗恒星'));
      ctx.save(); ctx.globalAlpha *= pa; g.cover(im, { s }); ctx.restore();
      const k = Math.max(W / im.width, H / im.height) * s, w = im.width * k, h = im.height * k, ox = (W - w) / 2, oy = (H - h) / 2;
      const P = (fx, fy) => [ox + fx * w, oy + fy * h];
      const la = pa * prog(t, at('F02', '三颗恒星') + 0.2, at('F02', '三颗恒星') + 0.8);
      const [ax, ay] = P(0.281, 0.474), [bx, by] = P(0.664, 0.49);
      g.tag(ax, ay, 'A', { p: la, r: 60, dx: -110, dy: -170, size: 44 });
      g.tag(bx, by, 'B', { p: la, r: 60, dx: 110, dy: -170, size: 44 });
      g.text('图片：ESA/Hubble & NASA', W - 40, H - 30, { size: 20, color: COL.grey, a: pa, align: 'right', weight: '400' });
      const ca = pa * prog(t, at('F02', '三颗恒星') + 0.5, at('F02', '三颗恒星') + 1.1);
      if (ca > 0) g.photo(await ph('potw1343a_hi.jpg'), 1620, 760, 260, { a: ca, name: '比邻星', years: '第三颗', rot: 0.02, filter: 'none', credit: 'ESA/Hubble & NASA' });
      const da = pa * prog(t, at('F02', '排法') - 0.1, at('F02', '排法') + 0.4);
      g.text('排法跟小说很不一样', W / 2, 120, { size: 44, color: '#fff', a: da, shadow: 14 });
    }
  }

  // ---------- 半人马座α 系统：AB 双星 → 一镜到底拉远到比邻星 ----------
  const U = 10;                                        // 1 场景单位 = 10 天文单位
  const AB = { a: 23.5 / U, e: 0.52, mA: 1.08, mB: 0.91, P: 80 };
  const PROX = [1300 * Math.cos(0.5), 0, -1300 * Math.sin(0.5)];
  const ABPATH = (() => { const n = 400, a = new Float32Array(n * 3), b = new Float32Array(n * 3), M2 = AB.mA + AB.mB; for (let i = 0; i < n; i++) { const r = ellipse(AB.a, AB.e, i / (n - 1)); a.set(r.map((v) => (-v * AB.mB) / M2), 3 * i); b.set(r.map((v) => (v * AB.mA) / M2), 3 * i); } return [a, b]; })();
  const PXPATH = (() => { const n = 800, a = new Float32Array(n * 3); for (let i = 0; i < n; i++) a.set(ellipse(870, 0.5, i / (n - 1), 0.5 + Math.PI), 3 * i); return a; })();
  const pullP = (t) => smooth(prog(t, T('F04') - 0.2, at('F04', '一万三千') + 0.8));
  function alphaSys(lt, t) {
    const ph0 = (t - T('F03')) / 6, rel = ellipse(AB.a, AB.e, ph0), M2 = AB.mA + AB.mB;
    const pA = rel.map((v) => (-v * AB.mB) / M2), pB = rel.map((v) => (v * AB.mA) / M2);
    const pp = pullP(t);
    const dist = 9 * Math.pow(2700 / 9, pp);
    const look = PROX.map((v) => v * 0.5 * smooth(prog(pp, 0.35, 1)));
    const cam = orbitCam(look, dist, lerp(0.95, 1.2, pp), 0.45 + 0.012 * lt, { near: Math.max(0.002, dist * 0.002), far: Math.max(9000, dist * 4) });
    const proj = K.draw3d({
      t, cam,
      stars: [{ p: pA, col: '#fff1d6', r: 0.12, glow: 0.55, glowRef: 6 }, { p: pB, col: '#ffc98a', r: 0.1, glow: 0.5, glowRef: 6 }, { p: PROX, col: '#ff5a3a', r: 0.05, glow: 0.7 * prog(pp, 0.4, 0.7), glowRef: 6 }],
      thins: [{ pts: ABPATH[0], col: '#fff1d6', a: 0.3 * (1 - prog(pp, 0, 0.4)) }, { pts: ABPATH[1], col: '#ffc98a', a: 0.3 * (1 - prog(pp, 0, 0.4)) }, { pts: PXPATH, col: '#ff8a6a', a: 0.22 * prog(pp, 0.55, 0.9) }],
      dust: { a: 0.35 * (1 - pp), scale: 1 }, sky: 0.9, bloom: 0.9,
    });
    const SA = proj(pA), SB = proj(pB), SP = proj(PROX), S0 = proj([0, 0, 0]);
    // AB 间距
    const a1 = fade(t, T('F03'), T('F04') + 0.3, 0.4, 0.4);
    g.tag(SA[0], SA[1], 'A', { p: a1 * prog(t, T('F03'), T('F03') + 0.6), r: 34, dx: -80, dy: -80, size: 36 });
    g.tag(SB[0], SB[1], 'B', { p: a1 * prog(t, T('F03') + 0.2, T('F03') + 0.8), r: 30, dx: 80, dy: -80, size: 36 });
    const da = a1 * prog(t, at('F03', '二十三点五') - 0.2, at('F03', '二十三点五') + 0.3);
    if (da > 0) {
      g.line(SA[0], SA[1], SB[0], SB[1], { color: COL.hud, w: 1.4, a: da, dash: [6, 6] });
      g.text('平均相距 ≈ 23.5 天文单位', W / 2, H - 230, { size: 40, color: '#fff', a: da, shadow: 12 });
    }
    g.text('= 日地距离 × 23 多', W / 2, H - 176, { size: 32, color: COL.hud, a: a1 * prog(t, at('F03', '日地距离') - 0.1, at('F03', '日地距离') + 0.3), shadow: 10 });
    const ya = a1 * prog(t, at('F03', '八十年') - 0.2, at('F03', '八十年') + 0.3);
    g.text(`第 ${Math.floor(Math.max(0, ph0) * AB.P)} 年`, W - 140, 140, { size: 44, font: F.mono, color: COL.hud, a: a1, align: 'right', weight: '400' });
    g.text('≈ 80 年互相绕一圈', W - 140, 200, { size: 34, color: COL.gold, a: ya, align: 'right' });
    // 比例尺
    const sa = fade(t, T('F04') + 0.2, T('F06') + 0.1, 0.4, 0.3);
    if (sa > 0) {
      const upp = (2 * dist * Math.tan((32 / 2) * Math.PI / 180)) / H * U;
      let v = 240 * upp; const e10 = Math.pow(10, Math.floor(Math.log10(v))), m = v / e10; v = (m < 2 ? 1 : m < 5 ? 2 : 5) * e10;
      const L = v / upp;
      g.line(120, H - 200, 120 + L, H - 200, { color: '#fff', w: 2, a: sa });
      g.line(120, H - 212, 120, H - 188, { color: '#fff', w: 2, a: sa }); g.line(120 + L, H - 212, 120 + L, H - 188, { color: '#fff', w: 2, a: sa });
      g.text(`${fmt(v)} 天文单位`, 120, H - 236, { size: 28, font: F.mono, color: '#fff', a: sa, align: 'left', weight: '400' });
      const dv = Math.exp(lerp(Math.log(23.5), Math.log(13000), smooth(prog(pp, 0.15, 1))));
      g.text('离 A、B', W - 140, 140, { size: 28, color: COL.grey, a: sa, align: 'right', weight: '400' });
      g.text(`${fmt(dv)} 天文单位`, W - 140, 200, { size: 56, font: F.num, color: '#fff', a: sa, align: 'right', weight: '600' });
    }
    const pa = fade(t, at('F04', '比邻星') - 0.2, T('F06') + 0.1, 0.3, 0.3) * prog(pp, 0.45, 0.75);
    if (pa > 0 && SP[2] < 1) {
      g.tag(SP[0], SP[1], '比邻星', { p: pa, r: 34, dx: -110, dy: -90, size: 38, color: '#ffb39a', sub: prog(t, at('F04', '红矮星'), at('F04', '红矮星') + 0.3) > 0.5 ? '红矮星' : null });
      g.line(S0[0], S0[1], SP[0], SP[1], { color: '#ffb39a', w: 1, a: pa * 0.5, dash: [4, 8] });
    }
    g.text('绕一圈 ≈ 55 万年', W - 140, 262, { size: 34, color: COL.gold, a: pa * prog(t, at('F04', '五十五万年') - 0.1, at('F04', '五十五万年') + 0.3), align: 'right' });
    g.text('示意：比邻星轨道', W - 40, H - 30, { size: 20, color: COL.grey, a: pa, align: 'right', weight: '400' });
    // 层级结构
    const ha = fade(t, T('F05') - 0.1, T('F06') + 0.1, 0.3, 0.3);
    if (ha > 0) {
      g.text('层级结构', W / 2, 130, { size: 56, font: F.serif, weight: '700', color: '#f4efe4', a: ha * prog(t, at('F05', '层级结构'), at('F05', '层级结构') + 0.4), shadow: 14 });
      const p1 = ha * prog(t, at('F05', '两颗凑成一对') - 0.1, at('F05', '两颗凑成一对') + 0.3);
      g.brackets(S0[0] - 50, S0[1] - 50, 100, 100, { p: p1, color: '#fff1d6', a: p1, len: 22 });
      g.text('一对：A + B', S0[0], S0[1] + 86, { size: 32, color: '#fff1d6', a: p1, shadow: 10 });
      const p2 = ha * prog(t, at('F05', '第三颗') - 0.1, at('F05', '第三颗') + 0.3);
      g.text('第三颗：远远地绕着这一对', SP[0], SP[1] + 120, { size: 32, color: '#ffb39a', a: p2, shadow: 10 });
    }
  }
  async function w12(lt, t) {
    await wan('W12', { zoom: 0.006 })(lt);
    g.text('艺术想象', W - 40, 44, { size: 22, color: COL.grey, align: 'right', weight: '400' });
    const a = fade(t, at('F06', '两个二体') - 0.2, T('F07') + 0.1, 0.3, 0.3);
    g.text('≈ 两个二体问题', 120, 150, { size: 46, color: '#fff', a, align: 'left', shadow: 16 });
    g.text('整体很稳定 · 没有乱纪元', 120, 215, { size: 34, color: COL.gold, a: a * prog(t, at('F06', '整体') - 0.1, at('F06', '整体') + 0.3), align: 'left', shadow: 14 });
  }
  function liuNote(lt, t) {
    K.bg(t, { sky: 0.55 });
    const a = fade(t, T('F07') - 0.2, T('F08') + 0.1, 0.3, 0.3);
    g.text('顺便说一句', W / 2, H / 2 - 170, { size: 30, color: COL.grey, a, weight: '400' });
    K.quote(['“三体人在半人马座”'], null, W / 2, H / 2 - 60, { a: a * prog(t, at('F07', '三体人') - 0.2, at('F07', '三体人') + 0.3), size: 64 });
    g.text('刘慈欣：这一点是编辑后来加上的', W / 2, H / 2 + 60, { size: 40, color: '#fff', a: a * prog(t, at('F07', '编辑') - 0.3, at('F07', '编辑') + 0.3), shadow: 10 });
    g.text('出处：中国作家网，2017 年 6 月 23 日', W / 2, H / 2 + 130, { size: 24, color: COL.grey, a: a * prog(t, at('F07', '编辑'), at('F07', '编辑') + 0.4), weight: '400' });
  }

  // ---------- 太阳系 + 拉斯卡尔 ----------
  const SOL = [[0.45, 1.6, 'rock', 0.03], [0.7, 1.2, 'rock', 0.04], [0.95, 1.0, 'earth', 0.042], [1.22, 0.8, 'rock', 0.034], [1.85, 0.42, 'jupiter', 0.1], [2.45, 0.3, 'jupiter', 0.085], [3.0, 0.22, 'moon', 0.06], [3.45, 0.17, 'moon', 0.058]];
  const SOLRING = SOL.map(([r]) => ring(r));
  function solar(lt, t) {
    const pos = SOL.map(([r, w], i) => { const u = 1.7 * i + w * 0.6 * (t - 677); return [r * Math.cos(u), 0, -r * Math.sin(u)]; });
    const cam = orbitCam([0, 0, 0], 8.2 - 0.8 * smooth(prog(lt, 0, 12)), 0.75, 0.2 + 0.02 * lt);
    const proj = K.draw3d({ t, cam, stars: [{ p: [0, 0, 0], col: SUN, r: 0.07, glow: 0.25, glowRef: 8 }], planets: pos.map((p, i) => ({ type: SOL[i][2], p, r: SOL[i][3], light: [0, 0, 0] })), thins: SOLRING.map((pts) => ({ pts, col: '#8aa0c0', a: 0.24 })), dust: { a: 0.2 } });
    const S = [[0, 0, 0], ...pos].map(proj);
    const la = fade(t, at('F09', '不止') - 0.2, T('F10') + 0.3, 0.4, 0.5);
    for (let i = 0; i < S.length; i++) for (let j = i + 1; j < S.length; j++) g.line(S[i][0], S[i][1], S[j][0], S[j][1], { color: COL.hud, w: 1.2, a: la * 0.32 });
    g.text('太阳 + 8 颗行星 + 无数小天体', W / 2, 140, { size: 40, color: COL.hud, a: la });
    g.text('比三体还难', W / 2, 205, { size: 44, color: '#fff', a: la * prog(t, at('F09', '比三体') - 0.1, at('F09', '比三体') + 0.3), weight: '700', shadow: 12 });
    const ka = fade(t, T('F10') - 0.1, T('F11') + 0.1, 0.4, 0.3);
    if (ka > 0) {
      dim(ka * 0.35);
      K.nameCard('雅克·拉斯卡尔', '1989', '法国天文学家', 130, 230, { a: ka, p: prog(t, at('F10', '拉斯卡尔') - 0.3, at('F10', '拉斯卡尔') + 0.7) });
      g.text('太阳系也是混沌的', W / 2, H - 260, { size: 54, font: F.serif, weight: '700', color: '#f4efe4', a: ka * prog(t, at('F10', '混沌') - 0.2, at('F10', '混沌') + 0.3), shadow: 14 });
      g.text('只不过乱得很慢', W / 2, H - 190, { size: 36, color: COL.gold, a: ka * prog(t, at('F10', '乱得很慢') - 0.1, at('F10', '乱得很慢') + 0.3), shadow: 12 });
    }
  }

  // ---------- 两个地球：差 15 米，一亿年后差一个日地距离 ----------
  const yrOf = (t) => 1e8 * prog(t, at('F11', '算到') - 0.2, at('F11', '一点五亿公里') + 0.3);
  const errKm = (y) => 0.015 * Math.pow(10, (10 * y) / 1e8);
  const kmStr = (d) => (d < 1 ? `${Math.round(d * 1000)} 米` : d < 1e4 ? `${fmt(d)} 公里` : d < 1e8 ? `${(d / 1e4).toFixed(d < 1e5 ? 1 : 0)} 万公里` : `${(d / 1e8).toFixed(1)} 亿公里`);
  const yrStr = (y) => (y < 1e4 ? `${fmt(y)} 年` : y < 1e8 ? `${fmt(y / 1e4)} 万年` : `1 亿年`);
  const cmpOf = (d) => (d < 0.2 ? '差不多一栋楼高' : d < 60 ? '一座城市那么大' : d < 2e4 ? '地球直径 1.27 万公里' : d < 1e6 ? '地月距离 38 万公里' : d < 1.2e8 ? '' : '日地距离');
  const EORB = ring(1, 600);
  const SMEAR = (() => { const r = rng(5), n = 3000, p = new Float32Array(n * 3); for (let i = 0; i < n; i++) { const u = r() * 6.2832, rr = 1 + (r() - 0.5) * 0.03; p.set([rr * Math.cos(u), (r() - 0.5) * 0.01, -rr * Math.sin(u)], 3 * i); } return p; })();
  function twoEarths(lt, t) {
    const y = yrOf(t), d = errKm(y), del = d / 1.496e8;
    const phi = 0.9 + 0.02 * lt;
    const e1 = [Math.cos(phi), 0, -Math.sin(phi)], e2 = [Math.cos(phi + del), 0, -Math.sin(phi + del)];
    const sm = prog(t, T('F12') - 0.2, at('F12', '算不准'));
    const cam = orbitCam([0.25, 0, -0.35], 3.6, 1.0, 0.3 + 0.015 * lt);
    const proj = K.draw3d({
      t, cam,
      stars: [{ p: [0, 0, 0], col: SUN, r: 0.05, glow: 0.22, glowRef: 4 }],
      planets: [{ type: 'earth', p: e1, r: 0.05, light: [0, 0, 0], a: 1 - sm }, { type: 'earth', p: e2, r: 0.05, light: [0, 0, 0], a: 0.55 * (1 - sm), tint: '#cfe0ff' }],
      thins: [{ pts: EORB, col: '#8fc4ff', a: 0.35 }],
      cloud: sm > 0 ? { pos: SMEAR, n: Math.floor(3000 * sm), col: '#8fc4ff', size: 3, a: 0.8 * sm } : null,
      dust: { a: 0.3 },
    });
    const a = fade(t, T('F11') - 0.2, TE('F12') + 0.4, 0.4, 0.5);
    const ra = a * (1 - prog(t, T('F12') - 0.3, T('F12') + 0.2));
    g.text('时间', 130, 150, { size: 28, color: COL.grey, a: ra, align: 'left', weight: '400' });
    g.text(yrStr(y), 130, 205, { size: 56, font: F.num, color: '#fff', a: ra, align: 'left', weight: '600' });
    g.text('两个地球相差', 130, 285, { size: 28, color: COL.grey, a: ra, align: 'left', weight: '400' });
    g.text(kmStr(d), 130, 340, { size: 56, font: F.num, color: d > 1e8 ? COL.red : COL.gold, a: ra, align: 'left', weight: '600' });
    g.text(cmpOf(d), 130, 395, { size: 28, color: COL.hud, a: ra, align: 'left', weight: '400' });
    // 放大镜：两个地球离得太近时，在圈里放大看
    const ma = ra * (1 - prog(del, 0.05, 0.15)) * prog(t, T('F11') + 0.2, T('F11') + 0.8);
    const P1 = proj(e1), P2 = proj(e2);
    if (ra > 0) {
      ctx.save(); ctx.globalAlpha *= ra; ctx.lineWidth = 2;
      ctx.strokeStyle = '#6fa8ff'; ctx.beginPath(); ctx.arc(P1[0], P1[1], 26, 0, 7); ctx.stroke();
      ctx.strokeStyle = 'rgba(255,255,255,0.85)'; ctx.setLineDash([5, 4]); ctx.beginPath(); ctx.arc(P2[0], P2[1], 26, 0, 7); ctx.stroke();
      ctx.restore();
    }
    if (ma > 0) {
      const cx = 1480, cy = 400, r = 190;
      g.line(P1[0], P1[1], cx - r * 0.8, cy + r * 0.6, { color: COL.hud, w: 1, a: ma * 0.6 });
      ctx.save(); ctx.globalAlpha *= ma;
      ctx.fillStyle = 'rgba(4,8,16,0.85)'; ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.fill();
      ctx.strokeStyle = COL.hud; ctx.lineWidth = 1.5; ctx.stroke();
      ctx.fillStyle = '#4f8fe0'; ctx.beginPath(); ctx.arc(cx - 70, cy, 34, 0, 7); ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.9)'; ctx.setLineDash([5, 4]); ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(cx + 70, cy, 34, 0, 7); ctx.stroke();
      ctx.restore();
      g.line(cx - 70, cy + 60, cx + 70, cy + 60, { color: '#fff', w: 1.5, a: ma });
      g.text(kmStr(d), cx, cy + 92, { size: 30, font: F.mono, color: '#fff', a: ma, weight: '400' });
      g.text('放大看', cx, cy - r - 26, { size: 24, color: COL.grey, a: ma, weight: '400' });
    }
    const la = ra * prog(del, 0.3, 0.6);
    if (la > 0) {
      g.line(P1[0], P1[1], P2[0], P2[1], { color: COL.red, w: 2, a: la, dash: [6, 6] });
      g.text('≈ 地球到太阳的距离', (P1[0] + P2[0]) / 2 + 30, (P1[1] + P2[1]) / 2 - 40, { size: 32, color: '#fff', a: la * prog(t, at('F11', '地球到太阳') - 0.2, at('F11', '地球到太阳') + 0.3), align: 'left', shadow: 12 });
    }
    const qa = a * sm;
    g.text('几千万年以后，地球在轨道上的哪个位置？', W / 2, 140, { size: 42, color: '#fff', a: qa, shadow: 12 });
    g.text('谁也算不准', W / 2, 205, { size: 48, color: COL.gold, a: a * prog(t, at('F12', '算不准') - 0.2, at('F12', '算不准') + 0.3), weight: '700', shadow: 12 });
  }

  // ---------- 结尾：回到三体星球，三颗太阳沉下去 ----------
  async function ending(lt, t) {
    await wan('W13', { s0: 1.0, zoom: 0.004 })(lt);
    const a = fade(t, M('ending') + 0.2, M('ending_end') + 0.2, 0.8, 0.8);
    g.text('三体问题为什么无解', W / 2, H / 2 + 230, { size: 64, font: F.serif, weight: '700', color: '#f4efe4', a, spacing: 8, shadow: 24 });
    g.text('用数字讲商业与时代', W / 2, H / 2 + 310, { size: 28, color: COL.grey, a: a * prog(t, M('ending') + 1.2, M('ending') + 2), spacing: 6, weight: '400' });
  }
  function credits(lt, t) {
    K.bg(t, { sky: 0.4, exposure: 0.7 });
    const a = prog(lt, 0.2, 0.8);
    const col = (x, title, lines, d) => {
      const ca = a * prog(lt, d, d + 0.5);
      g.text(title, x, 220, { size: 36, color: COL.gold, a: ca, align: 'left' });
      lines.forEach((s, i) => g.text(s, x, 290 + i * 52, { size: 28, color: '#d8dde6', a: ca, align: 'left', weight: '400' }));
    };
    col(140, '资料来源', ['Mittag-Leffler 研究所：奥斯卡国王奖', 'Barrow-Green：Poincaré and the Three Body Problem', 'Diacu 1996 · Wang 1991', 'Moore 1993 · Chenciner & Montgomery 2000', 'Šuvakov & Dmitrašinović 2013', '廖世俊团队 2017 / 2021 / 2025', 'Kervella et al. 2017 · Laskar 1989'], 0.3);
    col(1000, '画面来源', ['历史人物画像：Wikimedia Commons（公有领域）', '半人马座α、比邻星：ESA/Hubble & NASA', '刘慈欣：阳泉日报', '天河二号：抖音', '星体运动：按真实物理方程计算'], 0.6);
    const da = a * prog(lt, 1.0, 1.5);
    g.line(140, H - 250, W - 140, H - 250, { color: COL.hud, w: 1, a: da * 0.4 });
    g.text('部分画面由 AI 生成（通义万相），已在画面中标注；配音为 AI 合成', W / 2, H - 200, { size: 26, color: '#fff', a: da, weight: '400' });
    g.text('完整参考资料见简介', W / 2, H - 150, { size: 24, color: COL.grey, a: da, weight: '400' });
  }

  return [
    { a: M('ch5_end') - 0.2, b: T('E05') + 0.1, fi: 0.4, fo: 0.3, draw: steps },
    { a: T('E05') - 0.2, b: T('E06') + 0.1, fi: 0.3, fo: 0.3, draw: periodic },
    { a: T('E06') - 0.2, b: T('E08') + 0.1, fi: 0.3, fo: 0.3, draw: figure8 },
    { a: T('E08') - 0.2, b: T('E09') + 0.1, fi: 0.3, fo: 0.3, draw: gallery },
    { a: T('E09') - 0.2, b: M('pre_ch6') + 1.0, fi: 0.3, fo: 0.6, draw: liao },
    { a: M('ch6_end') - 0.2, b: T('F03') + 0.1, fi: 0.4, fo: 0.3, draw: alphaPhoto },
    { a: T('F03') - 0.2, b: T('F06') + 0.1, fi: 0.3, fo: 0.3, draw: alphaSys },
    { a: T('F06') - 0.2, b: T('F07') + 0.1, fi: 0.3, fo: 0.3, draw: w12 },
    { a: T('F07') - 0.2, b: T('F08') + 0.1, fi: 0.3, fo: 0.3, draw: liuNote },
    { a: T('F08') - 0.2, b: T('F11') + 0.1, fi: 0.3, fo: 0.3, draw: solar },
    { a: T('F11') - 0.2, b: T('F13') - 0.2, fi: 0.3, fo: 0.5, draw: twoEarths },
    { a: T('F13') - 0.6, b: M('ending_end'), fi: 0.6, fo: 0.6, draw: ending },
    { a: M('credits') - 0.3, b: FILM.duration + 0.2, fi: 0.4, fo: 0.3, draw: credits, noSub: true },
  ];
}
