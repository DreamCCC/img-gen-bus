// 冷开场 0:00–2:29 + 标题卡
import { W, H, COL, F, TINT, SIMCOL, clamp, lerp, prog, smooth, easeOut, easeInOut, fade, keys, mono, at, T, TE, M, clip, img } from './lib.js';
import { OP, samp, wp, vel, trail, frameOf, pairCom, orbitCam, starsOf, trailsOf, ellipse } from './sim.js';

export function coldShots(env) {
  const { g, space, ctx } = env;
  const A = OP.A, B = OP.B;
  const NAME = ['红星', '蓝星', '黄星'];

  // ---------- 模拟时间映射（成片秒 → 模拟时间），全部挂在词上 ----------
  const tSpin = at('H04', '转起来') - 0.8;           // 开始转
  const tBreak = at('H06', '散了') + 0.1;            // 队形散（s≈6.2）
  const tEject = at('H07', '甩了出去') + 0.25;        // 红星最后一次交会 s=42.13
  const sA = mono([
    [0, 0], [tSpin, 0], [tSpin + 1.2, 0.5], [tBreak, 6.2], [at('H06', '乱成一团'), 15],
    [at('H07', '红星') - 0.2, 33], [tEject - 0.9, 41.2], [tEject + 0.5, 42.6], [at('H07', '一路飞走', true), 46.5],
    [TE('H07'), 52], [TE('H08') + 0.4, 72],
  ]);
  const tRew0 = at('H09', '倒回开头') - 0.1, tRew1 = TE('H09') - 0.2;
  const sRew = (t) => (t < tRew0 ? sA(t) : t < tRew1 ? lerp(sA(tRew0), 0, easeInOut(prog(t, tRew0, tRew1))) : 0);

  const tGo = at('H14', '转一遍') + 0.2;
  const tSplit = tGo - 0.5;
  const sB = mono([
    [0, 0], [tGo, 0], [at('H15', '一模一样'), 8], [TE('H15') - 0.2, 23.5], [at('H16', '对不上了') + 0.3, 27.6],
    [at('H17', '红星') - 0.4, 37.0], [at('H17', '黄星') + 0.3, 40.2], [TE('H17') + 0.2, 43.5],
    [at('H18', '老远', true), 100.4], [at('H18', '拽了回来', true), 161.2], [at('H18', '又被甩了出去', true), 166],
    [at('H18', '真走了', true), 182], [T('H19') + 2.5, 196], [TE('H19') + 0.6, 206],
  ]);

  // ---------- 镜头参数 ----------
  // 开头俯视匹配 W01：黄星在上，红星左下，蓝星右下；三角形边长 350 像素，质心在 (989, 339)
  const t0 = 4.4;
  const elevK = keys([[t0, 1.562], [t0 + 1.0, 1.52], [t0 + 7.5, 0.6], [tSpin, 0.46], [40, 0.42], [T('H10'), 0.55], [at('H13', '一毫米'), 0.62], [tSplit, 0.5]]);
  const yawK = mono([[t0, -2.094], [t0 + 7.5, -1.25], [tSpin, -0.95], [tEject, -0.55], [40, -0.35], [T('H10') + 1, 0.05], [tSplit, 0.25], [90, 0.6]]);
  const offK = keys([[t0, 1], [t0 + 0.6, 1], [t0 + 4.5, 0]]);
  const OFF = [-0.456, 0, -0.359];
  const autoD = (R) => R * 4.4 + 0.6;
  const zoomK = keys([[t0, 5.38 / autoD(0.6)], [t0 + 0.6, 5.38 / autoD(0.6)], [t0 + 6, 1.15], [tSpin, 1.0]]);
  const pairW = keys([[TE('H07') - 0.6, 0], [T('H08') + 0.9, 1], [tRew0, 1], [tRew0 + 1.4, 0]]);
  const starR = keys([[t0, 0.165], [t0 + 0.7, 0.15], [t0 + 3.2, 0.04]]);
  const blueFocus = keys([[T('H10'), 0], [T('H10') + 1.6, 1], [at('H13', '一毫米', true) + 0.3, 1], [tSplit - 0.3, 0]]);

  // ---------- 通用：3D 一帧 + 投影 ----------
  const draw3d = (cfg, x = 0) => { const cv = space.draw(cfg); ctx.drawImage(cv, x, 0); return (p) => { const v = space.project(p); return [v[0] + x, v[1], v[2]]; }; };

  function arrowHead(x, y, ang, s, color, a = 1) {
    g.poly([[x - s * Math.cos(ang - 0.45), y - s * Math.sin(ang - 0.45)], [x, y], [x - s * Math.cos(ang + 0.45), y - s * Math.sin(ang + 0.45)]], { color, w: 2, a });
  }

  // ---------- 镜头 C01：单屏，A 次 ----------
  function singleA(lt, t) {
    const s = sRew(t);
    const q = samp(A, s);
    const ej = fade(t, tEject - 1.6, tEject + 0.9, 0.6, 0.8);
    const fA = frameOf(A, s, [0, 1, 2], lerp(4, 1.2, ej), lerp(2, 0.4, ej));
    const fP = frameOf(A, s, [1, 2], 3, 3);
    const pw = pairW(t);
    let c = fA.c.map((v, k) => lerp(v, fP.c[k], pw));
    let R = lerp(fA.R, Math.max(0.9, fP.R), pw);
    const bf = blueFocus(t);
    const blue = wp(q, 1);
    c = c.map((v, k) => lerp(v, lerp(blue[k], (blue[k] + wp(q, 0)[k]) / 2, 0.35), bf));
    R = lerp(R, 0.42, bf);
    const o = offK(t);
    c = c.map((v, k) => v + OFF[k] * o);
    const dist = autoD(R) * zoomK(t) * lerp(1, 0.8, ej);
    const cam = orbitCam(c, dist, elevK(t), yawK(t) + 0.004 * t);
    // 轨迹长度：快进时拉长
    const rate = Math.abs(sRew(t + 0.05) - sRew(t - 0.05)) / 0.1;
    const span = clamp(2.5 + rate * 0.9, 2.5, 14);
    const off = pw > 0 ? (si) => { const a = pairCom(A, si), b = pairCom(A, s); return [(a[0] - b[0]) * pw, 0, (a[2] - b[2]) * pw]; } : null;
    const trA = keys([[tSpin, 0], [tSpin + 2, 0.75]])(t) * (t > tRew0 ? 1 - 0.5 * prog(t, tRew0, tRew0 + 0.5) : 1);
    const rw = t > tRew0 && t < tRew1 + 0.5;
    const proj = draw3d({
      t, cam, stars: starsOf(q, { r: starR(t) }),
      trails: trA > 0 ? trailsOf(A, s, rw ? Math.min(span, 8) : pw > 0.5 ? 22 : span, { a: trA, off }) : [],
      dust: { a: 1 }, exposure: 1,
    });
    const P = [0, 1, 2].map((j) => proj(wp(q, j)));

    // 万有引力细线（H01–H03）：距离越近越亮，脉冲沿线流动
    const gA = fade(t, at('H01', '三颗星') + 0.3, at('H04', '三角形'), 0.8, 0.5);
    if (gA > 0) {
      const pulse = prog(t, at('H02', '万有引力'), at('H02', '万有引力') + 1.2);
      for (const [i, j] of [[0, 1], [1, 2], [0, 2]]) {
        const [x0, y0] = P[i], [x1, y1] = P[j];
        g.line(x0, y0, x1, y1, { color: COL.hud, w: 1, a: gA * 0.35 });
        for (let k = 0; k < 3; k++) {
          const u = (t * 0.6 + k / 3) % 1;
          const px = lerp(x0, x1, u), py = lerp(y0, y1, u), qx = lerp(x1, x0, u), qy = lerp(y1, y0, u);
          ctx.save(); ctx.globalAlpha *= gA * (0.4 + 0.6 * pulse) * Math.sin(Math.PI * u);
          ctx.fillStyle = COL.hud;
          ctx.beginPath(); ctx.arc(px, py, 2.2, 0, 7); ctx.arc(qx, qy, 2.2, 0, 7); ctx.fill(); ctx.restore();
        }
      }
      // 三颗星的名字
      const nA = fade(t, at('H01', '三颗星'), at('H03', '离得越近'), 0.4, 0.5);
      [0, 1, 2].forEach((j) => g.tag(P[j][0], P[j][1], NAME[j], { p: prog(t, at('H01', '三颗星') + j * 0.15, at('H01', '三颗星') + j * 0.15 + 0.8), a: nA, color: SIMCOL[j], dx: j === 0 ? -70 : 70, dy: j === 2 ? -60 : 60, r: 22 }));
      const eq = fade(t, at('H01', '一样大'), at('H03', '离得越近'), 0.3, 0.4);
      g.text('质量  1 : 1 : 1', W / 2, 150, { size: 32, font: F.mono, color: COL.hud, a: eq * 0.9, weight: '400', spacing: 3 });
    }
    // 三角形就位（H04）
    const triA = fade(t, at('H04', '三角形') - 0.1, tSpin + 2.5, 0.2, 0.6);
    if (triA > 0) {
      const p = prog(t, at('H04', '三角形') - 0.1, at('H04', '三角形') + 0.7);
      const q12 = Math.floor(p * 12) / 12;
      const pts = [P[0], P[1], P[2], P[0]].map((v) => [v[0], v[1]]);
      const per = 3 * q12;
      const seg = [];
      seg.push(pts[0]);
      for (let k = 0; k < 3; k++) {
        if (per >= k + 1) seg.push(pts[k + 1]);
        else if (per > k) { const u = per - k; seg.push([lerp(pts[k][0], pts[k + 1][0], u), lerp(pts[k][1], pts[k + 1][1], u)]); break; }
      }
      g.poly(seg, { color: COL.hud, w: 1.2, a: triA * 0.8 });
      const cx = (P[0][0] + P[1][0] + P[2][0]) / 3, cy = (P[0][1] + P[1][1] + P[2][1]) / 3;
      const rr = Math.max(...P.map((v) => Math.hypot(v[0] - cx, v[1] - cy))) + 60;
      g.brackets(cx - rr, cy - rr * 0.8, 2 * rr, 1.6 * rr, { p: prog(t, at('H04', '三角形'), at('H04', '三角形') + 0.5), a: triA });
      g.text('等边三角形', cx, cy - rr * 0.8 - 32, { size: 36, color: COL.hud, a: triA * prog(t, at('H04', '三角形') + 0.3, at('H04', '三角形') + 0.6), shadow: 8 });
    }
    // 队形散了
    const brA = fade(t, tBreak - 0.2, at('H06', '乱成一团', true), 0.2, 0.4);
    if (brA > 0) {
      const cx = (P[0][0] + P[1][0] + P[2][0]) / 3, cy = (P[0][1] + P[1][1] + P[2][1]) / 3;
      g.tag(cx, cy, '队形散了', { p: prog(t, tBreak - 0.2, tBreak + 0.6), a: brA, r: 34, dx: 120, dy: -110 });
    }
    // 红星被甩出
    const ejA = fade(t, at('H07', '红星') - 0.1, TE('H07') - 0.2, 0.2, 0.5);
    if (ejA > 0) {
      const p = prog(t, at('H07', '红星') - 0.1, at('H07', '红星') + 0.7);
      const sub = t > tEject - 0.5 ? `被甩出   v ${Math.hypot(...vel(A, s, 0)).toFixed(2)}` : '';
      g.tag(P[0][0], P[0][1], '红星', { p, a: ejA, color: TINT.red, dx: -90, dy: -80, sub, subColor: TINT.red });
    }
    const slo = fade(t, tEject - 0.9, tEject + 0.6, 0.15, 0.3);
    if (slo > 0) g.text('慢放 ×1/4', W - 120, 110, { size: 24, font: F.mono, color: COL.hud, a: slo, align: 'right', weight: '400', spacing: 2 });
    // 成了一对
    const prA = fade(t, at('H08', '蓝星') - 0.1, tRew0, 0.2, 0.3);
    if (prA > 0) {
      g.tag(P[1][0], P[1][1], '蓝星', { p: prog(t, at('H08', '蓝星'), at('H08', '蓝星') + 0.6), a: prA, color: TINT.blue, dx: -80, dy: 70, r: 20 });
      g.tag(P[2][0], P[2][1], '黄星', { p: prog(t, at('H08', '蓝星') + 0.25, at('H08', '蓝星') + 0.85), a: prA, color: TINT.yellow, dx: 80, dy: -70, r: 20 });
      const cA = prog(t, at('H08', '成了一对') - 0.1, at('H08', '成了一对') + 0.5);
      if (cA > 0) {
        const cx = (P[1][0] + P[2][0]) / 2, cy = (P[1][1] + P[2][1]) / 2, rr = Math.max(90, Math.hypot(P[1][0] - P[2][0], P[1][1] - P[2][1]) / 2 + 60);
        g.brackets(cx - rr, cy - rr * 0.75, 2 * rr, 1.5 * rr, { p: cA, a: prA });
        g.text('双星', cx, cy + rr * 0.75 + 36, { size: 36, color: COL.hud, a: prA * cA, shadow: 8 });
      }
    }
    // 倒带
    const rwA = fade(t, tRew0 - 0.1, tRew1 + 0.4, 0.15, 0.4);
    if (rwA > 0) {
      g.text('◀◀', 110, 112, { size: 40, color: COL.hud, a: rwA * (0.6 + 0.4 * Math.round((Math.sin(t * 18) + 1) / 2)), align: 'left', font: F.ui });
      g.text(`t = ${s.toFixed(1).padStart(5, ' ')}`, 190, 112, { size: 30, color: COL.hud, a: rwA, align: 'left', font: F.mono, weight: '400' });
      // 扫描线
      ctx.save(); ctx.globalAlpha *= rwA * 0.25; ctx.fillStyle = '#9fd0ff';
      for (let k = 0; k < 4; k++) { const y = ((t * 900 + k * 290) % (H + 60)) - 30; ctx.fillRect(0, y, W, 2); }
      ctx.restore();
    }
    // 蓝星往右挪
    const mvA = fade(t, at('H10', '蓝星') - 0.1, tSplit, 0.2, 0.4);
    if (mvA > 0) {
      const [bx, by] = P[1];
      g.tag(bx, by, '蓝星', { p: prog(t, at('H10', '蓝星') - 0.1, at('H10', '蓝星') + 0.6), a: mvA, color: TINT.blue, dx: -110, dy: -90, r: 26 });
      const ar = prog(t, at('H10', '往右挪'), at('H10', '往右挪') + 0.5);
      if (ar > 0) {
        const L = 110 * easeOut(ar);
        g.line(bx + 34, by, bx + 34 + L, by, { color: COL.hud, w: 2, a: mvA });
        arrowHead(bx + 34 + L, by, 0, 14, COL.hud, mvA);
      }
      // 距离线 + 百万分之一
      const dA = fade(t, T('H11'), tSplit, 0.3, 0.3);
      if (dA > 0) {
        const [rx, ry] = P[0];
        g.line(bx, by, rx, ry, { color: COL.hud, w: 1, a: dA * 0.6, dash: [6, 6] });
        const km = t > at('H13', '一公里') - 0.1;
        const lab = km ? '1 公里' : '距离 1';
        g.text(lab, (bx + rx) / 2 - 20, (by + ry) / 2 - 28, { size: 28, color: COL.hud, a: dA, shadow: 8, font: km ? F.ui : F.mono, weight: km ? '500' : '400' });
      }
      const nA = fade(t, at('H12', '百万分之一') - 0.15, at('H13', '一毫米') + 0.2, 0.2, 0.4);
      if (nA > 0) {
        g.text('挪动 ÷ 距离 =', W / 2 - 40, 140, { size: 30, color: COL.hud, a: nA, align: 'right', weight: '400' });
        g.text('0.000 001', W / 2 - 20, 140, { size: 54, color: '#ffffff', a: nA, align: 'left', font: F.mono, weight: '400' });
      }
      // 放大镜：1 毫米
      const mg = fade(t, at('H13', '一毫米') - 0.3, tSplit, 0.35, 0.4);
      if (mg > 0) {
        const mx = bx - 400, my = by - 250, mr = 190;
        g.line(bx - 22, by - 16, mx + mr * 0.72, my + mr * 0.7, { color: COL.hud, w: 1, a: mg * 0.7 });
        ctx.save(); ctx.globalAlpha *= mg;
        ctx.beginPath(); ctx.arc(mx, my, mr * easeOut(prog(t, at('H13', '一毫米') - 0.3, at('H13', '一毫米') + 0.1)), 0, 7);
        ctx.fillStyle = 'rgba(4,8,16,0.92)'; ctx.fill(); ctx.clip();
        for (let k = -6; k <= 6; k++) { g.line(mx + k * 25, my - mr, mx + k * 25, my + mr, { color: COL.hud, w: 1, a: 0.08 }); g.line(mx - mr, my + k * 25, mx + mr, my + k * 25, { color: COL.hud, w: 1, a: 0.08 }); }
        const gl = (x, y, c, rad, al) => { const gr = ctx.createRadialGradient(x, y, 0, x, y, rad); gr.addColorStop(0, c); gr.addColorStop(1, 'rgba(0,0,0,0)'); ctx.globalAlpha = mg * al; ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(x, y, rad, 0, 7); ctx.fill(); };
        gl(mx - 22, my, 'rgba(111,168,255,0.9)', 60, 0.6);
        gl(mx + 22, my, 'rgba(111,168,255,1)', 60, 1);
        ctx.globalAlpha = mg;
        ctx.strokeStyle = 'rgba(255,255,255,0.65)'; ctx.setLineDash([4, 4]); ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(mx - 22, my, 26, 0, 7); ctx.stroke(); ctx.setLineDash([]);
        ctx.restore();
        g.line(mx - 22, my + 66, mx + 22, my + 66, { color: '#fff', w: 1.5, a: mg });
        g.line(mx - 22, my + 58, mx - 22, my + 74, { color: '#fff', w: 1.5, a: mg });
        g.line(mx + 22, my + 58, mx + 22, my + 74, { color: '#fff', w: 1.5, a: mg });
        g.text('1 毫米', mx, my + 108, { size: 36, color: '#fff', a: mg, shadow: 8 });
        ctx.save(); ctx.globalAlpha *= mg; ctx.strokeStyle = COL.hud; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(mx, my, mr, 0, 7); ctx.stroke(); ctx.restore();
        g.text('原位置', mx - 70, my - 62, { size: 24, color: COL.grey, a: mg, weight: '400' });
      }
    }
  }

  // ---------- 镜头 C01：分屏，A / B 同步 ----------
  const ghostA = (t) => fade(t, tGo, at('H17', '红星'), 0.5, 1.0);
  function panel(arr, other, s, t, x, label, side, gaO = null) {
    const q = samp(arr, s), qo = samp(other, s);
    const esc = side === 0 ? 0 : 2;                     // 这一边最终被甩出的星
    const far = side === 0 ? prog(s, 44, 48) : (s > 168 ? prog(s, 168, 176) : 0);
    const fAll = frameOf(arr, s, [0, 1, 2], 4, 2);
    const fP = frameOf(arr, s, [0, 1, 2].filter((j) => j !== esc), 3, 3);
    let c = fAll.c.map((v, k) => lerp(v, fP.c[k], far));
    let R = lerp(Math.min(fAll.R, side === 0 ? 30 : 30), Math.max(0.9, fP.R), far);
    R = Math.max(R, 0.62);
    const cam = orbitCam(c, autoD(R) * 1.12, keys([[tGo, 0.5], [80, 0.62]])(t), 0.25 + 0.01 * (t - tGo), { fov: 34 });
    const rate = Math.abs(sB(t + 0.05) - sB(t - 0.05)) / 0.1;
    const span = clamp(2.5 + rate * 0.5, 2.5, 30);
    const ga = gaO ?? ghostA(t);
    const thins = ga > 0 ? [0, 1, 2].map((j) => ({ pts: trail(other, s, j, Math.min(span, 8), 300), col: '#ffffff', a: 0.35 * ga, fade: 1.5 })) : [];
    const proj = draw3d({ t, cam, stars: starsOf(q), trails: trailsOf(arr, s, span, { a: 0.8 }), thins, dust: { a: 0.8 }, size: [W / 2, H], vig: 0.6 }, x);
    const P = [0, 1, 2].map((j) => proj(wp(q, j)));
    // 幽灵星（另一次）+ 红色差距线
    if (ga > 0) {
      for (let j = 0; j < 3; j++) {
        const [gx, gy] = proj(wp(qo, j));
        const d = Math.hypot(gx - P[j][0], gy - P[j][1]);
        if (d > 4) g.line(P[j][0], P[j][1], gx, gy, { color: COL.red, w: 1.6, a: ga * clamp(d / 30) });
        ctx.save(); ctx.globalAlpha *= ga * 0.8; ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.arc(gx, gy, 7, 0, 7); ctx.stroke(); ctx.restore();
      }
    }
    // 面板标题
    const lx = side === 0 ? x + 60 : x + W / 2 - 60, al = side === 0 ? 'left' : 'right';
    g.text(label, lx, 90, { size: 38, color: COL.white, align: al, a: prog(t, tSplit, tSplit + 0.6), shadow: 10 });
    g.text(side === 0 ? '原位置' : '蓝星挪动 0.000001', lx, 136, { size: 24, color: COL.grey, align: al, a: prog(t, tSplit + 0.2, tSplit + 0.8), font: F.mono, weight: '400' });
    // 被甩出的星：屏内标注，屏外用边缘箭头
    const [ex, ey] = P[esc];
    const inside = ex > x + 40 && ex < x + W / 2 - 40 && ey > 40 && ey < H - 160;
    const tagT = side === 0 ? at('H17', '红星') + 0.6 : at('H17', '黄星');
    const tagA = fade(t, tagT, TE('H19') + 0.6, 0.2, 0.4);
    if (tagA > 0) {
      let sub = '被甩出';
      if (side === 1) {
        if (t > at('H18', '拽了回来') - 0.1) sub = '被拽了回来';
        if (t > at('H18', '又被甩了出去')) sub = '又被甩出';
        if (t > at('H18', '真走了') - 0.1) sub = '飞走了';
      } else if (t > at('H18', '老远')) sub = '飞走了';
      const dd = Math.hypot(...[0, 1].map((k) => q[2 * esc + k] - (q[2 * ((esc + 1) % 3) + k] + q[2 * ((esc + 2) % 3) + k]) / 2));
      if (inside) g.tag(ex, ey, NAME[esc], { p: prog(t, tagT, tagT + 0.7), a: tagA, color: SIMCOL[esc], dx: side === 0 ? 80 : -80, dy: -70, sub: `${sub}  距离 ${dd.toFixed(1)}`, subColor: SIMCOL[esc] });
      else {
        const cx = x + W / 4, cy = H / 2;
        const ang = Math.atan2(ey - cy, ex - cx);
        const bx = clamp(cx + Math.cos(ang) * 2000, x + 60, x + W / 2 - 60), by = clamp(cy + Math.sin(ang) * 2000, 230, H - 220);
        arrowHead(bx, by, ang, 18, SIMCOL[esc], tagA);
        g.text(`${NAME[esc]} ${sub}`, bx - Math.cos(ang) * 60, by - Math.sin(ang) * 40, { size: 26, color: SIMCOL[esc], a: tagA, shadow: 8 });
        g.text(`距离 ${dd.toFixed(1)}`, bx - Math.cos(ang) * 60, by - Math.sin(ang) * 40 + 32, { size: 20, color: SIMCOL[esc], a: tagA * 0.8, font: F.mono, weight: '400' });
      }
    }
    return P;
  }
  function split(lt, t) {
    const s = sB(t);
    const wipe = easeOut(prog(t, tSplit, tSplit + 0.6));
    panel(A, B, s, t, 0, '第一次', 0);
    panel(B, A, s, t, W / 2, '第二次', 1);
    // 中缝
    g.line(W / 2, H / 2 - (H / 2) * wipe, W / 2, H / 2 + (H / 2) * wipe, { color: COL.hud, w: 1.2, a: 0.7 });
    // 差距读数
    const d = OP.gap[Math.min(OP.gap.length - 1, Math.round(s * 60))];
    const dA = fade(t, tGo, at('H17', '黄星') + 0.6, 0.4, 0.5);
    if (dA > 0) {
      const v = d < 0.001 ? d.toFixed(6) : d < 0.1 ? d.toFixed(4) : d.toFixed(2);
      g.rect(W / 2 - 170, 40, 340, 84, { fill: 'rgba(2,6,12,0.75)', color: COL.hud, lw: 1, a: dA });
      g.text('两次的差距', W / 2, 64, { size: 20, color: COL.grey, a: dA, weight: '400' });
      g.text(v, W / 2, 100, { size: 34, color: d > 0.05 ? COL.red : '#fff', a: dA, font: F.mono, weight: '400' });
    }
    const slo = fade(t, at('H16', '对不上了') - 1.2, at('H16', '对不上了') + 0.5, 0.2, 0.3) + fade(t, at('H18', '拽了回来') - 0.4, at('H18', '又被甩了出去'), 0.2, 0.3);
    if (slo > 0) g.text('慢放', W - 70, H - 200, { size: 22, font: F.mono, color: COL.hud, a: clamp(slo), align: 'right', weight: '400' });
    // 结局对比
    const endA = fade(t, at('H19', '完全不一样') - 0.2, TE('H19') + 0.8, 0.3, 0.6);
    if (endA > 0) {
      for (const [x, txt, c] of [[W / 4, '结局：红星飞走', TINT.red], [W * 0.75, '结局：黄星飞走', TINT.yellow]]) {
        g.rect(x - 170, H - 250, 340, 64, { fill: 'rgba(2,6,12,0.7)', color: c, lw: 1.2, a: endA });
        g.text(txt, x, H - 218, { size: 32, color: c, a: endA });
      }
    }
  }

  // ---------- H20：三颗星继续乱舞 + 位置 / 方向 / 速度 ----------
  const sD = mono([[TE('H19') - 0.6, 7], [TE('H20') + 1.0, 30]]);
  function dance(lt, t) {
    const s = sD(t), q = samp(A, s);
    const f = frameOf(A, s, [0, 1, 2], 5, 3);
    const cam = orbitCam(f.c, autoD(f.R) * 1.15, 0.55, 0.9 + 0.02 * t);
    const proj = draw3d({ t, cam, stars: starsOf(q), trails: trailsOf(A, s, 4.5, { a: 0.7 }), dust: { a: 1 } });
    const P = [0, 1, 2].map((j) => proj(wp(q, j)));
    const k1 = at('H20', '在哪儿'), k2 = at('H20', '往哪儿跑'), k3 = at('H20', '跑多快'), k4 = at('H20', '任何时候');
    const hA = fade(t, k1 - 0.2, TE('H20') + 0.6, 0.2, 0.5);
    if (hA > 0) {
      for (let j = 0; j < 3; j++) {
        const [x, y] = P[j];
        const p1 = prog(t, k1 - 0.2 + j * 0.08, k1 + 0.4 + j * 0.08);
        g.brackets(x - 22, y - 22, 44, 44, { p: p1, a: hA, color: SIMCOL[j] });
        if (p1 >= 1) g.text(`x ${q[2 * j].toFixed(2)}  y ${q[2 * j + 1].toFixed(2)}`, x + 34, y - 30, { size: 19, font: F.mono, color: SIMCOL[j], a: hA, align: 'left', weight: '400', shadow: 6 });
        const p2 = prog(t, k2, k2 + 0.4);
        if (p2 > 0) {
          const v = vel(A, s, j);
          const pa = proj(wp(q, j)), pb = proj([q[2 * j] + v[0] * 0.25, 0, -(q[2 * j + 1] + v[1] * 0.25)]);
          const ang = Math.atan2(pb[1] - pa[1], pb[0] - pa[0]);
          const L = 70 * easeOut(p2);
          g.line(x + Math.cos(ang) * 26, y + Math.sin(ang) * 26, x + Math.cos(ang) * (26 + L), y + Math.sin(ang) * (26 + L), { color: SIMCOL[j], w: 2, a: hA });
          arrowHead(x + Math.cos(ang) * (26 + L), y + Math.sin(ang) * (26 + L), ang, 12, SIMCOL[j], hA);
          const p3 = prog(t, k3, k3 + 0.3);
          if (p3 > 0) g.text(`v ${Math.hypot(...v).toFixed(2)}`, x + 34, y + 34, { size: 19, font: F.mono, color: SIMCOL[j], a: hA * p3, align: 'left', weight: '400', shadow: 6 });
        }
      }
      const p4 = prog(t, k4 - 0.1, k4 + 0.4);
      if (p4 > 0) {
        g.rect(W - 440, 70, 360, 120, { fill: 'rgba(2,6,12,0.7)', color: COL.hud, lw: 1, a: hA * p4 });
        g.text('以后任何时刻', W - 260, 104, { size: 24, color: COL.grey, a: hA * p4, weight: '400' });
        g.text('t = ?', W - 260, 152, { size: 46, color: '#fff', a: hA * p4, font: F.mono, weight: '400' });
      }
    }
  }

  // ---------- 刘慈欣（T1）细线框 ----------
  async function liu(lt, t) {
    space && ctx.drawImage(space.draw({ t, cam: orbitCam([0, 0, 0], 5, 0.3, 0.2 * t), sky: 0.8 }), 0, 0);
    const im = await clip('T1', lt);
    const w = 1280, h = 720, x = (W - w) / 2, y = (H - h) / 2 - 40;
    const s = 1.0 + lt * 0.01;
    g.cover(im, { box: [x, y, w, h], s });
    g.rect(x, y, w, h, { color: COL.hud, lw: 1, a: 0.8 });
    g.brackets(x - 10, y - 10, w + 20, h + 20, { p: prog(lt, 0, 0.5), color: COL.hud, len: 26 });
    g.text('刘慈欣', x, y + h + 34, { size: 26, color: COL.white, align: 'left' });
    g.text('画面来源：阳泉日报', x + w, y + h + 34, { size: 20, color: COL.grey, align: 'right', weight: '400' });
  }

  // ---------- 三体星球地平线：三颗太阳乱跑 ----------
  const sH = mono([[T('H22') - 0.4, 28], [at('H22', '说不准', true), 47], [T('H23') + 0.3, 49]]);
  function horizon(lt, t) {
    const s = sH(t), q = samp(A, s);
    const cam = { pos: [0.3 + lt * 0.012, 0.0, 6.6 - lt * 0.03], look: [0, -0.45 + lt * 0.01, 0], fov: 30 };
    // 模拟平面竖起来贴在天上：y 低于地平线就是“落下”
    const fr = frameOf(A, s, [0, 1, 2], 6, 6);
    const cx = fr.c[0], cy = -fr.c[2];
    const stars = [0, 1, 2].map((j) => ({ p: [0.3 + (q[2 * j] - cx) * 0.55, 0.4 + (q[2 * j + 1] - cy) * 0.42, -1.2], col: SIMCOL[j], r: 0.04, glow: 1.3, light: 3 }));
    const cv = space.draw({ t, cam, stars, horizon: { p: [0.3, -3.245, 6.6], scale: 3.2 }, exposure: 1.05 });
    ctx.drawImage(cv, 0, 0);
  }

  // ---------- 万相快切 ----------
  const wan = (name, o = {}) => async (lt) => { const im = await clip(name, lt * (o.speed ?? 1) + (o.ss ?? 0)); g.cover(im, { s: (o.s0 ?? 1.02) + lt * (o.zoom ?? 0.01) }); };

  // ---------- 两个天体：太阳 + 地球（偏心率放大） ----------
  const SUN = '#ffd890';
  const P2 = 2.6;      // 一圈 2.6 秒
  function twoBody(lt, t) {
    const t0e = T('H25') - 0.2;
    const ph = Math.max(0, (t - t0e) / P2);
    const a = 1.5, e = 0.5;
    const pe = ellipse(a, e, ph + 0.5);
    const yaw = 0.3 + 0.02 * lt, cam = orbitCam([-0.6, 0, 0], 6.4, 0.72 - 0.004 * lt, yaw);
    const n = 600, pts = new Float32Array(n * 3);
    const done = Math.min(ph, 1);
    for (let i = 0; i < n; i++) { const p = ellipse(a, e, 0.5 + (done * i) / (n - 1)); pts.set(p, 3 * i); }
    const third = prog(t, at('H26', '加一个') - 0.2, at('H26', '加一个') + 0.6);
    const thirdP = [lerp(2.6, 1.6, easeOut(third)), 0.0, lerp(-2.2, -1.4, easeOut(third))];
    const stars = [{ p: [0, 0, 0], col: SUN, r: 0.1, glow: 0.45 }];
    if (third > 0) stars.push({ p: thirdP, col: TINT.red, r: 0.06, a: third });
    const proj = draw3d({
      t, cam, stars,
      planets: [{ type: 'earth', p: pe, r: 0.05, light: [0, 0, 0] }],
      trails: [{ pts, col: '#8fc4ff', a: 0.8, w: 1.6, fade: 0 }],
      dust: { a: 0.35 }, exposure: 1,
    });
    const [sx, sy] = proj([0, 0, 0]), [ex, ey] = proj(pe);
    const nA = fade(t, T('H25') + 0.2, TE('H26'), 0.3, 0.4);
    g.tag(sx, sy, '太阳', { p: prog(t, T('H25') + 0.2, T('H25') + 0.9), a: nA, color: SUN, dx: -90, dy: -80 });
    g.tag(ex, ey, '地球', { p: prog(t, T('H25') + 0.5, T('H25') + 1.2), a: nA, color: '#8fc4ff', dx: 80, dy: -60, r: 18 });
    const lapA = fade(t, at('H25', '椭圆'), TE('H26'), 0.3, 0.4);
    if (lapA > 0) {
      g.text(`第 ${Math.min(9, Math.floor(ph) + 1)} 圈`, W - 120, 120, { size: 36, font: F.ui, color: COL.hud, align: 'right', a: lapA });
      g.text('每一圈都走同一个椭圆', W - 120, 164, { size: 22, color: COL.grey, align: 'right', a: lapA * prog(t, at('H25', '永远'), at('H25', '永远') + 0.4), weight: '400' });
    }
    g.text('示意：椭圆扁度已夸大', 80, H - 40, { size: 18, color: COL.grey, align: 'left', a: nA * 0.8, weight: '400' });
    const q2 = fade(t, T('H26'), TE('H26') + 0.6, 0.3, 0.4);
    if (q2 > 0) {
      g.text('2 个', W / 2 - 220, 150, { size: 54, color: '#fff', a: q2, font: F.ui });
      g.text('能算', W / 2 - 220, 210, { size: 26, color: COL.hud, a: q2, weight: '400' });
      g.text('3 个', W / 2 + 220, 150, { size: 54, color: TINT.red, a: q2 * third, font: F.ui });
      g.text('？', W / 2 + 220, 210, { size: 30, color: TINT.red, a: q2 * third, weight: '400' });
    }
  }

  // ---------- 红星离开，只剩两个（H24） ----------
  const sL = mono([[T('H24') - 0.6, 43], [TE('H24') + 0.5, 60]]);
  function leave(lt, t) {
    const s = sL(t), q = samp(A, s);
    const fP = frameOf(A, s, [1, 2], 3, 3);
    const cam = orbitCam(fP.c, 3.6, 0.5, -0.4 + 0.02 * lt);
    const off = (si) => { const a = pairCom(A, si), b = pairCom(A, s); return [a[0] - b[0], 0, a[2] - b[2]]; };
    const proj = draw3d({ t, cam, stars: starsOf(q, { a: [1 - prog(t, at('H24', '两个天体') - 0.5, at('H24', '两个天体') + 0.3), 1, 1] }), trails: trailsOf(A, s, 10, { a: 0.6, off, idx: [1, 2] }), dust: { a: 1 } });
    const P = [1, 2].map((j) => proj(wp(q, j)));
    const k = prog(t, at('H24', '两个天体'), at('H24', '两个天体') + 0.6);
    if (k > 0) {
      const cx = (P[0][0] + P[1][0]) / 2, cy = (P[0][1] + P[1][1]) / 2, rr = 170;
      g.brackets(cx - rr, cy - rr * 0.7, 2 * rr, 1.4 * rr, { p: k });
      g.text('只有两个', cx, cy + rr * 0.7 + 32, { size: 28, color: COL.hud, a: k, shadow: 8 });
    }
  }

  // ---------- 松德曼卡 ----------
  let SUND = null, NOTE = null;
  async function sundman(lt, t) {
    SUND = SUND || (await img('/assets/photos/sundman.jpg'));
    ctx.drawImage(space.draw({ t, cam: orbitCam([0, 0, 0], 5, 0.35, 0.6 + 0.01 * t), sky: 0.7 }), 0, 0);
    g.photo(SUND, 600, 470, 560, { name: '卡尔·松德曼', years: '1873 – 1949', note: '芬兰数学家', s: 1 + lt * 0.004, rot: -0.02, a: prog(lt, 0, 0.6) });
    const y1 = fade(t, at('H27', '一九一二') - 0.1, TE('H27') + 0.3, 0.3, 0.4);
    g.text('1912', 1320, 300, { size: 150, font: F.num, color: COL.gold, a: y1, weight: '600' });
    const f1 = fade(t, at('H27', '公式') - 0.2, TE('H27') + 0.3, 0.4, 0.4);
    if (f1 > 0) {
      g.text('三个天体的位置 =', 1080, 470, { size: 40, color: COL.white, a: f1, align: 'left', weight: '400' });
      g.text('一个对任何时刻都成立的公式', 1080, 530, { size: 40, color: COL.white, a: f1, align: 'left', weight: '400' });
    }
    const st = prog(t, at('H27', '严格证明') - 0.05, at('H27', '严格证明') + 0.2);
    if (st > 0) {
      ctx.save(); ctx.globalAlpha *= st * fade(t, 0, TE('H27') + 0.3, 0, 0.4); ctx.translate(1300, 650); ctx.rotate(-0.08); ctx.scale(lerp(1.6, 1, easeOut(st)), lerp(1.6, 1, easeOut(st)));
      ctx.strokeStyle = COL.red; ctx.lineWidth = 4; ctx.strokeRect(-150, -46, 300, 92);
      ctx.fillStyle = COL.red; ctx.font = `700 52px ${F.serif}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('严格证明', 0, 4);
      ctx.restore();
    }
  }
  // 有解 vs 无解
  function versus(lt, t) {
    ctx.drawImage(space.draw({ t, cam: orbitCam([0, 0, 0], 5, 0.35, 0.6 + 0.01 * t), sky: 0.6 }), 0, 0);
    const a1 = prog(t, T('H28') - 0.3, T('H28') + 0.3), a2 = prog(t, at('H28', '无解') - 0.1, at('H28', '无解') + 0.25);
    g.text('有解', W / 2 - 300, H / 2 - 40, { size: 150, font: F.serif, weight: '700', color: COL.gold, a: a1 });
    g.text('1912 · 松德曼', W / 2 - 300, H / 2 + 80, { size: 26, color: COL.grey, a: a1, weight: '400' });
    g.text('无解', W / 2 + 300, H / 2 - 40, { size: 150, font: F.serif, weight: '700', color: '#e8e8ea', a: a2 });
    g.text('一百多年后 · 大家都这么说', W / 2 + 300, H / 2 + 80, { size: 26, color: COL.grey, a: a2, weight: '400' });
    g.line(W / 2, H / 2 - 170 * a1, W / 2, H / 2 + 120 * a1, { color: COL.hud, w: 1, a: 0.6 });
    const qm = prog(t, T('H29'), T('H29') + 0.4);
    if (qm > 0) g.text('？', W / 2, H / 2 - 230, { size: 90, color: '#fff', a: qm, font: F.serif });
  }
  // H30：三颗星安静地转，引向标题
  function calm(lt, t) {
    const s = 0.2 * lt, q = samp(A, s);
    const cam = orbitCam([0, 0, 0], lerp(4.2, 6.5, smooth(prog(lt, 0, 6))), lerp(0.5, 1.2, smooth(prog(lt, 0, 6))), 0.4 + 0.03 * lt);
    draw3d({ t, cam, stars: starsOf(q), trails: trailsOf(A, s, 1.5, { a: 0.6 }), dust: { a: 1 }, exposure: lerp(1, 0.4, prog(lt, 4.2, 5.2)) });
  }

  // ---------- 标题卡：三声号角各升起一颗星，轨迹汇成标题 ----------
  const N1 = 0.0, N2 = 1.45, N3 = 3.05, CH = 4.05;    // 相对标题起点（对齐《查拉图斯特拉》27.53 / 29 / 30.6 / 31.6 秒）
  function title(lt, t) {
    const ts = [N1, N2, N3];
    const ord = [2, 0, 1];     // 先黄，再红，最后蓝
    const stars = [], trails = [];
    ts.forEach((t0, i) => {
      if (lt < t0) return;
      const j = ord[i];
      stars.push({ p: riseAt(i, t0, lt), col: SIMCOL[j], r: 0.045, glow: 0.8, noShrink: true });
      const n = 120, pts = new Float32Array(n * 3);
      for (let k = 0; k < n; k++) pts.set(riseAt(i, t0, t0 + (lt - t0) * (k / (n - 1))), 3 * k);
      trails.push({ pts, col: SIMCOL[j], a: 0.85, w: 2.0, fade: 1.2 });
    });
    const cam = { pos: [0, 0.2, 7.5 - lt * 0.12], look: [0, 0.1, 0], fov: 30 };
    const ex = lerp(1, 0, prog(lt, 7.2, 8));
    ctx.drawImage(space.draw({ t, cam, stars, trails, exposure: ex, bloom: 1.1, sky: 0.6 }), 0, 0);
    const ta = prog(lt, CH - 0.05, CH + 0.5) * (1 - prog(lt, 7.2, 7.9));
    if (ta > 0) {
      const k = lerp(1.08, 1, easeOut(prog(lt, CH, CH + 1.6)));
      ctx.save(); ctx.translate(W / 2, H / 2 + 130); ctx.scale(k, k);
      g.text('三体问题为什么无解', 0, 0, { size: 120, font: F.serif, weight: '700', color: '#f6f1e6', a: ta, spacing: 12, shadow: 30 });
      ctx.restore();
      g.text('THE THREE-BODY PROBLEM', W / 2, H / 2 + 240, { size: 26, font: F.latin, color: COL.gold, a: ta * prog(lt, CH + 0.6, CH + 1.4), spacing: 14, weight: '400' });
    }
  }
  // 依次：黄（升到顶点）、红（左下角）、蓝（右下角），落成和开场一样的三角形
  const RS = [[0.2, -2.8, 0], [-3.4, -2.2, 0], [3.4, -2.2, 0]];
  const RC = [[-1.6, -0.6, 0], [-2.2, 1.6, 0], [2.2, 1.6, 0]];
  const RF = [[0, 1.42, 0], [-0.5, 0.98, 0], [0.5, 0.98, 0]];
  function riseAt(k, t0, lt) {
    const e = easeOut(clamp((lt - t0) / 3.0));
    return [0, 1, 2].map((d) => (1 - e) * (1 - e) * RS[k][d] + 2 * (1 - e) * e * RC[k][d] + e * e * RF[k][d]);
  }

  // W01 首帧：匹配剪辑到 3D
  async function w01(lt) {
    const im = await clip('W01', lt);
    g.cover(im, { s: 1.0 });
  }

  // 第三章复用：开场分屏，从 s0 到 s1
  env.reprise = (t, s, a = 1) => {
    panel(A, B, s, t, 0, '第一次', 0, a);
    panel(B, A, s, t, W / 2, '第二次', 1, a);
    g.line(W / 2, 0, W / 2, H, { color: COL.hud, w: 1.2, a: 0.7 });
    const d = OP.gap[Math.min(OP.gap.length - 1, Math.round(s * 60))];
    g.rect(W / 2 - 170, 40, 340, 84, { fill: 'rgba(2,6,12,0.75)', color: COL.hud, lw: 1 });
    g.text('两次的差距', W / 2, 64, { size: 20, color: COL.grey, weight: '400' });
    g.text(d < 0.001 ? d.toFixed(6) : d < 0.1 ? d.toFixed(4) : d.toFixed(2), W / 2, 100, { size: 34, color: d > 0.05 ? COL.red : '#fff', font: F.mono, weight: '400' });
  };

  const tSplitEnd = TE('H19') + 0.6;
  return [
    { a: t0, b: tSplit + 0.6, draw: singleA },
    { a: 0, b: t0 + 1.3, fi: 0.8, fo: 1.3, draw: w01 },
    { a: tSplit, b: tSplitEnd, fi: 0.5, fo: 0, draw: split },
    { a: tSplitEnd - 1.0, b: T('H21') + 0.2, fi: 1.0, fo: 0.3, draw: dance },
    { a: T('H21') - 0.1, b: T('H22') - 0.1, fi: 0.3, fo: 0.4, draw: liu },
    { a: T('H22') - 0.5, b: T('H23') + 0.1, fi: 0.5, fo: 0.15, draw: horizon },
    { a: T('H23') - 0.1, b: at('H23', '乱来') - 0.05, draw: wan('W02') },
    { a: at('H23', '乱来') - 0.05, b: at('H23', '冻死人') - 0.1, draw: wan('W03', { zoom: 0.02 }) },
    { a: at('H23', '冻死人') - 0.1, b: at('H23', '烤死人') - 0.05, draw: wan('W04') },
    { a: at('H23', '烤死人') - 0.05, b: T('H24') + 0.2, fo: 0.3, draw: wan('W05', { zoom: 0.03 }) },
    { a: T('H24') - 0.1, b: T('H25') + 0.4, fi: 0.3, fo: 0.6, draw: leave },
    { a: T('H25') - 0.2, b: TE('H26') + 0.8, fi: 0.6, fo: 0.5, draw: twoBody },
    { a: TE('H26') + 0.4, b: T('H28') - 0.1, fi: 0.4, fo: 0.3, draw: sundman },
    { a: T('H28') - 0.3, b: T('H30') + 0.2, fi: 0.3, fo: 0.4, draw: versus },
    { a: T('H30') - 0.1, b: M('title'), fi: 0.5, fo: 0.3, draw: calm },
    { a: M('title'), b: M('title_end'), draw: title, noSub: true },
  ];
}
