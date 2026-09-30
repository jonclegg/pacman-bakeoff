// Injected before any page script: audio / fps / scroll / error instrumentation + canvas blob analyzer.
(() => {
  const A = window.__audit = {
    ctx: 0, oscStarts: 0, bufStarts: 0, runningStarts: 0, states: {}, resumes: 0,
    mediaPlays: 0, frames: 0, maxScroll: 0, errors: []
  };

  for (const k of ['AudioContext', 'webkitAudioContext']) {
    const O = window[k];
    if (!O) continue;
    window[k] = new Proxy(O, { construct(t, args, nt) { A.ctx++; return Reflect.construct(t, args, nt); } });
  }
  if (window.AudioScheduledSourceNode) {
    const P = AudioScheduledSourceNode.prototype, s = P.start;
    P.start = function (...a) {
      try {
        if (this instanceof OscillatorNode) A.oscStarts++; else A.bufStarts++;
        const st = this.context.state;
        A.states[st] = (A.states[st] || 0) + 1;
        if (st === 'running') A.runningStarts++;
      } catch (e) {}
      return s.apply(this, a);
    };
  }
  if (window.BaseAudioContext) {
    const target = BaseAudioContext.prototype.resume ? BaseAudioContext.prototype : AudioContext.prototype;
    const r = target.resume;
    target.resume = function () { A.resumes++; return r.apply(this, arguments); };
  }
  const mp = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function () { A.mediaPlays++; return mp.apply(this, arguments); };

  const raf = window.requestAnimationFrame.bind(window);
  (function tick() { A.frames++; raf(tick); })();
  addEventListener('scroll', () => { A.maxScroll = Math.max(A.maxScroll, window.scrollY); }, true);
  addEventListener('error', e => A.errors.push(String(e.message)));
  addEventListener('unhandledrejection', e => A.errors.push('rejection: ' + String(e.reason)));

  // ---- canvas analyzer ----
  // classes: 1 yellow(pac) 2 red 3 pink 4 cyan 5 orange 6 wall-blue
  function classify(r, g, b) {
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b);
    if (mx < 80) return 0;
    const s = (mx - mn) / mx;
    let h = 0;
    if (mx !== mn) {
      if (mx === r) h = 60 * (((g - b) / (mx - mn)) % 6);
      else if (mx === g) h = 60 * ((b - r) / (mx - mn) + 2);
      else h = 60 * ((r - g) / (mx - mn) + 4);
    }
    if (h < 0) h += 360;
    if (mx > 150 && s > 0.6 && h >= 44 && h <= 70) return 1;
    if (mx > 150 && s > 0.6 && (h < 14 || h >= 345)) return 2;
    if (r > 200 && b > 190 && g >= 90 && g <= 215 && r - g >= 35) return 3;
    if (mx > 150 && s > 0.5 && h >= 165 && h <= 200) return 4;
    if (mx > 150 && s > 0.55 && h >= 20 && h < 44) return 5;
    if (s > 0.45 && h >= 200 && h <= 265 && mx > 90) return 6;
    return 0;
  }

  function mainCanvas() {
    const cs = [...document.querySelectorAll('canvas')]
      .filter(c => c.width * c.height > 0 && c.getBoundingClientRect().width > 0)
      .sort((a, b) => b.width * b.height - a.width * a.height);
    return cs[0] || null;
  }

  window.__analyze = function (captureRef) {
    const c = mainCanvas();
    if (!c) return { err: 'nocanvas' };
    let ctx;
    try { ctx = c.getContext('2d'); } catch (e) { return { err: 'ctx' }; }
    if (!ctx) return { err: 'notd2' };
    const W = c.width, H = c.height;
    let d;
    try { d = ctx.getImageData(0, 0, W, H).data; } catch (e) { return { err: 'tainted' }; }
    const S = Math.max(1, Math.round(Math.min(W, H) / 320));
    const gw = Math.floor(W / S), gh = Math.floor(H / S);
    const cls = new Uint8Array(gw * gh);
    const colB = new Uint32Array(gw), rowB = new Uint32Array(gh);
    for (let y = 0; y < gh; y++) {
      for (let x = 0; x < gw; x++) {
        const i = ((y * S) * W + x * S) * 4;
        const k = classify(d[i], d[i + 1], d[i + 2]);
        cls[y * gw + x] = k;
        if (k === 6) { colB[x]++; rowB[y]++; }
      }
    }
    let x0 = 0, x1 = gw - 1, y0 = 0, y1 = gh - 1;
    const thr = 2;
    while (x0 < gw && colB[x0] < thr) x0++;
    while (x1 > 0 && colB[x1] < thr) x1--;
    while (y0 < gh && rowB[y0] < thr) y0++;
    while (y1 > 0 && rowB[y1] < thr) y1--;
    let blue = 0; for (let i = 0; i < gh; i++) blue += rowB[i];
    if (captureRef) window.__ref = { cls: cls.slice(), gw, gh, S };
    const ref = window.__ref;

    const seen = new Uint8Array(gw * gh);
    const blobs = { 1: [], 2: [], 3: [], 4: [], 5: [] };
    const q = new Int32Array(gw * gh);
    for (let p = 0; p < gw * gh; p++) {
      const k = cls[p];
      if (k < 1 || k > 5 || seen[p]) continue;
      let qh = 0, qt = 0; q[qt++] = p; seen[p] = 1;
      let n = 0, sx = 0, sy = 0, mnx = 1e9, mxx = -1, mny = 1e9, mxy = -1;
      while (qh < qt) {
        const cur = q[qh++]; const cx = cur % gw, cy = (cur / gw) | 0;
        n++; sx += cx; sy += cy;
        if (cx < mnx) mnx = cx; if (cx > mxx) mxx = cx; if (cy < mny) mny = cy; if (cy > mxy) mxy = cy;
        for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
          const nx = cx + dx, ny = cy + dy;
          if (nx < 0 || ny < 0 || nx >= gw || ny >= gh) continue;
          const np = ny * gw + nx;
          if (!seen[np] && cls[np] === k) { seen[np] = 1; q[qt++] = np; }
        }
      }
      const bw = mxx - mnx + 1, bh = mxy - mny + 1;
      const gx = Math.round(sx / n), gy = Math.round(sy / n);
      let onWall = false;
      if (ref && ref.gw === gw && ref.gh === gh) onWall = ref.cls[gy * gw + gx] === 6;
      blobs[k].push({ x: (sx / n) * S, y: (sy / n) * S, n: n * S * S, w: bw * S, h: bh * S, onWall });
    }
    for (const k in blobs) blobs[k] = blobs[k].sort((a, b) => b.n - a.n).slice(0, 4);
    return { W, H, S, bbox: [x0 * S, y0 * S, (x1 + 1) * S, (y1 + 1) * S], blue: blue * S * S, blobs,
             scrollY: window.scrollY, frames: A.frames };
  };
})();
