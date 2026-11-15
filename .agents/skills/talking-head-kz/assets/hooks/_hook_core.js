// Mastery V2 Shared Deterministic Hook Engine (lemo-opuscar + rossark + reanimate + pixelfx + three.js math)
// Zero timers/random; every pixel derived purely from `window.seek(t)` and `window.__HOOK_PARAMS__`.
(function (global) {
  'use strict';

  const W = 1080, H = 1920;
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const lerp = (a, b, u) => a + (b - a) * u;
  const seg = (t, a, b) => clamp((t - a) / Math.max(b - a, 1e-6));
  const smoothstep = (u) => {
    const x = clamp(u, 0, 1);
    return x * x * (3 - 2 * x);
  };
  const easeOutCubic = (u) => 1 - Math.pow(1 - clamp(u), 3);

  // Closed-form analytic spring from reanimate / rossark: default stiffness=220, damping=18
  function springPhys(t, stiffness = 220, damping = 18, mass = 1.0) {
    if (t <= 0) return 0;
    const w = Math.sqrt(stiffness / mass);
    const z = damping / (2 * Math.sqrt(stiffness * mass));
    if (z < 1.0) {
      const wd = w * Math.sqrt(1 - z * z);
      return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + (z * w / wd) * Math.sin(wd * t));
    }
    return 1 - Math.exp(-w * t) * (1 + w * t);
  }

  // Perceptual gamma-squared RGB interpolation (from reanimate motion.js)
  function hexToRgb(hex) {
    const h = (hex || '#FFD600').replace('#', '');
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
  }
  function mixColor(c1, c2, u) {
    const x = clamp(u);
    const a = hexToRgb(c1), b = hexToRgb(c2);
    const r = Math.round(Math.sqrt(lerp(a[0] * a[0], b[0] * b[0], x)));
    const g = Math.round(Math.sqrt(lerp(a[1] * a[1], b[1] * b[1], x)));
    const bl = Math.round(Math.sqrt(lerp(a[2] * a[2], b[2] * b[2], x)));
    return `rgb(${r}, ${g}, ${bl})`;
  }

  function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function hash2(ix, iy, seed = 1337) {
    let n = Math.imul(ix, 374761393) + Math.imul(iy, 668265263) + Math.imul(seed, 1442695041);
    n = (n ^ (n >>> 13)) | 0;
    n = Math.imul(n, 1274126177);
    return ((n ^ (n >>> 16)) >>> 0) / 4294967295;
  }

  function vnoise2d(x, y, seed = 1337) {
    const ix = Math.floor(x), iy = Math.floor(y);
    const fx = smoothstep(x - ix), fy = smoothstep(y - iy);
    const a = hash2(ix, iy, seed), b = hash2(ix + 1, iy, seed);
    const c = hash2(ix, iy + 1, seed), d = hash2(ix + 1, iy + 1, seed);
    return lerp(lerp(a, b, fx), lerp(c, d, fx), fy);
  }

  function envelope(t, dur, enterDur = 0.45, exitDur = 0.35) {
    const d = Math.max(dur || 3.5, enterDur + exitDur + 0.1);
    const eIn = springPhys(t, 220, 18);
    const eOut = 1 - smoothstep(seg(t, d - exitDur, d));
    return { enter: eIn, out: eOut, alpha: clamp(clamp(t / 0.14) * eOut) };
  }

  function roundRectPath(ctx, x, y, w, h, r) {
    const rad = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + rad, y);
    ctx.lineTo(x + w - rad, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + rad);
    ctx.lineTo(x + w, y + h - rad);
    ctx.quadraticCurveTo(x + w, y + h, x + w - rad, y + h);
    ctx.lineTo(x + rad, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - rad);
    ctx.lineTo(x, y + rad);
    ctx.quadraticCurveTo(x, y, x + rad, y);
    ctx.closePath();
  }

  function getConfig(defaults) {
    const p = global.__HOOK_PARAMS__ || {};
    return Object.assign({
      dur: 3.5,
      accent: '#FFD600',
      accent2: '#00E676',
      danger: '#ED3B22',
      title: '',
      subtitle: '',
      label: '',
      from: 0,
      to: 100,
      suffix: '%',
      words: [],
    }, defaults || {}, p);
  }

  function loadImages(relMap) {
    const pAssets = (global.__HOOK_PARAMS__ && global.__HOOK_PARAMS__.assets) || {};
    const out = {};
    const promises = [];
    for (const [k, rel] of Object.entries(relMap || {})) {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      const src = pAssets[k] || rel;
      const pr = new Promise((resolve) => {
        img.onload = () => resolve();
        img.onerror = () => resolve();
      });
      img.src = src;
      out[k] = img;
      promises.push(pr);
    }
    global.__HOOK_ASSETS_READY__ = Promise.all(promises);
    return out;
  }

  function drawAsset(ctx, img, cx, cy, w, h, alpha = 1, rotRad = 0, scaleX = 1, scaleY = 1) {
    if (!img || !img.complete || !img.naturalWidth) return;
    ctx.save();
    ctx.globalAlpha *= clamp(alpha);
    ctx.translate(cx, cy);
    if (rotRad) ctx.rotate(rotRad);
    ctx.scale(scaleX, scaleY);
    const aspect = img.naturalWidth / Math.max(img.naturalHeight, 1);
    let dw = w, dh = h;
    if (!dh && dw) dh = dw / aspect;
    else if (!dw && dh) dw = dh * aspect;
    ctx.drawImage(img, -dw / 2, -dh / 2, dw, dh);
    ctx.restore();
  }

  function initStage(renderFn, relImages) {
    const canvas = document.getElementById('stage') || (() => {
      const c = document.createElement('canvas');
      c.id = 'stage'; c.width = W; c.height = H;
      document.body.appendChild(c);
      return c;
    })();
    const ctx = canvas.getContext('2d');
    const imgs = loadImages(relImages);
    global.seek = function (t) {
      ctx.clearRect(0, 0, W, H);
      renderFn(ctx, t, imgs, getConfig());
    };
    global.seek(0);
    return imgs;
  }

  global.HookCore = {
    W, H, clamp, lerp, seg, smoothstep, easeOutCubic, springPhys, mixColor,
    mulberry32, vnoise2d, envelope, roundRectPath, getConfig, loadImages, drawAsset, initStage,
  };
})(window);
