// 《一个数字：4.8%》第二章到片尾。依赖 lib_b.js 和 b.html 里的 S / E / Wd / M / scriptCard / dotGrid 等。
const C80 = { bg: '#e3e8e1', ink: '#22302d', teal: '#3d6b63', dark: '#16201f' };
const CC = { bg: '#121820', fg: '#e8eef3', mute: 'rgba(200,215,230,0.55)' };

function laterShots() {
  const m = M();
  const ch = (k) => m[k] + 2.5;
  return [
    { a: m.ch2, b: ch('ch2'), f: (t, lt) => chapterCard(t, lt, { no: '二', big: '3–5', unit: '倍', title: '八十年代的预选', bg: C80.dark, fg: '#e6efe9', accent: '#8fc1b5' }), nosub: true },
    { a: ch('ch2'), b: S('B06') - 0.2, f: shScissor, light: true },
    { a: S('B06') - 0.2, b: m.ch3, f: shFunnel, light: true },
    { a: m.ch3, b: ch('ch3'), f: (t, lt) => chapterCard(t, lt, { no: '三', big: '+47%', title: '1999 年扩招', bg: CC.bg, fg: CC.fg, accent: '#e8eef3', bars: true }), nosub: true },
    { a: ch('ch3'), b: S('C03') - 0.2, f: shFactory },
    { a: S('C03') - 0.2, b: S('C06') - 0.2, f: shProposal },
    { a: S('C06') - 0.2, b: S('C08') - 0.2, f: shRatio, light: true },
    { a: S('C08') - 0.2, b: S('C11') - 0.2, f: shReasons },
    { a: S('C11') - 0.2, b: S('C13') - 0.2, f: (t, lt, sh) => scriptCard(t, lt, sh, 2), ask: Wd('C11', '部长陈至立问他'), answer: Wd('C12', '说最多五十万'), strike: Wd('C12', '部长同意了') },
    { a: S('C13') - 0.2, b: S('C14') - 0.2, f: shJump },
    { a: S('C14') - 0.2, b: S('C15') - 0.2, f: shNoStop },
    { a: S('C15') - 0.2, b: S('C17') - 0.2, f: shTangQuote },
    { a: S('C17') - 0.2, b: S('C18') - 0.2, f: (t, lt, sh) => aiShot(t, lt, sh, IMG.dorm, 0.5, 0.55, 1.0, 1.1, 'rgba(120,150,190,0.05)'), tag: '资料：中国青年报 2000-09-14' },
    { a: S('C18') - 0.2, b: Wd('C19', '偏偏又碰上非典'), f: shGrads },
    { a: Wd('C19', '偏偏又碰上非典'), b: S('C20') - 0.2, f: (t, lt, sh) => aiShot(t, lt, sh, IMG.jobfair, 0.5, 0.5, 1.08, 1.0, 'rgba(120,150,190,0.06)') },
    { a: S('C20') - 0.2, b: S('C21') - 1.3, f: shGrads },
    { a: S('C21') - 1.3, b: S('C22') - 0.3, f: shEditorial },
    { a: S('C22') - 0.3, b: S('C25') - 0.2, f: shBands, light: true },
    { a: S('C25') - 0.2, b: S('C27') - 0.2, f: shReserve },
    { a: S('C27') - 0.2, b: m.ch4, f: shNote, light: true },
    { a: m.ch4, b: ch('ch4'), f: (t, lt) => chapterCard(t, lt, { no: '四', big: '90%', title: '90% 是怎么算的', bg: '#1f2328', fg: '#f2efe7', accent: C.red }), nosub: true },
    { a: ch('ch4'), b: S('D06') - 0.2, f: shFormula, light: true },
    { a: S('D06') - 0.2, b: S('D07') - 0.2, f: shHunan, light: true },
    { a: S('D07') - 0.2, b: S('D09') - 0.2, f: shNumer, light: true },
    { a: S('D09') - 0.2, b: S('D11') - 0.2, f: shTwoQ, light: true },
    { a: S('D11') - 0.2, b: S('D12') - 0.2, f: shTip, light: true },
    { a: S('D12') - 0.2, b: m.ch5, f: shAsk2, nosub: true },
    { a: m.ch5, b: ch('ch5'), f: (t, lt) => chapterCard(t, lt, { no: '五', big: '×1.6', title: '清华扩了多少', bg: '#1f2328', fg: '#f2efe7', accent: '#f2efe7' }), nosub: true },
    { a: ch('ch5'), b: S('E02') - 0.2, f: shNoteBack, light: true },
    { a: S('E02') - 0.2, b: S('E06') - 0.2, f: shGrowthCmp, light: true },
    { a: S('E06') - 0.2, b: S('E08'), f: shC9, light: true },
    { a: S('E08'), b: S('E10') - 0.2, f: shPlain, light: true },
    { a: S('E10') - 0.2, b: m.ending, f: shBeijing, light: true },
    { a: m.ending, b: S('F02') - 0.2, f: shNotice },
    { a: S('F02') - 0.2, b: S('F03') - 0.2, f: (t, lt, sh) => aiShot(t, lt, sh, IMG.gate, 0.5, 0.5, 1.0, 1.08, null, (t, lt) => {
      text('今年 1270 万人毕业', 120, 860, { size: 64, weight: 700, color: '#fff', alpha: ap(lt, 0.4) });
      text('不包分配', 124, 920, { size: 34, color: 'rgba(255,255,255,0.8)', alpha: ap(t, Wd('F02', '早就不包分配了')) });
    }) },
    { a: S('F03') - 0.2, b: S('F04') - 0.2, f: shFew },
    { a: S('F04') - 0.2, b: S('F05') - 1.2, f: shNarrow, light: true },
    { a: S('F05') - 1.2, b: TL.duration, f: shFinalQ, nosub: true },
  ];
}

// ---------- 通用 ----------
function chapterCard(t, lt, o) {
  ctx.fillStyle = o.bg; ctx.fillRect(0, 0, W, H);
  if (o.bars) {
    const yrs = [60.9, 62, 75.4, 92.4, 90, 92.6, 96.6, 100, 108, 159.7, 221, 268, 320];
    yrs.forEach((v, i) => {
      const h = v * 1.9 * easeOut(clamp(prog(lt, 0.2, 1.4) * 1.4 - i * 0.04)), x = 1010 + i * 62;
      ctx.fillStyle = i === 9 ? '#e8eef3' : 'rgba(200,215,230,0.25)'; ctx.fillRect(x, 900 - h, 44, h);
    });
  }
  const k = ap(lt, 0.1, 0.5), k2 = ap(lt, 0.4, 0.5);
  text(`第 ${o.no} 章`, 180, 300, { size: 32, color: o.fg, spacing: 6, alpha: 0.7 * k });
  text(o.big, 170, 560, { size: 300, font: F.num, color: o.fg, alpha: k });
  if (o.unit) text(o.unit, 190 + measure(o.big, 300, F.num), 560, { size: 130, weight: 700, font: F.serif, color: o.fg, alpha: k });
  ctx.fillStyle = o.accent; ctx.globalAlpha = k2; ctx.fillRect(184, 610, 120 * k2, 6); ctx.globalAlpha = 1;
  text(o.title, 180, 712, { size: 78, weight: 700, font: F.serif, color: o.fg, alpha: k2 });
  grain(t, 0.08);
  black(1 - clamp(lt / 0.12));
}
function aiShot(t, lt, sh, img, fx, fy, z0, z1, tint, over) {
  cover(img, lerp(z0, z1, easeIO(prog(lt, 0, sh.b - sh.a))), fx, fy);
  grade(tint, 0.45);
  over && over(t, lt);
  grain(t, 0.08);
  sourceTag('示意画面 · AI 生成' + (sh.tag ? ' · ' + sh.tag : ''), 'rgba(255,255,255,0.6)');
}
function quoteCard(x, y, w, h, rot, lines, who, { size = 52, tex = TEX.paperCool, ink = C.coolInk } = {}) {
  paper(tex, x, y, w, h, rot, (pw, ph) => {
    lines.forEach((s, i) => text(s, pw / 2, 120 + i * (size * 1.5), { size, weight: 700, font: F.serif, color: ink, align: 'center' }));
    if (who) text(who, pw - 60, ph - 50, { size: 30, font: F.serif, color: '#6b7680', align: 'right' });
  }, { shadow: 0.55 });
}

