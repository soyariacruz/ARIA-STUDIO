// ======================= CONFIG (cámbialo aquí) =======================
const MODEL_PATH = 'higgsfield-ai/soul/v2/standard';   // endpoint que enseña la consola
const PRICE      = 0.0032;                              // $/imagen · open.higgsfield.ai/pricing (Soul 2 Standard, 22 sep 2026)
const GEN_MS     = 1400;                                // teatro de «generando» al probar una prenda (0 = instantáneo)
const KEY_HINT   = '····7f2a';
// ======================================================================

const C = window.CATALOG;
const $ = s => document.querySelector(s);
const el = (t, cls, html) => { const e = document.createElement(t); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
const rnd = n => Math.floor(Math.random() * n);
const pad = n => String(n).padStart(2, '0');
const now = () => { const d = new Date(); return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`; };
const rid = () => 'req_' + Math.random().toString(16).slice(2, 10);

const tipos = [...new Set(C.expr.map(i => i.tipo).filter(Boolean))];
const TABS = {
  perfil:   { label: 'Perfil',    icon: '👤', shape: 'round', ar: 9 / 16 + 3 / 4, items: C.perfil.views, base: 'Ficha 360', sub: i => i.sub || 'vista', video: true },
  hair:     { label: 'Peinados',  icon: '💇‍♀️', shape: 'wide', ar: 16 / 9, items: C.hair,     filters: ['Trenzas', 'Moños/Recogidos', 'Coletas', 'Ondas/Rizos', 'Liso', 'Corto'], fkey: 'tags', base: 'Hair Styles', sub: i => (i.tags || []).join(' · ') || 'peinado' },
  expr:     { label: 'Expresiones', icon: '🙂', shape: 'wide', ar: 16 / 9, items: C.expr,     filters: tipos, fkey: 'tipo', base: 'Expresiones Faciales', sub: i => i.tipo || 'expresión' },
  vestidor: { label: 'Vestidor',  icon: '👗', shape: 'tall',  ar: 3 / 4,  items: C.vestidor, filters: ['De Vestir', 'Comfy', 'Sport', 'Nieve', 'Bañador'], fkey: 'tags', base: 'Vestidor Virtual', sub: i => (i.tags || []).join(' · ') + ' · Nº ' + i.num },
  cartoon:  { label: 'Cartoon',   icon: '🎨', shape: 'wide',  ar: 16 / 9, items: C.cartoon,  base: 'Cartoon Art Styles', sub: () => 'estilo de dibujo' },
  photo:    { label: 'Efectos',   icon: '📷', shape: 'wide',  ar: 16 / 9, items: C.photo,    base: 'Photography Styles', sub: () => 'estilo fotográfico' },
  movie:    { label: 'Movie looks', icon: '🎬', shape: 'wide',  ar: 16 / 9, items: C.movie,    base: 'Movie Looks', sub: () => 'movie look' },
  videoteca: { label: 'Filmoteca', icon: '🎞', shape: 'tall', ar: 9 / 16, items: (C.videoteca || []).map(v => Object.assign(v, { kind: 'video', src: v.video, thumb: v.poster })), filters: ['Cinematic', 'UGC'], fkey: 'tags', base: 'Prompts de Vídeo (pago)', sub: i => (i.ai || []).join(' · ') || 'vídeo' },
  biblio:   { label: 'Fototeca',  icon: '🖼️', shape: 'tall', ar: 3 / 4,  items: C.biblio || [], filters: ['Individual', 'Carrousel'], fkey: 'tags', base: 'Prompts de Imágenes (pago)', sub: i => (i.ai || []).join(' · ') || 'prompt' },
  crear:    { label: 'Crear imagen', icon: '📸', shape: 'tall', ar: 3 / 4, items: C.crear,    base: 'Tu creación', sub: i => i.sub || (i.custom ? 'combina lo que añadas' : 'receta') },
  video:    { label: 'Crear vídeo', icon: '🎥', shape: 'tall', ar: 3 / 4,  items: [],         base: 'Imágenes para animar', filters: ['Imágenes', 'Vídeos'], fkey: 'kindLabel', sub: i => i.sub || 'imagen' },
  creaciones: { label: 'Creaciones', icon: '🗂', shape: 'tall', ar: 3 / 4, items: [],   base: 'Generadas con la API', filters: ['Imágenes', 'Vídeos', 'Variaciones', 'Ocultos'], fkey: 'kindLabel', sub: i => i.sub || '' },
};
// Vestidor: la prenda base de Aria (tank top y leggings negros, n82) siempre primera; el resto de más nueva a más antigua
(function () { const base = C.vestidor.find(v => v.id === 'n82'); const rest = C.vestidor.filter(v => v !== base).sort((a, b) => ((b.date || '') > (a.date || '') ? 1 : (b.date || '') < (a.date || '') ? -1 : (b.num || 0) - (a.num || 0))); C.vestidor.length = 0; if (base) C.vestidor.push(base); rest.forEach(v => C.vestidor.push(v)); })();
const GALLERY_TABS = new Set(['creaciones', 'biblio', 'videoteca', 'vestidor', 'photo', 'movie', 'cartoon', 'expr', 'hair']); // sin imagen grande: la cuadrícula ocupa todo y la vista previa va en el panel izquierdo
const ORDER = ['perfil', 'creaciones', 'crear', 'video', '|', 'biblio', 'videoteca', '|', 'vestidor', 'photo', 'movie', 'cartoon', 'expr', 'hair'];
const TABKEYS = ORDER.filter(k => k !== '|');
const LIBS = ['vestidor', 'photo', 'movie', 'cartoon', 'expr', 'hair'];   // bibliotecas: en el menú solo se ve una (la última usada) y el resto sale en «Más»
const COMP = { biblio: 'Fototeca', vestidor: 'Prenda', photo: 'Efecto', movie: 'Movie look', cartoon: 'Cartoon', expr: 'Expresión', hair: 'Peinado' };
const CONVERT = new Set(['cartoon', 'photo', 'movie']);
const state = { tab: 'hair', sel: {}, filter: {}, search: {}, pose: {}, done: new Set(), added: new Set(), comp: {}, fold: {}, nGen: 0, spent: 0, spinning: false, busy: false, ready: false, quality: 'std', aspect: '3:4', vdur: 5, vres: '720p', vmode: 'i2v', vaspect: '3:4', vaudio: false };
try { state.quality = localStorage.getItem('am_quality') || 'std'; state.aspect = localStorage.getItem('am_aspect') || '3:4'; state.aspectV = localStorage.getItem('am_aspect_v') || '1:1'; state.vdur = +(localStorage.getItem('am_vdur') || 5); state.vres = localStorage.getItem('am_vres') || '720p'; state.vmode = localStorage.getItem('am_vmode') || 'i2v'; state.vaspect = localStorage.getItem('am_vaspect') || '3:4'; state.vaudio = localStorage.getItem('am_vaudio') !== '0'; state.vprov = localStorage.getItem('am_vprov') || 'hf'; state.vmodel = localStorage.getItem('am_vmodel') || '2.0'; } catch (e) {}
const mirror = $('#mirror'), layers = [$('#lA'), $('#lB')]; let front = 0;
const rail = $('#rail'), side = $('#side'), logEl = $('#log');

// ----------------------------------------------------------------- utilidades
function miniLb(src, cap, btns) { $('#mlbImg').src = src; hiSwap($('#mlbImg'), src); $('#mlbCap').textContent = cap || ''; const box = $('#mlbBtns'); box.innerHTML = ''; (btns || []).forEach(([t, fn], i) => { const b = el('button', 'btn w' + (i === 0 ? ' acc' : ''), t); b.onclick = fn; box.appendChild(b); }); $('#mlb').classList.add('on'); }
function closeMiniLb() { $('#mlb').classList.remove('on'); }
$('#mlbX').onclick = closeMiniLb; $('#mlb').onclick = e => { if (e.target === $('#mlb')) closeMiniLb(); };
function fullOf(src) { // la original sin reducir de una imagen de biblioteca (Fototeca y Vestidor se bajaron a 1024 / 1200 px para que la cuadrícula cargue rápido)
  const s = String(src || '').split('?')[0]; let m = s.match(/^assets\/biblio\/([^\/]+\.jpg)$/); if (m && !/_t\.jpg$/.test(m[1])) return 'assets/biblio/full/' + m[1];
  m = s.match(/^assets\/vestidor\/(n\d+_ficha\.jpg)$/); return m ? 'assets/vestidor/full/' + m[1] : null; }
function hiSwap(im, low) { // se ve al instante la copia ligera y, cuando llega, la original (si existe)
  const full = fullOf(low); if (!full) return; const hi = new Image(); hi.onload = () => { if (im.getAttribute('src') === low) { im.src = full; im.dataset.full = '1'; } }; hi.src = full; }
function lightbox(src, cap) { $('#lbImg').src = src; hiSwap($('#lbImg'), src); $('#lbCap').textContent = cap || ''; $('#lb').classList.add('on'); }
$('#lb').onclick = () => $('#lb').classList.remove('on');
function toast(msg) { const t = $('#toast'); t.textContent = msg; t.classList.add('on'); clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove('on'), 1800); }
function log(html) { const d = el('div', 'l', `<span class="t">${now()}</span>${html}`); logEl.appendChild(d); logEl.scrollTop = logEl.scrollHeight; while (logEl.children.length > 400) logEl.removeChild(logEl.firstChild); }
function meter() { const n = (state.totalN || 0) + state.nGen, u = (state.totalUsd || 0) + state.spent; $('#nGen').textContent = n; $('#spent').textContent = '$' + u.toFixed(2); $('#conMeta').textContent = `${n} generaciones · $${u.toFixed(2)} en total · sesión ${state.nGen} · $${state.spent.toFixed(4)}`; }
function openConsole(v) { $('#console').classList.toggle('open', v); $('#conTgTxt').textContent = v ? 'Esconder' : 'Desplegar'; setTimeout(sizeMirror, 400); }
function itemSrc(it) { const t = TABS[state.tab]; if (t === TABS.video || t === TABS.creaciones) return it.src; if (t === TABS.biblio) return it.image; if (t === TABS.vestidor || t === TABS.crear) return (it.looks && it.looks.length) ? it.looks[(state.pose[it.id] || 0) % it.looks.length] : (it.card || it.thumb || C.base.photo); if (t === TABS.perfil) return C.perfil.poster; return (it.files && it.files.main) || it.card || it.thumb || it.image || it.src || ''; }
const norm = x => (x || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
let BIBGROUPS = null;
function bibGroups() { if (BIBGROUPS) return BIBGROUPS; const m = new Map(); (C.biblio || []).filter(i => i.tags === 'Carrousel').forEach(i => { if (!m.has(i.n)) m.set(i.n, { id: 'g' + i.n, group: true, n: i.n, name: `Carrusel Nº ${i.n}`, thumb: i.thumb, image: i.image, tags: 'Carrousel', count: 0, date: i.date, ai: i.ai }); m.get(i.n).count++; }); BIBGROUPS = [...m.values()]; return BIBGROUPS; }
function aiLine(it) { const w = el('div', 'ailine'); (it.ai || []).forEach(a => w.appendChild(el('span', 'aichip', a))); if (!(it.ai || []).length) w.appendChild(el('span', 'aichip', 'IA sin indicar')); if (it.date) w.appendChild(el('small', '', it.date)); return w; }
function vtEnter(it) { state.vtScroll = rail.scrollTop; state.vtGroup = it.n; renderRail(); renderChips(); const v = view(); if (v.length) select(v[0], false, false); rail.scrollTop = 0; }
function loSrc(src) { return src && src.endsWith('.mp4') ? src.slice(0, -4) + '_lo.mp4' : src; }
function vtSlides(it) { if (it._slides) return it._slides; const L = (it.videos && it.videos.length > 1) ? it.videos : []; it._slides = L.map((sl, k) => ({ id: `${it.id}_${k + 1}`, name: `${it.name} · ${k + 1}`, n: it.n, kind: 'video', kindLabel: 'Vídeos', video: sl.file, src: sl.file, poster: sl.poster || it.poster, thumb: sl.poster || it.poster, w: sl.w, h: sl.h, dur: sl.dur, prompt: sl.prompt || it.prompt, ajustes: it.ajustes, refs: it.refs, ai: it.ai, tags: it.tags, escenas: it.escenas, date: it.date, parent: it })); return it._slides; }
function view() { const t = TABS[state.tab]; if (t === TABS.perfil) return TABS.creaciones.items.filter(i => !i.hidden);
  if (t === TABS.crear) { const f = state.filter.crearG; const q = norm(state.search.crear); let v = f === 'Variaciones' ? TABS.creaciones.items.filter(i => isVarAux(i) && !i.pending) : f === 'Ocultos' ? TABS.creaciones.items.filter(i => i.hidden && !isVarAux(i)) : TABS.creaciones.items.filter(i => !i.hidden && !isVarAux(i) && (!f || i.kindLabel === f)); if (q) v = v.filter(i => norm(i.name).includes(q)); return charFilt(v); }
  if (t === TABS.vestidor && !norm(state.search.vestidor)) { const f = state.filter.vestidor; let v = t.items.filter(i => !i.parent); if (f === '__fav') v = v.filter(i => i.fav || t.items.some(c => c.parent === i.id && c.fav)); else if (f === '__new') v = v.filter(i => isNew(i) || t.items.some(c => c.parent === i.id && isNew(c))); else if (f) v = v.filter(i => (i.tags || []).includes(f)); return vestSort(v); }
  if (t === TABS.videoteca && state.vtGroup) { const pg = t.items.find(i => i.n === state.vtGroup); return pg ? vtSlides(pg) : []; }
  if (t === TABS.creaciones) { const f = state.filter.creaciones; const q = norm(state.search.creaciones); let v = f === 'Variaciones' ? t.items.filter(i => isVarAux(i) && !i.pending) : f === 'Ocultos' ? t.items.filter(i => i.hidden && !isVarAux(i)) : t.items.filter(i => !i.hidden && !isVarAux(i) && (!f || i.kindLabel === f)); if (state.cfilt) { const sel = state.cfilt.sel; v = v.filter(i => selMatch(sel, i)); if (!f || f === 'Imágenes') { const seen = new Set(v.map(i => i.id)); creationsSel(sel).forEach(i => { if ((i.biblio || i.conv) && !seen.has(i.id)) v.push(i); }); } } if (q) v = v.filter(i => norm(i.name).includes(q) || norm(i.sub).includes(q)); return charFilt(v); }
  if (t === TABS.biblio && state.filter.biblio === 'Carrousel' && !norm(state.search.biblio) && true) { if (state.bibGroup) return t.items.filter(i => i.tags === 'Carrousel' && i.n === state.bibGroup); return bibGroups(); } const f = state.filter[state.tab]; const q = norm(state.search[state.tab]); let v = t.items; if (f === '__new') v = v.filter(i => !i.group && isNew(i)); else if (f) v = v.filter(i => Array.isArray(i[t.fkey]) ? i[t.fkey].includes(f) : i[t.fkey] === f); if (q) v = v.filter(i => norm(i.name).includes(q) || norm(Array.isArray(i.tags) ? i.tags.join(' ') : (i.tags || '')).includes(q) || norm(i.tipo).includes(q) || norm(i.prompt).includes(q) || norm(i.desc).includes(q)); return v; }
function cur() { return state.sel[state.tab]; }

// ----------------------------------------------------------------- espejo
let arOverride = null;
function sizeMirror() {
  const wrap = $('#wrap'); const ar = arOverride || TABS[state.tab].ar;
  const W = wrap.clientWidth - 64, H = wrap.clientHeight - 40;
  let w, h; if (W / H > ar) { h = H; w = Math.round(H * ar); } else { w = W; h = Math.round(W / ar); }
  mirror.style.width = w + 'px'; mirror.style.height = h + 'px';
  { const z = window.ESCALA || 1; mirror.classList.toggle('mini', h < 250 * z || w < 190 * z); }   // encogida: en el «Generando» solo cabe la barra
}
let showSeq = 0;
function showImage(src, fast) {
  const back = layers[1 - front], fr = layers[front];
  if (fr.getAttribute('src') === src && fr.classList.contains('on')) { state.lastSrc = src; syncMini(); return; }
  const seq = ++showSeq; let did = false; state.lastSrc = src; syncMini();
  const swap = () => { if (did || seq !== showSeq) return; did = true; back.onload = null; back.classList.add('on'); fr.classList.remove('on'); front = 1 - front; syncMini(); if (state.tab === 'crear' && back.naturalWidth) { const ar = back.naturalWidth / back.naturalHeight; if (Math.abs((arOverride || 0) - ar) > 0.01) { arOverride = ar; sizeMirror(); } } if (!fast) { mirror.classList.remove('flash'); void mirror.offsetWidth; mirror.classList.add('flash'); } };
  back.onload = swap; back.src = src; if (back.complete && back.naturalWidth) swap();
}
const cache = new Map();
let preloadGen = 0;
function preload(list, from) { // precarga alrededor de la selección (2 en paralelo, se cancela al cambiar de pestaña)
  const gen = ++preloadGen; const order = []; const n = list.length;
  for (let k = 0; k < Math.min(n, 13); k++) { const i = (from + (k % 2 ? -Math.ceil(k / 2) : Math.ceil(k / 2)) + n * 4) % n; if (!order.includes(i)) order.push(i); }
  let p = 0; const one = () => { if (gen !== preloadGen || p >= order.length) return; const it = list[order[p++]]; const s = it ? itemSrc(it) : ''; if (!s || cache.has(s)) return one(); const im = new Image(); cache.set(s, im); im.onload = im.onerror = () => setTimeout(one, 40); im.src = s; };
  setTimeout(() => { one(); one(); }, 250);
}

// ----------------------------------------------------------------- pestañas y rueda
function navMore(btn, items) { // desplegable que sale a la derecha del menú
  let m = $('#navmore'); if (m) { const same = m._for === btn; m.remove(); if (same) return; } m = el('div', 'navmore'); m.id = 'navmore'; m._for = btn;
  items.forEach(([ic, label, fn, sub, on]) => { const r = el('button', 'it' + (on ? ' on' : '') + (sub === 'pronto' ? ' dim' : ''), `<span>${ic}</span><b>${label}</b>${sub ? `<i>${sub}</i>` : ''}`); r.onclick = () => { m.remove(); fn(); }; m.appendChild(r); });
  document.body.appendChild(m); const r = btn.getBoundingClientRect(); m.style.left = Math.round(r.right + 8) + 'px'; m.style.top = Math.round(Math.max(12, Math.min(r.top - 6, innerHeight - m.offsetHeight - 12))) + 'px';
  setTimeout(() => { const close = e => { if (!m.isConnected) { document.removeEventListener('click', close, true); return; } if (!m.contains(e.target) && !btn.contains(e.target)) { m.remove(); document.removeEventListener('click', close, true); } }; document.addEventListener('click', close, true); }, 0);
}
function buildNav() {
  const nav = $('#nav'); nav.innerHTML = ''; { const old = $('#navmore'); if (old) old.remove(); }
  if (state.lib === undefined) { try { state.lib = localStorage.getItem('am_lib'); } catch (e) {} if (!LIBS.includes(state.lib)) state.lib = 'vestidor'; }
  let host = nav; const main = el('div', 'navmain');
  ORDER.forEach(k => { if (LIBS.includes(k) && k !== state.lib) return; if (k === '|') { nav.appendChild(el('div', 'nav-sep')); host = nav; return; } if (k === 'crear') { nav.appendChild(main); host = main; } if (k === 'creaciones') host = nav; const t = TABS[k]; const i = TABKEYS.indexOf(k); const b = el('button', (k === state.tab ? 'on' : '') + (k === 'perfil' ? ' story' : ''), k === 'perfil' ? `<span class="ring">${navAvatar() ? `<img src="${navAvatar()}" alt="">` : '<i class="ringv">👤</i>'}</span>${t.label}` : `<span>${t.icon}</span>${t.label}`); b.dataset.tab = k; b.title = `${t.label} (${i + 1})`; b.onclick = () => { if (state.tab === k) { state.filter[k === 'crear' ? 'crearG' : k] = null; state.cfilt = null; state.bibGroup = null; state.vtGroup = null; } setTab(k); }; if (k === 'crear' || k === 'video') b.appendChild(el('span', 'bd', '0'));
    if (k === 'video') { b.classList.add('soon'); b.insertAdjacentHTML('beforeend', '<i>pronto</i>'); b.title = 'Crear vídeo: próximamente'; b.onclick = () => { if (state.tab === 'video') return; const go = () => setTab('video'); if (window.devIntro) devIntro('Crear vídeo', go); else go(); }; } // en el MVP, Crear vídeo va como «pronto» (se puede entrar igualmente)
    if (LIBS.includes(k)) { const w = el('div', 'navlib'); w.appendChild(b); const mb = el('button', 'more', 'Más <span>▾</span>'); mb.title = 'Vestidor, Efectos, Movie looks, Cartoon, Expresiones, Peinados y Poses'; mb.onclick = () => navMore(w, LIBS.map(q => [TABS[q].icon, TABS[q].label, () => setTab(q), '', q === state.tab]).concat([['🤸', 'Poses', () => toast('Poses: próximamente'), 'pronto']])); w.appendChild(mb); host.appendChild(w); }
    else host.appendChild(b); });
  if (state.interno) { nav.appendChild(el('div', 'nav-sep')); const wb = el('button', 'more', '<span>🧰</span>Workflows'); wb.title = 'Programas internos del equipo (solo cuentas autorizadas)'; wb.onclick = () => navMore(wb, [['🥊', 'Duelos', () => { location.href = 'liga.html'; }, 'interno']]); nav.appendChild(wb); }
  nav.appendChild(el('div', 'sp'));
}
function setTab(k) {
  if (state.spinning || state.busy) return;
  if (state.pick && k !== state.pick.tab) { state.pick = null; pickNav(); }
  if (k !== 'perfil' && window.feedbackSection) feedbackSection(null); // el 💬 Feedback solo vive en las secciones en desarrollo
  if (cmp) toggleCmp(false); mirror.classList.remove('queue'); if (k !== 'video') { mirror.classList.remove('vidmode'); $('#vid').pause(); }
  arOverride = null;
  if ((state.tab === 'crear' || state.tab === 'video') && COMP[k]) state.back = state.tab; else if (!COMP[k]) state.back = null;
  state.tab = k; if (LIBS.includes(k) && state.lib !== k) { state.lib = k; persist('am_lib', k); buildNav(); badge(); } // la biblioteca que se abre pasa a ser la del menú
  document.querySelectorAll('#nav button[data-tab]').forEach(b => b.classList.toggle('on', b.dataset.tab === k));
  if (k !== 'creaciones') state.cfilt = null; if (k !== 'videoteca') state.vtGroup = null; state.vtClicked = false; state.vtArmed = null; if (!state._navving) { state.navStack = []; setTimeout(() => { const on = (state.back && COMP[k]) ? rail.querySelector('.cell.on') : null; rail.scrollTop = 0; if (on) on.scrollIntoView({ block: 'center' }); }, 0); } state.shown = null; mirror.classList.remove('bib'); persist('am_tab', k); const t = TABS[k]; $('#pickTitle').textContent = t === TABS.perfil ? `Mis creaciones · ${TABS.creaciones.items.filter(i => !i.pending).length}` : t === TABS.crear ? `Crear imagen · mis creaciones · ${TABS.creaciones.items.filter(i => !i.pending).length}` : t === TABS.creaciones ? `Mis creaciones · ${t.items.length}` : `${t.label} · ${t.items.length} en ${t.base}`;
  const tv = $('#turn'), iv = $('#idle'); if (t === TABS.perfil) { if (!tv.getAttribute('src')) { tv.src = C.perfil.video; tv.load(); } if (C.perfil.idle && !iv.getAttribute('src')) { iv.src = C.perfil.idle; iv.load(); } tv.play().catch(() => {}); iv.play().catch(() => {}); } else { tv.pause(); iv.pause(); }
  setCompact(false); $('#stageEl').classList.toggle('solo', k === 'perfil'); if (k === 'perfil') renderProfile(); if (k === 'crear') setTimeout(() => { cancelAnimationFrame(kAnim); setK(0.5); }, 0); $('#stageEl').classList.toggle('cine', k === 'video'); document.querySelector('main').classList.toggle('nopanel', k === 'creaciones'); if (k === 'video') { cineInit(); if (state.filter.video === undefined) state.filter.video = 'Vídeos'; setTimeout(() => { rail.scrollTop = 0; }, 0); } $('#stageEl').classList.toggle('gallery', GALLERY_TABS.has(k)); if (GALLERY_TABS.has(k)) { cancelAnimationFrame(kAnim); state.k = 0; $('#stageEl').style.gridTemplateRows = ''; } sizeMirror();
  const v = view(); if (k === 'crear') state.sel.crear = C.crear.find(x => x.custom) || C.crear[0]; else if (k === 'biblio') { if (!cur()) state.sel.biblio = (C.biblio || [])[0]; } else if (k !== 'perfil' && (!cur() || !v.includes(cur()))) state.sel[k] = v[0]; if (k === 'perfil' && !state.sel.perfil) state.sel.perfil = C.perfil.views[0];
  renderRail(); renderSide();
  const it = cur(); if (it) paint(it, false);
  preload(v, v.indexOf(it));
}
function isDone(it) { const t = TABS[state.tab]; if (t === TABS.video) return !!it.video; if (t === TABS.creaciones || t === TABS.biblio || t === TABS.perfil) return false; if (it.live) return true; if (LIVE) return (t === TABS.vestidor && !!(it.looks && it.looks[0])) || (CONVERT.has(state.tab) && !!convSrc(it)) || (t === TABS.crear && !!(it.looks && it.looks[0])); return (t === TABS.vestidor || CONVERT.has(state.tab) || t === TABS.crear) && state.done.has(it.id); }
function layoutMasonry() { // Videoteca: reparte las tarjetas en columnas por altura estimada (w/h); se rehace al cambiar el ancho
  const cells = [...rail.querySelectorAll('.cell')]; if (!cells.length) return; const sz = gsize(); const colW = sz === 's' ? 100 : sz === 'l' ? 230 : 150, gap = sz === 'l' ? 14 : 10;
  const W = rail.clientWidth - 44; const n = Math.max(1, Math.floor((W + gap) / (colW + gap))); const cols = Array.from({ length: n }, () => { const c = el('div', 'mcol'); c._h = 0; return c; });
  cells.forEach(c => { const it = c._it || {}; const h = it.w && it.h ? it.h / it.w : 16 / 9; const k = cols.reduce((b, x, i) => x._h < cols[b]._h ? i : b, 0); cols[k].appendChild(c); cols[k]._h += h + 0.08; });
  rail.innerHTML = ''; const wrap = el('div', 'masonry'); wrap.style.gap = gap + 'px'; cols.forEach(c => { c.style.gap = gap + 'px'; wrap.appendChild(c); }); rail.appendChild(wrap);
}
function masonryCheck() { if (state.tab === 'videoteca' && rail.querySelector('.masonry')) { const n = rail.querySelectorAll('.mcol').length; const sz = gsize(); const colW = sz === 's' ? 100 : sz === 'l' ? 230 : 150, gap = sz === 'l' ? 14 : 10; const want = Math.max(1, Math.floor((rail.clientWidth - 44 + gap) / (colW + gap))); if (want !== n) renderRail(); } }
new ResizeObserver(masonryCheck).observe(rail); window.addEventListener('resize', () => setTimeout(masonryCheck, 50));
const NEW_DAYS = 7;
function kidBump(it) { // la variación más reciente de una prenda (un color nuevo, otra variación…): '' si no tiene ninguna dentro del plazo de NEW
  let best = ''; TABS.vestidor.items.forEach(c => { if (c.parent !== it.id) return; if (c.pending) { best = '9999'; return; } if (!isNew(c)) return; const k = (c.date || '') + '|' + String(c.num || 0).padStart(6, '0'); if (k > best) best = k; }); return best; }
function vestSort(v) { // favoritas primero; después, las prendas a las que se les acaba de crear una variación (la más reciente arriba); el resto, como estaba
  const fav = i => (i.fav || TABS.vestidor.items.some(c => c.parent === i.id && c.fav)) ? 1 : 0; const B = new Map(v.map(i => [i, kidBump(i)]));
  return v.slice().sort((a, b) => (fav(b) - fav(a)) || (B.get(b) > B.get(a) ? 1 : B.get(b) < B.get(a) ? -1 : 0)); }
function isNew(it) { if (!it) return false; if (it.date) { const t = Date.parse(it.date); return isFinite(t) && (Date.now() - t) < NEW_DAYS * 864e5; } return !!it.new; }
function renderRail() { // cuadrícula vertical con scroll (estilo Freepik)
  const t = TABS[state.tab]; const v = view(); rail.innerHTML = ''; rail.className = 'grid ' + (t.shape === 'round' ? '' : t.shape) + ' t-' + state.tab + ' sz-' + gsize();
  const mk = it => {
    const d = el('div', 'cell'); const src = t === TABS.vestidor ? it.card : (t === TABS.crear || t === TABS.perfil || t === TABS.video || t === TABS.biblio || t === TABS.creaciones || t === TABS.videoteca) ? it.thumb : ((t === TABS.hair || t === TABS.expr) ? it.files.main : it.files.thumb);
    if (it === cur() && t === TABS.perfil) {}
    d.innerHTML = `<img class="im" loading="lazy" src="${src}" alt="">${it.kind === 'video' ? '<i class="play">▶</i>' : ''}${it.group ? `<i class="play" style="font-size:11px;letter-spacing:.05em">${it.count}</i>` : ''}${(t === TABS.creaciones || t === TABS.crear || t === TABS.perfil || t === TABS.video || t === TABS.biblio || t === TABS.vestidor || t === TABS.videoteca) ? '' : `<b title="${it.name}">${it.name}${it.group ? ' · ' + it.count + ' fotos' : ''}</b>`}`;
    { const im = d.querySelector('img.im'); if (im && src) { let n = 0; im.onerror = () => { n++; const base = String(src).split('?')[0]; if (n <= 3) setTimeout(() => { im.src = base + '?r=' + n + '_' + Date.now(); }, 1300 * n); else if (n === 4 && it.src && it.src.split('?')[0] !== base) im.src = it.src; }; } }
    if (it === cur() && !state.selset.size) d.classList.add('on'); if (isDone(it)) d.classList.add('done'); if ((isNew(it) || (t === TABS.vestidor && kidBump(it))) && t !== TABS.creaciones && t !== TABS.crear && t !== TABS.perfil && t !== TABS.video) d.classList.add('new');
    if (t !== TABS.videoteca && it.kind === 'video' && it.src && !it.pending) { d.classList.add('vt'); const hv = document.createElement('video'); hv.className = 'hover'; hv.muted = true; hv.loop = true; hv.playsInline = true; hv.preload = 'none'; hv.src = loSrc(it.src); hv.onerror = () => { if (hv.src.endsWith('_lo.mp4')) { hv.onerror = null; hv.src = it.src; } }; d.appendChild(hv); d.addEventListener('mouseenter', () => { hv.play().catch(() => {}); d.classList.add('playing'); }); d.addEventListener('mouseleave', () => { hv.pause(); hv.currentTime = 0; d.classList.remove('playing'); }); }
    if (t === TABS.vestidor) { const kids = t.items.filter(c => c.parent === it.id && !c.pending); if (kids.length) { d.appendChild(el('span', 'cnt', `🎨 ${kids.length + 1}`)); const all = [it, ...kids]; const im = d.querySelector('.im'); const dots = el('div', 'scrub'); all.forEach((k, i) => dots.appendChild(el('i', i ? '' : 'on'))); d.appendChild(dots);
        const show = i => { d._pick = all[i]; im.src = all[i].card; [...dots.children].forEach((x, j) => x.classList.toggle('on', j === i)); };
        d.addEventListener('mousemove', e => { const r = d.getBoundingClientRect(); show(Math.min(all.length - 1, Math.max(0, Math.floor((e.clientX - r.left) / r.width * all.length)))); });
        d.addEventListener('mouseleave', () => show(0)); } }
    if (t === TABS.videoteca) { d.classList.add('vt'); if (it.w && it.h) d.querySelector('.im').style.aspectRatio = it.w + ' / ' + it.h; if (it.nvid > 1 && !state.vtGroup) { const cnt = el('span', 'cnt' + (state.vtArmed === it.id ? ' open' : ''), `🎞 ${it.nvid}<b> · Ver todos</b>`); cnt.title = 'Ver los ' + it.nvid + ' vídeos de esta ficha'; cnt.onclick = e => { e.stopPropagation(); vtEnter(it); }; d.appendChild(cnt); } const hv = document.createElement('video'); hv.className = 'hover'; hv.muted = true; hv.loop = true; hv.playsInline = true; hv.preload = 'none'; hv.src = loSrc(it.video); hv.onerror = () => { if (hv.src.endsWith('_lo.mp4')) { hv.onerror = null; hv.src = it.video; } }; d.appendChild(hv); d.addEventListener('mouseenter', () => { hv.play().catch(() => {}); d.classList.add('playing'); }); d.addEventListener('mouseleave', () => { hv.pause(); hv.currentTime = 0; d.classList.remove('playing'); });
      const inVid = poolHas(it.video); const ab = el('button', 'addc' + (inVid ? ' on' : ''), inVid ? '✓ Añadido' : '＋ Añadir'); ab.title = 'Añadir este vídeo como referencia en Crear vídeo'; ab.onclick = e => { e.stopPropagation(); if (inVid) { const k = state.vpool.findIndex(r => r.src === it.video); if (k >= 0) state.vpool.splice(k, 1); vbadge(); renderRail(); } else { poolAdd({ id: 'vt:' + it.id, kind: 'video', name: 'Videoteca ' + it.name, src: it.video, thumb: it.poster }, true); vbadge(); setTab('video'); } }; d.appendChild(ab); }
    if (t === TABS.video && !it.pending) { if (it.kind === 'video') { const rc = el('span', 'rcb', 'Recrear'); rc.title = 'Cargar sus referencias, prompt y ajustes en el panel'; rc.onclick = e => { e.stopPropagation(); recreateVideo(it); }; d.appendChild(rc); const ex = el('span', 'ck exp', '⤢'); ex.title = 'Abrir en grande'; ex.onclick = e => { e.stopPropagation(); cineShow(it); openGal(it); }; d.appendChild(ex); d.ondblclick = () => { cineShow(it); openGal(it); }; if (state.vplay === it) d.classList.add('playing'); } else { const ab = el('button', 'addc' + (poolHas(it.src) ? ' on' : ''), poolHas(it.src) ? '✓ Añadida' : '＋ Añadir'); ab.onclick = e => { e.stopPropagation(); if (poolHas(it.src)) { const k = state.vpool.findIndex(r => r.src === it.src); if (k >= 0) state.vpool.splice(k, 1); vbadge(); renderSide(); renderRail(); } else { poolAdd(poolFromItem(it), true); renderRail(); toast(`«${it.name}» → referencias (@Image${state.vpool.length})`); } }; d.appendChild(ab); } }
    if ((t === TABS.creaciones || t === TABS.perfil || t === TABS.crear) && !it.pending && it.src && !it.biblio && !it.conv) { const ck = el('span', 'ck' + (state.selset.has(it.src) ? ' on' : ''), '✓'); ck.title = 'Seleccionar'; ck.onclick = e => { e.stopPropagation(); toggleSel(it.src); }; d.appendChild(ck); if (state.selset.has(it.src)) d.classList.add('sel'); }
    if ((COMP[state.tab] || t === TABS.biblio) && !it.group && !it.pending && !state.pick) { const ab = el('button', 'addc' + ((state.comp[state.tab] === it || poolHas(compImage(state.tab, it))) ? ' on' : ''), '＋ Añadir'); ab.title = 'Añadir a Crear imagen o a Crear vídeo'; ab.onclick = e => { e.stopPropagation(); addMenu(state.tab, it, d); }; d.appendChild(ab); }
    if (it.pending || (typeof jobFor === 'function' && t !== TABS.creaciones && t !== TABS.perfil && jobFor(it))) d.classList.add('pend');
    if ((t === TABS.creaciones || t === TABS.perfil || t === TABS.crear) && !it.pending && it.kind === 'video') { const rc = el('span', 'rcb', 'Recrear'); rc.title = 'Cargar este vídeo en Crear vídeo: referencias, prompt y ajustes'; rc.onclick = e => { e.stopPropagation(); recreateVideo(it); setTab('video'); }; d.appendChild(rc); }
    else if ((t === TABS.creaciones || t === TABS.perfil || t === TABS.crear) && !it.pending && it.meta && !it.biblio && !it.conv && Object.keys(recComp(it.meta)).length) { const rc = el('span', 'rcb', 'Recrear'); rc.title = 'Cargar esta combinación en Crear imagen'; rc.onclick = e => { e.stopPropagation(); recrear(it); }; d.appendChild(rc); }
    d.onclick = () => { if (t === TABS.vestidor && d._pick && d._pick !== it) { const k = d._pick; state.sel.vestidor = k; paint(k, true); renderSide(); setTimeout(() => [...rail.querySelectorAll('.cell')].forEach(x => x.classList.toggle('on', x === d)), 0); return; } if (t === TABS.videoteca) state.vtClicked = true; if (t === TABS.video && it.kind === 'video') { cineShow(it); return; } if (t === TABS.videoteca && it.nvid > 1 && !state.vtGroup) { if (state.vtArmed !== it.id) { state.vtArmed = it.id; select(it, false, false); [...rail.querySelectorAll('.cell')].forEach(x => { const c = x.querySelector('.cnt'); if (c) c.classList.toggle('open', x._it === it); }); return; } vtEnter(it); return; } if (it.group) { state.bibScroll = rail.scrollTop; state.bibGroup = it.n; renderRail(); const v = view(); if (v.length) select(v[0], false, true); return; } if (it.pending) { toast('Generándose… aparecerá aquí sola'); return; } if (t === TABS.creaciones) { state.sel.creaciones = it; [...rail.children].forEach(x => x.classList.toggle('on', x._it === it)); openGal(it); return; } if (t === TABS.perfil || t === TABS.crear) { if (state.shown === it) { openGal(it); return; } state.sel.creaciones = it; state.shown = it; [...rail.children].forEach(x => x.classList.toggle('on', x._it === it)); showCreation(it); return; } if (it === cur()) { if (t === TABS.biblio || t === TABS.videoteca || COMP[state.tab]) { openGal(it); return; } if (!LIVE && (t === TABS.vestidor || CONVERT.has(state.tab) || t === TABS.crear)) tryOn(false); return; } select(it, false, true); };
    d.ondblclick = () => { if (t === TABS.video && it.kind === 'video') { cineShow(it); openGal(it); return; } if (t !== TABS.perfil && t !== TABS.video && t !== TABS.creaciones && t !== TABS.biblio) freeTry(); };
    d._it = it; return d;
  };
  // por tandas: se pintan las primeras y el resto al bajar (la Fototeca tiene 1.946). Al repintar la misma pestaña se conserva lo que ya había a la vista
  const STEP = 240; let shown = 0; const key = state.tab + '|' + (state.filter[state.tab] || '') + '|' + (state.search[state.tab] || '');
  const more = n => { const f = document.createDocumentFragment(); const to = Math.min(v.length, shown + n); for (; shown < to; shown++) f.appendChild(mk(v[shown])); rail.appendChild(f); rail._count = shown; if (t === TABS.videoteca) layoutMasonry(); };
  const first = Math.max(STEP, v.indexOf(cur()) + 60, rail._key === key ? (rail._count || 0) : 0); rail._key = key;
  rail._more = () => { if (shown < v.length) more(STEP); }; rail._need = it => { const i = v.indexOf(it); if (i >= shown) more(i - shown + 60); };
  more(first); renderChips(); centerOn(cur(), false);
}
rail.addEventListener('scroll', () => { if (rail._more && rail.scrollTop + rail.clientHeight > rail.scrollHeight - 1200) rail._more(); }, { passive: true });
const SIZE_TABS = new Set(['biblio', 'videoteca', 'vestidor', 'photo', 'movie', 'cartoon', 'expr', 'hair', 'creaciones', 'video', 'crear']);
state.gsize = state.gsize || {}; try { Object.assign(state.gsize, JSON.parse(localStorage.getItem('am_gsize') || '{}')); } catch (e) {}
function gsize() { return state.gsize[state.tab] || 'm'; }
function firstVisibleCell() { const top = rail.getBoundingClientRect().top + 4; return [...rail.querySelectorAll('.cell')].find(c => c.getBoundingClientRect().bottom > top) || null; }
function keepAnchor(anchorIt, offset) { if (!anchorIt) { rail.scrollTop = 0; return; } const c = [...rail.querySelectorAll('.cell')].find(x => x._it === anchorIt); if (!c) return; rail.scrollTop += c.getBoundingClientRect().top - rail.getBoundingClientRect().top - (offset || 0); }
$('#gsize').onclick = e => { const b = e.target.closest('button'); if (!b) return; const fc = firstVisibleCell(); const anchor = fc && fc._it; const off = fc ? Math.max(0, fc.getBoundingClientRect().top - rail.getBoundingClientRect().top) : 0; state.gsize[state.tab] = b.dataset.s; persist('am_gsize', JSON.stringify(state.gsize)); renderRail(); renderChips(); keepAnchor(anchor, off); setTimeout(() => keepAnchor(anchor, off), 60); };
const charOf = i => (i.meta || {}).char || 'aria';
const cset = () => Array.isArray(state.cchar) ? state.cchar : state.cchar ? [state.cchar] : [];   // personajes marcados en el filtro (ninguno = todos)
const charsOf = i => { const m = i.meta || {}; return Array.isArray(m.chars) && m.chars.length ? m.chars : [charOf(i)]; };   // una imagen con dos personajes cuenta para los dos
function charFilt(v) { const s = cset(); return s.length ? v.filter(i => i.pending || s.every(id => charsOf(i).includes(id))) : v; }   // uno marcado: donde sale ese; varios: solo donde salen TODOS juntos. Lo que se está generando se ve siempre
function charChips(box) { // en Creaciones, un filtro por personaje (solo si hay creaciones de más de uno)
  const ids = [...new Set(TABS.creaciones.items.filter(i => !isVarAux(i) && i.meta).flatMap(charsOf))]; const all = charList().filter(c => ids.includes(c.id)); if (all.length < 2) { state.cchar = null; return; }
  all.forEach(c => { const on = cset().includes(c.id); const b = el('button', 'charchip' + (on ? ' on' : ''), `${c.avatar ? `<img src="${c.avatar}" alt="">` : ''}${esc((c.name || '').split(' ')[0])}`); b.title = on ? 'Quitar a ' + c.name + ' del filtro' : 'Ver las creaciones de ' + c.name + ' (con varios marcados: solo donde salen juntos)'; b.onclick = () => { const s0 = cset(); state.cchar = on ? s0.filter(x => x !== c.id) : s0.concat([c.id]); renderRail(); renderChips(); rail.scrollTop = 0; }; box.appendChild(b); }); }
function renderChips() { const box = $('#gridChips'); box.innerHTML = ''; $('#gsize').style.display = SIZE_TABS.has(state.tab) ? '' : 'none'; [...$('#gsize').children].forEach(b => b.classList.toggle('on', b.dataset.s === gsize())); let hd = $('#hdChips'); if (!hd) { hd = el('div', 'hdchips'); hd.id = 'hdChips'; $('.gridhd').insertBefore(hd, $('#pickTitle')); } hd.innerHTML = ''; const ch = chips(state.tab); box.classList.remove('two'); if (ch) { box.appendChild(ch); if (state.tab === 'crear' || state.tab === 'creaciones') { const row = el('div', 'chips charrow'); charChips(row); if (row.children.length) { box.appendChild(row); box.classList.add('two'); } } } box.style.display = ch ? '' : 'none'; const sr = $('#search'); sr.value = state.search[state.tab] || ''; sr.placeholder = 'Buscar…'; }
function centerOn(it, smooth) { // scroll mínimo DENTRO de la cuadrícula (scrollIntoView movía también el body)
  if (it && rail._need) rail._need(it);
  const d = [...rail.children].find(x => x._it === it); if (!d) return; const cTop = d.offsetTop - rail.offsetTop, cBot = cTop + d.offsetHeight, vTop = rail.scrollTop, vBot = vTop + rail.clientHeight; let top = null;
  if (cTop < vTop + 4) top = cTop - 8; else if (cBot > vBot - 4) top = cBot - rail.clientHeight + 8; if (top === null) return;
  rail._prog = true; rail.scrollTo({ top: Math.max(0, top), behavior: smooth ? 'smooth' : 'auto' }); setTimeout(() => rail._prog = false, smooth ? 500 : 30); }
state.k = 0; let kAnim = 0;
function setK(k) { // 0 = imagen grande · 1 = compacta; la rejilla del escenario se interpola con la rueda (sin saltos)
  k = Math.max(0, Math.min(1, k)); state.k = k; const st = $('#stageEl'); if (st.classList.contains('gallery') || st.classList.contains('solo')) { st.style.gridTemplateRows = ''; return; } st.style.gridTemplateRows = `minmax(0,${(62 - 45 * k).toFixed(2)}fr) minmax(0,${(38 + 45 * k).toFixed(2)}fr)`; st.classList.toggle('compact', k > 0.6); sizeMirror(); }
function setCompact(v) { const target = v ? 1 : 0; if (state.k === target) return; cancelAnimationFrame(kAnim); if (document.hidden) { setK(target); return; } const from = state.k, t0 = performance.now(); const step = t => { const u = Math.min(1, (t - t0) / 220); setK(from + (target - from) * (1 - Math.pow(1 - u, 3))); if (u < 1) kAnim = requestAnimationFrame(step); }; kAnim = requestAnimationFrame(step); }
function wheelK(e) { // devuelve true si la rueda se ha gastado en encoger/agrandar la imagen
  if ($('#stageEl').classList.contains('gallery') || $('#stageEl').classList.contains('solo')) return false; const can = rail.scrollHeight > rail.clientHeight + 20; cancelAnimationFrame(kAnim);
  if (e.deltaY > 0 && state.k < 1 && can) { setK(state.k + e.deltaY / 420); return true; }
  if (e.deltaY < 0 && rail.scrollTop <= 2 && state.k > 0) { setK(state.k + e.deltaY / 420); return true; }
  return false;
}
rail.addEventListener('wheel', e => { if (wheelK(e)) e.preventDefault(); }, { passive: false });
let searchT = 0; // el buscador espera a que dejes de teclear: antes repintaba toda la cuadrícula en cada tecla
$('#search').addEventListener('input', e => { const val = e.target.value.trim(); clearTimeout(searchT); searchT = setTimeout(() => searchNow(val), 160); });
function searchNow(val) { const e = { target: { value: val } }; state.search[state.tab] = e.target.value.trim(); renderRail(); const v = view(); if (v.length && !v.includes(cur())) select(v[0], true, false); else if (v.length) $('#count').textContent = `${v.indexOf(cur()) + 1} / ${v.length}`; }
function fitAr(it, src) { // ajusta el espejo al tamaño real de la imagen (una vez)
  if (it._ar) { if (arOverride !== it._ar) { arOverride = it._ar; sizeMirror(); } return; }
  const im = new Image(); im.onload = () => { it._ar = im.naturalWidth / im.naturalHeight; if (cur() === it && state.tab !== 'perfil') { arOverride = it._ar; sizeMirror(); } }; im.src = src;
}
function paint(it, fast) {
  const t = TABS[state.tab]; const v = view();
  $('#plName').textContent = it.name; $('#plSub').textContent = t.sub(it); $('#count').textContent = `${v.indexOf(it) + 1} / ${v.length}`;
  mirror.classList.toggle('video', t === TABS.perfil);
  if (t === TABS.perfil) { mirror.classList.remove('cached'); $('#plName').textContent = C.perfil.name; if (!fast && it.angle != null) turnTo(it.angle, true); }
  else if (t === TABS.video) { /* modo cine: el reproductor enseña los vídeos */ }
  else if (t === TABS.creaciones || t === TABS.videoteca) { /* galería: el popup / la mini enseñan el elemento */ }
  else if (t === TABS.biblio) { mirror.classList.remove('vidmode'); mirror.classList.add('cached', 'bib'); mirror.querySelector('.tag').textContent = 'biblioteca · para recrear'; fitAr(it, it.image); showImage(it.image, fast); }
  else if (LIVE && t === TABS.crear && it.custom && jobBg(it)) { // generando: debajo del «Generando» se ve la imagen que se está recreando, no el resultado anterior
    const bg = jobBg(it); mirror.classList.remove('cached'); if (arOverride !== null) { arOverride = null; sizeMirror(); } bgAr(bg); showImage(bg, fast);
  }
  else if (LIVE) { // en vivo: se elige y luego se pulsa Generar. Lo ya existente solo se enseña cuando se ha «generado» (paripé) en esta sesión
    const ex = existingImage(state.tab, it); const revealed = state.done.has(it.id);
    if (ex && (revealed || t === TABS.hair || t === TABS.expr || t === TABS.vestidor)) { if (t === TABS.vestidor && !revealed) state.done.add(it.id);
      mirror.classList.toggle('cached', revealed); mirror.querySelector('.tag').textContent = it.live ? 'generada antes · API' : 'ya generada · caché';
      let ar2 = null; if (it.live) { fitAr(it, ex); ar2 = it._ar || null; } else if (CONVERT.has(state.tab)) ar2 = REF_AR;
      if (ar2 !== arOverride) { arOverride = ar2; sizeMirror(); }
      showImage(ex, fast);
    } else if (t === TABS.vestidor) { mirror.classList.remove('cached'); showImage(it.ficha, fast); }
    else if (CONVERT.has(state.tab)) { mirror.classList.remove('cached'); if (arOverride !== null) { arOverride = null; sizeMirror(); } showImage(it.files.main, fast); }   // muestra del estilo
    else if (t === TABS.crear && it.custom) { mirror.classList.remove('cached'); const bib = state.comp.biblio; if (arOverride !== null) { arOverride = null; sizeMirror(); } if (bib) fitAr(bib, bib.image); showImage(bib ? bib.image : (userPhoto || (CH().aria ? C.base.photo : CH().foto)), fast); mirror.classList.add('cached'); mirror.querySelector('.tag').textContent = bib ? 'lienzo · imagen a recrear · sin generar' : 'combinación nueva · sin generar'; }
    else { mirror.classList.remove('cached'); if (t !== TABS.crear) { if (arOverride !== null) { arOverride = null; sizeMirror(); } showImage(userPhoto || baseDefault(state.tab), fast); mirror.classList.add('cached'); mirror.querySelector('.tag').textContent = t === TABS.vestidor ? 'Aria · base · sin la prenda todavía' : 'sin generar'; } }   // prenda / creación: el espejo mantiene la imagen anterior hasta Generar
  }
  else if (t === TABS.vestidor || t === TABS.crear) {
    if (state.done.has(it.id) && it.looks && it.looks.length) { mirror.classList.add('cached'); showImage(itemSrc(it), fast); }
    else { mirror.classList.remove('cached'); } // aún no generado: el espejo mantiene el look anterior
  } else if (CONVERT.has(state.tab)) {
    const conv = convSrc(it); const isConv = state.done.has(it.id) && !!conv;
    mirror.classList.toggle('cached', isConv); mirror.querySelector('.tag').textContent = isConv ? (it._ms > 20000 ? 'tu foto · convertida en vivo' : 'tu foto · convertida') : 'caché · 0 ms';
    const ar2 = isConv ? REF_AR : null; if (ar2 !== arOverride) { arOverride = ar2; sizeMirror(); }
    showImage(isConv ? conv : it.files.main, fast);
  } else { mirror.classList.toggle('cached', state.done.has(it.id)); showImage(itemSrc(it), fast); }
  if (t === TABS.crear && !it.custom) { $('#plSub').textContent = recipeSub(it); }
  const jb = (t !== TABS.perfil && t !== TABS.creaciones) ? jobFor(it) : null; mirror.classList.toggle('queue', !!jb); if (jb) { updateQueueOverlay(jb); if (t === TABS.crear && it.custom) { const n = [...JOBS.values()].filter(j => !j.end && j.it === it).length; if (n > 1) $('#genTxt').textContent = `Generando ${n} creaciones · la primera que termine aparece aquí`; } }
  mirror.classList.toggle('errored', !jb && !!it._err && t !== TABS.perfil && t !== TABS.creaciones); if (it._err && !jb) { const cr = errCreditos(it._err); $('#errTit').textContent = cr ? 'No hay suficientes créditos' : 'No se ha podido generar'; $('#errTxt').textContent = cr ? `Recarga tu saldo de ${cr.prov} y vuelve a generar. Esta imagen no se ha cobrado.` : it._err; const by = $('#errBuy'); by.style.display = cr ? '' : 'none'; if (cr) by.href = cr.url; } setTimeout(syncMini, 0);
  mirror.style.cursor = mirrorClickable() ? 'zoom-in' : ''; mirror.title = mirrorClickable() ? 'Abrir en grande' : '';
  [...rail.children].forEach(d => d.classList.toggle('on', d._it === it));
}
function select(it, fast, scroll) {
  if (state.busy) return;
  const t = TABS[state.tab]; const prev = cur(); state.sel[state.tab] = it; if (t === TABS.crear && !it.custom) applyRecipe(it); paint(it, fast); renderSide();
  if (scroll) { setCompact(false); centerOn(it, true); }
  if (!fast && prev !== it && t !== TABS.perfil) { const ex = LIVE ? existingImage(state.tab, it) : null; log(`<span class="g">▸</span> ${t.label.toLowerCase()} <span class="w">«${it.name}»</span> <span class="g">· ${ex ? (it.live ? 'generada antes por la API · se enseña sin gastar' : 'ya generada · caché local · 0 ms') : LIVE ? 'sin generar todavía' : 'look precomputado · caché local · 0 ms'}</span>`); }
}
let justDragged = false;
function step(dir) { if (state.busy || state.spinning || state.tab === 'crear' || state.tab === 'perfil') return; const v = view(); if (!v.length) return; const i = v.indexOf(cur()); const it = v[(i + dir + v.length) % v.length]; select(it, true, true); }

// ----------------------------------------------------------------- panel lateral
function chips(tab) {
  const t = TABS[tab]; const NEWTABS = ['vestidor', 'hair', 'expr', 'cartoon', 'movie', 'photo', 'biblio', 'videoteca'];
  if (tab === 'crear') { const box = el('div', 'chips'); const L = TABS.creaciones.items; const f = state.filter.crearG; const mk = (key, label) => { const b = el('button', f === key ? 'on' : '', label); b.onclick = () => { state.filter.crearG = key; renderRail(); renderChips(); rail.scrollTop = 0; }; box.appendChild(b); };
    mk(null, 'Todos'); mk('Imágenes', `Imágenes <span style="opacity:.5">${L.filter(i => !i.hidden && !isVarAux(i) && i.kindLabel === 'Imágenes').length}</span>`); const nv = L.filter(i => !i.hidden && !isVarAux(i) && i.kindLabel === 'Vídeos').length; if (nv) mk('Vídeos', `Vídeos <span style="opacity:.5">${nv}</span>`); const nx = L.filter(i => isVarAux(i) && !i.pending).length; if (nx) { mk('Variaciones', `Variaciones <span style="opacity:.5">${nx}</span>`); box.lastChild.title = 'Colores de peinados y prendas'; } const nh = L.filter(i => i.hidden && !isVarAux(i)).length; if (nh) { mk('Ocultos', `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" style="vertical-align:-1px"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg> ${nh}`); box.lastChild.title = 'Ocultas'; } return box; }
  if (!t.filters && !NEWTABS.includes(tab)) return null;
  const box = el('div', 'chips');
  if (tab === 'creaciones' && state.cfilt) { const cf = state.cfilt; const back = el('button', 'btn acc', cf.back === 'creaciones' ? '← Todas las creaciones' : `← Volver a ${TABS[cf.back].label}`); back.style.cssText = 'padding:9px 16px;font-size:11.5px;flex:0 0 auto'; back.onclick = () => clearCfilt(true); box.appendChild(back); back.textContent = state.navStack.length ? '← Volver' : back.textContent; cf.sel.forEach(x => { const ch = el('button', 'on', `${COMP[x.tab] || ''} · ${x.name} <span style="opacity:.8">✕</span>`); ch.title = 'Quitar este componente del filtro'; ch.onclick = () => { const rest = cf.sel.filter(y => y !== x); if (rest.length) { const sn = state.navStack.pop(); showCreationsSel(rest, cf.back, sn); } else clearCfilt(false); }; box.appendChild(ch); }); box.appendChild(el('span', 'ttl', `${view().length} con ${cf.sel.length > 1 ? 'todo esto' : 'esto'}`)); return box; }
  if (tab === 'videoteca' && state.vtGroup) { const back = el('button', 'btn acc', '← Atrás · toda la Filmoteca'); back.style.cssText = 'padding:9px 16px;font-size:11.5px;flex:0 0 auto'; back.onclick = () => { const pg = TABS.videoteca.items.find(i => i.n === state.vtGroup); state.vtGroup = null; if (pg) state.sel.videoteca = pg; renderRail(); renderChips(); renderSide(); rail.scrollTop = state.vtScroll || 0; setTimeout(() => { rail.scrollTop = state.vtScroll || 0; }, 60); }; box.appendChild(back); box.appendChild(el('span', 'ttl', `Ficha Nº ${state.vtGroup} · ${view().length} vídeos`)); return box; }
  if (tab === 'biblio' && state.bibGroup) { const back = el('button', 'btn acc', `← Atrás · todos los carruseles`); back.style.cssText = 'padding:9px 16px;font-size:11.5px;flex:0 0 auto'; back.onclick = () => { state.bibGroup = null; renderRail(); rail.scrollTop = state.bibScroll || 0; setTimeout(() => { rail.scrollTop = state.bibScroll || 0; }, 60); }; box.classList.add('bibhead'); box.appendChild(back); box.appendChild(el('span', 'ttl', `Carrusel Nº ${state.bibGroup}`)); return box; }
  const all = el('button', state.filter[tab] ? '' : 'on', 'Todos'); all.onclick = () => { state.filter[tab] = null; state.bibGroup = null; setTab(tab); }; box.appendChild(all);
  if (tab === 'vestidor') { const nf = t.items.filter(i => i.fav).length; if (nf) { const fb_ = el('button', state.filter[tab] === '__fav' ? 'on' : '', `★ Favoritos <span style="opacity:.5">${nf}</span>`); fb_.onclick = () => { state.filter[tab] = '__fav'; setTab(tab); }; box.appendChild(fb_); } }
  if (NEWTABS.includes(tab)) { const nn = t.items.filter(i => !i.group && isNew(i)).length; if (nn) { const nb = el('button', state.filter[tab] === '__new' ? 'on' : '', `New <span style="opacity:.5">${nn}</span>`); nb.onclick = () => { state.filter[tab] = '__new'; state.bibGroup = null; setTab(tab); }; box.appendChild(nb); } }
  (t.filters || []).forEach(f => { const n = f === 'Variaciones' ? t.items.filter(i => isVarAux(i) && !i.pending).length : f === 'Ocultos' ? t.items.filter(i => i.hidden && !isVarAux(i)).length : t.items.filter(i => (Array.isArray(i[t.fkey]) ? i[t.fkey].includes(f) : i[t.fkey] === f) && !i.hidden && !isVarAux(i)).length; if (!n) return; const b = el('button', state.filter[tab] === f ? 'on' : '', `${f} <span style="opacity:.5">${n}</span>`); b.onclick = () => { state.filter[tab] = f; state.bibGroup = null; setTab(tab); }; box.appendChild(b); });
  return box;
}
function sec(title, node, small) { const s = el('div', 'sec'); if (title) s.appendChild(el('h3', '', title + (small ? `<small>${small}</small>` : ''))); if (node) s.appendChild(node); return s; }
function pols(it, labels) { const p = el('div', 'pols'); ['real1', 'real2'].forEach((k, i) => { if (!it.files[k]) return; const d = el('div', 'pol', `<img src="${it.files[k]}" alt=""><small>${labels[i]}</small>`); d.onclick = () => lightbox(it.files[k], `${it.name} · ${labels[i]}`); p.appendChild(d); }); return p.children.length ? p : null; }
function lab(txt) { return el('span', 'lbl', txt); }
function genSettings(tab, it) { // modelo · calidad · formato · prompt (+ foto de referencia en Estilo/Efectos/Movie looks)
  const box = el('div', 'stack'); const m = curModel();
  if (CONVERT.has(tab)) { box.appendChild(lab('Foto de referencia')); box.appendChild(dropzone()); }
  if (tab === 'crear' && state.nsfw && modelKey !== NSFW_MODEL) nsfwModel();
  const msel = el('select', 'sel'); MODELS.forEach(x => { const o = document.createElement('option'); o.value = x.key; const off = tab === 'crear' && state.nsfw && x.key !== NSFW_MODEL; o.textContent = `${x.name} · ${fmtUsd(x.usd[state.quality])}${off ? ' · no admite NSFW' : ''}`; o.disabled = off; o.title = x.nota || ''; msel.appendChild(o); });
  UNAVAILABLE.forEach(u => { const o = document.createElement('option'); o.value = 'x:' + u.key; o.disabled = true; o.textContent = `${u.name} · ${u.why}`; msel.appendChild(o); });
  msel.value = modelKey; msel.onchange = () => { state.modelAntes = null; modeloManual(true); setModel(msel.value); renderSide(); };
  const w1 = el('div'); { const lr = el('div', 'lblrow'); lr.appendChild(lab('Modelo de imagen')); const bb = tab === 'crear' && state.comp.biblio;
    if (bb && !bb.double && !state.nsfw && modoDrop(bb) === 'swap' && MODELS.some(x => x.key === MISMA_MODEL)) { const okm = modelKey === MISMA_MODEL; const rc = el('span', 'recm' + (okm ? ' ok' : ''), okm ? '★ recomendado para «Misma foto»' : 'para «Misma foto»: GPT Image 2.5 →'); if (!okm) { rc.title = 'Usar el modelo recomendado'; rc.onclick = () => { modeloManual(false); state.modelAntes = modelKey; setModel(MISMA_MODEL); state.modelFlash = Date.now(); renderSide(); }; } lr.appendChild(rc); }
    w1.appendChild(lr); if (state.modelFlash && Date.now() - state.modelFlash < 1700) { msel.classList.add('flash'); msel.style.animationDelay = -(Date.now() - state.modelFlash) + 'ms'; } }
  if (tab === 'crear') { const rw = el('div', 'nsfwrow'); rw.appendChild(msel); const nw = el('div', 'nsfwwrap'); const nb = el('button', 'nsfwdot' + (state.nsfw ? ' on' : ''), state.nsfw ? '🔥' : '<i></i>'); nb.title = state.nsfw ? 'NSFW activado' : 'Opciones'; const dd = el('div', 'nsfwdd'); const opt = el('div', 'it' + (state.nsfw ? ' on' : ''), `<span class="sw"></span>🔥 NSFW`); opt.title = 'Quita la prenda y toda mención a ropa del prompt y añade «No clothes, she is naked.»'; opt.onclick = e => { e.stopPropagation(); state.nsfw = !state.nsfw; persist('am_nsfw', state.nsfw ? '1' : '0'); const sw = nsfwModel(); renderSide(); paint(cur(), true); toast((state.nsfw ? 'NSFW activado' : 'NSFW desactivado') + sw); }; dd.appendChild(opt); nb.onclick = e => { e.stopPropagation(); dd.classList.toggle('on'); }; document.addEventListener('click', () => dd.classList.remove('on')); nw.appendChild(nb); nw.appendChild(dd); rw.appendChild(nw); w1.appendChild(rw); } else w1.appendChild(msel); box.appendChild(w1);
  const row = el('div', 'ctl');
  const qsel = el('select', 'sel'); [['std', 'Estándar · ' + (m.std || '1k')], ['high', 'Alta · ' + (m.high || '2k')]].forEach(([k, n]) => { const o = document.createElement('option'); o.value = k; o.textContent = `${n} · ${fmtUsd(m.usd[k])}`; qsel.appendChild(o); }); qsel.value = state.quality;
  qsel.onchange = () => { state.quality = qsel.value; persist('am_quality', state.quality); renderSide(); };
  const asel = el('select', 'sel'); ASPECTS.forEach(a => { const o = document.createElement('option'); o.value = a; o.textContent = a + (a === '3:4' ? ' · retrato' : a === '9:16' ? ' · reel' : a === '16:9' ? ' · cine' : a === '1:1' ? ' · cuadrado' : ''); asel.appendChild(o); }); asel.value = state.aspect;
  asel.onchange = () => { state.aspect = asel.value; persist('am_aspect', state.aspect); renderSide(); };
  const w2 = el('div'); w2.appendChild(lab('Calidad')); w2.appendChild(qsel); row.appendChild(w2); box.appendChild(row); const w3 = el('div'); w3.appendChild(lab('Formato')); w3.appendChild(aspectPicker(ASPECTS, tab === 'vestidor' ? (state.aspectV || '1:1') : state.aspect, v => { if (tab === 'vestidor') { state.aspectV = v; persist('am_aspect_v', v); } else { state.aspect = v; persist('am_aspect', v); } renderSide(); })); box.appendChild(w3);
  if (tab === 'crear') { const sig = compSig(); if (it._promptSig !== sig) { it._prompt = null; it._promptSig = sig; it._last = null; } } // el prompt siempre corresponde a lo que hay puesto (y el espejo, a la combinación)
  const plan = livePlan(tab, it); const pl = el('div', 'lblrow'); pl.appendChild(lab('Prompt')); const rst = el('span', 'lnk', '↺ original'); rst.style.display = it._prompt ? '' : 'none'; pl.appendChild(rst); box.appendChild(pl);
  const pw = el('div', 'pw'); const ta = el('textarea', 'prompt'); ta.value = it._prompt || plan.prompt; ta.spellcheck = false;
  ta.oninput = () => { it._prompt = ta.value.trim() === plan.prompt.trim() ? null : ta.value; rst.style.display = it._prompt ? '' : 'none'; };
  rst.onclick = () => { it._prompt = null; ta.value = plan.prompt; rst.style.display = 'none'; }; pw.appendChild(ta); if (tab === 'crear') { promptWithMenu(ta, pw, () => planRefs(tab, it)); pl.classList.add('pleft');
    const ex = el('div', 'pexp'); const eb = el('span', 'lnk', state.promptExp ? '▴ contraer' : '▾ ver prompt completo'); ex.appendChild(eb); pw.appendChild(ex);
    const fit = () => { if (state.promptExp) { ta.style.height = 'auto'; ta.style.height = ta.scrollHeight + 2 + 'px'; ta.style.maxHeight = 'none'; } else { ta.style.height = ''; ta.style.maxHeight = ''; } };
    eb.onclick = () => { state.promptExp = !state.promptExp; eb.textContent = state.promptExp ? '▴ contraer' : '▾ ver prompt completo'; fit(); }; ta.addEventListener('input', () => { if (state.promptExp) fit(); }); requestAnimationFrame(fit); } box.appendChild(pw);
  const refsTxt = plan.images.length > m.refs ? `${plan.images.length} referencias → ${m.name} solo admite ${m.refs}: el resto va descrito en el prompt` : `${plan.images.length} referencia(s): ${plan.images.map(i => i.data ? 'tu foto' : i.path.split('/').pop()).join(', ')}`;
  if (tab !== 'crear') box.appendChild(el('div', 'status', refsTxt + (plan.images.length > m.refs ? ' · <b>Consejo:</b> con Grok Image 2.0 (10) o Marketing Studio (16) se mandan todas como imagen.' : '')));
  else if (plan.images.length > m.refs) box.appendChild(el('div', 'status', `${plan.images.length} referencias → ${m.name} admite ${m.refs}: se cambia solo a un modelo que las admita.`));
  return box;
}
state.refOrder = state.refOrder || [];
function sinLienzo(bib) { // ¿se crea una imagen NUEVA desde el prompt de la escena, sin mandar la foto? Las comparativas dobles y, con un personaje que no es Aria, cualquier imagen de la Fototeca (su foto enseña a Aria y Seedream conserva su cara al editarla)
  return !!(bib && (bib.double || (modoDrop(bib) === 'prompt' && (bib.drop ? bib.neutro : (bib.neutro || bib.prompt))))); }
function modoDrop(bib) { return bib.modo || ((!bib.drop && CH().aria && !extraChars().length) ? 'swap' : 'prompt'); }   // de partida, «desde su descripción»; solo Aria sola sobre una foto suya de la Fototeca parte de «misma foto»
//   // foto arrastrada: «misma foto» (se edita cambiando a la persona) o «desde su descripción» (se lee la foto y se crea una imagen nueva: la foto no se envía). Con un personaje propio, por defecto la segunda: es la que respeta siempre su cara
const MISMA_MODEL = 'gptimg';
function modeloManual(v) { // ¿ha elegido el usuario su modelo en el desplegable? Entonces manda el suyo (se recuerda entre visitas)
  if (v !== undefined) { state.modelManual = !!v; persist('am_model_manual', v ? '1' : '0'); } else if (state.modelManual === undefined) { try { state.modelManual = localStorage.getItem('am_model_manual') === '1'; } catch (e) { state.modelManual = false; } } return state.modelManual; }
function modeloPorModo(bib) { // con NSFW manda Seedream; si el modelo se ha elegido a mano, no se toca
  if (!bib || bib.double || state.nsfw || modeloManual() || !MODELS.some(m => m.key === MISMA_MODEL)) return;
  if (modoDrop(bib) === 'swap') { if (modelKey !== MISMA_MODEL) { state.modelAntes = modelKey; setModel(MISMA_MODEL); state.modelFlash = Date.now(); } }
  else if (state.modelAntes && modelKey === MISMA_MODEL && MODELS.some(m => m.key === state.modelAntes)) { setModel(state.modelAntes); state.modelAntes = null; state.modelFlash = Date.now(); } }
function leerEscena(bib) { // lee la foto arrastrada (lugar, pose, luz, encuadre, ropa; nunca quién es) para poder crearla de nuevo sin enviarla
  if (bib._leyendo || bib.neutro || bib._fallo || !LIVE) return bib._leyendo || null;
  bib._leyendo = (async () => {
    try { const r = await fetch('/api/describir', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: bib.image.startsWith('data:') ? { data: bib.image } : { path: bib.image.split('?')[0] }, modo: 'escena' }) }).then(x => x.json());
      if (!r || !r.ok || !r.desc) throw new Error((r && r.error) || 'sin respuesta'); bib.neutro = r.desc; bib.ropa = (r.extra || [])[0] || ''; bib.figura = (r.extra || [])[1] || ''; if (r.ref) { bib.image = r.ref; bib.thumb = r.ref; } }
    catch (e) { bib._fallo = true; toast('No se ha podido leer la foto: se recreará la misma foto'); }
    finally { bib._leyendo = null; if (state.comp.biblio === bib) { badge(); if (state.tab === 'crear') { renderSide(); const c = cur(); if (c) paint(c, true); } } } })();
  return bib._leyendo; }
function crearRefs() { // referencias de Crear imagen en el orden elegido (arrastrando); las nuevas se añaden al final en el orden por defecto
  const c = state.comp; const v = c.vestidor, h = c.hair, e = c.expr, bib = c.biblio; const all = [];
  if (bib && !sinLienzo(bib)) all.push({ key: 'canvas', name: bib.name, thumb: compThumb('biblio', bib), img: bib.image.startsWith('data:') ? { data: bib.image } : { path: bib.image }, comp: 'biblio' });
  const ch = CH(); const xs = extraChars(); if (!bib && !xs.length) all.push({ key: 'canvas', name: ch.aria ? 'Aria en estudio' : ch.short + ' de frente', thumb: ch.aria ? C.base.thumb : ch.avatar, img: basePhoto(v && !state.nsfw ? 'body' : 'face'), fixed: true });
  all.push({ key: 'ficha', name: 'Ficha 360 de ' + ch.short, thumb: ch.ficha, img: FICHA(), fixed: true });
  const accs = window.accActive ? accActive().filter(a => window.accAsRef ? accAsRef(a) : a.img) : []; const accAt = all.length; // complementos del personaje con foto (su móvil, etc.): se colocan después de contar el resto
  if (ch.cuerpo && (bib || state.nsfw)) all.push({ key: 'cuerpo', name: 'Cuerpo de ' + ch.short, thumb: ch.cuerpo, img: { path: ch.cuerpo.split('?')[0] }, fixed: true }); // su cuerpo real: al recrear una foto no se hereda el cuerpo de la otra persona
  if (v && !state.nsfw) all.push({ key: 'vestidor', name: v.name, thumb: v.card, img: v.pending ? { data: v.ficha } : { path: v.ficha }, comp: 'vestidor' });
  if (h && ch.aria) { const hv = hairVarColor(h); all.push({ key: 'hair',   /* con otro personaje el peinado va descrito en el prompt: la imagen enseña a Aria y arrastra su cara */ name: h.name + (hv ? ' · ' + hv : ''), thumb: state.hairVar || h.files.thumb, img: h.pending ? { data: h.files.main } : { path: (state.hairVar || h.files.main).split('?')[0] }, comp: 'hair' }); }
  if (e && ch.aria) all.push({ key: 'expr', name: e.name, thumb: e.files.thumb, img: e.pending ? { data: e.files.main } : { path: e.files.main }, comp: 'expr' });
  xs.forEach(x => { all.push({ key: 'ficha:' + x.id, name: 'Ficha 360 de ' + x.short, thumb: x.ficha, img: { path: x.ficha }, fixed: true }); const m = state.compBy[x.id] || {};
    if (m.vestidor && !state.nsfw) all.push({ key: 'vestidor:' + x.id, name: `${m.vestidor.name} · ${x.short}`, thumb: m.vestidor.card, img: m.vestidor.pending ? { data: m.vestidor.ficha } : { path: m.vestidor.ficha }, fixed: true });
    if (m.hair && x.aria) all.push({ key: 'hair:' + x.id, name: `${m.hair.name} · ${x.short}`, thumb: m.hair.files.thumb, img: m.hair.pending ? { data: m.hair.files.main } : { path: m.hair.files.main.split('?')[0] }, fixed: true });
    if (m.expr && x.aria) all.push({ key: 'expr:' + x.id, name: `${m.expr.name} · ${x.short}`, thumb: m.expr.files.thumb, img: m.expr.pending ? { data: m.expr.files.main } : { path: m.expr.files.main }, fixed: true }); });
  (state.ipool || []).forEach(r => all.push({ key: 'pool:' + r.id, name: r.name, thumb: r.thumb, img: r.src.startsWith('data:') ? { data: r.src } : { path: r.src }, pool: r }));
  { const room = Math.max(0, (curModel().refs || 16) - all.length); all.splice(accAt, 0, ...accs.slice(0, room).map(a => ({ key: 'acc:' + a.id, name: a.nombre, thumb: a.thumb || a.img, img: { path: a.img.split('?')[0] }, fixed: true }))); } // si no caben todas, los que sobran van descritos en el prompt (su descripción de reserva)
  const ord = state.refOrder; return all.slice().sort((x, y) => { const ix = ord.indexOf(x.key), iy = ord.indexOf(y.key); const ax = ix < 0 ? 1000 + all.indexOf(x) : ix, ay = iy < 0 ? 1000 + all.indexOf(y) : iy; return ax - ay; });
}
function refsNode() { // pool único de Crear imagen: ✕ en todas (menos la ficha), etiqueta debajo, arrastrar para reordenar
  const wrap = el('div', 'pool small refs'); const R = crearRefs();
  R.forEach((r, i) => {
    const c = el('div', 'pref lab' + (r.fixed ? ' fx' : '')); c.draggable = true; c.dataset.key = r.key; c.title = r.name;
    c.innerHTML = `<img src="${r.thumb}" alt=""><span class="tag">@Image${i + 1}</span>`;
    if (!r.fixed) { const x = el('button', 'x', '✕'); x.title = 'Quitar'; x.onclick = ev => { ev.stopPropagation(); if (r.comp) { delete state.comp[r.comp]; badge(); } else if (r.pool) { const k = state.ipool.indexOf(r.pool); if (k >= 0) state.ipool.splice(k, 1); } renderSide(); paint(cur(), true); }; c.appendChild(x); }
    c.onclick = () => lightbox(r.img.data || r.img.path, r.name);
    c.addEventListener('dragstart', ev => { ev.dataTransfer.setData('text/ref', r.key); ev.dataTransfer.effectAllowed = 'move'; c.classList.add('drag'); });
    c.addEventListener('dragend', () => c.classList.remove('drag'));
    c.addEventListener('dragover', ev => { if (ev.dataTransfer.types.includes('text/ref')) { ev.preventDefault(); ev.stopPropagation(); c.classList.add('tgt'); } });
    c.addEventListener('dragleave', () => c.classList.remove('tgt'));
    c.addEventListener('drop', ev => { const k = ev.dataTransfer.getData('text/ref'); if (!k) return; ev.preventDefault(); ev.stopPropagation(); c.classList.remove('tgt'); const keys = crearRefs().map(z => z.key); const from = keys.indexOf(k), to = keys.indexOf(r.key); if (from < 0 || to < 0 || from === to) return; keys.splice(to, 0, keys.splice(from, 1)[0]); state.refOrder = keys; renderSide(); });
    wrap.appendChild(c);
  });
  const add = el('div', 'pref add lab'); add.innerHTML = '<b>＋</b>'; add.title = 'Añadir imágenes de tu ordenador (o arrástralas aquí)';
  const inp = document.createElement('input'); inp.type = 'file'; inp.multiple = true; inp.accept = 'image/*'; inp.style.display = 'none'; inp.onchange = () => poolAddFiles(inp.files, state.ipool, true); add.appendChild(inp); add.onclick = () => inp.click(); wrap.appendChild(add);
  ['dragenter', 'dragover'].forEach(ev => wrap.addEventListener(ev, e => { if (e.dataTransfer.types.includes('text/ref')) return; e.preventDefault(); wrap.classList.add('over'); })); wrap.addEventListener('dragleave', () => wrap.classList.remove('over')); wrap.addEventListener('drop', e => { wrap.classList.remove('over'); if (e.dataTransfer.types.includes('text/ref')) return; e.preventDefault(); poolAddFiles(e.dataTransfer.files, state.ipool, true); });
  return wrap;
}
function planRefs(tab, it) { // todas las imágenes que se mandan, en orden, con su etiqueta @ImageN (para el menú del prompt)
  if (tab === 'crear') return crearRefs().map((r, i) => ({ tag: '@Image' + (i + 1), r: { name: r.name, thumb: r.thumb, kind: 'image', src: r.img.data || r.img.path } }));
  const plan = livePlan(tab, it); const c = state.comp; const names = [];
  plan.images.forEach((im, i) => { const src = im.data || im.path; let name = 'referencia', thumb = src;
    if (im.data && c.biblio && c.biblio.image === im.data) name = c.biblio.name; else if (im.path === CH().ficha) name = 'Ficha 360 de ' + CH().short; else if (c.biblio && im.path === c.biblio.image) name = c.biblio.name; else if (c.vestidor && im.path === c.vestidor.ficha) { name = c.vestidor.name; thumb = c.vestidor.card; } else if (c.hair && im.path === c.hair.files.main) name = c.hair.name; else if (c.expr && im.path === c.expr.files.main) name = c.expr.name; else if (im.path === C.base.photo) name = 'Aria en estudio'; else { const r = (state.ipool || []).find(x => x.src === src); if (r) { name = r.name; thumb = r.thumb; } }
    names.push({ tag: '@Image' + (i + 1), r: { name, thumb, kind: 'image', src } }); });
  return names;
}
function liveControls(tab, it) { // Crear imagen: ajustes a la vista + un solo botón
  const box = el('div', 'stack'); const m = curModel();
  box.appendChild(genSettings(tab, it));
  const ex = existingImage(tab, it); const revealed = (tab === 'crear' && it.custom) ? !!ex : state.done.has(it.id);
  const jb = (tab === 'crear' && it.custom) ? null : jobFor(it); const nJobs = [...JOBS.values()].filter(j => !j.end && j.it === it).length; if (nJobs && tab === 'crear') box.appendChild(el('div', 'status', `⏳ <b>${nJobs}</b> generándose ahora mismo: aparecen abajo, en Mis creaciones, y puedes lanzar otra (por ejemplo con otro modelo).`));
  if (jb) { const cb = el('button', 'btn w', `⏳ Generándose · ${Math.round((performance.now() - jb.t0) / 1000)} s · cancelar`); cb.onclick = () => cancelJob(jb, 'cancelada por ti'); box.appendChild(cb); }
  else { const b = el('button', 'btn w acc', `${ex && revealed ? 'Generar nueva' : 'Generar imagen'} · ${fmtUsd(m.usd[state.quality])}`); b.title = ex && !revealed ? 'Ya existe: se enseña al instante sin gastar' : 'Lanza una petición real a api.higgsfield.ai'; b.onclick = () => tryOn(false); box.appendChild(b); }
  box.appendChild(el('div', 'status', ex && revealed ? `Esta es la imagen que ya existía${it.live ? ' (generada con la API)' : ''}. <b>Generar nueva</b> lanza una petición real.` : ex ? `Ya existe una imagen de esta combinación: al pulsar se enseña al instante y sin gastar.` : `Se genera de verdad con lo elegido arriba.`));
  return sec('Generar con la API', box, m.ep);
}
function previewSection(tab, it) { // componentes: «Generar preview» + ajustes plegados
  const box = el('div', 'stack'); const m = curModel(); const ex = existingImage(tab, it); const revealed = state.done.has(it.id);
  const jb = jobFor(it); if (jb) { const cb = el('button', 'btn w', `⏳ Generándose · ${Math.round((performance.now() - jb.t0) / 1000)} s · cancelar`); cb.onclick = () => cancelJob(jb, 'cancelada por ti'); box.appendChild(cb); }

  const f = el('div', 'fold' + (state.fold[tab] ? '' : ' closed')); const h = el('h3', '', 'Ajustes de generación'); h.onclick = () => { state.fold[tab] = !state.fold[tab]; f.classList.toggle('closed', !state.fold[tab]); }; f.appendChild(h); f.appendChild(genSettings(tab, it)); box.appendChild(f);
  return sec('', box);
}

// ----------------------------------------------------------------- VÍDEO (Seedance 2.0 por la API)
const VIDEO_EP = { i2v: 'bytedance/seedance-2.0/image-to-video', r2v: 'bytedance/seedance-2.0/reference-to-video' };
const V_ASPECTS = ['3:4', '9:16', '16:9', '1:1', '4:3', '21:9'];
const ARK_USD = { '2.0': { '480p': 0.07, '720p': 0.15, '1080p': 0.30, '4k': 0.78 }, '2.5': { '480p': 0.10, '720p': 0.23, '1080p': 0.57 } }; // ByteDance directo, $/segundo aprox.
let ARK = false, WS = false; // el puente dice si hay clave de BytePlus / WaveSpeed
const WS_USD = { '480p': 0.12, '720p': 0.24, '1080p': 0.60, '4k': 1.20 }; // WaveSpeed, $/segundo (0,60 $ por 5 s a 480p; 720p ×2, 1080p ×5, 4K ×10)
function vprov() { return (state.vprov === 'ark' && ARK) ? 'ark' : (state.vprov === 'ws' && WS) ? 'ws' : 'hf'; }
function vmodelName() { return vprov() === 'ark' ? `Seedance ${state.vmodel} · ByteDance directo` : vprov() === 'ws' ? 'Seedance 2.0 · WaveSpeed' : 'Seedance 2.0 · Higgsfield'; }
function videoDims(res, aspect) { // Seedance fija el ÁREA del nivel (720p ≈ 1280×720 px): el vídeo real 3:4 salió a 834×1112 (23 sep), no a 720×960
  const area = { '480p': 854 * 480, '720p': 1280 * 720, '1080p': 1920 * 1080, '4k': 3840 * 2160 }[res] || 1280 * 720; const [a, b] = aspect.split(':').map(Number); const r = a / b; const w = Math.round(Math.sqrt(area * r) / 2) * 2, h = Math.round(Math.sqrt(area / r) / 2) * 2; return [w, h]; }
function videoUsd(sec, res, aspect) { const [w, h] = videoDims(res, aspect); if (vprov() === 'ark') { const rate = (ARK_USD[state.vmodel] || ARK_USD['2.0'])[res] || 0.15; return { tokens: 0, usd: sec * rate, w, h, rate }; } if (vprov() === 'ws') { const rate = WS_USD[res] || 0.24; return { tokens: 0, usd: sec * rate, w, h, rate }; } const tokens = Math.ceil(sec * w * h * 24 / 1024); const rate = res === '4k' ? 0.008 : 0.014; return { tokens, usd: tokens / 1000 * rate, w, h }; }
function nearestAspect(ar) { if (!ar) return '3:4'; let best = '3:4', bd = 1e9; V_ASPECTS.forEach(a => { const [x, y] = a.split(':').map(Number); const d = Math.abs(x / y - ar); if (d < bd) { bd = d; best = a; } }); return best; }
function aspectFor(it) { return state.vmode === 'r2v' ? state.vaspect : nearestAspect(it._ar); }
function defaultMotionPrompt(it) { return 'La misma mujer de la imagen, con sus gafas redondas y sus aros, mira a cámara, respira con naturalidad, parpadea y sonríe suavemente; ligerísimo movimiento de cámara en mano; misma luz y mismo fondo; sin texto ni logos.'; }
function libItem(src, name, sub) { const clean = src.startsWith('data:') ? src : src.split('?')[0]; const id = clean.startsWith('data:') ? 'tu-foto' : clean.split('/').pop().replace(/\.[a-z0-9]+$/i, ''); return { id, name, sub: sub || '', thumb: clean, src: clean }; }
function buildVideoLib(j) { // biblioteca de imágenes animables
  const items = []; const seen = new Set(); const add = it => { if (!seen.has(it.id)) { seen.add(it.id); items.push(it); } };
  const MN = { qwen: 'Qwen', grok: 'Grok', mstudio: 'Marketing Studio', ideogram: 'Ideogram', nbp: 'Nano Banana Pro', gptimg: 'GPT Image 2.5', seedream: 'Seedream 5.0' };
  const hiddenSet = new Set(((j && j.creations) || []).filter(c => c.meta && c.meta.hidden).map(c => c.file));
  ((j && j.all) || []).filter(pth => !hiddenSet.has(pth)).forEach(pth => { const base = pth.split('/').pop().replace(/\.[a-z0-9]+$/i, ''); const m = base.match(/^(.*)_([a-z]+)-([0-9a-f]{8})$/) || base.match(/^(.*)_([0-9a-f]{8})$/); const iid = m ? m[1] : base; const src = allItems().find(x => x.id === iid); add(libItem(pth, src ? src.name : base, 'API · ' + (m && MN[m[2]] ? MN[m[2]] : 'Qwen'))); });
  C.vestidor.forEach(v => { if (v.looks && v.looks[0]) add(libItem(v.looks[0], v.name, 'Vestidor')); }); C.crear.forEach(r => { if (r.looks && r.looks[0]) add(libItem(r.looks[0], r.name, 'Creación')); });
  ['cartoon', 'photo', 'movie'].forEach(k => C[k].forEach(i => { if (i.conv) add(libItem(i.conv, i.name, 'conversión')); }));
  add(libItem(C.perfil.refphoto, 'Foto de referencia', 'Aria en el baño')); add(libItem(C.base.photo, 'Aria en estudio', 'base'));
  const vids = (j && j.videos) || {}; const old = new Map(TABS.video.items.map(i => [i.id, i]));
  TABS.video.items = items.map(i => { const o = old.get(i.id) || {}; const it = Object.assign(o, i, { kindLabel: 'Imágenes' }); if (vids[it.id]) it.video = vids[it.id]; return it; });
  ((j && j.creations) || []).filter(c => c.kind === 'video' && !(c.meta && c.meta.hidden)).forEach(c => { const m = c.meta || {}; const id = 'vid:' + c.file.split('/').pop().replace(/\.[a-z0-9]+$/i, ''); const o = old.get(id) || {}; TABS.video.items.push(Object.assign(o, { id, kind: 'video', kindLabel: 'Vídeos', name: m.name || 'Vídeo', sub: m.model || 'Seedance 2.0', thumb: c.poster || (m.source && !String(m.source).startsWith('data:') ? m.source : C.base.thumb), src: c.file, meta: m, t: c.t || 0 })); });
  TABS.video.items.sort((a, b) => (b.kind === 'video') - (a.kind === 'video') || ((b.t || 0) - (a.t || 0)));
  if (!state.sel.video || !TABS.video.items.includes(state.sel.video)) state.sel.video = TABS.video.items[0];
  if (state.ready && state.tab === 'video') { renderRail(); renderSide(); }
}
function videoList() { return TABS.video.items.filter(i => i.kind === 'video').sort((a, b) => (b.t || 0) - (a.t || 0)); }
function cineShow(it) { const c = $('#cine'), v = $('#cineVid'); const L = videoList(); if (!it) it = L[0]; state.vplay = it || null; c.classList.toggle('empty', !it); $('#cineEmpty').style.display = it ? 'none' : ''; if (!it) return; if (v.getAttribute('src') !== it.src) { v.poster = it.thumb || ''; v.src = it.src; v.load(); } v.muted = false; v.play().catch(() => { v.muted = true; v.play().catch(() => {}); }); const i = L.indexOf(it); $('#cineTitle').textContent = `${it.name} · ${it.sub || ''} · ${i + 1} / ${L.length}`; $('#cinePrev').disabled = L.length < 2; $('#cineNext').disabled = L.length < 2; [...rail.children].forEach(x => x.classList.toggle('playing', x._it === it)); if (state.tab === 'video') renderSide(); }
function cineStep(d) { const L = videoList(); if (!L.length) return; cineShow(L[(L.indexOf(state.vplay) + d + L.length) % L.length]); }
function cineInit() { if (!state.vplay || !videoList().includes(state.vplay)) cineShow(null); else cineShow(state.vplay); }
$('#cinePrev').onclick = () => cineStep(-1); $('#cineNext').onclick = () => cineStep(1);
$('#cine').addEventListener('click', e => { if (e.target.closest('.cnav')) return; if (state.k > 0.25) { e.preventDefault(); e.stopPropagation(); setCompact(false); return; } const v = $('#cineVid'); if (e.target === v && state.vplay) { const r = v.getBoundingClientRect(); if (e.clientY < r.bottom - 64) { e.preventDefault(); e.stopPropagation(); v.pause(); openGal(state.vplay); } } }, true);
mirror.addEventListener('click', e => { if (state.tab === 'crear' && state.k > 0.25 && !e.target.closest('button')) { e.stopPropagation(); setCompact(false); } }, true);
function recreateVideo(it) { // carga en el panel todo lo que llevó ese vídeo: referencias, prompt, ajustes y proveedor
  const m = it.meta || {}; state.vpool = []; const src = m.source && !String(m.source).startsWith('data:') ? m.source : null;
  if (src) poolAdd({ id: 'src:' + src, kind: 'image', name: (m.comp && (m.comp['@Image1'] || m.comp.Imagen)) || 'Imagen de partida', src, thumb: src }, true);
  if ((m.refs || []).some(r => /ficha360|Ficha 360/i.test(r))) poolAdd({ id: 'ficha360', kind: 'image', name: 'Ficha 360 de Aria', src: C.perfil.ficha, thumb: C.perfil.ficha }, true);
  state.vprompt = m.prompt || null; if (m.duration) { state.vdur = +m.duration; persist('am_vdur', state.vdur); } if (m.resolution) { state.vres = m.resolution; persist('am_vres', state.vres); } if (m.aspect) { state.vaspect = m.aspect; persist('am_vaspect', state.vaspect); } if (m.audio != null) { state.vaudio = !!m.audio; persist('am_vaudio', state.vaudio ? '1' : '0'); } if (m.provider) { state.vprov = m.provider; persist('am_vprov', m.provider); }
  vbadge(); const vi = TABS.video.items.find(x => x.kind === 'video' && x.src === (it.src || '').split('?')[0]) || (it.kind === 'video' && it.thumb ? it : null); if (vi) cineShow(vi); if (state.tab === 'video') renderSide(); toast('Vídeo cargado en el panel: referencias, prompt y ajustes');
}
function animateCurrent() { const src = (layers[front].getAttribute('src') || ''); if (!src) return; const clean = src.startsWith('data:') ? src : src.split('?')[0]; let it = TABS.video.items.find(i => i.src === clean); if (!it) { it = libItem(clean, cur().name, 'imagen actual'); it._ar = arOverride || null; TABS.video.items.unshift(it); } state.vpool = [poolFromItem(it)]; state.sel.video = it; setTab('video'); select(it, true, true); toast('Elige duración y resolución; el coste sale antes de generar'); }
function paintVideo(it, fast) {
  const vid = $('#vid');
  if (it.video) {
    mirror.classList.add('vidmode', 'cached'); mirror.querySelector('.tag').textContent = 'vídeo generado · Seedance 2.0';
    if (vid.getAttribute('src') !== it.video) { vid.src = it.video; vid.load(); }
    vid.onloadedmetadata = () => { if (cur() === it && vid.videoWidth) { arOverride = vid.videoWidth / vid.videoHeight; sizeMirror(); } };
    if (vid.videoWidth) { arOverride = vid.videoWidth / vid.videoHeight; sizeMirror(); } vid.oncanplay = () => { if (cur() === it && mirror.classList.contains('vidmode')) vid.play().catch(() => {}); }; vid.play().catch(() => {});
  } else {
    mirror.classList.remove('vidmode', 'cached'); vid.pause();
    if (it._ar) { if (arOverride !== it._ar) { arOverride = it._ar; sizeMirror(); } } else { const im = new Image(); im.onload = () => { it._ar = im.naturalWidth / im.naturalHeight; if (cur() === it) { arOverride = it._ar; sizeMirror(); renderSide(); } }; im.src = it.src; }
    showImage(it.src, fast);
  }
}
$('#dlBtn').onclick = e => { e.stopPropagation(); save(); };
$('#rcBig').onclick = e => { e.stopPropagation(); const it = cur(); if (!it || state.tab !== 'biblio') return; state.comp.biblio = it; badge(); state.flash = 'biblio'; setTab('crear'); toast(`«${it.name}» como imagen a recrear`); };
mirror.addEventListener('click', e => { // clic en la imagen grande: si es una creación generada, se abre en el popup (y las flechas siguen por todas)
  if (e.target.closest('button') || state.tab === 'perfil' || state.tab === 'creaciones' || cmp || mirror.classList.contains('queue')) return;
  if (state.shown && (state.tab === 'crear' || state.tab === 'perfil')) { openGal(state.shown); return; }
  const it = cur(); if (!it) return; const src = (state.tab === 'crear' && it.custom) ? ((it._liveBy && it._liveBy[compSig()]) || it._last) : it.live; if (!src) { if (state.tab === 'biblio') lightbox(it.image, it.name); return; }
  const c = TABS.creaciones.items.find(x => !x.pending && x.src === src.split('?')[0]); if (c) { state.sel.creaciones = c; openGal(c); } else lightbox(src, it.name);
});
mirror.addEventListener('click', e => { // en la Fototeca o cuando el espejo enseña una imagen de catálogo: verla en grande
  if (e.target.closest('button') || state.tab === 'perfil' || state.tab === 'creaciones' || cmp || mirror.classList.contains('queue') || mirrorClickable() || state.shown) return;
  const src = layers[front].getAttribute('src'); if (src && !mirror.classList.contains('vidmode')) lightbox(src, cur() ? cur().name : '');
});
function mirrorClickable() { const it = cur(); if (!it || state.tab === 'perfil' || state.tab === 'creaciones') return false; if (state.tab === 'biblio') return true; const src = (state.tab === 'crear' && it.custom) ? (it._liveBy && it._liveBy[compSig()]) : it.live; return !!src; }
$('#vidBtn').onclick = () => { const v = $('#vid'); v.muted = !v.muted; $('#vidBtn').textContent = v.muted ? '🔇 Sonido' : '🔊 Sonido'; };
function aspectPicker(list, val, onchange) { // cuadraditos con la forma real del formato
  const w = el('div', 'aspects'); list.forEach(a => { const [x, y] = a.split(':').map(Number); const b = el('button', 'asp' + (a === val ? ' on' : '')); const r = x / y; const bw = r >= 1 ? 22 : Math.round(22 * r), bh = r >= 1 ? Math.round(22 / r) : 22; b.innerHTML = `<i style="width:${bw}px;height:${bh}px"></i><span>${a}</span>`; b.title = a; b.onclick = () => onchange(a); w.appendChild(b); }); return w; }
function mkSel(opts, val, onchange) { const sl = el('select', 'sel'); opts.forEach(([k, n]) => { const o = document.createElement('option'); o.value = k; o.textContent = n; sl.appendChild(o); }); sl.value = val; sl.onchange = () => onchange(sl.value); return sl; }
function persist(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
// ---- pool de referencias (estilo Higgsfield/Magnific): se añaden y se quitan; cada una lleva su etiqueta @Image1 / @Video1 / @Audio1 para el prompt
state.vpool = state.vpool || []; state.vprompt = state.vprompt || null; state.ipool = state.ipool || []; if (state.showPrompt === undefined) state.showPrompt = true; try { state.nsfw = localStorage.getItem('am_nsfw') === '1'; } catch (e) {}
function poolTags(pool) { pool = pool || state.vpool; const n = { image: 0, video: 0, audio: 0 }; return pool.map(r => { n[r.kind]++; return { r, tag: '@' + (r.kind === 'image' ? 'Image' : r.kind === 'video' ? 'Video' : 'Audio') + n[r.kind] }; }); }
function poolHas(src, pool) { return (pool || state.vpool).some(r => r.src === src); }
function poolAdd(r, quiet, pool) { pool = pool || state.vpool; if (poolHas(r.src, pool)) return; if (pool.length >= 12) { toast('Máximo 12 referencias'); return; } pool.push(r); if (pool === state.vpool) vbadge(); if (!quiet) toast(`${r.name} añadida como referencia`); renderSide(); if (pool === state.ipool) paint(cur(), true); }
function poolRemove(i, pool) { (pool || state.vpool).splice(i, 1); vbadge(); renderSide(); if (pool === state.ipool) paint(cur(), true); }
function poolFromItem(it) { return { id: it.id, kind: 'image', name: it.name, src: it.src, thumb: it.thumb || it.src }; }
function poolAddFiles(files, pool, onlyImages) { [...files].forEach(f => { const kind = f.type.startsWith('image/') ? 'image' : f.type.startsWith('video/') ? 'video' : f.type.startsWith('audio/') ? 'audio' : null; if (!kind || (onlyImages && kind !== 'image')) return; const rd = new FileReader(); rd.onload = () => { const r = { id: 'file-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6), kind, name: f.name.replace(/\.[a-z0-9]+$/i, ''), src: rd.result, thumb: kind === 'image' ? rd.result : null, mime: f.type }; if (kind === 'video') { const v = document.createElement('video'); v.muted = true; v.src = rd.result; v.onloadeddata = () => { try { const c = document.createElement('canvas'); c.width = 160; c.height = Math.round(160 * v.videoHeight / v.videoWidth) || 160; c.getContext('2d').drawImage(v, 0, 0, c.width, c.height); r.thumb = c.toDataURL('image/jpeg', .7); renderSide(); } catch (e) {} }; } poolAdd(r, false, pool); }; rd.readAsDataURL(f); }); }
function poolMode() { const imgs = state.vpool.filter(r => r.kind === 'image'); return (state.vpool.length === 1 && imgs.length === 1) ? 'i2v' : 'r2v'; }
function poolNode(pool, opts) { pool = pool || state.vpool; opts = opts || {};
  const wrap = el('div', 'pool refs' + (opts.small ? ' small' : ''));
  (opts.fixed || []).forEach(f => { const c = el('div', 'pref fx'); c.title = f.name + ' (fija)'; c.innerHTML = `<img src="${f.thumb}" alt="">`; c.appendChild(el('span', 'tag', f.tag)); c.onclick = () => lightbox(f.src, f.name); wrap.appendChild(c); });
  poolTags(pool).forEach(({ r, tag }, i) => { if (opts.offset) tag = '@Image' + (opts.offset + i + 1);
    const c = el('div', 'pref lab'); c.title = r.name;
    c.innerHTML = r.thumb ? `<img src="${r.thumb}" alt="">` : `<div class="ph">${r.kind === 'video' ? '🎬' : '🎵'}</div>`;
    c.appendChild(el('span', 'tag', tag)); const x = el('button', 'x', '✕'); x.title = 'Quitar'; x.onclick = e => { e.stopPropagation(); poolRemove(i, pool); }; c.appendChild(x);
    c.onclick = () => { if (r.kind === 'image') lightbox(r.src, r.name); }; wrap.appendChild(c);
  });
  const add = el('div', 'pref add'); add.innerHTML = '<b>＋</b><span>Añadir</span>'; add.title = 'Imágenes, vídeos o audios de tu ordenador (o arrástralos aquí)';
  const inp = document.createElement('input'); inp.type = 'file'; inp.multiple = true; inp.accept = opts.onlyImages ? 'image/*' : 'image/*,video/*,audio/*'; inp.style.display = 'none'; inp.onchange = () => poolAddFiles(inp.files, pool, opts.onlyImages); add.appendChild(inp); add.onclick = () => inp.click(); wrap.appendChild(add);
  ['dragenter', 'dragover'].forEach(ev => wrap.addEventListener(ev, e => { e.preventDefault(); wrap.classList.add('over'); })); wrap.addEventListener('dragleave', () => wrap.classList.remove('over')); wrap.addEventListener('drop', e => { e.preventDefault(); wrap.classList.remove('over'); poolAddFiles(e.dataTransfer.files, pool, opts.onlyImages); });
  return wrap;
}
function promptWithMenu(ta, box, listFn) { // al escribir «@» sale el menú con las referencias del pool; clic = inserta la etiqueta
  const menu = el('div', 'atmenu'); menu.style.display = 'none'; box.appendChild(menu);
  const close = () => { menu.style.display = 'none'; };
  const place = () => { const r = box.getBoundingClientRect(); const hgt = Math.min(360, innerHeight - 24); Object.assign(menu.style, { position: 'fixed', left: Math.round(r.right + 14) + 'px', right: 'auto', width: '270px', top: Math.round(Math.max(12, Math.min(r.top, innerHeight - hgt - 12))) + 'px', maxHeight: hgt + 'px', marginTop: '0' }); }; // a la derecha, encima del panel de la imagen (como los complementos)
  const open = () => { menu.innerHTML = ''; const tags = listFn ? listFn() : poolTags(); if (!tags.length) { menu.appendChild(el('div', 'it g', 'No hay referencias: añade alguna arriba')); } tags.forEach(({ r, tag }) => { const it = el('div', 'it'); it.innerHTML = (r.thumb ? `<img src="${r.thumb}">` : `<i>${r.kind === 'video' ? '🎬' : '🎵'}</i>`) + `<b>${tag}</b><span>${r.name}</span>`; it.onmousedown = e => { e.preventDefault(); const p = ta.selectionStart; const before = ta.value.slice(0, p).replace(/@[\wáéíóú]*$/i, ''); const after = ta.value.slice(p); ta.value = before + tag + ' ' + after; ta.selectionStart = ta.selectionEnd = before.length + tag.length + 1; ta.dispatchEvent(new Event('input')); close(); ta.focus(); }; menu.appendChild(it); }); menu.style.display = ''; place(); };
  const hl = el('div', 'hlx'); box.insertBefore(hl, ta); ta.classList.add('hlta');
  const paint = () => { const tags = new Set((listFn ? listFn() : poolTags()).map(t => t.tag)); const esc = t => t.replace(/&/g, '&amp;').replace(/</g, '&lt;'); hl.innerHTML = esc(ta.value).replace(/@(Image|Video|Audio)\d+/g, m => `<b class="${tags.has(m) ? 'on' : ''}">${m}</b>`) + '\n'; hl.scrollTop = ta.scrollTop; };
  ta.addEventListener('scroll', () => { hl.scrollTop = ta.scrollTop; }); new ResizeObserver(() => { hl.style.height = ta.offsetHeight + 'px'; }).observe(ta); setTimeout(paint, 0); ta._paint = paint;
  ta.addEventListener('input', () => { paint(); const p = ta.selectionStart; const m = ta.value.slice(0, p).match(/@[\wáéíóú]*$/i); if (m) open(); else close(); });
  ta.addEventListener('blur', () => setTimeout(close, 150)); ta.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
  ta.addEventListener('mouseup', () => { const p = ta.selectionStart; if (ta.selectionEnd !== p) return; const v = ta.value; const re = /@(Image|Video|Audio)\d+/g; let m; while ((m = re.exec(v))) { if (p >= m.index && p <= m.index + m[0].length) { const range = [m.index, m.index + m[0].length]; const old = m[0];
    menu.innerHTML = ''; menu.appendChild(el('div', 'it g', `${old} → elige a qué referencia apunta`)); (listFn ? listFn() : poolTags()).forEach(({ r, tag }) => { const it = el('div', 'it' + (tag === old ? ' cur' : '')); it.innerHTML = (r.thumb ? `<img src="${r.thumb}">` : `<i>${r.kind === 'video' ? '🎬' : '🎵'}</i>`) + `<b>${tag}</b><span>${r.name}</span>`; it.onmousedown = e => { e.preventDefault(); ta.value = v.slice(0, range[0]) + tag + v.slice(range[1]); ta.selectionStart = ta.selectionEnd = range[0] + tag.length; ta.dispatchEvent(new Event('input')); close(); ta.focus(); }; menu.appendChild(it); }); menu.style.display = ''; place(); return; } } close(); });
  const fuera = e => { if (!menu.isConnected) { document.removeEventListener('mousedown', fuera, true); return; } if (menu.style.display !== 'none' && !menu.contains(e.target) && e.target !== ta) close(); }; document.addEventListener('mousedown', fuera, true);

}
C.chars = C.chars || [{ id: 'aria', name: C.perfil.name || 'Aria Cruz', avatar: C.perfil.avatar || C.base.thumb, ficha: C.perfil.ficha }, { id: 'luna', name: 'Luna Vega', avatar: 'assets/perfil/demo_luna.jpg', demo: true }];
document.addEventListener('DOMContentLoaded', () => { const d = document.getElementById('livedot'); if (d) { d.style.cursor = 'pointer'; d.title = 'Tu API: clave y saldo'; d.addEventListener('click', () => openClaves()); } });
function charInfo(id) { // lo que Crear imagen necesita saber de un personaje (Aria o uno de «Mis personajes» con ficha 360)
  const cl = x => (x || '').split('?')[0]; const p = id && id !== 'aria' && window.PJ ? (PJ.list || []).find(x => x.id === id && x.ficha360) : null;
  if (!p) return { id: 'aria', aria: true, name: C.perfil.name || 'Aria Cruz', short: (C.perfil.name || 'Aria').split(' ')[0], avatar: C.perfil.avatar || C.base.thumb, ficha: C.perfil.ficha, cuerpo: C.perfil.cuerpo || '', foto: C.base.photo, gen: 'fem', body: 'slim, slender petite frame, small bust, narrow waist, narrow hips and slim legs', ident: 'same face, green eyes', hair: { color: 'black', style: 'long hair in a high sleek ponytail' } };
  const eyes = window.pjEyes ? pjEyes(p) : '';
  return { id: p.id, name: p.nombre, short: (p.nombre || 'Personaje').split(' ')[0], avatar: p.avatar || p.foto || p.ficha360, ficha: cl(p.ficha360), cuerpo: cl(p.cuerpo), foto: cl(p.foto || p.ficha360), gen: p.genero || 'fem', body: window.pjBody ? pjBody(p) : '', ident: 'same face' + (eyes ? ', ' + eyes + ' eyes' : ''), hair: window.pjHair ? pjHair(p) : { color: '', style: '' } };
}
function CH() { // personaje PRINCIPAL en Crear imagen / Crear vídeo
  if (state.char === undefined) { try { state.char = localStorage.getItem('am_charsel') || 'aria'; } catch (e) { state.char = 'aria'; } }
  return charInfo(state.char);
}
window.CH = CH; window.paint = window.paint || null;
// --- varios personajes en la misma imagen: el principal + los añadidos con «＋». Cada uno con SU prenda, peinado, expresión y complementos; efecto, movie look y cartoon se comparten
const PERCHAR = ['vestidor', 'hair', 'expr']; state.compBy = state.compBy || {};
function extraChars() { if (state.extras === undefined) { try { state.extras = JSON.parse(localStorage.getItem('am_extras') || '[]'); } catch (e) { state.extras = []; } if (!Array.isArray(state.extras)) state.extras = []; }
  const main = CH().id; return state.extras.filter((id, i, a) => id !== main && a.indexOf(id) === i).map(id => charInfo(id)).filter(c => state.extras.includes(c.id) && c.id !== main); }
function allChars() { return [CH()].concat(extraChars()); }
function multiOn() { return extraChars().length > 0; }
function cfocusId() { const ids = allChars().map(c => c.id); if (!ids.includes(state.cfocus)) state.cfocus = ids[0]; return state.cfocus; } // de quién se están eligiendo la ropa, el peinado, la expresión y los complementos
window.cfocusId = cfocusId;
function compFor(id) { return id === CH().id ? state.comp : (state.compBy[id] = state.compBy[id] || {}); }
function setComp(k, it) { const f = state.tab === 'crear' || state.back === 'crear' || true ? cfocusId() : CH().id; if (PERCHAR.includes(k) && f !== CH().id) compFor(f)[k] = it; else state.comp[k] = it; }
function saveExtras() { persist('am_extras', JSON.stringify(state.extras || [])); }
function addExtra(id) { extraChars(); if (id === CH().id || state.extras.includes(id)) return; state.extras.push(id); saveExtras(); state.cfocus = id; badge(); renderSide(); const it = cur(); if (it && state.tab === 'crear') paint(it, true); toast(`${charInfo(id).name} añadido a la imagen: elige su ropa, su peinado y su expresión`); }
function removeExtra(id) { extraChars(); state.extras = state.extras.filter(x => x !== id); delete state.compBy[id]; saveExtras(); state.cfocus = CH().id; const b = state.comp.biblio; if (b && b.people) b.people.forEach(p => { if (p.char === id) p.char = null; }); badge(); renderSide(); const it = cur(); if (it && state.tab === 'crear') paint(it, true); }
function nextMain() { const xs = extraChars(); const own = window.PJ && (PJ.list || []).some(p => p.ficha360); return ((typeof WEBM === 'function' && WEBM() && own) ? xs.filter(c => !c.aria) : xs)[0] || null; }   // quién pasa a principal si se quita al primero (un miembro con personaje propio nunca se queda con Aria de principal)
function removeMain() { const nx = nextMain(); if (!nx) return; const old = CH().id; const mine = state.compBy[nx.id] || {}; PERCHAR.forEach(k => { if (mine[k]) state.comp[k] = mine[k]; else delete state.comp[k]; }); delete state.compBy[nx.id]; state.hairVar = null; state.hairCol = null;
  const b = state.comp.biblio; if (b && b.people) b.people.forEach(p => { if (p.char === old) p.char = null; }); setChar(nx.id, true); toast(`${nx.name} pasa a ser el personaje principal`); }
function charPool() { const c = CH(); if (state.vchar === false) return; state.vpool = state.vpool.filter(r => r.id !== 'ficha360'); state.vpool.unshift({ id: 'ficha360', kind: 'image', name: c.name, src: c.ficha, thumb: c.avatar || c.ficha }); if (typeof vbadge === 'function') vbadge(); }
function setChar(id, quiet) { // cambia el personaje principal: sus fichas, su cuerpo y sus complementos pasan a ser las referencias
  extraChars(); state.char = id || 'aria'; persist('am_charsel', state.char); if (state.extras.includes(state.char)) { state.extras = state.extras.filter(x => x !== state.char); saveExtras(); } const c = CH(); if (window.PJ && !PJ.wiz && PJ.sel !== 'nuevo') PJ.sel = c.id; navSync();   // el Perfil y el círculo del menú van a la par del principal
  state.cfocus = c.id; state.accOn = {}; state.accFor = null; charPool(); badge(); chipSync();
  if (state.ready) { renderSide(); const it = cur(); if (it && (state.tab === 'crear' || state.tab === 'video')) paint(it, true); } if (!quiet) toast(`Ahora creas con ${c.name}`); }
window.setChar = setChar;
window.charsReady = function () { if (!charsReady._s && window.PJ && (PJ.list || []).length) { charsReady._s = true; if (!PJ.wiz && PJ.sel === 'aria' && !CH().aria) PJ.sel = CH().id; } navSync(); if (state.ready && (state.tab === 'crear' || state.tab === 'creaciones')) { try { renderChips(); } catch (e) {} } if ((state.char && state.char !== 'aria' && !CH().aria) || multiOn()) { charPool(); chipSync(); if (state.ready && (state.tab === 'crear' || state.tab === 'video')) { renderSide(); const it = cur(); if (it) paint(it, true); } } }; // los personajes llegan después del primer pintado
const WEBM = () => !!(window.CUENTA && CUENTA.web && !CUENTA.ariaMia);   // miembro de la web: primero SUS personajes; Aria es un personaje fijo (no se edita ni es su principal)
function navAvatar() { const c = CH(); if (!WEBM()) return c.avatar || C.perfil.avatar || C.base.thumb; const L = (window.PJ && PJ.list) || []; const p = L.find(x => x.id === c.id) || L[0]; return p ? (p.avatar || p.foto || p.ficha360 || '') : ''; }   // el círculo de «Perfil» es el personaje principal (en la web, siempre uno del miembro)
function navSync() { const r = document.querySelector('nav .ring'); if (!r) return; const a = navAvatar(); r.innerHTML = a ? `<img src="${a}" alt="">` : '<i class="ringv">👤</i>'; }
function charList() { const aria = [{ id: 'aria', name: C.perfil.name || 'Aria Cruz', avatar: C.perfil.avatar || C.base.thumb, ok: true }], suyos = ((window.PJ && PJ.list) || []).map(p => ({ id: p.id, name: p.nombre, avatar: p.avatar || p.foto || '', ok: !!p.ficha360 })); return WEBM() ? suyos.concat(aria) : aria.concat(suyos); }
document.addEventListener('click', e => { if (!(e.target.closest && e.target.closest('.charsel'))) state.charOpen = null; document.querySelectorAll('.chardd.on').forEach(dd => { if (!dd.parentElement.contains(e.target)) dd.classList.remove('on'); }); });
document.addEventListener('scroll', e => { if (e.target && e.target.tagName === 'ASIDE' && document.querySelector('.chardd.on')) { state.charOpen = null; document.querySelectorAll('.chardd.on').forEach(dd => dd.classList.remove('on')); } }, true);
addEventListener('resize', () => { state.charOpen = null; document.querySelectorAll('.chardd.on').forEach(dd => dd.classList.remove('on')); });
function charSel(tab) { // selector de personaje. En Crear imagen: una burbuja por personaje y UN desplegable (clic en el recuadro o en «＋») donde se marca quién sale en la imagen; si se quita al principal, pasa a serlo el siguiente
  const A = CH(); const crear = tab !== 'video'; const multi = crear && multiOn(); const on = tab === 'video' ? poolHas(A.ficha) : true; const dd = el('div', 'chardd'); let ch;
  const av = c => c.avatar ? `<img src="${c.avatar}" alt="">` : '<span class="pjplus">?</span>';
  const alPerfil = c => { dd.classList.remove('on'); state.charOpen = null; toast(`${c.name} aún no tiene su ficha 360: termínala en el Perfil`); if (window.PJ) { PJ.sel = c.id; PJ.wiz = null; } setTab('perfil'); };
  const fill = mode => { dd.innerHTML = ''; const act = allChars().map(c => c.id);
    if (mode === 'multi') { dd.appendChild(el('div', 'ddh', 'Quién sale en la imagen'));
      charList().forEach(c => { const dentro = act.includes(c.id); const r = el('div', 'it' + (dentro ? ' on' : '') + (c.ok ? '' : ' off'), `${av(c)}<b>${esc(c.name)}</b><small>${!c.ok ? 'le falta su ficha 360' : c.id === A.id ? 'principal' : dentro ? 'en la imagen' : 'añadir'}</small><span class="ck">✓</span>`);
        r.onclick = e => { e.stopPropagation(); if (!c.ok) { alPerfil(c); return; } state.charOpen = tab;
          if (!dentro) addExtra(c.id);
          else if (act.length < 2) toast('Tiene que quedar al menos un personaje: marca antes otro');
          else if (c.id === A.id) { if (nextMain()) removeMain(); else toast('Aria solo puede ir como segundo personaje'); }
          else removeExtra(c.id); }; dd.appendChild(r); }); }
    else charList().filter(c => !(WEBM() && c.id === 'aria' && CH().id !== 'aria')).forEach(c => { const r = el('div', 'it' + (c.id === A.id ? ' on' : '') + (c.ok ? '' : ' off'), `${av(c)}<b>${esc(c.name)}</b><small>${!c.ok ? 'le falta su ficha 360' : c.id === A.id ? 'principal' : 'crear con ' + (c.name || '').split(' ')[0]}</small>`);
      r.onclick = e => { e.stopPropagation(); if (!c.ok) { alPerfil(c); return; } dd.classList.remove('on'); if (c.id !== A.id) setChar(c.id); }; dd.appendChild(r); });
    const nw = el('div', 'it', '<span class="pjplus">＋</span><b>Crear personaje</b><small>en el Perfil</small>'); nw.onclick = e => { e.stopPropagation(); dd.classList.remove('on'); state.charOpen = null; setTab('perfil'); if (window.pjStart) setTimeout(pjStart, 50); }; dd.appendChild(nw); };
  const show = (mode, keep) => { const was = dd.classList.contains('on') && dd._mode === mode; document.querySelectorAll('.chardd.on').forEach(x => x.classList.remove('on')); if (was && !keep) { state.charOpen = null; return; } fill(mode); dd._mode = mode; dd.classList.add('on'); state.charOpen = crear ? tab : null;
    const r = ch.getBoundingClientRect(); dd.style.maxHeight = Math.min(420, innerHeight - 24) + 'px'; const w = dd.offsetWidth || 300;   // a la derecha, encima del panel de la imagen
    dd.style.left = Math.round(Math.max(12, Math.min(r.right + 12, innerWidth - w - 12))) + 'px'; dd.style.top = Math.round(Math.max(12, Math.min(r.top, innerHeight - dd.offsetHeight - 12))) + 'px'; };
  if (multi) { ch = el('div', 'charsel on multi crear'); const row = el('div', 'chb'); const f = cfocusId();
    allChars().forEach((c, i) => { const b = el('span', 'bub' + (c.id === f ? ' on' : ''), `<img src="${c.avatar}" alt="">${(i || nextMain()) ? '<i class="bx" title="Quitar de la imagen">×</i>' : ''}`); b.title = c.name + (c.id === f ? ' · estás eligiendo su ropa, su peinado, su expresión y sus complementos' : ' · clic para elegir lo suyo'); b.onclick = e => { e.stopPropagation(); if (e.target.classList.contains('bx')) { if (i) removeExtra(c.id); else removeMain(); return; } state.cfocus = c.id; renderSide(); }; row.appendChild(b); });
    ch.appendChild(row); const plus = el('span', 'bub add', '＋'); plus.title = 'Elegir quién sale en la imagen'; ch.appendChild(plus); }
  else { ch = el('div', 'charsel' + (on ? ' on' : '') + (crear ? ' crear' : '')); ch.innerHTML = `<img src="${A.avatar}" alt=""><div><b>${esc(A.name)}</b><span class="status">${tab === 'video' ? (on ? 'Su ficha 360 va como referencia' : 'Sin su ficha 360 (clic para volver a ponerla)') : 'Su ficha 360 va siempre como referencia'}</span></div>${tab === 'video' ? `<span class="ck${on ? ' on' : ''}" title="${on ? 'Quitar' : 'Poner'}">✓</span><span class="caret" title="Cambiar de personaje">▾</span>` : '<span class="bub add" title="Elegir quién sale en la imagen">＋</span>'}`;
    if (tab === 'video') ch.querySelector('.ck').onclick = e => { e.stopPropagation(); if (on) { state.vchar = false; const k = state.vpool.findIndex(r => r.src === A.ficha); if (k >= 0) state.vpool.splice(k, 1); vbadge(); renderSide(); } else { state.vchar = true; poolAdd({ id: 'ficha360', kind: 'image', name: A.name, src: A.ficha, thumb: A.avatar }); } }; }
  ch.appendChild(dd); ch.onclick = e => { if (e.target.closest('.chardd')) return; show(crear ? 'multi' : 'switch'); };
  if (crear && state.charOpen === tab) setTimeout(() => { if (state.charOpen === tab && ch.isConnected) show('multi', true); }, 0);   // tras marcar o desmarcar a alguien el desplegable sigue abierto
  return ch;
}
function planMulti() { // varios personajes en la misma imagen: cada uno con su ficha, su ropa, su peinado y su expresión; el estilo es común
  const c = state.comp; const full = c.biblio || null; const nuevo = !!(full && sinLienzo(full)); const bib = full && !nuevo ? full : null;   // nuevo = imagen nueva desde la descripción; bib = se edita la foto
  const R = crearRefs(); const n = key => R.findIndex(r => r.key === key) + 1; const I = key => 'image ' + n(key);
  const scene = nuevo ? sinRefs(deAria(cleanDesc(full.neutro || full.prompt || ''))).replace(/[.\s]+$/, '') : '';
  const fig = (nuevo && full.figura && !/^\W*real\b/i.test(full.figura)) ? full.figura.replace(/[.\s]+$/, '').replace(/^an?\s+/i, '') : '';
  const L = allChars(); const main = L[0]; const noun = x => x.gen === 'masc' ? 'man' : x.gen === 'fem' ? 'woman' : 'person';
  const fk = x => x.id === main.id ? 'ficha' : 'ficha:' + x.id; const ck = (x, k) => x.id === main.id ? k : k + ':' + x.id; const cmp = x => x.id === main.id ? c : (state.compBy[x.id] || {});
  const ident = x => [x.ident].concat((window.accOnFor ? accOnFor(x.id) : []).filter(a => a.desc && a.tipo !== 'movil').map(a => a.desc)).join(', ');
  const ppl = (full && full.people) || []; const ord = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth'];
  const where = (x, i) => { const p = ppl.find(q => q.char === x.id); return p ? p.desc : `the ${ord[i] || 'next'} person from the left`; };
  const base = bib ? `Edit ${I('canvas')}. Keep its scene, background, camera framing, poses, lighting and composition exactly as they are. Change ONLY who these people are: ${L.map((x, i) => `${where(x, i)} must become ${x.name}, the ${noun(x)} of ${I(fk(x))} (character sheet): ${ident(x)}`).join('; ')}. Anyone else in the image stays exactly as they are. This is a FULL BODY swap, not a face swap: each replaced person is redrawn from head to toe as the character, with the build, height, skin, shoulders, chest, waist, hips, arms, hands, legs and feet of their own character sheet and the clothes refitted to that body; from the original person keep only the pose, the action and the place in the frame${L.map((x, i) => { const d = where(x, i); const h = /\b(man|boy|guy|gentleman|male|father|husband|mestre|master)\b/i.test(d), w = /\b(woman|girl|lady|female|mother|wife)\b/i.test(d); return (noun(x) === 'woman' && h && !w) ? `. ${x.name} replaces a man: that figure becomes a WOMAN, with ${x.name}'s own female body from ${I(fk(x))}; nothing of the man's body, arms, hands, legs or feet remains` : (noun(x) === 'man' && w && !h) ? `. ${x.name} replaces a woman: that figure becomes a MAN, with ${x.name}'s own male body from ${I(fk(x))}; nothing of the woman's body remains` : ''; }).join('')}`
    : nuevo ? `Create ONE new ${fig ? 'image' : 'photograph'} of this scene: ${scene}.${full.drop && full.ropa ? ' Clothing seen in the scene: ' + full.ropa.replace(/[.\s]+$/, '') + '.' : ''} The people in it are these characters: ${L.map((x, i) => `${x.name} takes the place of ${where(x, i)}: ${x.name} is the ${noun(x)} of ${I(fk(x))} (character sheet): ${ident(x)}`).join('; ')}. Each character keeps the gender, body, face and hair of their own character sheet, even where the scene describes that person differently (a woman stays a woman in a man's place, and the other way round); only the place, the pose, the action and the framing come from the scene. Anyone else described in the scene stays as described${fig ? `. Every figure is a ${fig}: each character appears as a ${fig} version of themselves, never a photorealistic human` : ''}`
    : `Create ONE photograph of ${L.length} people together, side by side, natural relaxed poses, plain white studio backdrop, soft even lighting: ${L.map(x => `${x.name} is the ${noun(x)} of ${I(fk(x))} (character sheet): ${ident(x)}`).join('; ')}`;
  const parts = [];
  L.forEach(x => { const m = cmp(x);
    if (m.vestidor && n(ck(x, 'vestidor'))) parts.push(`${x.name} wears EXACTLY the outfit and shoes of ${I(ck(x, 'vestidor'))} (${m.vestidor.name}), every piece, same colors and fabrics; the person shown in that image is only a mannequin for the outfit`);
    else if (nuevo && !x.aria) parts.push(`${x.name} is dressed for the scene as the scene describes; the underwear or swimwear shown in their character sheet is ONLY a body reference and never their outfit, unless the scene itself is a beach or pool scene`);
    else if (!bib && !x.aria) parts.push(`${x.name} is fully dressed in simple everyday clothes (a plain fitted top and jeans); never the underwear or swimwear shown in their character sheet, which is only a body reference`);   // sin prenda elegida y sin foto de partida: su ficha suele enseñarla en ropa interior
    if (m.hair && n(ck(x, 'hair'))) parts.push(`${x.name}'s hairstyle is exactly the hairstyle of ${I(ck(x, 'hair'))}: ${m.hair.desc || m.hair.name}; the person in that image is only a model for the hairstyle, ${x.name} keeps their own hair color`);
    else if (m.hair) { const hh = x.hair || {}; parts.push(`${x.name}'s hairstyle is this one: ${(m.hair.desc || m.hair.name).replace(/\.$/, '')}${hh.color ? `; ${x.name} keeps their own hair color (${hh.color})` : ''}`); }   // sin imagen de referencia: el peinado va en palabras
    else if (full && !full.double && (!x.aria || full.drop)) { const hh = x.hair || {}; parts.push(`${x.name} keeps their own hair, exactly as in ${I(fk(x))}${hh.color ? ': ' + hh.color + ' hair' : ''}${hh.style ? ', ' + hh.style.replace(/\.$/, '') : ''} (same color, length and cut), not the hair ${bib ? 'of the person they replace' : 'described in the scene'}`); }   // sin peinado elegido: manda el pelo de su ficha, no el de la foto
    if (m.expr && n(ck(x, 'expr'))) parts.push(`${x.name}'s facial expression and gesture are exactly those of ${I(ck(x, 'expr'))}: ${m.expr.name}; the person in that image only shows the expression`);
    else if (m.expr) parts.push(`${x.name}'s facial expression and gesture: ${(m.expr.desc || m.expr.name).replace(/\.$/, '')} (${m.expr.name})`); });
  if (c.cartoon) parts.push(`render the whole image in this art style: ${deAria(c.cartoon.desc || c.cartoon.name)}`);
  if (c.photo) parts.push(`photographic style: ${c.photo.desc || c.photo.name}`);
  if (c.movie) parts.push(`cinematic color grading and look of ${c.movie.name}${c.movie.desc ? ': ' + c.movie.desc : ''}`);
  R.filter(r => r.key.startsWith('pool:')).forEach(r => parts.push(`use ${I(r.key)} (${r.name}) as a reference where the prompt mentions @Image${n(r.key)}`));
  parts.push('each person keeps their own identity: never mix their faces, hair or accessories with each other or with the people shown in the outfit, hairstyle or expression references');
  return { multi: true, images: R.map(r => r.img), aspect: '3:4', prompt: `${base}. ${parts.map(x => x[0].toUpperCase() + x.slice(1)).join('. ')}. ${(c.cartoon || fig) ? 'No text, no logos.' : 'Photoreal, no text, no logos.'}` };
}
// --- «¿Quién es quién?»: en una foto con varias personas, se elige qué personaje sustituye a cada una
const PCOL = ['#2ecc71', '#e74c3c', '#3498db', '#f1c40f', '#9b59b6', '#e67e22'];
function pplCache(key, val) { // personas ya detectadas en cada imagen (cajas y frases): la misma foto no se vuelve a leer
  if (!key || key.startsWith('data:')) return null; let m = {}; try { m = JSON.parse(localStorage.getItem('am_ppl') || '{}') || {}; } catch (e) {}
  if (val === undefined) return Array.isArray(m[key]) ? m[key] : null;
  delete m[key]; m[key] = val.map(p => ({ box: p.box, desc: p.desc, es: p.es || '' })); const ks = Object.keys(m); while (ks.length > 80) delete m[ks.shift()];
  try { localStorage.setItem('am_ppl', JSON.stringify(m)); } catch (e) {} return val; }
function pplHuella(d) { let h = 5381; const n = d.length; const st = Math.max(1, Math.floor(n / 4000)); for (let i = 0; i < n; i += st) h = ((h << 5) + h + d.charCodeAt(i)) | 0; return 'foto:' + n + ':' + (h >>> 0).toString(36); }   // huella de una foto arrastrada (no tiene ruta)
function pplGrande(L) { // fuera las personas diminutas del fondo (las asignadas o marcadas a mano se quedan)
  const ar = p => (p.box[2] - p.box[0]) * (p.box[3] - p.box[1]); const mx = Math.max(0, ...L.map(ar)); return L.filter(p => p.char || p.manual || (ar(p) >= 0.012 && ar(p) >= mx * 0.06)); }
function pplLugar(x, y) { // frase de reserva para una persona marcada a mano: dónde está
  const h = x < .2 ? ['on the far left', 'a la izquierda del todo'] : x < .4 ? ['on the left', 'a la izquierda'] : x < .6 ? ['in the center', 'en el centro'] : x < .8 ? ['on the right', 'a la derecha'] : ['on the far right', 'a la derecha del todo'];
  const v = y < .33 ? ['in the upper part of the image', 'en la parte de arriba'] : y < .66 ? ['at mid height', 'a media altura'] : ['in the lower part of the image', 'en la parte de abajo'];
  return { desc: `the person ${h[0]}, ${v[0]}`, es: `la persona ${h[1]}, ${v[1]}` }; }
async function openPeople(bib) {
  let m0 = $('#pplm'); if (m0) m0.remove(); m0 = el('div', 'fxm'); m0.id = 'pplm'; document.body.appendChild(m0); m0.onclick = e => { if (e.target === m0 && !m0._drag) m0.remove(); };
  const box = el('div', 'pplbox'); m0.appendChild(box); const key = bib.image.startsWith('data:') ? pplHuella(bib.image) : bib.image.split('?')[0];
  const imgBody = () => bib.image.startsWith('data:') ? { data: bib.image } : { path: bib.image.split('?')[0] };
  const cands = () => charList().filter(c => c.ok);
  const pal = t => String(t || '').toLowerCase().replace(/[^a-z ]/g, ' ').split(/\s+/).filter(w => w.length > 2);
  const hereda = (N, V) => { V.filter(o => o.char).forEach(o => { const a = pal(o.desc); let best = null, bs = 0; N.forEach(p => { if (p.char) return; const b = pal(p.desc); const sc = a.filter(w => b.includes(w)).length / Math.max(1, Math.min(a.length, b.length)); if (sc > bs) { bs = sc; best = p; } }); if (best && bs >= 0.5) best.char = o.char; }); return N; };   // las personas vuelven a tener el personaje que se les dio (se emparejan por su frase)
  let P = (bib.people || []).map(p => Object.assign({}, p)); let viejo = []; if (P.some(p => !p.box)) { viejo = P; P = []; }   // un reparto sin cajas viene de una creación antigua
  const pon = L => { P = pplGrande(hereda(L.map(p => ({ box: p.box, desc: p.desc, es: p.es || '', char: null })), viejo)); if (!viejo.length && P.length === 1 && !P[0].char) P[0].char = CH().id; viejo = []; };
  if (!P.length) { const c = bib._ppl || pplCache(key); if (c && c.length) pon(c); }   // esta foto ya se leyó: no se vuelve a leer
  let busy = !P.length ? performance.now() : 0; let err = ''; let pick = false;
  const libre = () => allChars().map(c => c.id).find(id => !P.some(p => p.char === id)) || null;
  let cs = libre() || CH().id;   // el personaje que se está colocando
  const auto = () => { const free = P.filter(p => !p.char); const act = allChars().map(c => c.id); const pool = (act.length > 1 ? act : []).filter(id => !P.some(p => p.char === id)); if (free.length === 1 && pool.length === 1) free[0].char = pool[0]; };   // con dos personas y dos personajes, al asignar una la otra se asigna sola
  const asigna = i => { const p = P[i]; if (p.char === cs) p.char = null; else { P.forEach(q => { if (q.char === cs) q.char = null; }); p.char = cs; auto(); const nx = libre(); if (nx) cs = nx; } draw(); };
  const marca = async (x, y, caja) => { pick = false; const hit = caja ? -1 : P.findIndex(p => x >= p.box[0] && x <= p.box[2] && y >= p.box[1] && y <= p.box[3]); if (hit >= 0) { if (P[hit].char === cs) draw(); else asigna(hit); return; }   // ya estaba detectada
    const cl = v => Math.round(Math.max(0, Math.min(1, v)) * 1e4) / 1e4; const ph = pplLugar(x, y); const np = { box: caja ? caja.map(cl) : [cl(x - .07), cl(y - .12), cl(x + .07), cl(y + .22)], desc: ph.desc, es: ph.es, manual: true, char: null, _lee: true };
    P.push(np); asigna(P.length - 1);
    let r = null; try { r = await fetch('/api/personas_img', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: imgBody(), punto: [cl(x), cl(y)] }) }).then(q => q.json()); } catch (e) {}
    const q = r && r.ok && (r.person || (r.people || []).find(p => x >= p.box[0] && x <= p.box[2] && y >= p.box[1] && y <= p.box[3]));   // la IA describe a esa persona; si no puede, vale la frase de dónde está
    delete np._lee; if (q && q.desc) { if (!caja) np.box = q.box; np.desc = q.desc; np.es = q.es || np.es; } if (m0.isConnected) draw(); };
  function draw() { box.innerHTML = '';
    const Lf = el('div', 'pplimg'); const wrap = el('div', 'pplwrap' + (pick ? ' pick' : '')); const im = el('img'); im.src = bib.image; wrap.appendChild(im);
    P.forEach((p, i) => { const b = el('div', 'pplbx' + (p.char === cs ? ' on' : ''), `<i>${i + 1}</i>${p.char ? `<img src="${charInfo(p.char).avatar}" alt="">` : ''}`); const [x0, y0, x1, y1] = p.box; Object.assign(b.style, { left: x0 * 100 + '%', top: y0 * 100 + '%', width: (x1 - x0) * 100 + '%', height: (y1 - y0) * 100 + '%' }); b.style.setProperty('--c', PCOL[i % 6]); b.title = p.es || p.desc; b.onclick = e => { e.stopPropagation(); asigna(i); }; wrap.appendChild(b); });
    if (pick) { wrap.appendChild(el('div', 'pplhint', 'Haz clic sobre la persona o dibuja su recuadro arrastrando'));
      const pos = e => { const r = im.getBoundingClientRect(); return [Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)), Math.max(0, Math.min(1, (e.clientY - r.top) / r.height))]; };
      wrap.onmousedown = e => { if (e.button) return; e.preventDefault(); const s0 = pos(e); const rb = el('div', 'pplrb'); wrap.appendChild(rb); m0._drag = true;
        const mv = ev => { const p = pos(ev); Object.assign(rb.style, { left: Math.min(s0[0], p[0]) * 100 + '%', top: Math.min(s0[1], p[1]) * 100 + '%', width: Math.abs(p[0] - s0[0]) * 100 + '%', height: Math.abs(p[1] - s0[1]) * 100 + '%' }); };
        const up = ev => { document.removeEventListener('mousemove', mv); document.removeEventListener('mouseup', up); setTimeout(() => { m0._drag = false; }, 60); const p = pos(ev);
          if (Math.abs(p[0] - s0[0]) > 0.03 && Math.abs(p[1] - s0[1]) > 0.03) marca((s0[0] + p[0]) / 2, (s0[1] + p[1]) / 2, [Math.min(s0[0], p[0]), Math.min(s0[1], p[1]), Math.max(s0[0], p[0]), Math.max(s0[1], p[1])]); else marca(p[0], p[1]); };   // recuadro dibujado o un simple clic
        document.addEventListener('mousemove', mv); document.addEventListener('mouseup', up); }; }
    if (busy) wrap.appendChild(el('div', 'pplbusy', `<b>Preparando la imagen</b><small>buscando a las personas · unos segundos</small><div class="pplbar"><i style="animation-delay:-${((performance.now() - busy) / 1000).toFixed(1)}s"></i></div>`)); Lf.appendChild(wrap); box.appendChild(Lf);
    const Rg = el('div', 'pplside'); Rg.appendChild(el('h3', '', '¿Quién es quién?')); Rg.appendChild(el('p', '', 'Elige un personaje y pulsa a quién sustituye, en la lista o en la imagen. Las personas que dejes «sin cambiar» se quedan como están.'));
    if (err) Rg.appendChild(el('div', 'claveserr', esc(err)));
    Rg.appendChild(el('small', 'pjk', 'Tus personajes')); const g = el('div', 'pplchars');
    cands().forEach(c => { const n = P.findIndex(p => p.char === c.id); const b = el('button', 'pplch' + (cs === c.id ? ' on' : ''), `<img src="${c.avatar}" alt="">${n >= 0 ? `<i style="background:${PCOL[n % 6]}">${n + 1}</i>` : ''}<b>${esc((c.name || '').split(' ')[0])}</b>`); b.title = c.name + (n >= 0 ? ' · sustituye a la persona ' + (n + 1) : ' · sin colocar'); b.onclick = () => { cs = c.id; draw(); }; g.appendChild(b); }); Rg.appendChild(g);
    if (!busy) { const cn0 = cands().find(c => c.id === cs); Rg.appendChild(el('small', 'pjk', `${esc(cn0 ? (cn0.name || '').split(' ')[0] : 'El personaje')} sustituye a`));
      P.forEach((p, i) => { const c = p.char && charInfo(p.char); const row = el('button', 'pplrow' + (p.char === cs ? ' on' : ''), `<i style="background:${PCOL[i % 6]}">${i + 1}</i><span>${p._lee ? 'Leyendo a esa persona…' : esc(p.es || p.desc)}</span>${c ? `<img src="${c.avatar}" alt="" title="${esc(c.name)}"><u title="Dejar sin cambiar">×</u>` : '<em>sin cambiar</em>'}`); row.onclick = e => { if (e.target.tagName === 'U') { p.char = null; draw(); return; } asigna(i); }; Rg.appendChild(row); });
      const ot = el('button', 'pplrow add' + (pick ? ' on' : ''), `<i>＋</i><span>${pick ? 'Haz clic sobre esa persona o dibuja su recuadro…' : 'Otra persona: márcala en la imagen'}</span>`); ot.title = 'Si la persona que quieres sustituir no está en la lista, márcala tú con un clic'; ot.onclick = () => { pick = !pick; draw(); }; Rg.appendChild(ot); }
    const a = el('div', 'pjacts'); const ok = el('button', 'btn acc big', '✓ Usar este reparto'); ok.disabled = !!busy || !P.some(p => p.char);
    ok.onclick = () => { bib.people = P; const ids = P.filter(p => p.char).map(p => p.char); const main = ids.includes(CH().id) ? CH().id : ids[0]; extraChars(); state.extras = ids.filter(id => id !== main); saveExtras(); if (main !== CH().id) setChar(main, true); state.cfocus = main; m0.remove(); badge(); renderSide(); const it = cur(); if (it) window.paint(it, true); toast(ids.length > 1 ? `${ids.length} personajes repartidos en la imagen` : 'Reparto guardado'); };
    const cn = el('button', 'btn', 'Cancelar'); cn.onclick = () => m0.remove(); a.appendChild(ok); a.appendChild(cn); Rg.appendChild(a); box.appendChild(Rg); }
  draw(); if (!busy) return;
  let r; try { r = await fetch('/api/personas_img', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: imgBody() }) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
  busy = 0; if (r && r.ok && r.people.length) { bib._ppl = r.people; pplCache(key, r.people); pon(r.people); cs = libre() || CH().id; } else err = r && r.ok ? 'No he encontrado personas en esta imagen: márcalas tú con «Otra persona».' : 'No se ha podido leer la imagen: ' + (r ? r.error : 'sin respuesta');
  if (m0.isConnected) draw();
}
function vTray() { // Crear vídeo: Prenda · Movie look · Cartoon → van al pool de referencias (id 'tab:id', como addToVideo)
  const t = el('div', 'tray vtray'); ['vestidor', 'movie', 'cartoon'].forEach(k => { const r = state.vpool.find(x => String(x.id).startsWith(k + ':')); const src = r ? (TABS[k].items || []).find(i => k + ':' + i.id === r.id) : null; const sample = TABS[k] && TABS[k].items.find(x => !x.group && !x.custom);
    const d = el('div', 'ing' + (k === 'vestidor' ? ' tall' : '') + (r ? ' on' : ' empty'), r ? `<span class="x" title="Quitar">×</span><img src="${r.thumb || (src && compThumb(k, src)) || ''}" alt=""><small>${COMP[k]}</small><b>${r.name}</b>` : `<img src="${sample ? compThumb(k, sample) : ''}" alt=""><small>${COMP[k]}</small><b>ninguno</b>`);
    d.title = r ? 'Cambiar' : 'Elegir'; d.onclick = e => { if (e.target.classList.contains('x')) { const i = state.vpool.indexOf(r); if (i >= 0) state.vpool.splice(i, 1); vbadge(); renderSide(); return; } state.back = 'video'; setTab(k); if (src) { const v = view(); if (v.includes(src)) select(src, false, true); } }; t.appendChild(d); });
  return t;
}
function videoControls(it) {
  const box = el('div', 'stack');
  const mode = poolMode(); const ep = VIDEO_EP[mode];
  if (state.vchar !== false && !poolHas(CH().ficha)) charPool();
  box.appendChild(charSel('video'));
  box.appendChild(vTray());
  box.appendChild(lab('Referencias · ' + state.vpool.length)); box.appendChild(poolNode());
  const quick = el('div', 'row');
  const qc = el('button', 'btn sm', '🗑 Vaciar'); qc.disabled = !state.vpool.length; qc.onclick = () => { state.vpool = []; renderSide(); }; quick.appendChild(qc); box.appendChild(quick);

  const w0 = el('div'); w0.appendChild(lab('Proveedor')); w0.appendChild(mkSel([['hf', 'Higgsfield · Seedance 2.0 (por tokens)'], ['ws', WS ? 'WaveSpeed · Seedance 2.0 (0,24 $/s a 720p)' : 'WaveSpeed · conecta tu clave en «Tus APIs»'], ['ark', ARK ? 'ByteDance directo · BytePlus (más barato; rechaza fotos realistas de personas)' : 'ByteDance directo · conecta tu clave en «Tus APIs»']], state.vprov, v => { state.vprov = v; persist('am_vprov', v); if (v === 'ark' && state.vres === '4k' && state.vmodel === '2.5') { state.vres = '1080p'; persist('am_vres', '1080p'); } renderSide(); })); box.appendChild(w0);
  if (vprov() === 'ark') { const wm = el('div'); wm.appendChild(lab('Modelo')); wm.appendChild(mkSel([['2.0', 'Seedance 2.0 · 4-15 s · hasta 4K'], ['2.5', 'Seedance 2.5 · 4-30 s · hasta 1080p']], state.vmodel, v => { state.vmodel = v; persist('am_vmodel', v); if (v === '2.5' && state.vres === '4k') { state.vres = '1080p'; persist('am_vres', '1080p'); } if (v === '2.0' && state.vdur > 15) { state.vdur = 15; persist('am_vdur', '15'); } renderSide(); })); box.appendChild(wm); }
  const row = el('div', 'ctl');
  const w2 = el('div'); w2.appendChild(lab('Duración')); w2.appendChild(mkSel(Array.from({ length: (vprov() === 'ark' && state.vmodel === '2.5') ? 27 : 12 }, (_, i) => [String(i + 4), (i + 4) + ' s']), String(state.vdur), v => { state.vdur = +v; persist('am_vdur', v); renderSide(); })); row.appendChild(w2);
  const w3 = el('div'); w3.appendChild(lab('Resolución')); w3.appendChild(mkSel([['480p', '480p'], ['720p', '720p · la de Max'], ['1080p', '1080p']].concat((vprov() === 'ark' && state.vmodel === '2.5') ? [] : [['4k', '4K']]), state.vres, v => { state.vres = v; persist('am_vres', v); renderSide(); })); row.appendChild(w3);
  box.appendChild(row);
  const first = state.vpool.find(r => r.kind === 'image'); const ar = mode === 'r2v' ? state.vaspect : (first && first.id === (it && it.id) && it._ar ? nearestAspect(it._ar) : state.vaspect);
  if (mode === 'r2v') { const w4 = el('div'); w4.appendChild(lab('Formato')); w4.appendChild(aspectPicker(V_ASPECTS, state.vaspect, v => { state.vaspect = v; persist('am_vaspect', v); renderSide(); })); box.appendChild(w4); }
  else box.appendChild(el('div', 'status', `Formato: el de la imagen (≈ ${ar}).`));
  const ck = el('label', 'chk'); ck.innerHTML = `<input type="checkbox" ${state.vaudio ? 'checked' : ''}> Generar audio (Seedance inventa voz/ambiente)`; ck.querySelector('input').onchange = e => { state.vaudio = e.target.checked; persist('am_vaudio', state.vaudio ? '1' : '0'); }; box.appendChild(ck);
  const plan = defaultMotionPrompt(it); const pl = el('div', 'lblrow'); pl.appendChild(lab('Prompt de movimiento')); const rst = el('span', 'lnk', '↺ original'); rst.style.display = state.vprompt ? '' : 'none'; pl.appendChild(rst); box.appendChild(pl);
  const pw = el('div', 'pw'); const ta = el('textarea', 'prompt'); ta.value = state.vprompt || plan; ta.spellcheck = false; ta.oninput = () => { state.vprompt = ta.value.trim() === plan.trim() ? null : ta.value; rst.style.display = state.vprompt ? '' : 'none'; }; rst.onclick = () => { state.vprompt = null; ta.value = plan; rst.style.display = 'none'; }; pw.appendChild(ta); promptWithMenu(ta, pw); box.appendChild(pw);
  const est = videoUsd(state.vdur, state.vres, ar);
  box.appendChild(el('div', 'est', vprov() === 'ark' ? `Coste estimado <b>${fmtUsd(est.usd)}</b> · ${state.vdur} s × ${est.rate.toFixed(2)} $/s a ${state.vres} · Seedance ${state.vmodel} · se cobra del saldo de BytePlus.` : vprov() === 'ws' ? `Coste estimado <b>${fmtUsd(est.usd)}</b> · ${state.vdur} s × ${est.rate.toFixed(2)} $/s a ${state.vres} · Seedance 2.0 · se cobra del saldo de WaveSpeed (el coste real queda en la ficha).` : `Coste estimado <b>${fmtUsd(est.usd)}</b> · ${est.tokens.toLocaleString('es-ES')} tokens de vídeo · ${state.vdur} s · ${est.w}×${est.h} · fórmula oficial (0,014 $ / 1000 tokens${state.vres === '4k' ? ', 4K 0,008 $' : ''}). Se cobra del monedero de la API.`));
  const jbv = it && jobFor(it); if (jbv) { const cb = el('button', 'btn w', `⏳ Generándose · ${Math.round((performance.now() - jbv.t0) / 1000)} s · cancelar`); cb.onclick = () => cancelJob(jbv, 'cancelada por ti'); box.appendChild(cb); }
  const b = el('button', 'btn w acc', `🎬 ${it && it.video ? 'Generar nuevo' : 'Generar vídeo'} · ≈${fmtUsd(est.usd)}`); b.disabled = !LIVE || !!jbv || !state.vpool.length; b.title = LIVE ? 'Lanza la petición real (tarda 1-4 min)' : 'Conecta primero tu API'; b.onclick = () => videoGenerate(it); box.appendChild(b);
  if (!LIVE) box.appendChild(el('div', 'status', 'Para generar vídeo, conecta primero tu API.'));
  if (state.vplay) { const d = el('button', 'btn w', '⬇ Descargar el vídeo que se ve'); d.onclick = () => { const a = document.createElement('a'); a.href = state.vplay.src; a.download = state.vplay.src.split('/').pop(); document.body.appendChild(a); a.click(); a.remove(); }; box.appendChild(d); }
  return sec('', box);
}
async function videoGenerate(it) {
  if (!LIVE || !state.vpool.length) return; const mode = poolMode(); const ep = VIDEO_EP[mode]; const first = state.vpool.find(r => r.kind === 'image');
  const ar = mode === 'r2v' ? state.vaspect : (first && first.id === (it && it.id) && it._ar ? nearestAspect(it._ar) : state.vaspect); const est = videoUsd(state.vdur, state.vres, ar); const prompt = state.vprompt || defaultMotionPrompt(it);
  if (it && jobFor(it)) { toast('Ya se está generando un vídeo de esta imagen'); return null; } if (it) it._err = null;
  const toRef = r => Object.assign({ kind: r.kind }, r.src.startsWith('data:') ? { data: r.src } : { path: r.src }); const tags = poolTags();
  const body = { item: (first || state.vpool[0]).id, mode, provider: vprov(), vmodel: state.vmodel, prompt, image: first ? toRef(first) : null, refs: state.vpool.map(toRef), duration: state.vdur, resolution: state.vres, aspect: ar, audio: state.vaudio, usd: +est.usd.toFixed(4), meta: { name: 'Vídeo · ' + (first ? first.name : state.vpool[0].name), tab: 'video', comp: Object.fromEntries(tags.map(t => [t.tag, t.r.name])), model: vmodelName() + (mode === 'r2v' ? ' · con referencias' : ' · imagen → vídeo'), provider: vprov(), ep: vprov() === 'ark' ? 'byteplus/contents/generations/tasks' : vprov() === 'ws' ? 'wavespeed/bytedance/seedance-2.0' : ep, duration: state.vdur, resolution: state.vres, aspect: ar, audio: state.vaudio, prompt, refs: tags.map(t => t.tag + ' ' + t.r.name), usd_est: +est.usd.toFixed(4), tokens: est.tokens, source: first ? first.src : '' } };
  log(`<span class="m">POST</span> ${vprov() === 'ark' ? 'https://ark.ap-southeast.bytepluses.com/<span class="u">api/v3/contents/generations/tasks</span>' : vprov() === 'ws' ? 'https://api.wavespeed.ai/<span class="u">api/v3/bytedance/seedance-2.0/' + (mode === 'r2v' ? 'text-to-video' : 'image-to-video') + '</span>' : 'https://api.higgsfield.ai/<span class="u">' + ep + '</span>'} <span class="g">· ${state.vpool.length} referencia(s) · ${state.vdur} s · ${state.vres} · estimación ${fmtUsd(est.usd)}</span>`);
  let r; try { r = await fetch('/api/video', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
  if (!r || r.error) { const msg = r ? r.error : 'sin respuesta del servidor'; log(`<span class="pr">      ✕ ${msg}</span>`); if (it) { it._err = msg; if (cur() === it) { paint(it, true); renderSide(); } } toast('No se ha podido generar el vídeo'); return null; }
  log(`<span class="q">      ← 202 queued</span>   request_id: ${r.request_id} <span class="g">· sigue generándose en segundo plano</span>`);
  const job = { rid: r.request_id, it: it || state.sel.video, tab: 'video', m: { name: 'Seedance 2.0', ep }, kind: 'video', meta: body.meta, t0: performance.now(), status: 'queued', usd: est.usd }; JOBS.set(job.rid, job);
  if (it && cur() === it) { paint(it, true); renderSide(); } renderRail(); buildCreations(); ensurePoller(); rail.scrollTop = 0; setTimeout(() => { rail.scrollTop = 0; }, 350); return job;
}
const PRENDA_PROMPT = `the girl from @Image1 , adult woman, feminine skinny/slim physique (slender frame, model-like proportions, subtle natural curves), slim legs (not muscular), slightly rounded hips, (trained look, not exaggerated), same identity and body proportions, wearing the exact outfit from @Image2 (same garments, colors, fabrics, fit and styling, no changes). Create ONE single composite image with 4 panels (4 images in 1), square 1:1.

REAL STUDIO PHOTO REQUIREMENT:
This must look like a real studio fashion e-commerce photo shot with a real camera and real lights (photographic realism). Natural, realistic fabric weave, true-to-life shadows and highlights. Absolutely NOT CGI, NOT 3D render, NOT illustration, NOT plastic skin.

BACKGROUND & LIGHT:
Neutral medium gray seamless studio background in every panel, consistent 3-point lighting (key + fill + subtle rim light) to reveal garment contours, seams and fabric texture, even exposure.

CRITICAL CROPPING (NO FACE):
No face visible in any panel. Crop at the base of the neck / collarbone (head fully out of frame).

LAYOUT (clean grid, thin dividers, no labels):

- LEFT panel (about 60% width): FRONT view, neck-down framing down to the shoes (shoes visible), close (body fills ~90% height), arms slightly away from torso to show silhouette.
- RIGHT column (about 40% width) with THREE stacked panels:
    1. TOP RIGHT: LATERAL side view (profile), crop from just ABOVE the knees up to the collarbone (no shoes, no feet).
    2. MIDDLE RIGHT: BACK view, crop from just ABOVE the knees up to the collarbone (no shoes, no feet).
    3. BOTTOM RIGHT: Footwear (if needed) detail close-up (both visible), sharp macro clarity showing materials, stitching, edges, straps/laces, and sole edge; clean studio light, no motion blur.

QUALITY:
Photorealistic, crisp focus, accurate fabric drape, visible weave and stitching, realistic proportions, 4K, no text, no watermark, no logos.

Negative: muscular legs, thick thighs, exaggerated hips, extreme hourglass, oversexualized pose, face visible, head in frame, CGI, 3D render, illustration, doll/plastic skin, over-smoothing, beauty filter, wrong outfit, changed colors, different shoes, missing pieces, extra accessories, logos, text, watermark, distorted anatomy, warped limbs, blurry, low-res textures.`;
function prendaDrop() { // Vestidor: arrastra la foto de una prenda (de internet o del ordenador) → se genera su ficha de 4 vistas y entra en la colección
  const m = curModel(); const d = el('div', 'bibrow bibdrop'); d.classList.add('oneline'); d.innerHTML = `<span class="dzi">＋</span><div><b>Añadir una prenda: arrastra su foto aquí</b><span class="status">Ficha cuadrada de 4 vistas con ${m.name} · ≈${fmtUsd(m.usd.high)} · o clic</span></div>`;
  const use = async files => { const L = [...files].filter(f => f && f.type.startsWith('image/')); if (!L.length) return; const datas = await Promise.all(L.map(f => new Promise(res => { const rd = new FileReader(); rd.onload = () => res(rd.result); rd.readAsDataURL(f); }))); askPrendaTagsBatch(datas); };
  ['dragenter', 'dragover'].forEach(ev => d.addEventListener(ev, e => { e.preventDefault(); d.classList.add('over'); })); ['dragleave', 'drop'].forEach(ev => d.addEventListener(ev, e => { e.preventDefault(); d.classList.remove('over'); }));
  d.addEventListener('drop', async e => { const dt = e.dataTransfer; if (dt.files && dt.files.length) return use(dt.files); let url = dt.getData('text/uri-list') || dt.getData('text/plain') || ''; const mm = (dt.getData('text/html') || '').match(/<img[^>]+src=["']([^"']+)["']/i); if (mm) url = mm[1]; if (!/^https?:\/\//i.test(url)) return; toast('Descargando la imagen…'); try { const j = await fetch('/api/fetch?url=' + encodeURIComponent(url)).then(r => r.json()); if (j.error) throw new Error(j.error); askPrendaTagsBatch([j.data]); } catch (err) { toast('No se pudo descargar: guárdala y arrástrala desde el ordenador'); } });
  d.onclick = () => { const inp = $('#file'); inp.multiple = true; inp.onchange = e => { use(e.target.files); inp.value = ''; inp.multiple = false; }; inp.click(); };
  return d;
}
function nextPrendaName() { const n = Math.max(0, ...C.vestidor.map(v => +v.num || 0), ...TABS.vestidor.items.map(v => +v.num || 0), ...TABS.vestidor.items.filter(v => v.pending).map(v => +(String(v.name).match(/(\d+)/) || [0, 0])[1])) + 1; return `Prenda Nº ${n}`; }
function askPrendaTagsBatch(datas) { // varias prendas a la vez: un popup por imagen («k de N»), etiquetas y Siguiente; al final se generan todas seguidas
  const TAGS = ['De Vestir', 'Comfy', 'Sport', 'Nieve', 'Bañador']; const picked = []; let k = 0;
  const step = () => { const sel = new Set(); $('#mlbImg').src = datas[k]; $('#mlbCap').textContent = `Prenda ${k + 1} de ${datas.length} · ¿qué etiqueta lleva?`; const box = $('#mlbBtns'); box.innerHTML = '';
    const chips = el('div', 'combo'); TAGS.forEach(t => { const c = el('button', 'tagpick', t); c.onclick = () => { if (sel.has(t)) sel.delete(t); else sel.add(t); c.classList.toggle('on', sel.has(t)); }; chips.appendChild(c); }); box.appendChild(chips);
    const last = k === datas.length - 1; const go = el('button', 'btn w acc', last ? (datas.length > 1 ? `✨ Generar las ${datas.length} fichas` : '✨ Generar la ficha') : 'Siguiente →'); go.onclick = () => { picked.push([...sel]); k++; if (k < datas.length) step(); else { closeMiniLb(); datas.forEach((d, i) => prendaGenerate(nextPrendaName(), d, picked[i])); if (datas.length > 1) toast(`${datas.length} fichas en cola`); } }; box.appendChild(go);
    if (datas.length > 1) { const sk = el('button', 'btn w', 'Saltar esta imagen'); sk.onclick = () => { datas.splice(k, 1); if (!datas.length) { closeMiniLb(); return; } if (k >= datas.length) k = datas.length - 1; step(); }; box.appendChild(sk); }
    $('#mlb').classList.add('on'); };
  step();
}
function askPrendaTags(name, dataUrl) { // mini popup: etiqueta(s) de la prenda nueva antes de generar
  const TAGS = ['De Vestir', 'Comfy', 'Sport', 'Nieve', 'Bañador']; const sel = new Set();
  $('#mlbImg').src = dataUrl; $('#mlbCap').textContent = name + ' · ¿qué etiqueta lleva?'; const box = $('#mlbBtns'); box.innerHTML = '';
  const chips = el('div', 'combo'); TAGS.forEach(t => { const c = el('button', 'tagpick', t); c.onclick = () => { if (sel.has(t)) sel.delete(t); else sel.add(t); c.classList.toggle('on', sel.has(t)); }; chips.appendChild(c); }); box.appendChild(chips);
  const go = el('button', 'btn w acc', '✨ Generar la ficha'); go.onclick = () => { const r0 = $('#mlbImg').getBoundingClientRect(); closeMiniLb(); flyToNav(dataUrl, r0, 'vestidor'); prendaGenerate(name, dataUrl, [...sel]); }; box.appendChild(go);
  $('#mlb').classList.add('on');
}
const VCOLORS = [['Negro', '#111'], ['Blanco', '#f4f4f4'], ['Rojo', '#c62828'], ['Rosa', '#f06292'], ['Azul', '#1e5bc6'], ['Celeste', '#8ec5ff'], ['Verde', '#2e7d32'], ['Amarillo', '#f9c80e'], ['Beige', '#d8c3a5'], ['Marrón', '#6d4c41'], ['Morado', '#7b3fa0'], ['Gris', '#8a8a8a']];
function hueName(h) { const N = [[15, 'rojo'], [40, 'naranja'], [65, 'amarillo'], [95, 'lima'], [150, 'verde'], [185, 'turquesa'], [210, 'celeste'], [250, 'azul'], [280, 'violeta'], [315, 'morado'], [345, 'rosa'], [361, 'rojo']]; return N.find(x => h < x[0])[1]; }
function hslHex(h, s, l) { s /= 100; l /= 100; const k = n => (n + h / 30) % 12, a = s * Math.min(l, 1 - l), f = n => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1))); return '#' + [f(0), f(8), f(4)].map(x => Math.round(x * 255).toString(16).padStart(2, '0')).join(''); }
function gridFor(it) { if (it._grid) return it._grid; const c = TABS.creaciones.items.find(x => x.meta && x.meta.variaciones && x.meta.compIds && x.meta.compIds.vestidor === it.id); return c ? c.src : null; }
function hairVariants(it) { return TABS.creaciones.items.filter(c => !c.pending && c.meta && c.meta.hairVar === it.id); }
function hairColorSection(it) { // color de pelo del peinado: slider → imagen del mismo peinado con otro color; las variantes quedan debajo y se pueden elegir
  const box = el('div', 'colsec'); const vars = hairVariants(it);
  if (vars.length || it._hvJob) { box.appendChild(el('div', 'lbl', `Colores de pelo · ${vars.length + 1}`)); const row = el('div', 'varrow wide'); const all = [{ src: it.files.main, name: 'Original', orig: true }, ...vars.map(v => ({ src: v.src, name: v.meta.color || v.name }))];
    all.forEach(v => { const d = el('div', 'var' + (((it._variant || null) === (v.orig ? null : v.src)) ? ' on' : ''), `<img src="${v.src}" alt=""><small>${v.name}</small>`); d.onclick = () => { it._variant = v.orig ? null : v.src; showImage(v.src, true); renderSide(); if (state.comp.hair === it) badge(); }; row.appendChild(d); });
    for (let q = 0; q < (it._hvJob || 0); q++) row.appendChild(el('div', 'var pend', '')); box.appendChild(row); slideRow(row); }
  box.appendChild(el('div', 'lbl', 'Color de pelo')); state.hHue = state.hHue == null ? 20 : state.hHue;
  const hr = el('div', 'huerow'); const dot = el('span', 'huedot'); const rng = document.createElement('input'); rng.type = 'range'; rng.min = 0; rng.max = 360; rng.value = state.hHue; rng.className = 'hue'; const nm = el('span', 'huename');
  const HN = h => h < 18 ? 'pelirrojo' : h < 40 ? 'cobrizo' : h < 55 ? 'rubio' : h < 150 ? 'verde' : h < 200 ? 'turquesa' : h < 250 ? 'azul' : h < 285 ? 'violeta' : h < 330 ? 'rosa' : 'rojo';
  const EN = { 'pelirrojo': 'ginger red', 'cobrizo': 'copper', 'rubio': 'blonde', 'verde': 'green', 'turquesa': 'turquoise', 'azul': 'blue', 'violeta': 'violet', 'rosa': 'pink', 'rojo': 'red', 'negro azabache': 'jet black', 'castaño oscuro': 'dark brown', 'castaño': 'brown', 'castaño claro': 'light brown', 'caoba': 'mahogany', 'pelirrojo natural': 'natural ginger', 'rubio oscuro': 'dark blonde', 'rubio miel': 'honey blonde', 'rubio platino': 'platinum blonde', 'gris plata': 'silver gray' };
  const pick = (es, hex) => { it._color = { es, en: EN[es] || es, hex }; if (state.comp.hair === it) { state.hairCol = it._color; badge(); toast('Color «' + es + '» puesto en Crear imagen'); } renderSide(); };   // el color viaja con el peinado, en palabras
  const upd = () => { state.hHue = +rng.value; dot.style.background = hslHex(state.hHue, 70, 45); nm.textContent = HN(state.hHue); }; rng.oninput = upd; rng.onchange = () => pick(HN(state.hHue), hslHex(state.hHue, 70, 45)); upd(); hr.appendChild(rng); hr.appendChild(dot); box.appendChild(hr); box.appendChild(nm);
  const nat = el('div', 'neutros'); [['negro azabache', '#0b0b0d'], ['castaño oscuro', '#3b2416'], ['castaño', '#5a3a22'], ['castaño claro', '#8a5a36'], ['caoba', '#6b2a1c'], ['pelirrojo natural', '#a8471f'], ['rubio oscuro', '#9c7a4a'], ['rubio miel', '#c89a55'], ['rubio platino', '#e8e0c8'], ['gris plata', '#a9a9ad']].forEach(([n, c]) => { const b = el('button', 'sw', ''); b.style.background = c; b.title = n; b.onclick = () => { state.hNatural = n; dot.style.background = c; nm.textContent = n; pick(n, c); }; nat.appendChild(b); }); rng.addEventListener('input', () => { state.hNatural = null; }); box.appendChild(nat);
  if (it._color) { dot.style.background = it._color.hex || ''; nm.textContent = it._color.es; const q = el('div', 'status colsel', `Color elegido: <b>${esc(it._color.es)}</b> · ${state.comp.hair === it ? 'ya está en Crear imagen' : 'se añade con el peinado'} · `); const x = el('span', 'lnk', 'quitar color'); x.onclick = () => { it._color = null; state.hNatural = null; if (state.comp.hair === it) { state.hairCol = null; badge(); } renderSide(); }; q.appendChild(x); box.appendChild(q); }
  const gb = el('button', 'btn w pr', `💇 Generar con este color${it._hvJob ? ` · ⏳ ${it._hvJob}` : ''}<i>${fmtUsd(curModel().usd[state.quality])}</i>`); gb.onclick = () => hairRecolor(it, state.hNatural || HN(state.hHue), state.hNatural ? '' : hslHex(state.hHue, 70, 45)); box.appendChild(gb);
  const w = el('div'); w.style.padding = '0 18px 10px'; w.appendChild(box); return w;
}
async function hairRecolor(it, color, hex) {
  if (!LIVE) { toast('Conecta primero tu API (arriba, «Conecta tu API»)'); return; } const m = curModel(); const prompt = `Change ONLY the hair color of the woman in @Image1 to ${color}${hex ? ' (' + hex + ')' : ''}, natural realistic hair coloring with depth and highlights. Keep EXACTLY the same hairstyle, cut, volume, parting and length, the same face, glasses, earrings, clothing, pose, framing, background and lighting. Photoreal, no text.`;
  it._hvJob = (it._hvJob || 0) + 1; renderSide();
  const body = { item: 'pelo_' + it.id, prompt, images: [{ path: it.files.main }], aspect: '16:9', quality: state.quality, model: m.key, meta: { name: `Pelo ${color} · ${it.name}`, tab: 'hair', hairVar: it.id, color, hidden: true, model: m.name, ep: m.ep, prompt, comp: { Peinado: it.name }, compIds: { hair: it.id } } };
  let r; try { r = await fetch('/api/generar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
  if (!r || r.error) { it._hvJob = Math.max(0, (it._hvJob || 1) - 1); renderSide(); toast('No se pudo generar: ' + (r ? r.error : 'sin respuesta')); return; }
  const job = { rid: r.request_id, it, tab: 'hair', m, kind: 'image', hairvar: true, t0: performance.now(), status: 'queued', usd: r.usd != null ? Number(r.usd) : m.usd[state.quality] }; JOBS.set(job.rid, job); ensurePoller(); toast(`Generando el peinado en ${color}…`);
}
function colorSection(it) {
  const root = it.parent ? (TABS.vestidor.items.find(x => x.id === it.parent) || it) : it;
  const box = el('div', 'colsec');
  
  const kids = TABS.vestidor.items.filter(c => c.parent === root.id);
  if (kids.length) { box.appendChild(el('div', 'lbl', `Colores de esta prenda · ${kids.length + 1}`)); const row = el('div', 'varrow slide'); [root, ...kids].forEach(k => { const d = el('div', 'var' + (k === it ? ' on' : '') + (k.pending ? ' pend' : ''), `<img src="${k.card}" alt="">`); d.title = k.pending ? 'Generándose…' : k.name; d.onclick = () => { if (k.pending) return; state.sel.vestidor = k; paint(k, true); renderSide(); }; row.appendChild(d); }); box.appendChild(row); slideRow(row); }
  box.appendChild(el('div', 'lbl', 'Nuevo color'));
  state.vHue = state.vHue == null ? 330 : state.vHue; const hr = el('div', 'huerow'); const dot = el('span', 'huedot'); const rng = document.createElement('input'); rng.type = 'range'; rng.min = 0; rng.max = 360; rng.value = state.vHue; rng.className = 'hue';
  const nm = el('span', 'huename'); const upd = () => { state.vHue = +rng.value; dot.style.background = hslHex(state.vHue, 80, 50); nm.textContent = hueName(state.vHue); }; rng.oninput = upd; upd(); hr.appendChild(rng); hr.appendChild(dot); box.appendChild(hr); box.appendChild(nm);
  state.vNeutral = null;
  const gc = el('button', 'btn w pr', `🎨 Generar en este color<i>${fmtUsd(curModel().usd.high)}</i>`); gc.onclick = () => { const n = state.vNeutral || hueName(state.vHue); const hex = state.vNeutral ? '' : ' (' + hslHex(state.vHue, 80, 50) + ')'; if (confirm(`¿Ficha nueva de «${root.name}» en ${n}? (${fmtUsd(curModel().usd.high)})`)) recolorPrenda(root, n + hex); }; box.appendChild(gc);
  const g = gridFor(root); const gb = el('button', 'btn w pr', root._gridJob ? '⏳ Generando las 9 variaciones…' : `${g ? '🎲 Otras 9 variaciones' : '🎲 Dame 9 variaciones de color'}<i>${fmtUsd(curModel().usd.high)}</i>`); gb.disabled = !!root._gridJob; gb.onclick = () => gridVariations(root); box.appendChild(gb);
  if (root._gridJob) { const ph = el('div', 'gridbox loading'); ph.innerHTML = `<div class="spin"></div><span class="gsec" id="gridSec">0 s</span>`; box.appendChild(ph); clearInterval(state._gridTimer); state._gridTimer = setInterval(() => { const e = $('#gridSec'); if (!e || !root._gridJob) { clearInterval(state._gridTimer); return; } e.textContent = Math.round((performance.now() - root._gridT0) / 1000) + ' s'; }, 1000); }
  else if (g) { const gx = el('div', 'gridbox'); gx.innerHTML = `<img src="${g}" alt="">`; gx.onclick = () => lightbox(g, root.name + ' · variaciones'); box.appendChild(gx); box.appendChild(el('div', 'lbl', 'Elige la que más te guste'));
    const nums = el('div', 'nums'); for (let k = 1; k <= 9; k++) { const b = el('button', 'num', String(k)); b.onclick = () => pickVariation(root, k, g); nums.appendChild(b); } box.appendChild(nums); }
  const w = el('div'); w.style.padding = '0 18px 10px'; w.appendChild(box); return w;
}
function colorSectionOld(it) { // variaciones de color de una prenda: un color concreto → ficha nueva · «Dame 9 variaciones» → rejilla 3×3 numerada → elige 1-9 → ficha nueva
  const box = el('div', 'colsec'); box.appendChild(el('div', 'lbl', 'Variaciones de color'));
  const sw = el('div', 'swatches'); VCOLORS.forEach(([n, c]) => { const b = el('button', 'sw', ''); b.style.background = c; b.title = `Ficha nueva en ${n.toLowerCase()}`; b.onclick = () => { if (confirm(`¿Generar una ficha nueva de «${it.name}» en ${n.toLowerCase()}? (${fmtUsd(curModel().usd.high)})`)) recolorPrenda(it, n); }; sw.appendChild(b); }); box.appendChild(sw);
  const gb = el('button', 'btn w', it._gridJob ? '⏳ Generando las 9 variaciones…' : '🎲 Dame 9 variaciones de color'); gb.disabled = !!it._gridJob; gb.onclick = () => gridVariations(it); box.appendChild(gb);
  if (it._grid) { const g = el('div', 'gridbox'); g.innerHTML = `<img src="${it._grid}" alt="">`; g.onclick = () => lightbox(it._grid, it.name + ' · variaciones'); box.appendChild(g); box.appendChild(el('div', 'lbl', 'Elige la que más te guste'));
    const nums = el('div', 'nums'); for (let k = 1; k <= 9; k++) { const b = el('button', 'num', String(k)); b.onclick = () => pickVariation(it, k); nums.appendChild(b); } box.appendChild(nums); }
  const w = el('div'); w.style.padding = '0 18px 10px'; w.appendChild(box); return w;
}
async function recolorPrenda(it, colorName) {
  const m = curModel(); const name = nextPrendaName(); const prompt = `Recolor the outfit in @Image1 to ${colorName} (main garment in that color; if it has several pieces, keep a harmonious combination led by that color). Keep EXACTLY the same garments, cut, fabrics, seams, details, shoes, the same 4-panel layout, framing, gray studio background and lighting. Photorealistic, no text, no watermark.`;
  prendaFromImage(name, it.ficha, { path: it.ficha }, prompt, it.tags || [], it.parent || it.id);
}
async function gridVariations(it) {
  if (!LIVE) { toast('Conecta primero tu API (arriba, «Conecta tu API»)'); return; } const m = curModel();
  const prompt = `Using the outfit of @Image1 as reference, create ONE square image: a clean 3×3 grid (9 equal panels, thin white dividers) showing the SAME outfit (identical garments, cut, fabrics and details) worn on the same headless mannequin-like front view, in 9 DIFFERENT harmonious color combinations (all pieces recolored coherently in each panel). Put a small bold number 1 to 9 in the top-left corner of each panel, reading order left→right, top→bottom. Neutral gray studio background, photorealistic, no other text.`;
  it._gridJob = true; it._gridT0 = performance.now(); renderSide();
  const body = { item: 'variaciones_' + it.id, prompt, images: [{ path: it.ficha }], aspect: '1:1', quality: 'high', model: m.key, meta: { name: 'Variaciones · ' + it.name, tab: 'vestidor', variaciones: true, hidden: true, model: m.name, ep: m.ep, prompt, comp: { Prenda: it.name }, compIds: { vestidor: it.id } } };
  let r; try { r = await fetch('/api/generar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
  if (!r || r.error) { it._gridJob = false; renderSide(); toast('No se pudo generar: ' + (r ? r.error : 'sin respuesta')); return; }
  const job = { rid: r.request_id, it, tab: 'vestidor', m, kind: 'image', variant: true, t0: performance.now(), status: 'queued', usd: r.usd != null ? Number(r.usd) : m.usd.high }; JOBS.set(job.rid, job); ensurePoller(); toast('Generando 9 variaciones de color…');
}
async function pickVariation(it, k, gsrc) { // recorta la celda k de la rejilla 3×3 y la usa como prenda de partida de una ficha nueva
  const img = new Image(); img.src = gsrc || gridFor(it); await new Promise(res => { img.onload = res; img.onerror = res; }); if (!img.naturalWidth) return;
  const cw = img.naturalWidth / 3, ch = img.naturalHeight / 3, c = (k - 1) % 3, r = Math.floor((k - 1) / 3); const cv = document.createElement('canvas'); cv.width = Math.round(cw); cv.height = Math.round(ch); cv.getContext('2d').drawImage(img, c * cw, r * ch, cw, ch, 0, 0, cv.width, cv.height);
  const data = cv.toDataURL('image/jpeg', 0.92); if (!confirm(`¿Crear una ficha nueva con la variación ${k}? (${fmtUsd(curModel().usd.high)})`)) return; prendaGenerate(nextPrendaName(), data, it.tags || [], it.parent || it.id);
}
function askDeletePrenda(it) { const kids = TABS.vestidor.items.filter(c => c.parent === it.id); const msg = it.parent ? `¿Eliminar esta variación de color («${it.name}»)?` : kids.length ? `¿Eliminar «${it.name}»? Sus ${kids.length} variación(es) se quedan (la primera pasa a ser la original).` : `¿Eliminar «${it.name}» del Vestidor?`; if (confirm(msg + '\nDeja de verse en tu Vestidor.')) deletePrenda(it.id); }
async function deletePrenda(id, quiet) {
  let r; try { r = await fetch('/api/borrar_prenda', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id }) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
  if (!r || r.error) { if (!quiet) toast('No se pudo eliminar: ' + (r ? r.error : 'sin respuesta')); return; }
  const L = TABS.vestidor.items; const it = L.find(x => x.id === id); const par = it && it.parent; const kids = L.filter(c => c.parent === id);
  if (kids.length) { const nu = kids[0]; delete nu.parent; kids.slice(1).forEach(k => k.parent = nu.id); }
  const i = L.indexOf(it); if (i >= 0) L.splice(i, 1);
  if (!quiet) { const next = kids[0] || (par && L.find(x => x.id === par)) || L[Math.max(0, i - 1)]; state.sel.vestidor = next; toast('Prenda eliminada'); }
  if (state.tab === 'vestidor') { const keep = rail.scrollTop; renderRail(); if (!quiet) { paint(cur(), true); renderSide(); } rail.scrollTop = keep; }
}
async function regenPrenda(it) { // nueva ficha a partir del panel frontal de la actual; al terminar sustituye a la antigua
  const img = new Image(); img.src = it.card; await new Promise(res => { img.onload = res; img.onerror = res; }); const cv = document.createElement('canvas'); cv.width = img.naturalWidth; cv.height = img.naturalHeight; cv.getContext('2d').drawImage(img, 0, 0); const data = cv.toDataURL('image/jpeg', 0.92);
  const job = await prendaGenerate(it.name, data, it.tags || [], it.parent || null, it.id); if (job) toast('Regenerando…'); }
async function prendaFromImage(name, thumbSrc, image, prompt, tags, parent) { // ficha nueva a partir de una ficha existente (recolor)
  if (!LIVE) { toast('Conecta primero tu API (arriba, «Conecta tu API»)'); return; } const m = curModel(); const it = { id: 'prenda-' + Date.now(), name, num: '…', tags, parent, date: new Date().toISOString().slice(0, 10), card: thumbSrc, ficha: thumbSrc, looks: [], pending: true, custom: false };
  TABS.vestidor.items.splice(TABS.vestidor.items[0] && TABS.vestidor.items[0].id === 'n82' ? 1 : 0, 0, it); if (state.tab === 'vestidor') { renderRail(); renderSide(); }
  const body = { item: 'prenda', prompt, images: [image], aspect: '1:1', quality: 'high', model: m.key, meta: { prenda: true, name, tags, parent, tab: 'vestidor', model: m.name, ep: m.ep, quality: 'high', aspect: '1:1', prompt, comp: { Prenda: name } } };
  let r; try { r = await fetch('/api/generar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
  if (!r || r.error) { it._err = r ? r.error : 'sin respuesta'; toast('No se ha podido generar la ficha'); renderSide(); return; }
  const job = { rid: r.request_id, it, tab: 'vestidor', m, kind: 'image', prenda: true, t0: performance.now(), status: 'queued', usd: r.usd != null ? Number(r.usd) : m.usd.high }; JOBS.set(job.rid, job); ensurePoller(); renderRail();
}
async function prendaGenerate(name, dataUrl, tags, parent, replaces) {
  if (!LIVE) { toast('Conecta primero tu API (arriba, «Conecta tu API»)'); return; } const m = curModel(); const it = { id: 'prenda-' + Date.now(), name, num: '…', parent, tags: (tags && tags.length) ? tags : [], date: new Date().toISOString().slice(0, 10), card: dataUrl, ficha: dataUrl, looks: [], pending: true, custom: false };
  const oldP = replaces ? TABS.vestidor.items.find(v => v.id === replaces) : null; // regenerar: sin tarjeta nueva, la misma ficha lleva el indicador de carga
  if (!oldP) { TABS.vestidor.items.splice(TABS.vestidor.items[0] && TABS.vestidor.items[0].id === 'n82' ? 1 : 0, 0, it); if (!parent) state.sel.vestidor = it; } else it.hidden_ = true;
  if (state.tab === 'vestidor') { renderRail(); if (!parent && !oldP) paint(it, true); renderSide(); }
  const body = { item: 'prenda', prompt: PRENDA_PROMPT, images: [userPhoto ? { data: userPhoto } : ariaBody(), { data: dataUrl }], aspect: '1:1', quality: 'high', model: m.key, meta: { prenda: true, name, tags: tags || [], parent, replaces: replaces || undefined, tab: 'vestidor', model: m.name, ep: m.ep, quality: 'high', aspect: '1:1', prompt: PRENDA_PROMPT, refs: ['aria_cuerpo', 'prenda.jpg'], comp: { Prenda: name } } };
  log(`<span class="m">POST</span> /api/generar <span class="u">${m.ep}</span> <span class="g">· nueva prenda «${name}» · ficha 4 vistas · 9:16 · ${fmtUsd(m.usd.high)}</span>`);
  let r; try { r = await fetch('/api/generar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
  if (!r || r.error) { it._err = r ? r.error : 'sin respuesta'; toast('No se ha podido generar la ficha'); renderSide(); return; }
  const job = { rid: r.request_id, it: oldP || it, tab: 'vestidor', m, kind: 'image', prenda: true, replaces, t0: performance.now(), status: 'queued', usd: r.usd != null ? Number(r.usd) : m.usd.high }; JOBS.set(job.rid, job); ensurePoller(); renderRail(); if (cur() === it) { paint(it, true); renderSide(); } return job;
}
// modo «elegir»: otra parte de la app (p. ej. «＋ Nueva ficha») manda al Vestidor; el único botón es «Añadir» y vuelve sola
function startPick(tab, opts) { state.pick = Object.assign({ tab, label: 'la ficha' }, opts); setTab(tab); pickNav(); renderSide(); toast(`Elige una prenda y pulsa «＋ Añadir a ${state.pick.label}»`); }
function pickNav() { document.querySelectorAll('#nav button[data-tab]').forEach(b => b.classList.toggle('pickmode', !!(state.pick && b.dataset.tab === state.pick.tab))); document.body.classList.toggle('picking', !!state.pick); }
function pickDone(it) { const p = state.pick; if (!p) return; if (it.pending) { toast('Esa prenda todavía se está generando'); return; } state.pick = null; pickNav(); p.done(it); }
function pickCancel() { const p = state.pick; state.pick = null; pickNav(); if (p && p.cancel) p.cancel(); else setTab('perfil'); }
function pickPanel(it) {
  const top = el('div', 'picktop'); const bk = el('button', 'btn backbtn', '← Volver sin elegir'); bk.onclick = pickCancel; top.appendChild(bk);
  if (!it.pending) { const b = el('button', 'btn w acc pickadd', '＋ Añadir a ' + state.pick.label); b.onclick = () => pickDone(it); top.appendChild(b); }
  side.appendChild(top);
  if (it.pending) { side.appendChild(sec('Ficha en camino', el('div', 'status', `«${esc(it.name)}» todavía se está generando.`))); return; }
  const src = it.ficha || (it.files && (it.files.main || it.files.thumb)) || it.card || it.thumb || ''; const fb = el('div', 'fichabox big pickficha'); fb.innerHTML = `<img src="${src}" alt="">`; fb.onclick = () => lightbox(src, it.name); side.appendChild(fb);
  side.appendChild(el('div', 'status cap', `${esc(it.name)}${(it.tags || []).length ? ' · ' + [].concat(it.tags).join(', ') : ''}${it.num ? ' · Nº ' + it.num : ''}`));
}
window.startPick = startPick;
function vestidorPanel(it) { // Usar en una creación · ficha con «Generar preview» al pasar el ratón · Aria con la prenda (si existe) · ajustes · añadir prenda
  if (it.pending) { side.appendChild(sec('Ficha en camino', el('div', 'status', `Generando la ficha de 4 vistas de «${it.name}»…`))); side.appendChild(sec('', prendaDrop())); return; }
  side.appendChild(addBtn('vestidor', 'prenda'));
  const m = curModel(); const ex = existingImage('vestidor', it); const jb = jobFor(it);
  const fb = el('div', 'fichabox big'); fb.innerHTML = `<img src="${it.ficha}" alt="">`; fb.onclick = () => { const root = it.parent ? (TABS.vestidor.items.find(x => x.id === it.parent) || it) : it; const kids = TABS.vestidor.items.filter(c => c.parent === root.id && !c.pending); if (kids.length) state.galGroup = [root, ...kids]; openGal(it); };
  { const gp = el('span', 'rcb', `🔄 Regenerar · ${fmtUsd(m.usd.high)}`); gp.title = 'Vuelve a generar esta ficha (la actual se sustituye cuando termine)'; gp.onclick = e => { e.stopPropagation(); if (confirm(`¿Regenerar «${it.name}»? La ficha actual se sustituirá cuando termine. (${fmtUsd(m.usd.high)})`)) regenPrenda(it); }; fb.appendChild(gp); }
  { const sb = el('button', 'favb' + (it.fav ? ' on' : ''), it.fav ? '★' : '☆'); sb.title = it.fav ? 'Quitar de favoritos' : 'Añadir a favoritos'; sb.onclick = e => { e.stopPropagation(); toggleFav(it); }; fb.appendChild(sb); }
  { const tb = el('button', 'trash', '🗑'); tb.title = 'Eliminar esta prenda'; tb.onclick = e => { e.stopPropagation(); askDeletePrenda(it); }; fb.appendChild(tb); }
  side.appendChild(fb);
  side.appendChild(el('div', 'status cap', `Vestidor Virtual · ${(it.tags || []).join(', ') || 'sin etiqueta'} · Nº ${it.num}`));
  side.appendChild(colorSection(it));
  { const wb = el('div'); wb.style.padding = '0 18px 8px'; wb.appendChild(withBtn('vestidor', it)); side.appendChild(wb); }
  const box = el('div', 'stack');
  if (jb) { const cb = el('button', 'btn w', `⏳ Generándose · ${Math.round((performance.now() - jb.t0) / 1000)} s · cancelar`); cb.onclick = () => cancelJob(jb, 'cancelada por ti'); box.appendChild(cb); }
  const f = el('div', 'fold' + (state.fold.vestidor ? '' : ' closed')); const h = el('h3', '', 'Ajustes de generación'); h.onclick = () => { state.fold.vestidor = !state.fold.vestidor; f.classList.toggle('closed', !state.fold.vestidor); }; f.appendChild(h); f.appendChild(genSettings('vestidor', it)); box.appendChild(f);
  side.appendChild(sec('', prendaDrop())); side.appendChild(sec('', box));
}
const SND = { on: true, vol: 0.8 };   // en la Filmoteca, el vídeo elegido suena (las miniaturas del hover, no) try { Object.assign(SND, JSON.parse(localStorage.getItem('am_vtsound') || '{}')); } catch (e) {}
function persistSound() { persist('am_vtsound', JSON.stringify(SND)); }
function applySound(v) { if (!v) return; v.muted = !SND.on; v.volume = SND.vol; }
function videotecaPanel(it) {
  const st = el('div', 'stack'); const rc = el('button', 'btn w acc', '🔄 Recrear vídeo'); rc.onclick = () => recreateFromVideoteca(it); st.appendChild(rc);
  const inVid = poolHas(it.video); const b = el('button', 'btn w', inVid ? '✓ Ya en Crear vídeo' : '🎬 Añadir como referencia'); b.onclick = () => { if (!inVid) poolAdd({ id: 'vt:' + it.id, kind: 'video', name: 'Videoteca ' + it.name, src: it.video, thumb: it.poster }, true); setTab('video'); }; st.appendChild(b); side.appendChild(sec('Usar en una creación', st));
  const mv = el('div', 'mini vt'); mv.innerHTML = `<video src="${it.video}" poster="${it.poster}" loop autoplay playsinline></video><button class="pp" title="Reproducir / pausar"></button>`; const v = mv.querySelector('video'); applySound(v); if (!state.vtClicked) v.muted = true; v.play().catch(() => { v.muted = true; v.play().catch(() => {}); }); v.onclick = () => { v.pause(); openGal(it); };
  const pp = mv.querySelector('.pp'); const ICO = { play: '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>', pause: '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg>' }; const syncPP = () => { pp.innerHTML = v.paused ? ICO.play : ICO.pause; }; v.addEventListener('play', syncPP); v.addEventListener('pause', syncPP); syncPP(); pp.onclick = e => { e.stopPropagation(); if (v.paused) v.play().catch(() => {}); else v.pause(); };
  const SPK = on => on ? '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5L6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/></svg>' : '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5L6 9H2v6h4l5 4z"/><line x1="15" y1="15" x2="21" y2="9"/></svg>';
  const sc = el('div', 'sndctl'); sc.innerHTML = `<button class="sb" title="Sonido">${SPK(SND.on)}</button><input type="range" min="0" max="1" step="0.05" value="${SND.vol}" title="Volumen">`; sc.onclick = e => e.stopPropagation();
  sc.querySelector('.sb').onclick = () => { SND.on = !SND.on; persistSound(); sc.querySelector('.sb').innerHTML = SPK(SND.on); applySound(v); };
  sc.querySelector('input').oninput = e => { SND.vol = +e.target.value; if (SND.vol > 0 && !SND.on) { SND.on = true; sc.querySelector('.sb').innerHTML = SPK(true); } persistSound(); applySound(v); }; mv.appendChild(sc); side.appendChild(mv); side.appendChild(aiLine(it));
  const box = el('div', 'stack'); const pbx = el('div', 'promptbox scrollbox', atHtml(it.prompt)); box.appendChild(pbx);
  const cp = el('button', 'btn w', 'Copiar prompt'); cp.onclick = () => { navigator.clipboard && navigator.clipboard.writeText(it.prompt || ''); toast('Prompt copiado'); }; box.appendChild(cp); side.appendChild(sec('', box));
}
function biblioPanel(it) {
  side.appendChild(addBtn('biblio', 'esta imagen para recrearla')); side.appendChild(miniPreview(it)); setTimeout(syncMini, 0); side.appendChild(aiLine(it)); if (!it.group) { const wb = el('div'); wb.style.padding = '0 18px 8px'; wb.appendChild(withBtn('biblio', it)); side.appendChild(wb); }
  const box = el('div', 'stack');
  const pbx = el('div', 'promptbox scrollbox', atHtml(it.neutro || it.prompt)); box.appendChild(pbx);
  const cp = el('button', 'btn w', 'Copiar prompt'); cp.onclick = () => { navigator.clipboard && navigator.clipboard.writeText(it.neutro || it.prompt); toast('Prompt copiado'); }; box.appendChild(cp);
  if (!it.group) { const pr = el('button', 'btn w pr', `👗 Crear prenda<i>${fmtUsd(curModel().usd.high)}</i>`); pr.title = 'Como arrastrar esta foto al Vestidor: se genera su ficha de prenda con la ropa que lleva'; pr.onclick = () => prendaDesdeImagen(it.image, it.name); box.appendChild(pr); }
  side.appendChild(sec('', box));
}
async function prendaDesdeImagen(src, from) { // una imagen de la app (Fototeca, creación…) → ficha nueva del Vestidor, igual que al arrastrarla
  if (!LIVE) { toast('Conecta primero tu API (arriba, «Conecta tu API»)'); return; }
  let du; try { const b = await fetch(src.split('?')[0]).then(r => r.blob()); du = await new Promise((ok, ko) => { const f = new FileReader(); f.onload = () => ok(f.result); f.onerror = ko; f.readAsDataURL(b); }); } catch (e) { toast('No se pudo leer la imagen'); return; }
  askPrendaTags(nextPrendaName(), du); toast(`Elige la etiqueta: la ficha de la ropa de «${from}» irá al Vestidor`);
}
function creationMeta(it, host) { // panel de una creación (en el popup): combinación → prompt → datos → acciones
  const m = it.meta || {}; const rows = []; const MN = { qwen: 'Qwen Image 3 · Edit', grok: 'Grok Image 2.0', mstudio: 'Marketing Studio Image 2.0', ideogram: 'Ideogram 4.0', nbp: 'Nano Banana Pro', gptimg: 'GPT Image 2.5', seedream: 'Seedream 5.0 Pro', i2v: 'Seedance 2.0 · imagen → vídeo', r2v: 'Seedance 2.0 · con referencias' };
  const fecha = m.t ? new Date(m.t * 1000).toLocaleString('es-ES', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';
  host.innerHTML = ''; const head = el('div', 'sec'); { const ids = (Array.isArray(m.chars) && m.chars.length) ? m.chars : (m.char ? [m.char] : []);
    if (ids.length) { const cr = el('div', 'galchars'); ids.forEach(id => { const c = charList().find(x => x.id === id); cr.appendChild(el('span', 'galchar', `${c && c.avatar ? `<img src="${c.avatar}" alt="">` : '<i></i>'}${esc(c ? c.name : id)}`)); }); head.appendChild(cr); }
    else head.appendChild(el('div', m.charName ? 'status' : 'big', m.charName ? esc(m.charName) : it.name)); } head.appendChild(el('div', 'status', [it.kind === 'video' ? 'Vídeo' : 'Imagen', m.model || MN[m.model_key] || ''].filter(Boolean).join(' · '))); if (fecha) head.appendChild(el('div', 'status', fecha)); host.appendChild(head);
  const combo = Object.assign({}, m.comp || {}); if (!Object.keys(combo).length && m.item && m.sin_ficha) combo[it.kind === 'video' ? 'Imagen' : 'Elemento'] = (allItems().find(x => x.id === m.item) || {}).name || m.item;
  const resolved = resolveComp(m);
  if (Object.keys(combo).length) { const cb = el('div', 'combo col'); const marked = new Set(); const wrap = el('div', 'stack'); wrap.appendChild(cb);
    const fb = el('button', 'btn w', '🔎 Buscar'); fb.disabled = true; fb.title = 'Marca (✓) uno o varios componentes y busca las creaciones que los llevan todos'; wrap.appendChild(fb);
    const refresh = () => { const sel = [...marked].map(tk => ({ tab: tk, id: resolved[tk].id, name: resolved[tk].name })); const n = sel.length ? creationsSel(sel).length : 0; fb.disabled = !sel.length; fb.textContent = sel.length ? `🔎 Buscar · ${n} creaci${n === 1 ? 'ón' : 'ones'}` : '🔎 Buscar'; fb.onclick = () => { const sn = navSnap(); closeGal(); showCreationsSel(sel, 'creaciones', sn); }; };
    const ORD = Object.values(COMP); Object.entries(combo).sort((a, b) => (ORD.indexOf(a[0]) === -1 ? 99 : ORD.indexOf(a[0])) - (ORD.indexOf(b[0]) === -1 ? 99 : ORD.indexOf(b[0]))).forEach(([k, v]) => { const tk = Object.keys(COMP).find(x => COMP[x] === k); const it2 = tk && resolved[tk]; const sp = el('span', 'cchip' + (it2 ? ' link' : ''), `<b>${k}</b><i>${v}</i>${it2 ? '<em class="mk" title="Marcar para buscar">✓</em>' : ''}`);
      if (it2) { sp.title = 'Abrir ' + k.toLowerCase() + ' con su ficha'; sp.querySelector('i').onclick = e => { e.stopPropagation(); miniLb(compImage(tk, it2), `${k} · ${it2.name}`, [[`↗ Ir a ${TABS[tk].label}`, () => { closeMiniLb(); closeGal(); state.cfilt = null; state.sel[tk] = it2; setTab(tk); select(it2, true, true); openGal(it2); }], ['⬇ Descargar', () => { const a = document.createElement('a'); a.href = compImage(tk, it2); a.download = compImage(tk, it2).split('/').pop(); document.body.appendChild(a); a.click(); a.remove(); }]]); }; sp.querySelector('.mk').onclick = e => { e.stopPropagation(); if (marked.has(tk)) marked.delete(tk); else marked.add(tk); sp.classList.toggle('on', marked.has(tk)); refresh(); }; }
      if (!it2 && k === COMP.biblio && m.canvasRef) { sp.classList.add('link'); sp.title = 'Ver la imagen original que se usó'; sp.querySelector('i').onclick = e => { e.stopPropagation(); miniLb(m.canvasRef, `${k} · ${v}`, [['⬇ Descargar', () => { const a = document.createElement('a'); a.href = m.canvasRef; a.download = (v || 'captura') + '.' + m.canvasRef.split('.').pop(); document.body.appendChild(a); a.click(); a.remove(); }]]); }; }
      cb.appendChild(sp); });
    if (m.modoFoto) wrap.insertBefore(el('div', 'status galmet', m.modoFoto === 'misma' ? 'Misma foto · se editó la imagen' : m.modoFoto === 'descripcion' ? 'Desde su descripción · imagen nueva' : 'Desde el prompt de la escena · imagen nueva'), wrap.firstChild);
    host.appendChild(sec('Combinación', wrap)); }
  { const rs = el('div', 'stack'); const rec_ = recComp(m); if (Object.keys(rec_).length) { const rb = el('button', 'btn w acc', '✨ Recrear'); rb.title = 'Carga en Crear imagen todo lo de esta creación: personaje, prenda, peinado, referencia, complementos y ajustes'; rb.onclick = () => { closeGal(); recrear(it); }; rs.appendChild(rb); } const d0 = el('button', 'btn w outline', '⬇ Descargar'); d0.onclick = () => { const a = document.createElement('a'); a.href = it.src; a.download = it.src.split('/').pop(); document.body.appendChild(a); a.click(); a.remove(); }; rs.appendChild(d0); host.appendChild(sec('', rs)); }
  if (m.prompt) { const pb = el('div', 'stack'); pb.appendChild(el('div', 'promptbox', atHtml(m.prompt, m.refs))); pb.querySelectorAll('b.at.link').forEach(b => { b.title = 'Ver la imagen · ' + b.title; b.onclick = e => { e.stopPropagation(); openRefN(m, +b.dataset.n); }; }); const cp = el('button', 'btn w', 'Copiar prompt'); cp.onclick = () => { navigator.clipboard && navigator.clipboard.writeText(m.prompt); toast('Prompt copiado'); }; pb.appendChild(cp); host.appendChild(sec('Prompt', pb)); }
  if (m.model || MN[m.model_key]) rows.push(['Modelo', m.model || MN[m.model_key]]); if (m.quality) rows.push(['Calidad', m.quality]); if (m.resolution) rows.push(['Resolución', m.resolution]); if (m.aspect) rows.push(['Formato', m.aspect]); if (m.width && m.height) rows.push(['Tamaño', `${m.width} × ${m.height} px`]); if (m.duration) rows.push(['Duración', m.duration + ' s']);
  if (m.usd != null || m.usd_est != null) rows.push(['Coste', (it.kind === 'video' ? '≈' : '') + fmtUsd(m.usd != null ? m.usd : m.usd_est)]); if (m.ms) rows.push(['Tiempo', (m.ms / 1000).toFixed(0) + ' s']); if (fecha) rows.push(['Fecha', fecha]); if (m.refs && m.refs.length) rows.push(['Referencias', m.refs.join(', ')]); rows.push(['Archivo', it.src.split('/').pop()]);
  host.appendChild(sec('Datos', el('div', 'kv', rows.map(([k, v]) => `<span>${k}</span><b>${v}</b>`).join(''))));
  if (m.sin_ficha) host.appendChild(sec('', el('div', 'status', 'Generada antes de que el puente guardara la ficha: solo se conoce lo que dice el nombre del archivo.')));
  const st = el('div', 'stack');
  if (it.conv) { const d = el('button', 'btn w', '⬇ Descargar'); d.onclick = () => { const a = document.createElement('a'); a.href = it.src; a.download = it.src.split('/').pop(); document.body.appendChild(a); a.click(); a.remove(); }; st.appendChild(d); host.appendChild(sec('Acciones', st)); return; }
  if (m.fototeca && it.biblio) { const fb = el('button', 'btn w acc', '📚 Ver en la Fototeca'); fb.onclick = () => { closeGal(); state.cfilt = null; state.sel.biblio = it.biblio; state.filter.biblio = null; setTab('biblio'); select(it.biblio, false, true); }; st.appendChild(fb); const rb = el('button', 'btn w', '✨ Recrear esta imagen (Crear imagen)'); rb.onclick = () => { closeGal(); state.cfilt = null; addToImage('biblio', it.biblio, true); }; st.appendChild(rb); host.appendChild(sec('Acciones', st)); return; }
  if (it.kind !== 'video') { const vb = el('button', 'btn w', '🎥 Crear vídeo con esta imagen'); vb.onclick = () => { closeGal(); let li = TABS.video.items.find(i => i.src === it.src); if (!li) { li = libItem(it.src, it.name, 'creación'); TABS.video.items.unshift(li); } state.sel.video = li; setTab('video'); }; st.appendChild(vb); }
  const EYE_OFF = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';
  const EYE = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  const hd = el('button', 'btn w eye'); hd.innerHTML = it.hidden ? EYE : EYE_OFF; hd.title = it.hidden ? 'Vuelve a Mis creaciones' : 'Ocultar: solo se verá en la pestaña «Ocultos» de Mis creaciones'; hd.onclick = async () => { try { const r = await fetch('/api/ocultar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ file: it.src.split('?')[0], hidden: !it.hidden }) }).then(x => x.json()); if (r.error) throw new Error(r.error); } catch (e) { toast('No se ha podido: ' + e.message); return; } it.hidden = !it.hidden; it.meta.hidden = it.hidden; toast(it.hidden ? 'Oculta: la tienes en «Ocultos»' : 'Visible otra vez'); closeGal(); renderRail(); renderSide(); }; st.appendChild(hd);
  const del = el('button', 'btn w', '🗑 Eliminar esta creación'); del.style.color = '#b3261e'; del.onclick = async () => { if (!confirm('¿Eliminar «' + it.name + '»? Deja de verse y se borra del todo a los 30 días.')) return; try { const r = await fetch('/api/borrar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ file: it.src.split('?')[0] }) }).then(x => x.json()); if (r.error) throw new Error(r.error); } catch (e) { toast('No se ha podido eliminar: ' + e.message); return; } closeGal(); allItems().forEach(x => { if (x.live && x.live.split('?')[0] === it.src.split('?')[0]) { x.live = null; state.done.delete(x.id); } }); TABS.video.items.forEach(x => { if (x.video && x.video.split('?')[0] === it.src.split('?')[0]) x.video = null; }); toast('Eliminada'); const keep = rail.scrollTop; refreshLive(); [0, 400, 900, 1500].forEach(ms => setTimeout(() => { if (ms) { renderRail(); renderSide(); } rail.scrollTop = keep; }, ms)); }; st.appendChild(del);
  { const fila = el('div', 'galacts'); fila.appendChild(del); fila.appendChild(hd); st.appendChild(fila); }
  host.appendChild(sec('Acciones', st));
}
function creationPanel(it) { creationMeta(it, side); }
function libMeta(it, host) { // popup de Fototeca / Videoteca: nombre, etiquetas, IA, fecha, prompt, ajustes y Añadir
  host.innerHTML = ''; const vt = state.tab === 'videoteca';
  if (COMP[state.tab] && state.tab !== 'biblio') { const tab = state.tab; const head = el('div', 'sec'); head.appendChild(el('div', 'big', it.name)); head.appendChild(el('div', 'status', `${TABS[tab].base}${it.num ? ' · Nº ' + it.num : ''}${it.tipo ? ' · ' + it.tipo : ''}`)); host.appendChild(head);
    const tg = [].concat(Array.isArray(it.tags) ? it.tags : (it.tags ? [it.tags] : []), it.tipo ? [it.tipo] : []); if (tg.length) { const cb = el('div', 'combo'); tg.forEach(t => cb.appendChild(el('span', '', `<b>${t}</b>`))); host.appendChild(sec('Etiquetas', cb)); }
    if (state.pick && state.pick.tab === tab) { const ps = el('div', 'stack'); const pb = el('button', 'btn w acc', '＋ Añadir a ' + state.pick.label); pb.onclick = () => { closeGal(); pickDone(it); }; ps.appendChild(pb); host.appendChild(sec('Elegir', ps)); if (tab === 'vestidor') { const fb = el('div', 'fichabox'); fb.innerHTML = `<img src="${it.ficha}" alt=""><span class="tag">Ficha</span>`; fb.style.margin = '0 18px 12px'; fb.onclick = () => lightbox(it.ficha, it.name); host.appendChild(fb); } return; }
    const st = el('div', 'stack'); const inImg = inCrear(tab, it); const b1 = el('button', 'btn w acc', inImg ? '✓ Ya en Crear imagen' : '✨ Añadir a Crear imagen'); b1.onclick = () => { closeGal(); addToImage(tab, it, true); }; st.appendChild(b1);
    const inVid = poolHas(compImage(tab, it)); const b2 = el('button', 'btn w', inVid ? '✓ Ya en Crear vídeo' : '🎬 Añadir a Crear vídeo'); b2.onclick = () => { closeGal(); addToVideo(tab, it); setTab('video'); }; st.appendChild(b2);
    const wb = withBtn(tab, it); wb.onclick = () => { const sn = navSnap(); closeGal(); showCreationsWith(tab, it, sn); }; st.appendChild(wb); host.appendChild(sec('Usar', st));
    if (tab === 'vestidor') { const db = el('button', 'btn w', '🗑 Eliminar esta prenda'); db.style.color = '#b3261e'; db.onclick = () => { closeGal(); askDeletePrenda(it); }; st.appendChild(db); }
    if (tab === 'vestidor') { const fb = el('div', 'fichabox'); fb.innerHTML = `<img src="${it.ficha}" alt=""><span class="tag">Ficha</span>`; fb.style.margin = '0 18px 12px'; fb.onclick = () => lightbox(it.ficha, it.name); host.appendChild(fb); }
    if (it.desc) host.appendChild(sec('Descripción', el('div', 'promptbox scrollbox', it.desc)));
    return; }
  const head = el('div', 'sec'); head.appendChild(el('div', 'big', it.name)); head.appendChild(el('div', 'status', `${vt ? 'Prompts de Vídeo' : 'Prompts de Imágenes'}${it.date ? ' · ' + it.date : ''}`)); host.appendChild(head);
  const tags = [].concat(Array.isArray(it.tags) ? it.tags : (it.tags ? [it.tags] : []), it.escenas || [], (it.ai || []).map(a => 'IA: ' + a)); if (tags.length) { const cb = el('div', 'combo'); tags.forEach(t => cb.appendChild(el('span', '', `<b>${t}</b>`))); host.appendChild(sec('Etiquetas', cb)); }
  const st = el('div', 'stack');
  if (vt) { const rc = el('button', 'btn w acc', '🔄 Recrear vídeo'); rc.onclick = () => { closeGal(); recreateFromVideoteca(it); }; st.appendChild(rc);
    const inVid = poolHas(it.video); const b = el('button', 'btn w', inVid ? '✓ Ya en Crear vídeo' : '🎬 Añadir como referencia'); b.onclick = () => { if (!inVid) poolAdd({ id: 'vt:' + it.id, kind: 'video', name: 'Videoteca ' + it.name, src: it.video, thumb: it.poster }, true); closeGal(); setTab('video'); }; st.appendChild(b); }
  else { const b = el('button', 'btn w acc', state.comp.biblio === it ? '✓ Ya es la imagen a recrear' : '✨ Recrear esta imagen (Crear imagen)'); b.onclick = () => { closeGal(); addToImage('biblio', it, true); }; st.appendChild(b); const bv = el('button', 'btn w', '🎬 Añadir a Crear vídeo'); bv.onclick = () => { closeGal(); addToVideo('biblio', it); setTab('video'); }; st.appendChild(bv); if (!it.group) { const wb = withBtn('biblio', it); wb.onclick = () => { const sn = navSnap(); closeGal(); showCreationsWith('biblio', it, sn); }; st.appendChild(wb); } }
  host.appendChild(sec('Usar', st));
  if (it.prompt) { const pb = el('div', 'stack'); pb.appendChild(el('div', 'promptbox', atHtml(it.neutro || it.prompt))); const cp = el('button', 'btn w', 'Copiar prompt'); cp.onclick = () => { navigator.clipboard && navigator.clipboard.writeText(it.neutro || it.prompt); toast('Prompt copiado'); }; pb.appendChild(cp); host.appendChild(sec('Prompt', pb)); }
  if (vt) { const rows = []; if (it.ajustes) rows.push(['Ajustes', it.ajustes]); if (it.w) rows.push(['Tamaño', `${it.w} × ${it.h} px`]); if (it.dur) rows.push(['Duración', it.dur + ' s']); if (it.refs && it.refs.length) rows.push(['Referencias', it.refs.map(r => r.label).join(', ')]); if (rows.length) host.appendChild(sec('Datos', el('div', 'kv', rows.map(([k, v]) => `<span>${k}</span><b>${v}</b>`).join(''))));
    if (it.refs && it.refs.length) { const rr = el('div', 'refrow'); it.refs.forEach(r => { const d = el('div', 'ref', `<img src="${r.file}" alt=""><small>${r.label}</small>`); d.onclick = () => lightbox(r.file, r.label); rr.appendChild(d); }); host.appendChild(sec('Imágenes de referencia', rr)); } }
}
function recreateFromVideoteca(it) { // carga en Crear vídeo el prompt, las referencias y los ajustes que Max usó (parseados del callout de Notion)
  state.vpool = []; (it.refs || []).forEach((r, i) => poolAdd({ id: 'vtref:' + it.id + ':' + i, kind: 'image', name: r.label, src: r.file, thumb: r.file }, true));
  state.vprompt = (it.prompt || '').replace(/<<<image_(\d+)>>>/g, '@Image$1').replace(/@image_(\d+)/g, '@Image$1') || null; const a = it.ajustes || '';
  const md = a.match(/(\d+)\s*s\b/); if (md) { state.vdur = Math.max(4, Math.min(15, +md[1])); persist('am_vdur', state.vdur); } const mr = a.match(/(480p|720p|1080p|4k)/i); if (mr) { state.vres = mr[1].toLowerCase(); persist('am_vres', state.vres); } const ma = a.match(/\b(\d+:\d+)\b/); if (ma && V_ASPECTS.includes(ma[1])) { state.vaspect = ma[1]; persist('am_vaspect', ma[1]); } state.vaudio = !/sin audio/i.test(a); persist('am_vaudio', state.vaudio ? '1' : '0');
  vbadge(); setTab('video'); toast('Cargado en Crear vídeo: prompt, referencias y ajustes');
}
state.selset = state.selset || new Set();
function toggleSel(src, on) { if (on === undefined) on = !state.selset.has(src); if (on) state.selset.add(src); else state.selset.delete(src); [...rail.children].forEach(d => d.classList.remove('on')); [...rail.children].forEach(d => { if (d._it && d._it.src === src) { d.classList.toggle('sel', on); const c = d.querySelector('.ck'); if (c) c.classList.toggle('on', on); } }); selBar(); }
function clearSel() { state.selset.clear(); [...rail.children].forEach(d => { d.classList.remove('sel'); const c = d.querySelector('.ck'); if (c) c.classList.remove('on'); }); selBar(); }
function selBar() { let b = $('#selbar'); if (!b) { b = el('div', 'selbar'); b.id = 'selbar'; b.innerHTML = `<span id="selN"></span><button class="btn acc" id="selDl">⬇ Descargar</button><button class="btn del" id="selDel" title="Mover a la papelera">🗑</button><button class="btn" id="selX">✕</button>`; document.body.appendChild(b); $('#selX').onclick = clearSel; $('#selDl').onclick = downloadSel; $('#selDel').onclick = deleteSel; }
  const n = state.selset.size; b.classList.toggle('on', n > 0 && (state.tab === 'creaciones' || state.tab === 'crear' || state.tab === 'perfil')); $('#selN').textContent = n === 1 ? '1 imagen seleccionada' : `${n} seleccionadas`; }
async function deleteSel() { const files = [...state.selset].map(x => x.split('?')[0]); if (!files.length) return; if (!confirm(`¿Eliminar ${files.length} creación${files.length > 1 ? 'es' : ''}? Se mueven a assets/papelera.`)) return;
  let ok = 0; for (const f of files) { try { const r = await fetch('/api/borrar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ file: f }) }).then(x => x.json()); if (!r.error) ok++; } catch (e) {} }
  allItems().forEach(x => { if (x.live && files.includes(x.live.split('?')[0])) { x.live = null; state.done.delete(x.id); } }); TABS.video.items.forEach(x => { if (x.video && files.includes(x.video.split('?')[0])) x.video = null; });
  const keep = rail.scrollTop; clearSel(); toast(`${ok} eliminada${ok !== 1 ? 's' : ''} (papelera)`); refreshLive(); [0, 400, 900, 1500].forEach(ms => setTimeout(() => { if (ms) { renderRail(); renderSide(); } rail.scrollTop = keep; }, ms)); }
async function downloadSel() { const files = [...state.selset].map(x => x.split('?')[0]); if (!files.length) return; if (files.length === 1) { const a = document.createElement('a'); a.href = files[0]; a.download = files[0].split('/').pop(); document.body.appendChild(a); a.click(); a.remove(); return; }
  toast(`Preparando ${files.length} archivos…`); try { const r = await fetch('/api/zip', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ files }) }); if (!r.ok) throw new Error((await r.json()).error || r.status); const blob = await r.blob(); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'aria-studio-' + files.length + '.zip'; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 5000); } catch (e) { toast('No se pudo preparar el zip: ' + e.message); } }
// arrastrar en el hueco de la cuadrícula = seleccionar con un rectángulo
(function () { let start = null, box = null;
  rail.addEventListener('mousedown', e => { if (e.button !== 0 || !(state.tab === 'creaciones' || state.tab === 'crear' || state.tab === 'perfil')) return; if (e.target.closest('.cell') || e.target.closest('button')) return; start = { x: e.clientX, y: e.clientY }; e.preventDefault(); });
  document.addEventListener('mousemove', e => { if (!start) return; if (!box) { if (Math.hypot(e.clientX - start.x, e.clientY - start.y) < 6) return; box = el('div', 'marquee'); document.body.appendChild(box); }
    const x1 = Math.min(start.x, e.clientX), y1 = Math.min(start.y, e.clientY), x2 = Math.max(start.x, e.clientX), y2 = Math.max(start.y, e.clientY); Object.assign(box.style, { left: x1 + 'px', top: y1 + 'px', width: (x2 - x1) + 'px', height: (y2 - y1) + 'px' });
    [...rail.children].forEach(d => { if (!d._it || !d._it.src || d._it.pending) return; const r = d.getBoundingClientRect(); const hit = r.left < x2 && r.right > x1 && r.top < y2 && r.bottom > y1; if (hit !== state.selset.has(d._it.src)) toggleSel(d._it.src, hit); }); });
  document.addEventListener('mouseup', () => { if (box) box.remove(); box = null; start = null; });
})();
function showCreation(it) { // enseña una creación en la imagen grande (sin abrir el popup)
  const vid = $('#vid'); mirror.classList.remove('queue', 'errored'); setCompact(false);
  if (it.kind === 'video') { mirror.classList.add('vidmode', 'cached'); mirror.querySelector('.tag').textContent = 'vídeo · ' + ((it.meta || {}).model || 'Seedance 2.0'); if (vid.getAttribute('src') !== it.src) { vid.src = it.src; vid.load(); } vid.onloadedmetadata = () => { if (state.shown === it && vid.videoWidth) { arOverride = vid.videoWidth / vid.videoHeight; sizeMirror(); } }; vid.oncanplay = () => { if (state.shown === it) vid.play().catch(() => {}); }; vid.play().catch(() => {}); }
  else { mirror.classList.remove('vidmode'); vid.pause(); mirror.classList.remove('video'); mirror.classList.add('cached'); mirror.querySelector('.tag').textContent = 'creación · ' + ((it.meta || {}).model || 'API'); fitAr(it, it.src); showImage(it.src, false); }
  mirror.style.cursor = 'zoom-in'; mirror.title = 'Abrir en grande';
}
function compImage(k, it) { if (!it) return null; if (k === 'hair' && it._variant) return it._variant; if (k === 'vestidor') return it.ficha; if (k === 'biblio') return it.image; return it.files ? it.files.main : (it.thumb || null); }
function biblioWith(tab, it) { return (C.biblio || []).filter(b => b.compIds && b.compIds[tab] === it.id && !b.group).map(b => b._asCreation || (b._asCreation = { id: 'bib:' + b.id, name: b.name, kind: 'image', kindLabel: 'Imágenes', src: b.image, thumb: b.thumb, biblio: b, meta: { name: b.name, model: (b.ai || []).join(' · '), prompt: b.neutro || b.prompt, comp: b.comp || {}, compIds: b.compIds || {}, t: b.date ? Date.parse(b.date) / 1000 : 0, fototeca: true } })); }
function convWith(tab, it) { if (!it.conv || !CONVERT.has(tab)) return []; const src = it.conv.split('?')[0]; if (TABS.creaciones.items.some(c => c.src === src)) return []; return [it._asConv || (it._asConv = { id: 'conv:' + it.id, name: 'Prueba · ' + it.name, kind: 'image', kindLabel: 'Imágenes', src, thumb: src, conv: true, meta: { name: 'Prueba · ' + it.name, model: 'conversión de prueba', comp: { [COMP[tab]]: it.name }, compIds: { [tab]: it.id }, t: 0 } })]; }
function creationsWith(tab, it) { return TABS.creaciones.items.filter(c => !c.pending && !c.hidden && !isVarAux(c) && c.meta && resolveComp(c.meta)[tab] === it).concat(biblioWith(tab, it), convWith(tab, it)); }
state.navStack = state.navStack || [];
function navSnap() { return { tab: state.tab, filter: state.filter[state.tab], cfilt: state.cfilt, scroll: rail.scrollTop, gal: galIt, sel: state.sel[state.tab] }; }
function navBack() { // vuelve exactamente a donde estabas: pestaña, filtro, scroll y el popup que tenías abierto
  const sn = state.navStack.pop(); if (!sn) return false; state.cfilt = null; state._navving = true; try { setTab(sn.tab); } finally { state._navving = false; } state.cfilt = sn.cfilt; state.filter[sn.tab] = sn.filter; if (sn.sel) state.sel[sn.tab] = sn.sel; renderRail(); renderChips(); if (sn.tab !== 'creaciones' && sn.sel) renderSide();
  [0, 60, 300].forEach(ms => setTimeout(() => { rail.scrollTop = sn.scroll; }, ms)); if (sn.gal) setTimeout(() => openGal(sn.gal), 80); return true; }
function showCreationsWith(tab, it, snap) { showCreationsSel([{ tab, id: it.id, name: it.name }], tab, snap); }
function showCreationsSel(sel, back, snap) { if (!sel.length) return; state.navStack.push(snap || navSnap()); state.cfilt = { sel, back: back || 'creaciones', tab: sel[0].tab, id: sel[0].id, name: sel[0].name }; state.filter.creaciones = null; if (state.tab === 'creaciones') { renderRail(); renderChips(); rail.scrollTop = 0; } else { state._navving = true; try { setTab('creaciones'); } finally { state._navving = false; } rail.scrollTop = 0; } }
function selMatch(sel, item) { // ¿la creación lleva TODOS los componentes elegidos?
  if (item.biblio) { const ids = item.biblio.compIds || {}; return sel.every(x => ids[x.tab] === x.id); }
  if (item.conv) { const ids = (item.meta && item.meta.compIds) || {}; return sel.every(x => ids[x.tab] === x.id); }
  if (!item.meta) return false; const r = resolveComp(item.meta); return sel.every(x => r[x.tab] && r[x.tab].id === x.id);
}
function creationsSel(sel) { const base = TABS.creaciones.items.filter(c => !c.pending && !c.hidden && !isVarAux(c)); const extra = sel.length ? [].concat(...sel.map(x => { const ref = (TABS[x.tab].items || []).find(i => i.id === x.id); return ref ? biblioWith(x.tab, ref).concat(convWith(x.tab, ref)) : []; })) : []; const seen = new Set(); return base.concat(extra).filter(i => selMatch(sel, i) && !seen.has(i.id) && seen.add(i.id)); }
function clearCfilt(back) { if (navBack()) return; const b = state.cfilt && state.cfilt.back; state.cfilt = null; if (back && b) setTab(b); else { renderRail(); renderChips(); } }
function withBtn(tab, it) { const n = creationsWith(tab, it).length; const G = { vestidor: 'esta prenda', hair: 'este peinado', expr: 'esta expresión', photo: 'este efecto', movie: 'este movie look', cartoon: 'este estilo', biblio: 'esta imagen' }; const w = G[tab] || 'esto'; const b = el('button', 'btn w', n ? `🖼 Ver ${n} creaci${n === 1 ? 'ón' : 'ones'} con ${w}` : `🖼 Sin creaciones con ${w}`); b.disabled = !n; b.onclick = () => showCreationsWith(tab, it); return b; }
function resolveComp(m) { const out = {}; const ids = m.compIds || {}; Object.keys(COMP).forEach(k => { const list = TABS[k] ? TABS[k].items : []; let it = ids[k] ? list.find(x => x.id === ids[k]) : null; if (!it && m.comp && m.comp[COMP[k]]) it = list.find(x => x.name === m.comp[COMP[k]]); if (it) out[k] = it; }); return out; }
let galIt = null;
function slideRow(row) { const upd = () => row.classList.toggle('more', row.scrollLeft + row.clientWidth < row.scrollWidth - 4); row.onscroll = upd; row.onwheel = e => { if (Math.abs(e.deltaY) > Math.abs(e.deltaX) && row.scrollWidth > row.clientWidth) { e.preventDefault(); row.scrollLeft += e.deltaY; } }; requestAnimationFrame(upd); setTimeout(upd, 300); }
function hairVarColor(h) { if (h && state.hairCol) return state.hairCol.en + (state.hairCol.hex ? ' (' + state.hairCol.hex + ')' : ''); if (!h || !state.hairVar) return ''; const src = state.hairVar.split('?')[0]; const c = TABS.creaciones.items.find(i => i.src === src); return (c && c.meta && c.meta.color) || ''; }
function esc(t) { return String(t == null ? '' : t).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]); }
function inCrear(tab, it) { return state.comp[tab] === it && (tab !== 'hair' || (state.hairVar || null) === (it._variant || null)); }
function recHairVar(meta) { if (!meta) return null; if (meta.hairVariant) return meta.hairVariant; const r = (meta.refs || []).find(x => /^pelo_/.test(x)); return r ? 'assets/live/' + r : null; }
async function toggleFav(it) { it.fav = !it.fav; renderSide(); renderRail(); renderChips(); toast(it.fav ? `★ «${it.name}» en Favoritos` : `«${it.name}» fuera de Favoritos`);
  try { const r = await fetch('/api/prenda_fav', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: it.id, fav: it.fav }) }).then(x => x.json()); if (!r.ok) throw new Error(r.error || 'error'); } catch (e) { it.fav = !it.fav; renderSide(); renderRail(); renderChips(); toast('No se pudo guardar el favorito: ' + e.message); } }
function recSettings(meta) { // «Recrear» también carga el modelo, la calidad, el formato y el NSFW con los que se hizo
  if (!meta) return ''; const out = []; const mk = meta.model_key && MODELS.find(x => x.key === meta.model_key);
  const vale = id => id === 'aria' || (window.PJ && (PJ.list || []).some(p => p.id === id && p.ficha360));
  const fijo = WEBM() && meta.char === 'aria' && window.PJ && (PJ.list || []).some(p => p.ficha360);   // un miembro con personaje propio no pasa a tener a Aria de principal
  if (meta.char && meta.char !== CH().id && vale(meta.char) && !fijo) { setChar(meta.char, true); out.push(CH().name); } // se recrea con el personaje con el que se hizo
  extraChars(); state.extras = (meta.chars || []).filter(id => id !== CH().id && vale(id)); state.compBy = {}; saveExtras(); state.cfocus = CH().id;   // y solo con los personajes que llevaba esa imagen (antes se quedaban los añadidos de la última)
  if (window.accRestore) accRestore(meta.acc);   // con sus complementos
  if (mk) { modelKey = mk.key; persist('am_model', mk.key); out.push(mk.name); }
  const q = /alta|2k|4k|high/i.test(meta.quality || '') ? 'high' : meta.quality ? 'std' : null; if (q) { state.quality = q; persist('am_quality', q); out.push(q === 'high' ? 'calidad alta' : 'calidad estándar'); }
  if (meta.aspect && ASPECTS.includes(meta.aspect)) { state.aspect = meta.aspect; persist('am_aspect', meta.aspect); out.push(meta.aspect); }
  if (typeof meta.nsfw === 'boolean' && meta.tab === 'crear') { state.nsfw = meta.nsfw; persist('am_nsfw', meta.nsfw ? '1' : '0'); if (meta.nsfw) nsfwModel(); }
  return out.length ? ' · ' + out.join(' · ') : '';
}
function pplDelPrompt(m) { // creaciones anteriores a la v164: el reparto se saca del prompt («… must become X» / «X takes the place of …»); sin cajas, que se vuelven a buscar al abrir el reparto
  const t = String(m.prompt || ''); const out = []; const q = x => x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  (Array.isArray(m.chars) ? m.chars : []).forEach(id => { const nm = charInfo(id).name; if (!nm || charInfo(id).id !== id) return; const a = t.match(new RegExp('(?:: |; )(the [^;:.]*?) must become ' + q(nm) + '\\b', 'i')) || t.match(new RegExp(q(nm) + ' takes the place of (the [^:;]*?): ' + q(nm) + ' is the', 'i'));
    if (a && !/^the (first|second|third|fourth|fifth|sixth|next) person from the left$/i.test(a[1].trim())) out.push({ desc: a[1].trim(), char: id }); });
  return out; }
function recrear(it) { // carga en Crear imagen TODO lo de una creación (personajes, prenda, peinado, referencia, complementos, ajustes) y la enseña en grande, sin mover la lista de creaciones
  const m = it.meta || {}; const ya = state.tab === 'crear';
  state.comp = recComp(m); state.hairVar = recHairVar(m); state.hairCol = m.hairCol || null; const why = recSettings(m);
  { const fb = state.comp.biblio; if (fb && !fb.drop) { if (m.modoFoto) fb.modo = m.modoFoto === 'misma' ? 'swap' : 'prompt'; else delete fb.modo; }
    if (fb) { const pp = (Array.isArray(m.people) && m.people.length) ? m.people.map(p => Object.assign({}, p)) : pplDelPrompt(m); if (pp.length) fb.people = pp; else delete fb.people; } }   // el «¿Quién es quién?» con el que se hizo   // foto de la Fototeca: el mismo método con el que se hizo
  { const cu = C.crear.find(x => x.custom); if (cu && it.kind !== 'video' && it.src) { const sg = compSig(); cu._liveBy = cu._liveBy || {}; cu._liveBy[sg] = it.src; cu._promptSig = sg; cu._prompt = null; cu._last = it.src; cu._ar = null; state.done.add(cu.id); } }   // en grande, la imagen que se recrea
  badge();
  if (ya) { renderSide(); const c = cur(); if (c) paint(c, true); }   // ya en Crear imagen: la lista se queda donde estaba y la imagen no cambia de tamaño
  else { setTab('crear'); setTimeout(() => { try { if (rail._need) rail._need(it); keepAnchor(it, 60); } catch (e) {} }, 150); }   // viniendo de Creaciones: la lista de abajo se coloca en esa creación
  toast('Combinación cargada en Crear imagen' + why);
}
function recComp(meta) { // lo que carga «Recrear»: los componentes + la captura o imagen de internet original si se guardó
  const r = Object.assign({}, resolveComp(meta || {})); const p0 = ((meta && meta.refPaths) || [])[0] || '';
  const lienzo = meta && (meta.canvasRef || (p0.startsWith('assets/refs/') ? p0 : ''));   // la imagen de partida: la que guardó el servidor o, si no, la primera referencia cuando era una imagen subida
  if (!r.biblio && lienzo) r.biblio = { id: (meta.compIds && meta.compIds.biblio) || 'drop-' + Date.now(), name: (meta.comp && meta.comp[COMP.biblio]) || 'Tu foto', image: lienzo, thumb: lienzo, prompt: '', drop: true, tags: 'Tu foto', modo: meta.modoFoto === 'descripcion' ? 'prompt' : meta.modoFoto === 'misma' ? 'swap' : undefined, neutro: (meta.escena && meta.escena.d) || undefined, ropa: (meta.escena && meta.escena.r) || undefined, figura: (meta.escena && meta.escena.f) || undefined }; return r; }
const BG_AR = {}; function bgAr(src) { // proporción de la imagen de partida (se calcula una vez)
  const set = () => { if (state.tab === 'crear' && jobBg(cur()) === src && arOverride !== BG_AR[src]) { arOverride = BG_AR[src]; sizeMirror(); } };
  if (BG_AR[src]) return set(); const im = new Image(); im.onload = () => { BG_AR[src] = im.naturalWidth / im.naturalHeight; set(); }; im.src = src; }
function jobBg(it) { const js = [...JOBS.values()].filter(j => !j.end && j.it === it && j.bg); return js.length ? js[js.length - 1].bg : null; }
async function submitGen() { // un clic = una petición: el botón se bloquea hasta que la generación ha arrancado (se ve «Generando» en la imagen principal)
  if (state.submitting) return; state.submitting = true; renderSide();
  { const b = state.comp.biblio; if (state.tab === 'crear' && b && b._leyendo) { toast('Leyendo la foto… genero en cuanto termine'); try { await b._leyendo; } catch (e) {} } }
  try { await tryOn(false); } finally { state.submitting = false; renderSide(); } }
function flyToNav(src, r0, tab) { // la imagen «vuela» hasta el botón del menú y el contador rojo se enciende al llegar
  const nb = document.querySelector(`#nav button[data-tab="${tab}"]`); if (!nb || !r0 || !r0.width) { navBadges(); return; }
  const r1 = nb.getBoundingClientRect(); const f = document.createElement('img'); f.src = src; f.className = 'flyimg';
  Object.assign(f.style, { left: r0.left + 'px', top: r0.top + 'px', width: r0.width + 'px', height: r0.height + 'px' }); document.body.appendChild(f);
  const dx = r1.left + r1.width / 2 - (r0.left + r0.width / 2), dy = r1.top + r1.height / 2 - (r0.top + r0.height / 2), sc = 36 / Math.max(r0.width, r0.height);
  f.animate([{ transform: 'translate(0,0) scale(1)', opacity: 1, borderRadius: '16px' }, { transform: `translate(${dx * 0.55}px,${dy * 0.35 - 60}px) scale(${(1 + sc) / 2.4})`, opacity: 1, offset: 0.55 }, { transform: `translate(${dx}px,${dy}px) scale(${sc})`, opacity: 0.2, borderRadius: '50%' }], { duration: 750, easing: 'cubic-bezier(.5,0,.3,1)', fill: 'forwards' })
    .onfinish = () => { f.remove(); navBadges(); nb.animate([{ transform: 'scale(1)' }, { transform: 'scale(1.18)' }, { transform: 'scale(1)' }], { duration: 320, easing: 'ease-out' }); };
}
function navBadges() { // contador rojo en Vestidor mientras hay fichas de prenda generándose
  const nb = document.querySelector('#nav button[data-tab="vestidor"]'); if (!nb) return; let b = nb.querySelector('.bdv'); if (!b) { b = el('span', 'bdv'); nb.appendChild(b); }
  const n = (TABS.vestidor.items || []).filter(i => i.pending).length; b.textContent = n; b.classList.toggle('on', n > 0); }
setInterval(() => { if (document.querySelector('#nav button[data-tab="vestidor"] .bdv.on') || (TABS.vestidor.items || []).some(i => i.pending)) navBadges(); }, 1500);
function isVarAux(i) { const m = i.meta || i; return !!(m.hairVar || m.variaciones || m.personaje); }
function galList() { if (state.galGroup) return state.galGroup; if (galIt && galIt.meta && COMP[state.tab]) return TABS.creaciones.items.filter(i => !i.pending && !i.hidden && !isVarAux(i)); if (state.tab === 'biblio') return view().filter(i => !i.group); if (state.tab === 'videoteca' || COMP[state.tab]) return view(); return (state.tab === 'creaciones' || state.tab === 'video' || state.tab === 'crear' ? view() : TABS.creaciones.items.filter(i => !i.hidden && !isVarAux(i))).filter(i => !i.pending); }
function openGal(it) {
  galIt = it; const g = $('#gal'), im = $('#galImg'), vd = $('#galVid'); const list = galList(); const i = list.indexOf(it);
  $('#galN').textContent = `${i + 1} / ${list.length}`; $('#galPrev').disabled = list.length < 2; $('#galNext').disabled = list.length < 2; galZoomReset();
  $('.galmedia').classList.toggle('isvideo', it.kind === 'video'); if (it.kind === 'video' && galTimer) galPlay(false);
  if (it.kind === 'video') { im.style.display = 'none'; vd.style.display = ''; vd.muted = false; if (state.tab === 'videoteca') applySound(vd); if (vd.getAttribute('src') !== it.src) vd.src = it.src; vd.play().catch(() => {}); }
  else { vd.pause(); vd.style.display = 'none'; im.style.display = ''; im.src = (COMP[state.tab] && state.tab !== 'biblio' && !it.meta) ? (state.tab === 'vestidor' ? it.ficha : (state.tab === 'hair' && state.galGroup ? it.files.main : compImage(state.tab, it))) : (it.src || it.image); hiSwap(im, im.getAttribute('src')); }
  if ((state.tab === 'biblio' || state.tab === 'videoteca' || COMP[state.tab]) && !it.meta) libMeta(it, $('#galSide')); else creationMeta(it, $('#galSide')); g.classList.add('on'); requestAnimationFrame(() => { $('.galmedia').style.setProperty('--galnw', $('#galN').offsetWidth + 'px'); });
}
function closeGal() { const gm_ = document.querySelector('.galmedia'); if (gm_ && gm_.classList.contains('galfs')) { gm_.classList.remove('galfs'); $('#gzReset').textContent = '⛶'; } state.galGroup = null; $('#gal').classList.remove('on'); $('#galVid').pause(); galIt = null; galPlay(false); }
let galTimer = 0;
function galPlay(on) { if (on === undefined) on = !galTimer; clearInterval(galTimer); galTimer = 0; if (on) galTimer = setInterval(() => galStep(1), 4000); $('#galPlay').textContent = galTimer ? '❚❚' : '▶'; $('#galPlay').classList.toggle('on', !!galTimer); }
$('#galPlay').onclick = e => { e.stopPropagation(); galPlay(); };
const GZ = { s: 1, x: 0, y: 0 };
function galZoomApply() { [$('#galImg'), $('#galVid')].forEach(e => { e.style.transform = GZ.s > 1 ? `translate(${GZ.x}px,${GZ.y}px) scale(${GZ.s})` : ''; }); $('#gzRange').value = GZ.s; $('.galmedia').classList.toggle('zoomed', GZ.s > 1); }
function galZoomReset() { GZ.s = 1; GZ.x = 0; GZ.y = 0; galZoomApply(); }
function galZoomTo(s, cx, cy) { const box = $('.galmedia').getBoundingClientRect(); const ns = Math.max(1, Math.min(6, s)); if (cx != null) { const px = cx - box.left - box.width / 2, py = cy - box.top - box.height / 2; GZ.x = px - (px - GZ.x) * (ns / GZ.s); GZ.y = py - (py - GZ.y) * (ns / GZ.s); } GZ.s = ns; if (GZ.s === 1) { GZ.x = 0; GZ.y = 0; } galZoomApply(); }
$('.galmedia').addEventListener('wheel', e => { if (e.target.closest('.galzoom')) return; e.preventDefault(); galZoomTo(GZ.s * (e.deltaY < 0 ? 1.05 : 1 / 1.05), e.clientX, e.clientY); }, { passive: false });
$('#gzRange').oninput = e => galZoomTo(+e.target.value); $('#gzIn').onclick = () => galZoomTo(GZ.s * 1.25); $('#gzOut').onclick = () => galZoomTo(GZ.s / 1.25); $('#gzReset').onclick = () => { const gm = $('.galmedia'); const fsBtn = on => { $('#gzReset').textContent = on ? '✕' : '⛶'; $('#gzReset').title = on ? 'Salir de pantalla completa' : 'Pantalla completa'; };
    if (document.fullscreenElement) { document.exitFullscreen(); return; } if (gm.classList.contains('galfs')) { gm.classList.remove('galfs'); fsBtn(false); galZoomReset(); return; }
    const fb = () => { gm.classList.add('galfs'); fsBtn(true); galZoomReset(); }; // si el navegador no deja pantalla completa real, ocupa toda la ventana
    let done = false; const fb2 = () => { if (!done && !document.fullscreenElement) { done = true; fb(); } }; try { const p = (gm.requestFullscreen || gm.webkitRequestFullscreen).call(gm); if (p && p.then) p.then(() => { done = true; }, fb2); } catch (e) { fb2(); } setTimeout(fb2, 500); }; document.addEventListener('fullscreenchange', () => { const on = !!document.fullscreenElement; $('#gzReset').textContent = on ? '✕' : '⛶'; $('#gzReset').title = on ? 'Salir de pantalla completa' : 'Pantalla completa'; galZoomReset(); });
(function () { let drag = null; const gm = $('.galmedia');
  gm.addEventListener('mousedown', e => { if (GZ.s <= 1 || e.button !== 0 || e.target.closest('button') || e.target.closest('.galzoom')) return; drag = { x: e.clientX - GZ.x, y: e.clientY - GZ.y }; gm.classList.add('dragging'); e.preventDefault(); });
  document.addEventListener('mousemove', e => { if (!drag) return; GZ.x = e.clientX - drag.x; GZ.y = e.clientY - drag.y; galZoomApply(); });
  document.addEventListener('mouseup', () => { drag = null; gm.classList.remove('dragging'); });
})();
function galStep(d) { const list = galList(); if (!list.length) return; const i = (list.indexOf(galIt) + d + list.length) % list.length; if (state.galGroup) { openGal(list[i]); return; } if ((state.tab === 'biblio' || state.tab === 'videoteca' || COMP[state.tab]) && !list[i].meta) { state.sel[state.tab] = list[i]; if (COMP[state.tab] && state.tab !== 'biblio') { paint(list[i], true); renderSide(); } } else if (list[i].meta) state.sel.creaciones = list[i]; else state.sel.creaciones = list[i]; [...rail.children].forEach(x => x.classList.toggle('on', x._it === list[i])); openGal(list[i]); }
$('#galPrev').onclick = () => galStep(-1); $('#galNext').onclick = () => galStep(1); $('#galX').onclick = closeGal; $('#gal').onclick = e => { if (e.target === $('#gal')) closeGal(); };
function syncMini() { // la vista previa del panel izquierdo enseña lo mismo que enseñaría la imagen grande
  const m = $('#miniImg'); if (!m) return; const it = cur(); const src = state.lastSrc || layers[front].getAttribute('src') || ''; if (src && m.getAttribute('src') !== src) m.src = src;
  const st = $('#miniState'); const jb = it && jobFor(it); if (jb) { st.textContent = `⏳ Generando «${it.name}»…`; st.style.display = ''; } else if (it && it._err) { st.textContent = '✕ ' + (errCreditos(it._err) ? 'No hay suficientes créditos' : it._err); st.style.display = ''; st.classList.add('err'); } else { st.style.display = 'none'; st.classList.remove('err'); }
  const tg = $('#miniTag'); if (tg) { const txt = mirror.querySelector('.tag').textContent; tg.textContent = txt; tg.style.display = txt && mirror.classList.contains('cached') ? '' : 'none'; }
}
function miniPreview(it) {
  const w = el('div', 'mini'); w.innerHTML = `<img id="miniImg" alt=""><span class="tag" id="miniTag"></span><div class="mstate" id="miniState"></div>`;
  w.onclick = () => { if (jobFor(it)) return; if (state.tab === 'hair') { const vs = hairVariants(it); if (vs.length) { state.galGroup = [it, ...vs]; const cur_ = it._variant ? vs.find(v => v.src === it._variant.split('?')[0]) || it : it; openGal(cur_); return; } } const src = (state.lastSrc || '').split('?')[0]; const c = src && TABS.creaciones.items.find(x => !x.pending && x.src === src); if (c && COMP[state.tab] && state.tab !== 'biblio') { state.sel.creaciones = c; openGal(c); return; } if (state.tab === 'biblio' || COMP[state.tab]) { openGal(it); return; } if (c) { state.sel.creaciones = c; openGal(c); } else if (src) lightbox(src, it.name); };
  if (state.tab === 'biblio') w.classList.add('full');
  w.title = 'Ver en grande'; return w;
}
const ym = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
state.calM = state.calM || ym(new Date());
async function renderProfile() { // Perfil: sin calendario; de momento la ficha 360 del personaje (aquí irá el creador de personajes)
  const host = $('#profcard'); const P = C.perfil;
  host.innerHTML = `<div class="profx"><div class="profx-hd"><small>Ficha 360</small><b>${P.name}</b></div><img src="${P.ficha}" alt="Ficha 360 de ${P.name}"></div>`;
  host.querySelector('img').onclick = () => lightbox(P.ficha, 'Ficha 360 · ' + P.name);
}

function renderProfileOld() { // ficha tipo red social a la derecha del giro 360
  const P = C.perfil, D = P.datos || {}, ig = P.ig || {}; const host = $('#profcard'); host.innerHTML = '';
  const card = el('div', 'pc');
  card.innerHTML = `<div class="pc-head"><img src="${P.avatar || C.base.thumb}" alt=""><div><h2>${P.name}</h2><div class="pc-h">${P.handle || ''}</div><div class="pc-t">${P.tagline || ''}</div></div></div>
    <div class="pc-stats">${ig.posts != null ? `<div><b>${ig.posts}</b><small>posts</small></div>` : ''}${ig.followers ? `<div><b>${ig.followers}</b><small>seguidores</small></div>` : ''}<div><b>${state.totalN || 0}</b><small>generadas aquí</small></div></div>
    <p class="pc-bio">${P.bio || ''}</p>
    <dl class="pc-dl">
      ${[['Edad', D.edad], ['Altura', D.altura], ['Origen', D.origen], ['Idiomas', D.idiomas], ['Nacida', D.nacida]].filter(x => x[1]).map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}
    </dl>
    ${D.rasgos ? `<div class="pc-sec"><h4>Rasgos fijos</h4><div class="pc-chips">${D.rasgos.map(r => `<span>${r}</span>`).join('')}</div></div>` : ''}
    ${D.personalidad ? `<div class="pc-sec"><h4>Personalidad</h4><p>${D.personalidad}</p></div>` : ''}
    ${D.voz ? `<div class="pc-sec"><h4>Voz y cadencia</h4><p>${D.voz}</p></div>` : ''}
    ${D.mision ? `<div class="pc-sec"><h4>Historia</h4><p>${D.mision}</p></div>` : ''}
    ${D.contenido ? `<div class="pc-sec"><h4>Contenido</h4><p>${D.contenido}</p></div>` : ''}
    ${D.redes ? `<div class="pc-sec"><h4>Redes</h4><dl class="pc-dl">${D.redes.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl></div>` : ''}`;
  host.appendChild(card);
}
(function () { try { if (localStorage.getItem('am_theme') !== 'light') document.documentElement.classList.add('dark'); } catch (e) { document.documentElement.classList.add('dark'); } const b = document.getElementById('themeBtn'); const sync = () => { b.textContent = document.documentElement.classList.contains('dark') ? '☀' : '☾'; }; sync(); b.onclick = () => { const on = document.documentElement.classList.toggle('dark'); persist('am_theme', on ? 'dark' : 'light'); sync(); }; })();
// perfil editable: clic en un dato → se edita ahí mismo; al salir se guarda. Prompt base ↔ datos se sincronizan solos (Gemini, céntimos)
const COPY_SVG = '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="12" height="12" rx="2.5"/><path d="M5 15H4.5A1.5 1.5 0 0 1 3 13.5v-9A1.5 1.5 0 0 1 4.5 3h9A1.5 1.5 0 0 1 15 4.5V5"/></svg>';
const CHECK_SVG = '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>';
const pathGet = (o, k) => k.split('.').reduce((a, x) => (a || {})[x], o);
async function postJ(url, body) { let r; try { r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; } if (!r || !r.ok) { toast('No se pudo: ' + (r ? r.error : 'sin respuesta')); return null; } return r; }
const editing = () => document.activeElement && document.activeElement.classList.contains('edin');
function igNum(t) { const m = String(t || '').trim().replace(/\s/g, '').match(/^([\d.,]+)([KMB])?$/i); if (!m) return null; const u = (m[2] || '').toUpperCase(); let n = m[1]; if (!u && /^\d{1,3}([.,]\d{3})+$/.test(n)) n = n.replace(/[.,]/g, ''); else n = n.replace(',', '.'); const v = parseFloat(n); return isNaN(v) ? null : Math.round(v * (u === 'K' ? 1e3 : u === 'M' ? 1e6 : u === 'B' ? 1e9 : 1)); }   // «11.6K» → 11600
async function igSync(owner, url, avisar) { // seguidores y publicaciones de su Instagram, leídos de la página pública del perfil
  let r; try { r = await fetch('/api/ig', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url }) }).then(x => x.json()); } catch (e) { r = { error: 'sin respuesta' }; }
  if (!r || !r.ok) { if (avisar) toast((r && r.error) || 'No se ha podido leer Instagram'); return; }
  const mia = String((((owner ? (window.pjPerfil ? pjPerfil() : {}) : C.perfil) || {}).ig || {}).followers || '').trim(); const a = igNum(mia), b = igNum(r.followers); const u = /[KMB]$/i.test(r.followers) && !/[.,]/.test(r.followers) ? b / parseFloat(r.followers) : 0;
  const fo = (u && a != null && a !== b && Math.round(a / u) * u === b) ? mia : r.followers;   // la tuya es la misma cifra, con más detalle
  await profSave({ 'ig.followers': fo, 'ig.posts': r.posts }, owner); toast(fo !== r.followers ? `Instagram solo da la cifra redondeada (${r.followers}): se queda la tuya, ${fo} · ${r.posts} publicaciones` : `Instagram: ${r.followers} seguidores · ${r.posts} publicaciones`);
}
function profEdit(node, key, opts = {}) {
  if (WEBM() && !opts.owner) return;   // la ficha de Aria es fija para los miembros
  node.classList.add('ed'); node.title = 'Clic para editar'; if (!node.textContent.trim()) { node.classList.add('edph'); node.dataset.ph = opts.ph || '＋ Añadir'; }
  node.onclick = () => { if (node.querySelector('input,textarea')) return; node.classList.remove('edph'); const src = opts.owner && window.pjPerfil ? pjPerfil() : C.perfil; const val = String((key === 'basePrompt' ? src.basePrompt : pathGet(src, key)) || ''); const inp = el(opts.multi ? 'textarea' : 'input', 'pjin edin'); inp.value = val; if (opts.multi) inp.rows = Math.max(3, Math.min(14, Math.ceil(val.length / 34) + 1));
    node.innerHTML = ''; node.appendChild(inp); inp.focus(); try { inp.setSelectionRange(inp.value.length, inp.value.length); } catch (e) {}
    let done = false; const fin = async save => { if (done) return; done = true; const v = inp.value.trim(); if (!save || v === val.trim()) { renderSide(); return; } await profSave({ [key]: v }, opts.owner); if (key === 'ig.url' && v) igSync(opts.owner, v); };
    inp.onblur = () => fin(true); inp.onkeydown = e => { if (e.key === 'Escape') { e.preventDefault(); done = true; renderSide(); } else if (e.key === 'Enter' && (!opts.multi || e.metaKey || e.ctrlKey)) { e.preventDefault(); inp.blur(); } }; };
}
async function profSave(set, owner) {
  if (owner) { const ok = window.pjSetPerfil && await pjSetPerfil(owner, set); toast(ok ? 'Guardado' : 'No se pudo guardar'); if (!editing()) renderSide(); return; }
  const r = await postJ('/api/perfil', { action: 'set', set }); if (!r) { renderSide(); return; } Object.assign(C.perfil, r.perfil); if (!editing()) renderSide(); toast('Guardado'); const k = Object.keys(set)[0];
  if (k === 'basePrompt') profSync('prompt'); else if (/^datos\.(edad|altura|origen|rasgos)$/.test(k) && C.perfil.basePrompt) profSync('datos'); }
async function profSync(from) { state.profSync = from; if (!editing()) renderSide(); const r = await postJ('/api/perfil', { action: 'sync', from }); state.profSync = null; if (r) { Object.assign(C.perfil, r.perfil); const n = { 'datos.edad': 'edad', 'datos.altura': 'altura', 'datos.origen': 'origen', 'datos.rasgos': 'rasgos' };
    if (r.changed.length) toast(from === 'prompt' ? 'Datos actualizados con el prompt: ' + r.changed.map(k => n[k] || k).join(', ') : 'Prompt base actualizado con sus datos'); else toast(from === 'prompt' ? 'Sus datos ya encajan con el prompt' : 'El prompt base ya encajaba con sus datos'); }
  if (state.tab === 'perfil' && !editing()) renderSide(); }
// foto de perfil de Aria: subir, arrastrar o pegar, elegir de sus creaciones o traerla de Instagram; se encuadra en un círculo
function openAvatar(owner) {
  if (WEBM() && !owner) return;   // la foto de Aria no la cambian los miembros
  const P = owner && window.pjPerfil ? Object.assign({}, pjPerfil(), { avatarSrc: (q => { const b = x => (x || '').split('?')[0]; return (q.avatarSrc && b(q.avatarSrc) !== b(q.foto)) ? q.avatarSrc : (q.ficha360 || q.foto); })((window.PJ && PJ.list.find(x => x.id === owner)) || {}) }) : C.perfil; const A = { src: P.avatarSrc || P.avatar || P.ficha, crop: Object.assign({ z: 1, x: 0.5, y: 0.5 }, P.avatarCrop || {}), data: null, saving: false };
  let m0 = $('#avm'); if (m0) m0.remove(); m0 = el('div', 'fxm'); m0.id = 'avm'; document.body.appendChild(m0); const close = () => m0.remove(); m0.onclick = e => { if (e.target === m0) close(); };
  const toJpg = src => new Promise((res, rej) => { const im = new Image(); im.crossOrigin = 'anonymous'; im.onload = () => { const k = Math.min(1, 1600 / Math.max(im.naturalWidth, im.naturalHeight)); const cv = document.createElement('canvas'); cv.width = Math.round(im.naturalWidth * k); cv.height = Math.round(im.naturalHeight * k); cv.getContext('2d').drawImage(im, 0, 0, cv.width, cv.height); res(cv.toDataURL('image/jpeg', 0.92)); }; im.onerror = () => rej(new Error('no se pudo abrir')); im.src = src; });
  const use = async du => { try { A.data = await toJpg(du); A.src = A.data; A.crop = { z: 1, x: 0.5, y: 0.35 }; paint(); } catch (e) { toast('No se pudo abrir esa imagen'); } };
  const useUrl = async url => { if (/^data:image\//.test(url)) return use(url); if (!/^https?:\/\//i.test(url)) return; toast('Descargando la imagen…'); try { const j = await fetch('/api/fetch?url=' + encodeURIComponent(url)).then(r => r.json()); if (j.error) throw new Error(j.error); use(j.data); } catch (e) { toast('No se pudo descargar: guárdala y arrástrala desde el ordenador'); } };
  const onPaste = e => { if (!document.getElementById('avm')) { document.removeEventListener('paste', onPaste); return; } const it = [...(e.clipboardData || {}).items || []].find(x => x.type.startsWith('image/')); if (it) { const f = it.getAsFile(); const r = new FileReader(); r.onload = () => use(r.result); r.readAsDataURL(f); e.preventDefault(); return; } const t = (e.clipboardData.getData('text') || '').trim(); if (/^https?:\/\/.+\.(jpe?g|png|webp)|cdninstagram|fbcdn/i.test(t)) useUrl(t); };
  document.addEventListener('paste', onPaste);
  async function save() {
    const im = m0.querySelector('.avvp img'); if (!im || !im.naturalWidth) return; const cr = A.crop; const S = 512, cv = document.createElement('canvas'); cv.width = cv.height = S; const nw = im.naturalWidth, nh = im.naturalHeight, side = Math.min(nw, nh) / cr.z; cv.getContext('2d').drawImage(im, cr.x * nw - side / 2, cr.y * nh - side / 2, side, side, 0, 0, S, S);
    A.saving = true; paint();
    if (owner) { const ok = window.pjSaveAvatar && await pjSaveAvatar(owner, cv.toDataURL('image/jpeg', 0.92), A.data); A.saving = false; if (!ok) { toast('No se pudo guardar'); paint(); return; } close(); if (window.PJ) { const q = PJ.list.find(x => x.id === owner); if (q && C.chars) { const c0 = C.chars.find(c => c.id === owner); if (c0) c0.avatar = q.avatar; } } renderSide(); renderProfile(); toast('Foto de perfil guardada'); return; }
    const r = await postJ('/api/perfil', { action: 'avatar', data: cv.toDataURL('image/jpeg', 0.92), src: A.data || (A.src || '').split('?')[0], crop: cr }); A.saving = false; if (!r) { paint(); return; }
    Object.assign(C.perfil, r.perfil); if (C.chars && C.chars[0]) C.chars[0].avatar = C.perfil.avatar; const ci = $('#charImg'); if (ci) ci.src = C.perfil.avatar; close(); buildNav(); renderSide(); if (state.tab === 'perfil') renderProfile(); toast('Foto de perfil guardada');
  }
  function paint() {
    m0.innerHTML = ''; const box = el('div', 'fxbox accbox avbox');
    const media = el('div', 'fxmedia accmedia'); const vp = el('div', 'accvp avvp'); const im = document.createElement('img'); im.src = A.src; im.draggable = false; vp.appendChild(im); vp.appendChild(el('div', 'avring')); media.appendChild(vp);
    const cr = A.crop; const place = () => { const W = vp.clientWidth, nw = im.naturalWidth, nh = im.naturalHeight; if (!nw) return; const sc = W / Math.min(nw, nh) * cr.z; im.style.width = nw * sc + 'px'; im.style.height = nh * sc + 'px'; im.style.left = (W / 2 - cr.x * nw * sc) + 'px'; im.style.top = (W / 2 - cr.y * nh * sc) + 'px'; };
    im.onload = place; if (im.complete) setTimeout(place, 0);
    let drag = null; vp.onmousedown = e => { drag = { x: e.clientX, y: e.clientY, cx: cr.x, cy: cr.y }; e.preventDefault(); };
    window.onmousemove = e => { if (!drag) return; const sc = vp.clientWidth / Math.min(im.naturalWidth, im.naturalHeight) * cr.z; cr.x = Math.min(1, Math.max(0, drag.cx - (e.clientX - drag.x) / (im.naturalWidth * sc))); cr.y = Math.min(1, Math.max(0, drag.cy - (e.clientY - drag.y) / (im.naturalHeight * sc))); place(); };
    window.onmouseup = () => { drag = null; };
    const zr = document.createElement('input'); zr.type = 'range'; zr.min = 1; zr.max = 6; zr.step = 0.02; zr.value = cr.z; zr.className = 'acczoom'; zr.oninput = () => { cr.z = +zr.value; place(); };
    vp.onwheel = e => { e.preventDefault(); cr.z = Math.min(6, Math.max(1, cr.z * (e.deltaY < 0 ? 1.06 : 0.94))); zr.value = cr.z; place(); };
    const tools = el('div', 'acctools'); tools.appendChild(el('small', '', 'Arrastra para centrarla · rueda o barra para acercar')); tools.appendChild(zr); media.appendChild(tools);
    media.appendChild(el('div', 'accdrop', '<b>Suelta la foto aquí</b><small>de tu ordenador o de otra web</small>'));
    let dn = 0; media.ondragenter = e => { e.preventDefault(); dn++; media.classList.add('accover'); }; media.ondragover = e => { e.preventDefault(); }; media.ondragleave = () => { dn = Math.max(0, dn - 1); if (!dn) media.classList.remove('accover'); };
    media.ondrop = e => { e.preventDefault(); dn = 0; media.classList.remove('accover'); const dt = e.dataTransfer; const f = dt.files && [...dt.files].find(x => x.type.startsWith('image/')); if (f) { const r = new FileReader(); r.onload = () => use(r.result); r.readAsDataURL(f); return; } let url = dt.getData('text/uri-list') || dt.getData('text/plain') || ''; const mm = (dt.getData('text/html') || '').match(/<img[^>]+src=["']([^"']+)["']/i); if (mm) url = mm[1]; useUrl(url.trim()); };
    box.appendChild(media);
    const side = el('div', 'fxside accside'); const x = el('button', 'galx', '×'); x.title = 'Cerrar sin guardar'; x.onclick = close; box.appendChild(x);
    const acts = el('div', 'fxacts accacts top'); const sv = el('button', 'btn acc', A.saving ? '⏳ Guardando…' : '✓ Guardar'); sv.disabled = A.saving; sv.onclick = save; const cn = el('button', 'btn', 'Cancelar'); cn.onclick = close; acts.appendChild(sv); acts.appendChild(cn); side.appendChild(acts);
    side.appendChild(el('div', 'fxtitle', `<small>Foto de perfil</small><b>${esc(P.name)}</b><p>Sale en el menú, en «Mis personajes» y en el selector de personaje.</p>`));
    const fld = (t, node, sub) => { const g = el('div', 'fxsec'); g.appendChild(el('h4', '', t + (sub ? `<small>${sub}</small>` : ''))); g.appendChild(node); side.appendChild(g); };
    { const w = el('div', 'stack'); const up = el('label', 'btn', '🖼 Subir una foto'); const f = document.createElement('input'); f.type = 'file'; f.accept = 'image/*'; f.hidden = true; up.appendChild(f); f.onchange = () => { const file = f.files[0]; if (!file) return; const r = new FileReader(); r.onload = () => use(r.result); r.readAsDataURL(file); }; w.appendChild(up); fld('Desde tu ordenador', w, 'o arrástrala a la izquierda, o pégala con ⌘V'); }
    { const g = el('div', 'avgrid'); (TABS.creaciones.items || []).filter(it => it.kind !== 'video' && !it.hidden && (it.thumb || it.src)).slice(0, 48).forEach(it => { const b = el('button', 'avpick', `<img src="${it.thumb || it.src}" alt="" loading="lazy">`); b.title = it.name || ''; b.onclick = () => use(it.src || it.thumb); g.appendChild(b); }); if (!g.children.length) g.appendChild(el('small', 'pjnote', 'Todavía no hay creaciones.')); fld('De tus creaciones', g, 'pulsa una y la centras a la izquierda'); }
    { const w = el('div', 'stack'); const inp = el('input', 'pjin'); inp.placeholder = 'https://www.instagram.com/tu_usuario/'; inp.value = (P.ig && P.ig.url) || ''; const b = el('button', 'btn', '↗ Abrir su perfil de Instagram'); b.onclick = () => { const u = inp.value.trim(); if (!/instagram\.com\//i.test(u)) { toast('Pega el enlace de su perfil de Instagram'); return; } window.open(u, '_blank', 'noopener'); if (!owner && (!P.ig || P.ig.url !== u)) postJ('/api/perfil', { action: 'set', set: { 'ig.url': u } }).then(r => { if (r) Object.assign(C.perfil, r.perfil); }); };
      w.appendChild(inp); w.appendChild(b); w.appendChild(el('small', 'pjnote', 'Instagram no deja leer la foto sin iniciar sesión. Se abre su perfil: arrastra su foto de perfil hasta el círculo de la izquierda (o haz clic derecho, «Copiar imagen» y pégala aquí con ⌘V).')); fld('Desde Instagram', w); }
    box.appendChild(side); m0.appendChild(box);
  }
  paint();
}
function rasgosNode(list, editable, owner) {
  const ch = el('div', 'pc-chips' + (editable ? ' edchips' : '')); list.forEach((r, i) => { const s0 = el('span', '', esc(r)); if (editable) { const x = el('button', 'chx', '×'); x.title = 'Quitar'; x.onclick = () => profSave({ 'datos.rasgos': list.filter((_, k) => k !== i) }, owner); s0.appendChild(x); } ch.appendChild(s0); });
  if (editable) { const ad = el('button', 'chadd', '＋'); ad.title = 'Añadir un rasgo'; ad.onclick = () => { const inp = el('input', 'pjin edin chin'); inp.placeholder = 'Nuevo rasgo'; ad.replaceWith(inp); inp.focus(); let done = false; const fin = s1 => { if (done) return; done = true; const v = inp.value.trim(); if (s1 && v) profSave({ 'datos.rasgos': list.concat([v]) }, owner); else renderSide(); }; inp.onblur = () => fin(true); inp.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); inp.blur(); } if (e.key === 'Escape') { e.preventDefault(); fin(false); } }; }; ch.appendChild(ad); }
  return ch;
}
function renderSide() {
  side.querySelectorAll('video').forEach(v => { try { v.pause(); v.removeAttribute('src'); v.load(); } catch (e) {} });   // que ningún vídeo del panel siga sonando tras re-pintar
  const t = TABS[state.tab], it = cur(); side.innerHTML = '';
  if (state.pick && state.tab === state.pick.tab && it) { pickPanel(it); return; }
  if (!it && state.tab !== 'perfil') { side.appendChild(sec(t.label, el('div', 'status', state.tab === 'creaciones' ? 'Todavía no hay nada generado con la API. Lo que generes en cualquier sección aparecerá aquí con su modelo, calidad, formato, coste y prompt.' : 'No hay elementos.'))); return; }
  if (state.back && COMP[state.tab]) { const bb = el('button', 'btn backbtn', '← Volver a ' + (state.back === 'video' ? 'Crear vídeo' : 'Crear imagen')); bb.onclick = () => setTab(state.back); side.appendChild(bb); }
  if (state.tab === 'biblio' || state.tab === 'videoteca') { /* la IA y la fecha van debajo de la imagen/vídeo */ }
  else if (state.tab !== 'perfil' && state.tab !== 'video' && !(state.tab === 'vestidor' && LIVE) && !(state.tab === 'crear' && it.custom && LIVE)) { const head = el('div', 'sec'); head.appendChild(el('div', 'big', it.name)); head.appendChild(el('div', 'status', `<b>${t.base}</b> · ${t.sub(it)}`)); side.appendChild(head); if (GALLERY_TABS.has(state.tab) && state.tab !== 'creaciones' && !LIVE) { side.appendChild(miniPreview(it)); setTimeout(syncMini, 0); } }
  if (state.tab === 'perfil') {
    if (window.pjWizSide && pjWizSide(side)) return;
    if (WEBM() && window.PJ && PJ.sel === 'nuevo') { const v = el('div', 'profile'); v.appendChild(el('div', 'profvacio', '<span>👤</span><b>Tu personaje</b><small>Aquí aparecerá su ficha: su foto, sus rasgos, su personalidad, su voz y su prompt base. Empieza creándolo a la derecha.</small>')); side.appendChild(sec('', v)); return; }   // web, cuenta sin personaje propio: el panel no enseña el de Aria
    const P = window.pjPerfil ? pjPerfil() : C.perfil; const ig = P.ig || {}; const box = el('div', 'profile');
    const isAria = P === C.perfil; const own = isAria ? null : P.id; const hl = el('div', 'profhl'); box.appendChild(hl); // todos los personajes con el mismo panel que Aria
    const head = el('div', 'head', `${P.avatar ? `<span class="avwrap"><img src="${P.avatar}" alt=""><i>✎</i></span>` : `<span class="avwrap"><span class="pjav0">${(P.name || '?')[0]}</span><i>✎</i></span>`}<div><b>${esc(P.name)}</b><small>${esc(P.handle || '')}</small><small>${esc(P.tagline || '')}</small></div>`); const aw = head.querySelector('.avwrap'); aw.title = 'Cambiar o centrar su foto de perfil'; aw.onclick = () => openAvatar(own); hl.appendChild(head);
    { const st = el('div', 'stats two'); [['followers', 'seguidores'], ['posts', 'publicaciones']].forEach(([k, n]) => { const d = el('div'); const bb = el('b', '', esc(ig[k] != null && ig[k] !== '' ? String(ig[k]) : '')); profEdit(bb, 'ig.' + k, { owner: own, ph: '—' }); d.appendChild(bb); d.appendChild(el('small', '', n)); st.appendChild(d); }); hl.appendChild(st); }
    { const row = el('div', 'status igrow'); row.appendChild(el('span', '', 'Instagram ')); if (ig.url) { const a = el('a', '', 'abrir ↗'); a.href = ig.url; a.target = '_blank'; a.rel = 'noopener'; row.appendChild(a); if (!(WEBM() && !own)) { const up = el('span', 'lnk igup', ' · actualizar'); up.title = 'Leer otra vez sus seguidores y publicaciones'; up.onclick = () => { up.textContent = ' · leyendo…'; igSync(own, ig.url, true); }; row.appendChild(up); } }
      const u = el('span', 'igurl', esc(ig.url || '')); profEdit(u, 'ig.url', { owner: own, ph: '＋ Añadir su Instagram (enlace)' }); row.appendChild(u); hl.appendChild(row);
      const nC = TABS.creaciones.items.filter(i => !isVarAux(i) && !i.pending && i.meta && charOf(i) === (own || 'aria')).length; const cr = el('div', 'status igrow'); const ln = el('span', 'lnk', `${nC} creaci${nC === 1 ? 'ón' : 'ones'} en ARIA STUDIO`); ln.title = 'Ver sus creaciones'; ln.onclick = () => { state.cchar = nC ? [own || 'aria'] : []; setTab('creaciones'); }; cr.appendChild(ln); hl.appendChild(cr); }
    const secP = (title, node, host) => { const sc = el('div', 'pc-sec'); sc.appendChild(el('h4', '', title)); sc.appendChild(node); (host || box).appendChild(sc); };
    { const bp = el('p', 'bio', esc(P.bio || '')); profEdit(bp, 'bio', { multi: true, owner: own }); secP('Bio', bp, hl); }
    { const D = P.datos || {}; const dl = el('dl', 'pc-dl'); [['Edad', 'edad'], ['Altura', 'altura'], ['Origen', 'origen'], ['Idiomas', 'idiomas'], ['Nacida', 'nacida']].forEach(([n, k]) => { dl.appendChild(el('dt', '', n)); const dd = el('dd', '', esc(D[k] || '')); profEdit(dd, 'datos.' + k, { owner: own }); dl.appendChild(dd); }); hl.appendChild(dl);
      hl.appendChild(rasgosNode(D.rasgos || [], true, own));
      [['Personalidad', 'personalidad'], ['Voz y cadencia', 'voz']].forEach(([n, k]) => { const pp = el('p', '', esc(D[k] || '')); profEdit(pp, 'datos.' + k, { multi: true, owner: own }); secP(n, pp); }); }
    side.appendChild(sec('', box)).classList.add('psec');
    { const pw = el('div', 'pbwrap'); const pb = el('div', 'promptbox pbed', esc(P.basePrompt || '')); profEdit(pb, 'basePrompt', { multi: true, owner: own }); pw.appendChild(pb);
      const cp = el('button', 'copyb', COPY_SVG); cp.title = 'Copiar'; cp.onclick = e => { e.stopPropagation(); try { navigator.clipboard.writeText(P.basePrompt || ''); } catch (x) {} cp.innerHTML = CHECK_SVG; cp.classList.add('ok'); setTimeout(() => { cp.innerHTML = COPY_SVG; cp.classList.remove('ok'); }, 1500); }; pw.appendChild(cp);
      if (state.profSync && isAria) pw.appendChild(el('small', 'pjnote', state.profSync === 'prompt' ? '⏳ Actualizando sus datos con el prompt…' : '⏳ Actualizando el prompt con sus datos…'));
      side.appendChild(sec('Prompt base', pw, 'clic para editar' + (isAria ? ' · sus datos se actualizan solos' : ''))).classList.add('psec'); }
  } else if (state.tab === 'video') {
    side.appendChild(videoControls(it));
  } else if (state.tab === 'creaciones') {
    const n = TABS.creaciones.items.length, nv = TABS.creaciones.items.filter(i => i.kind === 'video').length; side.appendChild(sec('Galería', el('div', 'status', `<b>${n}</b> creaciones (${n - nv} imágenes · ${nv} vídeos), de más nueva a más antigua. Filtra arriba y haz clic en una para abrirla en grande con su ficha; con ‹ › pasas a la siguiente.`)));
    const ob = el('button', 'btn w acc', '⤢ Abrir la seleccionada'); ob.onclick = () => openGal(it); const st = el('div', 'stack'); st.appendChild(ob); side.appendChild(sec('Ver', st));
  } else if (state.tab === 'videoteca') {
    videotecaPanel(it);
  } else if (state.tab === 'biblio') {
    biblioPanel(it);
  } else if (LIVE && state.tab === 'crear') {
    side.appendChild(crearPanel(it));
  } else if (LIVE) { // secciones de componentes: primero Añadir, luego la preview con los ajustes plegados
    if (state.tab === 'vestidor') { vestidorPanel(it); return; }
    if (COMP[state.tab]) side.appendChild(addBtn(state.tab, COMP[state.tab].toLowerCase()));
    { const mp = miniPreview(it); const m = curModel(); const ex = existingImage(state.tab, it); if (state.tab === 'hair') { const ab = el('span', 'rcb', '＋ Añadir'); ab.title = 'Añadir a Crear imagen (con el color de pelo elegido)'; ab.onclick = e => { e.stopPropagation(); addMenu('hair', it, ab); }; mp.appendChild(ab); } else if (!jobFor(it)) { const gp = el('span', 'rcb', `${ex && state.done.has(it.id) ? 'Nueva preview' : 'Generar preview'} · ${fmtUsd(m.usd[state.quality])}`); gp.onclick = e => { e.stopPropagation(); tryOn(false); }; mp.appendChild(gp); } side.appendChild(mp); if (state.tab === 'hair' || state.tab === 'photo') { const p = pols(it, state.tab === 'hair' ? ['en la vida real', 'de cerca'] : ['variante 1', 'variante 2']); if (p) side.appendChild(p); } if (state.tab === 'hair') side.appendChild(hairColorSection(it)); { const wb = el('div'); wb.style.padding = '0 18px 8px'; wb.appendChild(withBtn(state.tab, it)); side.appendChild(wb); } setTimeout(syncMini, 0); }
    side.appendChild(previewSection(state.tab, it));
    if (false && state.tab === 'vestidor' && it.looks && it.looks.length > 1 && !userPhoto && state.done.has(it.id)) { const st = el('div', 'stack'); const b2 = el('button', 'btn w', 'Otra pose (pregenerada)'); b2.onclick = () => { state.pose[it.id] = (state.pose[it.id] || 0) + 1; mirror.classList.add('cached'); showImage(itemSrc(it), false); }; st.appendChild(b2); side.appendChild(sec('Poses', st)); }

  } else if (state.tab === 'crear') {
    side.appendChild(sec('Tu creación', tray(), 'Aria + lo que hayas añadido'));
    side.appendChild(sec('Imagen a recrear', trayBib(), 'opcional · Fototeca'));
    const st = el('div', 'stack'); const done = state.done.has(it.id); const match = matchRecipe();
    const b1 = el('button', 'btn w ' + (done ? '' : 'acc'), done ? '✓ Generada · ver' : 'Generar imagen'); b1.onclick = () => tryOn(false); st.appendChild(b1);
    if (it.looks && it.looks.length > 1) { const b2 = el('button', 'btn w', 'Otra pose'); b2.disabled = !done; b2.onclick = () => { state.pose[it.id] = (state.pose[it.id] || 0) + 1; paint(it, false); }; st.appendChild(b2); }
    st.appendChild(el('div', 'status', match ? `Combinación de la receta <b>«${match.name}»</b>${done ? ` · generada en ${(it._ms / 1000).toFixed(1)} s · $${PRICE.toFixed(4)}` : ` · sin generar todavía · <b>$${PRICE.toFixed(4)}</b>`}` : 'Combinación nueva: en esta demo hay 6 creaciones pregeneradas; con el puente encendido se generaría de verdad.'));
    side.appendChild(sec('Generar', st));
  } else if (CONVERT.has(state.tab)) {
    side.appendChild(addBtn(state.tab, COMP[state.tab].toLowerCase()));
    side.appendChild(sec('Tu foto de referencia', dropzone(), 'arrastra otra si quieres'));
    const st = el('div', 'stack'); const done = state.done.has(it.id);
    const inQ = pending.has(it.id);
    const b1 = el('button', 'btn w ' + (done || inQ ? '' : 'acc'), inQ ? '⏳ En cola · esperando el resultado' : done ? '✓ Convertida · ver' : 'Generar imagen'); b1.onclick = inQ ? () => cancelQueue(it) : () => tryOn(false); st.appendChild(b1);
    st.appendChild(el('div', 'status', inQ ? 'Petición enviada. Cuando el archivo aparezca en <b>assets/conv/</b> se enseña solo (revisa cada 4 s). Pulsa el botón para cancelar la espera.' : done ? `<b>Convertida</b> · ${(it._ms / 1000).toFixed(1)} s · $${PRICE.toFixed(4)}` : convSrc(it) ? `Lista para convertir tu foto de referencia: <b>$${PRICE.toFixed(4)}</b> por imagen` : `Este estilo aún no está convertido: al pulsar se queda <b>en cola</b> y se enseña en cuanto Claude lo genere por el MCP.`));
    side.appendChild(sec('Convertir', st));
    if (it.desc) { const box = el('div', 'stack'); box.appendChild(el('div', 'promptbox', it.desc)); side.appendChild(sec('Prompt del estilo', box)); }
    if (state.tab === 'photo') { const p = pols(it, ['variante', 'variante']); if (p) side.appendChild(sec('Variantes', p)); }
  } else if (state.tab === 'hair') {
    side.appendChild(addBtn('hair', 'peinado'));
    const p = pols(it, ['en la vida real', 'y de cerca']); if (p) side.appendChild(sec('¿Y en la vida real?', p, '2 fotos por peinado'));
    if (it.desc) side.appendChild(sec('Peinado (prompt)', el('div', 'promptbox', it.desc)));
  } else if (state.tab === 'expr') {
    side.appendChild(addBtn('expr', 'expresión'));
    if (it.desc) side.appendChild(sec('Prompt', el('div', 'promptbox', it.desc)));
  } else if (state.tab === 'vestidor') {
    const f = el('img', 'ficha'); f.src = it.ficha; f.alt = ''; f.onclick = () => lightbox(it.ficha, it.name); side.appendChild(sec('Ficha de la prenda', f, 'Vestidor Virtual · Nº ' + it.num));
    side.appendChild(addBtn('vestidor', 'prenda'));
    const st = el('div', 'stack');
    const done = state.done.has(it.id);
    const b1 = el('button', 'btn w ' + (done ? '' : 'acc'), done ? '✓ Generado · ver' : 'Generar imagen'); b1.onclick = () => tryOn(false); st.appendChild(b1);
    if (it.looks && it.looks.length > 1) { const b2 = el('button', 'btn w', 'Otra pose'); b2.disabled = !done; b2.onclick = () => { state.pose[it.id] = (state.pose[it.id] || 0) + 1; paint(it, false); log(`<span class="g">▸</span> pose alternativa de <span class="w">«${it.name}»</span> <span class="g">· caché local</span>`); }; st.appendChild(b2); }
    const b3 = el('button', 'btn w p', 'Probar 10 a la vez'); b3.onclick = batch10; st.appendChild(b3);
    const s = el('div', 'status', done ? `<b>Generado</b> · ${(it._ms / 1000).toFixed(1)} s · $${PRICE.toFixed(4)}` : `Sin generar todavía · <b>$${PRICE.toFixed(4)}</b> por imagen`); st.appendChild(s);
    side.appendChild(sec('Probar en el espejo', st));
  } else {
    if (it.desc) { const box = el('div', 'stack'); box.appendChild(el('div', 'promptbox', it.desc)); side.appendChild(sec('Prompt', box)); }
    if (state.tab === 'photo') { const p = pols(it, ['variante', 'variante']); if (p) side.appendChild(sec('Variantes', p)); }
  }
}

// ----------------------------------------------------------------- creación (bandeja), referencia (drop) y giro 360
function restoreComp() { try { const o = JSON.parse(localStorage.getItem('am_comp') || '{}'); Object.entries(o).forEach(([k, id]) => { const it = COMP[k] && TABS[k] && (TABS[k].items || []).find(x => x.id === id); if (it) state.comp[k] = it; }); } catch (e) {} }
function badge() { if (state.ready) { try { localStorage.setItem('am_comp', JSON.stringify(Object.fromEntries(Object.entries(state.comp).filter(([k, v]) => v && v.id && !v.drop && !v.pending).map(([k, v]) => [k, v.id])))); } catch (e) {} } // lo elegido (prenda, peinado, expresión, estilos, Fototeca) se recuerda; una foto soltada no
  const n = Object.keys(state.comp).length; const nb = document.querySelector('#nav button[data-tab="crear"] .bd'); if (nb) { nb.textContent = String(n); nb.classList.toggle('on', n > 0); } }
function compSig() { const p = (state.ipool || []).map(r => r.id).join(',') + (state.nsfw ? ',nsfw' : '') + (window.accSig ? accSig() : '') + ((state.refOrder || []).length ? ',ord:' + crearRefs().map(r => r.key).join('>') : ''); return (Object.keys(COMP).filter(k => state.comp[k]).map(k => k + ':' + state.comp[k].id + (k === 'hair' && state.hairVar ? '@' + state.hairVar : '') + (k === 'hair' && state.hairCol ? '#' + state.hairCol.en : '')).join('|') || 'aria') + (p ? '|refs:' + p : '') + (CH().aria ? '' : '|ch:' + CH().id) + (multiOn() ? '|x:' + extraChars().map(c => c.id + ':' + PERCHAR.map(k => ((state.compBy[c.id] || {})[k] || {}).id || '').join(',')).join(';') + '|p:' + ((state.comp.biblio && state.comp.biblio.people) || []).map(p => p.char || '').join(',') : ''); }
function compNames() { return Object.keys(COMP).filter(k => state.comp[k]).map(k => state.comp[k].name).join(' + ') || CH().short; }
function addToImage(tab, it, jump) { if (tab === 'biblio' && it.group) return; if (tab === 'biblio') delete it.modo; setComp(tab, it); if (tab === 'biblio') { const cu = C.crear.find(x => x.custom); if (cu) { cu._last = null; if (cu._liveBy) delete cu._liveBy[compSig()]; } modeloPorModo(it); } if (tab === 'hair') { state.hairVar = it._variant || null; state.hairCol = it._color || null; } badge(); log(`<span class="g">✨ ${COMP[tab]} «${it.name}» añadida a la creación</span>`); if (jump) { state.flash = tab; setTab('crear'); if (tab === 'biblio') setTimeout(() => setK(0), 10); rail.scrollTop = 0; } else { renderSide(); renderRail(); } toast(`«${it.name}» → Crear imagen`); }
function addToVideo(tab, it) { const src = compImage(tab, it); if (!src) return; poolAdd({ id: tab + ':' + it.id, kind: 'image', name: it.name, src, thumb: compThumb(tab, it) }, true); vbadge(); toast(`«${it.name}» → Crear vídeo (@Image${state.vpool.length})`); if (state.tab !== 'video') { renderSide(); } }
function vbadge() { const nb = document.querySelector('#nav button[data-tab="video"] .bd'); if (nb) { nb.textContent = String(state.vpool.length); nb.classList.toggle('on', state.vpool.length > 0); } }
function addMenu(tab, it, anchor) { // menú de dos opciones pegado al botón «＋ Añadir»
  document.querySelectorAll('.addmenu').forEach(x => x.remove()); const m = el('div', 'addmenu'); const inImg = inCrear(tab, it); const inVid = poolHas(compImage(tab, it));
  const a = el('div', 'it', inImg ? '✓ Ya en Crear imagen' : '🖼 A Crear imagen'); a.onclick = e => { e.stopPropagation(); m.remove(); if (inImg) { delete state.comp[tab]; badge(); renderSide(); renderRail(); toast('Quitada de Crear imagen'); } else addToImage(tab, it, true); }; m.appendChild(a);
  const b = el('div', 'it', inVid ? '✓ Ya en Crear vídeo' : '🎬 A Crear vídeo'); b.onclick = e => { e.stopPropagation(); m.remove(); if (inVid) { const k = state.vpool.findIndex(r => r.src === compImage(tab, it)); if (k >= 0) state.vpool.splice(k, 1); vbadge(); renderSide(); renderRail(); toast('Quitada de Crear vídeo'); } else { addToVideo(tab, it); setTab('video'); } }; m.appendChild(b);
  const btn = anchor.querySelector('.addc') || anchor; const r = btn.getBoundingClientRect(); document.body.appendChild(m); m.style.position = 'fixed'; m.style.zIndex = 80;
  const mw = m.offsetWidth, mh = m.offsetHeight; let left = Math.round(r.left + r.width / 2 - mw / 2); left = Math.max(8, Math.min(window.innerWidth - mw - 8, left)); const above = r.top - mh - 6 >= 8; m.style.left = left + 'px'; m.style.top = Math.round(above ? r.top - mh - 6 : r.bottom + 6) + 'px'; m.style.bottom = 'auto'; m.style.transform = 'none';
  const kill = () => { m.remove(); rail.removeEventListener('scroll', kill); document.removeEventListener('click', eat, true); }; const eat = e => { if (!m.isConnected) { kill(); return; } if (m.contains(e.target)) return; e.stopPropagation(); e.preventDefault(); kill(); }; setTimeout(() => document.addEventListener('click', eat, true), 0); rail.addEventListener('scroll', kill, { once: true });
}
function addBtn(tab, what) {
  const it = state.sel[tab]; const st = el('div', 'stack'); const inTray = inCrear(tab, it);
  const b = el('button', 'btn w ' + (inTray ? '' : 'acc'), inTray ? '✓ En Crear imagen · quitar' : '✨ Añadir a Crear imagen');
  b.onclick = () => { if (inTray) { delete state.comp[tab]; badge(); renderSide(); return; } state.comp[tab] = it; if (tab === 'hair') { state.hairVar = it._variant || null; state.hairCol = it._color || null; } badge(); log(`<span class="g">✨ ${COMP[tab]} «${it.name}» añadida a la creación</span>`); state.flash = tab; setTab('crear'); toast(`«${it.name}» añadida a tu creación`); };
  st.appendChild(b);
  const inVid = poolHas(compImage(tab, it)); const bv = el('button', 'btn w', inVid ? '✓ En Crear vídeo · quitar' : '🎬 Añadir a Crear vídeo'); bv.onclick = () => { if (inVid) { const k = state.vpool.findIndex(r => r.src === compImage(tab, it)); if (k >= 0) state.vpool.splice(k, 1); vbadge(); renderSide(); renderRail(); } else { addToVideo(tab, it); setTab('video'); } }; st.appendChild(bv);

  return sec('Usar en una creación', st);
}
function atHtml(t, refs) { // las etiquetas @ImageN de un prompt, en rosa y como enlace (si se sabe a qué imagen apuntan, lo dice al pasar el ratón)
  return String(t || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/@(?:Image|Video|Audio|img|image)_?(\d+)/gi, (m0, n) => `<b class="at${refs && refs[n - 1] ? ' link' : ''}" data-n="${n}"${refs && refs[n - 1] ? ` title="${String(refs[n - 1]).replace(/"/g, '&quot;')}"` : ''}>${m0}</b>`); }
let _refMap = null;
function refPathOf(m, n) { // a qué archivo apunta @ImageN en una creación guardada
  if (m.refPaths && m.refPaths[n - 1]) return m.refPaths[n - 1]; const name = (m.refs || [])[n - 1]; if (!name) return null; if (name === 'tu foto') return m.canvasRef || null;
  if (!_refMap) { _refMap = new Map(); const add = p => { if (p && typeof p === 'string' && !p.startsWith('data:')) { const q = p.split('?')[0]; _refMap.set(q.split('/').pop(), q); } };
    allItems().forEach(x => { if (x.files) Object.values(x.files).forEach(add); add(x.ficha); add(x.image); (x.looks || []).forEach(add); });
    [C.perfil.ficha, C.perfil.cuerpo, C.perfil.combo, C.base.photo, C.perfil.refphoto].forEach(add); (C.perfil.complementos || []).forEach(c => { add(c.img); add(c.foto); }); }
  return _refMap.get(name) || (/^[0-9a-f]{12,}\.(jpe?g|png|webp)$/i.test(name) ? 'assets/refs/' + name : null); }
function openRefN(m, n) { const p = refPathOf(m, n); if (!p) { toast(`No encuentro la imagen de @Image${n}`); return; } const nm = (m.refs || [])[n - 1] || ''; miniLb(p, `@Image${n}${nm ? ' · ' + nm : ''}`, [['⬇ Descargar', () => { const a = document.createElement('a'); a.href = p; a.download = p.split('/').pop(); document.body.appendChild(a); a.click(); a.remove(); }]]); }
function compThumb(k, it) { if (k === 'vestidor') return it.card; if (k === 'biblio') return it.thumb; return it.files ? it.files.thumb : it.thumb; }
function crearPanel(it) { // todo en una sección compacta: sin scroll en el panel, botón siempre a la vista
  const m = curModel(); const box = el('div', 'stack compact');
  box.appendChild(charSel('crear'));
  box.appendChild(tray());
  if (window.accChips) { const ac = accChips(); if (ac) box.appendChild(ac); }
  { // un solo recuadro: la imagen a recrear (de la Fototeca o tuya). Soltar otra encima la sustituye, sin tener que quitar antes la que hay
    const bib = state.comp.biblio; const row = el('div', 'bibrow bibone' + (bib ? ' on' : ' bibdrop'));
    if (bib) { if (bib.drop && modoDrop(bib) === 'prompt') leerEscena(bib);
      row.innerHTML = `<img src="${compThumb('biblio', bib)}" alt=""><div><small>${bib.drop ? 'Imagen a recrear' : bib.double ? 'Recrea de la Fototeca · comparativa doble' : 'Recrea de la Fototeca'}</small>${bib.drop ? '' : `<b>${bib.name}</b>`}<span class="status">${bib.drop ? (modoDrop(bib) !== 'prompt' ? '' : bib._leyendo ? 'Leyendo la foto…' : bib.neutro ? '' : 'No se ha podido leer: se recrea la misma foto.') : bib.double ? 'Es una comparativa de dos modelos: no se copia la imagen, se usa su prompt con ' + CH().short + ' y lo que añadas.' : ''}${bib.drop ? '' : ' <i class="bibhint">Suelta otra imagen encima para cambiarla.</i>'}</span>${bib.double ? '' : `<button type="button" class="biblnk bibppl">👥 ${(bib.people || []).some(p => p.char) ? (bib.people.filter(p => p.char).length + ' de ' + bib.people.length + ' personas') : '¿Quién es quién?'}</button>`}</div><span class="x" title="Quitar">×</span>`; { const pb = row.querySelector('.bibppl'); if (pb) pb.onclick = e => { e.stopPropagation(); openPeople(bib); }; }
      if (!bib.double) { const md = modoDrop(bib); const g = el('div', 'bibmodo'); [['prompt', 'Desde su descripción', 'Crea una imagen nueva a partir de la descripción de la escena: la foto no se envía, así no se cuelan ni la cara ni el cuerpo de quien sale en ella'], ['swap', 'Misma foto', 'Edita la foto cambiando a la persona: conserva el encuadre exacto, pero puede arrastrar rasgos o accesorios de quien sale en ella']].forEach(([k, t, h]) => { const b = el('button', 'bibm' + (md === k ? ' on' : ''), t); b.type = 'button'; b.title = h; b.onclick = e => { e.stopPropagation(); if (md === k) return; bib.modo = k; if (k === 'prompt') bib._fallo = false; modeloPorModo(bib); badge(); renderSide(); const c = cur(); if (c) paint(c, true); }; g.appendChild(b); }); row.appendChild(g); if (md === 'prompt' && bib.drop) leerEscena(bib); } row.querySelector('.x').onclick = e => { e.stopPropagation(); delete state.comp.biblio; badge(); renderSide(); paint(cur(), true); }; row.onclick = () => { if (bib.drop) { lightbox(bib.image, bib.name); return; } if (state.filter.biblio === 'Carrousel') state.bibGroup = bib.n; setTab('biblio'); const v = view(); if (v.includes(bib)) select(bib, false, true); }; }
    else { row.innerHTML = `<span class="dzi">⬇</span><div><b>Copia cualquier imagen</b><span class="status">Arrástrala aquí o haz clic para subirla.</span><button type="button" class="biblnk">Recrea de la Fototeca →</button></div>`; row.onclick = () => { const inp = $('#file'); inp.onchange = e => { useDrop(e.target.files[0]); inp.value = ''; }; inp.click(); }; row.querySelector('.biblnk').onclick = e => { e.stopPropagation(); setTab('biblio'); }; }
    ['dragenter', 'dragover'].forEach(ev => row.addEventListener(ev, e => { e.preventDefault(); row.classList.add('over'); })); ['dragleave', 'drop'].forEach(ev => row.addEventListener(ev, e => { e.preventDefault(); row.classList.remove('over'); })); row.addEventListener('drop', e => dropAny(e, row));
    box.appendChild(row); }
  { const w = el('div'); w.appendChild(lab('Referencias')); w.appendChild(refsNode()); box.appendChild(w); }
  box.appendChild(genSettings('crear', it));
  const ex = existingImage('crear', it); const revealed = !!ex; const nJobs = [...JOBS.values()].filter(j => !j.end && j.it === it).length;
  const foot = el('div', 'genfoot'); const b = el('button', 'btn w acc', state.submitting ? '⏳ Generando imagen…' : `${ex && revealed ? 'Generar nueva' : 'Generar imagen'} · ${fmtUsd(m.usd[state.quality])}${nJobs ? ' · ⏳ ' + nJobs : ''}`); b.disabled = !!state.submitting; b.title = 'Lanza una petición real'; b.onclick = () => submitGen(); foot.appendChild(b); box.appendChild(foot);
  return sec('', box);
}
async function dropAny(e, dz) { const dt = e.dataTransfer; const f = dt.files && dt.files[0]; if (f) return useDrop(f);
  let url = dt.getData('text/uri-list') || dt.getData('text/plain') || ''; const html = dt.getData('text/html') || ''; const m = html.match(/<img[^>]+src=["']([^"']+)["']/i); if (m) url = m[1];
  if (!/^https?:\/\//i.test(url) && !url.startsWith('data:')) return; toast('Descargando la imagen…');
  try { const r = await fetch('/api/fetch?url=' + encodeURIComponent(url)); const j = await r.json(); if (j.error) throw new Error(j.error); state.comp.biblio = { id: 'drop-' + Date.now(), name: (url.split('/').pop().split('?')[0] || 'imagen de internet').replace(/\.[a-z0-9]+$/i, '').slice(0, 40) || 'imagen de internet', image: j.data, thumb: j.data, prompt: '', drop: true, tags: 'Tu foto' }; modeloPorModo(state.comp.biblio); badge(); state.flash = 'biblio'; renderSide(); paint(cur(), true); toast('La imagen de internet es ahora la imagen a recrear'); }
  catch (err) { toast('No se pudo descargar esa imagen: guárdala y arrástrala desde el ordenador'); }
}
function useDrop(f) { if (!f || !f.type.startsWith('image/')) return; const r = new FileReader(); r.onload = () => { state.comp.biblio = { id: 'drop-' + Date.now(), name: f.name.replace(/\.[a-z0-9]+$/i, ''), image: r.result, thumb: r.result, prompt: '', drop: true, tags: 'Tu foto' }; modeloPorModo(state.comp.biblio); badge(); state.flash = 'biblio'; renderSide(); paint(cur(), true); toast('Tu foto es ahora la imagen a recrear'); }; r.readAsDataURL(f); }
function tray() { const w = el('div', 'stack'); w.appendChild(trayGroup(['vestidor', 'hair', 'expr'])); w.appendChild(trayGroup(['photo', 'movie', 'cartoon'])); return w; }
function dropRecrear() { // arrastra cualquier imagen del escritorio: se usa como lienzo a recrear (sin prompt de la Fototeca)
  const d = el('div', 'dz', `<img src="" alt="" style="width:54px;height:54px;border-radius:10px;background:#f3efe8"><div class="t"><b>O arrastra aquí una foto tuya</b>Se usa como imagen a recrear en vez de una de la Fototeca (sin su prompt). También vale hacer clic.</div>`);
  d.querySelector('img').style.opacity = '.4';
  const use = f => { if (!f || !f.type.startsWith('image/')) return; const r = new FileReader(); r.onload = () => { state.comp.biblio = { id: 'drop-' + Date.now(), name: f.name.replace(/\.[a-z0-9]+$/i, ''), image: r.result, thumb: r.result, prompt: '', drop: true, tags: 'Tu foto' }; modeloPorModo(state.comp.biblio); badge(); state.flash = 'biblio'; renderSide(); paint(cur(), true); toast('Tu foto es ahora la imagen a recrear'); }; r.readAsDataURL(f); };
  ['dragenter', 'dragover'].forEach(ev => d.addEventListener(ev, e => { e.preventDefault(); d.classList.add('over'); }));
  ['dragleave', 'drop'].forEach(ev => d.addEventListener(ev, e => { e.preventDefault(); d.classList.remove('over'); }));
  d.addEventListener('drop', e => use(e.dataTransfer.files && e.dataTransfer.files[0]));
  d.onclick = () => { const inp = $('#file'); inp.onchange = e => { use(e.target.files[0]); inp.value = ''; }; inp.click(); };
  return d;
}
function trayBib() { const t = trayGroup(['biblio']); t.classList.add('one'); const d = t.firstChild; const it = state.comp.biblio; if (it) { d.innerHTML = `<span class="x" title="Quitar">×</span><img src="${compThumb('biblio', it)}" alt=""><div><small>${it.drop ? 'Tu foto' : 'Fototeca'}</small><b>${it.name}</b><div class="status">${it.drop ? 'Imagen arrastrada: se recrea la escena tal cual, sin prompt.' : (it.prompt || '').slice(0, 90) + '…'}</div></div>`; } else d.innerHTML = `<img src="${((C.biblio || [])[0] || {}).thumb || ''}" alt=""><div><small>Fototeca</small><b>ninguna</b><div class="status">Elige una imagen de la Fototeca para recrearla con Aria y lo que hayas añadido arriba.</div></div>`; return t; }
async function dropData(e) { // la imagen soltada (del ordenador o de otra web) como dataURL
  const dt = e.dataTransfer; const f = dt.files && dt.files[0];
  if (f) { if (!f.type.startsWith('image/')) return null; return await new Promise(res => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = () => res(null); r.readAsDataURL(f); }); }
  let url = dt.getData('text/uri-list') || dt.getData('text/plain') || ''; const m = (dt.getData('text/html') || '').match(/<img[^>]+src=["']([^"']+)["']/i); if (m) url = m[1];
  if (url.startsWith('data:image')) return url; if (!/^https?:\/\//i.test(url)) return null; toast('Descargando la imagen…');
  try { const j = await fetch('/api/fetch?url=' + encodeURIComponent(url)).then(r => r.json()); return j.data || null; } catch (x) { return null; } }
window.dropData = dropData;
const DROPMSG = { vestidor: 'Suelta: crea la prenda', hair: 'Suelta: crea el peinado', expr: 'Suelta: crea la expresión' };
function trayDrop(d, k) { // soltar una foto encima del recuadro crea la prenda / el peinado / la expresión en su biblioteca y la deja elegida
  if (!DROPMSG[k] || state.tab !== 'crear') return; d.dataset.drop = DROPMSG[k];
  ['dragenter', 'dragover'].forEach(ev => d.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); d.classList.add('over'); })); d.addEventListener('dragleave', () => d.classList.remove('over'));
  d.addEventListener('drop', async e => { e.preventDefault(); e.stopPropagation(); d.classList.remove('over'); if (!LIVE) { toast('Conecta primero tu API (arriba, «Conecta tu API»)'); return; } const data = await dropData(e); if (!data) { toast('No he podido leer esa imagen: guárdala y arrástrala desde el ordenador'); return; } if (k === 'vestidor') nuevaPrendaDrop(data); else nuevoEstiloDrop(k, data); }); }
function waitPend(it) { const iv = setInterval(() => { if (it.pending && !it._err) return; clearInterval(iv); if (state.tab === 'crear') { renderSide(); const c = cur(); if (c) paint(c, true); } }, 1200); }
async function nuevaPrendaDrop(data) { // misma ficha de 4 vistas que al soltarla en el Vestidor; se puede abrir el Vestidor mientras carga
  const m = curModel(); toast(`Creando la ficha de la prenda con ${m.name} · ${fmtUsd(m.usd.high)}`); const job = await prendaGenerate(nextPrendaName(), data, []); if (!job) return;
  setComp('vestidor', job.it); badge(); renderSide(); waitPend(job.it); }
async function nuevoEstiloDrop(k, data) { // 1) la IA lee el peinado o la expresión de la foto · 2) se genera con Aria en el formato de la biblioteca · 3) entra en Peinados / Expresiones
  const lab = k === 'hair' ? 'peinado' : 'expresión'; const it = { id: 'nuevo-' + k + '-' + Date.now(), name: 'Leyendo la foto…', desc: '', files: { main: data, thumb: data }, pending: true, date: new Date().toISOString().slice(0, 10) };
  setComp(k, it); if (k === 'hair') { state.hairVar = null; state.hairCol = null; } badge(); renderSide();
  const fail = msg => { it._err = msg; it.name = 'No se pudo crear'; toast(`No se ha podido crear el ${lab}: ${msg}`); if (state.tab === 'crear') renderSide(); };
  let r; try { r = await fetch('/api/describir', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: { data }, modo: k }) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
  if (!r || !r.ok) return fail(r ? r.error : 'sin respuesta');
  it.name = r.nombre || 'Nuevo ' + lab; it.desc = r.desc || ''; const ex = r.extra || []; if (state.tab === 'crear') renderSide(); // expresiones: ex[0] = prompt en español (el que se guarda), ex[1] = categoría
  const m = MODELS.find(x => x.key === 'gptimg') || curModel(); const keep = 'Same face, glasses, earrings, black tank top, framing, plain white studio background and soft even lighting as @Image1. @Image2 is her 360 character sheet: match her exact face.';
  const prompt = k === 'hair' ? `Change ONLY the hairstyle of the woman in @Image1 to exactly the hairstyle shown in @Image3: ${it.desc} Keep her own natural black hair color. ${keep} The person in @Image3 is only a model for the hairstyle: never copy their face, hair color, clothes or background. Photoreal, no text, no logos.`
    : `Give the woman in @Image1 exactly the facial expression and gesture of the person in @Image3: ${it.desc} Same hairstyle as @Image1. ${keep} The person in @Image3 only shows the expression: never copy their face, hair, clothes or background. Photoreal, no text, no logos.`;
  const body = { item: 'estilo_' + k, prompt, images: [{ path: C.base.photo.split('?')[0] }, { path: C.perfil.ficha.split('?')[0] }, { data }], aspect: '16:9', quality: 'std', model: m.key, meta: { name: `${k === 'hair' ? 'Peinado' : 'Expresión'} · ${it.name}`, tab: k, hidden: true, estilo: { kind: k, nombre: it.name, desc: k === 'expr' && ex[0] ? ex[0] : it.desc, tipo: ex[1] || '' }, model: m.name, ep: m.ep, prompt } };
  toast(`Creando «${it.name}» con Aria para la biblioteca · ${fmtUsd(m.usd.std)}`);
  let g; try { g = await fetch('/api/generar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(x => x.json()); } catch (e) { g = { error: String(e) }; }
  if (!g || g.error) return fail(g ? g.error : 'sin respuesta');
  const job = { rid: g.request_id, it, tab: k, m, kind: 'image', estilo: k, t0: performance.now(), status: 'queued', usd: g.usd != null ? Number(g.usd) : m.usd.std }; JOBS.set(job.rid, job); ensurePoller(); }
function estiloFinish(job, st) { job.end = true; const it = job.it, k = job.estilo; const usd = st.usd != null ? Number(st.usd) : (job.usd || 0); state.nGen++; state.spent += usd; meter();
  if (st.estilo) Object.assign(it, st.estilo); else it.files = { main: st.file, thumb: st.file }; it.pending = false; it._err = null;
  if (!TABS[k].items.includes(it)) TABS[k].items.unshift(it); if (C[k] && !C[k].includes(it)) C[k].unshift(it);
  toast(`«${it.name}» ya está en ${k === 'hair' ? 'Peinados' : 'Expresiones'} · ${fmtUsd(usd)}`); renderRail(); renderSide(); if (state.tab === 'crear') { const c = cur(); if (c) paint(c, true); } refreshLive(); }
function trayGroup(keys) {
  const t = el('div', 'tray');
  keys.forEach(k => { const lab_ = COMP[k];
    const store = PERCHAR.includes(k) && state.tab === 'crear' ? compFor(cfocusId()) : state.comp; const it = store[k]; const sample = TABS[k] && TABS[k].items.find(x => !x.group && !x.custom); const off = k === 'vestidor' && state.nsfw && state.tab === 'crear' && it; const offEmpty = k === 'vestidor' && state.nsfw && state.tab === 'crear' && !it; const d = el('div', 'ing' + (k === 'vestidor' || k === 'biblio' ? ' tall' : '') + (it && !off ? ' on' : ' empty') + (off ? ' nsfwoff' : ''), it ? `<span class="x" title="Quitar">×</span><img src="${k === 'hair' && state.hairVar ? state.hairVar : compThumb(k, it)}" alt=""><small>${lab_}</small><b>${it.name}</b>` : `<img src="${sample ? compThumb(k, sample) : ''}" alt=""><small>${lab_}</small><b>por defecto</b>`); if (offEmpty) { d.classList.add('nsfwoff'); d.innerHTML = `<span class="slash"><img src="${sample ? compThumb(k, sample) : ''}" alt=""></span><small>${lab_}</small><b>sin ropa (NSFW)</b>`; d.title = 'NSFW activado: no se usa ropa'; } if (off) { d.innerHTML = `<span class="x" title="Quitar">×</span><span class="slash"><img src="${compThumb(k, it)}" alt=""></span><small>${lab_}</small><b>sin ropa (NSFW)</b>`; d.title = 'NSFW activado: la prenda se guarda pero no se usa; al desactivar NSFW vuelve'; }
    d.title = it ? 'Cambiar' : 'Elegir'; d.onclick = e => { if (e.target.classList.contains('x')) { delete store[k]; badge(); renderSide(); paint(cur(), true); return; } if (it && it.drop) return; if (it && k === 'biblio' && state.filter.biblio === 'Carrousel') state.bibGroup = it.n; setTab(k); if (it) { const v = view(); if (v.includes(it)) select(it, false, true); } };
    if (it && it.pending) { d.classList.add('pend'); d.insertAdjacentHTML('beforeend', it._err ? '<span class="ingbusy err">⚠</span>' : '<span class="ingbusy"><i class="spin"></i></span>'); d.title = it._err ? 'No se pudo crear: quítalo con la ×' : 'Se está creando: ya puedes usarlo'; }
    trayDrop(d, k);
    if (state.flash === k) { d.classList.add('flash'); setTimeout(() => { d.classList.remove('flash'); if (state.flash === k) state.flash = null; }, 1200); }
    t.appendChild(d);
  });
  return t;
}
function matchRecipe() { const c = state.comp; if (!CH().aria) return null; if (!c.hair || !c.expr || !c.vestidor || c.cartoon || c.photo || c.movie || c.biblio) return null; return C.crear.find(r => r.hair === c.hair.id && r.expr === c.expr.id && r.vest === c.vestidor.id) || null; }
function recipeSub(r) { const h = C.hair.find(x => x.id === r.hair), e = C.expr.find(x => x.id === r.expr), v = C.vestidor.find(x => x.id === r.vest); return `${h ? h.name : ''} · ${e ? e.name : ''} · ${v ? v.name : ''}`; }
function applyRecipe(r) { const h = C.hair.find(x => x.id === r.hair), e = C.expr.find(x => x.id === r.expr), v = C.vestidor.find(x => x.id === r.vest); state.comp = {}; state.hairVar = null; if (h) state.comp.hair = h; if (e) state.comp.expr = e; if (v) state.comp.vestidor = v; if (h) state.sel.hair = h; if (e) state.sel.expr = e; if (v) state.sel.vestidor = v; badge(); }
const refPhoto = {};
const REF_AR = C.perfil.refAr || 0.8;
function baseDefault(tab) { return CONVERT.has(tab) ? C.perfil.refphoto : tab === 'vestidor' ? (C.vestidor.find(v => v.looks && v.looks[0]) || {}).looks[0] : C.base.photo; }
function refSrc() { return refPhoto[state.tab] || (LIVE && userPhoto) || baseDefault(state.tab); }
function convSrc(it) { return (!refPhoto[state.tab] && it.conv) ? it.conv : null; }
function dropzone() {
  const mine = !!(refPhoto[state.tab] || (LIVE && userPhoto));
  const d = el('div', 'dz', `<img src="${refSrc()}" alt=""><div class="t"><b>${mine ? 'Tu foto' : CONVERT.has(state.tab) ? 'Foto de referencia' : 'Foto base · Aria'}</b>${mine ? 'Cargada desde tu equipo. <span class="lnk" id="quitFoto">Volver a Aria</span>' : CONVERT.has(state.tab) ? 'Aria en el baño, luz de flash. Los 3 primeros estilos de esta pestaña ya están convertidos con ella.' : state.tab === 'vestidor' ? 'Aria de cuerpo entero en estudio: sobre ella se prueba la prenda.' : 'Aria en plano medio en estudio: sobre ella se aplica el cambio.'}<br>Arrastra aquí otra foto o haz clic.</div>`);
  const q = d.querySelector('#quitFoto'); if (q) q.onclick = e => { e.stopPropagation(); userPhoto = null; Object.keys(refPhoto).forEach(k => delete refPhoto[k]); renderSide(); renderRail(); paint(cur(), false); toast('Vuelves a la foto de Aria'); };
  d.querySelector('img').onclick = e => { e.stopPropagation(); lightbox(refSrc(), 'Foto de referencia'); };
  ['dragenter', 'dragover'].forEach(ev => d.addEventListener(ev, e => { e.preventDefault(); d.classList.add('over'); }));
  ['dragleave', 'drop'].forEach(ev => d.addEventListener(ev, e => { e.preventDefault(); d.classList.remove('over'); }));
  d.addEventListener('drop', e => { const f = e.dataTransfer.files && e.dataTransfer.files[0]; if (f && f.type.startsWith('image/')) { const r = new FileReader(); r.onload = () => { refPhoto[state.tab] = r.result; userPhoto = r.result; state.done = new Set([...state.done].filter(id => !TABS[state.tab].items.some(i => i.id === id))); renderSide(); renderRail(); log(`<span class="m">POST</span> https://api.higgsfield.ai/v1/media <span class="g">· ${f.name}</span> <span class="q">← 201</span>`); toast('Foto de referencia cargada'); }; r.readAsDataURL(f); } });
  d.onclick = () => { const inp = $('#file'); inp.onchange = e => { const f = e.target.files[0]; if (!f) return; const r = new FileReader(); r.onload = () => { refPhoto[state.tab] = r.result; userPhoto = r.result; renderSide(); toast('Foto de referencia cargada'); }; r.readAsDataURL(f); inp.value = ''; }; inp.click(); };
  return d;
}
let turnAuto = true;
let turnTimer = 0;
function turnTo(angle, smooth) { const v = $('#turn'); const go = () => { if (v.duration) { v.currentTime = (angle / 360) * v.duration; $('#angle').textContent = Math.round(angle) + '°'; if (state.tab === 'perfil') v.play().catch(() => {}); } }; if (v.readyState >= 1) go(); else v.addEventListener('loadedmetadata', go, { once: true }); }
(() => { const v = $('#turn'); let on = false, lx = 0;
  v.addEventListener('timeupdate', () => { if (v.duration) $('#angle').textContent = Math.round(v.currentTime / v.duration * 360) % 360 + '°'; });
  mirror.addEventListener('pointerdown', e => { if (state.tab !== 'perfil' || cmp || !e.target.closest('#paneTurn')) return; on = true; lx = e.clientX; v.pause(); mirror.classList.add('grabbing'); mirror.setPointerCapture(e.pointerId); });
  mirror.addEventListener('pointermove', e => { if (!on || !v.duration) return; const dx = e.clientX - lx; lx = e.clientX; let t = v.currentTime + dx / mirror.clientWidth * v.duration * 1.2; t = ((t % v.duration) + v.duration) % v.duration; v.currentTime = t; });
  const up = () => { if (!on) return; on = false; mirror.classList.remove('grabbing'); setTimeout(() => { if (state.tab === 'perfil' && !on) v.play().catch(() => {}); }, 900); };
  mirror.addEventListener('pointerup', up); mirror.addEventListener('pointercancel', up); })();

// ----------------------------------------------------------------- MODO EN VIVO (puente.py → API real de Higgsfield)
function allItems() { return ['hair', 'expr', 'vestidor', 'cartoon', 'photo', 'movie', 'crear', 'biblio', 'videoteca'].flatMap(k => C[k] || []); }
let lastLiveJ = null;
function buildCreations(j) {
  if (j && j.creations) { lastLiveJ = j; state.totalN = j.creations.length; state.totalUsd = j.creations.reduce((a, c) => { const m = c.meta || {}; const u = m.usd != null ? Number(m.usd) : (m.usd_est != null ? Number(m.usd_est) : (c.kind === 'video' ? 1.2 : 0.04)); return a + (isFinite(u) ? u : 0); }, 0); state.nGen = 0; state.spent = 0; meter(); } else j = lastLiveJ;
  const list = (j && j.creations) || []; const MN = { qwen: 'Qwen', grok: 'Grok', mstudio: 'Marketing Studio', ideogram: 'Ideogram', i2v: 'Seedance 2.0', r2v: 'Seedance 2.0' };
  const old = new Map(TABS.creaciones.items.map(i => [i.id, i]));
  TABS.creaciones.items = list.map(c => { const m = c.meta || {}; const id = c.file.split('/').pop().replace(/\.[a-z0-9]+$/i, ''); const fecha = m.t ? new Date(m.t * 1000).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' }) : '';
    let thumb = c.kind === 'video' ? (c.poster || (m.source && !String(m.source).startsWith('data:') ? m.source : null) || C.base.thumb) : (c.thumb || c.file);
    const o = old.get(id) || {}; o.kindLabel = c.kind === 'video' ? 'Vídeos' : 'Imágenes'; o.hidden = !!m.hidden; const srcName = c.kind === 'video' ? ((TABS.video.items.find(x => x.id === m.item) || {}).name) : null; return Object.assign(o, { id, name: m.name || srcName || (allItems().find(x => x.id === m.item) || {}).name || m.item || id, sub: `${m.model || MN[m.model_key] || ''}${fecha ? ' · ' + fecha : ''}`, kind: c.kind, src: c.file, thumb, meta: m, video: c.kind === 'video' ? c.file : null }); });
  const pend = (typeof activeJobs === 'function' ? activeJobs() : []).map(j => ({ id: 'job-' + j.rid, name: (j.kind === 'video' ? 'Vídeo · ' : '') + (j.name || j.it.name), sub: 'generándose · ' + j.m.name, kind: j.kind, kindLabel: j.kind === 'video' ? 'Vídeos' : 'Imágenes', pending: true, src: '', thumb: j.thumb || j.it.thumb || (j.it.files && j.it.files.thumb) || j.it.card || j.it.src || C.base.thumb, meta: {} }));
  TABS.creaciones.items = pend.concat(TABS.creaciones.items);
  if (!state.sel.creaciones || !TABS.creaciones.items.includes(state.sel.creaciones)) state.sel.creaciones = TABS.creaciones.items.find(i => !i.pending) || TABS.creaciones.items[0];
  if (state.ready && (state.tab === 'creaciones' || state.tab === 'perfil' || state.tab === 'crear')) { renderRail(); if (state.tab === 'creaciones') renderSide(); $('#pickTitle').textContent = `Mis creaciones · ${TABS.creaciones.items.filter(i => !i.pending).length}`; }
}
function paintCreation(it, fast) {
  const vid = $('#vid');
  if (it.kind === 'video') { mirror.classList.add('vidmode', 'cached'); mirror.querySelector('.tag').textContent = 'vídeo · ' + ((it.meta || {}).model || 'Seedance 2.0'); if (vid.getAttribute('src') !== it.src) { vid.src = it.src; vid.load(); } vid.onloadedmetadata = () => { if (cur() === it && vid.videoWidth) { arOverride = vid.videoWidth / vid.videoHeight; sizeMirror(); } }; if (vid.videoWidth) { arOverride = vid.videoWidth / vid.videoHeight; sizeMirror(); } vid.oncanplay = () => { if (cur() === it && mirror.classList.contains('vidmode')) vid.play().catch(() => {}); }; vid.play().catch(() => {}); }
  else { mirror.classList.remove('vidmode'); vid.pause(); mirror.classList.add('cached'); mirror.querySelector('.tag').textContent = 'creación · ' + ((it.meta || {}).model || 'API'); fitAr(it, it.src); showImage(it.src, fast); }
}
function refreshLive() { fetch('/api/live').then(r => r.json()).then(j => { if (!j) return; buildVideoLib(j); buildCreations(j); if (state.ready) renderSide(); }).catch(() => {}); }
function hydrateLive() { // lo ya generado se recupera (it.live) pero NO se revela hasta pulsar Generar (paripé) — regla de Max
  fetch('/api/live').then(r => r.json()).then(j => {
    if (!j || !j.files) return; const map = new Map(allItems().map(i => [i.id, i])); let n = 0;
    for (const [id, f] of Object.entries(j.files)) { const it = map.get(id); if (it) { it.live = f; n++; } }
    if (n) { log(`<span class="g">· ${n} imagen(es) generadas antes por la API recuperadas de assets/live/ · se enseñan sin gastar al pulsar Generar</span>`); if (state.ready) { renderRail(); renderSide(); } }
    if (!hydrateLive._ja) { hydrateLive._ja = true; jobsRecuperar(); }   // antes de montar Mis creaciones: así las que siguen generándose tienen su tarjeta
    buildVideoLib(j); buildCreations(j); if (state.ready && (state.tab === 'crear' || state.tab === 'creaciones')) renderChips();
    if (!hydrateLive._ya) { hydrateLive._ya = true;   // solo al abrir la página: en grande, tu última creación (la de esta combinación si se sabe cuál fue; si no, la más reciente). Al cambiar la combinación vuelve el lienzo
      try { const cu = C.crear.find(x => x.custom); let u = JSON.parse(localStorage.getItem('am_crear_last') || 'null'); const sg = compSig();
        const src = (u && u.sig === sg && (j.all || []).includes(u.src)) ? u.src : (cu && j.files && j.files[cu.id]);
        if (cu && src && !(cu._liveBy && cu._liveBy[sg])) { cu._liveBy = cu._liveBy || {}; cu._liveBy[sg] = src; state.done.add(cu.id); if (state.ready && state.tab === 'crear') paint(cur(), true); } } catch (e) {} }
    if (state.ready) renderSide(); const nv = Object.keys(j.videos || {}).length; if (nv) log(`<span class="g">· ${nv} vídeo(s) generados antes recuperados de assets/video/</span>`);
  }).catch(() => {});
}
let LIVE = false, userPhoto = null;   // userPhoto = dataURL de la foto arrastrada por el usuario
let MODELS = [], UNAVAILABLE = [], ASPECTS = ['3:4', '1:1', '4:3', '9:16', '16:9', '2:3', '3:2'], modelKey = 'qwen';
function curModel() { return MODELS.find(m => m.key === modelKey) || MODELS[0] || { key: 'qwen', name: 'Qwen Image 3 · Edit', ep: 'alibaba/qwen-image-3/edit', refs: 3, usd: { std: 0.04, high: 0.075 }, high: '2k' }; }
function fmtUsd(u) { return '$' + Number(u).toFixed(3).replace(/0$/, ''); }
function setModel(k) { if (!MODELS.some(m => m.key === k)) return; modelKey = k; try { localStorage.setItem('am_model', k); } catch (e) {} const m = curModel(); log(`<span class="ok">modelo</span> <span class="u">${m.ep}</span> <span class="g">· ${m.name} · ${fmtUsd(m.usd[state.quality])}/imagen · ${m.refs} referencia(s) máx.</span>`); toast(`Ahora se genera con ${m.name}`); }
const NSFW_MODEL = 'seedream';
function nsfwModel() { // devuelve el texto para el aviso
  if (state.nsfw && modelKey !== NSFW_MODEL && MODELS.some(x => x.key === NSFW_MODEL)) { persist('am_model_prensfw', modelKey); modelKey = NSFW_MODEL; persist('am_model', modelKey); return ' · se genera con Seedream 5.0 Pro, el único que lo permite'; }
  if (!state.nsfw) { let prev = null; try { prev = localStorage.getItem('am_model_prensfw'); localStorage.removeItem('am_model_prensfw'); } catch (e) {} if (prev && prev !== modelKey && MODELS.some(x => x.key === prev)) { modelKey = prev; persist('am_model', prev); return ' · vuelve ' + curModel().name; } }
  return '';
}
function fitModel(n) { const ok = MODELS.filter(x => x.refs >= n); const ws = ok.filter(x => x.prov === 'ws'); return (ws.length ? ws : ok).sort((a, b) => a.usd[state.quality] - b.usd[state.quality])[0] || null; } // el más barato que admite n referencias
window.fitModel = fitModel;
function refCount() { try { return state.tab === 'crear' ? crearRefs().length : state.tab === 'vestidor' ? 3 : 2; } catch (e) { return 2; } } // cuántas imágenes de referencia lleva lo que se va a generar
function setupModels(j) {
  MODELS = j.models || []; UNAVAILABLE = j.unavailable || []; if (j.aspects) ASPECTS = j.aspects; if (!MODELS.length) return;
  MODELS.forEach(m => { const base = m.usd, per = m.per || 0; const calc = q => +(base[q] + per * Math.max(0, Math.min(refCount(), m.refs || 16) - 1)).toFixed(4); m.usd0 = base; m.usd = { get std() { return calc('std'); }, get high() { return calc('high'); } }; }); // el precio que se enseña ya cuenta las referencias que van (varios modelos cobran por cada una)
  { const ORD = ['seedream', 'nbp', 'gptimg', 'qwenws', 'mstudio', 'grok', 'qwen']; const ix = m => { const i = ORD.indexOf(m.key); return i < 0 ? 99 : i; }; MODELS.sort((a, b) => ix(a) - ix(b)); } // orden de Max
  try { const saved = localStorage.getItem('am_model'); const migrated = localStorage.getItem('am_model_v2'); const def = MODELS[0].key; modelKey = (migrated && saved && MODELS.some(m => m.key === saved)) ? saved : def; localStorage.setItem('am_model_v2', '1'); if (!migrated) localStorage.setItem('am_model', modelKey); } catch (e) { modelKey = MODELS[0].key; }   // por defecto, el primero del orden que la cuenta tenga conectado (antes podía quedar uno sin clave y el desplegable salía vacío)
  if (!ASPECTS.includes(state.aspect)) state.aspect = '3:4';
}
function fitPlan(tab, it, plan, m) { // si el modelo admite menos referencias de las que lleva el plan, lo que sobra va descrito en texto
  if (plan.images.length <= m.refs) return plan;
  let extra = ` Only the first ${m.refs} image(s) are provided; for anything that mentions a later image, rely on the description in parentheses.`;
  if (m.refs < 2) extra += ' Keep her exact face, thin round metal glasses and silver hoop earrings.';
  if (tab === 'vestidor') extra += ` The outfit to put on her, in words: ${it.name}.`;
  else if (tab === 'hair') extra += ` The target hairstyle, in words: ${it.desc || it.name}.`;
  else if (tab === 'expr') extra += ` The target expression, in words: ${it.name}.`;
  log(`<span class="q">      ${m.name} solo admite ${m.refs} referencia(s): se manda${m.refs > 1 ? 'n las primeras' : ' la primera'} y el resto va descrito en el prompt</span>`);
  return Object.assign({}, plan, { images: plan.images.slice(0, m.refs), prompt: plan.prompt + extra });
}
fetch('/api/ping').then(r => r.json()).then(j => { if (j && j.interno && !state.interno) { state.interno = true; buildNav(); badge(); } if (j && j.ok && (j.key || j.ws)) { LIVE = true; ARK = !!j.ark; WS = !!j.ws; if (ARK) log(`<span class="ok">● ByteDance directo</span> <span class="g">· clave de BytePlus encontrada · disponible en Crear vídeo</span>`); $('#livedot').classList.add('on'); setupModels(j); hydrateLive(); const m = curModel(); log(`<span class="ok">● API en vivo</span> <span class="g">· puente local → api.higgsfield.ai · modelo ${m.name} (${m.ep}) · ${MODELS.length} modelos disponibles</span>`); if (state.ready) { renderRail(); renderSide(); paint(cur(), true); } } else if (j && j.ok) { log(`<span class="q">falta conectar tu API: pulsa «Conecta tu API» arriba</span>`); const d = $('#livedot'); d.classList.add('on', 'nokey'); d.innerHTML = '<i style="background:#e0a23a"></i> Conecta tu API'; setTimeout(openClaves, 600); } }).catch(() => { const d = $('#livedot'); d.classList.add('on'); d.style.cssText = 'color:#b3261e;background:#fdeceb;border-color:#f3c2be'; d.innerHTML = '<i style="background:#e0443a;box-shadow:0 0 0 3px rgba(224,68,58,.25)"></i> Sin conexión con el servidor · recarga la página'; d.title = 'No se ha podido conectar con el servidor de ARIA STUDIO. Recarga la página en un momento.'; log(`<span class="pr">✕ puente apagado: doble clic en «ARIA MIRROR.command» y recarga</span>`); });
function ariaBody() { const v = (C.vestidor || []).find(x => x.looks && x.looks[0]); return { path: v ? v.looks[0] : C.base.photo }; } // Aria de cuerpo entero (tank top + leggings)
async function openClaves() { // «Tus APIs»: las que tienes conectadas (con su saldo) y un solo campo para pegar otra: el puente reconoce de qué proveedor es. Las claves se guardan en el ordenador y nunca vuelven al navegador
  let m0 = $('#clavesm'); if (m0) m0.remove(); m0 = el('div', 'fxm'); m0.id = 'clavesm'; document.body.appendChild(m0); m0.onclick = e => { if (e.target === m0) m0.remove(); };
  const b = el('div', 'devbox clavesbox'); m0.appendChild(b); let A = []; let msg = {}; let dirty = false; let add = false;   // add: se está pegando una clave nueva
  const post = async body => { let r; try { r = await fetch('/api/claves', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(x => x.json()); } catch (e) { r = { error: 'sin respuesta' }; } if (r && r.ok) { A = r.apis; dirty = true; msg = {}; add = false; } else msg = { [body.id]: 'No se ha guardado: ' + (r ? r.error : 'sin respuesta') }; draw(); };
  const cerrar = () => { m0.remove(); if (dirty) location.reload(); };
  const card = a => { const c = el('div', 'apicard' + (a.on ? ' on' : ' off'));
    c.appendChild(el('div', 'apihd', `<b>${a.nombre}</b><small>${a.para}</small><span class="apist">${a.on ? `✓ Conectada · ····${esc(a.fin)}${a.saldo != null ? ` · saldo <b>$${Number(a.saldo).toFixed(2)}</b>` : ''}` : 'Desconectada'}</span>`));
    if (a.error) c.appendChild(el('div', 'claveserr', esc(a.error)));
    const row = el('div', 'apirow'); const inp = el('input', 'pjin'); inp.type = 'password'; inp.autocomplete = 'off'; inp.placeholder = 'Pega otra clave para cambiarla'; row.appendChild(inp);
    const sv = el('button', 'btn acc', 'Guardar'); sv.onclick = async () => { const k = inp.value.trim(); if (!k) { inp.focus(); return; } sv.disabled = true; sv.textContent = 'Comprobando…'; await post({ id: a.id, key: k }); }; row.appendChild(sv);
    if (a.on) { const x = el('button', 'btn apix', '× Desconectar'); x.title = 'Deja de usarse. La clave sigue guardada por si la vuelves a conectar'; x.onclick = () => post({ id: a.id, off: true }); row.appendChild(x); }
    if (a.off) { const y = el('button', 'btn', '↺ Volver a conectar'); y.onclick = () => post({ id: a.id, off: false }); row.appendChild(y); }
    c.appendChild(row); if (msg[a.id]) c.appendChild(el('div', 'claveserr', esc(msg[a.id]))); return c; };
  const nueva = hayMas => { const c = el('div', 'apicard apiadd');   // un solo campo: se pega la clave y el puente averigua de quién es
    const row = el('div', 'apirow'); const inp = el('input', 'pjin'); inp.type = 'password'; inp.autocomplete = 'off'; inp.placeholder = 'Pega aquí tu clave de API'; row.appendChild(inp);
    const go = async () => { const k = inp.value.trim(); if (!k) { inp.focus(); return; } sv.disabled = true; sv.textContent = 'Comprobando…'; await post({ id: 'auto', key: k }); };
    const sv = el('button', 'btn acc', 'Conectar'); sv.onclick = go; inp.onkeydown = e => { if (e.key === 'Enter') go(); }; row.appendChild(sv);
    if (hayMas) { const z = el('button', 'btn', 'Cancelar'); z.onclick = () => { add = false; msg = {}; draw(); }; row.appendChild(z); }
    c.appendChild(row); c.appendChild(el('small', 'apinote', 'ARIA STUDIO reconoce sola de quién es. Hoy funciona con claves de <b>WaveSpeed</b>, <b>Higgsfield</b> (con la forma ID:SECRET) y <b>BytePlus</b>.'));
    if (msg.auto) c.appendChild(el('div', 'claveserr', esc(msg.auto))); setTimeout(() => inp.focus(), 0); return c; };
  const draw = () => { b.innerHTML = ''; const n = A.filter(a => a.on).length; const mias = A.filter(a => a.on || a.off), resto = A.filter(a => !a.on && !a.off);
    b.appendChild(el('div', 'devemo', '🔑')); b.appendChild(el('h3', '', 'Tus APIs')); b.appendChild(el('p', '', `ARIA STUDIO genera con <b>tus propias cuentas</b>: tú pones la clave y pagas solo lo que generas. Las claves se guardan cifradas en tu cuenta de ARIA STUDIO y solo se usan para tus generaciones. ${n ? `Ahora tienes <b>${n}</b> conectada${n === 1 ? '' : 's'}.` : 'Todavía no tienes ninguna conectada.'}`));
    b.appendChild(el('div', 'clavesvid', '▶<small>Vídeo de Aria: cómo conectar tu API · pronto</small>'));
    mias.forEach(a => b.appendChild(card(a)));
    if (!mias.length || add) b.appendChild(nueva(mias.length > 0));   // la primera vez, el campo ya está a la vista
    else if (resto.length) { const nb = el('button', 'btn apinew', '＋ Añadir otra API'); nb.onclick = () => { add = true; draw(); }; b.appendChild(nb); }
    const ft = el('div', 'pjacts'); const c0 = el('button', 'btn acc big', dirty ? 'Listo' : 'Cerrar'); c0.onclick = cerrar; ft.appendChild(c0); b.appendChild(ft); };
  b.appendChild(el('p', '', 'Mirando tus conexiones…')); try { const st = await fetch('/api/claves').then(x => x.json()); A = st.apis || []; } catch (e) {} draw();
}
window.openClaves = openClaves;
function basePhoto(kind) { // imagen 1 para las ediciones: la foto del usuario si la hay; si no, Aria
  if (userPhoto) return { data: userPhoto };
  { const ch = CH(); if (!ch.aria) return { path: ch.foto }; }   // otro personaje: su foto de frente
  if (kind === 'body') return ariaBody();   // cuerpo entero (tank top + leggings)
  return { path: C.base.photo };                                   // plano medio en estudio
}
const FICHA = () => ({ path: CH().ficha });   // ficha 360 de Aria: SIEMPRE imagen 2 (regla de Max)
const CLOTH_RE = /\b(wear|wears|wearing|worn|outfit|clothing|clothes|dress|dressed|swimsuit|bikini|lingerie|underwear|bra\b|panties|top\b|tank top|t-shirt|shirt|blouse|sweater|hoodie|jacket|coat|blazer|cardigan|jeans|trousers|pants|shorts|leggings|skirt|jumpsuit|bodysuit|corset|fabric|neckline|sleeves?|denim|lace|silk|cotton|linen|knit|uniform|costume|robe|towel wrapped|apron|catsuit|leotard|cosplay|cosplaying|boots?|sneakers|heels|socks|hood|gloves|leather|latex|vinyl|fully clothed|clothed|covered)\b/i;
function nsfwPrompt(t) { // estructura: edición → identidad → «No clothes, she is naked.» → escena sin ropa → Photoreal → Negative prompt (limpio)
  const NEG = /\s*Negative prompt:\s*/i; let body = t, neg = ''; const m = t.match(NEG); if (m) { body = t.slice(0, m.index); neg = t.slice(m.index + m[0].length); }
  body = stripClothing(unSafe(body)).replace(/\s*(Photoreal, )?no text, no logos\.?\s*$/i, '').replace(/\.{2,}/g, '.').trim();
  const sents = body.split(/(?<=[.!?])\s+/); let k = sents.findIndex(x => /The woman must be/i.test(x)); if (k < 0) k = 0; sents.splice(k + 1, 0, 'No clothes, she is naked.');
  const nl = neg.replace(/\.+\s*$/, '').split(',').map(x => x.trim()).filter(x => x && !/\b(explicit|nude|nudity|naked|see-through|nsfw|topless|nipples?|revealing|cleavage|clothes|clothing)\b/i.test(x));
  return sents.join(' ').replace(/\s{2,}/g, ' ') + (/Photoreal/i.test(t) ? ' Photoreal, no text, no logos.' : ' No text, no logos.') + (nl.length ? ' Negative prompt: ' + nl.join(', ') + '.' : ''); }
function unSafe(t) { // NSFW: quita lo que lo contradice («tasteful, fully clothed, non-explicit» y del negativo «explicit, nude, see-through»)
  t = t.replace(/\b(tasteful|non-explicit|sfw|modest|fully clothed|clothed)\b\s*,?\s*/gi, '');
  return t.replace(/(Negative prompt:)([^]*?)(\.\s|$)/i, (m, h, list, end) => { const keep = list.split(',').map(x => x.trim()).filter(x => x && !/\b(explicit|nude|nudity|naked|see-through|nsfw|topless|nipples?|revealing|cleavage)\b/i.test(x)); return keep.length ? h + ' ' + keep.join(', ') + end : ''; }); }
function stripClothing(t) { // quita SOLO los fragmentos que hablan de ropa (entre comas, «;», guiones o «while/with/and»); la escena, la luz y la cámara se quedan
  return t.split(/(?<=[.!?])\s+/).map(sent => { if (!CLOTH_RE.test(sent)) return sent; const end = /[.!?]$/.test(sent) ? sent.slice(-1) : ''; const parts = sent.replace(/[.!?]$/, '').split(/\s*[,;]\s*|\s+—\s+|\s+-\s+/); const keep = parts.map(p => CLOTH_RE.test(p) ? p.replace(/\b(wearing|dressed in|in)\b[^,]*$/i, '').trim() : p).filter(p => p && !CLOTH_RE.test(p)); return keep.length ? keep.join(', ') + end : ''; }).filter(Boolean).join(' ').replace(/\s{2,}/g, ' ').trim();
}
function deAria(t) { return (t || '').split(/(?<=[.!?])\s+/).map(sn => sn.split(/,\s*/).filter(x => !/\b(Aria|glasses|ponytail|hoop earrings?|hoops|green eyes|green-eyed)\b/i.test(x)).join(', ')).filter(x => x.trim()).join(' '); }
function genderize(t, g) { // los prompts están escritos en femenino: se pasan a masculino o a neutro según el personaje
  if (!g || g === 'fem') return t;
  if (g === 'masc') return t.replace(/\bThe woman\b/g, 'The man').replace(/\bwoman\b/g, 'man').replace(/\bShe\b/g, 'He').replace(/\bshe\b/g, 'he').replace(/\bherself\b/g, 'himself').replace(/\bHer\b/g, 'His').replace(/\bher(?=\s+(?:more than once|plus)\b|[.,;)]|$)/g, 'him').replace(/\bher\b/g, 'his');
  const V = { wears: 'wear', has: 'have', is: 'are', keeps: 'keep', holds: 'hold', uses: 'use' };
  return t.replace(/\bThe woman\b/g, 'The person').replace(/\bwoman\b/g, 'person').replace(/\b(She|she)( now)? (wears|has|is|keeps|holds|uses)\b/g, (m0, s, now, v) => (s === 'She' ? 'They' : 'they') + (now || '') + ' ' + V[v])
    .replace(/\bShe\b/g, 'They').replace(/\bshe\b/g, 'they').replace(/\bherself\b/g, 'themself').replace(/\bHer\b/g, 'Their').replace(/\bher(?=\s+(?:more than once|plus)\b|[.,;)]|$)/g, 'them').replace(/\bher\b/g, 'their'); }
function livePlan(tab, it) { const p = livePlanRaw(tab, it);
  if (state.nsfw && tab === 'crear' && !p.multi) p.prompt = nsfwPrompt(p.prompt);
  p.prompt = p.prompt.replace(/\b(?:image|Image) (\d+)\b/g, '@Image$1'); if (!p.multi) { const ch = CH(); if (!ch.aria) { p.prompt = p.prompt.replace(/Same face, glasses, earrings,/g, 'Same face, accessories,').replace(/Same face, hairstyle, glasses, earrings,/g, 'Same face, hairstyle, accessories,'); if (tab === 'vestidor') p.prompt += ' The person wearing the outfit in @Image3 is only a mannequin for the clothes: never copy her face, hair, glasses or earrings.'; } p.prompt = genderize(p.prompt, ch.gen); }
  return p; } // las referencias van etiquetadas @Image1, @Image2… (igual que en el pool y el menú @)
// texto de una escena (el prompt de la Fototeca o la lectura de una foto) sin las frases que nombran sus propias imágenes de referencia
function cleanDesc(t) { return (t || '').replace(/,?\s*of the woman in image 1 as (the )?subject[,.]?\s*/gi, ' ').replace(/the woman in image 1 as (the )?subject[,.]?\s*/gi, '').replace(/MANDATORY:[^.]*\.\s*/gi, '').replace(/maintaining her [^.]*\.\s*/gi, '').replace(/\s*Negative prompt:[\s\S]*$/i, '').trim(); }
function sinRefs(t) { return t.replace(/@?(?:image|img)[_ ]?\d+\s+as\s+(?:an?\s+)?(?:exact\s+)?(?:outfit|moodboard|style|pose|background|location)\b[^.@]*/gi, '').replace(/use @?(?:image|img)[_ ]?\d+ only as [^,.]*[,.]\s*/gi, '').replace(/\b(?:the )?(?:woman|girl|person|subject) (?:in|from|of) @?(?:image|img)[_ ]?\d+\b/gi, 'she').replace(/\bwearing @?(?:image|img)[_ ]?\d+\s*,?/gi, '').replace(/@?(?:image|img)[_ ]?\d+\s+as\s+(an?\s+)?(exact\s+)?(\w+\s+)?reference:?\s*/gi, '').replace(/@?\bimg[_ ]?\d+\b/gi, '').replace(/\bimage[_ ]\d+\b/gi, '').replace(/^[\s,—-]+/, '').replace(/\(?@image[_ ]?\d+\)?/gi, '').replace(/^\s*as (the )?subject[,.]?\s*/i, '').replace(/\s{2,}/g, ' ').replace(/\s*,\s*\./g, '.').replace(/\.\.+/g, '.'); }
function livePlanRaw(tab, it) { // qué mandar a la API según la pestaña · imagen 1 = base a editar · imagen 2 = ficha 360 · después, el componente
  const ch = CH(); const ID = ch.aria ? 'Image 2 is her 360 character sheet (four views): match her exact face, green eyes, thin round metal glasses and silver hoop earrings.' : `Image 2 is her character sheet (several views of her): match her exact identity: ${window.accIdent ? accIdent(() => 'image 0') : ch.ident}.`;
  const H = 'Photoreal, no text, no logos.';
  if (tab === 'vestidor') return { images: [basePhoto('body'), FICHA(), { path: it.ficha }], aspect: '3:4', prompt: `Make the person in image 1 wear EXACTLY the complete outfit shown in image 3 (every piece, same colors, fabrics, and the same shoes), fitted naturally, full body visible from head to shoes, plain white studio backdrop, soft even lighting. ${ID} Keep everything else in image 1 unchanged. ${H}` };
  if (tab === 'hair') return { images: [basePhoto('face'), FICHA()], aspect: '3:4', prompt: `Change ONLY the hairstyle of the person in image 1 to: ${it.desc || it.name} (${it.name}). Same face, glasses, earrings, clothes, pose and background. ${ID} ${H}` };
  if (tab === 'expr') return { images: [basePhoto('face'), FICHA()], aspect: '3:4', prompt: `Give the person in image 1 this facial expression and gesture: ${it.name}${it.desc ? ' — ' + it.desc : ''}. Same face, hairstyle, glasses, earrings, clothes and background. ${ID} ${H}` };
  if (tab === 'crear' && multiOn()) return planMulti();
  if (tab === 'crear') { // referencias con clave (lienzo, ficha, prenda, peinado, expresión, extras) ordenadas por state.refOrder; los números del prompt se calculan después de ordenar
    const c = state.comp; const parts = []; const v = c.vestidor, h = c.hair, e = c.expr, bib = c.biblio;
    const sceneTxt = b => ch.aria ? cleanDesc(b.neutro || b.prompt) : deAria(cleanDesc(b.neutro || b.prompt));
    const extras = !!(v || h || e || c.cartoon || c.photo || c.movie);
    const R = crearRefs(); const n = key => { const i = R.findIndex(r => r.key === key); return i + 1; }; const I = key => 'image ' + n(key);
    const NOTME = (k, what) => ch.aria ? '' : `; the person shown in ${I(k)} is only ${what}: never copy her face, hair color, glasses or earrings`; // las bibliotecas enseñan a Aria: de ahí solo se copia la prenda, el peinado o el gesto
    const dbl = sinLienzo(bib);   // imagen nueva desde el prompt (sin la foto de la escena)
    const fig = (dbl && bib && bib.figura && !/^\W*real\b/i.test(bib.figura)) ? bib.figura.replace(/[.\s]+$/, '').replace(/^an?\s+/i, '') : '';   // la foto leída no es una persona de verdad (Funko, muñeco, dibujo…): se recrea como esa misma clase de figura
    let base;
    if (bib && dbl) base = `${fig ? `Create a new image whose main figure is a ${fig}: a ${fig} VERSION of the woman of ${I('ficha')} (her 360 character sheet), with her features, hair and colors translated into that exact style, material, finish and proportions; never a photorealistic human` : `Create a new photograph. The woman is the woman of ${I('ficha')} (her 360 character sheet)`}: ${window.accIdent ? accIdent(I) : 'same face, green eyes, thin round metal glasses, silver hoop earrings'}. Scene: ${sinRefs(sceneTxt(bib))}${bib.ropa && !n('vestidor') ? ' She wears ' + bib.ropa.replace(/\.$/, '') + '.' : ''}`;
    else if (bib) base = `Edit ${I('canvas')}. Keep its scene, background, camera framing, pose, lighting and composition exactly as they are. The woman must be the woman of ${I('ficha')} (her 360 character sheet): ${window.accIdent ? accIdent(I) : 'same face, green eyes, thin round metal glasses, silver hoop earrings'}${(extras || !(bib.neutro || bib.prompt)) ? '' : '. Scene, for reference: ' + sceneTxt(bib)}`;
    else base = `Portrait of the woman in ${I('canvas')}, whose face must match ${I('ficha')} (her 360 character sheet), natural pose, plain white studio backdrop, soft even lighting`;
    if (n('vestidor')) parts.push(`REPLACE her clothing completely: she wears EXACTLY the outfit and shoes of ${I('vestidor')} (${v.name}), every piece, same colors and fabrics; nothing of the original clothing remains${NOTME('vestidor', 'a mannequin for the outfit')}`);
    const hh = ch.hair || {};   // su pelo de siempre (el de su ficha)
    if (n('hair')) parts.push(`REPLACE her hairstyle with exactly the hairstyle of ${I('hair')}: ${h.desc || h.name}${hairVarColor(h) ? ` Hair color: ${hairVarColor(h)}${state.hairCol ? '' : `, exactly as in ${I('hair')}`}.` : (!ch.aria && hh.color ? ` Hair color: ${hh.color}, her own, exactly as in ${I('ficha')}.` : '')}; do not keep the original hairstyle${NOTME('hair', 'a model for the hairstyle (copy only the cut and the styling)')}`);
    if (dbl && !n('vestidor') && !ch.aria) parts.push(`she is dressed for the scene as the scene describes; the underwear or swimwear shown in ${I('ficha')} is ONLY a body reference and never her outfit, unless the scene itself is a beach or pool scene`);   // sin prenda elegida: que no salga con la ropa interior de su ficha
    if (n('hair')) {} else if (h) parts.push(`REPLACE her hairstyle with this one: ${(h.desc || h.name).replace(/\.$/, '')}${hairVarColor(h) ? `. Hair color: ${hairVarColor(h)}` : (hh.color ? `. Hair color stays ${hh.color}, her own, exactly as in ${I('ficha')}` : '')}; do not keep the original hairstyle`);   // sin imagen de referencia (personaje propio): el peinado va en palabras
    else if (bib && (!ch.aria || bib.drop)) parts.push(`her hair is her own hair, exactly as in ${I('ficha')}${hh.color ? ': ' + hh.color + ' hair' : ''}${hh.style ? ', ' + hh.style.replace(/\.$/, '') : ''} (same color, length and cut)${dbl ? '' : `; do not keep the hair of the person in ${I('canvas')}`}`);   // sin peinado elegido: al recrear una foto ajena (o con otro personaje) manda el pelo de su ficha, no el de la foto
    if (n('expr')) parts.push(`her facial expression and gesture are exactly those of ${I('expr')}: ${e.name}${NOTME('expr', 'a model for the expression')}`);
    else if (e) parts.push(`her facial expression and gesture: ${(e.desc || e.name).replace(/\.$/, '')} (${e.name}), performed with her own face`);   // sin imagen de referencia (personaje propio): la expresión va en palabras
    if (c.cartoon) parts.push(`render the whole image in this art style: ${ch.aria ? (c.cartoon.desc || c.cartoon.name) : deAria(c.cartoon.desc || c.cartoon.name)}`);
    if (c.photo) parts.push(`photographic style: ${c.photo.desc || c.photo.name}`);
    if (c.movie) parts.push(`cinematic color grading and look of ${c.movie.name}${c.movie.desc ? ': ' + c.movie.desc : ''}`);
    R.filter(r => r.key.startsWith('pool:')).forEach(r => parts.push(`use ${I(r.key)} (${r.name}) as a reference where the prompt mentions @Image${n(r.key)}`));
    const otra = !!(bib && !dbl && (!ch.aria || bib.drop));   // la persona de la foto NO es el personaje (las fotos de la Fototeca son Aria; una foto arrastrada, o cualquiera con un personaje propio, enseña a otra)
    if (otra) parts.unshift(`REPLACE the identity of the person in ${I('canvas')} completely: the face shape, bone structure, eyes and eye color, eyebrows, nose, lips, skin tone and age are EXACTLY those of ${I('ficha')}; she is a DIFFERENT person from the one in ${I('canvas')} and nothing of the original face remains (same place and same pose, new person). If the figure in ${I('canvas')} is a toy, vinyl collectible, doll, figurine, cartoon or illustration, she becomes that SAME kind of figure of herself: her features translated into that exact style, material and proportions (same oversized head, simplified eyes and finish), never a photorealistic human face on it. She does NOT wear the glasses, earrings, jewelry, hat or any accessory of the original person: only her own accessories, if any are listed above. This is a FULL BODY swap, not a face swap: her build, height, skin, shoulders, chest, waist, hips, arms, hands, legs and feet are her own, as in ${I('ficha')}, with the clothes refitted to her body; from the original person keep only the pose, the action and the place in the frame`);
    if (bib && !dbl && !e) { // sin expresión elegida manda la del original: la frase del prompt de la Fototeca que la describe + la de @Image1
      const src = cleanDesc(bib.neutro || bib.prompt || ''); const EXPR_RE = /\b(stare|staring|smil\w*|laugh\w*|grin\w*|expression|gaze|gazing|looking|look(s)? (at|away|down|up)|eyes?|mouth|pout\w*|frown\w*|cry\w*|tears?|wink\w*|tongue|surpris\w*|shock\w*|scream\w*|yawn\w*|sleepy|tired|exhausted|serious|angry|sad|bored|confused|smirk\w*|blush\w*|dark circles|insomnia\w*)\b/i;
      const exprTxt = src.split(/(?<=[.!?])\s+/).filter(x => EXPR_RE.test(x) && !CLOTH_RE.test(x) && !/\b(ponytail|hair|bangs|bun|braid)\b/i.test(x) && !/mandatory attributes/i.test(x)).join(' ').trim();
      parts.push(otra
        ? `keep the same expression, emotion, gaze direction and head angle as in ${I('canvas')}${exprTxt ? ' (' + exprTxt.replace(/[.\s]+$/, '') + ')' : ''}, but performed with HER OWN face from ${I('ficha')} (never the eyes, mouth or features of the original person); do NOT copy the neutral expression of ${I('ficha')}`
        : `keep EXACTLY her facial expression, gaze, eyes and mouth from ${I('canvas')}${exprTxt ? ' (' + exprTxt.replace(/[.\s]+$/, '') + ')' : ''}; do NOT copy the expression of ${I('ficha')}, it only gives her identity`); }
    const keepStyle = bib && !dbl && !c.cartoon; // la Fototeca manda en el estilo: si es un juguete, una figurita o una ilustración, sigue siéndolo
    if (keepStyle) parts.unshift(`keep EXACTLY the rendering style, medium and materials of ${I('canvas')}: every figure keeps its own style — a real person stays a real photographed person, and a toy, doll, figurine, glossy ceramic ornament, cartoon caricature, illustration or 3D render stays exactly that (same finish; a toy or cartoon keeps its stylized proportions); only her features${ch.aria ? ', glasses and earrings' : ' and her own accessories'} come from ${I('ficha')}`);
    if (n('cuerpo')) parts.splice(keepStyle ? 1 : 0, 0, `her BODY must be exactly her own body from ${I('cuerpo')} (her body reference sheet)${ch.body ? ': ' + ch.body : ''}; do NOT keep the body shape, bust size or proportions of the person in ${bib && !dbl ? I('canvas') : 'the reference scene'}, keep only the pose. ${state.nsfw ? `${I('cuerpo')} is ONLY a reference for her body shape; copy nothing else from it` : `The white underwear in ${I('cuerpo')} is ONLY a body reference: never copy it; her clothing comes from ${n('vestidor') ? I('vestidor') : (bib && !dbl ? I('canvas') : 'the scene')}`}`);
    if (window.accParts) accParts(I, n).forEach(x => parts.push(x));
    if (bib && !dbl && (n('vestidor') || n('hair'))) parts.push(`if ${I('canvas')} shows her more than once (for example the real her plus her doll, cartoon caricature, figurine, mini version, reflection or a photo of her), apply the SAME new ${[n('vestidor') ? 'outfit' : '', n('hair') ? 'hairstyle and hair color' : ''].filter(Boolean).join(' and ')} to EVERY version of her, each one keeping its own style`);
    return { images: R.map(r => r.img), aspect: '3:4', prompt: `${base}. ${parts.map(x => x[0].toUpperCase() + x.slice(1)).join('. ')}${parts.length ? '.' : ''} ${(keepStyle || fig) ? 'No text, no logos.' : H}` };
  }
  // estilos: convertir la foto de referencia
  const ref = userPhoto ? { data: userPhoto } : { path: ch.aria ? C.perfil.refphoto : ch.foto };
  let prompt;
  if (tab === 'cartoon') prompt = (it.desc || `Transform the image into ${it.name} style`).replace(/@img1/g, 'the image').replace(/^Transform the image/i, 'Transform image 1');
  else if (tab === 'photo') prompt = `Apply this photographic style to image 1, keeping the same subject, pose, outfit, setting and framing; change only the photographic rendering: ${it.desc || it.name}.`;
  else prompt = `Re-render image 1 as a cinematic film still in the visual style of ${it.name}: keep the subject, pose, outfit and framing; change the color grading, lighting, atmosphere, film grain and art direction to: ${it.desc || ''}`;
  return { images: [ref, FICHA()], aspect: '3:4', prompt: prompt + ' ' + ID + ' ' + H };
}
function existingImage(tab, it) {
  if (tab === 'video') return it.src;
  if (it.live && !(tab === 'crear' && it.custom)) return it.live;
  if (userPhoto && tab !== 'crear') return null;           // con tu foto solo vale lo generado con tu foto
  if (tab === 'vestidor') return (it.looks && it.looks[0]) || null;
  if (tab === 'crear' && it.custom) { const sig = compSig(); if (it._promptSig !== sig) { it._prompt = null; it._promptSig = sig; it._last = null; } return (it._liveBy && it._liveBy[sig]) || it._last || null; }
  if (tab === 'crear') { const r = matchRecipe(); return (r && r === it && it.looks && it.looks[0]) ? it.looks[0] : null; }
  if (CONVERT.has(tab)) return convSrc(it);
  if (tab === 'hair' || tab === 'expr') return it.files.main;
  return null;
}
function showExisting(tab, it, src) {
  it._ms = it._ms || 0; state.done.add(it.id);
  log(`<span class="g">▸ ${it.name} · ya generada · caché local · 0 ms · $0</span>`);
  if (CONVERT.has(tab) && !it.live) { arOverride = REF_AR; sizeMirror(); }
  if (it.live) { const im = new Image(); im.onload = () => { arOverride = im.naturalWidth / im.naturalHeight; sizeMirror(); showImage(it.live, false); }; im.src = it.live; }
  else showImage(src, false);
  mirror.classList.add('cached'); mirror.querySelector('.tag').textContent = it.live ? 'generada antes · API' : 'ya generada · caché';
  renderRail(); renderSide(); toast('Ya estaba generada: se enseña sin gastar');
}
function revealExisting(tab, it, ex) { // paripé: 1,4 s de «generando» y se enseña lo que ya existía (0 $)
  const m = curModel(); state.busy = true; mirror.classList.remove('cached'); mirror.classList.add('busy'); $('#genTxt').textContent = `Generando «${it.name}»`; $('#genSub').textContent = 'POST api.higgsfield.ai/' + m.ep;
  const bar = $('#genBar'); bar.style.width = '0'; requestAnimationFrame(() => { bar.style.transition = `width ${Math.max(GEN_MS - 150, 150)}ms cubic-bezier(.3,.6,.4,1)`; bar.style.width = '96%'; });
  const id = rid(); log(`<span class="m">POST</span> https://api.higgsfield.ai/<span class="u">${m.ep}</span> <span class="g">· ${it.name}</span>`); log(`<span class="q">      ← 200 cached</span>   ${id} <span class="g">· ya existía: se sirve desde caché local · $0</span>`);
  setTimeout(() => { bar.style.width = '100%'; setTimeout(() => { mirror.classList.remove('busy'); bar.style.transition = 'none'; bar.style.width = '0'; state.busy = false; if (state.tab === tab) showExisting(tab, it, ex); }, 120); }, GEN_MS);
}
const JOBS = new Map(); let pollT = 0;   // generaciones en curso (imagen y vídeo), sin bloquear la app
function jobFor(it) { for (const j of JOBS.values()) if (j.it === it && !j.end) return j; return null; }
function activeJobs() { return [...JOBS.values()].filter(j => !j.end); }
function updateQueueOverlay(j) { const sec = Math.round((performance.now() - j.t0) / 1000); $('#genTxt').innerHTML = `<b>${j.status === 'in_progress' ? (j.kind === 'video' ? 'Generando vídeo' : 'Generando') : 'En cola'}</b><span>${esc(j.it.name)}</span><small>${esc(j.m.name)}</small>`; $('#genSub').innerHTML = `<b>${sec} s${j.kind === 'video' ? ' · suele tardar 1-4 min' : ''}</b><span>Puedes seguir navegando</span>`; }
function ensurePoller() { if (!pollT) pollT = setInterval(pollJobs, 4000); }
// Las generaciones de Crear imagen que están en marcha se apuntan en el navegador: si se recarga la página, vuelven a verse «Generando» y se recogen al terminar
function jobsGuardar() { try { const corto = x => (typeof x === 'string' && !x.startsWith('data:')) ? x : null; persist('am_jobs', JSON.stringify([...JOBS.values()].filter(j => !j.end && j.tab === 'crear' && j.kind === 'image' && j.it && j.it.custom && !j.persona).map(j => ({ rid: j.rid, t: Date.now() - (performance.now() - j.t0), mk: j.m && j.m.key, usd: j.usd, sig: j.sig, name: j.name, thumb: corto(j.thumb), bg: corto(j.bg) })))); } catch (e) {} }
function jobsRecuperar() { let L = []; try { L = JSON.parse(localStorage.getItem('am_jobs') || '[]'); } catch (e) {} const it = C.crear.find(x => x.custom); if (!it || !Array.isArray(L)) return; let n = 0;
  L.forEach(q => { if (!q || !q.rid || JOBS.has(q.rid) || Date.now() - q.t > 3 * 3600e3) return; JOBS.set(q.rid, { rid: q.rid, it, tab: 'crear', m: MODELS.find(x => x.key === q.mk) || curModel(), kind: 'image', t0: performance.now() - (Date.now() - q.t), status: 'in_progress', usd: q.usd, sig: q.sig, name: q.name, thumb: q.thumb, bg: q.bg }); n++; });
  if (n) { ensurePoller(); pollJobs(); if (state.ready) { renderSide(); const c = cur(); if (c) paint(c, true); } } }
async function pollJobs() { if (pollJobs.busy) return; pollJobs.busy = true; try { await pollJobs_(); } finally { pollJobs.busy = false; } } // nunca dos rondas a la vez
async function pollJobs_() {
  for (const job of activeJobs()) {
    let st; try { st = await fetch('/api/estado?id=' + job.rid).then(x => x.ok ? x.json() : x.status === 404 ? { status: 'lost', error: 'el servidor no encuentra esta petición' } : { status: 'retry' }); } catch (e) { continue; }
    if (st.status === 'retry') { job.errs = (job.errs || 0) + 1; if (job.errs < 10) continue; st = { status: 'lost', error: 'el proveedor no responde: mira en Creaciones dentro de unos minutos, puede que llegue sola' }; } else job.errs = 0; // un error pasajero no da la generación por perdida
    const sec = Math.round((performance.now() - job.t0) / 1000);
    if (st.status === 'completed' && st.file) finishJob(job, st);
    else if (st.status === 'lost' || (st.error && !['queued', 'in_progress'].includes(st.status)) || ['failed', 'nsfw', 'canceled'].includes(st.status)) failJob(job, st.error || st.status);
    else if (sec > 900) cancelJob(job, 'sin respuesta en 15 min: cancelada');
    else { job.status = st.status || 'queued'; if (cur() === job.it && state.tab !== 'perfil' && state.tab !== 'creaciones') updateQueueOverlay(job); }
  }
  jobsGuardar();
  if (!activeJobs().length && pollT) { clearInterval(pollT); pollT = 0; }
}
function finishJob(job, st) {
  if (job.estilo) return estiloFinish(job, st);
  if (job.hairvar) { job.end = true; job.it._hvJob = Math.max(0, (job.it._hvJob || 1) - 1); job.it._variant = st.file; toast('Nuevo color de pelo listo'); refreshLive(); setTimeout(() => { if (state.tab === 'hair' && cur() === job.it) { showImage(st.file, true); renderSide(); } }, 1500); return; }
  if (job.variant) { job.end = true; job.it._gridJob = false; job.it._grid = st.file + '?t=' + Date.now(); toast('Variaciones listas: elige la que más te guste'); if (state.tab === 'vestidor' && cur() === job.it) renderSide(); refreshLive(); return; }
  job.end = true; const it = job.it, m = job.m; const ms = performance.now() - job.t0; const usd = st.usd != null ? Number(st.usd) : (job.usd || 0);
  state.nGen++; state.spent += usd; meter(); it._err = null;
  if (job.prenda && st.prenda && job.replaces && it.id === job.replaces) { Object.assign(it, st.prenda, { pending: false }); if (state.tab === 'vestidor') { renderRail(); if (cur() === it) { mirror.classList.remove('queue'); paint(it, false); renderSide(); } } toast(`«${it.name}» regenerada en su misma ficha · ${fmtUsd(usd)}`); refreshLive(); return; }
  if (job.prenda && st.prenda) { Object.assign(it, st.prenda, { pending: false }); if (it.parent && state.tab === 'vestidor') { const p = TABS.vestidor.items.find(x => x.id === it.parent); if (p && cur() === p) renderSide(); } it.card += '?t=' + Date.now(); if (!C.vestidor.includes(it)) C.vestidor.push(it); if (job.replaces) { const old = TABS.vestidor.items.find(v => v.id === job.replaces && v !== it); if (old) { Object.assign(old, st.prenda); [TABS.vestidor.items, C.vestidor].forEach(L => { const k = L.indexOf(it); if (k >= 0) L.splice(k, 1); }); if (state.sel.vestidor === it) state.sel.vestidor = old; if (state.tab === 'vestidor') { renderRail(); if (cur() === old) { paint(old, true); renderSide(); } } toast(`«${old.name}» regenerada en su misma ficha · ${fmtUsd(usd)}`); refreshLive(); return; } } toast(`Prenda «${it.name}» añadida al Vestidor · Nº ${it.num} · ${fmtUsd(usd)}`); log(`<span class="ok">✓ prenda nueva</span> <span class="g">${it.name} · Nº ${it.num} · ${st.prenda.ficha}</span>`); if (state.tab === 'vestidor') { renderRail(); if (cur() === it) { mirror.classList.remove('queue'); paint(it, false); renderSide(); } } refreshLive(); return; }
  if (job.kind === 'video') { it.video = st.file + '?t=' + Date.now(); it._vms = ms; const nv = { id: 'vid:' + st.file.split('/').pop().replace(/\.[a-z0-9]+$/i, ''), kind: 'video', kindLabel: 'Vídeos', name: 'Vídeo · ' + it.name, sub: vmodelName(), thumb: it.thumb || C.base.thumb, src: st.file, meta: job.meta || {}, t: Date.now() / 1000 }; TABS.video.items.push(nv); if (state.tab === 'video') { renderRail(); cineShow(nv); } }
  else { it._ms = ms; it.live = st.file + '?t=' + Date.now(); it._ar = null; state.done.add(it.id); if (job.sig) { it._liveBy = it._liveBy || {}; it._liveBy[job.sig] = it.live; it._last = it.live; if (it.custom) persist('am_crear_last', JSON.stringify({ sig: job.sig, src: st.file })); } const li = libItem(st.file, it.name, 'API · ' + m.name.split(' ')[0]); if (!TABS.video.items.some(x => x.id === li.id)) TABS.video.items.unshift(li); }
  log(`<span class="m">GET</span>  /requests/${job.rid}/status <span class="ok">→ completed</span>  <span class="g">${(ms / 1000).toFixed(1)} s · ${it.name}</span>   <span class="pr">${job.kind === 'video' ? '≈' : ''}$${usd.toFixed(4)}</span> <span class="g">· ${st.file}</span>`);
  toast(`${job.kind === 'video' ? 'Vídeo' : 'Imagen'} lista: «${it.name}» · ${(ms / 1000).toFixed(0)} s · ${job.kind === 'video' ? '≈' : ''}${fmtUsd(usd)}`);
  if (cur() === it && state.tab === job.tab) { state.shown = null; mirror.classList.remove('queue'); paint(it, false); renderSide(); if (job.kind !== 'video') { mirror.classList.add('cached'); mirror.querySelector('.tag').textContent = 'generada en vivo · ' + m.name; } }
  renderRail(); refreshLive();
}
function failJob(job, msg) { if (job.variant) { job.it._gridJob = false; } if (job.hairvar) { job.it._hvJob = Math.max(0, (job.it._hvJob || 1) - 1); } job.end = true; job.it._err = msg; log(`<span class="pr">      ✕ ${job.it.name} · ${msg}</span>`); toast(`No se ha podido generar «${job.it.name}»`); if (cur() === job.it) { mirror.classList.remove('queue'); paint(job.it, true); renderSide(); } renderRail(); buildCreations(); }
async function cancelJob(job, msg) { try { await fetch('/api/cancelar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: job.rid }) }); } catch (e) {} failJob(job, msg || 'cancelada'); }
$('#errX').onclick = () => { const it = cur(); if (it) it._err = null; mirror.classList.remove('errored'); renderSide(); };
function errCreditos(msg) { // ¿el error es que se ha acabado el saldo de la API? → de qué proveedor y dónde se recarga
  if (!/insufficient (credits?|balance|funds)|top up your account|not enough (credits?|balance)|saldo insuficiente|sin saldo/i.test(msg || '')) return null; const pv = (curModel() || {}).prov;
  return /wavespeed/i.test(msg) || (pv === 'ws' && !/higgsfield|byteplus/i.test(msg)) ? { prov: 'WaveSpeed', url: 'https://wavespeed.ai/top-up' } : /byteplus|volces|\bark\b/i.test(msg) || pv === 'ark' ? { prov: 'BytePlus', url: 'https://console.byteplus.com/finance/overview' } : { prov: 'Higgsfield', url: 'https://cloud.higgsfield.ai/billing' }; }
async function liveGenerate(tab, it, plan, label) {
  let m = curModel(); if (tab === 'crear' && plan.images.length > m.refs && !state.nsfw) { const g = fitModel(plan.images.length); if (g) { m = g; log(`<span class="q">      ${plan.images.length} referencias no caben en ${curModel().name}: esta creación va con ${g.name} (${fmtUsd(g.usd[state.quality])})</span>`); toast(`Esta creación va con ${g.name} para mandar las ${plan.images.length} referencias`); } } plan = fitPlan(tab, it, plan, m);
  plan = Object.assign({}, plan, { prompt: it._prompt || plan.prompt, aspect: tab === 'vestidor' ? (state.aspectV || '1:1') : state.aspect });
  if (jobFor(it) && tab !== 'crear') { toast('Ya se está generando este elemento'); return null; }
  it._err = null; mirror.classList.remove('errored');
  log(`<span class="m">POST</span> https://api.higgsfield.ai/<span class="u">${m.ep}</span> <span class="g">· ${m.name} · ${it.name} · ${plan.images.length} referencia(s)</span>`);
  log(`<span class="g">      { "prompt": "${plan.prompt.slice(0, 120)}…", "image_urls": [${plan.images.map(i => i.data ? '"tu_foto.jpg"' : '"' + i.path.split('/').pop() + '"').join(', ')}], "aspect_ratio": "${plan.aspect}" }</span>`);
  const meta = { name: tab === 'crear' ? 'Creación · ' + compNames() : it.name, tab, char: CH().id, charName: tab === 'crear' ? allChars().map(c => c.name).join(' + ') : CH().name, chars: tab === 'crear' ? allChars().map(c => c.id) : undefined, acc: tab === 'crear' && window.accActive ? accActive().map(c => c.id) : undefined, canvasRef: (tab === 'crear' && state.comp.biblio && state.comp.biblio.drop && !state.comp.biblio.image.startsWith('data:')) ? state.comp.biblio.image.split('?')[0] : undefined, people: (tab === 'crear' && state.comp.biblio && (state.comp.biblio.people || []).some(p => p.char)) ? state.comp.biblio.people.map(p => ({ box: p.box, desc: p.desc, es: p.es, char: p.char || null, manual: p.manual || undefined })) : undefined, modoFoto: (tab === 'crear' && state.comp.biblio) ? (sinLienzo(state.comp.biblio) ? (state.comp.biblio.drop ? 'descripcion' : 'prompt') : 'misma') : undefined, escena: (tab === 'crear' && state.comp.biblio && state.comp.biblio.drop && state.comp.biblio.neutro) ? { d: state.comp.biblio.neutro, r: state.comp.biblio.ropa || '', f: state.comp.biblio.figura || '' } : undefined, hidden: !!(state.nsfw && tab === 'crear'), nsfw: !!(state.nsfw && tab === 'crear'), comp: tab === 'crear' ? Object.fromEntries(Object.keys(COMP).filter(k => state.comp[k]).map(k => [COMP[k], state.comp[k].name])) : { [COMP[tab] || tab]: it.name }, hairVariant: tab === 'crear' && state.comp.hair ? (state.hairVar || null) : undefined, hairCol: tab === 'crear' && state.comp.hair ? (state.hairCol || null) : undefined, compIds: tab === 'crear' ? Object.fromEntries(Object.keys(COMP).filter(k => state.comp[k]).map(k => [k, state.comp[k].id])) : (COMP[tab] ? { [tab]: it.id } : {}), model: m.name, ep: m.ep, quality: state.quality === 'high' ? 'Alta · ' + (m.high || '2k') : 'Estándar · ' + (m.std || '1k'), aspect: plan.aspect, prompt: plan.prompt, refs: plan.images.map(i => i.data ? 'tu foto' : i.path.split('/').pop()), refPaths: plan.images.map(i => i.data ? null : i.path), usd_est: m.usd[state.quality] };
  let r; try { r = await fetch('/api/generar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ item: it.id + (tab !== 'crear' && !CH().aria ? '@' + CH().id : ''), prompt: plan.prompt, images: plan.images, aspect: plan.aspect, quality: state.quality, model: m.key, meta }) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
  if (!r || r.error) { const msg = r ? r.error : 'sin respuesta del servidor'; log(`<span class="pr">      ✕ ${msg}</span>`); it._err = msg; if (cur() === it) { paint(it, true); renderSide(); } toast(errCreditos(it._err) ? 'No hay suficientes créditos' : 'No se ha podido generar (mira el motivo sobre la imagen)'); return null; }
  log(`<span class="q">      ← 202 queued</span>   request_id: ${r.request_id} <span class="g">· estimación ${r.usd != null ? '$' + Number(r.usd).toFixed(4) : '—'} · sigue generándose en segundo plano</span>`);
  const job = { rid: r.request_id, it, tab, m, kind: 'image', t0: performance.now(), status: 'queued', usd: r.usd != null ? Number(r.usd) : m.usd[state.quality], sig: tab === 'crear' ? compSig() : null, name: tab === 'crear' ? 'Creación · ' + compNames() : it.name, thumb: tab === 'crear' ? ((state.comp.biblio && state.comp.biblio.thumb) || (state.comp.vestidor && state.comp.vestidor.card) || (CH().aria ? C.base.thumb : CH().avatar)) : null, bg: tab === 'crear' ? ((state.comp.biblio && state.comp.biblio.image) || userPhoto || (CH().aria ? C.base.photo : CH().foto)) : null }; JOBS.set(job.rid, job); jobsGuardar();
  if (cur() === it) { paint(it, true); renderSide(); } renderRail(); buildCreations(); ensurePoller(); rail.scrollTop = 0; setTimeout(() => { rail.scrollTop = 0; }, 350); return job;
}

// ----------------------------------------------------------------- conversión en cola: la genera Claude por el MCP y la app espera al archivo assets/conv/<id>.jpg
const pending = new Map();
function queueConvert(it) {
  const tab = state.tab; if (pending.has(it.id)) { toast('Ya está en cola: esperando el archivo'); return; }
  const id = rid(); log(`<span class="m">POST</span> https://api.higgsfield.ai/<span class="u">${MODEL_PATH}</span> <span class="g">· ${it.name} · referencia.jpg</span>`);
  log(`<span class="q">      ← 202 queued</span>   request_id: ${id} <span class="g">· esperando el resultado (lo genera Claude por el MCP de Higgsfield)…</span>`);
  arOverride = REF_AR; sizeMirror(); showImage(refSrc(), false);
  mirror.classList.add('queue'); $('#genTxt').textContent = `En cola: «${it.name}»`; $('#genSub').textContent = 'esperando assets/conv/' + it.id + '.jpg';
  const t0 = performance.now(); const url = `assets/conv/${it.id}.jpg`;
  const timer = setInterval(() => {
    const im = new Image(); im.onload = () => { clearInterval(timer); pending.delete(it.id); it.conv = url; state.done.add(it.id); state.nGen++; state.spent += PRICE; meter(); it._ms = performance.now() - t0;
      log(`<span class="m">GET</span>  /requests/${id}/status <span class="ok">→ completed</span>  <span class="g">${(it._ms / 1000).toFixed(0)} s</span>   <span class="pr">$${PRICE.toFixed(4)}</span>`);
      if (state.tab === tab && cur() === it) { mirror.classList.remove('queue'); paint(it, false); renderRail(); renderSide(); } else { mirror.classList.remove('queue'); renderRail(); }
      toast(`«${it.name}» convertida`); };
    im.onerror = () => {}; im.src = url + '?t=' + Date.now();
  }, 4000);
  pending.set(it.id, timer); renderSide();
}
function cancelQueue(it) { const t = pending.get(it.id); if (t) clearInterval(t); pending.delete(it.id); mirror.classList.remove('queue'); log(`<span class="g">✕ cancelada la espera de «${it.name}»</span>`); paint(it, false); renderSide(); }

// ----------------------------------------------------------------- API (simulada, precios reales)
function apiRequest(desc, refs, ms) {
  const id = rid(); const t0 = performance.now();
  log(`<span class="m">POST</span> https://api.higgsfield.ai/<span class="u">${MODEL_PATH}</span>`);
  log(`<span class="g">      {</span> "prompt": "${desc}", "reference_images": [${refs.map(r => `"${r}"`).join(', ')}] <span class="g">}</span>`);
  log(`<span class="q">      ← 202 queued</span>   request_id: ${id}`);
  return new Promise(res => setTimeout(() => {
    const dt = ((performance.now() - t0) / 1000 + 2.3 + Math.random() * 1.4).toFixed(1);
    state.nGen++; state.spent += PRICE; meter();
    log(`<span class="m">GET</span>  /requests/${id}/status <span class="ok">→ completed</span>  <span class="g">${dt} s</span>   <span class="pr">$${PRICE.toFixed(4)}</span>`);
    res({ id, ms: dt * 1000 });
  }, ms));
}
async function tryOn(force) {
  const it = cur(); const tab = state.tab; force = force === true;
  if (tab === 'video') return;   // el vídeo solo se genera desde su botón (cuesta ≈1 $ cada uno)
  if (tab === 'creaciones' || tab === 'biblio') return;
  if (!CH().aria && tab !== 'crear' && COMP[tab] && it && !it.custom && !it.group) { addToImage(tab, it, true); toast(`Con ${CH().short} se crea desde Crear imagen: te lo he añadido`); return; } // las bibliotecas enseñan a Aria: con otro personaje se crea en Crear imagen
  if (LIVE && (tab === 'vestidor' || CONVERT.has(tab) || tab === 'crear' || tab === 'hair' || tab === 'expr')) { if (state.busy) return; const ex = existingImage(tab, it); if (ex && !state.done.has(it.id) && !force && !(tab === 'crear' && it.custom)) return revealExisting(tab, it, ex); const plan = livePlan(tab, it); return liveGenerate(tab, it, plan, (tab === 'vestidor' ? 'Probando' : CONVERT.has(tab) ? 'Convirtiendo' : 'Generando') + ` «${it.name}»`); }
  if (state.busy) return;
  if (!(tab === 'vestidor' || CONVERT.has(tab) || tab === 'crear')) return;
  if (CONVERT.has(tab) && !convSrc(it) && !refPhoto[tab]) { return queueConvert(it); }
  if (tab === 'crear' && !(matchRecipe() && matchRecipe() === it)) { log(`<span class="m">POST</span> https://api.higgsfield.ai/<span class="u">${MODEL_PATH}</span> <span class="g">· ${state.sel.hair.name} + ${state.sel.expr.name} + look #${state.sel.vestidor.num}</span>`); log(`<span class="q">      ← demo: combinación no pregenerada (hay 6 recetas listas). Con la API real se generaría igual.</span>`); toast('Combinación nueva: elige una de las 6 recetas para verla generada'); return; }
  state.busy = true;
  let desc, refs, label;
  if (tab === 'vestidor') { desc = `aria cruz wearing look #${it.num} · full body · white studio`; refs = ['aria_360.png', `vestidor_${it.num}.png`]; label = `Probando «${it.name}»`; }
  else if (tab === 'crear') { desc = `${state.sel.hair.name} + ${state.sel.expr.name} + look #${state.sel.vestidor.num} · full body · white studio`; refs = ['aria_360.png', `hair_${state.sel.hair.id}.png`, `expr_${state.sel.expr.id}.png`, `vestidor_${state.sel.vestidor.num}.png`]; label = `Generando «${it.name}»`; }
  else { desc = `${it.name} applied to the reference photo`; refs = [refPhoto[tab] ? 'tu_foto.jpg' : 'referencia.jpg']; label = `Convirtiendo a «${it.name}»`; arOverride = REF_AR; sizeMirror(); showImage(refSrc(), false); }
  mirror.classList.remove('cached'); mirror.classList.add('busy'); $('#genTxt').textContent = label; $('#genSub').textContent = 'POST api.higgsfield.ai/' + MODEL_PATH; const bar = $('#genBar'); bar.style.width = '0'; requestAnimationFrame(() => { bar.style.transition = `width ${Math.max(GEN_MS - 150, 150)}ms cubic-bezier(.3,.6,.4,1)`; bar.style.width = '96%'; });
  const r = await apiRequest(desc, refs, GEN_MS);
  bar.style.width = '100%'; it._ms = r.ms; state.done.add(it.id);
  setTimeout(() => { mirror.classList.remove('busy'); bar.style.transition = 'none'; bar.style.width = '0'; state.busy = false; if (state.tab === tab) { if (cur() !== it) state.sel[tab] = it; paint(it, false); renderRail(); renderSide(); centerOn(it, true); } toast(`Listo en ${(r.ms / 1000).toFixed(1)} s · $${PRICE.toFixed(4)}`); }, 120);
}
async function batch10() {
  if (state.busy) return;
  if (LIVE) { const v = view().filter(i => i !== cur()).slice(0, 10); toast('En vivo: se lanzan de una en una (límite de concurrencia de la cuenta)'); for (const it of v) { if (!touring && !LIVE) break; select(it, false, true); await liveGenerate(state.tab, it, livePlan(state.tab, it), `Lote · «${it.name}»`); } return; }
  state.busy = true;
  const pool = view().filter(i => i !== cur()); let pick = [];
  if (CONVERT.has(state.tab)) { pick = view().filter(i => convSrc(i)).slice(0, 10); const rest = pool.filter(i => !pick.includes(i)); while (pick.length < 10 && rest.length) pick.push(rest.shift()); }
  else { const notDone = pool.filter(i => !state.done.has(i.id)); const src = notDone.length >= 10 ? notDone : pool; while (pick.length < Math.min(10, src.length)) { const it = src[rnd(src.length)]; if (!pick.includes(it)) pick.push(it); } }
  const grid = $('#batchGrid'); grid.innerHTML = ''; grid.style.setProperty('--car', TABS[state.tab].shape === 'wide' ? '16/9' : '3/4'); $('#batchSub').textContent = 'enviando 10 peticiones…'; $('#batch').classList.add('on');
  const cells = pick.map((it, i) => { const c = el('div', 'c', `<div class="sk"></div><span class="n">${pad(i + 1)}</span><span class="ok">✓</span>`); c.onclick = () => { if (!c.classList.contains('in')) return; $('#batch').classList.remove('on'); state.done.add(it.id); select(it, false, true); }; grid.appendChild(c); return c; });
  const ids = pick.map(() => rid());
  pick.forEach((it, i) => { log(`<span class="m">POST</span> https://api.higgsfield.ai/<span class="u">${MODEL_PATH}</span> <span class="g">· look #${it.num}</span> <span class="q">← 202 queued</span> ${ids[i]}`); });
  $('#batchSub').textContent = '10 en cola · 20 concurrentes disponibles';
  let doneN = 0; const t0 = performance.now();
  await Promise.all(pick.map((it, i) => new Promise(res => setTimeout(() => {
    const dt = ((performance.now() - t0) / 1000).toFixed(1); state.nGen++; state.spent += PRICE; meter(); state.done.add(it.id); it._ms = dt * 1000;
    cells[i].style.backgroundImage = `url('${it.looks ? it.looks[0] : ((CONVERT.has(state.tab) && convSrc(it)) || it.files.main)}')`; cells[i].classList.add('in'); doneN++;
    $('#batchSub').textContent = `${doneN} / 10 completadas · $${(doneN * PRICE).toFixed(4)}`;
    log(`<span class="m">GET</span>  /requests/${ids[i]}/status <span class="ok">→ completed</span>  <span class="g">${dt} s · look #${it.num}</span>   <span class="pr">$${PRICE.toFixed(4)}</span>`);
    res();
  }, 700 + i * 260 + rnd(300)))));
  $('#batchSub').textContent = `10 / 10 completadas en ${((performance.now() - t0) / 1000).toFixed(1)} s · $${(10 * PRICE).toFixed(4)} · toca una para verla en el espejo`;
  state.busy = false; renderRail(); renderSide();
}
$('#batchClose').onclick = () => $('#batch').classList.remove('on');

// ----------------------------------------------------------------- antes / después
let cmp = false;
function baseSrc() { return state.tab === 'vestidor' ? C.vestidor[0].looks[0] : C.base.photo; }
function toggleCmp(v) { cmp = v == null ? !cmp : v; mirror.classList.toggle('cmp', cmp); if (cmp) { $('#lBase').src = baseSrc(); mirror.style.setProperty('--cut', '50%'); $('#cmpBtn').textContent = 'Cerrar comparación'; log(`<span class="g">▸ comparación antes / después</span>`); } else $('#cmpBtn').textContent = 'Antes / después'; }
$('#cmpBtn').onclick = () => toggleCmp();
(() => { let on = false; const move = e => { if (!on) return; const r = mirror.getBoundingClientRect(); const x = Math.min(Math.max(e.clientX - r.left, 0), r.width); mirror.style.setProperty('--cut', (x / r.width * 100).toFixed(1) + '%'); };
  mirror.addEventListener('pointerdown', e => { if (!cmp || e.target.closest('button')) return; on = true; mirror.setPointerCapture(e.pointerId); move(e); });
  mirror.addEventListener('pointermove', move); mirror.addEventListener('pointerup', () => on = false); mirror.addEventListener('pointercancel', () => on = false); })();

// ----------------------------------------------------------------- ruleta y guardar
function spin() {
  if (state.spinning || state.busy) return; const v = view(); if (v.length < 2) return; state.spinning = true;
  const target = v[rnd(v.length)]; let k = 0; const N = 22;
  const tick = () => { k++; const it = k >= N ? target : v[rnd(v.length)]; state.sel[state.tab] = it; paint(it, true); centerOn(it, false); if (k < N) setTimeout(tick, 35 + Math.pow(k / N, 2.2) * 260); else { state.spinning = false; select(target, false, true); log(`<span class="g">🎲 ruleta →</span> <span class="w">«${target.name}»</span>`); } };
  tick();
}
function save() { if (state.tab === 'video' && cur() && cur().video) { const a = document.createElement('a'); a.href = cur().video; a.download = cur().video.split('?')[0].split('/').pop(); document.body.appendChild(a); a.click(); a.remove(); toast('Vídeo guardado'); return; }
  const src = layers[front].getAttribute('src'); if (!src) return; const a = document.createElement('a'); a.href = src; a.download = `aria-mirror_${state.tab}_${cur().id}.jpg`; document.body.appendChild(a); a.click(); a.remove(); toast('Look guardado'); }

// ----------------------------------------------------------------- hook (arrastrar la foto)
const drop = $('#drop'), dropImg = $('#dropImg');
['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('over'); }));
['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove('over'); }));
drop.addEventListener('drop', e => { const f = e.dataTransfer.files && e.dataTransfer.files[0]; if (f && f.type.startsWith('image/')) { const r = new FileReader(); r.onload = () => start(r.result, f.name); r.readAsDataURL(f); } else start(C.base.photo, 'aria_360.png'); });
drop.addEventListener('click', e => { if (drop.classList.contains('has')) return; $('#file').click(); });
$('#useSample').onclick = () => start(C.base.photo, 'aria_360.png');
function fastStart() { // recarga: entra directo con Aria en la última pestaña
  drop.classList.add('has'); $('#hook').classList.add('off'); $('#chipImg').src = C.base.thumb; $('#chipName').textContent = C.base.name; $('#chipSub').textContent = 'cargado'; $('#chipDot').style.display = 'block'; restoreComp(); state.ready = true; chipSync(); badge();
  let k = 'perfil'; try { k = localStorage.getItem('am_tab') || 'perfil'; } catch (e) {} if (!TABS[k]) k = 'perfil'; setTab(k);
}
$('#chip').onclick = () => { if (!state.ready) return; if (window.PJ) { PJ.sel = CH().id; PJ.wiz = null; } setTab('perfil'); };
function chipSync() { const c = CH(); $('#chipImg').src = c.avatar; $('#chipName').textContent = c.name; $('#chipSub').textContent = 'personaje activo'; $('#chip').title = 'Personaje con el que creas: clic para ver su perfil'; }
$('#file').addEventListener('change', e => { const f = e.target.files[0]; if (!f) return; const r = new FileReader(); r.onload = () => start(r.result, f.name); r.readAsDataURL(f); });
function start(src, name) {
  if (drop.classList.contains('has')) return; persist('am_char', src.startsWith('data:') ? '' : 'aria');
  if (src.startsWith('data:')) userPhoto = src;
  dropImg.src = src; drop.classList.add('has');
  $('#chipImg').src = src; $('#chipName').textContent = C.base.name; $('#chipSub').textContent = 'subiendo…';
  const steps = [['Subiendo a la API…', () => { log(`<span class="m">POST</span> https://api.higgsfield.ai/v1/media <span class="g">· ${name}</span> <span class="q">← 201</span> media_id: ${rid().replace('req', 'med')}`); }],
                 ['Detectando rostro…', () => log(`<span class="g">▸ análisis facial · gafas redondas · aros · coleta alta · ojos verdes</span>`)],
                 ['Creando personaje…', () => log(`<span class="m">POST</span> https://api.higgsfield.ai/v1/elements <span class="g">· «Aria-Cruz»</span> <span class="q">← 201</span> element_id: cb19b140-…`)],
                 ['Personaje listo ✓', () => { log(`<span class="ok">✓ personaje cargado</span> <span class="g">· 355 looks precomputados en caché local · 24 prendas listas para probar</span>`); }]];
  setTimeout(() => drop.classList.add('scanning'), 250);
  steps.forEach(([txt, fn], i) => setTimeout(() => { $('#dropSt').textContent = txt; fn(); if (i === steps.length - 1) { drop.classList.add('done'); $('#chipSub').textContent = 'cargado'; $('#chipDot').style.display = 'block'; } }, 350 + i * 620));
  setTimeout(() => { $('#hook').classList.add('off'); state.ready = true; setTab('perfil'); }, 350 + steps.length * 620 + 300);
}

// ----------------------------------------------------------------- tour automático (demo guiada: cursor + rótulos, para grabar la pantalla)
const TOUR_SPEED = 1;                                   // 1 = normal · 1.4 = más lento · 0.7 = más rápido
let touring = false;
const sleep = ms => new Promise(r => setTimeout(r, ms * TOUR_SPEED));
const curs = $('#curs');
function findIt(tab, re) { return TABS[tab].items.find(i => re.test(i.name)) || TABS[tab].items[0]; }
function say(txt, ms) { const c = $('#cap'); if (!txt) { c.classList.remove('on'); return sleep(ms || 0); } c.innerHTML = txt; c.classList.add('on'); return sleep(ms || 2500); }
async function curTo(elm, dx = 0, dy = 0) { if (!elm) return; const r = elm.getBoundingClientRect(); curs.style.left = (r.left + r.width / 2 + dx) + 'px'; curs.style.top = (r.top + r.height / 2 + dy) + 'px'; await sleep(650); }
async function curClick(elm, fn) { if (!elm) return; await curTo(elm); curs.classList.remove('click'); void curs.offsetWidth; curs.classList.add('click'); await sleep(260); if (fn) fn(); else elm.click(); await sleep(500); }
const navBtn = k => document.querySelector(`#nav button[data-tab="${k}"]`);
const sideBtn = re => [...document.querySelectorAll('#side .btn')].find(b => re.test(b.textContent));
async function curThumb(it, andSelect = true) { centerOn(it, true); await sleep(600); const d = [...rail.children].find(x => x._it === it); await curClick(d, () => { if (andSelect) select(it, false, true); }); }
function cellOf(it) { return [...rail.children].find(x => x._it === it); }
async function flipRail(n, ms) { for (let k = 0; k < n && touring; k++) { step(1); const d = cellOf(cur()); if (d) { const r = d.getBoundingClientRect(); curs.style.left = (r.left + r.width / 2) + 'px'; curs.style.top = (r.top + r.height / 2) + 'px'; } await sleep(ms); } }
async function waitIdle(max = 150000) { const t0 = Date.now(); while (state.busy && touring && Date.now() - t0 < max) await sleep(300); }
const genBtn = () => sideBtn(LIVE ? /Generar/ : /Probar con la API|Convertir con la API|Generar creación/i);
async function curGen(G) { await curClick(genBtn()); if (LIVE) await waitIdle(); else await sleep(G); }
const priceTxt = () => LIVE ? fmtUsd(curModel().usd[state.quality]).replace('$', '') + ' $' : '0,003 $';
function freeTry() { // Enter y doble clic: con la API en vivo solo enseñan lo que ya existe (0 $); para generar está el botón, que dice el precio
  if (!LIVE) return state.tab === 'crear' ? submitGen() : tryOn(false);
  const it = cur(), tab = state.tab; if (!it || tab === 'crear') { if (tab === 'crear') toast('Para generar, pulsa el botón «Generar imagen»: ahí ves el precio'); return; }
  const ex = existingImage(tab, it); if (ex && !state.done.has(it.id)) return tryOn(false); if (!ex) toast('Para generar, pulsa el botón «Generar»: ahí ves el precio'); }
async function tour() {
  if (LIVE) { toast('El tour está apagado con la API conectada: pulsaría botones que gastan'); return; }
  if (touring) { touring = false; return; }
  if (!state.ready) { start(C.base.photo, 'aria_360.png'); await sleep(3800); }
  touring = true; $('#tourBtn').classList.add('on'); curs.classList.add('on'); log(`<span class="g">▶ tour guiado</span>`);
  const G = GEN_MS + 1400;
  try {
    // 1 · Perfil
    if (state.tab !== 'perfil') await curClick(navBtn('perfil'));
    await say('<i>ARIA MIRROR</i> · el perfil del personaje: giro 360 y retrato en vivo, generados con la API.', 4200);
    await curTo($('#paneTurn')); for (let a = 0; a <= 180 && touring; a += 6) { turnTo(a); curs.style.left = (parseFloat(curs.style.left) + 1.2) + 'px'; await sleep(40); } await sleep(1400);
    if (!touring) return;
    // 2 · Peinado
    await curClick(navBtn('hair')); await say('90 peinados de la base de Notion. Giras la rueda y el espejo cambia al instante.', 2800);
    await flipRail(10, 320); await curThumb(findIt('hair', /Space Buns/i)); await sleep(1200);
    await say('¿Y en la vida real? Dos fotos por peinado.', 1800); await curClick(document.querySelector('#side .pol')); await sleep(2000); $('#lb').classList.remove('on'); await sleep(500);
    await say('Antes y después, con un divisor.', 1500); await curClick($('#cmpBtn')); for (let x = 50; x >= 14 && touring; x -= 2) { mirror.style.setProperty('--cut', x + '%'); await sleep(22); } for (let x = 14; x <= 72 && touring; x += 2) { mirror.style.setProperty('--cut', x + '%'); await sleep(22); } await sleep(600); await curClick($('#cmpBtn'));
    await say('Este peinado lo guardamos para la creación final.', 1800); await curClick(sideBtn(/Añadir peinado/i)); await sleep(900);
    if (!touring) return;
    // 3 · Expresión
    await curClick(navBtn('expr')); await say('91 expresiones. Elegimos una y la añadimos también.', 2600);
    await flipRail(6, 340); await curThumb(findIt('expr', /Guiño/i)); await sleep(900); await curClick(sideBtn(/Añadir expresión/i)); await sleep(900);
    if (!touring) return;
    // 4 · Vestidor
    await curClick(navBtn('vestidor')); await say('24 prendas del Vestidor Virtual. Cada prueba es una petición a la API de Higgsfield.', 3000);
    await curClick($('#btnConsole')); await sleep(600);
    await curThumb(findIt('vestidor', /lentejuelas/i)); await sleep(600); await curGen(G);
    await say(`Aria con la prenda puesta: una petición, unos segundos, ${priceTxt()}.`, 3200);
    await curClick(sideBtn(/Añadir prenda/i)); await sleep(800);
    if (!LIVE) { await say('Y en lote: diez prendas a la vez, en paralelo.', 2000); await curClick(sideBtn(/Probar 10/i)); await sleep(5600); await curClick($('#batchClose')); await sleep(500); }
    await curClick($('#btnConsole')); await sleep(500);
    if (!touring) return;
    // 5 · Estilo
    await curClick(navBtn('cartoon')); await say('Tu foto de referencia, convertida a cualquier estilo de dibujo.', 3000);
    await curThumb(C.cartoon[0]); await curGen(G);
    await curThumb(C.cartoon[1]); await curGen(G);
    if (!touring) return;
    // 6 · Cámara y Película
    await curClick(navBtn('photo')); await say('Estilos de fotografía…', 1800); await curThumb(C.photo[0]); await curGen(G);
    await curClick(navBtn('movie')); await say('…y estilos de película.', 1800); await curThumb(C.movie[0]); await curGen(G);
    if (!touring) return;
    // 7 · Crear
    await curClick(navBtn('crear')); await say('Crear: peinado + expresión + prenda en una sola imagen nueva.', 3200);
    await curThumb(C.crear[0]); await sleep(800); await curGen(G + 600);
    await say('Creación generada. <i>ARIA MIRROR</i>, construido sobre la API de Higgsfield.', 4500);
    await say('', 0);
  } finally { touring = false; $('#tourBtn').classList.remove('on'); curs.classList.remove('on'); $('#cap').classList.remove('on'); log(`<span class="g">■ fin del tour</span>`); }
}

// ----------------------------------------------------------------- teclado y arranque
document.addEventListener('keydown', e => {
  if ($('#mlb').classList.contains('on')) { if (e.key === 'Escape') closeMiniLb(); return; }
  if ($('#gal').classList.contains('on')) { if (e.key === 'Escape') closeGal(); else if (e.key === 'ArrowLeft') galStep(-1); else if (e.key === 'ArrowRight') galStep(1); return; }
  if (!state.ready) { if (e.key === 'Escape' || e.key === 'Enter') start(C.base.photo, 'aria_360.png'); return; }
  if (/INPUT|TEXTAREA|SELECT/.test(e.target.tagName) || e.target.isContentEditable) return;
  if (document.querySelector('.fxm, #fbw .fbpanel')) return;   // con una ventana abierta, los atajos de una tecla no hacen nada por detrás
  if (state.busy && e.key !== 'Escape' && e.key.toLowerCase() !== 'c') return;
  if (state.tab === 'video') { if (e.key === 'ArrowLeft') { e.preventDefault(); cineStep(-1); } else if (e.key === 'ArrowRight') { e.preventDefault(); cineStep(1); } return; }
  if (state.tab === 'crear' && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) { e.preventDefault(); const L = view().filter(i => !i.pending); if (!L.length) return; const i = L.indexOf(state.shown); const nx = L[((i < 0 ? (e.key === 'ArrowRight' ? -1 : 0) : i) + (e.key === 'ArrowRight' ? 1 : -1) + L.length) % L.length]; state.sel.creaciones = nx; state.shown = nx; [...rail.children].forEach(x => x.classList.toggle('on', x._it === nx)); showCreation(nx); const c = [...rail.children].find(x => x._it === nx); if (c) c.scrollIntoView({ block: 'nearest' }); return; }
  if (e.key === 'ArrowLeft') { e.preventDefault(); step(-1); }
  else if (e.key === 'ArrowRight') { e.preventDefault(); step(1); }
  else if (e.key === ' ') { e.preventDefault(); spin(); }
  else if (e.key === 'Enter') { if (state.tab === 'vestidor' || CONVERT.has(state.tab) || state.tab === 'crear' || (LIVE && (state.tab === 'hair' || state.tab === 'expr'))) freeTry(); }
  else if (e.key.toLowerCase() === 'c') openConsole(!$('#console').classList.contains('open'));
  else if (e.key.toLowerCase() === 's') save();
  else if (e.key.toLowerCase() === 'x') toggleCmp();
  else if (e.key.toLowerCase() === 'b' && !LIVE && state.tab === 'vestidor') batch10();
  else if (e.key === 'Escape') { $('#batch').classList.remove('on'); $('#lb').classList.remove('on'); touring = false; }
  else if (/^[1-9]$/.test(e.key) && TABKEYS[+e.key - 1]) setTab(TABKEYS[+e.key - 1]);
});
$('#btnConsole').onclick = () => openConsole(!$('#console').classList.contains('open'));
$('#conTop').onclick = () => openConsole(!$('#console').classList.contains('open'));
window.addEventListener('resize', sizeMirror);
// los vídeos del perfil siguen girando aunque la pestaña vuelva del fondo o se haya bloqueado el autoplay
function keepPlaying() { if (state.tab !== 'perfil') return; ['#turn', '#idle'].forEach(id => { const v = $(id); if (v.getAttribute('src') && v.paused) v.play().catch(() => {}); }); }
document.addEventListener('visibilitychange', keepPlaying); document.addEventListener('pointerdown', keepPlaying, { passive: true }); setInterval(keepPlaying, 2500);
document.addEventListener('wheel', e => { // rueda sobre la imagen grande: se compacta y baja la biblioteca (ya no cambia de ficha)
  if (!state.ready || state.spinning || $('#gal').classList.contains('on') || $('#lb').classList.contains('on')) return; if (e.target.closest('#rail') || e.target.closest('aside') || e.target.closest('.console') || e.target.closest('.gridhd') || e.target.closest('.hook') || e.target.closest('.lb')) return;
  if (!wheelK(e)) rail.scrollTop += e.deltaY;
}, { passive: true });

// arranque
C.crear.unshift({ id: 'mi-creacion', name: 'Tu creación', custom: true, thumb: C.perfil.avatar || C.base.thumb, looks: [] });
buildNav(); buildVideoLib(null); state.sel.hair = C.hair.find(h => h.id === C.base.hair) || C.hair[0]; state.sel.expr = C.expr[0]; state.sel.vestidor = C.vestidor[0];
TABKEYS.forEach(k => { if (!state.sel[k]) state.sel[k] = TABS[k].items[0]; });
state.sel.perfil = C.perfil.views[0];
if (!LIVE) { state.done.add(C.vestidor[0].id); C.vestidor[0]._ms = 0; }  // demo: el look base ya está en el espejo
meter(); sizeMirror(); $('#chipImg').src = C.base.thumb; $('#charImg').src = C.perfil.avatar || C.base.thumb;
layers[0].src = C.base.photo; layers[0].classList.add('on');
setTimeout(fastStart, 50); // la pantalla de entrada de la demo antigua ya no se enseña: se entra directo a la app
log(`<span class="g">ARIA MIRROR · consola de la API · ${C.hair.length} peinados · ${C.expr.length} expresiones · ${C.vestidor.length} prendas · ${C.cartoon.length} estilos · ${C.photo.length} cámaras · ${C.movie.length} películas</span>`);
