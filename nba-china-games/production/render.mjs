// 用法：
//   node render.mjs <scene.html> <out.mp4> [--audio a.wav]
//   node render.mjs <scene.html> <outDir> --stills 1,3.5,7.5
import puppeteer from 'puppeteer-core';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.glb': 'model/gltf-binary', '.png': 'image/png', '.jpg': 'image/jpeg', '.wav': 'audio/wav' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const BASE = `http://127.0.0.1:${server.address().port}/`;

const CHROME = process.env.CHROME_PATH || {
  darwin: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  linux: '/usr/bin/google-chrome',
  win32: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
}[process.platform];
const argv = process.argv.slice(2);
const [scene, out] = argv;
const opt = (name) => {
  const i = argv.indexOf(name);
  return i >= 0 ? argv[i + 1] : undefined;
};
const audio = opt('--audio');
const stills = opt('--stills');

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  args: ['--no-sandbox', '--force-device-scale-factor=1', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', ...(process.env.GL_ARGS || '').split(' ').filter(Boolean)],
});
const page = await browser.newPage();
page.on('console', (m) => console.log('[scene]', m.text()));
page.on('pageerror', (e) => console.error('[scene error]', e.message));
page.on('response', (r) => { if (r.status() >= 400) console.log('[404]', r.url().replace(BASE, '')); });
await page.goto(BASE + path.relative(ROOT, path.resolve(scene)) + (process.env.QUERY ? '?' + process.env.QUERY : ''));
await page.waitForFunction(() => window.ready !== undefined, { timeout: 60000 });
await page.evaluate(() => window.ready);
const { duration, fps, width, height } = await page.evaluate(() => ({
  duration: window.DURATION,
  fps: window.FPS,
  width: document.getElementById('c').width,
  height: document.getElementById('c').height,
}));
await page.setViewport({ width, height, deviceScaleFactor: 1 });

const JPEG = !!process.env.JPEG;
const grab = (t) =>
  page.evaluate(async (t, jpeg) => {
    try { await window.renderFrame(t); } catch (e) { console.log('renderFrame error @' + t + ': ' + e.stack); throw e; }
    const c = document.getElementById('c');
    return (jpeg ? c.toDataURL('image/jpeg', 0.96) : c.toDataURL('image/png')).split(',')[1];
  }, t, JPEG);

if (stills) {
  fs.mkdirSync(out, { recursive: true });
  for (const s of stills.split(',')) {
    const t = parseFloat(s);
    fs.writeFileSync(path.join(out, `t${t.toFixed(2)}.png`), Buffer.from(await grab(t), 'base64'));
  }
  await browser.close();
  server.close();
  process.exit(0);
}

// FRAMES=a:b renders only frames [a, b) so several processes can split one film
const [fa, fb] = (process.env.FRAMES || `0:${Math.round(duration * fps)}`).split(':').map(Number);
const args = ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', JPEG ? 'mjpeg' : 'png', '-i', '-'];
if (audio) args.push('-i', audio);
args.push('-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16', '-preset', 'medium', '-movflags', '+faststart');
if (audio) args.push('-c:a', 'aac', '-b:a', '256k', '-shortest');
args.push(out);
const ff = spawn('ffmpeg', args, { stdio: ['pipe', 'inherit', 'inherit'] });

const t0 = Date.now();
for (let i = fa; i < fb; i++) {
  const buf = Buffer.from(await grab(i / fps), 'base64');
  if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
  if (i % 150 === 0) console.log(`frame ${i}/${fb}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
}
ff.stdin.end();
await new Promise((r) => ff.on('close', r));
await browser.close();
server.close();
console.log(`done: ${out}`);