// ---------- 第二章 ----------
function shScissor(t, lt) {
  ctx.fillStyle = C80.bg; ctx.fillRect(0, 0, W, H);
  const X = (y) => 260 + (y - 1977) / 8 * 1400, base = 820, top = 200;
  const R = (v) => base - v / 40 * (base - top), P = (v) => base - v / 600 * (base - top);
  const k = ap(lt, 0, 0.4);
  ctx.save(); ctx.globalAlpha = k; ctx.fillStyle = 'rgba(34,48,45,0.3)'; ctx.fillRect(260, base, 1400, 2);
  for (let y = 1977; y <= 1985; y++) text(String(y), X(y), base + 44, { size: 26, font: F.num, color: '#6b7a76', align: 'center' });
  ctx.restore();
  text('录取率', 260, 160, { size: 34, weight: 700, color: '#a0561c', alpha: k });
  text('参加高考的人数', 1660, 160, { size: 34, weight: 700, color: C80.ink, align: 'right', alpha: k });
  const rate = [[1977, 4.8, 0], [1980, 8, Wd('B02', '一九八零年')], [1981, 11, Wd('B02', '一九八一年')], [1983, 23, Wd('B02', '一九八三年')], [1985, 35, Wd('B02', '一九八五年')]];
  const ppl = [[1977, 570, S('B03')], [1980, 333, Wd('B03', '一九八零年三百')], [1981, 259, Wd('B03', '一九八一年二百')], [1983, 167, Wd('B03', '一九八三年只有')]];
  const series = (pts, Y, col, lab) => {
    ctx.save(); ctx.strokeStyle = col; ctx.lineWidth = 6; ctx.lineJoin = 'round'; ctx.beginPath();
    let started = false;
    pts.forEach(([yr, v, tt], i) => {
      if (t < tt) return;
      let x = X(yr), y = Y(v);
      if (i > 0) { const [y0, v0] = pts[i - 1], u = ap(t, tt, 0.35); x = lerp(X(y0), x, u); y = lerp(Y(v0), y, u); }
      started ? ctx.lineTo(x, y) : ctx.moveTo(x, y); started = true;
    });
    ctx.stroke(); ctx.restore();
    pts.forEach(([yr, v, tt]) => {
      const a = ap(t, tt + 0.25, 0.3); if (a <= 0) return;
      ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = col; ctx.beginPath(); ctx.arc(X(yr), Y(v), 10, 0, Math.PI * 2); ctx.fill(); ctx.restore();
      text(lab(v), X(yr), Y(v) - 24, { size: 32, font: F.num, color: col, align: 'center', alpha: a });
    });
  };
  series(rate, R, '#a0561c', (v) => v + '%');
  series(ppl, P, C80.ink, (v) => v + ' 万');
  const t4 = S('B04');
  if (t > t4) text('前几年积压的考生陆续考完了', X(1978.5), P(470) - 10, { size: 32, font: F.hand, color: C80.teal, alpha: ap(t, t4 + 0.3) });
  const t5 = S('B05');
  if (t > t5) text('另一部分原因？', X(1983) + 20, P(240), { size: 40, font: F.hand, color: C.red, alpha: ap(t, t5) });
  sourceTag('资料：教育部、中国教育统计年鉴', 'rgba(34,48,45,0.5)');
}

function shFunnel(t, lt) {
  ctx.fillStyle = C80.bg; ctx.fillRect(0, 0, W, H);
  const x0 = 260, BW = 1100, k = ap(lt, 0, 0.4);
  const bar = (x, y, w, col, lab, a) => {
    if (a <= 0) return;
    ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = col; ctx.fillRect(x, y, w, 90); ctx.restore();
    text(lab, x + w / 2, y + 58, { size: 34, weight: 700, color: '#fff', align: 'center', alpha: a });
  };
  bar(x0, 200, BW, '#7d8b87', '想考大学的高中生', k);
  const tc = Wd('B06', '先筛一轮'), pc = ap(t, tc, 0.6), fr = 0.45, wIn = BW * fr;
  // 被预选刷掉的一块：红色斜线，往右错开
  if (pc > 0) {
    const xr = x0 + wIn + 60 * pc, w = BW * (1 - fr);
    ctx.save(); ctx.globalAlpha = pc; ctx.fillStyle = 'rgba(210,65,42,0.12)'; ctx.fillRect(xr, 330, w, 90);
    ctx.fillStyle = hatch('rgba(210,65,42,0.85)', 10, 3); ctx.fillRect(xr, 330, w, 90);
    ctx.strokeStyle = C.red; ctx.lineWidth = 3; ctx.strokeRect(xr, 330, w, 90); ctx.restore();
    text('预选没挑上', xr + w / 2, 388, { size: 34, weight: 700, color: C.red, align: 'center', alpha: pc });
    bar(x0, 330, wIn, C80.teal, '进考场', pc);
    bar(x0, 460, wIn / 4, '#a0561c', '录取', ap(t, tc + 0.8, 0.4));
    const t7 = S('B07');
    if (t > t7) {
      text('连考场都进不去，', xr + 20, 480, { size: 34, font: F.hand, color: C.red, alpha: ap(t, t7 + 0.2) });
      text('统计的“参加高考人数”里也没有他们', xr + 20, 528, { size: 34, font: F.hand, color: C.red, alpha: ap(t, Wd('B07', '也就没有他们') - 0.6) });
    }
  }
  const tq = Math.max(Wd('B06', '三到五倍'), tc + 0.9);
  if (t > tq) text('进考场的 ≈ 名额的 3–5 倍', x0 + wIn / 4 + 30, 518, { size: 30, font: F.hand, color: C80.teal, alpha: ap(t, tq) });
  const t8 = S('B08');
  if (t > t8) {
    const k8 = ap(t, t8, 0.4);
    text('录取率 ＝ 录取人数 ÷ 进了考场的人', 260, 760, { size: 48, weight: 700, color: C80.ink, alpha: k8 });
    const xa = 260 + measure('录取率 ＝ 录取人数 ÷ ', 48, F.sans, 700), wa = measure('进了考场的人', 48, F.sans, 700);
    handEllipse(xa + wa / 2, 742, wa / 2 + 24, 44, t, ap(t, Wd('B08', '分母里少了一大块人'), 0.6), { color: C.red, lw: 4.5, seed: 201 });
  }
  const t9 = S('B09');
  if (t > t9) text('这种事后面还会遇到一次', 260, 880, { size: 40, font: F.hand, color: C.red, alpha: ap(t, t9 + 0.2) });
  sourceTag('示意图，比例不代表实际人数 · 资料：国务院批转教育部 1980 年招生工作会议报告', 'rgba(34,48,45,0.5)');
}

