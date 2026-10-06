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
    const big = (src, title, sub, kind, cls) => { const nb = running(kind).length; const d = el('div', 'f3card big ' + (cls || ''), `<div class="f3img"><img src="${src}" alt="">${nb ? `<span class="f3busy"><i class="spin"></i>${nb === 1 ? 'Generando una versión' : `Generando ${nb} versiones`}</span>` : ''}<button class="f3edit">✎ Editar</button></div><b>${title}</b><small>${sub}</small>`); d.querySelector('.f3edit').onclick = e => { e.stopPropagation(); openFX(kind); }; d.querySelector('.f3img').onclick = e => { if (typeof WEBM === 'function' && WEBM()) return lightbox(src, title); const r = e.currentTarget.getBoundingClientRect(); openFX(kind === 'combo' ? ((e.clientX - r.left) < r.width * 0.42 ? '360' : 'cuerpo') : kind); }; d.classList.add('clic'); top.appendChild(d); };
    big(principal(), 'Ficha principal', 'sus cuatro vistas y su cuerpo entero de frente y de perfil, del cuello a los pies', 'combo', 'combo');
    { const col = el('div', 'f3sidecol'); const small = (src, title, sub, kind) => { const nb = running(kind).length; const d = el('div', 'f3card big mini', `<div class="f3img"><img src="${src}" alt="">${nb ? `<span class="f3busy"><i class="spin"></i>Generando</span>` : ''}<button class="f3edit">✎ Editar</button></div><b>${title}</b><small>${sub}</small>`); d.querySelector('.f3edit').onclick = e => { e.stopPropagation(); openFX(kind); }; d.querySelector('.f3img').onclick = () => (typeof WEBM === 'function' && WEBM()) ? lightbox(src, title) : openFX(kind); d.classList.add('clic'); col.appendChild(d); };
      small(P().ficha, 'Cara de cerca', 'cuatro ángulos: frente, perfil, tres cuartos y espalda', '360'); if (P().cuerpo) small(P().cuerpo, 'Cuerpo completo', 'tres ángulos: frente, perfil y espalda', 'cuerpo'); top.appendChild(col); }
    if (F3.solo !== 'creadas') w.appendChild(top);
    const sec2 = el('div', 'f3sec'); const hd = el('div', 'f3head');
    hd.appendChild(el('h4', '', 'Creador de fichas<small>fichas completas para usarlas en fotos y en vídeos</small>')); const nb = el('div', 'f3newbtns'); const b1 = el('button', 'btn acc', '＋ Nueva ficha'); b1.title = 'Su ficha principal con otra ropa y otros objetos'; b1.onclick = () => window.fichaTipo ? fichaTipo() : abrirNueva(); nb.appendChild(b1); hd.appendChild(nb); hd.classList.add('stacked'); sec2.appendChild(hd);
    const g = el('div', 'f3grid'); const V = [];   // V: lo que enseña el visor (con las flechas se pasa de una a otra)
    const card = (src, title, tag, sub, acts, cls) => { const d = el('div', 'f3card ' + (cls || ''), `<div class="f3img sm"><img src="${src}" alt=""></div>${tag ? `<span class="f3tag">${tag}</span>` : ''}<b>${title}</b><small>${sub || ''}</small>`); { const k = V.length; V.push({ src: src.replace('_t.jpg', '.jpg'), nombre: title, info: [tag, sub].filter(Boolean).join(' · '), acts }); d.querySelector('.f3img').onclick = () => visorFichas(V, k); } const a = el('div', 'f3acts'); acts.forEach(([t, fn, tip]) => { const b = el('button', 'btn', t); if (tip) b.title = tip; b.onclick = e => { e.stopPropagation(); fn(); }; a.appendChild(b); }); d.appendChild(a); g.appendChild(d); };
    const same = (a, b) => (a || '').split('?')[0] === (b || '').split('?')[0];
    F3.jobs.forEach(j => { const d = el('div', 'f3card wide gen', `<div class="f3img sm"><img src="${P().comboThumb || principal()}" alt=""><span class="f3busy"><i class="spin"></i>Generando · <i data-t0="${j.t0}">${Math.round((performance.now() - j.t0) / 1000)} s</i></span></div><b>${esc(j.it.name)}</b><small>se guardará aquí sola al terminar</small>`); g.appendChild(d); });
    if (F3.jobs.length) { clearInterval(F3.gtick); F3.gtick = setInterval(() => { const ns = document.querySelectorAll('.f3card.gen [data-t0]'); if (!ns.length) { clearInterval(F3.gtick); return; } ns.forEach(n => { n.textContent = Math.round((performance.now() - +n.dataset.t0) / 1000) + ' s'; }); }, 1000); }
    const info = f => [f.t, f.modelo, f.size ? (f.size[0] >= 2400 ? '2K' : f.size[0] < 1500 ? '1K · baja resolución' : '') : ''].filter(Boolean).join(' · ');
    (P().fichas || []).filter(f => !same(f.img, P().combo)).forEach(f => card(f.thumb || f.img, f.nombre, '', info(f), [['✨', () => fichaAImagen(f.img, f.nombre), 'Usar en Crear imagen'], ['🎬', () => window.FBapi && FBapi.usarEnVideo(f), 'Usar en Crear vídeo'], ['⬇', () => dl(f.img), 'Descargar'], ['🗑', () => window.FBapi && FBapi.borrar(f), 'Borrar']], 'wide'));
    extra().filter(f => !same(f.img, P().ficha)).forEach(f => card(f.img, f.nombre, '4 vistas', f.t, [['★ Principal', async () => { if ((await pregunta(`¿Usar «${f.nombre}» como sus 4 vistas principales en toda la app? Las de ahora se quedan aquí.`))) { if (await api({ action: 'principal', id: f.id })) { await comboApi({ action: 'ensure' }); toast('Vistas principales cambiadas'); renderProfile(); renderSide(); } } }, 'Hacerla principal'], ['⬇', () => dl(f.img), 'Descargar'], ['🗑', async () => { if ((await pregunta(`¿Borrar «${f.nombre}»?`))) { if (await api({ action: 'delete', id: f.id })) renderProfile(); } }, 'Borrar']]));
    (P().cuerpos || []).filter(c => !same(c.img, P().cuerpo)).forEach(c => card(c.img, c.nombre, 'Cuerpo', c.t, [['★ Principal', async () => { if ((await pregunta(`¿Usar «${c.nombre}» como su ficha de cuerpo principal?`))) { const r = await panelApi({ action: 'principal_cuerpo', id: c.id }); if (r) { await comboApi({ action: 'ensure' }); toast('Ficha de cuerpo principal cambiada'); renderProfile(); } } }, 'Hacerla principal'], ['⬇', () => dl(c.img), 'Descargar']]));
    if (!g.children.length) g.appendChild(el('div', 'accempty', 'Todavía no has creado ninguna. Empieza con «＋ Nueva ficha».'));
    sec2.appendChild(g); if ((F3.solo === 'creadas' || !window.TABS_TIENE_FICHAS) && !(window.CUENTA && CUENTA.web)) w.appendChild(sec2); return w;   // v260: el Creador de fichas, solo en local hasta que esté terminado
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
    if (job.nf) { job.end = true; F3.jobs = F3.jobs.filter(j => j !== job); F3.fallos = [{ t: Date.now(), msg: String(msg || 'sin motivo'), nombre: (job.it && job.it.name) || 'Ficha nueva' }].concat(F3.fallos || []).slice(0, 12); toast('No se pudo generar la ficha: ' + msg); rpinta(); return; }   // v302: el fallo se queda a la vista en la galería
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
    const R = [baseK() === 'otra' ? { key: 'base', data: F3.baseData, thumb: F3.baseData, name: 'Tu imagen de partida' } : { key: 'base', path: baseSrc(), name: baseNombre() }];   // v303: la ficha de partida elegida
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
    if (pj || baseK() !== 'combo') { const R0 = nfRefs(); const man = R0.filter(r => r.p).map(r => r.tag).join(' and '); const k = baseK();   // v303: también para «solo la cara», «solo el cuerpo» u otra imagen
      const vistas = k === 'cara' ? ': four views of her head and upper body' : k === 'cuerpo' ? ': her full body' : pj && pj.combo ? ': four views of her head and upper body, then her full body from the front and from the side' : '';
      const ropa = ps.length ? `she now wears EXACTLY the outfit of ${ps.map(r => `${r.tag} (${r.p.name})`).join(' combined with ')} — every garment, color, fabric, pattern and detail — as far as each panel shows it` : 'she keeps her clothes';
      const intro = k === 'otra' ? 'Edit @Image1, a reference image of her' : `Edit @Image1, her character reference sheet (several views of the same person${vistas})`;
      const t = `${intro}. Keep EXACTLY the same layout, the same panels, framing and crops, poses, expressions, face, hair, accessories, body shape and proportions, the background and the light. ONLY change what she wears: in every panel ${ropa}.${obj}${man ? ` The person wearing the outfit in ${man} is only a mannequin for the clothes: never copy her face, hair, glasses or earrings.` : ''} Photoreal, sharp, natural skin texture, no text, no labels, no extra panels.`;
      return pj && typeof genderize === 'function' ? genderize(t, pj.genero) : t; }
    return `Edit @Image1, her character reference sheet: on the left a 2x2 grid of her head and upper body (top-left front view with a big joyful toothy smile, top-right left side profile, bottom-left three-quarter view smiling, bottom-right back view), then a full-body FRONT view and a full-body left SIDE PROFILE view, both from the neck down. Keep EXACTLY the same layout, the same six panels, framing and crops, poses, expressions, face, hair, glasses, earrings, body shape and proportions, the gray studio background and the soft light. ONLY change what she wears: in all six panels ${outfit}.${obj} Whatever she wears in @Image1 (a tank top, plain underwear) is only the base: none of it stays visible unless the new outfit shows it. Photoreal, sharp, natural skin texture, no text, no labels, no extra panels.`;
  }
  async function nfGenerate() {
    if (!LIVE) { toast('Conecta primero tu API (arriba, «Conecta tu API»)'); return; } if (!F3.prendas.length && !F3.acc.length && !F3.extras.length) { toast('Elige primero la ropa o algún objeto'); return; }
    const R = nfRefs(); const images = R.map(r => r.data ? { data: r.data } : { path: r.path.split('?')[0] });
    const m = nfModelFor(images.length);
    const usd = m.usd[NFQ]; if (!(await pregunta(`¿Generar la ficha nueva con ${m.name} a 2K? (${fmtUsd(usd)})`))) return;
    const prompt = nfPrompt(); F3.sending = true; rpinta();
    const pj0 = pjOf(); const body = { item: 'ficha_nueva', prompt, images, aspect: baseAspect(), quality: NFQ, model: m.key, meta: { name: 'Ficha nueva · ' + (R.filter(r => r.p).map(r => r.p.name).join(' + ') || 'objetos'), tab: 'perfil', personaje: '_fichas', hidden: true, model: m.name, ep: m.ep, prompt, nf: { owner: F3.owner || undefined, nombre: nfNombre(), prendas: F3.prendas.slice(), acc: F3.acc.slice(), extras: F3.extras.map(x => x.label || 'objeto') } } };
    let r; try { r = await fetch('/api/generar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
    F3.sending = false; if (!r || r.error) { toast('No se pudo generar: ' + (r ? r.error : 'sin respuesta')); rpinta(); return; }
    const job = { rid: r.request_id, it: { id: 'nf', name: body.meta.name }, tab: 'perfil', m, kind: 'image', nf: true, owner: F3.owner || null, t0: performance.now(), status: 'queued', usd: r.usd != null ? Number(r.usd) : usd, prendas: F3.prendas.slice(), acc: F3.acc.slice(), extras: F3.extras.map(x => x.label || 'objeto') };
    JOBS.set(job.rid, job); F3.jobs.push(job); ensurePoller(); rpinta();
  }
  async function nfFinish(job, st) {
    job.end = true; F3.jobs = F3.jobs.filter(j => j !== job); const usd = st.usd != null ? Number(st.usd) : (job.usd || 0); state.nGen++; state.spent += usd; meter();
    if (job.owner) { if (window.pjReload) await pjReload(); } else await comboApi({ action: 'ensure' }); F3.pick = st.file; F3.meta = F3.meta || {}; F3.meta[st.file] = { prendas: job.prendas, acc: job.acc, extras: job.extras }; // el puente ya la ha guardado en Fichas creadas: aquí solo se refresca
    toast('Ficha nueva lista y guardada en «Fichas creadas» · ' + fmtUsd(usd)); rpinta();
  }
  async function nfGuardar() {
    const f = F3.pick; if (!f) return; const mt = (F3.meta || {})[f] || { prendas: F3.prendas, acc: F3.acc, extras: F3.extras.map(x => x.label || 'objeto') };
    const nm = (($('#nfName') || {}).value || '').trim() || 'Aria · ' + (mt.prendas.map(prenda).filter(Boolean).map(p => p.name).join(' + ') || 'ficha nueva');
    const r = await comboApi({ action: 'save', file: f, nombre: nm, prendas: mt.prendas, acc: mt.acc, extras: mt.extras }); if (!r) return;
    Object.assign(F3, { open: false, pick: null }); toast(`«${nm}» guardada en Fichas creadas`); window.pjScrollTop = true; rpinta();
  }
  function elegirPrenda() { if (enPagina()) return pickPrenda();   // v302: en el Creador de fichas, sin salir de la página
    if (!window.startPick) { toast('Actualiza la página'); return; }
    startPick('vestidor', { label: 'tu ficha nueva', done: it => { F3.prendas = [it.id]; F3.open = true; if (window.PJ) { PJ.sel = OW(); PJ.tabBy = Object.assign(PJ.tabBy || {}, { [OW()]: 'ficha' }); } setTab('perfil'); toast(`«${it.name}» añadida a la ficha nueva`); setTimeout(() => { const s = document.querySelector('.nfstep.s3'); if (s) s.scrollIntoView({ block: 'start', behavior: 'smooth' }); }, 120); }, cancel: () => { F3.open = true; if (window.PJ) { PJ.sel = OW(); PJ.tabBy = Object.assign(PJ.tabBy || {}, { [OW()]: 'ficha' }); } setTab('perfil'); } });
  }
  function elegirComplementos() { if (enPagina()) return pickAcc();
    const back = () => { F3.open = true; if (window.PJ) { PJ.sel = OW(); PJ.tabBy = Object.assign(PJ.tabBy || {}, { [OW()]: 'ficha' }); } rpinta(); setTimeout(() => { const s = document.querySelector('.nfstep.s3'); if (s) s.scrollIntoView({ block: 'start', behavior: 'smooth' }); }, 120); };
    window.accPick = { label: 'tu ficha nueva', sel: F3.acc.slice(), done: ids => { F3.acc = ids; back(); toast(ids.length === 1 ? 'Complemento añadido a la ficha nueva' : `${ids.length} complementos añadidos a la ficha nueva`); }, cancel: back };
    if (window.PJ) { PJ.sel = OW(); PJ.tabBy = Object.assign(PJ.tabBy || {}, { [OW()]: 'complementos' }); } window.pjScrollTop = true; rpinta();
  }
  const step = (n, t, sub, cls) => { const g = el('div', 'pjgrp nfstep ' + (cls || '')); g.appendChild(el('h4', '', `<i class="nfn">${n}</i>${t}${sub ? `<small>${sub}</small>` : ''}`)); return g; };
  window.f3Render = function (host) {
    if (!F3.open) return false; host.innerHTML = ''; const w = el('div', 'nfwrap');
    const bk0 = el('button', 'btn fxback', F3.owner ? '← Volver al creador de fichas' : '← Volver a Fichas 360'); bk0.onclick = () => { F3.open = false; if (window.PJ) PJ.sel = OW(); window.pjScrollTop = true; rpinta(); }; if (!enPagina()) w.appendChild(bk0);
    w.appendChild(el('div', 'pjwhd', `<div><h3>Nueva ficha</h3><p>Su ficha principal con otra ropa y otros objetos: las cuatro vistas y el cuerpo entero salen en una sola imagen, de una vez.</p></div>`));
    // 1 · personaje
    const s1 = step(1, 'Personaje', 'la ficha se hace con ella'); const pc = el('div', 'nfchar', `<img class="av" src="${P().avatar || C.base.thumb}" alt=""><div><b>${P().name}</b><small>Se parte de: ${baseNombre().toLowerCase()}</small></div><img class="base" src="${baseThumb()}" alt="">`); pc.querySelector('.base').onclick = () => lightbox(baseSrc(), baseNombre()); s1.appendChild(pc); if (enPagina()) s1.appendChild(baseSel()); w.appendChild(s1);
    // 2 · ropa (del Vestidor)
    const s2 = step(2, 'Ropa', 'del Vestidor', 's2'); const ch = el('div', 'nfchips'); const pr = F3.prendas.map(prenda).filter(Boolean)[0];
    if (pr) { const c = el('div', 'nfchip', `<img src="${pr.card}" alt=""><b>${pr.name}</b>`); const x = el('button', 'pjx', '×'); x.title = 'Quitar'; x.onclick = () => { F3.prendas = []; rpinta(); }; c.appendChild(x); c.querySelector('img').onclick = () => lightbox(pr.ficha, pr.name); const cb = el('button', 'lnk nfchg', 'Cambiar'); cb.onclick = elegirPrenda; c.appendChild(cb); ch.appendChild(c); }
    else { const pb = el('button', 'nfpick', `<span>👗</span><b>Elegir en el Vestidor</b><small>vas al Vestidor, eliges y vuelves aquí</small>`); pb.onclick = elegirPrenda; ch.appendChild(pb); }
    s2.appendChild(ch); w.appendChild(s2);
    // 3 · complementos: se eligen en su pestaña (como la ropa) o se suelta la foto de un objeto
    const s3 = step(3, 'Complementos', 'opcional · de su pestaña de complementos o la foto de un objeto', 's3');
    const fijos = accAll().filter(c => c.regla === 'siempre'); if (fijos.length) s3.appendChild(el('small', 'pjnote', `Ya lleva siempre: ${fijos.map(c => c.nombre).join(', ')}.`));
    const ac = el('div', 'nfaccs'); accSel().forEach(c => { const d = el('div', 'nfacc on', `${(c.thumb || c.img) ? `<img src="${c.thumb || c.img}" alt="">` : '<span>✨</span>'}<b>${c.nombre}</b>`); const x = el('button', 'pjx', '×'); x.title = 'Quitar'; x.onclick = () => { F3.acc = F3.acc.filter(z => z !== c.id); rpinta(); }; d.appendChild(x); ac.appendChild(d); });
    F3.extras.forEach((x, i) => { const d = el('div', 'nfacc on extra', `<img src="${x.data}" alt="">`); const li = el('input', 'pjin'); li.placeholder = 'Qué es · ej.: black bucket hat'; li.value = x.label || ''; li.oninput = () => { x.label = li.value; }; d.appendChild(li); const q = el('button', 'pjx', '×'); q.onclick = () => { F3.extras.splice(i, 1); rpinta(); }; d.appendChild(q); ac.appendChild(d); });
    { const pb = el('button', 'nfpick', `<span>🧩</span><b>${accSel().length ? 'Elegir más' : 'Elegir en Complementos'}</b><small>vas a sus complementos, marcas y vuelves aquí</small>`); pb.onclick = elegirComplementos; ac.appendChild(pb); }
    { const z = el('label', 'nfdrop', '<span>＋</span><b>Suelta aquí un objeto</b><small>o haz clic para subir su foto</small>'); const f = document.createElement('input'); f.type = 'file'; f.accept = 'image/*'; f.hidden = true; z.appendChild(f);
      const rd = file => { if (!file || !/^image\//.test(file.type)) return; const r = new FileReader(); r.onload = () => { F3.extras.push({ data: r.result, label: '' }); rpinta(); }; r.readAsDataURL(file); };
      f.onchange = () => rd(f.files[0]); z.ondragover = e => { e.preventDefault(); z.classList.add('over'); }; z.ondragleave = () => z.classList.remove('over'); z.ondrop = e => { e.preventDefault(); z.classList.remove('over'); rd(e.dataTransfer.files[0]); }; ac.appendChild(z); }
    s3.appendChild(ac); w.appendChild(s3);
    // 4 · generar (una sola imagen) y elegir la mejor versión
    const nR = nfRefs().length; const m = nfModelFor(nR); const cost = fmtUsd(m.usd[NFQ]);
    const s4 = step(4, 'Generar la ficha', 'una sola imagen: 4 vistas + cuerpo de frente y de perfil', 's4');
    { const row = el('div', 'nfmodel'); row.appendChild(el('small', 'pjk', 'Modelo')); const ms = el('select', 'sel'); MODELS.forEach(x => { const o = document.createElement('option'); o.value = x.key; o.textContent = `${x.name} · ${fmtUsd(x.usd[NFQ])}${x.refs < nR ? ` · solo ${x.refs} referencias` : ''}`; ms.appendChild(o); }); ms.value = nfModel().key;
      ms.onchange = () => { F3.model = ms.value; try { localStorage.setItem(MKEY, ms.value); } catch (e) {} rpinta(); }; row.appendChild(ms); if (m.key !== nfModel().key) row.appendChild(el('small', 'pjnote', `Van ${nR} referencias: esta ficha irá con ${m.name}`)); s4.appendChild(row); }
    const rr = el('div', 'fxrefs'); nfRefs().forEach(r => rr.appendChild(el('span', 'fxref', `<i style="background-image:url('${r.thumb || r.path}')"></i><b>${r.tag} · ${esc(r.name)}</b>`))); s4.appendChild(el('small', 'pjk', 'Se basa en')); s4.appendChild(rr);
    const det = el('details', 'fxprompt nfprompt'); det.appendChild(el('summary', '', 'Ver el prompt que se enviará')); det.appendChild(el('div', 'promptbox', esc(nfPrompt()))); s4.appendChild(det);
    const ok = F3.prendas.length || F3.acc.length || F3.extras.length; const gb = el('button', 'btn acc pr nfgen', F3.sending ? '⏳ Enviando…' : `${nfHist().length || F3.jobs.length ? 'Generar otra versión' : 'Generar la ficha'}<i>${cost}</i>`); gb.disabled = !!F3.sending || !ok; if (!ok) gb.title = 'Elige primero la ropa o algún objeto'; gb.onclick = nfGenerate; s4.appendChild(gb); if (enPagina()) s4.appendChild(el('small', 'pjnote', 'Cada versión aparece en la galería de la derecha: mientras se genera, cuando está lista y también si falla.'));
    const H = nfHist(); if (!enPagina() && (H.length || F3.jobs.length)) {
      const vg = el('div', 'nfvers'); F3.jobs.slice().reverse().forEach(j => vg.appendChild(el('div', 'nfv gen', `<i class="spin"></i><b>Generando</b><small data-t0="${j.t0}">${Math.round((performance.now() - j.t0) / 1000)} s</small>`)));
      H.forEach(f => { const t = el('button', 'nfv' + (F3.pick === f ? ' on' : ''), `<img src="${f}" alt="">`); t.onclick = () => { F3.pick = F3.pick === f ? null : f; rpinta(); }; t.ondblclick = () => lightbox(f, 'Ficha nueva'); vg.appendChild(t); });
      s4.appendChild(el('small', 'pjk', 'Versiones · elige la mejor')); s4.appendChild(vg);
    }
    if (F3.pick && !enPagina()) { const big = el('div', 'nfbig', `<img src="${F3.pick}" alt="">`); big.onclick = () => lightbox(F3.pick, 'Ficha nueva'); s4.appendChild(big);
      const sv0 = nfSaved(F3.pick); const r5 = el('div', 'pjacts');
      if (sv0) { r5.appendChild(el('span', 'nfok', `✓ Guardada en «Fichas creadas» como <b>${esc(sv0.nombre)}</b>`)); const bk = el('button', 'btn acc', 'Ver en Fichas creadas'); bk.onclick = () => { F3.open = false; window.pjScrollTop = true; rpinta(); }; r5.appendChild(bk); }
      else if (pjOf()) r5.appendChild(el('span', 'nfok', 'Esta versión se guarda sola al terminar.'));
      else { const nm = el('input', 'pjin'); nm.id = 'nfName'; nm.style.maxWidth = '360px'; nm.value = nfNombre(); r5.appendChild(nm); const sv = el('button', 'btn acc', '✓ Guardar en Fichas creadas'); sv.onclick = nfGuardar; r5.appendChild(sv); }
      s4.appendChild(r5);
      s4.appendChild(el('small', 'pjnote', 'Cada ficha que generas se guarda sola en «Fichas creadas». Allí puedes hacerla principal, usarla en vídeo, descargarla o borrarla.')); }
    w.appendChild(s4);
    host.appendChild(w);
    clearInterval(F3.tick); if (F3.jobs.length) F3.tick = setInterval(() => { if (!document.querySelector('.nfwrap')) { clearInterval(F3.tick); return; } document.querySelectorAll('.nfwrap [data-t0]').forEach(n => { n.textContent = Math.round((performance.now() - +n.dataset.t0) / 1000) + ' s'; }); }, 1000);
    return true;
  };

  // ------------------------------------------------ v302: el Creador de fichas como página propia (⚙️ Admin): constructor a la izquierda, galería a la derecha
  function enPagina() { return !!document.querySelector('#fichpage'); }
  function rpinta() { if (enPagina()) window.fichPinta(); else if (state.tab === 'perfil') renderProfile(); }
  function pickModal(id, titulo) { let m0 = document.querySelector('#' + id); if (m0) m0.remove(); m0 = el('div', 'fxm'); m0.id = id; document.body.appendChild(m0); const cierra = () => m0.remove(); m0.onclick = e => { if (e.target === m0) cierra(); };
    const b = el('div', 'devbox f3pickbox'); m0.appendChild(b); const x = el('button', 'btn carpverx', '✕'); x.onclick = cierra; b.appendChild(x); b.appendChild(el('h3', '', titulo)); return [b, cierra]; }
  function pickPrenda() { const L = (TABS.vestidor.items || []).filter(v => !v.pending && v.ficha && v.card); const [b, cierra] = pickModal('f3pick', '👗 Elige la ropa');
    const q = el('input', 'f3pickq'); q.placeholder = `Buscar entre ${L.length} prendas…`; b.appendChild(q); const g = el('div', 'f3pickg'); b.appendChild(g);
    const pinta = () => { g.innerHTML = ''; const t = q.value.trim().toLowerCase(); const M = L.filter(v => !t || (String(v.name || '') + ' ' + [].concat(v.tags || []).join(' ')).toLowerCase().includes(t));
      M.forEach(v => { const c = el('button', 'f3pickc' + (F3.prendas.includes(v.id) ? ' on' : ''), `<img src="${v.card}" alt="" loading="lazy"><b>${esc(v.name || 'Prenda')}</b>`); c.type = 'button'; c.onclick = () => { F3.prendas = [v.id]; cierra(); rpinta(); toast(`«${v.name}» en la ficha nueva`); }; g.appendChild(c); });
      if (!M.length) g.appendChild(el('p', 'vozvacio', 'Ninguna prenda con ese nombre.')); };
    q.oninput = pinta; pinta(); setTimeout(() => q.focus(), 50); }
  function pickAcc() { const L = accAll(); if (!L.length) { toast('Todavía no tiene complementos'); return; } const sel = new Set(F3.acc); const [b, cierra] = pickModal('f3pick', '🧩 Elige complementos');
    const g = el('div', 'f3pickg'); b.appendChild(g); L.forEach(c => { const t = el('button', 'f3pickc' + (sel.has(c.id) ? ' on' : ''), `${(c.thumb || c.img) ? `<img src="${c.thumb || c.img}" alt="" loading="lazy">` : '<span class="f3pickno">✨</span>'}<b>${esc(c.nombre || 'Complemento')}</b>`); t.type = 'button'; t.onclick = () => { if (sel.has(c.id)) sel.delete(c.id); else sel.add(c.id); t.classList.toggle('on', sel.has(c.id)); }; g.appendChild(t); });
    const pie = el('div', 'vozpie'); pie.appendChild(el('span', '', 'Toca para marcar o desmarcar')); const ok = el('button', 'btn acc', 'Listo'); ok.onclick = () => { F3.acc = [...sel]; cierra(); rpinta(); }; pie.appendChild(ok); b.appendChild(pie); }
  window.fichPinta = function () {
    const pg = document.querySelector('#fichpage'); if (!pg) return; F3.open = true; if (F3._medido !== baseSrc()) medir();
    const y1 = (pg.querySelector('.fichizq') || {}).scrollTop || 0, y2 = (pg.querySelector('.fichder') || {}).scrollTop || 0;
    pg.innerHTML = ''; const w = el('div', 'fich'); pg.appendChild(w); const izq = el('div', 'fichizq'), der = el('div', 'fichder'); w.appendChild(izq); w.appendChild(der);
    const hd = el('div', 'fichhd', '<h2>🧍 Creador de fichas</h2><small>solo el equipo</small>'); const x = el('button', 'btn fichx', '✕'); x.title = 'Cerrar'; x.onclick = () => window.fichCierra && fichCierra(); hd.appendChild(x); izq.appendChild(hd);
    const host = el('div', ''); izq.appendChild(host); window.f3Render(host);
    ensureCombo(); const same = (a, b) => (a || '').split('?')[0] === (b || '').split('?')[0];
    const V = []; const g = el('div', 'fichgrid');
    const tarjeta = (src, nombre, sub, acts, cls) => { const k = V.length; V.push({ src: String(src).replace('_t.jpg', '.jpg'), nombre, info: sub, acts }); const d = el('button', 'fichc ' + (cls || ''), `<img class="fichim" src="${src}" alt="" loading="lazy"><span class="fichtx"><b>${esc(nombre)}</b><small>${esc(sub || '')}</small></span>`); d.type = 'button'; d.onclick = () => visorFichas(V, k); g.appendChild(d); };
    tarjeta(P().comboThumb || principal(), 'Ficha principal', 'de la que parten todas', [['⬇', () => dl(principal()), 'Descargar']], 'prin');   // v303: siempre la primera
    F3.jobs.slice().reverse().forEach(j => g.appendChild(el('div', 'fichc gen', `<span class="fichim fichspin"><i class="spin"></i><b data-t0="${j.t0}">${Math.round((performance.now() - j.t0) / 1000)} s</b></span><span class="fichtx"><b>${esc(j.it.name)}</b><small>Generando…</small></span>`)));
    (F3.fallos || []).forEach((f, i) => { const d = el('div', 'fichc mal', `<span class="fichim fichmal">⚠️<small>${esc(f.msg)}</small></span><span class="fichtx"><b>${esc(f.nombre)}</b><small>No se ha generado · ${new Date(f.t).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}</small></span>`); const q = el('button', 'fichq', '✕'); q.title = 'Quitar este aviso'; q.onclick = () => { F3.fallos.splice(i, 1); rpinta(); }; d.appendChild(q); g.appendChild(d); });
    const info = f => [f.t, f.modelo, f.size ? (f.size[0] >= 2400 ? '2K' : f.size[0] < 1500 ? '1K · baja resolución' : '') : ''].filter(Boolean).join(' · ');
    const fuera = fn => async () => { if (window.fichCierra) fichCierra(); await fn(); };
    const out = (P().fichas || []).filter(f => !same(f.img, P().combo)).slice().sort((a, b) => String(b.t || '').localeCompare(String(a.t || '')));   // v303: de la más nueva a la más vieja
    nfHist().filter(f => !nfSaved(f) && !out.some(o => same(o.img, f))).slice().reverse().forEach(f => tarjeta(f, 'Versión sin guardar', 'recién generada', [['✓ Guardar en Fichas creadas', async () => { const mt = (F3.meta || {})[f] || { prendas: F3.prendas, acc: F3.acc, extras: F3.extras.map(x => x.label || 'objeto') }; const nm = nfNombre(); if (await comboApi({ action: 'save', file: f, nombre: nm, prendas: mt.prendas, acc: mt.acc, extras: mt.extras })) { toast(`«${nm}» guardada`); rpinta(); } }], ['⬇', () => dl(f), 'Descargar']], 'suelta'));
    out.forEach(f => tarjeta(f.thumb || f.img, f.nombre, info(f), [['⬇', () => dl(f.img), 'Descargar'], ['✨', fuera(() => fichaAImagen(f.img, f.nombre)), 'Usar en Crear imagen'], ['🎬', fuera(() => window.FBapi && FBapi.usarEnVideo(f)), 'Usar en Crear vídeo'], ['🗑', async () => { await (window.FBapi && FBapi.borrar(f)); rpinta(); }, 'Borrar']]));
    der.appendChild(el('div', 'fichhd2', `<h3>Fichas</h3><small>${out.length} creada${out.length === 1 ? '' : 's'}${F3.jobs.length ? ` · ${F3.jobs.length} generando` : ''} · toca una para verla en grande</small>`)); der.appendChild(g);
    izq.scrollTop = y1; der.scrollTop = y2;
    clearInterval(F3.ptick); if (F3.jobs.length) F3.ptick = setInterval(() => { if (!enPagina()) { clearInterval(F3.ptick); return; } document.querySelectorAll('#fichpage .fichspin [data-t0]').forEach(n => { n.textContent = Math.round((performance.now() - +n.dataset.t0) / 1000) + ' s'; }); }, 1000);
  };

  // ------------------------------------------------ v303: de qué ficha se parte (la principal, solo la cara, solo el cuerpo u otra imagen) y con qué personaje
  const BASES = [['combo', 'Cara y cuerpo'], ['cara', 'Solo la cara'], ['cuerpo', 'Solo el cuerpo'], ['otra', 'Otra imagen']];
  function baseDe(k) { const p = P(); return k === 'combo' ? principal() : k === 'cara' ? p.ficha : k === 'cuerpo' ? p.cuerpo : F3.baseData; }
  function baseK() { const k = F3.base || 'combo'; if (k === 'otra') return F3.baseData ? 'otra' : 'combo'; return baseDe(k) ? k : 'combo'; }
  function baseSrc() { return baseDe(baseK()); }
  function baseThumb() { return baseK() === 'combo' ? (P().comboThumb || principal()) : baseSrc(); }
  function baseNombre() { return { combo: 'Su ficha principal (cara y cuerpo)', cara: 'Su ficha de la cara', cuerpo: 'Su ficha de cuerpo', otra: 'Tu imagen' }[baseK()]; }
  function medir() { const src = baseSrc(); F3._medido = src; F3.baseRatio = null; if (!src) return; const im = new Image(); im.onload = () => { if (F3._medido === src) F3.baseRatio = im.naturalWidth / im.naturalHeight; }; im.src = src; }
  function baseAspect() { const pj0 = pjOf(); const k = baseK(); if (k === 'combo') return pj0 && !pj0.combo ? '2:3' : '16:9'; const r = F3.baseRatio || (k === 'cara' ? 2 / 3 : 16 / 9); const A = (typeof ASPECTS !== 'undefined' && ASPECTS.length) ? ASPECTS : ['16:9', '3:2', '1:1', '2:3']; let best = A[0], d = 99; A.forEach(a => { const [x, y] = a.split(':').map(Number); const dd = Math.abs(Math.log((x / y) / r)); if (dd < d) { d = dd; best = a; } }); return best; }
  function leeBase(file) { if (!file || !/^image\//.test(file.type)) { toast('Tiene que ser una imagen'); return; } const r = new FileReader(); r.onload = () => { F3.baseData = r.result; F3.base = 'otra'; medir(); rpinta(); }; r.readAsDataURL(file); }
  function baseSel() {
    const w = el('div', 'nfbase');
    const L = [{ id: null, nombre: C.perfil.name || 'Aria Cruz', av: C.perfil.avatar || C.base.thumb }].concat(((window.PJ && PJ.list) || []).filter(p => p.ficha360 || p.combo).map(p => ({ id: p.id, nombre: p.nombre || 'Personaje', av: p.avatar || p.foto || p.ficha360 })));
    if (L.length > 1) { const r = el('div', 'nfpjs'); L.forEach(p => { const b = el('button', 'nfpj' + ((F3.owner || null) === p.id ? ' on' : ''), `<img src="${p.av}" alt=""><b>${esc(String(p.nombre).split(' ')[0])}</b>`); b.type = 'button'; b.onclick = () => { if ((F3.owner || null) === p.id) return; Object.assign(F3, { owner: p.id, acc: [], pick: null }); medir(); rpinta(); }; r.appendChild(b); }); w.appendChild(el('small', 'pjk', 'Personaje')); w.appendChild(r); }
    w.appendChild(el('small', 'pjk', 'Ficha de partida')); const seg = el('div', 'nfseg'); const k0 = baseK();
    const fi = document.createElement('input'); fi.type = 'file'; fi.accept = 'image/*'; fi.hidden = true; fi.onchange = () => leeBase(fi.files[0]); w.appendChild(fi);
    BASES.forEach(([k, t]) => { const ok = k === 'otra' || !!baseDe(k); const b = el('button', k === k0 ? 'on' : '', t); b.type = 'button'; b.disabled = !ok; if (!ok) b.title = 'Este personaje no tiene esa ficha'; b.onclick = () => { if (k === 'otra' && !F3.baseData) { fi.click(); return; } F3.base = k; medir(); rpinta(); }; seg.appendChild(b); });
    w.appendChild(seg);
    if (k0 === 'otra') { const c = el('div', 'nfotra'); const cb = el('button', 'lnk', 'Cambiar la imagen'); cb.onclick = () => fi.click(); const q = el('button', 'lnk', 'Quitar'); q.onclick = () => { F3.baseData = null; F3.base = 'combo'; medir(); rpinta(); }; c.appendChild(cb); c.appendChild(q); w.appendChild(c); }
    const z = el('div', 'nfbdrop', '⤓ O arrastra aquí una imagen de tu ordenador para partir de ella'); z.onclick = () => fi.click(); z.ondragover = e => { e.preventDefault(); z.classList.add('over'); }; z.ondragleave = () => z.classList.remove('over'); z.ondrop = e => { e.preventDefault(); z.classList.remove('over'); leeBase(e.dataTransfer.files[0]); }; w.appendChild(z);
    return w; }
})();
