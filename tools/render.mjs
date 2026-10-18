// Render the motion graphic frame by frame with headless Chromium.
//
//   node tools/render.mjs stills 2.9 10.8 22.4    # PNG stills into out/stills/
//   node tools/render.mjs video [fps]             # out/genlayer-silent.mp4 (no audio)
//
// Options for other pages in this repo:
//   --page mascot-loop/index.html   page to load (default index.html)
//   --size 1080x1080                viewport (default 1920x1080)
//   --scale 2                       device pixel ratio, for supersampled frames (default 1)
//   --out name                      file name stem for video mode (default genlayer-silent)
//   --query lite                    query string for the page (default none)
//   --alpha                         transparent background: video mode writes PNG frames
//                                   into out/<name>-frames/ instead of an mp4
//
// Each frame is drawn by window.renderAt(t), so the result does not depend on render speed.
import { createRequire } from 'node:module';
import { spawn, execSync } from 'node:child_process';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); }
catch { ({ chromium } = require(path.join(execSync('npm root -g').toString().trim(), 'playwright'))); }

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.join(ROOT, 'out');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.woff2': 'font/woff2', '.png': 'image/png', '.mp3': 'audio/mpeg' };

const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));

const args = process.argv.slice(2);
const opt = (name, def) => { const i = args.indexOf(name); if (i < 0) return def; const v = args[i + 1]; args.splice(i, 2); return v; };
const flag = name => { const i = args.indexOf(name); if (i < 0) return false; args.splice(i, 1); return true; };
const pagePath = opt('--page', 'index.html');
const [W, H] = opt('--size', '1920x1080').split('x').map(Number);
const outName = opt('--out', 'genlayer-silent');
const scale = +opt('--scale', '1');
const alpha = flag('--alpha');
const query = opt('--query', '');
const url = `http://127.0.0.1:${server.address().port}/${pagePath}${query ? '?' + query : ''}#${alpha ? 'capture-alpha' : 'capture'}`;

const browser = await chromium.launch({ args: ['--force-color-profile=srgb', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: scale });
page.on('pageerror', e => console.error('page error:', e.message));
page.on('console', m => { if (m.type() === 'error') console.error('console:', m.text()); });
await page.goto(url);
await page.waitForFunction(() => window.READY === true, null, { timeout: 120000 });
const clip = { x: 0, y: 0, width: W, height: H };

const [mode = 'stills', ...rest] = args;
fs.mkdirSync(OUT, { recursive: true });
if (mode === 'stills') {
  const dir = path.join(OUT, 'stills');
  fs.mkdirSync(dir, { recursive: true });
  for (const s of rest) {
    await page.evaluate(t => window.renderAt(t), +s);
    await page.screenshot({ path: path.join(dir, `t${(+s).toFixed(2).padStart(6, '0')}.png`), clip, omitBackground: alpha });
  }
  console.log('stills ->', dir);
} else {
  const fps = +(rest[0] || 30);
  const dur = await page.evaluate(() => window.DURATION);
  const frames = Math.round(dur * fps);
  if (alpha) {
    const dir = path.join(OUT, `${outName}-frames`);
    fs.rmSync(dir, { recursive: true, force: true });
    fs.mkdirSync(dir, { recursive: true });
    for (let f = 0; f < frames; f++) {
      await page.evaluate(t => window.renderAt(t), f / fps);
      await page.screenshot({ path: path.join(dir, `f${String(f).padStart(5, '0')}.png`), clip, omitBackground: true });
      if (f % (fps * 5) === 0) console.log(`frame ${f}/${frames}`);
    }
    console.log('frames ->', dir);
    await browser.close(); server.close(); process.exit(0);
  }
  const file = path.join(OUT, `${outName}.mp4`);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', file], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let f = 0; f < frames; f++) {
    await page.evaluate(t => window.renderAt(t), f / fps);
    const buf = await page.screenshot({ type: 'jpeg', quality: 96, clip });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (f % (fps * 5) === 0) console.log(`frame ${f}/${frames}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  console.log('video ->', file);
}
await browser.close();
server.close();