// ---------- 第三章 ----------
function shFactory(t, lt, sh) {
  aiShot(t, lt, sh, IMG.factory, 0.5, 0.45, 1.0, 1.08, 'rgba(120,150,190,0.08)', () => {
    text('1998', 120, 260, { size: 150, font: F.num, color: '#eef2f5', alpha: ap(lt, 0.2) });
    const tags = [['亚洲金融危机', '亚洲金融危机'], ['国企改革 · 工人下岗', '国企改革'], ['经济增长目标 8%', '经济增长百分之八']];
    tags.forEach(([s, w], i) => {
      const a = ap(t, Wd('C02', w) - 0.1, 0.35);
      if (a <= 0) return;
      ctx.save(); ctx.globalAlpha = a * 0.85; ctx.fillStyle = 'rgba(10,14,20,0.7)';
      const tw = measure(s, 36, F.sans, 700) + 40; ctx.fillRect(120, 330 + i * 76, tw, 58); ctx.restore();
      text(s, 140, 372 + i * 76, { size: 36, weight: 700, color: '#eef2f5', alpha: a });
    });
  });
}

function shProposal(t, lt, sh) {
  ctx.drawImage(TEX.deskCool, 0, 0);
  const z = lerp(1.0, 1.06, easeIO(prog(lt, 0, sh.b - sh.a)));
  camera(z, 960, 420, () => {
    paper(TEX.paperCool, 360, 90, 1200, 860, -0.01, (w) => {
      const title1 = '关于启动中国经济有效途径的思考', title2 = '——扩大高校招生一倍的建议';
      const t0 = Wd('C04', '题目叫') + 0.4, n1 = [...title1].length;
      const typedAll = typed(title1 + title2, t, t0, 9);
      const s1 = [...typedAll].slice(0, n1).join(''), s2 = [...typedAll].slice(n1).join('');
      text('建议书', w / 2, 120, { size: 30, font: F.mono, color: '#6b7680', align: 'center', spacing: 8 });
      text(s1, w / 2, 230, { size: 52, weight: 700, font: F.serif, color: C.coolInk, align: 'center' });
      text(s2, w / 2, 310, { size: 44, weight: 700, font: F.serif, color: C.coolInk, align: 'center' });
      const ka = ap(t, Wd('C03', '汤敏') - 0.2);
      text('汤敏　左小蕾', w / 2, 400, { size: 34, font: F.serif, color: '#4a535c', align: 'center', alpha: ka });
      text('1998 年 11 月', w / 2, 450, { size: 28, font: F.serif, color: '#6b7680', align: 'center', alpha: ka });
      const r = rng(41);
      for (let i = 0; i < 7; i++) { ctx.fillStyle = 'rgba(30,37,44,0.12)'; ctx.fillRect(120, 530 + i * 40, (w - 240) * (0.75 + r() * 0.25), 10); }
      const tc = S('C05'), key = '扩大高校招生一倍', x2 = w / 2 - measure(title2, 44, F.serif, 700) / 2 + measure('——', 44, F.serif, 700);
      handLine(x2 - 6, 330, x2 + measure(key, 44, F.serif, 700) + 6, 332, t, ap(t, tc - 0.1, 0.5), { color: C.pen, lw: 5, seed: 211, bow: 3 });
    });
  });
  grain(t, 0.07);
  sourceTag('画面为重新排版，正文以灰条示意，不是原件 · 标题据左小蕾访谈');
}

function shRatio(t, lt) {
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
  text('18–22 岁的人里，在上大学的比例', 200, 220, { size: 44, weight: 700, color: C.ink, alpha: ap(lt, 0, 0.4) });
  text('汤敏当年的算法，1998 年前后', 200, 275, { size: 28, color: '#777', alpha: ap(lt, 0.2, 0.4) });
  const rows = [['中国', 4, Wd('C07', '只有百分之四'), C.ink], ['菲律宾', 31, Wd('C07', '菲律宾'), '#9a9488'], ['泰国', 37, Wd('C07', '泰国'), '#9a9488']];
  rows.forEach(([n, v, tt, col], i) => {
    const y = 380 + i * 150, a = ap(t, tt - 0.1, 0.5);
    text(n, 200, y + 58, { size: 44, weight: 700, color: C.ink, alpha: a });
    ctx.fillStyle = col; ctx.fillRect(400, y, v * 32 * a, 80);
    text(v + '%', 420 + v * 32 * a, y + 60, { size: 56, font: F.num, color: col, alpha: a });
  });
  sourceTag('资料：汤敏接受《广州日报》采访（2007-08）；官方统计的 1998 年毛入学率为 9.8%，口径不同', 'rgba(31,35,40,0.5)');
}

function shReasons(t, lt) {
  ctx.drawImage(TEX.deskCool, 0, 0);
  paper(TEX.paperCool, 300, 120, 1320, 720, 0.008, (w) => {
    text('汤敏的理由', 90, 120, { size: 48, weight: 700, font: F.serif, color: C.coolInk });
    const items = [['上大学的人太少（4% 左右）', -1], ['让年轻人晚几年再进就业市场', S('C08') + 0.3], ['上大学要花钱，能拉动消费', S('C09')]];
    items.forEach(([s, tt], i) => {
      const y = 260 + i * 130, a = tt < 0 ? 0.5 : ap(t, tt, 0.4);
      text(`${i + 1}`, 110, y, { size: 56, font: F.num, color: C.pen, alpha: tt < 0 ? 0.5 : a });
      text(s, 180, y, { size: 44, font: F.serif, color: C.coolInk, alpha: a });
    });
    const tp = S('C10'), ka = ap(t, tp, 0.4);
    ctx.fillStyle = `rgba(30,37,44,${0.2 * ka})`; ctx.fillRect(90, 610, w - 180, 2);
    text('方案：3 年扩一倍', 90, 690, { size: 50, weight: 700, font: F.serif, color: C.coolInk, alpha: ka });
    const tq = Wd('C10', '很快被采纳了');
    handCheck(560, 668, 48, t, prog(t, tq, tq + 0.5), { color: C.pen, lw: 6, seed: 221 });
    text('很快被采纳', 640, 690, { size: 40, font: F.hand, color: C.pen, alpha: ap(t, tq + 0.4) });
  }, { shadow: 0.5 });
  grain(t, 0.07);
  sourceTag('资料：汤敏接受《广州日报》采访（2007-08）');
}

