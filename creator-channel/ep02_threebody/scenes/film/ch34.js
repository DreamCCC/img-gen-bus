// 第三章（国王的奖金）+ 第四章（有解，但没法用）
import { W, H, COL, F, TINT, SIMCOL, clamp, lerp, prog, smooth, easeOut, easeIn, easeInOut, fade, keys, mono, at, T, TE, M, clip, img, rng } from './lib.js';
import { OP, FD, WEB, samp, wp, frameOf, orbitCam, starsOf, trailsOf, ellipse } from './sim.js';
import { kit } from './common.js';

export function ch34Shots(env) {
  const { g, space, ctx } = env;
  const K = kit(env);
  const A = OP.A;
  const SUN = '#ffd890';
  const photo = {};
  const ph = async (n) => (photo[n] = photo[n] || (await img(`/assets/photos/${n}`)));
  const wan = (name, o = {}) => async (lt) => { const im = await clip(name, lt); g.cover(im, { s: (o.s0 ?? 1.02) + lt * (o.zoom ?? 0.008) }); };
  const dim = (a) => { ctx.save(); ctx.globalAlpha *= a; ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H); ctx.restore(); };
  const year = (s, x, y, a) => g.text(s, x, y, { size: 150, font: F.num, color: COL.gold, a, weight: '600' });

  // ---------- 斯德哥尔摩 + 奥斯卡二世 ----------
  async function oscar(lt, t) {
    await wan('W09', { zoom: 0.004 })(lt);
    const a = fade(t, at('C02', '奥斯卡') - 0.3, TE('C02') + 0.3, 0.4, 0.4);
    if (a > 0) {
      dim(a * 0.45);
      g.photo(await ph('oscar2.jpg'), 1380, 460, 500, { a, name: '奥斯卡二世', years: '1829 – 1907', note: '瑞典国王', rot: 0.02 });
      year('1885', 560, 380, a * prog(t, T('C02'), T('C02') + 0.4));
      g.text('悬赏征解数学难题', 560, 490, { size: 44, color: '#fff', a: a * prog(t, at('C02', '悬赏'), at('C02', '悬赏') + 0.4), shadow: 12 });
      g.text('60 岁生日那天颁奖', 560, 560, { size: 34, color: COL.gold, a: a * prog(t, at('C02', '六十岁'), at('C02', '六十岁') + 0.4), shadow: 12 });
    }
  }
  // ---------- 太阳系：很多天体互相吸引 ----------
  const PL = [[0.55, 0.9, '#c9b9a0', 'moon', 0.018], [0.8, 0.72, '#e8c38a', 'rock', 0.026], [1.1, 0.6, '#6fa8ff', 'earth', 0.028], [1.45, 0.5, '#d9785a', 'rock', 0.022], [2.2, 0.3, '#e8c9a0', 'jupiter', 0.07], [2.9, 0.22, '#e8d8a8', 'jupiter', 0.058]];
  function solar(lt, t) {
    const pos = PL.map(([r, w], i) => { const u = 1.3 * i + w * (t - 330); return [r * Math.cos(u), 0, -r * Math.sin(u)]; });
    const thins = PL.map(([r]) => { const n = 300, pts = new Float32Array(n * 3); for (let i = 0; i < n; i++) { const u = (i / (n - 1)) * 6.2832; pts.set([r * Math.cos(u), 0, -r * Math.sin(u)], 3 * i); } return { pts, col: '#8aa0c0', a: 0.28 }; });
    const proj = K.draw3d({ t, cam: orbitCam([0, 0, 0], 7.2, 0.8, 0.2 + 0.02 * lt), stars: [{ p: [0, 0, 0], col: SUN, r: 0.1, glow: 0.4, glowRef: 7 }], planets: pos.map((p, i) => ({ type: PL[i][3], p, r: PL[i][4], light: [0, 0, 0] })), thins, dust: { a: 0.2 } });
    const a = fade(t, at('C03', '很多天体') - 0.2, TE('C03') + 0.3, 0.4, 0.4);
    const S = [[0, 0, 0], ...pos].map(proj);
    for (let i = 0; i < S.length; i++) for (let j = i + 1; j < S.length; j++) g.line(S[i][0], S[i][1], S[j][0], S[j][1], { color: COL.hud, w: 1, a: a * 0.22 });
    g.text('很多天体互相吸引', W / 2, 140, { size: 40, color: COL.hud, a });
    g.text('能不能算出它们任何时候的位置？', W / 2, 200, { size: 32, color: '#fff', a: a * prog(t, at('C03', '能不能'), at('C03', '能不能') + 0.4) });
  }
  // ---------- 奖金横条 ----------
  function medal(x, y, r, a) {
    ctx.save(); ctx.globalAlpha *= a;
    const gr = ctx.createRadialGradient(x - r * 0.3, y - r * 0.3, r * 0.1, x, y, r);
    gr.addColorStop(0, '#fff3c4'); gr.addColorStop(0.5, '#e2b85a'); gr.addColorStop(1, '#8a6420');
    ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill();
    ctx.strokeStyle = '#fff1c0'; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(x, y, r * 0.82, 0, 7); ctx.stroke();
    ctx.restore();
  }
  function bar(x, y, w, h, val, label, color, a, p = 1) {
    if (a <= 0) return;
    h = 80;
    g.rect(x, y, w * easeOut(clamp(p)), h, { fill: color, lw: 0, a: a * 0.85 });
    g.text(label, x, y - 36, { size: 40, color: '#fff', a, align: 'left' });
    g.text(val, x + w * easeOut(clamp(p)) + 24, y + h / 2 + 4, { size: 68, font: F.num, color, a: a * clamp(p * 2 - 1), align: 'left', weight: '600' });
  }
  async function prize(lt, t) {
    K.bg(t, { sky: 0.5 });
    const a = fade(t, T('C04'), TE('C06') + 0.4, 0.3, 0.4);
    const m = prog(t, at('C04', '金质奖章') - 0.2, at('C04', '金质奖章') + 0.4);
    medal(W / 2 - 600, 330, 110 * easeOut(m), a * m);
    g.text('金质奖章', W / 2 - 600, 490, { size: 40, color: COL.gold, a: a * m });
    const scale = 1050 / 7000;
    bar(W / 2 - 360, 290, 2500 * scale, 56, '2500 克朗', '奖金', COL.gold, a, prog(t, at('C04', '两千五百') - 0.1, at('C04', '两千五百') + 0.6));
    const ml = prog(t, at('C06', '七千') - 0.2, at('C06', '七千') + 0.6);
    bar(W / 2 - 360, 560, 7000 * scale, 56, '7000 克朗', '米塔格-莱弗勒 当教授一年的工资', '#9fb8d8', a, ml);
    const ca = fade(t, at('C06', '米塔格莱弗勒') - 0.2, TE('C06') + 0.4, 0.3, 0.4);
    if (ca > 0) g.photo(await ph('mittagleffler.jpg'), 1600, 700, 300, { a: ca, name: '米塔格-莱弗勒', years: '1846 – 1927', rot: -0.02 });
    const q = fade(t, T('C05'), at('C06', '七千') - 0.2, 0.2, 0.3);
    if (q > 0) g.text('？', W / 2 - 360 + 2500 * scale + 330, 330, { size: 60, color: '#fff', a: q, font: F.serif });
  }
  // ---------- 庞加莱 + 格言 ----------
  const MOTTO = ['Nunquam', 'praescriptos', 'transibunt', 'sidera', 'fines'];
  function motto(x, y, t0, a, size = 76) {
    let w = 0; const ws = MOTTO.map((s) => { const ww = g.measure(s, size, F.latin, '400'); w += ww + size * 0.4; return ww; });
    let cx = x - w / 2;
    MOTTO.forEach((s, i) => {
      const p = prog(env.t, t0 + i * 0.35, t0 + i * 0.35 + 0.6);
      g.text(s, cx, y - 10 * (1 - easeOut(p)), { size, font: F.latin, color: '#f4efe4', a: a * p, align: 'left', weight: '400', shadow: 16, base: 'middle' });
      cx += ws[i] + size * 0.4;
    });
  }
  async function poincare(lt, t) {
    env.t = t;
    K.bg(t, { sky: 0.5 });
    const ca = fade(t, T('C07') - 0.2, at('C08', '拉丁文') - 0.1, 0.4, 0.5);
    if (ca > 0) {
      g.photo(await ph('poincare.png'), 760, 470, 560, { a: ca, name: '亨利·庞加莱', years: '1854 – 1912', note: '法国数学家', rot: -0.015, s: 1 + 0.004 * lt });
      g.text('匿名参赛', 1340, 420, { size: 44, color: '#fff', a: ca * prog(t, at('C08', '匿名'), at('C08', '匿名') + 0.4) });
      g.text('用一句格言当记号', 1340, 490, { size: 34, color: COL.gold, a: ca * prog(t, at('C08', '格言'), at('C08', '格言') + 0.4) });
    }
    const ma = fade(t, at('C08', '拉丁文') - 0.2, TE('C08') + 0.5, 0.3, 0.4);
    if (ma > 0) {
      g.line(W / 2 - 600, H / 2 - 110, W / 2 + 600, H / 2 - 110, { color: COL.gold, w: 1, a: ma * 0.5 });
      motto(W / 2, H / 2 - 30, at('C08', '拉丁文') - 0.1, ma);
      g.text('群星永不越出既定的边界', W / 2, H / 2 + 80, { size: 50, font: F.serif, weight: '600', color: COL.gold, a: ma * prog(t, at('C08', '意思是'), at('C08', '意思是') + 0.6), spacing: 6 });
      g.line(W / 2 - 600, H / 2 + 150, W / 2 + 600, H / 2 + 150, { color: COL.gold, w: 1, a: ma * 0.5 });
    }
  }
  // ---------- 简化的三体：两大一小 ----------
  function restricted(lt, t) {
    const w = 0.45, u = lt * w;
    const p1 = [-0.5 * Math.cos(u), 0, 0.5 * Math.sin(u)], p2 = [Math.cos(u), 0, -Math.sin(u)];
    const pa = [0.5 * Math.cos(u + 1.05) + 0.03 * Math.sin(lt * 1.7), 0, -0.5 * Math.sin(u + 1.05) * 1.73 * 0.58];
    const proj = K.draw3d({ t, cam: orbitCam([0.2, 0, 0], 4.8, 0.85, 0.3 + 0.015 * lt), stars: [{ p: p1, col: TINT.yellow, r: 0.07 }, { p: p2, col: TINT.blue, r: 0.05 }], planets: [{ type: 'rock', p: pa, r: 0.02, light: p1 }], dust: { a: 0.4 } });
    const a = fade(t, at('C09', '简化'), TE('C09') + 0.3, 0.3, 0.4);
    const [x, y] = proj(pa);
    g.tag(x, y, '第三个：小到可以忽略', { p: prog(t, at('C09', '简化'), at('C09', '简化') + 0.7), a, dx: 90, dy: -90, r: 18 });
    g.text('简化的三体问题', W / 2, 140, { size: 40, color: COL.hud, a });
    const st = prog(t, at('C09', '稳定') - 0.2, at('C09', '稳定') + 0.3);
    if (st > 0) { g.text('他的结论：稳定', W / 2, 205, { size: 36, color: COL.gold, a: a * st }); }
    const nt = fade(t, at('C09', '没有解决'), at('C09', '简化'), 0.2, 0.2);
    if (nt > 0) g.text('没有解决整个问题', W / 2, 140, { size: 40, color: '#fff', a: nt });
  }
  // ---------- 魏尔斯特拉斯 ----------
  async function weier(lt, t) {
    K.bg(t, { sky: 0.5 });
    const a = fade(t, T('C10') - 0.2, TE('C10') + 0.3, 0.4, 0.4);
    g.photo(await ph('weierstrass.jpg'), 480, 470, 520, { a, name: '卡尔·魏尔斯特拉斯', years: '1815 – 1897', note: '评委', rot: 0.02 });
    K.quote(['“这不算完整的解答，', '可它会开启天体力学的', '一个新纪元。”'], '— 魏尔斯特拉斯的评语（大意）', 1260, 380, { a, size: 50, p: prog(t, at('C10', '这不算'), at('C10', '新纪元') + 0.3) });
  }
  // ---------- 颁奖日 ----------
  function award(lt, t) {
    const k = 1 + lt * 0.02;
    ctx.save();
    const gr = ctx.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, H * 0.9);
    gr.addColorStop(0, 'rgba(120,90,40,0.55)'); gr.addColorStop(1, 'rgba(0,0,0,1)');
    ctx.fillStyle = gr; ctx.fillRect(0, 0, W, H);
    ctx.translate(W / 2, H / 2); ctx.scale(k, k);
    const a = prog(lt, 0.1, 0.6);
    g.text('1889 年 1 月 21 日', 0, -60, { size: 90, font: F.serif, weight: '700', color: '#f8e6b8', a, shadow: 30 });
    g.text('国王 60 岁生日 · 庞加莱获奖', 0, 50, { size: 38, color: '#fff', a: a * prog(t, at('C11', '庞加莱'), at('C11', '庞加莱') + 0.4) });
    ctx.restore();
    medal(W / 2, 820, 56, prog(t, at('C11', '拿了奖') - 0.1, at('C11', '拿了奖') + 0.4));
  }
  // ---------- 印刷 + 弗拉格曼 ----------
  async function press(lt, t) {
    const sw = at('C13', '弗拉格曼') + 1.2;
    if (t < sw) await wan('W10a', { zoom: 0.005 })(lt);
    else await wan('W10c', { zoom: 0.005 })(t - sw);
    const a = fade(t, at('C13', '弗拉格曼') - 0.3, TE('C13') + 0.3, 0.4, 0.4);
    if (a > 0) {
      dim(a * 0.4);
      g.photo(await ph('phragmen.jpg'), 1400, 470, 460, { a, name: '弗拉格曼', years: '1863 – 1937', note: '时年 26 岁', rot: 0.02 });
      g.text('校对时有几处没看懂', 560, 470, { size: 44, color: '#fff', a: a * prog(t, at('C13', '没看懂') - 0.2, at('C13', '没看懂') + 0.3), shadow: 12 });
      g.text('→ 写信去问', 560, 540, { size: 36, color: COL.gold, a: a * prog(t, at('C13', '写信') - 0.2, at('C13', '写信') + 0.3), shadow: 12 });
    }
    const j = fade(t, T('C13'), at('C13', '弗拉格曼') - 0.2, 0.3, 0.3);
    if (j > 0) g.text('Acta Mathematica', W / 2, 150, { size: 56, font: F.latin, color: '#f4efe4', a: j, weight: '400', shadow: 16 });
  }
  // ---------- 论文页：错误 ----------
  const pageLines = rng(42);
  const LINES = Array.from({ length: 22 }, (_, i) => ({ w: 0.55 + 0.4 * pageLines(), f: i === 9 || i === 15 }));
  function paper(x, y, w, h, a, o = {}) {
    ctx.save(); ctx.globalAlpha *= a;
    ctx.shadowColor = 'rgba(0,0,0,0.7)'; ctx.shadowBlur = 50;
    ctx.fillStyle = COL.paper; ctx.fillRect(x, y, w, h);
    ctx.shadowColor = 'transparent';
    ctx.restore();
    if (o.title) g.text(o.title, x + w / 2, y + 70, { size: 34, font: F.latin, color: COL.ink, a, weight: '400' });
  }
  function errorPage(lt, t) {
    K.bg(t, { sky: 0.4, exposure: 0.7 });
    const a = fade(t, T('C14') - 0.3, TE('C15') + 0.2, 0.4, 0.4);
    const x = W / 2 - 380, y = 90, w = 760, h = 900;
    const k = 1 + lt * 0.015;
    ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(k, k); ctx.translate(-W / 2, -H / 2);
    paper(x, y, w, h, a, { title: 'Sur le problème des trois corps' });
    LINES.forEach((L, i) => {
      const ly = y + 150 + i * 33;
      if (L.f) g.text(i === 9 ? 'dx/dt = dF/dy ,   dy/dt = − dF/dx' : 'F = F₀ + μF₁ + μ²F₂ + …', x + w / 2, ly, { size: 28, font: F.latin, color: COL.ink, a, weight: '400' });
      else g.rect(x + 70, ly - 5, (w - 140) * L.w, 9, { fill: 'rgba(43,36,27,0.35)', lw: 0, a });
    });
    const e = prog(t, at('C14', '错误') - 0.2, at('C14', '错误') + 0.4);
    if (e > 0) {
      ctx.save(); ctx.globalAlpha *= a; ctx.strokeStyle = COL.red; ctx.lineWidth = 4;
      ctx.beginPath(); ctx.ellipse(x + w / 2, y + 150 + 15 * 33, 240, 34, -0.02, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * easeOut(e)); ctx.stroke(); ctx.restore();
      g.text('错误', x + w + 90, y + 150 + 15 * 33, { size: 50, color: COL.red, a: a * e, font: F.serif, weight: '700' });
    }
    g.text('示意重排', x + w - 20, y + h - 24, { size: 18, color: 'rgba(43,36,27,0.6)', a, align: 'right', weight: '400' });
    ctx.restore();
    const pr = fade(t, T('C15'), TE('C15') + 0.2, 0.3, 0.3);
    if (pr > 0) { dim(pr * 0.6); g.text('杂志已经印出来了', W / 2, H / 2 - 40, { size: 60, color: '#fff', a: pr, font: F.serif, weight: '700' }); g.text('有的已经寄出', W / 2, H / 2 + 50, { size: 40, color: COL.red, a: pr * prog(t, at('C15', '寄出去') - 0.2, at('C15', '寄出去') + 0.3) }); }
  }
  // ---------- 电报 → 印刷机停 ----------
  async function telegram(lt, t) {
    const st = at('C16', '停印') - 0.3;
    if (t < st) await wan('W11', { zoom: 0.01 })(lt);
    else await wan('W10b', { zoom: 0 })(Math.min(t - st, 1.6));
    const a = fade(t, T('C16'), at('C16', '停印') + 0.2, 0.2, 0.2);
    if (a > 0) {
      dim(a * 0.35);
      g.text('1889 年 11 月底', W / 2, 200, { size: 56, font: F.serif, weight: '700', color: '#fff', a, shadow: 14 });
      const s = '电报：立即停印';
      const ty = g.typed(s, t, at('C16', '电报') - 0.1, 0.12);
      g.rect(W / 2 - 330, H / 2 - 60, 660, 120, { fill: 'rgba(233,225,207,0.92)', lw: 0, a });
      g.text(ty, W / 2 - 290, H / 2, { size: 56, font: F.mono, color: COL.ink, a, align: 'left', weight: '400' });
    }
    const s2 = fade(t, st + 0.1, TE('C16') + 0.3, 0.1, 0.3);
    if (s2 > 0) g.text('停 印', W / 2, H / 2, { size: 130, font: F.serif, weight: '700', color: COL.red, a: s2, shadow: 30, spacing: 30 });
  }
  // ---------- 信 ----------
  function letter(lt, t) {
    K.bg(t, { sky: 0.4, exposure: 0.7 });
    const a = fade(t, T('C17') - 0.2, TE('C17') + 0.3, 0.3, 0.3);
    const x = W / 2 - 420, y = 120, w = 840, h = 820;
    ctx.save(); ctx.translate(W / 2, H / 2); ctx.rotate(-0.03); ctx.scale(1 + lt * 0.02, 1 + lt * 0.02); ctx.translate(-W / 2, -H / 2);
    paper(x, y, w, h, a);
    ctx.save(); ctx.globalAlpha *= a * 0.55; ctx.filter = 'blur(2.2px)'; ctx.strokeStyle = '#3a2e20'; ctx.lineWidth = 2.2;
    const r = rng(7);
    for (let i = 0; i < 16; i++) {
      const ly = y + 110 + i * 42; let px = x + 70;
      ctx.beginPath(); ctx.moveTo(px, ly);
      while (px < x + w - 80 - (i === 15 ? 300 : 0)) { px += 6 + r() * 10; ctx.lineTo(px, ly + (r() - 0.5) * 14); }
      ctx.stroke();
    }
    ctx.restore(); ctx.restore();
    g.text('第二天', W / 2, 180, { size: 40, color: '#fff', a: a * prog(t, T('C17'), T('C17') + 0.3), shadow: 14 });
    const q = prog(t, at('C17', '问自己') - 0.2, at('C17', '问自己') + 0.5);
    if (q > 0) { dim(q * a * 0.35); K.quote(['“我还配不配得这个奖？”'], '— 庞加莱给米塔格-莱弗勒的信（大意）', W / 2, H / 2 - 20, { a: a * q, size: 64 }); }
  }
  // ---------- 收回 + 重印的钱 ----------
  function recall(lt, t) {
    K.bg(t, { sky: 0.5 });
    const a = fade(t, T('C18') - 0.2, TE('C19') + 0.4, 0.3, 0.4);
    const r = rng(3);
    const back = easeInOut(prog(t, at('C18', '收了回来') - 0.6, at('C18', '收了回来') + 0.6));
    const fadeJ = 1 - prog(t, T('C19') - 0.3, T('C19') + 0.2);
    for (let i = 0; i < 26; i++) {
      const ang = r() * 6.28, d = 380 + r() * 420;
      const x = W / 2 + Math.cos(ang) * d * (1 - back), y = H / 2 + Math.sin(ang) * d * 0.6 * (1 - back) - i * 3 * back;
      ctx.save(); ctx.globalAlpha *= a * fadeJ; ctx.translate(x, y); ctx.rotate((r() - 0.5) * (1 - back) * 1.2);
      ctx.fillStyle = '#d9cdb0'; ctx.fillRect(-60, -80, 120, 160); ctx.strokeStyle = '#6b5a40'; ctx.strokeRect(-60, -80, 120, 160);
      ctx.fillStyle = '#6b5a40'; ctx.font = `400 16px ${F.latin}`; ctx.textAlign = 'center'; ctx.fillText('ACTA', 0, -50);
      ctx.restore();
    }
    g.text('样刊全部收回 · 重新印', W / 2, 150, { size: 40, color: COL.hud, a: a * fadeJ * prog(t, at('C18', '收了回来'), at('C18', '收了回来') + 0.4) });
    const ba = a * prog(t, T('C19') - 0.2, T('C19') + 0.3);
    if (ba > 0) {
      const scale = 1150 / 3600;
      bar(W / 2 - 560, 330, 2500 * scale, 56, '2500 克朗', '他拿到的奖金', COL.gold, ba, 1);
      const p = prog(t, at('C19', '三千五百') - 0.1, at('C19', '三千五百') + 0.6);
      bar(W / 2 - 560, 560, 2500 * scale, 56, '', '重印的费用（庞加莱出）', '#9fb8d8', ba, p);
      const ex = prog(t, at('C19', '还多') - 0.1, at('C19', '还多') + 0.5);
      if (p > 0) g.rect(W / 2 - 560 + 2500 * scale, 560, 1100 * scale * easeOut(ex), 80, { fill: COL.red, lw: 0, a: ba });
      if (p >= 1) g.text('3500 多克朗', W / 2 - 560 + 3600 * scale + 24, 604, { size: 68, font: F.num, color: '#9fb8d8', a: ba, align: 'left', weight: '600' });
      if (ex > 0) g.text('多出 1000 多', W / 2 - 560 + 2500 * scale + 175, 690, { size: 40, color: COL.red, a: ba * ex });
      const bt = prog(t, at('C19', '倒贴钱') - 0.2, at('C19', '倒贴钱') + 0.3);
      if (bt > 0) g.text('得了奖，还倒贴钱', W / 2, 820, { size: 48, font: F.serif, weight: '700', color: '#fff', a: ba * bt });
    }
  }
  // ---------- 整版已销毁 ----------
  function destroyed(lt, t) {
    K.bg(t, { sky: 0.35, exposure: 0.6 });
    const a = fade(t, T('C20') - 0.2, TE('C20') + 0.8, 0.4, 0.6);
    const x = W / 2 - 360, y = 80, w = 720, h = 920;
    const k = lerp(1, 1.12, smooth(prog(t, T('C20'), TE('C20'))));
    ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(k, k); ctx.translate(-W / 2, -H / 2 - 40 * (k - 1) * 8);
    paper(x, y, w, h, a);
    g.text('ACTA MATHEMATICA', x + w / 2, y + 180, { size: 46, font: F.latin, color: COL.ink, a, weight: '400', spacing: 6 });
    g.text('13', x + w / 2, y + 260, { size: 40, font: F.latin, color: COL.ink, a, weight: '400' });
    g.line(x + 160, y + 320, x + w - 160, y + 320, { color: COL.ink, w: 1, a: a * 0.6 });
    g.text('STOCKHOLM  1889', x + w / 2, y + 380, { size: 26, font: F.latin, color: COL.ink, a, weight: '400', spacing: 4 });
    const hw = at('C20', '整版已销毁') - 0.05;
    const p = prog(t, hw, hw + 1.4);
    if (p > 0) {
      ctx.save(); ctx.beginPath(); ctx.rect(x, y + 470, (w - 40) * p + 40, 200); ctx.clip();
      g.text('Hela upplagan förstörd', x + w / 2, y + 560, { size: 60, font: '"Snell Roundhand", "Apple Chancery", cursive', color: '#3a2a8a', a, weight: '400' });
      ctx.restore();
      g.text('整版已销毁', x + w / 2, y + 680, { size: 50, font: '"Xingkai SC", "Kaiti SC", serif', color: '#3a2a8a', a: a * prog(t, hw + 1.0, hw + 1.6), weight: '400' });
    }
    g.text('示意重制', x + w - 20, y + h - 24, { size: 18, color: 'rgba(43,36,27,0.6)', a, align: 'right', weight: '400' });
    ctx.restore();
    const two = fade(t, at('C20', '两本') - 0.2, hw - 0.4, 0.3, 0.4);
    if (two > 0) g.text('错误的那一版 · 只剩 2 本', W / 2, 1000 - 40, { size: 30, color: '#fff', a: two, shadow: 12 });
  }
  // ---------- 混沌之网 ----------
  const WD = FD.web;
  const webPts = (m, j, s) => {
    const n = Math.max(2, Math.min(2048, Math.floor(s * WD.rate) + 1));
    const stride = Math.max(1, Math.ceil((Math.floor(s * WD.rate) + 1) / 2048));
    const cnt = Math.min(2048, Math.floor((Math.floor(s * WD.rate)) / stride) + 1);
    const pts = new Float32Array(cnt * 3);
    for (let i = 0; i < cnt; i++) {
      const f = Math.min(WD.n - 1, i * stride), o = (m * WD.n + f) * 6;
      pts[3 * i] = WEB[o + 2 * j]; pts[3 * i + 1] = 0; pts[3 * i + 2] = -WEB[o + 2 * j + 1];
    }
    return { pts, n: cnt };
  };
  function web(lt, t) {
    const s = lerp(4, 60, easeIn(prog(t, T('C22') - 0.3, TE('C22') + 0.6)) * 0.5 + 0.5 * prog(t, T('C22') - 0.3, TE('C22') + 0.6));
    const thins = [];
    for (let m = 0; m < WD.m; m++) for (const j of [0, 2]) { const w = webPts(m, j, s); thins.push({ pts: w.pts, n: w.n, col: SIMCOL[j], a: 0.22 }); }
    const coll = prog(t, at('C24', '混沌') - 1.0, at('C24', '混沌') + 0.3);
    const cam = orbitCam([0, 0, 0], lerp(lerp(3.2, 9, smooth(prog(t, T('C22'), TE('C22')))), 5.5, coll), lerp(1.1, 0.8, prog(t, T('C22'), TE('C22'))), 0.4 + 0.04 * lt);
    const proj = K.draw3d({ t, cam, thins, dust: { a: 0.4 }, bloom: 1.2, exposure: 1.1 });
    const a = fade(t, at('C22', '起点'), TE('C22') + 0.4, 0.3, 0.4);
    const p0 = proj(wp(samp(A, 0), 0));
    g.tag(p0[0], p0[1], '起点只差一点点', { p: prog(t, at('C22', '起点'), at('C22', '起点') + 0.6), a, r: 24, dx: -100, dy: -100 });
    g.text(`${WD.m} 次模拟 · 起点相差百万分之几`, W - 100, 110, { size: 24, color: COL.grey, a: fade(t, T('C22'), TE('C22') + 0.3, 0.4, 0.3), align: 'right', weight: '400' });
    const ca = prog(t, at('C24', '混沌') - 0.1, at('C24', '混沌') + 0.4) * fade(t, 0, TE('C24') + 0.8, 0, 0.5);
    if (ca > 0) {
      dim(ca * 0.35);
      g.text('混 沌', W / 2, H / 2 - 20, { size: 180, font: F.serif, weight: '700', color: '#fff6e8', a: ca, shadow: 40, spacing: 40 });
      g.text('CHAOS', W / 2, H / 2 + 120, { size: 34, font: F.latin, color: COL.gold, a: ca * prog(t, at('C24', '混沌') + 0.4, at('C24', '混沌') + 1.0), spacing: 24, weight: '400' });
    }
  }
  function reprise(lt, t) {
    const s = lerp(22, 31, prog(t, T('C23') - 0.4, TE('C23') + 0.3));
    env.reprise(t, s, 1);
  }
  // ---------- 290 页 ----------
  function pages(lt, t) {
    K.bg(t, { sky: 0.5 });
    const a = fade(t, T('C25') - 0.2, TE('C25') + 0.3, 0.3, 0.4);
    const n = Math.round(290 * easeOut(prog(t, at('C25', '两百九十') - 0.3, at('C25', '两百九十') + 0.9)));
    for (let i = 0; i < Math.min(40, n / 7); i++) { const x = W / 2 - 520 + i * 2, y = 620 - i * 9; g.rect(x - 160, y, 320, 9, { fill: i % 2 ? '#ddd2b8' : '#cfc3a6', lw: 0, a }); }
    g.text(`${n}`, W / 2 + 260, 440, { size: 220, font: F.num, color: '#fff', a, weight: '600' });
    g.text('页', W / 2 + 470, 470, { size: 60, color: '#fff', a });
    g.text('1890 年底才登出来', W / 2 + 280, 620, { size: 40, color: COL.gold, a: a * prog(t, at('C25', '一八九零'), at('C25', '一八九零') + 0.4) });
  }
  function irony(lt, t) {
    env.t = t;
    const s = 12 + lt * 1.6, q = samp(A, s);
    const f = frameOf(A, s, [0, 1, 2], 4, 2);
    K.draw3d({ t, cam: orbitCam(f.c, f.R * 4.4 + 1.2, 0.5, 0.3 + 0.03 * lt), stars: starsOf(q), trails: trailsOf(A, s, 5, { a: 0.7 }), dust: { a: 1 }, exposure: 0.9 });
    dim(0.35);
    const a = fade(t, T('C26') - 0.2, TE('C26') + 0.6, 0.3, 0.5);
    motto(W / 2, H / 2 - 50, T('C26') + 0.6, a, 60);
    g.text('群星永不越出既定的边界', W / 2, H / 2 + 60, { size: 46, font: F.serif, weight: '600', color: COL.gold, a: a * prog(t, at('C26', '群星'), at('C26', '群星') + 0.5), spacing: 6 });
    const ir = prog(t, at('C26', '讽刺') - 0.2, at('C26', '讽刺') + 0.3);
    if (ir > 0) g.line(W / 2 - 330, H / 2 + 60, W / 2 + 330, H / 2 + 60, { color: COL.red, w: 4, a: a * ir });
  }

  // ================= 第四章 =================
  let SUND = null;
  async function sund2(lt, t) {
    SUND = SUND || (await img('/assets/photos/sundman.jpg'));
    K.bg(t, { sky: 0.6 });
    g.photo(SUND, 600, 470, 560, { name: '卡尔·松德曼', years: '1873 – 1949', note: '芬兰数学家', s: 1 + lt * 0.004, rot: -0.02, a: prog(lt, 0, 0.5) });
    year('1912', 1320, 360, fade(t, at('D01', '一九一二') - 0.1, TE('D02') + 0.3, 0.3, 0.3));
    const y = prog(t, T('D02'), T('D02') + 0.3);
    if (y > 0) {
      ctx.save(); ctx.globalAlpha *= y; ctx.translate(1320, 560); ctx.rotate(-0.08); ctx.scale(lerp(1.6, 1, easeOut(y)), lerp(1.6, 1, easeOut(y)));
      ctx.strokeStyle = COL.gold; ctx.lineWidth = 4; ctx.strokeRect(-150, -50, 300, 100);
      ctx.fillStyle = COL.gold; ctx.font = `700 60px ${F.serif}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('写出来了', 0, 4);
      ctx.restore();
    }
  }
  // 级数：项数越多，近似越准（用真实轨迹的切比雪夫部分和做示意）
  const SER = (() => {
    const N = 40, S0 = 0, S1 = 9, M = 256;
    const xs = [], ys = [];
    for (let k = 0; k < M; k++) { const th = (Math.PI * (k + 0.5)) / M, u = Math.cos(th); const q = samp(A, S0 + (u + 1) / 2 * (S1 - S0)); xs.push(q[0]); ys.push(q[1]); }
    const cx = [], cy = [];
    for (let n = 0; n < N; n++) {
      let sx = 0, sy = 0;
      for (let k = 0; k < M; k++) { const c = Math.cos((Math.PI * n * (k + 0.5)) / M); sx += xs[k] * c; sy += ys[k] * c; }
      cx.push((2 / M) * sx * (n === 0 ? 0.5 : 1)); cy.push((2 / M) * sy * (n === 0 ? 0.5 : 1));
    }
    const ev = (c, u, nT) => { let s = c[0]; if (nT > 1) s += c[1] * u; let t0 = 1, t1 = u; for (let n = 2; n < nT; n++) { const tn = 2 * u * t1 - t0; s += c[n] * tn; t0 = t1; t1 = tn; } return s; };
    return { S0, S1, curve: (nT, nPts = 400) => { const pts = new Float32Array(nPts * 3); for (let i = 0; i < nPts; i++) { const u = -1 + (2 * i) / (nPts - 1); pts.set([ev(cx, u, nT), 0, -ev(cy, u, nT)], 3 * i); } return pts; } };
  })();
  function series(lt, t) {
    const nT = Math.max(1, Math.min(40, Math.floor(1 + 3.2 * Math.max(0, t - at('D03', '无穷级数')))));
    const truth = trailsOf(A, SER.S1, SER.S1, { idx: [0], a: 0.35, col: '#ffffff', n: 400 })[0];
    truth.fade = 0;
    const cam = orbitCam([0, 0, 0.2], 3.4, 1.05, 0.3);
    K.draw3d({ t, cam, stars: [], trails: [truth, { pts: SER.curve(nT), col: TINT.red, a: 0.95, w: 2.2, fade: 0 }], dust: { a: 0.3 } });
    const a = fade(t, T('D03'), TE('D04') + 0.2, 0.3, 0.3);
    const terms = ['a₀', 'a₁τ', 'a₂τ²', 'a₃τ³', 'a₄τ⁴', 'a₅τ⁵', 'a₆τ⁶', 'a₇τ⁷', 'a₈τ⁸', 'a₉τ⁹'];
    let s = 'x = ';
    for (let i = 0; i < Math.min(terms.length, nT); i++) s += (i ? ' + ' : '') + terms[i];
    s += ' + …';
    g.text(s, 120, 150, { size: 46, font: F.latin, color: '#fff', a, align: 'left', weight: '400' });
    g.text(`已加 ${nT} 项`, W - 120, 230, { size: 30, color: COL.hud, a, align: 'right' });
    g.text('白线：真实轨道    红线：级数加到这一项的结果', W - 120, H - 170, { size: 22, color: COL.grey, a, align: 'right', weight: '400' });
    g.text('示意', 120, H - 170, { size: 22, color: COL.grey, a, align: 'left', weight: '400' });
  }
  // 三颗星同时撞到一点：被排除
  function collide(lt, t) {
    const t0 = at('D04', '同时撞到一起') - 1.0;
    const u = easeIn(clamp((t - t0) / 1.0));
    const P = [90, 210, 330].map((d) => { const r = (1 - u) * 0.9 + 0.001; const a = (d * Math.PI) / 180 + u * 1.5; return [r * Math.cos(a), 0, -r * Math.sin(a)]; });
    const proj = K.draw3d({ t, cam: orbitCam([0, 0, 0], 4.2, 0.9, 0.3 + 0.02 * lt), stars: P.map((p, j) => ({ p, col: SIMCOL[j], r: 0.05 })), dust: { a: 0.6 } });
    const x = prog(t, at('D04', '同时撞到一起') + 0.1, at('D04', '同时撞到一起') + 0.4);
    const [cx, cy] = proj([0, 0, 0]);
    if (x > 0) { g.line(cx - 130 * x, cy - 130 * x, cx + 130 * x, cy + 130 * x, { color: COL.red, w: 8 }); g.line(cx + 130 * x, cy - 130 * x, cx - 130 * x, cy + 130 * x, { color: COL.red, w: 8 }); }
    g.text('三颗同时撞到一起 → 排除', W / 2, 150, { size: 38, color: COL.hud, a: prog(t, at('D04', '同时撞到一起'), at('D04', '同时撞到一起') + 0.4) });
    const ok = prog(t, at('D04', '多远的将来') - 0.2, at('D04', '多远的将来') + 0.4);
    if (ok > 0) g.text('其余情况：算到多远的将来都管用 ✓', W / 2, 210, { size: 34, color: COL.gold, a: ok });
  }
  function hasSol(lt, t) {
    K.bg(t, { sky: 0.6 });
    const a = fade(t, T('D05') - 0.1, TE('D05') + 0.4, 0.3, 0.3);
    g.text('从这个意义上说', W / 2, H / 2 - 120, { size: 38, color: COL.grey, a, weight: '400' });
    g.text('三体问题  有解', W / 2, H / 2, { size: 110, font: F.serif, weight: '700', color: COL.gold, a: a * prog(t, at('D05', '有解') - 0.2, at('D05', '有解') + 0.3), spacing: 8 });
  }
  // 收得太慢 → 10 的 800 万次方
  function slow(lt, t) {
    K.bg(t, { sky: 0.5 });
    const a = fade(t, T('D06') - 0.1, T('D09') + 0.1, 0.3, 0.3);
    g.text('那为什么还说无解？', W / 2, 180, { size: 44, color: '#fff', a: a * fade(t, T('D06'), T('D07') + 0.2, 0.2, 0.3) });
    const s = fade(t, T('D07'), at('D08', '十的八百万') - 0.1, 0.2, 0.3);
    if (s > 0) {
      const terms = Math.floor(Math.pow(10, clamp((t - T('D07')) / 4.5) * 7));
      g.text('收得太慢', W / 2, 180, { size: 56, font: F.serif, weight: '700', color: COL.red, a: s });
      g.text(`已加 ${terms.toLocaleString('en-US')} 项`, W / 2, 420, { size: 54, font: F.mono, color: '#fff', a: s, weight: '400' });
      const acc = 0.03 + 0.04 * clamp((t - T('D07')) / 6);
      g.rect(W / 2 - 500, 520, 1000, 36, { color: COL.hud, lw: 1.2, a: s });
      g.rect(W / 2 - 500, 520, 1000 * acc, 36, { fill: COL.hud, lw: 0, a: s });
      g.text('离天文学家要的精度', W / 2 - 500, 600, { size: 28, color: COL.grey, a: s, align: 'left', weight: '400' });
    }
    const k = at('D08', '十的八百万') - 0.05;
    const big = prog(t, k, k + 0.25) * fade(t, 0, T('D09') + 0.1, 0, 0.3);
    if (big > 0) {
      const sc = lerp(1.5, 1, easeOut(prog(t, k, k + 0.5)));
      ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(sc, sc);
      g.text('10', -120, 30, { size: 220, font: F.num, color: '#fff', a: big, weight: '600' });
      g.text('8,000,000', 220, -70, { size: 110, font: F.num, color: COL.gold, a: big, weight: '600' });
      ctx.restore();
      g.text('项', W / 2 + 560, H / 2 + 60, { size: 80, color: '#fff', a: big });
    }
  }
  // 数字瀑布：1 后面 800 万个 0 → 十几本厚书 → 和宇宙原子数比
  const zcv = (() => {
    const c = document.createElement('canvas'); c.width = 1920; c.height = 1080;
    const x = c.getContext('2d'); x.fillStyle = '#e8e4da'; x.font = `400 14px ${F.mono}`;
    for (let y = 0; y < 1080; y += 15) { let s = ''; for (let i = 0; i < 230; i++) s += '0'; x.fillText(s, 0, y + 12); }
    return c;
  })();
  function waterfall(lt, t) {
    K.bg(t, { sky: 0.4, exposure: 0.6 });
    const a = fade(t, T('D10') - 0.4, TE('D11') + 0.5, 0.3, 0.5);
    const z = prog(t, at('D10', '八百万个零') - 0.2, at('D10', '十几本') + 0.4);
    const k = lerp(1, 0.12, easeInOut(z));
    const fall = (t * 900) % 15;
    ctx.save(); ctx.globalAlpha *= a;
    ctx.translate(W / 2, H / 2); ctx.scale(k, k);
    const cols = Math.ceil(1 / k) + 1;
    for (let i = -cols; i <= cols; i++) for (let j = -cols; j <= cols; j++) ctx.drawImage(zcv, i * 1920 - 960, j * 1080 - 540 + fall);
    ctx.restore();
    g.text('1', W / 2 - 960 * k - 30, H / 2 - 540 * k + 10, { size: 60 * Math.max(0.5, k), font: F.mono, color: COL.gold, a: a * (1 - prog(t, at('D10', '十几本') - 0.6, at('D10', '十几本'))), weight: '700' });
    const books = prog(t, at('D10', '十几本') - 0.3, at('D10', '十几本') + 0.4) * (1 - prog(t, T('D11') - 0.2, T('D11') + 0.3));
    if (books > 0) {
      dim(books * 0.94);
      for (let i = 0; i < 13; i++) {
        const x = W / 2 - 13 * 46 + i * 92, h = 420 + (i % 3) * 18;
        g.rect(x, 700 - h, 78, h, { fill: ['#5a3a2a', '#3a4a5a', '#4a3a5a'][i % 3], color: COL.gold, lw: 1.2, a: books * prog(t, at('D10', '十几本') - 0.3 + i * 0.03, at('D10', '十几本') + i * 0.03) });
        g.text('000…', x + 39, 700 - h / 2, { size: 18, font: F.mono, color: COL.gold, a: books, weight: '400' });
      }
      g.text('光是把这个数写出来，就要十几本厚书', W / 2, 820, { size: 38, color: '#fff', a: books });
    }
    const at2 = prog(t, T('D11') - 0.2, T('D11') + 0.4) * fade(t, 0, TE('D11') + 0.5, 0, 0.5);
    if (at2 > 0) {
      dim(at2 * 0.85);
      g.text('写出来要多少位数字', W / 2, 220, { size: 38, color: COL.grey, a: at2, weight: '400' });
      g.rect(160, 360, 1600, 70, { fill: COL.gold, lw: 0, a: at2 * prog(t, T('D11'), T('D11') + 0.6) });
      g.text('10⁸⁰⁰⁰⁰⁰⁰ 项：8,000,001 位', 160, 320, { size: 34, color: COL.gold, a: at2, align: 'left' });
      const ap = prog(t, at('D11', '原子') - 0.2, at('D11', '十的八十') + 0.3);
      g.rect(160, 600, Math.max(2, 1600 * 81 / 8000001), 70, { fill: '#9fd0ff', lw: 0, a: at2 * ap });
      g.text('宇宙里的原子 10⁸⁰ 个：81 位', 160, 560, { size: 34, color: '#9fd0ff', a: at2 * ap, align: 'left' });
      g.tag(162, 635, '在这里', { p: prog(t, at('D11', '十的八十'), at('D11', '十的八十') + 0.6), a: at2, r: 20, dx: 90, dy: 90, size: 28 });
    }
  }
  function wang(lt, t) {
    K.bg(t, { sky: 0.6 });
    const a = fade(t, T('D12') - 0.2, TE('D12') + 0.3, 0.3, 0.4);
    K.nameCard('王秋东', '1991', '当时在美国读研究生', 520, H / 2 - 20, { a, p: prog(t, at('D12', '王秋东') - 0.3, at('D12', '王秋东') + 0.8) });
    const p = prog(t, at('D12', '任意多个') - 0.2, at('D12', '任意多个') + 0.5);
    g.text('松德曼的方法', 1360, H / 2 - 60, { size: 40, color: '#fff', a: a * prog(t, at('D12', '松德曼'), at('D12', '松德曼') + 0.4) });
    g.text('3 个天体  →  任意多个天体', 1360, H / 2 + 20, { size: 44, color: COL.gold, a: a * p });
  }
  function diacu(lt, t) {
    K.bg(t, { sky: 0.6 });
    const a = fade(t, T('D13') - 0.2, TE('D13') + 0.3, 0.3, 0.4);
    const n1 = fade(t, T('D13'), at('D13', '迪亚库') - 0.2, 0.3, 0.3);
    g.text('数学上，这是很漂亮的工作', W / 2, H / 2 - 20, { size: 60, font: F.serif, weight: '700', color: COL.gold, a: a * n1 });
    const n2 = fade(t, at('D13', '迪亚库') - 0.3, TE('D13') + 0.3, 0.3, 0.3);
    g.text('弗洛林·迪亚库', W / 2, 300, { size: 40, color: '#fff', a: a * n2 });
    K.quote(['“有了这个解，我们对这些系统的了解', '一点也没变多。”'], '— 天体力学学者，评价王秋东的解（大意）', W / 2, 440, { a: a * prog(t, at('D13', '有了这个解') - 0.3, at('D13', '有了这个解')), size: 52, p: prog(t, at('D13', '有了这个解') - 0.3, TE('D13') - 1) });
  }
  // 结论：左边二体椭圆 + 短公式，右边三体乱轨 + 望不到头的级数
  function verdict(lt, t) {
    const a = fade(t, T('D14') - 0.3, M('pre_ch5') + 1.0, 0.4, 0.6);
    const ph = (t - T('D14')) / 3;
    const pe = ellipse(1.2, 0.5, ph);
    const n = 300, pts = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) pts.set(ellipse(1.2, 0.5, i / (n - 1)), 3 * i);
    K.draw3d({ t, cam: orbitCam([-0.6, 0, 0], 5.6, 0.8, 0.3), stars: [{ p: [0, 0, 0], col: SUN, r: 0.08, glow: 0.4, glowRef: 5 }], planets: [{ type: 'earth', p: pe, r: 0.045, light: [0, 0, 0] }], trails: [{ pts, col: '#8fc4ff', a: 0.7, w: 1.6, fade: 0 }], size: [W / 2, H], vig: 0.6 }, 0);
    const s = 14 + lt * 1.4, q = samp(A, s), f = frameOf(A, s, [0, 1, 2], 4, 2);
    K.draw3d({ t, cam: orbitCam(f.c, f.R * 4.4 + 1.2, 0.5, 0.4 + 0.02 * lt, { fov: 34 }), stars: starsOf(q), trails: trailsOf(A, s, 5, { a: 0.75 }), dust: { a: 0.8 }, size: [W / 2, H], vig: 0.6 }, W / 2);
    g.line(W / 2, 0, W / 2, H, { color: COL.hud, w: 1.2, a: 0.7 });
    g.text('两个天体', W / 4, 120, { size: 40, color: '#fff', a });
    g.text('r = p / (1 + e·cosθ)', W / 4, 200, { size: 44, font: F.latin, color: COL.gold, a, weight: '400' });
    g.text('简单 · 能直接用', W / 4, 270, { size: 30, color: COL.hud, a, weight: '400' });
    g.text('三个天体', W * 0.75, 120, { size: 40, color: '#fff', a });
    g.text('a₀ + a₁τ + a₂τ² + a₃τ³ + …', W * 0.75, 200, { size: 40, font: F.latin, color: '#c8c8cc', a, weight: '400' });
    g.text('要加 10⁸⁰⁰⁰⁰⁰⁰ 项', W * 0.75, 270, { size: 30, color: COL.red, a, weight: '400' });
    const fin = prog(t, T('D15') - 0.1, T('D15') + 0.4) * a;
    if (fin > 0) { g.rect(W / 2 - 360, H / 2 - 70, 720, 140, { fill: 'rgba(2,6,12,0.85)', color: COL.gold, lw: 1.2, a: fin }); g.text('解是有的，只是没法用', W / 2, H / 2, { size: 54, font: F.serif, weight: '700', color: '#f4efe4', a: fin }); }
  }

  return [
    { a: M('ch3_end') - 0.2, b: T('C03') + 0.1, fi: 0.4, fo: 0.4, draw: oscar },
    { a: T('C03') - 0.2, b: T('C04') + 0.1, fi: 0.4, fo: 0.3, draw: solar },
    { a: T('C04') - 0.2, b: T('C07') + 0.1, fi: 0.3, fo: 0.3, draw: prize },
    { a: T('C07') - 0.2, b: T('C09') + 0.1, fi: 0.3, fo: 0.3, draw: poincare },
    { a: T('C09') - 0.2, b: T('C10') + 0.1, fi: 0.3, fo: 0.3, draw: restricted },
    { a: T('C10') - 0.2, b: T('C11') + 0.1, fi: 0.3, fo: 0.3, draw: weier },
    { a: T('C11') - 0.2, b: T('C13') + 0.1, fi: 0.3, fo: 0.3, draw: award },
    { a: T('C13') - 0.2, b: T('C14') + 0.0, fi: 0.3, fo: 0.15, draw: press },
    { a: T('C14') - 0.15, b: T('C16') + 0.1, fi: 0.15, fo: 0.2, draw: errorPage },
    { a: T('C16') - 0.1, b: T('C17') + 0.1, fi: 0.15, fo: 0.25, draw: telegram },
    { a: T('C17') - 0.2, b: T('C18') + 0.1, fi: 0.25, fo: 0.3, draw: letter },
    { a: T('C18') - 0.2, b: T('C20') + 0.1, fi: 0.3, fo: 0.3, draw: recall },
    { a: T('C20') - 0.2, b: T('C21') + 0.2, fi: 0.4, fo: 0.4, draw: destroyed },
    { a: T('C21') - 0.2, b: T('C23') + 0.1, fi: 0.4, fo: 0.2, draw: web },
    { a: T('C23') - 0.1, b: T('C24') + 0.1, fi: 0.2, fo: 0.3, draw: reprise },
    { a: T('C24') - 0.2, b: T('C25') + 0.1, fi: 0.3, fo: 0.4, draw: web },
    { a: T('C25') - 0.2, b: T('C26') + 0.1, fi: 0.3, fo: 0.3, draw: pages },
    { a: T('C26') - 0.2, b: M('pre_ch4') + 0.6, fi: 0.3, fo: 0.6, draw: irony },
    { a: M('ch4_end') - 0.2, b: T('D03') + 0.1, fi: 0.4, fo: 0.3, draw: sund2 },
    { a: T('D03') - 0.2, b: at('D04', '同时撞到一起') - 1.2, fi: 0.3, fo: 0.3, draw: series },
    { a: at('D04', '同时撞到一起') - 1.4, b: T('D05') + 0.1, fi: 0.3, fo: 0.3, draw: collide },
    { a: T('D05') - 0.2, b: T('D06') + 0.1, fi: 0.3, fo: 0.3, draw: hasSol },
    { a: T('D06') - 0.2, b: T('D10') - 0.2, fi: 0.3, fo: 0.2, draw: slow },
    { a: T('D10') - 0.4, b: T('D12') + 0.1, fi: 0.2, fo: 0.4, draw: waterfall },
    { a: T('D12') - 0.2, b: T('D13') + 0.1, fi: 0.3, fo: 0.3, draw: wang },
    { a: T('D13') - 0.2, b: T('D14') + 0.0, fi: 0.3, fo: 0.3, draw: diacu },
    { a: T('D14') - 0.3, b: M('pre_ch5') + 1.0, fi: 0.4, fo: 0.6, draw: verdict },
  ];
}
