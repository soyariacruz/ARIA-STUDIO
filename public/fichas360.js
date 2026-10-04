// ARIA STUDIO · FICHAS DE ARIA (v114) · la principal: 4 vistas de la cara + cuerpo de frente + cuerpo de perfil (16:9)
// Pestaña «Fichas 360» del Perfil. La ficha principal es la COMBINADA: sus 4 vistas (2x2) a la izquierda + su cuerpo entero del cuello a los pies a la derecha.
// «＋ Nueva ficha»: paso a paso (1 personaje → 2 ropa del Vestidor → 3 otros objetos → 4 generar) y la ficha nueva sale DE UNA VEZ, editando la principal.
// El editor (✎ Editar) cambia una vista o el cuerpo: se generan varias versiones, se ven en su sitio y se elige la mejor.
(function () {
  const F3 = window.F3 = { open: false, prendas: [], acc: [], extras: [], jobs: [], sending: false, pick: null, nombre: '' };
  const pjOf = () => F3.owner && window.PJ ? (PJ.list || []).find(p => p.id === F3.owner) || null : null;   // el creador «Nueva ficha» sirve para Aria (owner vacío) y para cualquier personaje
  const OW = () => F3.owner || 'aria';
  const P = () => { const p = pjOf(); if (!p) return C.perfil; return { name: p.nombre, avatar: p.avatar || p.foto, combo: p.combo || p.ficha360, comboThumb: p.combo || p.ficha360, ficha: p.ficha360, complementos: p.complementos || [], alt: { nueva: { combo: p.fichasVers || [] } }, fichas: p.fichas || [] }; };
  const extra = () => P().fichas360 || [];
  const prenda = id => (TABS.vestidor.items || []).find(v => v.id === id);
  const dl = (src) => { const a = document.createElement('a'); a.href = src; a.download = src.split('/').pop().split('?')[0]; document.body.appendChild(a); a.click(); a.remove(); };
  const post = async (url, body) => { let r; try { r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; } if (!r || !r.ok) { toast('No se pudo: ' + (r ? r.error : 'sin respuesta')); return null; } return r; };
  async function api(body) { const r = await post('/api/fichas360', body); if (!r) return null; P().fichas360 = r.list; P().ficha = r.ficha; return r; }
  async function panelApi(body) { const r = await post('/api/ficha_panel', body); if (r) Object.assign(P(), r.perfil); return r; }
  async function comboApi(body) { const r = await post('/api/ficha_combo', body); if (r) Object.assign(P(), r.perfil); return r; }
  const comboSig = () => (P().ficha || '') + '|' + (P().comboBody || P().cuerpo || '') + '|' + (P().comboSide || P().cuerpo || '');
  let ensuring = false;
  async function ensureCombo() { if (ensuring || (P().combo && P().comboSig === comboSig())) return; ensuring = true; const r = await comboApi({ action: 'ensure' }); ensuring = false; if (r && state.tab === 'perfil' && !F3.open) renderProfile(); }
  const principal = () => P().combo || P().ficha;
  const scrollTop = () => setTimeout(() => { const h = document.querySelector('.nfwrap') || document.querySelector('.f3wrap'); if (!h) return; let s = h.parentElement; while (s && s !== document.body && !(s.scrollHeight > s.clientHeight + 4 && /auto|scroll/.test(getComputedStyle(s).overflowY))) s = s.parentElement; const tb = document.querySelector('.pjtabs'); if (s && s !== document.body) s.scrollTop = Math.max(0, (tb || h).getBoundingClientRect().top - s.getBoundingClientRect().top + s.scrollTop - 12); }, 30);
  function abrirNueva(owner) { const o = owner && owner !== 'aria' ? owner : null; if ((F3.owner || null) !== o) Object.assign(F3, { prendas: [], acc: [], extras: [], pick: null }); F3.owner = o; F3.open = true; window.pjScrollTop = true; renderProfile(); }
  window.nfOpenFor = abrirNueva; window.nfJobs = id => F3.jobs.filter(j => (j.owner || 'aria') === id);
  window.nfOpen = abrirNueva;

  // ------------------------------------------------ pestaña «Fichas 360»: la principal (combinada) y su cuerpo arriba + fichas creadas abajo
  window.f3Gallery = function () {
    if (!F3.open) F3.owner = null;   // la galería de esta pestaña es la de Aria
    ensureCombo();
    const w = el('div', 'f3wrap');
    const top = el('div', 'f3main');
    const big = (src, title, sub, kind, cls) => { const nb = running(kind).length; const d = el('div', 'f3card big ' + (cls || ''), `<div class="f3img"><img src="${src}" alt="">${nb ? `<span class="f3busy"><i class="spin"></i>${nb === 1 ? 'Generando una versión' : `Generando ${nb} versiones`}</span>` : ''}<button class="f3edit">✎ Editar</button></div><b>${title}</b><small>${sub}</small>`); d.querySelector('.f3edit').onclick = e => { e.stopPropagation(); openFX(kind); }; d.querySelector('.f3img img').onclick = () => lightbox(src, title); top.appendChild(d); };
    big(principal(), 'Ficha principal', 'sus cuatro vistas y su cuerpo entero de frente y de perfil, del cuello a los pies', 'combo', 'combo');
    { const col = el('div', 'f3sidecol'); const small = (src, title, sub, kind) => { const nb = running(kind).length; const d = el('div', 'f3card big mini', `<div class="f3img"><img src="${src}" alt="">${nb ? `<span class="f3busy"><i class="spin"></i>Generando</span>` : ''}<button class="f3edit">✎ Editar</button></div><b>${title}</b><small>${sub}</small>`); d.querySelector('.f3edit').onclick = e => { e.stopPropagation(); openFX(kind); }; d.querySelector('.f3img img').onclick = () => lightbox(src, title); col.appendChild(d); };
      small(P().ficha, 'Cara de cerca', 'cuatro ángulos: frente, perfil, tres cuartos y espalda', '360'); if (P().cuerpo) small(P().cuerpo, 'Cuerpo completo', 'tres ángulos: frente, perfil y espalda', 'cuerpo'); top.appendChild(col); }
    w.appendChild(top);
    const sec2 = el('div', 'f3sec'); const hd = el('div', 'f3head');
    hd.appendChild(el('h4', '', 'Fichas creadas<small>para usarlas en fotos y en vídeos</small>')); const nb = el('div', 'f3newbtns'); const b1 = el('button', 'btn acc', '＋ Nueva ficha'); b1.title = 'Su ficha principal con otra ropa y otros objetos'; b1.onclick = abrirNueva; nb.appendChild(b1); hd.appendChild(nb); hd.classList.add('stacked'); sec2.appendChild(hd);
    const g = el('div', 'f3grid'); const V = [];   // V: lo que enseña el visor (con las flechas se pasa de una a otra)
    const card = (src, title, tag, sub, acts, cls) => { const d = el('div', 'f3card ' + (cls || ''), `<div class="f3img sm"><img src="${src}" alt=""></div>${tag ? `<span class="f3tag">${tag}</span>` : ''}<b>${title}</b><small>${sub || ''}</small>`); { const k = V.length; V.push({ src: src.replace('_t.jpg', '.jpg'), nombre: title, info: [tag, sub].filter(Boolean).join(' · '), acts }); d.querySelector('.f3img').onclick = () => visorFichas(V, k); } const a = el('div', 'f3acts'); acts.forEach(([t, fn, tip]) => { const b = el('button', 'btn', t); if (tip) b.title = tip; b.onclick = e => { e.stopPropagation(); fn(); }; a.appendChild(b); }); d.appendChild(a); g.appendChild(d); };
    const same = (a, b) => (a || '').split('?')[0] === (b || '').split('?')[0];
    F3.jobs.forEach(j => { const d = el('div', 'f3card wide gen', `<div class="f3img sm"><img src="${P().comboThumb || principal()}" alt=""><span class="f3busy"><i class="spin"></i>Generando · <i data-t0="${j.t0}">${Math.round((performance.now() - j.t0) / 1000)} s</i></span></div><b>${esc(j.it.name)}</b><small>se guardará aquí sola al terminar</small>`); g.appendChild(d); });
    if (F3.jobs.length) { clearInterval(F3.gtick); F3.gtick = setInterval(() => { const ns = document.querySelectorAll('.f3card.gen [data-t0]'); if (!ns.length) { clearInterval(F3.gtick); return; } ns.forEach(n => { n.textContent = Math.round((performance.now() - +n.dataset.t0) / 1000) + ' s'; }); }, 1000); }
    const info = f => [f.t, f.modelo, f.size ? (f.size[0] >= 2400 ? '2K' : f.size[0] < 1500 ? '1K · baja resolución' : '') : ''].filter(Boolean).join(' · ');
    (P().fichas || []).filter(f => !same(f.img, P().combo)).forEach(f => card(f.thumb || f.img, f.nombre, '', info(f), [['★ Principal', async () => { if (!confirm(`¿Hacer «${f.nombre}» su ficha principal? Sus 4 vistas pasan a ser su ficha 360 en toda la app. La principal de ahora se queda aquí, en Fichas creadas.`)) return; if (await comboApi({ action: 'principal', id: f.id })) { toast('Ficha principal cambiada'); renderProfile(); renderSide(); } }, 'Hacerla principal'], ['✨', () => fichaAImagen(f.img, f.nombre), 'Usar en Crear imagen'], ['🎬', () => window.FBapi && FBapi.usarEnVideo(f), 'Usar en Crear vídeo'], ['⬇', () => dl(f.img), 'Descargar'], ['🗑', () => window.FBapi && FBapi.borrar(f), 'Borrar']], 'wide'));
    extra().filter(f => !same(f.img, P().ficha)).forEach(f => card(f.img, f.nombre, '4 vistas', f.t, [['★ Principal', async () => { if (confirm(`¿Usar «${f.nombre}» como sus 4 vistas principales en toda la app? Las de ahora se quedan aquí.`)) { if (await api({ action: 'principal', id: f.id })) { await comboApi({ action: 'ensure' }); toast('Vistas principales cambiadas'); renderProfile(); renderSide(); } } }, 'Hacerla principal'], ['⬇', () => dl(f.img), 'Descargar'], ['🗑', async () => { if (confirm(`¿Borrar «${f.nombre}»?`)) { if (await api({ action: 'delete', id: f.id })) renderProfile(); } }, 'Borrar']]));
    (P().cuerpos || []).filter(c => !same(c.img, P().cuerpo)).forEach(c => card(c.img, c.nombre, 'Cuerpo', c.t, [['★ Principal', async () => { if (confirm(`¿Usar «${c.nombre}» como su ficha de cuerpo principal?`)) { const r = await panelApi({ action: 'principal_cuerpo', id: c.id }); if (r) { await comboApi({ action: 'ensure' }); toast('Ficha de cuerpo principal cambiada'); renderProfile(); } } }, 'Hacerla principal'], ['⬇', () => dl(c.img), 'Descargar']]));
    if (!g.children.length) g.appendChild(el('div', 'accempty', 'Todavía no has creado ninguna. Empieza con «＋ Nueva ficha».'));
    sec2.appendChild(g); w.appendChild(sec2); return w;
  };

  // ------------------------------------------------ editor de la ficha principal (combinada) y de la ficha de cuerpo
  const FX = window.FX = { kind: null, src: null, sel: null, jobs: [], pick: null, nuevo: null, bodyNew: null, notas: '', adj: {} };
  // prompts de Max (curso «Ficha 360 para tu Influencer IA»): el frente y los tres cuartos SIEMPRE con sonrisa enseñando los dientes
  const SMILE = 'Expresión: sonrisa amplia de felicidad enseñando dientes (big joyful toothy smile), boca ligeramente abierta, dientes superiores e inferiores visibles, dientes anatómicamente correctos, proporción natural, sin deformaciones.';
  const TAIL = 'Fotografía realista de estudio, iluminación suave y neutra, fondo gris neutro liso, encuadre de cabeza y torso en vertical 2:3, alta nitidez, sin CGI, sin 3D. Sin texto, sin watermark, sin logos.';
  const who = () => `Chica de @img1 y @img2 (${P().name}), mantener identidad exacta y rasgos faciales idénticos a @img2 (su cara en grande); mismo peinado, ${(P().complementos || []).filter(c => c.regla === 'siempre').map(c => c.nombre.toLowerCase()).join(', ') || 'mismos accesorios'} y la misma ropa.`;
  const V360 = [['frente', 'Frente', () => `${who()} Toma frontal perfecta (0°), mirando a cámara, postura neutra. ${SMILE}`], ['perfil', 'Perfil', () => `${who()} Vista lateral estricta 90° (perfil), mirando completamente hacia la izquierda, nariz y barbilla en perfil, hombros en perfil, postura neutra, expresión tranquila.`], ['tres', 'Tres cuartos', () => `${who()} Ángulo 45° (three-quarter view), cuerpo girado 45° respecto a cámara, rostro mostrando ambos ojos, mirada hacia cámara, postura neutra. ${SMILE}`], ['espalda', 'Espalda', () => `${who()} Vista trasera 180° (de espaldas a cámara), peinado muy visible desde atrás, patillas de las gafas visibles, cabeza centrada, hombros y espalda alineados, postura neutra.`]];
  const VIEWS = { combo: V360.concat([['cuerpo', 'Cuerpo de frente', () => ''], ['lado', 'Cuerpo de perfil', () => '']]), '360': V360, cuerpo: [['frente', 'Frente', () => 'front view, standing straight facing the camera'], ['perfil', 'Perfil', () => 'strict left side profile (90°)'], ['espalda', 'Espalda', () => 'back view (180°)']] };
  const AREA = { combo: { frente: '1 / 1', perfil: '1 / 2', tres: '2 / 1', espalda: '2 / 2', cuerpo: '1 / 4 / 3 / 5', lado: '1 / 6 / 3 / 7' }, '360': { frente: '1 / 1', perfil: '1 / 2', tres: '2 / 1', espalda: '2 / 2' }, cuerpo: { frente: '1 / 1', perfil: '1 / 2', espalda: '1 / 3' } };
  const ADJ = [['pecho+', 'Más pecho', 'a slightly fuller bust'], ['pecho-', 'Menos pecho', 'a slightly smaller bust'], ['cadera+', 'Más cadera y glúteos', 'slightly wider hips and rounder glutes'], ['cadera-', 'Menos cadera', 'slightly narrower hips'], ['delgada', 'Más delgada', 'a slightly slimmer figure'], ['tonificada', 'Más tonificada', 'a more toned, athletic figure'], ['piernas', 'Piernas más largas', 'slightly longer legs']];
  const isBody = k => FX.kind === 'cuerpo' || k === 'cuerpo' || k === 'lado';
  const isView = k => (FX.kind === 'combo' || FX.kind === '360') && V360.some(v => v[0] === k);
  const altOf = (kind, k) => kind === 'combo' ? (k === 'cuerpo' || k === 'lado' ? ['combo', k] : ['360', k]) : [kind, k];
  const hist = k => { const [a, b] = altOf(FX.kind, k); return ((P().alt || {})[a] || {})[b] || []; };
  const base2x2 = () => (FX.nuevo && FX.nuevo.img) || P().ficha;
  function openFX(kind) { if (kind === 'combo' && !P().combo) { toast('Preparando la ficha principal…'); ensureCombo(); return; } Object.assign(FX, { kind, src: kind === 'combo' ? P().combo : kind === '360' ? P().ficha : P().cuerpo, sel: null, pick: null, nuevo: null, bodyNew: null, sideNew: null, notas: '', adj: {} }); clearInterval(FX.tick); FX.tick = setInterval(() => { if (!$('#fxm')) { clearInterval(FX.tick); return; } document.querySelectorAll('#fxm [data-t0]').forEach(n => { n.textContent = Math.round((performance.now() - +n.dataset.t0) / 1000) + ' s'; }); }, 1000); paintFX(); }
  function closeFX() { const m = $('#fxm'); if (m) m.remove(); clearInterval(FX.tick); FX.kind = null; renderProfile(); }
  const running = (kind, k) => FX.jobs.filter(j => !j.end && j.fxKind === kind && (k == null || j.fx === k));
  const FRONT = [0, 0, 0.5, 0.5]; // el frente es la vista de arriba a la izquierda de la rejilla 2x2
  const seedreamKey = () => (MODELS.find(x => x.key === 'seedream') || curModel()).key;
  function fxPrompt(k) {
    const notes = FX.notas.trim() ? ` Además: ${FX.notas.trim()}.` : '';
    const adj = ADJ.filter(a => FX.adj[a[0]]).map(a => a[2]); const bodyAdj = adj.length ? ` Adjust her body: ${adj.join(', ')}; everything else identical.` : '';
    if (isView(k)) { const v = V360.find(x => x[0] === k); return `@img1 es su ficha 360 completa (rejilla 2x2: arriba a la izquierda el frente, arriba a la derecha el perfil, abajo a la izquierda tres cuartos, abajo a la derecha la espalda): de ahí salen su peinado, su ropa, la luz y el encuadre. @img2 es el frente de esa misma ficha recortado en grande: úsalo para clavar su cara. Genera SOLO la vista «${v[1]}», como UNA sola imagen, con el mismo encuadre que las vistas de @img1: ${v[2]()}${notes} ${TAIL}`; }
    if (FX.kind === 'combo') return `@Image1 is her main character sheet: on the left a 2x2 grid of her head and upper body, then a full-body FRONT view and a full-body left SIDE PROFILE view, both from the neck down. @Image2 is her body reference sheet (only for her real body proportions). Generate ONLY the full-body ${k === 'lado' ? 'SIDE PROFILE' : 'FRONT'} panel again, as ONE single vertical image: ${k === 'lado' ? 'strict left side profile (90°), standing straight, arms relaxed along the body' : 'standing straight facing the camera, relaxed arms'}, framed FROM THE NECK DOWN (the top edge cuts just below the chin, no face), from the neck to the feet with a little space below them, wearing exactly the same clothes and shoes as in the body panels of @Image1 (if she is in plain white underwear there, the same plain white underwear), same body, same light-gray studio background and soft light.${bodyAdj}${notes ? ' Also: ' + FX.notas.trim() + '.' : ''} Photoreal, no text, no grid.`;
    if (k === 'entera') return `Create a new BODY reference sheet of the exact woman of @Image1 with exactly the body of @Image2: one single wide image with THREE views side by side, framed FROM THE NECK DOWN (the top edge cuts just below the chin, no face): left front view, middle left side profile, right back view, each from the neck to the feet. Plain minimalist white bra and white briefs, matte cotton, no lace, no logos, tasteful model-agency body polaroid style. Standing straight and relaxed, barefoot.${bodyAdj}${notes ? ' Also: ' + FX.notas.trim() + '.' : ''} Plain neutral light-gray studio background, soft even light, photoreal, no text.`;
    return `@Image1 is her body reference sheet (three full-body views from the neck down in plain white underwear: left front, middle left side profile, right back). Generate ONLY this view again, as ONE single vertical image: ${VIEWS.cuerpo.find(v => v[0] === k)[2]()}. Exactly the same body, same plain white underwear, framed FROM THE NECK DOWN (no face), from the neck to the feet, same light-gray background and soft light; @Image2 only confirms her skin and hair color.${bodyAdj}${notes ? ' Also: ' + FX.notas.trim() + '.' : ''} Photoreal, no text, no grid.`;
  }
  function fxImages(k) {
    const b = base2x2().split('?')[0];
    if (isView(k)) return [{ path: b }, { path: b, crop: FRONT }];
    if (FX.kind === 'combo') return [{ path: P().combo.split('?')[0] }, { path: P().cuerpo.split('?')[0] }];
    if (k === 'entera') return [{ path: P().ficha.split('?')[0] }, { path: FX.src.split('?')[0] }];
    return [{ path: FX.src.split('?')[0] }, { path: P().ficha.split('?')[0] }];
  }
  function fxRefs(k) { // miniaturas de lo que se envía
    const b = base2x2();
    if (isView(k)) return [[b, '@img1 · sus 4 vistas', ''], [b, '@img2 · su cara en grande', 'crop']];
    if (FX.kind === 'combo') return [[P().combo, '@Image1 · su ficha principal', ''], [P().cuerpo, '@Image2 · su cuerpo real', '']];
    if (k === 'entera') return [[P().ficha, '@Image1 · su ficha 360', ''], [FX.src, '@Image2 · esta ficha de cuerpo', '']];
    return [[FX.src, '@Image1 · esta ficha de cuerpo', ''], [P().ficha, '@Image2 · su ficha 360', '']];
  }
  async function genFX(k) {
    if (!LIVE) { toast('Conecta primero tu API (arriba, «Conecta tu API»)'); return; } const body_ = isBody(k); const key = body_ ? seedreamKey() : curModel().key; const m = MODELS.find(x => x.key === key) || curModel(); const usd = m.usd[state.quality];
    const prompt = fxPrompt(k); const images = fxImages(k);
    FX.sending = true; paintFX();
    const body = { item: 'editor_' + FX.kind + '_' + k, prompt, images, aspect: k === 'entera' ? '3:2' : '2:3', quality: state.quality, model: key, meta: { name: `Editor de ficha · ${FX.kind === 'combo' ? 'Principal' : FX.kind === '360' ? 'Cara' : 'Cuerpo'} · ${k}`, tab: 'perfil', personaje: '_ficha_editor', hidden: true, model: m.name, ep: m.ep, prompt } };
    let r; try { r = await fetch('/api/generar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
    FX.sending = false; if (!r || r.error) { toast('No se pudo generar: ' + (r ? r.error : 'sin respuesta')); if (FX.kind) paintFX(); return; }
    const job = { rid: r.request_id, it: { id: 'fx:' + k, name: body.meta.name }, tab: 'perfil', m, kind: 'image', fx: k, fxKind: FX.kind, t0: performance.now(), status: 'queued', usd: r.usd != null ? Number(r.usd) : usd };
    JOBS.set(job.rid, job); FX.jobs.push(job); ensurePoller(); if (FX.kind) paintFX();
  }
  const _fin2 = window.finishJob, _fail2 = window.failJob;
  window.finishJob = async function (job, st) {
    if (job.nf) return nfFinish(job, st);
    if (!job.fx) return _fin2(job, st); job.end = true; const usd = st.usd != null ? Number(st.usd) : (job.usd || 0); state.nGen++; state.spent += usd; meter();
    FX.jobs = FX.jobs.filter(j => j !== job); const [a, b] = altOf(job.fxKind, job.fx); await panelApi({ action: 'alt_add', kind: a, view: b, file: st.file });
    if (FX.kind === job.fxKind && (!FX.sel || FX.sel === job.fx)) { FX.sel = job.fx; FX.pick = st.file; }
    toast(`Versión nueva lista: la ves en su sitio de la ficha y en su historial · ${fmtUsd(usd)}`); if (FX.kind) paintFX(); else if (state.tab === 'perfil') renderProfile(); };
  window.failJob = function (job, msg) {
    if (job.nf) { job.end = true; F3.jobs = F3.jobs.filter(j => j !== job); toast('No se pudo generar la ficha: ' + msg); if (state.tab === 'perfil') renderProfile(); return; }
    if (!job.fx) return _fail2(job, msg); job.end = true; FX.jobs = FX.jobs.filter(j => j !== job); toast('No se pudo generar: ' + msg); if (FX.kind) paintFX(); else if (state.tab === 'perfil') renderProfile(); };
  async function ponerEnFicha() {
    const k = FX.sel, f = FX.pick; if (!k || !f) return; let r;
    if (FX.kind === 'combo' && (k === 'cuerpo' || k === 'lado')) { if (k === 'lado') FX.sideNew = f; else FX.bodyNew = f; r = await comboApi({ action: 'preview', ficha: base2x2(), body: FX.bodyNew || '', side: FX.sideNew || '' }); if (!r) return; FX.src = r.preview; }
    else if (isView(k)) { const idx = V360.findIndex(x => x[0] === k); r = await panelApi({ action: 'compose', base: base2x2(), panel: f, index: idx, layout: '2x2', target: 'ficha360', nombre: `4 vistas · ${V360[idx][1]} cambiada` }); if (!r) return; FX.nuevo = r.item;
      if (FX.kind === 'combo') { const pv = await comboApi({ action: 'preview', ficha: r.item.img, body: FX.bodyNew || '', side: FX.sideNew || '' }); if (pv) FX.src = pv.preview; } else FX.src = r.item.img; }
    else if (k === 'entera') { r = await panelApi({ action: 'add_cuerpo', panel: f, nombre: 'Ficha de cuerpo nueva' }); if (!r) return; FX.nuevo = r.item; FX.src = r.item.img; }
    else { const L = VIEWS.cuerpo; const idx = L.findIndex(x => x[0] === k); r = await panelApi({ action: 'compose', base: FX.src, panel: f, index: idx, layout: '3x1', target: 'cuerpo', nombre: `Ficha de cuerpo · ${L[idx][1]} cambiada` }); if (!r) return; FX.nuevo = r.item; FX.src = r.item.img; }
    FX.pick = null; toast('Puesta en la ficha. La principal no cambia hasta que pulses «★ Hacer principal».'); paintFX();
  }
  async function hacerPrincipal() {
    if (FX.kind === 'combo' || FX.kind === '360') {
      if (FX.nuevo && !(await api({ action: 'principal', id: FX.nuevo.id }))) return;
      if (FX.bodyNew && !(await comboApi({ action: 'set_body', which: 'front', file: FX.bodyNew }))) return;
      if (FX.sideNew && !(await comboApi({ action: 'set_body', which: 'side', file: FX.sideNew }))) return;
      await comboApi({ action: 'ensure' }); FX.nuevo = null; FX.bodyNew = null; FX.sideNew = null; FX.src = FX.kind === 'combo' ? P().combo : P().ficha; toast(FX.kind === 'combo' ? 'Ficha principal cambiada (lo anterior sigue guardado)' : 'Cara de cerca cambiada: la ficha principal ya la lleva'); paintFX(); renderSide(); return;
    }
    const it = FX.nuevo; if (!it) return; const ok = await panelApi({ action: 'principal_cuerpo', id: it.id });
    if (ok) { await comboApi({ action: 'ensure' }); toast('Ficha de cuerpo principal cambiada (la anterior sigue en Fichas creadas)'); FX.nuevo = null; FX.src = P().cuerpo; paintFX(); }
  }
  function paintFX() {
    let m0 = $('#fxm'); if (!m0) { m0 = el('div', 'fxm'); m0.id = 'fxm'; document.body.appendChild(m0); m0.onclick = e => { if (e.target === m0) closeFX(); }; }
    const combo = FX.kind === 'combo'; const L = VIEWS[FX.kind]; const A = AREA[FX.kind]; m0.innerHTML = '';
    const box = el('div', 'fxbox'); const media = el('div', 'fxmedia');
    const wrap = el('div', 'fxsheet ' + (combo ? 'gc' : FX.kind === '360' ? 'g2' : 'g3')); wrap.innerHTML = `<img src="${FX.src}" alt="">`;
    L.forEach(([k, n]) => { const area = A[k];
      if (FX.pick && FX.sel === k) { const pv = el('div', 'fxprev', `<img src="${FX.pick}" alt=""><span>Vista previa · sin guardar</span>`); pv.style.gridArea = area; wrap.appendChild(pv); }
      const hot = el('button', 'fxhot' + (FX.sel === k ? ' on' : ''), `<span>${n}</span>`); hot.title = 'Seleccionar'; hot.style.gridArea = area; hot.onclick = () => { FX.sel = k; FX.pick = null; paintFX(); }; wrap.appendChild(hot);
      const R = running(FX.kind, k); if (R.length) { const g = el('div', 'fxgen', `<div class="bar"><i></i></div><b>Generando</b><span>${n}${R.length > 1 ? ` · ${R.length} versiones` : ''}</span><small data-t0="${R[R.length - 1].t0}">${Math.round((performance.now() - R[R.length - 1].t0) / 1000)} s</small>`); g.style.gridArea = area; wrap.appendChild(g); } });
    { const R = FX.sel === 'entera' ? running(FX.kind, 'entera') : []; if (R.length) { const g = el('div', 'fxgen', `<div class="bar"><i></i></div><b>Generando</b><span>Ficha de cuerpo entera</span><small data-t0="${R[0].t0}">0 s</small>`); g.style.gridArea = '1 / 1 / -1 / -1'; wrap.appendChild(g); } }
    media.appendChild(wrap); box.appendChild(media);
    const side = el('div', 'fxside'); const x = el('button', 'galx', '×'); x.onclick = closeFX; box.appendChild(x);
    side.appendChild(el('div', 'fxtitle', `<small>${FX.nuevo || FX.bodyNew || FX.sideNew ? 'Cambios sin hacer principal' : 'Ficha principal'}</small><b>${combo ? 'Ficha principal' : FX.kind === '360' ? 'Cara de cerca' : 'Cuerpo completo'}</b><p>${combo ? 'Pulsa una vista o uno de los cuerpos para cambiarlo. Nada se pierde: cada versión generada queda en su historial.' : FX.kind === '360' ? 'Sus cuatro ángulos de cerca. Pulsa uno para cambiarlo; la ficha principal se actualiza sola al hacerlo principal.' : 'Pulsa una vista para cambiarla. Puedes ajustar el cuerpo antes de generar.'}</p>`));
    if (FX.nuevo || FX.bodyNew || FX.sideNew) { const sc = el('div', 'fxsec fxok'); sc.appendChild(el('h4', '', 'Así queda la ficha<small>la principal no cambia hasta que la hagas principal</small>')); const a = el('div', 'fxacts'); const pz = el('button', 'btn acc', '★ Hacer principal'); pz.onclick = hacerPrincipal; a.appendChild(pz); sc.appendChild(a); side.appendChild(sc); }
    // 1 · elegir qué cambiar
    const s1 = el('div', 'fxsec'); s1.appendChild(el('h4', '', '1 · Qué quieres cambiar')); const vb = el('div', 'fxviews'); L.forEach(([k, n]) => { const b = el('button', 'btn' + (FX.sel === k ? ' acc' : ''), n); b.onclick = () => { FX.sel = k; FX.pick = null; paintFX(); }; vb.appendChild(b); }); if (FX.kind === 'cuerpo') { const b = el('button', 'btn' + (FX.sel === 'entera' ? ' acc' : ''), 'Ficha entera'); b.onclick = () => { FX.sel = 'entera'; FX.pick = null; paintFX(); }; vb.appendChild(b); } s1.appendChild(vb); side.appendChild(s1);
    if (FX.sel) {
      const k = FX.sel; const nm = k === 'entera' ? 'Ficha entera' : L.find(v => v[0] === k)[1];
      const m = MODELS.find(z => z.key === (isBody(k) ? seedreamKey() : curModel().key)) || curModel(); const cost = fmtUsd(m.usd[state.quality]);
      // 2 · historial
      const H = hist(k); const RJ = running(FX.kind, k); const s2 = el('div', 'fxsec'); s2.appendChild(el('h4', '', `2 · Versiones de «${nm}»<small>${H.length || RJ.length ? 'elige la que más te guste: se ve en su sitio de la ficha antes de guardarla' : 'todavía no has generado ninguna'}</small>`));
      if (H.length || RJ.length) { const g = el('div', 'fxhist'); RJ.slice().reverse().forEach(j => g.appendChild(el('div', 'fxh gen', `<i class="spin"></i><small data-t0="${j.t0}">${Math.round((performance.now() - j.t0) / 1000)} s</small>`))); H.forEach(f => { const t = el('button', 'fxh' + (FX.pick === f ? ' on' : ''), `<img src="${f}" alt="">`); t.onclick = () => { FX.pick = FX.pick === f ? null : f; paintFX(); }; t.ondblclick = () => lightbox(f, nm); g.appendChild(t); }); s2.appendChild(g); }
      if (FX.pick) { const a = el('div', 'fxacts'); const y = el('button', 'btn acc', k === 'entera' ? '✓ Guardar como ficha de cuerpo' : '✓ Poner en la ficha'); y.onclick = ponerEnFicha; const v = el('button', 'btn', '🔍 Ver grande'); v.onclick = () => lightbox(FX.pick, nm); a.appendChild(y); a.appendChild(v); s2.appendChild(a); }
      side.appendChild(s2);
      // 3 · generar otra
      const s3 = el('div', 'fxsec'); s3.appendChild(el('h4', '', `3 · Generar otra versión<small>${m.name} · ${cost} cada una · puedes lanzar varias y elegir la mejor</small>`));
      { const rr = el('div', 'fxrefs'); fxRefs(k).forEach(([s0, n, crop]) => rr.appendChild(el('span', 'fxref', `<i class="${crop ? 'crop' : ''}" style="background-image:url('${s0}')"></i><b>${n}</b>`))); s3.appendChild(rr); }
      if (isBody(k)) { const aj = el('div', 'accreg'); ADJ.forEach(([id, n]) => { const b = el('button', FX.adj[id] ? 'on' : '', n); b.onclick = () => { FX.adj[id] = !FX.adj[id]; paintFX(); }; aj.appendChild(b); }); s3.appendChild(aj); }
      const nt = el('textarea', 'pjin'); nt.placeholder = isBody(k) ? 'Algo más que ajustar (opcional)' : 'Algo que cambiar (opcional) · ej.: un poco más de flequillo'; nt.value = FX.notas; nt.oninput = () => { FX.notas = nt.value; pv.textContent = fxPrompt(k); }; s3.appendChild(nt);
      const det = el('details', 'fxprompt'); det.appendChild(el('summary', '', 'Ver el prompt que se enviará')); const pv = el('div', 'promptbox', fxPrompt(k)); det.appendChild(pv); s3.appendChild(det);
      const gb = el('button', 'btn acc pr', FX.sending ? '⏳ Enviando…' : `${RJ.length ? 'Generar una más' : `Generar otra «${nm}»`}<i>${cost}</i>`); gb.disabled = !!FX.sending; gb.onclick = () => genFX(k); s3.appendChild(gb);
      if (RJ.length) s3.appendChild(el('small', 'pjnote', `⏳ ${RJ.length === 1 ? 'Una versión se está generando' : RJ.length + ' versiones se están generando'}: la verás difuminada en su sitio de la ficha y aparecerá en el historial.`));
      side.appendChild(s3);
    }
    const s4 = el('div', 'fxsec'); s4.appendChild(el('h4', '', 'Más')); const st = el('div', 'stack');
    if (combo) { const a1 = el('button', 'btn w', '＋ Nueva ficha con otra ropa'); a1.onclick = () => { $('#fxm').remove(); FX.kind = null; abrirNueva(); }; st.appendChild(a1); }
    const dlb = el('button', 'btn w', '⬇ Descargar esta ficha'); dlb.onclick = () => dl(FX.src); st.appendChild(dlb); s4.appendChild(st); side.appendChild(s4);
    box.appendChild(side); m0.appendChild(box);
  }

  // ------------------------------------------------ «＋ Nueva ficha»: paso a paso y una sola generación
  const accAll = () => P().complementos || [];
  const MKEY = 'am_model_ficha_v2'; const NFQ = 'high'; // GPT Image 2.5 por defecto (edita la ropa sin deformar la cara) y SIEMPRE a 2K: son seis paneles en una imagen y a 1K sale pixelada
  const nfModel = () => { let k = F3.model; if (!k) { try { k = localStorage.getItem(MKEY); } catch (e) {} } return MODELS.find(x => x.key === k) || MODELS.find(x => x.key === 'gptimg') || MODELS.find(x => x.key === 'seedream') || curModel(); };
  const nfNombre = () => (P().name || 'Aria').split(' ')[0] + ' · ' + (F3.prendas.map(prenda).filter(Boolean).map(p => p.name).join(' + ') || 'ficha nueva');
  const nfSaved = f => (P().fichas || []).find(x => x.from === f);
  const nfModelFor = n => { const m = nfModel(); return n > m.refs ? (window.fitModel && fitModel(n)) || m : m; };
  const accSel = () => accAll().filter(c => F3.acc.includes(c.id));
  const nfHist = () => (((P().alt || {}).nueva || {}).combo) || [];
  function nfRefs() { // @Image1 = su ficha principal · prendas · complementos con foto · objetos sueltos
    const R = [{ key: 'base', path: principal(), name: 'Su ficha principal' }];
    F3.prendas.map(prenda).filter(Boolean).forEach(p => R.push({ key: 'p:' + p.id, path: p.ficha, thumb: p.card, name: p.name, p }));
    accSel().forEach(c => { if (c.img && c.modo !== 'prompt') R.push({ key: 'a:' + c.id, path: c.img, thumb: c.thumb || c.img, name: c.nombre, c }); });
    F3.extras.forEach((x, i) => R.push({ key: 'x:' + i, data: x.data, thumb: x.data, name: x.label || 'Objeto ' + (i + 1), x }));
    return R.map((r, i) => Object.assign(r, { tag: '@Image' + (i + 1) }));
  }
  function nfPrompt() {
    const R = nfRefs(); const ps = R.filter(r => r.p); const as = R.filter(r => r.c); const xs = R.filter(r => r.x); const described = accSel().filter(c => !(c.img && c.modo !== 'prompt'));
    const outfit = ps.length ? `she now wears EXACTLY the outfit of ${ps.map(r => `${r.tag} (${r.p.name})`).join(' combined with ')} — every garment, color, fabric, pattern and detail — as far as each panel shows it; the two full-body panels show the complete outfit from the neck down (front and side), including its shoes` : 'she keeps her clothes';
    const objs = as.map(r => `${r.c.desc || r.c.nombre} exactly as in ${r.tag}`).concat(described.map(c => c.desc || c.nombre)).concat(xs.map(r => `${r.x.label ? r.x.label + ', ' : 'the object of '}exactly as in ${r.tag}`));
    const obj = objs.length ? ` She also has ${objs.join('; ')}: worn or held naturally, visible in the full-body panels and in the views where it would be seen.` : '';
    const pj = pjOf();
    if (pj) { const R0 = nfRefs(); const man = R0.filter(r => r.p).map(r => r.tag).join(' and ');
      const t = `Edit @Image1, her character reference sheet (several views of the same person${pj.combo ? ': four views of her head and upper body, then her full body from the front and from the side' : ''}). Keep EXACTLY the same layout, the same panels, framing and crops, poses, expressions, face, hair, accessories, body shape and proportions, the background and the light. ONLY change what she wears: in every panel ${outfit}.${obj}${man ? ` The person wearing the outfit in ${man} is only a mannequin for the clothes: never copy her face, hair, glasses or earrings.` : ''} Photoreal, sharp, natural skin texture, no text, no labels, no extra panels.`;
      return typeof genderize === 'function' ? genderize(t, pj.genero) : t; }
    return `Edit @Image1, her character reference sheet: on the left a 2x2 grid of her head and upper body (top-left front view with a big joyful toothy smile, top-right left side profile, bottom-left three-quarter view smiling, bottom-right back view), then a full-body FRONT view and a full-body left SIDE PROFILE view, both from the neck down. Keep EXACTLY the same layout, the same six panels, framing and crops, poses, expressions, face, hair, glasses, earrings, body shape and proportions, the gray studio background and the soft light. ONLY change what she wears: in all six panels ${outfit}.${obj} Whatever she wears in @Image1 (a tank top, plain underwear) is only the base: none of it stays visible unless the new outfit shows it. Photoreal, sharp, natural skin texture, no text, no labels, no extra panels.`;
  }
  async function nfGenerate() {
    if (!LIVE) { toast('Conecta primero tu API (arriba, «Conecta tu API»)'); return; } if (!F3.prendas.length && !F3.acc.length && !F3.extras.length) { toast('Elige primero la ropa o algún objeto'); return; }
    const R = nfRefs(); const images = R.map(r => r.data ? { data: r.data } : { path: r.path.split('?')[0] });
    const m = nfModelFor(images.length);
    const usd = m.usd[NFQ]; if (!confirm(`¿Generar la ficha nueva con ${m.name} a 2K? (${fmtUsd(usd)})`)) return;
    const prompt = nfPrompt(); F3.sending = true; renderProfile();
    const pj0 = pjOf(); const body = { item: 'ficha_nueva', prompt, images, aspect: pj0 && !pj0.combo ? '2:3' : '16:9', quality: NFQ, model: m.key, meta: { name: 'Ficha nueva · ' + (R.filter(r => r.p).map(r => r.p.name).join(' + ') || 'objetos'), tab: 'perfil', personaje: '_fichas', hidden: true, model: m.name, ep: m.ep, prompt, nf: { owner: F3.owner || undefined, nombre: nfNombre(), prendas: F3.prendas.slice(), acc: F3.acc.slice(), extras: F3.extras.map(x => x.label || 'objeto') } } };
    let r; try { r = await fetch('/api/generar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
    F3.sending = false; if (!r || r.error) { toast('No se pudo generar: ' + (r ? r.error : 'sin respuesta')); renderProfile(); return; }
    const job = { rid: r.request_id, it: { id: 'nf', name: body.meta.name }, tab: 'perfil', m, kind: 'image', nf: true, owner: F3.owner || null, t0: performance.now(), status: 'queued', usd: r.usd != null ? Number(r.usd) : usd, prendas: F3.prendas.slice(), acc: F3.acc.slice(), extras: F3.extras.map(x => x.label || 'objeto') };
    JOBS.set(job.rid, job); F3.jobs.push(job); ensurePoller(); renderProfile();
  }
  async function nfFinish(job, st) {
    job.end = true; F3.jobs = F3.jobs.filter(j => j !== job); const usd = st.usd != null ? Number(st.usd) : (job.usd || 0); state.nGen++; state.spent += usd; meter();
    if (job.owner) { if (window.pjReload) await pjReload(); } else await comboApi({ action: 'ensure' }); F3.pick = st.file; F3.meta = F3.meta || {}; F3.meta[st.file] = { prendas: job.prendas, acc: job.acc, extras: job.extras }; // el puente ya la ha guardado en Fichas creadas: aquí solo se refresca
    toast('Ficha nueva lista y guardada en «Fichas creadas» · ' + fmtUsd(usd)); if (state.tab === 'perfil') renderProfile();
  }
  async function nfGuardar() {
    const f = F3.pick; if (!f) return; const mt = (F3.meta || {})[f] || { prendas: F3.prendas, acc: F3.acc, extras: F3.extras.map(x => x.label || 'objeto') };
    const nm = (($('#nfName') || {}).value || '').trim() || 'Aria · ' + (mt.prendas.map(prenda).filter(Boolean).map(p => p.name).join(' + ') || 'ficha nueva');
    const r = await comboApi({ action: 'save', file: f, nombre: nm, prendas: mt.prendas, acc: mt.acc, extras: mt.extras }); if (!r) return;
    Object.assign(F3, { open: false, pick: null }); toast(`«${nm}» guardada en Fichas creadas`); window.pjScrollTop = true; renderProfile();
  }
  function elegirPrenda() {
    if (!window.startPick) { toast('Actualiza la página'); return; }
    startPick('vestidor', { label: 'tu ficha nueva', done: it => { F3.prendas = [it.id]; F3.open = true; if (window.PJ) { PJ.sel = OW(); PJ.tabBy = Object.assign(PJ.tabBy || {}, { [OW()]: 'ficha' }); } setTab('perfil'); toast(`«${it.name}» añadida a la ficha nueva`); setTimeout(() => { const s = document.querySelector('.nfstep.s3'); if (s) s.scrollIntoView({ block: 'start', behavior: 'smooth' }); }, 120); }, cancel: () => { F3.open = true; if (window.PJ) { PJ.sel = OW(); PJ.tabBy = Object.assign(PJ.tabBy || {}, { [OW()]: 'ficha' }); } setTab('perfil'); } });
  }
  function elegirComplementos() {
    const back = () => { F3.open = true; if (window.PJ) { PJ.sel = OW(); PJ.tabBy = Object.assign(PJ.tabBy || {}, { [OW()]: 'ficha' }); } renderProfile(); setTimeout(() => { const s = document.querySelector('.nfstep.s3'); if (s) s.scrollIntoView({ block: 'start', behavior: 'smooth' }); }, 120); };
    window.accPick = { label: 'tu ficha nueva', sel: F3.acc.slice(), done: ids => { F3.acc = ids; back(); toast(ids.length === 1 ? 'Complemento añadido a la ficha nueva' : `${ids.length} complementos añadidos a la ficha nueva`); }, cancel: back };
    if (window.PJ) { PJ.sel = OW(); PJ.tabBy = Object.assign(PJ.tabBy || {}, { [OW()]: 'complementos' }); } window.pjScrollTop = true; renderProfile();
  }
  const step = (n, t, sub, cls) => { const g = el('div', 'pjgrp nfstep ' + (cls || '')); g.appendChild(el('h4', '', `<i class="nfn">${n}</i>${t}${sub ? `<small>${sub}</small>` : ''}`)); return g; };
  window.f3Render = function (host) {
    if (!F3.open) return false; host.innerHTML = ''; const w = el('div', 'nfwrap');
    const bk0 = el('button', 'btn fxback', '← Volver a Fichas 360'); bk0.onclick = () => { F3.open = false; if (window.PJ) PJ.sel = OW(); window.pjScrollTop = true; renderProfile(); }; w.appendChild(bk0);
    w.appendChild(el('div', 'pjwhd', `<div><h3>Nueva ficha</h3><p>Su ficha principal con otra ropa y otros objetos: las cuatro vistas y el cuerpo entero salen en una sola imagen, de una vez.</p></div>`));
    // 1 · personaje
    const s1 = step(1, 'Personaje', 'la ficha se hace con ella'); const pc = el('div', 'nfchar', `<img class="av" src="${P().avatar || C.base.thumb}" alt=""><div><b>${P().name}</b><small>Se parte de su ficha principal</small></div><img class="base" src="${P().comboThumb || principal()}" alt="">`); pc.querySelector('.base').onclick = () => lightbox(principal(), 'Ficha principal'); s1.appendChild(pc); w.appendChild(s1);
    // 2 · ropa (del Vestidor)
    const s2 = step(2, 'Ropa', 'del Vestidor', 's2'); const ch = el('div', 'nfchips'); const pr = F3.prendas.map(prenda).filter(Boolean)[0];
    if (pr) { const c = el('div', 'nfchip', `<img src="${pr.card}" alt=""><b>${pr.name}</b>`); const x = el('button', 'pjx', '×'); x.title = 'Quitar'; x.onclick = () => { F3.prendas = []; renderProfile(); }; c.appendChild(x); c.querySelector('img').onclick = () => lightbox(pr.ficha, pr.name); const cb = el('button', 'lnk nfchg', 'Cambiar'); cb.onclick = elegirPrenda; c.appendChild(cb); ch.appendChild(c); }
    else { const pb = el('button', 'nfpick', `<span>👗</span><b>Elegir en el Vestidor</b><small>vas al Vestidor, eliges y vuelves aquí</small>`); pb.onclick = elegirPrenda; ch.appendChild(pb); }
    s2.appendChild(ch); w.appendChild(s2);
    // 3 · complementos: se eligen en su pestaña (como la ropa) o se suelta la foto de un objeto
    const s3 = step(3, 'Complementos', 'opcional · de su pestaña de complementos o la foto de un objeto', 's3');
    const fijos = accAll().filter(c => c.regla === 'siempre'); if (fijos.length) s3.appendChild(el('small', 'pjnote', `Ya lleva siempre: ${fijos.map(c => c.nombre).join(', ')}.`));
    const ac = el('div', 'nfaccs'); accSel().forEach(c => { const d = el('div', 'nfacc on', `${(c.thumb || c.img) ? `<img src="${c.thumb || c.img}" alt="">` : '<span>✨</span>'}<b>${c.nombre}</b>`); const x = el('button', 'pjx', '×'); x.title = 'Quitar'; x.onclick = () => { F3.acc = F3.acc.filter(z => z !== c.id); renderProfile(); }; d.appendChild(x); ac.appendChild(d); });
    F3.extras.forEach((x, i) => { const d = el('div', 'nfacc on extra', `<img src="${x.data}" alt="">`); const li = el('input', 'pjin'); li.placeholder = 'Qué es · ej.: black bucket hat'; li.value = x.label || ''; li.oninput = () => { x.label = li.value; }; d.appendChild(li); const q = el('button', 'pjx', '×'); q.onclick = () => { F3.extras.splice(i, 1); renderProfile(); }; d.appendChild(q); ac.appendChild(d); });
    { const pb = el('button', 'nfpick', `<span>🧩</span><b>${accSel().length ? 'Elegir más' : 'Elegir en Complementos'}</b><small>vas a sus complementos, marcas y vuelves aquí</small>`); pb.onclick = elegirComplementos; ac.appendChild(pb); }
    { const z = el('label', 'nfdrop', '<span>＋</span><b>Suelta aquí un objeto</b><small>o haz clic para subir su foto</small>'); const f = document.createElement('input'); f.type = 'file'; f.accept = 'image/*'; f.hidden = true; z.appendChild(f);
      const rd = file => { if (!file || !/^image\//.test(file.type)) return; const r = new FileReader(); r.onload = () => { F3.extras.push({ data: r.result, label: '' }); renderProfile(); }; r.readAsDataURL(file); };
      f.onchange = () => rd(f.files[0]); z.ondragover = e => { e.preventDefault(); z.classList.add('over'); }; z.ondragleave = () => z.classList.remove('over'); z.ondrop = e => { e.preventDefault(); z.classList.remove('over'); rd(e.dataTransfer.files[0]); }; ac.appendChild(z); }
    s3.appendChild(ac); w.appendChild(s3);
    // 4 · generar (una sola imagen) y elegir la mejor versión
    const nR = nfRefs().length; const m = nfModelFor(nR); const cost = fmtUsd(m.usd[NFQ]);
    const s4 = step(4, 'Generar la ficha', 'una sola imagen: 4 vistas + cuerpo de frente y de perfil', 's4');
    { const row = el('div', 'nfmodel'); row.appendChild(el('small', 'pjk', 'Modelo')); const ms = el('select', 'sel'); MODELS.forEach(x => { const o = document.createElement('option'); o.value = x.key; o.textContent = `${x.name} · ${fmtUsd(x.usd[NFQ])}${x.refs < nR ? ` · solo ${x.refs} referencias` : ''}`; ms.appendChild(o); }); ms.value = nfModel().key;
      ms.onchange = () => { F3.model = ms.value; try { localStorage.setItem(MKEY, ms.value); } catch (e) {} renderProfile(); }; row.appendChild(ms); if (m.key !== nfModel().key) row.appendChild(el('small', 'pjnote', `Van ${nR} referencias: esta ficha irá con ${m.name}`)); s4.appendChild(row); }
    const rr = el('div', 'fxrefs'); nfRefs().forEach(r => rr.appendChild(el('span', 'fxref', `<i style="background-image:url('${r.thumb || r.path}')"></i><b>${r.tag} · ${esc(r.name)}</b>`))); s4.appendChild(el('small', 'pjk', 'Se basa en')); s4.appendChild(rr);
    const det = el('details', 'fxprompt nfprompt'); det.appendChild(el('summary', '', 'Ver el prompt que se enviará')); det.appendChild(el('div', 'promptbox', esc(nfPrompt()))); s4.appendChild(det);
    const ok = F3.prendas.length || F3.acc.length || F3.extras.length; const gb = el('button', 'btn acc pr nfgen', F3.sending ? '⏳ Enviando…' : `${nfHist().length || F3.jobs.length ? 'Generar otra versión' : 'Generar la ficha'}<i>${cost}</i>`); gb.disabled = !!F3.sending || !ok; if (!ok) gb.title = 'Elige primero la ropa o algún objeto'; gb.onclick = nfGenerate; s4.appendChild(gb);
    const H = nfHist(); if (H.length || F3.jobs.length) {
      const vg = el('div', 'nfvers'); F3.jobs.slice().reverse().forEach(j => vg.appendChild(el('div', 'nfv gen', `<i class="spin"></i><b>Generando</b><small data-t0="${j.t0}">${Math.round((performance.now() - j.t0) / 1000)} s</small>`)));
      H.forEach(f => { const t = el('button', 'nfv' + (F3.pick === f ? ' on' : ''), `<img src="${f}" alt="">`); t.onclick = () => { F3.pick = F3.pick === f ? null : f; renderProfile(); }; t.ondblclick = () => lightbox(f, 'Ficha nueva'); vg.appendChild(t); });
      s4.appendChild(el('small', 'pjk', 'Versiones · elige la mejor')); s4.appendChild(vg);
    }
    if (F3.pick) { const big = el('div', 'nfbig', `<img src="${F3.pick}" alt="">`); big.onclick = () => lightbox(F3.pick, 'Ficha nueva'); s4.appendChild(big);
      const sv0 = nfSaved(F3.pick); const r5 = el('div', 'pjacts');
      if (sv0) { r5.appendChild(el('span', 'nfok', `✓ Guardada en «Fichas creadas» como <b>${esc(sv0.nombre)}</b>`)); const bk = el('button', 'btn acc', 'Ver en Fichas creadas'); bk.onclick = () => { F3.open = false; window.pjScrollTop = true; renderProfile(); }; r5.appendChild(bk); }
      else if (pjOf()) r5.appendChild(el('span', 'nfok', 'Esta versión se guarda sola al terminar.'));
      else { const nm = el('input', 'pjin'); nm.id = 'nfName'; nm.style.maxWidth = '360px'; nm.value = nfNombre(); r5.appendChild(nm); const sv = el('button', 'btn acc', '✓ Guardar en Fichas creadas'); sv.onclick = nfGuardar; r5.appendChild(sv); }
      s4.appendChild(r5);
      s4.appendChild(el('small', 'pjnote', 'Cada ficha que generas se guarda sola en «Fichas creadas». Allí puedes hacerla principal, usarla en vídeo, descargarla o borrarla.')); }
    w.appendChild(s4);
    host.appendChild(w);
    clearInterval(F3.tick); if (F3.jobs.length) F3.tick = setInterval(() => { if (!document.querySelector('.nfwrap')) { clearInterval(F3.tick); return; } document.querySelectorAll('.nfwrap [data-t0]').forEach(n => { n.textContent = Math.round((performance.now() - +n.dataset.t0) / 1000) + ' s'; }); }, 1000);
    return true;
  };
})();