function shJump(t, lt) {
  ctx.fillStyle = CC.bg; ctx.fillRect(0, 0, W, H);
  const vals = [[1990, 60.9], [1991, 62], [1992, 75.4], [1993, 92.4], [1994, 90], [1995, 92.6], [1996, 96.6], [1997, 100], [1998, 108.4], [1999, 159.7]];
  vals.forEach(([y, v], i) => {
    const x = 900 + i * 90, last = y === 1999, g = last ? ap(t, Wd('C13', '涨了百分之四十七') - 0.5, 0.5) : ap(lt, i * 0.05, 0.3), h = v * 3.6 * g;
    ctx.fillStyle = last ? CC.fg : 'rgba(200,215,230,0.35)'; ctx.fillRect(x, 880 - h, 64, h);
    text(String(y), x + 32, 920, { size: 24, font: F.num, color: CC.mute, align: 'center', alpha: g });
  });
  const k = ap(t, Wd('C13', '涨了百分之四十七') - 0.2, 0.4);
  text('+47%', 160, 520, { size: 260, font: F.num, color: CC.fg, alpha: k });
  text('1999 年比上一年多招 51 万', 170, 590, { size: 34, color: CC.mute, alpha: k });
  text('1990–1998 年平均每年 +7.5% 左右', 170, 660, { size: 34, color: CC.mute, alpha: ap(t, Wd('C13', '在这之前')) });
  grain(t, 0.06);
  sourceTag('资料：《中国统计年鉴》、1999 年全国教育事业发展统计公报', 'rgba(200,215,230,0.4)');
}

function shNoStop(t, lt) {
  const items = [[2000, 220.6, Wd('C14', '两千年')], [2001, 268.3, Wd('C14', '两千零一年')], [2002, 320.5, Wd('C14', '两千零二年')]];
  let cur = items[0];
  items.forEach((it) => { if (t >= it[2] - 0.1) cur = it; });
  ctx.fillStyle = CC.bg; ctx.fillRect(0, 0, W, H);
  const k = ap(t, cur[2] - 0.1, 0.15);
  text(String(cur[0]), 960, 360, { size: 90, font: F.num, color: CC.mute, align: 'center', alpha: k });
  text(`${Math.round(cur[1])} 万`, 960, 640, { size: 280, font: F.num, color: CC.fg, align: 'center', alpha: k });
  text('全国普通高校本专科招生', 960, 730, { size: 30, color: CC.mute, align: 'center' });
  grain(t, 0.06);
  sourceTag('资料：历年全国教育事业发展统计公报', 'rgba(200,215,230,0.4)');
}

function shTangQuote(t, lt) {
  ctx.drawImage(TEX.deskCool, 0, 0);
  quoteCard(260, 150, 1400, 420, -0.01, ['“我的建议是 3 年扩一倍，', '结果是 6 年扩了超过 5 倍。”'], '—— 汤敏', { size: 56 });
  const t6 = S('C16');
  if (t > t6) {
    const a = ap(t, t6, 0.4), b = ap(t, Wd('C16', '到二零零五年') - 0.2, 0.5), wb = 120 * 504 / 108.4;
    text('建议书要的', 460, 690, { size: 32, color: 'rgba(232,238,243,0.8)', alpha: a });
    ctx.fillStyle = `rgba(200,215,230,${0.6 * a})`; ctx.fillRect(460, 710, 240 * a, 50);
    text('×2', 720, 750, { size: 48, font: F.num, color: CC.fg, alpha: a });
    text('2005 年实际招生 504 万（1998 年 108 万）', 460, 820, { size: 32, color: 'rgba(232,238,243,0.8)', alpha: b });
    ctx.fillStyle = `rgba(232,238,243,${b})`; ctx.fillRect(460, 840, wb * b, 50);
    text('×4.6', 480 + wb * b, 880, { size: 48, font: F.num, color: CC.fg, alpha: b });
  }
  grain(t, 0.07);
  sourceTag('引语：汤敏接受《广州日报》采访（2007-08）；招生数：全国教育事业发展统计公报');
}

function shGrads(t, lt) {
  ctx.fillStyle = CC.bg; ctx.fillRect(0, 0, W, H);
  const tg = Wd('C20', '还有一百多万人没找到工作'), p = ap(t, tg - 0.1, 0.8);
  const gx = 1060, gy = 170, cell = 66;
  for (let i = 0; i < 100; i++) {
    const [x, y] = gridCell(gx, gy, 10, cell, i);
    const gray = i >= 50 ? p : 0;
    ctx.save(); ctx.globalAlpha = ap(lt, 0, 0.4); person(x, y, 58, 'rgba(200,215,230,0.15)');
    ctx.globalAlpha *= 1 - gray; person(x, y, 58, CC.fg); ctx.restore();
  }
  text('2003', 160, 300, { size: 110, font: F.num, color: CC.mute, alpha: ap(lt, 0, 0.4) });
  text('212 万', 150, 520, { size: 220, font: F.num, color: CC.fg, alpha: ap(t, Wd('C19', '毕业生二百一十二万') - 0.1) });
  text('扩招后第一批本科生毕业 · 比上一年多 46%', 160, 590, { size: 30, color: CC.mute, alpha: ap(t, Wd('C19', '比上一年多了百分之四十六')) });
  if (p > 0) {
    text('7 月 17 日公布', 160, 700, { size: 40, weight: 700, color: CC.fg, alpha: p });
    text('100 多万人还没找到工作', 160, 760, { size: 40, color: CC.fg, alpha: p });
  }
  grain(t, 0.06);
  sourceTag('资料：中国青年报、教育部 · 1 个小人 ≈ 2 万人', 'rgba(200,215,230,0.4)');
}

function shEditorial(t, lt) {
  ctx.fillStyle = '#0d1116'; ctx.fillRect(0, 0, W, H);
  const p = easeOut(prog(lt, 0.2, 1.4));
  ctx.save(); ctx.globalAlpha = p;
  paper(TEX.paperNews, 330, 230 + 30 * (1 - p), 1260, 520, -0.008, (w) => {
    text('编者按', 80, 100, { size: 40, weight: 700, font: F.serif, color: '#2a241f' });
    text('《中国青年报》 · 2003 年 7 月 18 日', w - 80, 100, { size: 26, font: F.serif, color: '#6b5f50', align: 'right' });
    ctx.fillStyle = '#3a332c'; ctx.fillRect(80, 124, w - 160, 3);
    text('一直被称做“天之骄子”的大学生，', w / 2, 270, { size: 56, weight: 700, font: F.serif, color: '#2a241f', align: 'center' });
    text('什么时候成了社会的“负担”？', w / 2, 370, { size: 56, weight: 700, font: F.serif, color: '#2a241f', align: 'center' });
  }, { shadow: 0.6 });
  ctx.restore();
  grain(t, 0.08);
  sourceTag('画面为重新排版 · 资料：中国青年报');
}

