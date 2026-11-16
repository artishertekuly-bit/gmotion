// kz-kinetic-studio Shared Deterministic Transparent Hero Hook Core (v3)
// Zero black screen backdrops, zero neon boxes. Every pixel renders on transparent alpha canvas.
(function (global) {
  'use strict';

  const W = 880, H = 420;
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const lerp = (a, b, u) => a + (b - a) * u;
  const seg = (t, a, b) => clamp((t - a) / Math.max(b - a, 1e-6));
  const smoothstep = (u) => {
    const x = clamp(u, 0, 1);
    return x * x * (3 - 2 * x);
  };
  const easeOutCubic = (u) => 1 - Math.pow(1 - clamp(u), 3);

  function springPhys(t, stiffness = 240, damping = 18, mass = 1.0) {
    if (t <= 0) return 0;
    const w = Math.sqrt(stiffness / mass);
    const z = damping / (2 * Math.sqrt(stiffness * mass));
    if (z < 1.0) {
      const wd = w * Math.sqrt(1 - z * z);
      return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + (z * w / wd) * Math.sin(wd * t));
    }
    return 1 - Math.exp(-w * t) * (1 + w * t);
  }

  function hexToRgb(hex) {
    const h = (hex || '#FFD600').replace('#', '');
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
  }
  function mixColor(c1, c2, u) {
    const x = clamp(u);
    const a = hexToRgb(c1), b = hexToRgb(c2);
    return `rgb(${Math.round(Math.sqrt(lerp(a[0] * a[0], b[0] * b[0], x)))}, ${Math.round(Math.sqrt(lerp(a[1] * a[1], b[1] * b[1], x)))}, ${Math.round(Math.sqrt(lerp(a[2] * a[2], b[2] * b[2], x)))})`;
  }

  function formatSpaced(n) {
    const iv = Math.round(n);
    return String(iv).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }

  function envelope(t, dur, enterDur = 0.42, exitDur = 0.34) {
    const d = Math.max(dur || 3.5, enterDur + exitDur + 0.1);
    const enter = springPhys(t, 240, 18);
    const out = 1 - smoothstep(seg(t, d - exitDur, d));
    return { enter, out, alpha: clamp(clamp(t / 0.14) * out) };
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

  function drawGlassPanel(ctx, x, y, w, h, r, opts = {}) {
    ctx.save();
    ctx.shadowColor = opts.shadowColor || 'rgba(0, 0, 0, 0.48)';
    ctx.shadowBlur = opts.shadowBlur ?? 34;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = opts.shadowOffsetY ?? 14;
    roundRectPath(ctx, x, y, w, h, r);
    const g = ctx.createLinearGradient(x, y, x, y + h);
    g.addColorStop(0, opts.topFill || 'rgba(28, 32, 44, 0.72)');
    g.addColorStop(1, opts.botFill || 'rgba(14, 16, 22, 0.80)');
    ctx.fillStyle = g;
    ctx.fill();
    ctx.restore();

    // Inner specular frosted sheen + delicate glass hairline
    ctx.save();
    roundRectPath(ctx, x, y, w, h, r);
    ctx.clip();
    const sheen = ctx.createLinearGradient(x, y, x + w * 0.4, y + h * 0.55);
    sheen.addColorStop(0, 'rgba(255, 255, 255, 0.18)');
    sheen.addColorStop(0.5, 'rgba(255, 255, 255, 0.04)');
    sheen.addColorStop(1, 'rgba(255, 255, 255, 0.0)');
    ctx.fillStyle = sheen;
    ctx.fillRect(x, y, w, h);
    ctx.restore();

    ctx.save();
    roundRectPath(ctx, x + 0.75, y + 0.75, w - 1.5, h - 1.5, Math.max(2, r - 0.75));
    ctx.strokeStyle = opts.borderColor || 'rgba(255, 255, 255, 0.34)';
    ctx.lineWidth = opts.borderWidth ?? 1.6;
    ctx.stroke();
    ctx.restore();
  }

  function getConfig(defaults) {
    const p = Object.assign({}, global.EDL_PAYLOAD || {}, global.__HOOK_PARAMS__ || {});
    const cW = Number(p.W) || (defaults && defaults.W) || W;
    const cH = Number(p.H) || (defaults && defaults.H) || H;
    return Object.assign({
      dur: 3.6,
      accent: '#FFD600',
      accent2: '#F59E0B',
      danger: '#E03B24',
      ink: '#1A1410',
      W: cW,
      H: cH,
      cx: cW * 0.5,
      cy: cH * 0.5,
      title: '',
      subtitle: '',
      label: '',
      stamp: '',
      asset: 'compass',
      spoken_words: '',
      from: 0,
      to: 0,
      suffix: '',
      kpis: [],
      items: [],
      words: [],
    }, defaults || {}, p);
  }

  function deriveText(cfg) {
    const sw = String(cfg.spoken_words || '').trim();
    const tokens = sw ? sw.split(/\s+/).filter(Boolean) : [];
    const title = String(cfg.title || tokens.slice(0, 3).join(' ')).trim();
    const subtitle = String(cfg.subtitle || tokens.slice(3, 7).join(' ')).trim();
    const label = String(cfg.label || '').trim();
    return { title, subtitle, label, tokens };
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
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
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

  function initStage(renderFn, imageMap, defaults) {
    const cfg = getConfig(defaults);
    const canvas = document.getElementById('stage') || document.querySelector('canvas');
    if (!canvas) return;
    canvas.width = cfg.W;
    canvas.height = cfg.H;
    canvas.style.width = cfg.W + 'px';
    canvas.style.height = cfg.H + 'px';
    if (document.documentElement) document.documentElement.style.background = 'transparent';
    if (document.body) document.body.style.background = 'transparent';

    const ctx = canvas.getContext('2d', { alpha: true });
    const imgs = loadImages(imageMap || {});

    function drawAt(t) {
      const tt = Math.max(0, Number(t) || 0);
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.globalAlpha = 1;
      ctx.clearRect(0, 0, cfg.W, cfg.H);
      renderFn(ctx, tt, imgs, cfg);
      ctx.restore();
    }

    global.seek = drawAt;
    global.__HOOK_READY__ = true;
    if (global.__HOOK_ASSETS_READY__) {
      global.__HOOK_ASSETS_READY__.then(() => drawAt(0));
    } else {
      drawAt(0);
    }
  }

  global.HookCore = {
    W, H, clamp, lerp, seg, smoothstep, easeOutCubic,
    springPhys, mixColor, formatSpaced, envelope, roundRectPath,
    drawGlassPanel, getConfig, deriveText, loadImages, drawAsset, initStage,
  };
})(window);
