// ARIA STUDIO · FICHAS PARA VÍDEO (v105)
// La ficha 360 de Aria con la ropa que eliges del Vestidor (+ sombrero, zapatos u otros objetos) y, a la derecha, su cuerpo entero con esa ropa.
// Dos imágenes que se aprueban por separado (como las vistas del creador de personajes) y el puente las une en una sola ficha, casi cuadrada.
(function () {
  const FB = window.FB = { open: false, prendas: [], extras: [], notas: '', res: {}, jobs: {}, q: '' };
  const SLOTS = [['vistas', 'Ficha 360 con la ropa', '2:3', '4 vistas: frente, perfil, tres cuartos y espalda'], ['cuerpo', 'Cuerpo entero', '9:16', 'del cuello a los zapatos: la cara ya está en la ficha']];
  const prenda = id => (TABS.vestidor.items || []).find(v => v.id === id);
  const fichas = () => C.perfil.fichas || [];
  const ident = () => ['same face, green eyes'].concat((C.perfil.complementos || []).filter(c => c.regla === 'siempre').map(c => c.desc)).join(', ');
  function refs() { // @Image1 = ficha 360 · (cuerpo) · prendas · objetos extra
    return { prendas: FB.prendas.map(prenda).filter(Boolean), extras: FB.extras.filter(x => x.data) };
  }
  function promptFor(kind) {
    const { prendas, extras } = refs(); let n = kind === 'cuerpo' ? 3 : 2; const P = prendas.map(p => ({ tag: '@Image' + n++, p })); const X = extras.map(x => ({ tag: '@Image' + n++, x }));
    const outfit = P.map(o => `${o.tag} (${o.p.name})`).join(' combined with ');
    const ext = X.length ? ', plus ' + X.map(o => `${o.x.label || 'this item'} exactly as in ${o.tag}`).join(', ') : '';
    const notes = FB.notas.trim() ? ` Also: ${FB.notas.trim()}.` : '';
    if (kind === 'vistas') return `Recreate @Image1 EXACTLY as it is: the same 2x2 character reference sheet of the same woman (top-left front view smiling, top-right left side profile, bottom-left three-quarter view smiling, bottom-right back three-quarter view), same framing and crops, ${ident()}, same hair, same neutral gray studio background and soft even light. ONLY change her clothing: in every panel she now wears EXACTLY the outfit of ${outfit || 'the reference'} (same garments, colors, fabrics and details, as far as each crop shows them)${ext}.${notes} Nothing else changes. Photoreal, no text, no labels.`;
    return `Vertical studio photo of the body of the woman of @Image1 (her 360 character sheet, for her skin, hair color and build) with the body of @Image2 (her body reference sheet; the white underwear there is ONLY a body reference, never copy it), framed FROM THE NECK DOWN: the top edge of the image cuts just below her chin, so her face is NOT visible (the face is already shown in her character sheet); from the neck down to the shoes everything is visible, with a little space below the feet. She stands straight facing the camera in a relaxed natural pose, arms slightly away from the body. She wears EXACTLY the complete outfit of ${outfit || 'the reference'} (every piece, same colors, fabrics and details, and its shoes)${ext}.${notes} Plain neutral gray studio background matching @Image1, soft even studio light, photoreal, natural skin texture, no text, no labels.`;
  }
  async function generate(kind) {
    if (!LIVE) { toast('Hace falta el puente'); return; } const { prendas, extras } = refs();
    if (!prendas.length) { toast('Elige primero la ropa del Vestidor'); return; }
    const images = [{ path: C.perfil.ficha }].concat(kind === 'cuerpo' && C.perfil.cuerpo ? [{ path: C.perfil.cuerpo }] : []).concat(prendas.map(p => ({ path: p.ficha.split('?')[0] }))).concat(extras.map(x => ({ data: x.data })));
    let m = curModel(); if (images.length > m.refs) { const g = MODELS.find(x => x.refs >= images.length && x.prov === 'ws') || MODELS.find(x => x.refs >= images.length); if (g) { m = g; toast(`Van ${images.length} referencias: esta ficha va con ${g.name}`); } }
    const usd = m.usd[state.quality]; const s = SLOTS.find(x => x[0] === kind);
    if (!confirm(`¿Generar «${s[1]}» con ${m.name}? (${fmtUsd(usd)})`)) return;
    const prompt = promptFor(kind); FB.sending = Object.assign({}, FB.sending, { [kind]: true }); renderProfile(); // un clic = una petición
    const body = { item: 'ficha_video_' + kind, prompt, images, aspect: s[2], quality: state.quality, model: m.key, meta: { name: `Ficha para vídeo · ${s[1]}`, tab: 'perfil', personaje: '_fichas', hidden: true, model: m.name, ep: m.ep, prompt } };
    let r; try { r = await fetch('/api/generar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
    FB.sending[kind] = false;
    if (!r || r.error) { toast('No se pudo generar: ' + (r ? r.error : 'sin respuesta')); renderProfile(); return; }
    const job = { rid: r.request_id, it: { id: 'fichaout:' + kind, name: body.meta.name }, tab: 'perfil', m, kind: 'image', fichaOut: kind, t0: performance.now(), status: 'queued', usd: r.usd != null ? Number(r.usd) : usd };
    JOBS.set(job.rid, job); FB.jobs[kind] = job; ensurePoller(); toast(`Generando «${s[1]}»…`); renderProfile();
  }
  const _fin = window.finishJob, _fail = window.failJob;
  window.finishJob = function (job, st) {
    if (!job.fichaOut) return _fin(job, st);
    job.end = true; delete FB.jobs[job.fichaOut]; const usd = st.usd != null ? Number(st.usd) : (job.usd || 0); state.nGen++; state.spent += usd; meter();
    FB.res[job.fichaOut] = { file: st.file, ok: false }; FB.ver = job.fichaOut; toast(`«${SLOTS.find(x => x[0] === job.fichaOut)[1]}» lista: apruébala o genera otra · ${fmtUsd(usd)}`); if (state.tab === 'perfil') renderProfile();
  };
  window.failJob = function (job, msg) { if (!job.fichaOut) return _fail(job, msg); job.end = true; delete FB.jobs[job.fichaOut]; toast('No se pudo generar: ' + msg); if (state.tab === 'perfil') renderProfile(); };
  async function guardar() {
    const nm = (document.querySelector('#fbName') || {}).value || ''; const { prendas } = refs();
    let r; try { r = await fetch('/api/fichas_outfit', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'save', nombre: nm.trim() || 'Aria · ' + prendas.map(p => p.name).join(' + '), prendas: FB.prendas, extras: FB.extras.map(x => x.label || 'objeto'), notas: FB.notas, vistas: FB.res.vistas.file, cuerpo: FB.res.cuerpo.file }) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
    if (!r || !r.ok) { toast('No se pudo guardar la ficha: ' + (r ? r.error : 'sin respuesta')); return; }
    C.perfil.fichas = r.list; Object.assign(FB, { open: false, prendas: [], extras: [], notas: '', res: {} }); toast('Ficha para vídeo guardada'); renderProfile();
    setTimeout(() => { const f = fichas()[0]; if (f) lightbox(f.img, f.nombre); }, 150);
  }
  async function borrar(f) { if (!confirm(`¿Borrar la ficha «${f.nombre}»? Pasa a la papelera de la app.`)) return; const r = await fetch('/api/fichas_outfit', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'delete', id: f.id }) }).then(x => x.json()).catch(e => ({ error: String(e) })); if (!r.ok) { toast('No se pudo borrar: ' + r.error); return; } C.perfil.fichas = r.list; renderProfile(); }
  function usarEnVideo(f) { poolAdd({ id: 'fichaout:' + f.id, kind: 'image', name: f.nombre, src: f.img, thumb: f.thumb || f.img }, true); vbadge(); toast(`«${f.nombre}» añadida a Crear vídeo`); setTab('video'); }
  function descargar(f) { const a = document.createElement('a'); a.href = f.img; a.download = f.nombre.replace(/[^\wáéíóúñ ·+-]/gi, '').replace(/\s+/g, '_') + '.jpg'; document.body.appendChild(a); a.click(); a.remove(); }

  // ------------------------------------------------ sección en el Perfil de Aria
  window.fbSection = function () {
    const box = el('div', 'pjgrp fbsec'); box.appendChild(el('h4', '', 'Fichas para vídeo<small>su ficha 360 con la ropa que elijas + cuerpo entero · para Higgsfield y Crear vídeo</small>'));
    const g = el('div', 'fbgrid'); fichas().forEach(f => {
      const d = el('div', 'fbcard', `<img src="${f.thumb || f.img}" alt=""><b>${f.nombre}</b>`); d.querySelector('img').onclick = () => lightbox(f.img, f.nombre);
      const a = el('div', 'fbacts'); [['⬇', 'Descargar', () => descargar(f)], ['🎬', 'Usar en Crear vídeo', () => usarEnVideo(f)], ['🗑', 'Borrar', () => borrar(f)]].forEach(([i, t, fn]) => { const b = el('button', '', i); b.title = t; b.onclick = e => { e.stopPropagation(); fn(); }; a.appendChild(b); }); d.appendChild(a); g.appendChild(d); });
    if (fichas().length) box.appendChild(g);
    const nb = el('button', 'btn w acc', '＋ Nueva ficha para vídeo'); nb.onclick = () => { FB.open = true; renderProfile(); }; box.appendChild(nb);
    return box;
  };
  // ------------------------------------------------ el creador (ocupa la zona grande del Perfil)
  window.fbRender = function (host) {
    if (!FB.open) return false; host.innerHTML = ''; const m = curModel(); const cost = fmtUsd(m.usd[state.quality]);
    const bk0 = el('button', 'btn fxback', '← Volver a Fichas 360'); bk0.onclick = () => { FB.open = false; renderProfile(); }; host.appendChild(bk0);
    const hd = el('div', 'pjwhd'); hd.appendChild(el('div', '', `<h3>Nueva ficha para vídeo</h3><p>Su ficha 360 con la ropa que elijas y, a la derecha, su cuerpo entero con esa ropa. Todo en una imagen.</p>`)); host.appendChild(hd);
    const st = el('div', 'pjstep');
    // 1 · la ropa
    const sel = el('div', 'fbsel'); if (!FB.prendas.length) sel.appendChild(el('span', 'pjnote', 'Elige hasta 3 prendas o conjuntos del Vestidor.'));
    FB.prendas.forEach(id => { const p = prenda(id); if (!p) return; const c = el('div', 'fbchip', `<img src="${p.card}" alt=""><b>${p.name}</b>`); const x = el('button', 'pjx', '×'); x.onclick = () => { FB.prendas = FB.prendas.filter(z => z !== id); FB.res = {}; renderProfile(); }; c.appendChild(x); sel.appendChild(c); });
    st.appendChild(grp('1 · La ropa', sel, 'del Vestidor'));
    const sr = el('input', 'pjin'); sr.placeholder = 'Buscar prenda por nombre o número…'; sr.value = FB.q; const lib = el('div', 'pjcards tall fblib');
    const paintLib = () => { lib.innerHTML = ''; const q = norm(FB.q || ''); const L = (TABS.vestidor.items || []).filter(v => !v.pending && (!q || norm(v.name).includes(q) || String(v.num) === q)).sort((a, b) => (b.fav ? 1 : 0) - (a.fav ? 1 : 0));
      L.slice(0, 120).forEach(v => { const on = FB.prendas.includes(v.id); const c = el('button', 'pjcard' + (on ? ' on' : ''), `<span class="pjvis"><img src="${v.card}" alt="" loading="lazy"></span><b>${v.fav ? '★ ' : ''}${v.name}</b>`); c.onclick = () => { if (on) FB.prendas = FB.prendas.filter(z => z !== v.id); else { if (FB.prendas.length >= 3) FB.prendas.shift(); FB.prendas.push(v.id); } FB.res = {}; renderProfile(); }; lib.appendChild(c); }); };
    sr.oninput = () => { FB.q = sr.value; paintLib(); }; paintLib(); const lw = el('div', 'stack'); lw.appendChild(sr); lw.appendChild(lib); st.appendChild(lw);
    // 2 · otros objetos
    const ex = el('div', 'pjrow'); FB.extras.forEach((x, i) => { const w = el('div', 'fbex'); w.appendChild(el('div', 'fbexim', `<img src="${x.data}" alt="">`)); const li = el('input', 'pjin'); li.placeholder = 'Qué es · ej.: black bucket hat'; li.value = x.label || ''; li.oninput = () => { x.label = li.value; }; w.appendChild(li); const q = el('button', 'pjx', '×'); q.onclick = () => { FB.extras.splice(i, 1); FB.res = {}; renderProfile(); }; w.appendChild(q); ex.appendChild(w); });
    if (FB.extras.length < 3) { const z = el('label', 'pjdrop fbdrop', '<span>＋</span><b>Sombrero, zapatos…</b><small>foto del objeto</small>'); const f = document.createElement('input'); f.type = 'file'; f.accept = 'image/*'; f.hidden = true; z.appendChild(f); const rd = file => { if (!file || !/^image\//.test(file.type)) return; const r = new FileReader(); r.onload = () => { FB.extras.push({ data: r.result, label: '' }); FB.res = {}; renderProfile(); }; r.readAsDataURL(file); }; f.onchange = () => rd(f.files[0]); z.ondragover = e => { e.preventDefault(); z.classList.add('over'); }; z.ondragleave = () => z.classList.remove('over'); z.ondrop = e => { e.preventDefault(); z.classList.remove('over'); rd(e.dataTransfer.files[0]); }; ex.appendChild(z); }
    st.appendChild(grp('2 · Otros objetos', ex, 'opcional · hasta 3'));
    const nt = el('textarea', 'pjin'); nt.placeholder = 'Notas opcionales · ej.: white chunky sneakers instead of the shoes of the outfit'; nt.value = FB.notas; nt.oninput = () => { FB.notas = nt.value; }; st.appendChild(grp('Notas', nt, 'en inglés funciona mejor'));
    // 3 · generar y aprobar
    const vw = el('div', 'fbslots'); SLOTS.forEach(([k, nm, ar, sub]) => {
      const r = FB.res[k], job = FB.jobs[k]; const w = el('div', 'pjvw fbslot' + (r && r.ok ? ' ok' : ''));
      w.appendChild(el('div', 'pjvimg fbimg ' + k, job ? '<div class="spin"></div>' : r ? `<img src="${r.file}" alt="">` : `<i>${k === 'vistas' ? '▦' : '▯'}</i>`)); if (r && !job) w.querySelector('.fbimg').onclick = () => lightbox(r.file, nm);
      w.appendChild(el('b', '', nm)); w.appendChild(el('small', 'pjnote', sub));
      const a = el('div', 'pjvact'); if (job) a.appendChild(el('small', '', 'Generando…')); else if (FB.sending && FB.sending[k]) a.appendChild(el('small', '', '⏳ Enviando…'));
      else if (!r) { const b = el('button', 'btn acc pr', `Generar<i>${cost}</i>`); b.disabled = !FB.prendas.length; b.onclick = () => generate(k); a.appendChild(b); }
      else if (!r.ok) { const y = el('button', 'btn acc', '✓ Aprobar'); y.onclick = () => { r.ok = true; renderProfile(); }; const n = el('button', 'btn', '↻ Otra'); n.onclick = () => generate(k); a.appendChild(y); a.appendChild(n); }
      else { a.appendChild(el('small', 'okk', '✓ Aprobada')); const n = el('button', 'btn', '↻'); n.title = 'Generar otra'; n.onclick = () => generate(k); a.appendChild(n); }
      w.appendChild(a); vw.appendChild(w); });
    st.appendChild(grp('3 · Genera y aprueba', vw, `con ${m.name} (se cambia en Crear imagen) · ${cost} cada una`));
    // 4 · guardar
    if (FB.res.vistas && FB.res.vistas.ok && FB.res.cuerpo && FB.res.cuerpo.ok) { const g4 = el('div', 'pjacts'); const nm = el('input', 'pjin'); nm.id = 'fbName'; nm.style.maxWidth = '360px'; nm.value = 'Aria · ' + refs().prendas.map(p => p.name).join(' + '); g4.appendChild(nm); const sv = el('button', 'btn acc', '✓ Unir y guardar la ficha'); sv.onclick = guardar; g4.appendChild(sv); st.appendChild(grp('4 · Guardar', g4, 'se unen en una sola imagen: la ficha 360 a la izquierda y el cuerpo entero a la derecha')); }
    host.appendChild(st);
    const nav = el('div', 'pjnav'); const bk = el('button', 'btn', '✕ Salir'); bk.onclick = () => { FB.open = false; renderProfile(); }; nav.appendChild(bk); host.appendChild(nav);
    return true;
  };
  function grp(t, node, sub) { const g = el('div', 'pjgrp'); g.appendChild(el('h4', '', t + (sub ? `<small>${sub}</small>` : ''))); g.appendChild(node); return g; }
  window.FBapi = { usarEnVideo, descargar, borrar };
})();