const GER = [9.8, 10.5, 12.5, 13.3, 15.0, 17.0, 19.0, 21.0, 22.0, 23.0, 23.3, 24.2, 26.5, 26.9, 30.0, 34.5, 37.5, 40.0, 42.7, 45.7, 48.1, 51.6, 54.4, 57.8, 59.6, 60.2];
function shBands(t, lt) {
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
  const X = (y) => 220 + (y - 1998) / 25 * 1300, Y = (v) => 820 - v / 70 * 560, k = ap(lt, 0, 0.5);
  const band = (v0, v1, col, lab, tt) => {
    const a = ap(t, tt, 0.4) * k;
    ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = col; ctx.fillRect(220, Y(v1), 1300, Y(v0) - Y(v1)); ctx.restore();
    text(lab, 1540, (Y(v0) + Y(v1)) / 2 + 12, { size: 30, weight: 700, color: C.ink, alpha: a });
  };
  band(0, 15, 'rgba(31,35,40,0.10)', '精英教育  <15%', Wd('C23', '算精英教育') - 0.6);
  band(15, 50, 'rgba(31,35,40,0.05)', '大众化', Wd('C23', '过了百分之五十') - 0.2);
  band(50, 70, 'rgba(160,86,28,0.10)', '普及化  >50%', Wd('C23', '算普及化') - 0.2);
  for (let y = 2000; y <= 2020; y += 5) text(String(y), X(y), 870, { size: 26, font: F.num, color: '#9a9488', align: 'center', alpha: k });
  text('中国高等教育毛入学率', 220, 160, { size: 36, weight: 700, color: C.ink, alpha: k });
  const t0 = S('C24'), u = easeIO(prog(t, t0, Wd('C24', '中间用了十七年')));
  const n = 1 + Math.floor(u * 25);
  ctx.save(); ctx.strokeStyle = C.ink; ctx.lineWidth = 6; ctx.beginPath();
  for (let i = 0; i < n; i++) i ? ctx.lineTo(X(1998 + i), Y(GER[i])) : ctx.moveTo(X(1998), Y(GER[0]));
  ctx.stroke(); ctx.restore();
  const mark = (yr, v, tt, lab) => {
    const a = ap(t, tt, 0.3); if (a <= 0) return;
    ctx.fillStyle = C.ink; ctx.globalAlpha = a; ctx.beginPath(); ctx.arc(X(yr), Y(v), 12, 0, Math.PI * 2); ctx.fill(); ctx.globalAlpha = 1;
    text(lab, X(yr), Y(v) - 28, { size: 30, weight: 700, color: C.ink, align: 'center', alpha: a });
  };
  mark(2002, 15, Wd('C24', '中国二零零二年过的'), '2002 · 15%');
  mark(2019, 51.6, Wd('C24', '二零一九年过的'), '2019 · 50%');
  const tb = Wd('C24', '中间用了十七年');
  handBracket(X(2002), X(2019), Y(68), t, ap(t, tb, 0.6), { color: C.ink, lw: 4 });
  text('17 年', (X(2002) + X(2019)) / 2, Y(68) - 30, { size: 40, font: F.hand, color: C.ink, align: 'center', alpha: ap(t, tb + 0.4) });
  const tu = Wd('C24', '美国走同样一段');
  if (t > tu) {
    const a = ap(t, tu, 0.5), bx = 250, by = 330;
    ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = 'rgba(242,239,231,0.94)'; ctx.strokeStyle = '#cfc9bb'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.roundRect(bx, by, 600, 190, 12); ctx.fill(); ctx.stroke(); ctx.restore();
    text('从 15% 走到 50%', bx + 30, by + 50, { size: 28, color: '#666', alpha: a });
    ctx.fillStyle = C.ink; ctx.globalAlpha = a; ctx.fillRect(bx + 30, by + 76, 17 * 14, 30); ctx.globalAlpha = 1;
    text('中国 17 年', bx + 30 + 17 * 14 + 16, by + 101, { size: 28, weight: 700, color: C.ink, alpha: a });
    ctx.fillStyle = '#9a9488'; ctx.globalAlpha = a; ctx.fillRect(bx + 30, by + 130, 30 * 14, 30); ctx.globalAlpha = 1;
    text('美国约 30 年', bx + 30 + 30 * 14 + 16, by + 155, { size: 28, weight: 700, color: '#6b6560', alpha: a });
    text('（1941–1971）', bx + 30 + 30 * 14 + 16, by + 185, { size: 20, color: '#8a847a', alpha: a });
  }
  sourceTag('资料：历年全国教育事业发展统计公报；美国据邬大光《中国高教研究》2023 年第 4 期', 'rgba(31,35,40,0.5)');
}

function shReserve(t, lt) {
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
  quoteCard(260, 200, 1400, 460, 0.006, ['扩招给中国多储备了', '好几千万大学生'], '—— 汤敏', { size: 72, tex: TEX.paperCard, ink: C.warmInk });
  text('这笔账算得过来', 960, 820, { size: 48, font: F.hand, color: C.ink, align: 'center', alpha: ap(t, S('C26') - 0.1) });
  sourceTag('资料：澎湃新闻', 'rgba(31,35,40,0.5)');
}

// 汤敏那张便签：第三章末钉到右上角，一直留到第五章开头
const NOTE_LINES = ['“我主张好学校多扩，', '差学校少扩，', '但结果却并不是这样。”'];
function stickyNote(x, y, s, rot) {
  paper(TEX.sticky, x, y, 330 * s, 260 * s, rot, (w, h) => {
    ctx.fillStyle = 'rgba(255,255,255,0.45)'; ctx.save(); ctx.translate(w / 2, 6 * s); ctx.rotate(-0.06); ctx.fillRect(-60 * s, -16 * s, 120 * s, 32 * s); ctx.restore();
    NOTE_LINES.forEach((l, i) => text(l, 26 * s, 80 * s + i * 46 * s, { size: 28 * s, font: F.hand, color: '#3a3320' }));
    text('汤敏', w - 26 * s, h - 26 * s, { size: 26 * s, font: F.hand, color: '#5a5040', align: 'right' });
  }, { shadow: 0.3 });
}
const NOTE_BIG = { x: 960 - 330 * 1.25, y: 200, s: 2.5, r: -0.02 }, NOTE_PIN = { x: 1570, y: 40, s: 0.9, r: 0.05 };
function noteAt(u) { stickyNote(lerp(NOTE_BIG.x, NOTE_PIN.x, u), lerp(NOTE_BIG.y, NOTE_PIN.y, u), lerp(NOTE_BIG.s, NOTE_PIN.s, u), lerp(NOTE_BIG.r, NOTE_PIN.r, u)); }
function pinnedNote() { noteAt(1); }
function shNote(t, lt, sh) {
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
  const t8 = S('C28');
  if (t < t8 - 0.3) {
    text('汤敏还说过另一句话', 960, 500, { size: 56, weight: 700, color: C.ink, align: 'center', alpha: ap(lt, 0.1) });
    return;
  }
  const u = easeIO(prog(t, E('C28') + 0.2, sh.b - 0.1));
  const k = ap(t, t8 - 0.3, 0.4);
  ctx.save(); ctx.globalAlpha = k; noteAt(u); ctx.restore();
}

