// 全片镜头表：各段的镜头函数按时间排好，后面的画在上面
import { W, H, COL, F, prog, easeOut, lerp, M, FILM } from './lib.js';
import { loadSims } from './sim.js';
import { orbitCam } from './sim.js';
import { coldShots } from './cold.js';
import { ch12Shots } from './ch12.js';
import { ch34Shots } from './ch34.js';
import { ch56Shots } from './ch56.js';

const CHAPTERS = {
  ch1: ['第一章', '两个天体为什么好算'],
  ch2: ['第二章', '一百年，只找到两个特例'],
  ch3: ['第三章', '国王的奖金'],
  ch4: ['第四章', '有解，但没法用'],
  ch5: ['第五章', '那就一步一步算'],
  ch6: ['第六章', '天上真有三体吗'],
};

export async function buildShots(env) {
  await loadSims();
  const { g, space, ctx } = env;
  const card = (key) => (lt, t) => {
    const [no, name] = CHAPTERS[key];
    const dur = M(key + '_end') - M(key);
    ctx.drawImage(space.draw({ t, cam: orbitCam([0, 0, 0], 6, 0.3, 0.8 + 0.02 * lt), sky: 0.55, exposure: 0.8 }), 0, 0);
    const a = prog(lt, 0.1, 0.6) * (1 - prog(lt, dur - 0.45, dur));
    const lp = easeOut(prog(lt, 0.15, 0.9));
    g.line(W / 2 - 260 * lp, H / 2 - 70, W / 2 + 260 * lp, H / 2 - 70, { color: COL.hud, w: 1, a: a * 0.7 });
    g.text(no, W / 2, H / 2 - 110, { size: 30, color: COL.gold, a, spacing: 10, weight: '400' });
    g.text(name, W / 2, H / 2, { size: 76, font: F.serif, weight: '700', color: '#f4efe4', a: a * prog(lt, 0.3, 0.8), spacing: 6, shadow: 20 });
    g.text(`CHAPTER 0${key.slice(2)}`, W / 2, H / 2 + 80, { size: 20, font: F.mono, color: COL.grey, a: a * 0.8, spacing: 8, weight: '400' });
  };
  const shots = [...coldShots(env), ...ch12Shots(env), ...ch34Shots(env), ...ch56Shots(env)];
  for (const k of Object.keys(CHAPTERS)) shots.push({ a: M(k), b: M(k + '_end'), fi: 0.3, fo: 0.3, draw: card(k), noSub: true });
  return shots;
}
