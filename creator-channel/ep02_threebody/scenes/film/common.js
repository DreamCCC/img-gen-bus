// 各章共用：3D 绘制、星空底、箭头、锁、转盘、引语卡、名字卡
import { W, H, COL, F, clamp, lerp, prog, easeOut } from './lib.js';
import { orbitCam } from './sim.js';

export function kit({ g, space, ctx }) {
  const k = {};
  k.draw3d = (cfg, x = 0) => {
    const cv = space.draw(cfg);
    ctx.drawImage(cv, x, 0);
    return (p) => { const v = space.project(p); return [v[0] + x, v[1], v[2]]; };
  };
  // 只有星空的底（2D 卡片下面垫着，保持质感一致）
  k.bg = (t, o = {}) => space && ctx.drawImage(space.draw({ t, cam: orbitCam([0, 0, 0], 6, o.elev ?? 0.3, (o.yaw ?? 0.6) + 0.012 * t), sky: o.sky ?? 0.6, exposure: o.exposure ?? 0.9 }), 0, 0);
  k.arrow = (x0, y0, x1, y1, o = {}) => {
    const { color = COL.hud, w = 2, a = 1, head = 14 } = o;
    g.line(x0, y0, x1, y1, { color, w, a });
    const ang = Math.atan2(y1 - y0, x1 - x0);
    g.poly([[x1 - head * Math.cos(ang - 0.45), y1 - head * Math.sin(ang - 0.45)], [x1, y1], [x1 - head * Math.cos(ang + 0.45), y1 - head * Math.sin(ang + 0.45)]], { color, w, a });
  };
  // 锁：p = 扣上进度（0 开，1 扣上）
  k.lock = (x, y, s, o = {}) => {
    const { p = 1, a = 1, color = COL.gold } = o;
    if (a <= 0) return;
    ctx.save(); ctx.globalAlpha *= a; ctx.translate(x, y); ctx.scale(s / 40, s / 40);
    ctx.strokeStyle = color; ctx.lineWidth = 3.2; ctx.lineCap = 'round';
    const lift = (1 - easeOut(clamp(p))) * 12;
    ctx.beginPath(); ctx.moveTo(-11, -4 - lift); ctx.lineTo(-11, -14 - lift); ctx.arc(0, -14 - lift, 11, Math.PI, 0); ctx.lineTo(11, -4 - lift * (p < 1 ? 1.6 : 1)); ctx.stroke();
    ctx.fillStyle = p >= 1 ? color : 'rgba(0,0,0,0)';
    ctx.globalAlpha *= p >= 1 ? 0.22 : 1;
    ctx.fillRect(-17, -4, 34, 26);
    ctx.globalAlpha /= p >= 1 ? 0.22 : 1;
    ctx.strokeRect(-17, -4, 34, 26);
    ctx.beginPath(); ctx.arc(0, 7, 3, 0, 7); ctx.fillStyle = color; ctx.fill();
    ctx.restore();
  };
  // 转盘：ang 指针角度
  k.dial = (x, y, r, ang, o = {}) => {
    const { color = COL.hud, a = 1, locked = false } = o;
    if (a <= 0) return;
    ctx.save(); ctx.globalAlpha *= a; ctx.translate(x, y);
    ctx.strokeStyle = color; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(0, 0, r, 0, 7); ctx.stroke();
    for (let i = 0; i < 24; i++) {
      const u = (i / 24) * Math.PI * 2, l = i % 6 === 0 ? 0.22 : 0.1;
      ctx.beginPath(); ctx.moveTo(Math.cos(u) * r * (1 - l), Math.sin(u) * r * (1 - l)); ctx.lineTo(Math.cos(u) * r, Math.sin(u) * r); ctx.stroke();
    }
    ctx.lineWidth = 2.5; ctx.strokeStyle = locked ? COL.gold : '#ffffff';
    ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(Math.cos(ang) * r * 0.78, Math.sin(ang) * r * 0.78); ctx.stroke();
    ctx.fillStyle = locked ? COL.gold : '#fff'; ctx.beginPath(); ctx.arc(0, 0, 3.5, 0, 7); ctx.fill();
    ctx.restore();
  };
  // 引语卡：宋体，带引号和出处
  k.quote = (lines, who, x, y, o = {}) => {
    const { a = 1, size = 54, align = 'center', color = '#f4efe4', p = 1 } = o;
    if (a <= 0) return;
    lines.forEach((s, i) => g.text(s, x, y + i * size * 1.45, { size, font: F.serif, weight: '600', color, a: a * clamp(p * lines.length - i), align, shadow: 16 }));
    if (who) g.text(who, align === 'center' ? x : x, y + lines.length * size * 1.45 + 10, { size: 26, color: COL.grey, a: a * clamp(p * lines.length - lines.length + 1), align, weight: '400' });
  };
  // 名字卡（不用照片）
  k.nameCard = (name, years, note, x, y, o = {}) => {
    const { a = 1, p = 1 } = o;
    if (a <= 0) return;
    const lp = easeOut(clamp(p));
    g.line(x, y - 70, x, y - 70 + 150 * lp, { color: COL.gold, w: 2, a });
    g.text(name, x + 30, y - 30, { size: 64, font: F.serif, weight: '700', color: '#f4efe4', a: a * clamp(p * 2 - 0.3), align: 'left', shadow: 12 });
    g.text(years, x + 30, y + 30, { size: 26, font: F.mono, color: COL.gold, a: a * clamp(p * 2 - 0.6), align: 'left', weight: '400' });
    if (note) g.text(note, x + 30, y + 72, { size: 26, color: COL.grey, a: a * clamp(p * 2 - 0.8), align: 'left', weight: '400' });
  };
  // 读数行：标签 + 数值 + 状态
  k.readout = (x, y, label, value, state, o = {}) => {
    const { a = 1, color = COL.hud, valColor = '#fff', w = 520 } = o;
    if (a <= 0) return;
    g.text(label, x, y, { size: 30, color, a, align: 'left' });
    g.text(value, x + w * 0.52, y, { size: 32, font: F.mono, color: valColor, a, align: 'left', weight: '400' });
    if (state) g.text(state, x + w, y, { size: 24, color: state === '不变' ? COL.gold : COL.grey, a, align: 'right', weight: '400' });
  };
  return k;
}