// ---------- 第四章 ----------
function formulaLine(t, y, circleT) {
  text('录取率 ＝ 录取总人数 ÷ 高考报名总人数', 160, y, { size: 58, weight: 700, color: C.ink });
  if (circleT !== undefined) {
    const xa = 160 + measure('录取率 ＝ 录取总人数 ÷ ', 58, F.sans, 700), wa = measure('高考报名总人数', 58, F.sans, 700);
    handEllipse(xa + wa / 2, y - 20, wa / 2 + 26, 50, t, ap(t, circleT, 0.6), { color: C.red, lw: 4.5, seed: 301 });
  }
}
function shFormula(t, lt) {
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
  text('90% 多', 160, 300, { size: 200, font: F.num, color: C.ink, alpha: ap(lt, 0, 0.4) });
  const t9 = Wd('D02', '百分之九十二点九') - 0.3, k9 = ap(t, t9, 0.4);
  text('2021 年：1001 万 ÷ 1078 万 ≈ 92.9%', 790, 230, { size: 38, weight: 700, color: C.ink, alpha: k9 });
  text('这 1001 万还含 45 万五年制高职转入专科，别的年份不含', 790, 278, { size: 24, color: '#777', alpha: k9 });
  const t2 = S('D02');
  if (t > t2 - 0.2) { ctx.save(); ctx.globalAlpha = ap(t, t2 - 0.2, 0.4); formulaLine(t, 440, S('D03')); ctx.restore(); }
  const t4 = S('D04');
  if (t > t4) {
    const bx = 160, by = 560, bw = 1420, fr = 0.64, a = ap(t, t4, 0.5), b = ap(t, Wd('D04', '单独招生') - 0.1, 0.5);
    ctx.fillStyle = C.ink; ctx.globalAlpha = a; ctx.fillRect(bx, by, bw * fr, 100); ctx.globalAlpha = 1;
    text('走进统考考场的人', bx + 30, by + 62, { size: 36, weight: 700, color: '#fff', alpha: a });
    if (b > 0) {
      ctx.save(); ctx.globalAlpha = b; ctx.fillStyle = hatch('rgba(210,65,42,0.85)', 10, 3); ctx.fillRect(bx + bw * fr, by, bw * (1 - fr), 100);
      ctx.strokeStyle = C.red; ctx.lineWidth = 3; ctx.strokeRect(bx + bw * fr, by, bw * (1 - fr), 100); ctx.restore();
      text('单招、对口招生等', bx + bw * fr + bw * (1 - fr) / 2, by + 150, { size: 34, weight: 700, color: C.red, align: 'center', alpha: b });
      text('不少人统考前就被录取了', bx + bw * fr + bw * (1 - fr) / 2, by + 196, { size: 30, color: C.red, align: 'center', alpha: ap(t, Wd('D04', '不少在全国统考之前')) });
    }
  }
  const t5 = S('D05');
  if (t > t5) {
    const xn = 160 + measure('录取率 ＝ ', 58, F.sans, 700) + measure('录取总人数', 58, F.sans, 700) / 2;
    handArrow(1380, 600, xn + 40, 470, t, ap(t, t5 + 0.2, 0.6), { color: C.red, lw: 4, seed: 311, bow: 40 });
    text('也算在录取里', xn - 40, 360, { size: 36, font: F.hand, color: C.red, alpha: ap(t, Wd('D05', '也算在录取里')) });
  }
  pinnedNote();
  sourceTag('资料：教育部 2021 年统计公报、2021 年高考报名人数', 'rgba(31,35,40,0.5)');
}
function shHunan(t, lt) {
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
  formulaLine(t, 220, -99);
  text('湖南 · 2024 年高考报名 72.7 万人', 160, 350, { size: 36, weight: 700, color: C.ink, alpha: ap(lt, 0.1) });
  const tin = Wd('D06', '走进六月统考考场的是');
  const bx = 160, by = 440, bw = 1420, bh = 110, fr = 50.5 / 72.7, pb = easeIO(prog(t, tin - 0.3, tin + 0.6));
  ctx.fillStyle = C.ink; ctx.fillRect(bx, by, bw * fr * pb, bh);
  if (pb > 0.7) text('走进 6 月统考考场 50.5 万', bx + 36, by + bh / 2 + 2, { size: 38, weight: 700, color: '#fff', base: 'middle', alpha: prog(pb, 0.7, 1) });
  const pr = ap(t, Wd('D06', '另外二十二万多人') - 0.1, 0.6);
  if (pr > 0) {
    ctx.save(); ctx.globalAlpha = pr; ctx.fillStyle = 'rgba(210,65,42,0.16)'; ctx.fillRect(bx + bw * fr, by, bw * (1 - fr), bh);
    ctx.fillStyle = hatch('rgba(210,65,42,0.85)', 10, 3); ctx.fillRect(bx + bw * fr, by, bw * (1 - fr), bh);
    ctx.strokeStyle = C.red; ctx.lineWidth = 3; ctx.strokeRect(bx + bw * fr, by, bw * (1 - fr), bh); ctx.restore();
    text('没进统考考场 22.2 万', bx + bw * fr + bw * (1 - fr) / 2, by + bh + 62, { size: 34, weight: 700, color: C.red, align: 'center', alpha: pr });
    text('单招、保送等提前录取，转段考试等', bx + bw * fr + bw * (1 - fr) / 2, by + bh + 108, { size: 26, color: C.red, align: 'center', alpha: pr });
  }
  pinnedNote();
  sourceTag('资料：湖南省人民政府网 2024-06-06（湖南省教育考试院数据）', 'rgba(31,35,40,0.5)');
}
function shNumer(t, lt) {
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
  text('2023 年全国普通、职业本专科招生 1042 万', 160, 260, { size: 40, weight: 700, color: C.ink, alpha: ap(lt, 0.1) });
  const bx = 160, by = 320, bw = 1420, bh = 120, fb = 487 / 1042;
  const a1 = ap(t, Wd('D07', '全国本科招了') - 0.1, 0.5), a2 = ap(t, Wd('D07', '专科招了') - 0.1, 0.5);
  ctx.fillStyle = C.ink; ctx.fillRect(bx, by, bw * fb * a1, bh);
  text('本科 487 万（含职业本科）', bx + 30, by + 76, { size: 40, weight: 700, color: '#fff', alpha: a1 });
  ctx.fillStyle = '#b8b2a5'; ctx.fillRect(bx + bw * fb, by, bw * (1 - fb) * a2, bh);
  text('专科 555 万', bx + bw * fb + 30, by + 76, { size: 40, weight: 700, color: C.ink, alpha: a2 });
  const t8 = S('D08');
  if (t > t8) {
    const a = ap(t, t8, 0.5);
    text('本科 487 万 ÷ 高考报名 1291 万 ≈ 38%', 160, 600, { size: 50, weight: 700, color: C.ink, alpha: a });
    text('不到四成', 160, 700, { size: 64, font: F.hand, color: C.ink, alpha: ap(t, Wd('D08', '不到四成')) });
  }
  pinnedNote();
  sourceTag('资料：2023 年全国教育事业发展统计公报（本科含职业本科）', 'rgba(31,35,40,0.5)');
}
function shTwoQ(t, lt) {
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
  const card = (x, top, line, a, dim) => {
    ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = dim ? 'rgba(31,35,40,0.06)' : '#fff'; ctx.strokeStyle = '#cfc9bb'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.roundRect(x, 330, 700, 300, 18); ctx.fill(); ctx.stroke(); ctx.restore();
    text(top, x + 50, 410, { size: 32, color: '#777', alpha: a });
    text(line, x + 50, 520, { size: 52, weight: 700, color: dim ? '#8a847a' : C.ink, alpha: a });
  };
  card(200, '90% 回答的问题', '能不能上个学校', ap(t, Wd('D09', '回答的是') - 0.2, 0.4), false);
  card(1020, '我们平时问的', '……另一件事', ap(t, S('D10') + 0.3, 0.4), true);
  pinnedNote();
}
function shTip(t, lt) {
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
  const a = ap(lt, 0.1, 0.4);
  ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = '#fff'; ctx.strokeStyle = C.ink; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.roundRect(360, 300, 1200, 380, 20); ctx.fill(); ctx.stroke(); ctx.restore();
  text('小贴士', 420, 380, { size: 34, weight: 700, color: C.red, alpha: a });
  text('看到录取率、中签率，', 420, 490, { size: 60, weight: 700, color: C.ink, alpha: a });
  text('先找分母是谁', 420, 590, { size: 60, weight: 700, color: C.ink, alpha: a });
  pinnedNote();
}
function shAsk2(t, lt) {
  ctx.fillStyle = '#1f2328'; ctx.fillRect(0, 0, W, H);
  text('你们那届，班上考上本科的有几个？', 960, 500, { size: 60, font: F.hand, color: '#f2efe7', align: 'center', alpha: ap(lt, 0.2, 0.6) });
  text('我挺好奇各地差多少。', 960, 600, { size: 44, font: F.hand, color: 'rgba(242,239,231,0.7)', align: 'center', alpha: ap(lt, 1.2, 0.6) });
  grain(t, 0.06);
}

