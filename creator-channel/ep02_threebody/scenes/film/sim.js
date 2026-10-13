// 模拟数据的取样、轨迹、取景、镜头
import { clamp, lerp, SIMCOL } from './lib.js';

export let OP = null;   // 开场 A/B：{rate, A, B}
export let FD = null;   // film.json：周期轨道、混沌之网、特洛伊
export let WEB = null, TROJ = null;
export async function loadSims() {
  OP = await (await fetch('/scenes/data/opening.json')).json();
  FD = await (await fetch('/scenes/data/film.json')).json();
  WEB = new Float32Array(await (await fetch('/scenes/data/web.bin')).arrayBuffer());
  TROJ = new Float32Array(await (await fetch('/scenes/data/trojans.bin')).arrayBuffer());
}

// 按模拟时间 s 取样（线性插值），返回 6 个数 x0 y0 x1 y1 x2 y2
export function samp(arr, s, rate = 60) {
  const f = clamp(s * rate, 0, arr.length - 1.001), i = Math.floor(f), u = f - i;
  const a = arr[i], b = arr[i + 1];
  return a.map((x, k) => x + (b[k] - x) * u);
}
export const wp = (q, j) => [q[2 * j], 0, -q[2 * j + 1]];
export const run = (name) => OP[name];

// 速度（数值差分）
export function vel(arr, s, j) {
  const a = samp(arr, s - 0.01), b = samp(arr, s + 0.01);
  return [(b[2 * j] - a[2 * j]) / 0.02, (b[2 * j + 1] - a[2 * j + 1]) / 0.02];
}

// 轨迹点：从 s-span 到 s，n 个点；off(s') 返回要减去的偏移（相对坐标系用）
export function trail(arr, s, j, span, n = 400, off = null) {
  const out = new Float32Array(n * 3);
  const s0 = Math.max(0, s - span);
  for (let i = 0; i < n; i++) {
    const si = lerp(s0, s, i / (n - 1));
    const q = samp(arr, si);
    let x = q[2 * j], z = -q[2 * j + 1];
    if (off) { const o = off(si); x -= o[0]; z -= o[2]; }
    out[3 * i] = x; out[3 * i + 1] = 0; out[3 * i + 2] = z;
  }
  return out;
}

// 取景：idx 这几颗星在 [s-back, s+fwd] 内的中心和半径
export function frameOf(arr, s, idx = [0, 1, 2], back = 4, fwd = 2) {
  let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
  for (let k = 0; k <= 24; k++) {
    const q = samp(arr, s - back + ((back + fwd) * k) / 24);
    for (const j of idx) {
      x0 = Math.min(x0, q[2 * j]); x1 = Math.max(x1, q[2 * j]);
      z0 = Math.min(z0, -q[2 * j + 1]); z1 = Math.max(z1, -q[2 * j + 1]);
    }
  }
  return { c: [(x0 + x1) / 2, 0, (z0 + z1) / 2], R: Math.max(0.6, Math.hypot(x1 - x0, z1 - z0) / 2) };
}
export const pairCom = (arr, s, a = 1, b = 2) => { const q = samp(arr, s); return [(q[2 * a] + q[2 * b]) / 2, 0, -(q[2 * a + 1] + q[2 * b + 1]) / 2]; };

// 环绕镜头：target + 距离 + 仰角 + 方位角
export function orbitCam(target, dist, elev, yaw, o = {}) {
  const pos = [target[0] + dist * Math.cos(elev) * Math.sin(yaw), target[1] + dist * Math.sin(elev), target[2] + dist * Math.cos(elev) * Math.cos(yaw)];
  return { pos, look: target, fov: o.fov ?? 32, ...o };
}

// 三颗星的 cfg
export function starsOf(q, o = {}) {
  const { r = 0.04, a = [1, 1, 1], glow = 1 } = o;
  return [0, 1, 2].map((j) => ({ p: wp(q, j), col: SIMCOL[j], r, a: a[j], glow }));
}
export function trailsOf(arr, s, span, o = {}) {
  const { a = 0.75, w = 1.7, n = 400, off = null, idx = [0, 1, 2], col = null } = o;
  return idx.map((j) => ({ pts: trail(arr, s, j, span, n, off), col: col || SIMCOL[j], a: Array.isArray(a) ? a[j] : a, w }));
}

// Kepler：平近点角 M → 偏近点角 E
export function kepler(M, e) {
  let E = M;
  for (let i = 0; i < 12; i++) E -= (E - e * Math.sin(E) - M) / (1 - e * Math.cos(E));
  return E;
}
// 椭圆轨道上的位置（焦点在原点），phase 0..1 = 平近点角 / 2π，近日点朝 +x
export function ellipse(a, e, phase, rot = 0) {
  const E = kepler(2 * Math.PI * phase, e);
  const x = a * (Math.cos(E) - e), y = a * Math.sqrt(1 - e * e) * Math.sin(E);
  const c = Math.cos(rot), s = Math.sin(rot);
  return [x * c - y * s, 0, -(x * s + y * c)];
}
