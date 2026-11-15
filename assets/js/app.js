/* Dizaster · sitio de consulta (sin build): reglamento, glosario y cartas desde data/*.json */
(function () {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const norm = s => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const debounce = (f, ms = 140) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => f(...a), ms); }; };
  const anchor = id => 'r-' + id.replace(/\./g, '-');
  let RULES, CARDS, META, GLOSS, RULE_IDS = new Set(), BYCODE = {};

  // ── utilidades de enlace ──
  function rref(id) { return RULE_IDS.has(id) ? `<a class="rref" href="#${anchor(id)}">${id}</a>` : esc(id); }
  function linkify(text) {   // escapa y enlaza «12.3» y códigos de carta
    let h = esc(text);
    h = h.replace(/(?<![\w.])(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)(?![\w.]*\d)/g, m => RULE_IDS.has(m) ? rref(m) : m);
    h = h.replace(/\b(EV\d{2}|[ADEICRX]\d{2})\b/g, m => BYCODE[m] ? cardLink(m) : m);
    return h;
  }
  function cardLink(code) { const c = BYCODE[code]; return `<a class="clink" href="#carta-${code}" style="--c:${c.color}" title="${esc(c.name.es)}">${code}</a>`; }
  // regex insensible a acentos para resaltar
  const ACC = { a: '[aáàäâ]', e: '[eéèëê]', i: '[iíìïî]', o: '[oóòöô]', u: '[uúùüû]', n: '[nñ]' };
  function hlRegex(q) {
    const toks = norm(q).split(/\s+/).filter(t => t.length > 1);
    if (!toks.length) return null;
    const src = toks.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/[aeioun]/g, ch => ACC[ch])).join('|');
    return new RegExp(src, 'gi');
  }
  function highlight(root, re) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, { acceptNode: n => n.parentElement.closest('mark,script,style') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
    const nodes = []; while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const n of nodes) {
      re.lastIndex = 0; if (!re.test(n.nodeValue)) continue; re.lastIndex = 0;
      const frag = document.createDocumentFragment(); let i = 0, m; const s = n.nodeValue;
      while ((m = re.exec(s))) { frag.append(s.slice(i, m.index)); const mk = document.createElement('mark'); mk.textContent = m[0]; frag.append(mk); i = m.index + m[0].length; if (!m[0].length) re.lastIndex++; }
      frag.append(s.slice(i)); n.replaceWith(frag);
    }
  }
  function unhighlight(root) { $$('mark', root).forEach(m => m.replaceWith(m.textContent)); root.normalize(); }

  // ── carga ──
  Promise.all(['data/rules.json', 'data/cards.json', 'data/glossary.json'].map(u => fetch(u).then(r => { if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); })))
    .then(([r, c, g]) => {
      RULES = r; CARDS = c.cards; META = c.meta; GLOSS = g.terms;
      r.items.forEach(x => RULE_IDS.add(x.id)); CARDS.forEach(x => BYCODE[x.code] = x);
      renderHome(); renderRules(); renderGloss(); initCards(); initNav(); handleHash(true);
    })
    .catch(err => { console.error(err); $('#rules').innerHTML = `<p class="noresult">No se pudieron cargar los datos (${esc(err.message)}). Abre el sitio desde un servidor (p. ej. <code>python3 -m http.server</code>).</p>`; });

  // ── 1 · inicio ──
  function renderHome() {
    $$('.steps').forEach(ol => [...ol.children].forEach((li, i) => li.dataset.n = (ol.start || 1) + i));
    const d = META.mazos;
    const tile = (k, txt) => `<div class="deck" style="--c:${d[k].color}"><img src="assets/gems/${d[k].gem}" alt="" width="56" height="56"><div><h3>${d[k].nombre}</h3><p>${txt}</p></div></div>`;
    $('#decks').innerHTML = tile('asalto', `${d.asalto['diseños']} diseños · ${d.asalto.copias} ejemplares. Robas 1 al inicio de cada turno. ${rref('4.3.1')}`) +
      tile('dominio', `${d.dominio['diseños']} diseños · ${d.dominio.copias} ejemplares. 1 carta cada vez que una pieza termina en una casilla de Dominio. ${rref('4.3.2')}`) +
      tile('evento', `43 cartas únicas. Abren cada ronda; al agotarse, el descarte se rebaraja. ${rref('4.3.3')}`);
    if ($('#news')) $('#news').innerHTML = RULES.novedades.map(n => `<li><span class="v">v${n.version}</span>${n.titulo ? `<b class="t">${esc(n.titulo[0].toUpperCase() + n.titulo.slice(1))}.</b> ` : ''}${n.html}</li>`).join('');
  }

  // ── 3 · reglamento ──
  function renderRules() {
    const box = $('#rules'); let html = `<div class="rintro">${RULES.intro_html}</div>`;
    if (RULES.novedades.length) html += `<details class="rnews"><summary>Novedades</summary>${RULES.novedades.map(n => `<p><b>v${n.version}${n.titulo ? ' · ' + esc(n.titulo) : ''}.</b> ${n.html}</p>`).join('')}</details>`;
    let open = false;
    for (const it of RULES.items) {
      if (it.level === 1) { if (open) html += '</div>'; html += `<div class="chap" data-chap="${it.id}">`; open = true; }
      const tag = it.level === 1 ? 'h3' : it.level === 2 ? 'h4' : 'h5';
      html += `<div class="rule l${it.level}" id="${it.anchor}" data-id="${it.id}"><${tag}><a class="rid" href="#${it.anchor}" title="Enlace a ${it.id}">${it.id}</a><span>${esc(it.title)}</span><button class="copyl" data-copy="${it.anchor}" title="Copiar enlace">copiar enlace</button></${tag}>${it.html}</div>`;
    }
    if (open) html += '</div>';
    box.innerHTML = html;
    $('#toc').innerHTML = RULES.chapters.map(c => `<li><a href="#${c.anchor}" data-chap="${c.id}"><span class="n">${c.id}</span>${esc(c.title)}</a></li>`).join('');
    const hay = new Map(RULES.items.map(it => [it.id, norm(it.id + ' ' + it.title + ' ' + it.text)]));
    const run = () => {
      const q = $('#rq').value.trim(); unhighlight(box); const nq = norm(q);
      const toks = nq.split(/\s+/).filter(Boolean);
      if (!toks.length) { $$('.rule,.chap', box).forEach(e => e.classList.remove('hide')); $$('#toc a').forEach(a => a.classList.remove('dim')); $('#rcount').textContent = ''; $('.rintro', box).hidden = false; if ($('.rnews', box)) $('.rnews', box).hidden = false; return; }
      $('.rintro', box).hidden = true; if ($('.rnews', box)) $('.rnews', box).hidden = true;
      let n = 0; const chapHit = new Set();
      for (const el of $$('.rule', box)) {
        const ok = toks.every(t => hay.get(el.dataset.id).includes(t));
        el.classList.toggle('hide', !ok); if (ok) { n++; chapHit.add(el.closest('.chap').dataset.chap); }
      }
      $$('.chap', box).forEach(c => { const hit = chapHit.has(c.dataset.chap); c.classList.toggle('hide', !hit); if (hit) c.querySelector('.rule.l1').classList.remove('hide'); });
      $$('#toc a').forEach(a => a.classList.toggle('dim', !chapHit.has(a.dataset.chap)));
      $('#rcount').textContent = n ? `${n} apartado${n > 1 ? 's' : ''} con «${q}»` : 'Sin resultados';
      const re = hlRegex(q); if (re) $$('.rule:not(.hide)', box).forEach(el => highlight(el, re));
      if (!n && !$('.noresult', box)) box.insertAdjacentHTML('beforeend', '<p class="noresult">Sin resultados en el reglamento.</p>');
      if (n) $$('.noresult', box).forEach(e => e.remove());
    };
    $('#rq').addEventListener('input', debounce(run));
    box.addEventListener('click', e => {
      const b = e.target.closest('[data-copy]'); if (!b) return;
      const url = location.origin + location.pathname + '#' + b.dataset.copy;
      (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).then(() => { b.textContent = '¡copiado!'; setTimeout(() => b.textContent = 'copiar enlace', 1200); }).catch(() => { });
    });
    // scrollspy del índice
    const obs = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { const id = e.target.dataset.chap; $$('#toc a').forEach(a => a.classList.toggle('on', a.dataset.chap === id)); } }), { rootMargin: '-30% 0px -60% 0px' });
    $$('.chap', box).forEach(c => obs.observe(c));
  }
  function clearRuleSearch() { const i = $('#rq'); if (i.value) { i.value = ''; i.dispatchEvent(new Event('input')); } }

  // ── glosario ──
  function renderGloss() {
    const letter = t => norm(t.termino)[0].toUpperCase();
    const letters = [...new Set(GLOSS.map(letter))];
    $('#az').innerHTML = 'ABCDEFGHIJKLMNÑOPQRSTUVWXYZ'.split('').map(L => letters.includes(L) ? `<a href="#gl-${L}">${L}</a>` : `<a class="off" aria-disabled="true">${L}</a>`).join('');
    let prev = '';
    $('#gloss').innerHTML = GLOSS.map(g => {
      const L = letter(g); const first = L !== prev; prev = L;
      return `<div class="gterm" ${first ? `id="gl-${L}"` : ''} data-h="${esc(norm(g.termino + ' ' + g.def))}"><dt>${first ? `<span class="L">${L}</span>` : ''}${esc(g.termino)}</dt><dd>${linkify(g.def)}<div class="refs">${g.reglas.map(rref).join('')}</div></dd></div>`;
    }).join('');
    $('#gq').addEventListener('input', debounce(() => {
      const toks = norm($('#gq').value).split(/\s+/).filter(Boolean);
      $$('.gterm').forEach(el => el.classList.toggle('hide', !toks.every(t => el.dataset.h.includes(t))));
    }));
  }

  // ── 4 · cartas ──
  const F = { q: '', deck: '', clase: '', tipo: '', mod: '', modo: '', avisos: false };
  function initCards() {
    const clases = Object.entries(META.clases);
    $('#fclase').innerHTML += clases.map(([k, v]) => `<option value="${k}">${v.nombre}</option>`).join('');
    CARDS.forEach(c => c._h = norm([c.code, c.name.es, c.name.en, c.texts.final.completo, c.texts.referencia.completo, c.texts.catalogo.cuerpo, c.texts.original.cuerpo, META.clases[c.clase].nombre, META.tipos[c.type].nombre, c.mods.join(' '), c.deck].join(' ')));
    $('#cq').addEventListener('input', debounce(e => { F.q = e.target.value; renderGrid(); }, 100));
    $('#fdeck').addEventListener('click', e => { const b = e.target.closest('.chip'); if (!b) return; $$('#fdeck .chip').forEach(x => x.classList.toggle('on', x === b)); F.deck = b.dataset.v; renderGrid(); });
    $('#fclase').addEventListener('change', e => { F.clase = e.target.value; renderGrid(); });
    $('#ftipo').addEventListener('change', e => { F.tipo = e.target.value; renderGrid(); });
    $('#fmod').addEventListener('change', e => { F.mod = e.target.value; renderGrid(); });
    $('#fmodo').addEventListener('change', e => { F.modo = e.target.value; renderGrid(); });
    $('#favisos').addEventListener('change', e => { F.avisos = e.target.checked; renderGrid(); });
    $('#grid').addEventListener('click', e => { const b = e.target.closest('.cbtn'); if (b) { e.preventDefault(); location.hash = 'carta-' + b.dataset.code; } });
    renderGrid();
    const dlg = $('#detail');
    dlg.addEventListener('click', e => {
      if (e.target === dlg || e.target.closest('[data-close]')) { closeDetail(); return; }
      const tab = e.target.closest('[data-text]'); if (tab) { showText(tab.dataset.text); return; }
    });
    dlg.addEventListener('cancel', e => { e.preventDefault(); closeDetail(); });
    dlg.addEventListener('keydown', e => { if (e.key === 'ArrowRight') step(1); if (e.key === 'ArrowLeft') step(-1); });
    $('#d-prev').addEventListener('click', () => step(-1)); $('#d-next').addEventListener('click', () => step(1));
  }
  let VISIBLE = [];
  function filtered() {
    const toks = norm(F.q).split(/\s+/).filter(Boolean);
    return CARDS.filter(c => (!F.deck || c.deck === F.deck) && (!F.clase || c.clase === F.clase) && (!F.tipo || c.type === F.tipo) &&
      (!F.mod || (F.mod === 'none' ? !c.mods.length : c.mods.includes(F.mod))) && (!F.modo || c.modo.includes(F.modo)) &&
      (!F.avisos || c.avisos.length || c.notas.length) && toks.every(t => c._h.includes(t) || c.code.toLowerCase() === t));
  }
  function renderGrid() {
    const list = filtered(); VISIBLE = list.map(c => c.code);
    const groups = ['asalto', 'dominio', 'evento'];
    let html = '';
    for (const g of groups) {
      const cs = list.filter(c => c.deck === g); if (!cs.length) continue;
      html += `<h3 class="cgroup" style="--c:${META.mazos[g].color}">${META.mazos[g].nombre} <small>${cs.length} de ${META.mazos[g]['diseños']}</small></h3>`;
      html += cs.map(c => `<div><a class="cbtn" href="#carta-${c.code}" data-code="${c.code}" style="--cc:${c.color}" aria-label="Abrir ${c.code} · ${esc(c.name.es)}">${DZCard.html(c, META)}</a>
        <div class="cmeta"><span>${c.code} · ${c.qty > 1 ? '×' + c.qty : '1 ejemplar'}</span>${c.avisos.length || c.notas.length ? `<span class="warn" title="Tiene avisos o decisiones pendientes">⚠ ${c.avisos.length + c.notas.length}</span>` : ''}</div></div>`).join('');
    }
    $('#grid').innerHTML = html || '<p class="noresult" style="grid-column:1/-1">Ninguna carta coincide con la búsqueda.</p>';
    $('#ccount').textContent = `${list.length} de ${CARDS.length} cartas`;
  }

  // ── detalle ──
  let CUR = null, CURTEXT = null;
  function responders(c) {
    const out = [];
    if (c.mods.includes('furia')) return [['Inmune', `Lleva Furia: ninguna carta puede cancelarla, redirigirla, copiarla ni reactivarla; la que lo intente se descarta sin efecto (10.5.1).`]];
    if (c.deck === 'evento') {
      out.push(['Reactiva', 'C12 · Resurgir del Olvido puede reactivarlo desde el descarte de Eventos.']);
      if (c.mods.includes('vestigio')) out.push(['Ojo', 'Vestigio: su efecto queda para siempre; solo otra carta que lo destruya expresamente lo termina (10.5.2).']);
      return out;
    }
    const r = [];
    if (c.clase === 'ataque') r.push('D01 (la invierte)', 'D02 (la cancela)', 'D03 (la desvía)');
    if (c.clase === 'efecto') r.push('C13 (la cancela)');
    if (c.clase === 'invocacion') r.push('C06 (la cancela)', 'R08 (cobra 2 cartas)');
    if (c.clase === 'reaccion') r.push('C07 (la cancela)');
    if (c.type === 'instantaneo') r.push('R02 (la cancela por ser Instantánea)');
    if (c.code !== 'C08') r.push('C08 (la copia)');
    const rr = r.filter(x => !x.startsWith(c.code));
    if (rr.length) out.push(['Responde', 'Pueden responderla: ' + rr.join(', ') + '.']);
    out.push(['Responde', 'C11 · Bloqueo Mental impide activarla a quien la sufra, y C10 · Escudo Sagrado protege de cartas enemigas.']);
    const re = []; if (c.deck === 'asalto' && c.code !== 'C16') re.push('C16 (desde el descarte de Asalto)'); if (c.code !== 'C12') re.push('C12 (desde cualquier descarte)');
    if (re.length) out.push(['Reactiva', 'Pueden reactivarla: ' + re.join(', ') + '.']);
    return out;
  }
  function relatedRules(c) {
    const ids = [...(c.texts.final.reglas || []), ...(c.uso_refs || []), META.tipos[c.type].regla, ...c.mods.map(m => META.mods[m].regla), c.deck === 'evento' ? '10.2.3' : '10.3'];
    if (c.type !== 'evento' && c.type !== 'nexo') ids.push('11.2'); if (c.type === 'nexo') ids.push('11.4');
    if (c.necro) ids.push('14.3.4');
    return [...new Set(ids)].filter(i => RULE_IDS.has(i));
  }
  function openDetail(code) {
    const c = BYCODE[code]; if (!c) return; CUR = c;
    const dlg = $('#detail'); const tabs = [['final', 'Oficial · Set v1.5'], ['referencia', 'Referencia v1.4 (anterior)'], ['catalogo', 'Catálogo JSX'], ['original', 'Original («Antes»)']];
    if (c.texts.propuesta) tabs.push(['propuesta', 'Propuesta (borrador)']);
    $('#d-tabs').innerHTML = tabs.filter(([k]) => c.texts[k] && c.texts[k].cuerpo).map(([k, l]) => `<button role="tab" data-text="${k}" class="${k === 'propuesta' ? 'draft' : ''}">${l}</button>`).join('');
    showText(META.texto_activo);
    const t = META.tipos[c.type], ev = c.deck === 'evento';
    const tags = [`<span class="tag" style="--c:${META.mazos[c.deck].color}">${META.mazos[c.deck].nombre}</span>`,
      ev ? `<span class="tag" style="--c:#E9E4D4">${esc(META.familias[c.familia])}</span>` : `<span class="tag" style="--c:${c.color}">${META.clases[c.clase].nombre}</span>`,
      ev ? '' : `<span class="tag"><span class="g">${t.simbolo}</span>${t.nombre}</span>`,
      ...c.mods.map(m => `<span class="tag" style="--c:#ffffff"><span class="g">${META.mods[m].simbolo}</span>${META.mods[m].nombre}</span>`),
      `<span class="tag">${c.qty > 1 ? c.qty + ' ejemplares' : '1 ejemplar'}</span>`, `<span class="tag">#${String(c.n).padStart(2, '0')} / ${c.of}</span>`].join('');
    const tips = [...c.tips, ...responders(c)];
    const notes = [...c.avisos.map(a => `<div class="warnbox"><b>Inconsistencia detectada:</b> ${linkify(a)}</div>`), ...c.notas.map(n => `<div class="warnbox">⚠ ${linkify(n)}</div>`)].join('');
    const ref = c.texts.final;
    $('#d-info').style.setProperty('--cc', c.color);
    $('#d-info').innerHTML = `
      <p class="kicker">${c.code} · ${META.mazos[c.deck].nombre}</p>
      <h2 id="d-title">${esc(c.name.es)}</h2><p class="en">${esc(c.name.en)}</p>
      <div class="tags">${tags}</div>
      <div class="blk"><h3>Texto oficial <span class="lbl ok">vigente</span></h3><p class="official">${linkify(ref.completo)}</p><p class="src">${esc(ref.fuente)}</p></div>
      ${c.uso_html ? `<div class="blk"><h3>Descripción y uso</h3><p>${c.uso_html}</p><p class="src">${c.uso_final ? 'Actualizado al set final v1.5' : 'Referencia de Cartas v1.4' + (ev ? ' · comentario del Evento' : ' · «Uso»')}</p></div>` : ''}
      <div class="blk"><h3>Recomendaciones <span class="lbl">consejo, no regla</span></h3><ul class="tips">${tips.map(([k, v]) => `<li><span class="k ${esc(k)}">${esc(k)}</span><span>${linkify(v)}</span></li>`).join('')}</ul></div>
      ${c.necro ? `<div class="blk"><h3>Habilidad Necrovante</h3><div class="necrobox">${linkify(c.necro.texto)}<br><span class="src">${esc(c.necro.estado)} · ${rref('14.3.4')}</span></div></div>` : ''}
      ${notes ? `<div class="blk"><h3>Notas y avisos</h3>${notes}</div>` : ''}
      <div class="blk"><h3>Reglas relacionadas</h3><div class="refs">${relatedRules(c).map(rref).join('')}</div></div>
      <div class="blk"><h3>Comparar textos</h3><div class="cmp">
        <div><span class="src">Referencia de Cartas v1.4 («Ahora», anterior)</span>${esc(c.texts.referencia.completo)}</div>
        ${c.texts.original.cuerpo ? `<div><span class="src">Original («Antes»)</span>${esc(c.texts.original.cuerpo)}</div>` : ''}
        <div><span class="src">Catálogo dz-elevate-data-v14.jsx</span>${esc(c.texts.catalogo.cuerpo)}</div>
        ${c.texts.propuesta ? `<div><span class="src">Propuesta v1.4.2 · borrador NO oficial</span>${esc(c.texts.propuesta.cuerpo)}</div>` : ''}
      </div></div>`;
    if (!dlg.open) dlg.showModal();
    $('.d-wrap', dlg).scrollTop = 0;
    document.title = `${c.code} · ${c.name.es} · Dizaster`;
  }
  function showText(k) {
    if (!CUR) return; CURTEXT = CUR.texts[k] && CUR.texts[k].cuerpo ? k : 'final';
    $('#d-face').innerHTML = DZCard.html(CUR, META, { text: CURTEXT });
    $$('#d-tabs [data-text]').forEach(b => b.setAttribute('aria-selected', String(b.dataset.text === CURTEXT)));
  }
  function step(d) {
    if (!CUR) return; const list = VISIBLE.length ? VISIBLE : CARDS.map(c => c.code);
    let i = list.indexOf(CUR.code); i = (i + d + list.length) % list.length; history.replaceState(null, '', '#carta-' + list[i]); openDetail(list[i]);
  }
  function closeDetail() {
    const dlg = $('#detail'); if (dlg.open) dlg.close(); CUR = null; document.title = 'Dizaster · Reglamento v1.5 y Cartas';
    if (location.hash.startsWith('#carta-')) history.replaceState(null, '', '#cartas');
  }

  // ── navegación ──
  function handleHash(initial) {
    const h = decodeURIComponent(location.hash || '');
    if (h.startsWith('#carta-')) { if (initial) $('#cartas').scrollIntoView(); openDetail(h.slice(7)); return; }
    if ($('#detail').open) $('#detail').close();
    if (h.startsWith('#r-')) {
      const el = document.getElementById(h.slice(1)); if (!el) return;
      if (el.classList.contains('hide') || el.closest('.chap.hide')) clearRuleSearch();
      requestAnimationFrame(() => { el.scrollIntoView({ block: 'start', behavior: 'instant' }); el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash'); setTimeout(() => el.classList.remove('flash'), 2200); });
    } else if (initial && h.length > 1) { const el = document.getElementById(h.slice(1)); el && el.scrollIntoView(); }
  }
  function initNav() {
    addEventListener('hashchange', () => handleHash(false));
    document.addEventListener('click', e => {
      const a = e.target.closest('a[href^="#r-"]'); if (!a) return;
      if ($('#detail').open) { e.preventDefault(); const h = a.getAttribute('href'); $('#detail').close(); CUR = null; history.pushState(null, '', h); handleHash(false); }
      else if (location.hash === a.getAttribute('href')) { e.preventDefault(); handleHash(false); }
    });
    const nav = $('#nav'), tg = $('.navtoggle');
    tg.addEventListener('click', () => { const o = nav.classList.toggle('open'); tg.setAttribute('aria-expanded', String(o)); });
    nav.addEventListener('click', e => { if (e.target.closest('a')) { nav.classList.remove('open'); tg.setAttribute('aria-expanded', 'false'); } });
    const secs = $$('main > .sec');
    const obs = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) $$('.nav a').forEach(a => a.classList.toggle('on', a.dataset.sec === e.target.id)); }), { rootMargin: '-45% 0px -50% 0px' });
    secs.forEach(s => obs.observe(s));
  }
})();