// ---------- 第五章 ----------
function shNoteBack(t, lt) {
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
  noteAt(1 - easeIO(prog(lt, 0.2, 1.2)));
}
function shGrowthCmp(t, lt) {
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
  text('扩招前后，一年招多少人', 160, 140, { size: 40, weight: 700, color: C.ink, alpha: ap(lt, 0.1) });
  const groups = [['全国本专科', '1998：108 万 → 2023：1042 万', 9.6, '×9.6', S('E02')], ['清华本科', '1997：2318 → 2024：3800 余', 1.6, '×1.6', S('E03')], ['中国科大本科', '2001：1860 → 2024：2033', 2033 / 1860, '差不多', S('E04')]];
  const base = 780, unit = 54;
  groups.forEach(([n, d, r, lab, tt], i) => {
    const x = 260 + i * 520, a = ap(t, tt, 0.4), g = easeOut(prog(t, tt + 0.3, tt + 1.3));
    ctx.fillStyle = '#b8b2a5'; ctx.globalAlpha = a; ctx.fillRect(x, base - unit, 120, unit);
    ctx.fillStyle = C.ink; ctx.fillRect(x + 150, base - unit * lerp(1, r, g), 120, unit * lerp(1, r, g)); ctx.globalAlpha = 1;
    text(lab, x + 210, base - unit * lerp(1, r, g) - 24, { size: 56, font: F.num, color: C.ink, align: 'center', alpha: a * g });
    text(n, x + 135, base + 60, { size: 36, weight: 700, color: C.ink, align: 'center', alpha: a });
    text(d, x + 135, base + 104, { size: 26, color: '#777', align: 'center', alpha: a });
  });
  const t5 = S('E05');
  if (t > t5) text('扩出来的名额，大头在地方院校和高职', 1640, 300, { size: 40, font: F.hand, color: C.ink, align: 'right', alpha: ap(t, t5 + 0.2) });
  sourceTag('资料：统计公报；清华大学校友总会、清华新闻网；中国科大本科教学质量报告、《中国新闻周刊》', 'rgba(31,35,40,0.5)');
}
function shC9(t, lt) {
  ctx.fillStyle = C.warmDark; ctx.fillRect(0, 0, 960, H);
  ctx.fillStyle = C.bg; ctx.fillRect(960, 0, 960, H);
  const k = ap(lt, 0, 0.35), t7 = S('E07');
  const kl = ap(t, t7 - 0.2, 0.4);
  text('1977 · 考上任何一所大学', 480, 190, { size: 36, weight: 700, color: C.amber, align: 'center', alpha: kl });
  ctx.save(); ctx.globalAlpha = kl; dotGrid(230, 240, 10, 10, 50, 42, 'rgba(236,225,200,0.14)', [{ to: 4.8, fill: C.amber }]); ctx.restore();
  text('4.8%', 480, 860, { size: 110, font: F.num, color: C.amber, align: 'center', alpha: kl });
  text('2023 · 考上 C9', 1440, 190, { size: 36, weight: 700, color: C.ink, align: 'center', alpha: k });
  const lit = clamp((t - Wd('E06', '一千个人里不到四个')) * 5, 0, 3.3);
  dotGrid(1060, 250, 40, 25, 19, 17, C.mute, [{ to: lit, fill: C.ink }]);
  const tl = Wd('E06', '一千个人里不到四个');
  handEllipse(1098, 259, 58, 24, t, ap(t, tl + 0.5, 0.5), { color: C.ink, lw: 3.5, seed: 411 });
  text('亮着的只有 3.3 个', 1170, 236, { size: 30, font: F.hand, color: C.ink, alpha: ap(t, tl + 0.9) });
  text('约 4.2 万 ÷ 1291 万 ≈ 0.33%', 1440, 860, { size: 44, weight: 700, color: C.ink, align: 'center', alpha: ap(t, Wd('E06', '按一千二百九十一万')) });
  text('一千个人里不到四个', 1440, 910, { size: 30, color: '#777', align: 'center', alpha: ap(t, Wd('E06', '一千个人里不到四个')) });
  const ts = Wd('E07', '难了十几倍'), ps = prog(t, ts - 0.05, ts + 0.3);
  if (ps > 0) {
    const sc = lerp(1.7, 1, easeBack(ps));
    ctx.save(); ctx.translate(960, 520); ctx.rotate(-0.07); ctx.scale(sc, sc); ctx.globalAlpha = clamp(ps * 3);
    ctx.fillStyle = C.ink; ctx.beginPath(); ctx.arc(0, 0, 130, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = C.bg; ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(0, 0, 116, 0, Math.PI * 2); ctx.stroke();
    text('难了', 0, -30, { size: 34, color: C.bg, align: 'center', font: F.serif });
    text('十几倍', 0, 40, { size: 62, weight: 700, color: C.bg, align: 'center', font: F.serif });
    ctx.restore();
  }
  sourceTag('左：1 个小人 = 1%  ·  右：1 个小人 = 0.1%  ·  资料：各校 2023 年本科招生人数、教育部', 'rgba(236,225,200,0.5)');
}
function shPlain(t, lt) {
  ctx.fillStyle = '#e9e7e2'; ctx.fillRect(0, 0, W, H);
  const a = ap(lt, 0.2, 0.4), b = ap(t, Wd('E09', '今天比的是最顶上的九所'), 0.4);
  text('1977 年比的是', 520, 380, { size: 36, color: '#777', align: 'center', alpha: a });
  text('所有大学', 520, 480, { size: 72, weight: 700, color: '#555', align: 'center', alpha: a });
  text('今天比的是', 1400, 380, { size: 36, color: '#777', align: 'center', alpha: b });
  text('最顶上的 9 所', 1400, 480, { size: 72, weight: 700, color: '#555', align: 'center', alpha: b });
  text('口径不一样', 960, 470, { size: 40, font: F.hand, color: '#888', align: 'center', alpha: b });
  const tc = Wd('E09', '卷的恰恰就是这九所');
  if (t > tc) {
    handEllipse(1400, 462, 290, 60, t, ap(t, tc, 0.6), { color: C.ink, lw: 4, seed: 401 });
    text('大家说卷，卷的就是这里', 1400, 640, { size: 38, font: F.hand, color: C.ink, align: 'center', alpha: ap(t, tc + 0.4) });
  }
}
function shBeijing(t, lt) {
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
  const tb = S('E11');
  text('考生进 C9 的比例', 200, 280, { size: 40, weight: 700, color: C.ink, alpha: ap(t, tb - 0.2) });
  const rows = [['北京考生', 1.5, '约 1.5%（估算）', Wd('E11', '北京考生进C九的比例')], ['全国平均', 0.33, '约 0.33%', Wd('E11', '是全国平均的四倍多')]];
  rows.forEach(([n, v, lab, tt], i) => {
    const y = 380 + i * 170, a = ap(t, tt - 0.1, 0.5);
    text(n, 200, y + 64, { size: 44, weight: 700, color: C.ink, alpha: a });
    ctx.fillStyle = i ? '#9a9488' : C.ink; ctx.fillRect(440, y, v * 560 * a, 90);
    text(lab, 460 + v * 560 * a, y + 64, { size: 52, font: F.num, color: C.ink, alpha: a });
  });
  text('四倍多', 1300, 760, { size: 72, font: F.hand, color: C.ink, align: 'center', alpha: ap(t, Wd('E11', '四倍多')) });
  if (t < tb - 0.2) text('还有一个数', 960, 520, { size: 64, weight: 700, color: C.ink, align: 'center', alpha: ap(lt, 0.2) });
  sourceTag('估算：C9 2023 年在京招生计划约 992 人 ÷ 北京高考报名 6.5 万；全国：约 4.2 万 ÷ 1291 万', 'rgba(31,35,40,0.5)');
}

// ---------- 结尾 ----------
function shNotice(t, lt, sh) {
  ctx.drawImage(TEX.deskWarm, 0, 0);
  const z = lerp(1.0, 1.05, easeIO(prog(lt, 0, sh.b - sh.a)));
  camera(z, 960, 500, () => {
    paper(TEX.paperWarm, 560, 120, 800, 740, -0.015, (w) => {
      text('录取通知书', w / 2, 150, { size: 64, weight: 700, font: F.serif, color: C.warmInk, align: 'center', spacing: 10 });
      text('　　　　同志：', 80, 270, { size: 34, font: F.serif, color: C.warmInk });
      ctx.fillStyle = 'rgba(43,37,32,0.5)'; ctx.fillRect(80, 278, 160, 2);
      const r = rng(77);
      for (let i = 0; i < 5; i++) { ctx.fillStyle = 'rgba(43,37,32,0.16)'; ctx.fillRect(120, 340 + i * 56, (w - 200) * (0.7 + r() * 0.3), 12); }
      text('一九七八年', w - 100, 680, { size: 30, font: F.serif, color: C.warmInk, align: 'right' });
    });
  });
  text('1977', 110, 470, { size: 90, font: F.num, color: '#efe4cc', alpha: ap(lt, 0.3) });
  text('录取 27 万人', 110, 540, { size: 40, weight: 700, color: '#efe4cc', alpha: ap(lt, 0.5) });
  grain(t, 0.12);
  sourceTag('虚构样式，不对应任何真实学校');
}
function shFew(t, lt) {
  ctx.fillStyle = C.warmDark; ctx.fillRect(0, 0, W, H);
  const gx = 1020, gy = 190, cell = 68;
  dotGrid(gx, gy, 10, 10, cell, 64, 'rgba(236,225,200,0.12)', [{ to: 4.8, fill: C.amber }]);
  const tw = Wd('F03', '连门都进不去');
  text('1977 年', 180, 400, { size: 44, weight: 700, color: C.amber, alpha: ap(lt, 0.1) });
  text('100 个人里 95 个', 180, 500, { size: 64, weight: 700, color: '#efe4cc', alpha: ap(t, tw - 0.8) });
  text('连门都进不去', 180, 590, { size: 64, weight: 700, color: '#efe4cc', alpha: ap(t, tw - 0.2) });
  grain(t, 0.1);
}
function shNarrow(t, lt) {
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
  const bx = 160, by = 470, bw = 1600, a = ap(lt, 0.1, 0.5);
  ctx.fillStyle = '#d9d4c8'; ctx.globalAlpha = a; ctx.fillRect(bx, by, bw, 120); ctx.globalAlpha = 1;
  text('今天能上大学的人', bx, by - 30, { size: 36, weight: 700, color: C.ink, alpha: a });
  const tn = Wd('F04', '很窄的一段'), p = ap(t, tn - 0.2, 0.5);
  ctx.fillStyle = C.ink; ctx.globalAlpha = p; ctx.fillRect(bx + bw - 48, by, 48, 120); ctx.globalAlpha = 1;
  text('很窄的一段', bx + bw - 24, by - 30, { size: 40, font: F.hand, color: C.ink, align: 'right', alpha: p });
  const tc = Wd('F04', '想挤的人也都挤在那儿');
  for (let i = 0; i < 14; i++) {
    const u = easeIO(prog(t, tc - 0.2 + i * 0.05, tc + 1.2 + i * 0.05));
    const x0 = bx + 120 + (i % 7) * 160, y0 = by + 230 + Math.floor(i / 7) * 80;
    const x1 = bx + bw - 30 - (i % 5) * 44, y1 = by + 190 + Math.floor(i / 5) * 56;
    person(lerp(x0, x1, u), lerp(y0, y1, u), 52, `rgba(31,35,40,${0.25 + 0.5 * u})`);
  }
  sourceTag('示意图', 'rgba(31,35,40,0.5)');
}
function shFinalQ(t, lt) {
  ctx.fillStyle = C.warmDark; ctx.fillRect(0, 0, W, H);
  const k = ap(t, S('F05') - 0.1, 0.6);
  text('要是能选，', 960, 440, { size: 64, font: F.hand, color: '#efe4cc', align: 'center', alpha: k });
  text('你愿意在 1977 年考，', 960, 550, { size: 72, font: F.hand, color: C.amber, align: 'center', alpha: ap(t, Wd('F05', '你愿意在一九七七年考') - 0.1, 0.5) });
  text('还是在今天考？', 960, 660, { size: 72, font: F.hand, color: '#efe4cc', align: 'center', alpha: ap(t, Wd('F05', '还是在今天考') - 0.1, 0.5) });
  grain(t, 0.1);
  black(prog(t, TL.duration - 1.5, TL.duration));
}
