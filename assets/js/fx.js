/* Dizaster · fondo animado: brasas cian/púrpura + relámpagos tenues. Respeta prefers-reduced-motion. */
(function () {
  const cv = document.getElementById('fx'); if (!cv) return;
  const ctx = cv.getContext('2d'); const btn = document.getElementById('fxtoggle');
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let on = localStorage.getItem('dz-fx') !== 'off' && !reduce, W, H, dpr, parts = [], bolts = [], raf = 0, last = 0;
  const COLORS = ['53,208,223', '131,71,182', '176,126,224', '233,228,212'];
  function size() { dpr = Math.min(devicePixelRatio || 1, 2); W = innerWidth; H = innerHeight; cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); }
  function spawn(init) {
    return { x: Math.random() * W, y: init ? Math.random() * H : H + 10, r: .6 + Math.random() * 1.8, vy: .15 + Math.random() * .5, vx: (Math.random() - .5) * .2,
      a: .15 + Math.random() * .5, c: COLORS[Math.random() < .5 ? 0 : Math.random() < .7 ? 1 : Math.random() < .5 ? 2 : 3], ph: Math.random() * 6.28 };
  }
  function mkBolt() {
    const x = Math.random() * W, pts = [[x, -10]]; let y = -10, cx = x;
    while (y < H * (.35 + Math.random() * .4)) { y += 18 + Math.random() * 30; cx += (Math.random() - .5) * 60; pts.push([cx, y]); }
    return { pts, life: 1, c: Math.random() < .5 ? COLORS[0] : COLORS[1] };
  }
  function frame(t) {
    raf = requestAnimationFrame(frame); const dt = Math.min(50, t - last); last = t;
    ctx.clearRect(0, 0, W, H);
    for (const p of parts) {
      p.y -= p.vy * dt * .06; p.x += p.vx * dt * .06 + Math.sin(t / 1400 + p.ph) * .08; if (p.y < -10) Object.assign(p, spawn(false));
      const tw = .6 + .4 * Math.sin(t / 600 + p.ph);
      ctx.beginPath(); ctx.fillStyle = `rgba(${p.c},${p.a * tw})`; ctx.shadowColor = `rgba(${p.c},.9)`; ctx.shadowBlur = 8; ctx.arc(p.x, p.y, p.r, 0, 6.28); ctx.fill();
    }
    ctx.shadowBlur = 0;
    if (Math.random() < .0025 && bolts.length < 1) bolts.push(mkBolt());
    for (const b of bolts) {
      ctx.beginPath(); b.pts.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
      ctx.strokeStyle = `rgba(${b.c},${.35 * b.life})`; ctx.lineWidth = 2; ctx.shadowColor = `rgba(${b.c},1)`; ctx.shadowBlur = 18; ctx.stroke();
      ctx.strokeStyle = `rgba(255,255,255,${.25 * b.life})`; ctx.lineWidth = .7; ctx.stroke(); ctx.shadowBlur = 0;
      b.life -= dt / 700;
    }
    bolts = bolts.filter(b => b.life > 0);
  }
  function start() { size(); parts = Array.from({ length: Math.round(Math.min(90, W * H / 16000)) }, () => spawn(true)); cancelAnimationFrame(raf); last = performance.now(); raf = requestAnimationFrame(frame); cv.style.display = ''; }
  function stop() { cancelAnimationFrame(raf); ctx && ctx.clearRect(0, 0, W, H); cv.style.display = 'none'; }
  function set(v) { on = v; localStorage.setItem('dz-fx', v ? 'on' : 'off'); btn && btn.setAttribute('aria-pressed', String(v)); v ? start() : stop(); }
  addEventListener('resize', () => { if (on) size(); });
  document.addEventListener('visibilitychange', () => { if (!on) return; document.hidden ? cancelAnimationFrame(raf) : (last = performance.now(), raf = requestAnimationFrame(frame)); });
  btn && btn.addEventListener('click', () => set(!on));
  set(on);
})();
