/* Dizaster · render de carta en HTML/CSS (sin imagen): DZCard.html(card, meta, {text}) */
(function () {
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  function rng(seed) { let h = 2166136261; for (const ch of seed) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); } return () => ((h = Math.imul(h ^ (h >>> 15), 2246822507) ^ Math.imul(h ^ (h >>> 13), 3266489909)) >>> 0) / 4294967296; }
  // rayo zigzag con ramas, sobre un viewBox 200×300
  function bolt(r, x0, y0, x1, y1, steps, amp) {
    let d = `M${x0.toFixed(1)} ${y0.toFixed(1)}`, pts = [];
    for (let i = 1; i <= steps; i++) {
      const t = i / steps, x = x0 + (x1 - x0) * t + (i < steps ? (r() - .5) * amp : 0), y = y0 + (y1 - y0) * t + (i < steps ? (r() - .5) * amp * .5 : 0);
      d += ` L${x.toFixed(1)} ${y.toFixed(1)}`; pts.push([x, y]);
    }
    return { d, pts };
  }
  function bolts(code, corner) {
    const r = rng(code + corner); let paths = [];
    const main = corner === 'tl' ? bolt(r, 6 + r() * 4, 46, 3 + r() * 5, 150 + r() * 25, 11, 9) : bolt(r, 196 - r() * 5, 290, 193 - r() * 6, 175 - r() * 25, 11, 9);
    paths.push(main.d);
    const nb = 3 + Math.floor(r() * 3);
    for (let i = 0; i < nb; i++) {
      const p = main.pts[1 + Math.floor(r() * (main.pts.length - 2))];
      const dx = corner === 'tl' ? 10 + r() * 22 : -(10 + r() * 22), dy = (r() - .4) * 26;
      paths.push(bolt(r, p[0], p[1], p[0] + dx, p[1] + dy, 4, 6).d);
    }
    if (corner === 'tl') paths.push(bolt(r, 40, 6, 70 + r() * 20, 4 + r() * 5, 6, 5).d);
    else paths.push(bolt(r, 160, 296, 128 - r() * 22, 294 - r() * 4, 6, 5).d);
    const g = paths.map(d => `<path class="glow" d="${d}"/>`).join('');
    const c = paths.map((d, i) => `<path class="core" d="${d}"/>` + (i === 0 ? `<path class="core hi" d="${d}"/>` : '')).join('');
    return `<g class="${corner}">${g}${c}</g>`;
  }
  // texto → oraciones (salto de línea tras cada punto y seguido), arranque en negritas
  function sentences(t) {
    const out = []; let s = String(t || '').trim();
    const re = /(?<=[.!?»])\s+(?=[«¿¡A-ZÁÉÍÓÚÑ0-9⛔])/u;
    return s.split(re).filter(Boolean);
  }
  function fmt(s) {
    let h = esc(s).replace(/⛔[^.]*\.?/g, m => `<span class="pend">${m}</span>`);
    h = h.replace(/^(Furia:|Vestigio:)/, '<b>$1</b>');
    const m = h.match(/^([^:<]{6,64}):\s/);
    if (m && !/^<b>/.test(h)) h = `<b>${m[1]}:</b>` + h.slice(m[0].length - 1);
    return h;
  }
  function html(card, meta, opt = {}) {
    const key = opt.text || meta.texto_activo || 'referencia';
    const tx = card.texts[key] || card.texts.referencia;
    let body = tx.cuerpo || card.texts.referencia.cuerpo;
    let refs = tx.reglas || (key === 'referencia' ? card.texts.referencia.reglas : []);
    if (key === 'propuesta' && tx.cuerpo) {           // la propuesta trae las reglas entre paréntesis
      refs = tx.reglas || []; body = body.replace(/\s*\((?:\d{1,2}\.\d{1,2}(?:\.\d{1,2})?(?:\s*[,y·]\s*)?)+\)/g, '').replace(/\s+([.,;:])/g, '$1');
      body = body.replace(/^Instantáneo(?: con Furia)?\.\s*/, '');
    }
    const title = (key === 'propuesta' && tx.titulo) ? tx.titulo : card.name.es;
    const ev = card.deck === 'evento';
    const deckColor = meta.mazos[card.deck].color;
    const sent = sentences(body);
    const nwords = body.split(/\s+/).length;
    const bs = nwords > 70 ? 3.7 : nwords > 52 ? 4.15 : nwords > 38 ? 4.5 : nwords > 24 ? 4.9 : 5.3;
    const ts = title.length > 22 ? 5.2 : title.length > 18 ? 5.9 : 6.9;
    const lines = sent.map((s, i) => `<p>${i === 0 ? '«' : ''}${fmt(s)}${i === sent.length - 1 ? '»' : ''}</p>`).join('');
    const clsName = meta.clases[card.clase].nombre;
    const typeName = ev ? meta.familias[card.familia].replace(/ \(.*\)/, '') : meta.tipos[card.type].nombre;
    const mod = card.mods[0];
    const modHtml = card.mods.map(m => `<span class="dzc-mod" title="${meta.mods[m].nombre}" aria-label="${meta.mods[m].nombre}">${meta.mods[m].simbolo}</span>`).join('');
    const oct = ev ? '<span class="txt">EV</span>' : `<span title="${typeName}">${meta.tipos[card.type].simbolo}</span>`;
    const rule = refs.length ? `<div class="dzc-rule"><i>◆</i>${refs.length > 1 ? 'Reglas' : 'Regla'} ${refs.join(' · ')}<i>◆</i></div>` : '';
    const n = String(card.n).padStart(2, '0');
    return `<div class="dzc-box"><div class="dzc${ev ? ' ev' : ''}" style="--cc:${card.color};--dc:${deckColor}" role="img" aria-label="Carta ${esc(card.code)} · ${esc(title)}">
  <div class="dzc-face">
    <svg class="dzc-bolts" viewBox="0 0 200 300" preserveAspectRatio="none" aria-hidden="true">${bolts(card.code, 'tl')}${bolts(card.code, 'br')}</svg>
    <div class="dzc-head"><span class="dzc-class">${esc(clsName)}</span>${modHtml}</div>
    <div class="dzc-titlewrap"><div class="dzc-badge"><div class="dzc-title" style="--ts:${ts}cqw">${esc(title)}</div></div><div class="dzc-type">${esc(typeName)}</div></div>
    <div class="dzc-body" style="--bs:${bs}cqw">${lines}</div>
    <div class="dzc-oct">${oct}</div>
    ${rule}
    ${card.qty > 1 ? `<div class="dzc-qty">×${card.qty}</div>` : ''}
    <div class="dzc-code">${esc(card.code)}<small>#${n} / ${card.of}</small></div>
  </div>
  <div class="dzc-gem"><img src="assets/gems/${card.gem}" alt="" loading="lazy" decoding="async" width="240" height="240"></div>
</div></div>`;
  }
  window.DZCard = { html, sentences, esc };
})();
