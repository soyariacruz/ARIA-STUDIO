// ARIA STUDIO · COMPLEMENTOS DEL PERSONAJE (v111)
// Cada personaje tiene sus complementos con una regla: «siempre» (gafas, aros…), «en escena» (su móvil: solo si la foto tiene un móvil) o «nunca».
// En Crear imagen salen como chips que se encienden solos según la regla y la escena; los que tienen foto van como referencia @ImageN.
(function () {
  const T = {
    movil: { es: 'Móvil', emo: '📱', kw: /\b(phone|smartphone|selfie|iphone|cellphone|mobile|texting|scrolling)\b/i, no: 'phone' },
    gafas: { es: 'Gafas', emo: '👓', kw: /\b(glasses|eyewear|spectacles)\b/i, no: 'glasses', ident: true },
    gafassol: { es: 'Gafas de sol', emo: '🕶', kw: /\bsunglasses\b/i, no: 'sunglasses', ident: true },
    pendientes: { es: 'Pendientes', emo: '💎', kw: /\b(earrings?|hoops?)\b/i, no: 'earrings', ident: true },
    collar: { es: 'Collar', emo: '📿', kw: /\b(necklace|pendant|choker)\b/i, no: 'necklace', ident: true },
    reloj: { es: 'Reloj', emo: '⌚', kw: /\b(watch|wristwatch)\b/i, no: 'watch' },
    bolso: { es: 'Bolso', emo: '👜', kw: /\b(bag|handbag|purse|tote)\b/i, no: 'bag' },
    gorra: { es: 'Gorra o sombrero', emo: '🧢', kw: /\b(cap|hat|beanie)\b/i, no: 'hat' },
    otro: { es: 'Otro', emo: '✨', kw: null, no: '' },
  };
  const tipos = () => Object.assign({}, T, Object.fromEntries((C.perfil.accTipos || []).map(t => [t.id, { es: t.es, emo: t.emo || '🏷', kw: null, no: '' }])));
  const tipoOf = k => tipos()[k] || T.otro;
  const REGLAS = [['siempre', 'Siempre'], ['escena', 'Si sale en la escena'], ['nunca', 'Nunca']];
  const list = (owner = (window.CH ? CH().id : 'aria')) =>   // sin dueño explícito = el personaje activo de Crear imagen
    owner === 'aria' ? (C.perfil.complementos || []) : (((window.PJ && PJ.list) || []).find(p => p.id === owner) || {}).complementos || [];
  function setList(owner, L) { if (owner === 'aria') C.perfil.complementos = L; else { const p = PJ.list.find(x => x.id === owner); if (p) p.complementos = L; } }
  const cajaOk = b => { if (!Array.isArray(b) || b.length !== 4 || !b.every(v => typeof v === 'number')) return null; if (Math.max(...b) > 1.5) b = b.map(v => v / 1000); b = b.map(v => Math.max(0, Math.min(1, v))); return (b[2] - b[0] > 0.01 && b[3] - b[1] > 0.01) ? b : null; };
  const recorte = (src, box) => new Promise(res => { const b = cajaOk(box); if (!b || !src) return res(null); const im = new Image(); if (!String(src).startsWith('data:')) im.crossOrigin = 'anonymous';
    im.onload = () => { try { const W = im.naturalWidth, H = im.naturalHeight; const cx = (b[0] + b[2]) / 2 * W, cy = (b[1] + b[3]) / 2 * H; let z = Math.max((b[2] - b[0]) * W, (b[3] - b[1]) * H) * 1.35; z = Math.min(Math.max(z, Math.min(W, H) * 0.09), W, H);
        const sx = Math.max(0, Math.min(W - z, cx - z / 2)), sy = Math.max(0, Math.min(H - z, cy - z / 2)); const cv = document.createElement('canvas'); cv.width = cv.height = 480; cv.getContext('2d').drawImage(im, sx, sy, z, z, 0, 0, 480, 480); res(cv.toDataURL('image/jpeg', 0.9)); } catch (e) { res(null); } };
    im.onerror = () => res(null); im.src = src; });
  window.accRecorte = recorte;
  async function portadas(owner) { // los complementos que solo están descritos: se buscan en la ficha del personaje (una lectura) y se les pone de portada su recorte
    const L = list(owner).slice(); const sin = L.filter(c => !(c.thumb || c.cover || c.img)); const p = owner === 'aria' ? null : ((window.PJ && PJ.list) || []).find(q => q.id === owner); const ficha = String(owner === 'aria' ? (C.perfil.ficha || '') : ((p && p.ficha360) || '')).split('?')[0];
    if (!sin.length || !ficha) { toast('No hay ficha del personaje de la que recortar'); return; } toast('Buscando sus complementos en la ficha…');
    let r; try { r = await fetch('/api/acc_cajas', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: { path: ficha }, items: sin.map(c => ({ id: c.id, nombre: c.nombre, desc: c.desc || '' })) }) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
    if (!r || !r.ok) { toast(/WaveSpeed no está conectado|WS_API_KEY/i.test(String(r && r.error)) ? 'Para leer la ficha hace falta tu clave de WaveSpeed' : 'No se ha podido leer la ficha: ' + (r ? r.error : 'sin respuesta')); return; }
    const files = {}; for (const c of sin) { const t = r.cajas && r.cajas[c.id] && await recorte(ficha, r.cajas[c.id]); if (t) files[c.id + '__thumb'] = t; }
    const n = Object.keys(files).length; if (!n) { toast('No los he encontrado en la ficha: puedes ponerles su foto a mano'); return; }
    if (await save(owner, L, files)) { toast(`${n} portada${n > 1 ? 's' : ''} puesta${n > 1 ? 's' : ''} desde su ficha`); renderProfile(); renderSide(); } }
  async function save(owner, L, files) {
    let r; try { r = await fetch('/api/complementos', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ owner, list: L, files: files || {} }) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
    if (!r || !r.ok) { toast('No se pudo guardar: ' + (r ? r.error : 'sin respuesta')); return false; } setList(owner, r.list); return true;
  }
  // ------------------------------------------------ Crear imagen
  const scene = () => { const b = state.comp.biblio; return b ? [b.neutro || b.prompt || '', b.drop ? '' : b.name || ''].join(' ') : ''; };
  const sceneId = () => (state.comp.biblio && state.comp.biblio.id) || 'estudio';
  function overrides() { state.accOn = state.accOn || {}; return state.accOn; }   // lo que se enciende o apaga a mano se queda así al cambiar de imagen (antes se deshacía y, p. ej., volvían los pendientes); se limpia al cambiar de personaje
  function auto(c) { if (c.regla === 'siempre') return true; if (c.regla === 'nunca') return false; const t = tipoOf(c.tipo); const txt = scene(); const ks = (c.claves || []).concat(c.clave ? String(c.clave).split('|') : []).map(k => k.trim()).filter(Boolean); return !!(t.kw && t.kw.test(txt)) || ks.some(k => new RegExp('\\b' + k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'i').test(txt)); }
  const isOn = c => { const o = overrides(); return c.id in o ? o[c.id] : auto(c); };
  window.accActive = () => list().filter(isOn);
  window.accRestore = ids => { state.accOn = {}; if (Array.isArray(ids)) list().forEach(c => { state.accOn[c.id] = ids.includes(c.id); }); };   // «Recrear»: los mismos complementos que llevó esa imagen (si no se guardaron, vuelven a su regla)
  window.accOnFor = owner => list(owner).filter(isOn);   // complementos encendidos de cualquier personaje (para imágenes con varios)
  const asRef = c => !!(c.img && c.modo !== 'prompt'); window.accAsRef = asRef;
  const refTag = (I, c) => { if (!asRef(c)) return ''; const t = I('acc:' + c.id); return /\b0$/.test(t) ? '' : t; }; // si no cupo como referencia (demasiados complementos) va solo descrito
  window.accSig = () => ',acc:' + list().map(c => (isOn(c) ? '1' : '0')).join('');
  window.accIdent = function (I) { // la frase de identidad: su cara + los complementos fijos que están encendidos (gafas, pendientes, collar…)
    const on = list().filter(c => (tipoOf(c.tipo) || {}).ident && isOn(c)).map(c => { const r = refTag(I, c); return c.desc + (r ? ` (exactly as in ${r})` : ''); });
    return [window.CH ? CH().ident : 'same face, green eyes'].concat(on).join(', ');
  };
  window.accParts = function (I) {
    const out = [];
    list().forEach(c => {
      const t = tipoOf(c.tipo); const on = isOn(c); const ref = refTag(I, c);
      if (on && !t.ident) {
        if (c.tipo === 'movil') out.push(`the phone she holds or uses must be EXACTLY the phone of ${ref || 'her own phone'} (${c.desc}): same color, same camera layout and finish; replace any other phone with it`);
        else out.push(`she has ${c.desc}${ref ? ' exactly as in ' + ref : ''}`);
      }
      if (!on && (c.regla === 'nunca' || (c.regla === 'siempre' && t.ident)) && t.no) out.push(`in this image she has NO ${t.no}`);
    });
    return [...new Set(out)]; // dos bolsos en «nunca» no repiten la misma frase
  };
  window.accDropNew = async function (data) { // foto de un objeto soltada sobre «Complementos» en Crear imagen: entra en la lista en «Nunca» y se enciende a mano cuando haga falta
    const owner = window.cfocusId ? cfocusId() : window.CH ? CH().id : 'aria'; toast('Leyendo el objeto…'); let r;
    try { r = await fetch('/api/describir', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: { data } }) }).then(z => z.json()); } catch (e) { r = { error: String(e) }; }
    const ok0 = r && r.ok; const nombre = (ok0 && r.nombre) || 'Complemento nuevo'; const desc = (ok0 && r.desc) || nombre; const id = 'c-' + Date.now().toString(36);
    const tipo = Object.keys(T).find(t => T[t].kw && T[t].kw.test(desc)) || 'otro';
    const done = await save(owner, list(owner).concat([{ id, nombre, tipo, regla: 'nunca', desc }]), { [id]: data }); if (!done) return;
    toast(`«${nombre}» añadido a sus complementos, en «Nunca»: enciéndelo en la lista cuando lo quieras`); state.accOpen = true; renderSide();
  };
  const dropOn = w => { ['dragenter', 'dragover'].forEach(ev => w.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); w.classList.add('over'); })); w.addEventListener('dragleave', () => w.classList.remove('over'));
    w.addEventListener('drop', async e => { e.preventDefault(); e.stopPropagation(); w.classList.remove('over'); const data = window.dropData ? await dropData(e) : null; if (!data) { toast('No he podido leer esa imagen'); return; } accDropNew(data); }); };
  window.accChips = function () { // selector compacto (una línea) que despliega la lista de complementos
    const L = list(window.cfocusId ? cfocusId() : undefined); const o = overrides(); const on = L.filter(isOn);
    const w = el('div', 'accsel' + (state.accOpen ? ' open' : '')); dropOn(w);
    const mini = el('span', 'accmini'); on.slice(0, 5).forEach(c => mini.appendChild((c.thumb || c.img) ? Object.assign(document.createElement('img'), { src: c.thumb || c.img, alt: '' }) : el('span', '', tipoOf(c.tipo).emo)));
    w.appendChild(el('small', '', 'Complementos')); w.appendChild(mini); w.appendChild(el('span', 'cnt', on.length ? `${on.length} de ${L.length}` : 'ninguno seleccionado')); w.appendChild(el('span', 'caret', '▾'));
    const dd = el('div', 'accdd');
    if (!L.length) dd.appendChild(el('div', 'accnone', '<b>Ninguno seleccionado</b><span>Este personaje todavía no tiene complementos.</span>'));
    L.forEach(c => { const t = tipoOf(c.tipo), a = auto(c), is = isOn(c); const why = c.id in o ? 'a mano' : c.regla === 'siempre' ? 'siempre' : c.regla === 'nunca' ? 'nunca' : a ? 'auto' : 'en escena';
      const r = el('div', 'it' + (is ? ' on' : ''), `${(c.thumb || c.img) ? `<img src="${c.thumb || c.img}" alt="">` : `<span class="emo">${t.emo}</span>`}<b>${c.nombre}</b><em class="${c.regla === 'escena' && a && !(c.id in o) ? 'auto' : ''}">${why}</em><span class="ck">✓</span>`);
      r.title = c.regla === 'escena' ? (a ? 'Encendido solo porque la escena lo tiene' : 'Se enciende solo si la escena lo tiene') : ''; r.onclick = e => { e.stopPropagation(); o[c.id] = !is; state.accOpen = true; renderSide(); paint(cur(), true); }; dd.appendChild(r); });
    const irPerfil = e => { e.stopPropagation(); state.accOpen = false; const ow = window.cfocusId ? cfocusId() : window.CH ? CH().id : 'aria'; if (window.PJ) { PJ.sel = ow; PJ.wiz = null; PJ.tabBy = Object.assign(PJ.tabBy || {}, { [ow]: 'complementos' }); } setTab('perfil'); };
    { const nw = el('div', 'it accadd', '<span class="emo">＋</span><b>Añadir nuevo complemento</b>'); nw.title = 'Se crea en su Perfil'; nw.onclick = irPerfil; dd.appendChild(nw); }   // un recuadro más de la lista, como «Crear personaje»
    if (L.length) { const ft = el('div', 'foot'); const ed = el('span', 'lnk', 'Editar complementos en el Perfil'); ed.onclick = irPerfil; ft.appendChild(ed); dd.appendChild(ft); } w.appendChild(dd);
    const place = () => { if (!w.isConnected) return; const r = w.getBoundingClientRect(); const h = Math.min(460, innerHeight - 24); Object.assign(dd.style, { left: Math.round(r.right + 12) + 'px', top: Math.round(Math.max(12, Math.min(r.top - 8, innerHeight - h - 12))) + 'px', maxHeight: h + 'px' }); }; // sale a la derecha, encima del panel de la imagen
    w.onclick = e => { if (e.target.closest('.accdd')) return; state.accOpen = !state.accOpen; w.classList.toggle('open', state.accOpen); if (state.accOpen) place(); };
    if (state.accOpen) setTimeout(place, 0); { const sc = w.closest('aside') || document.querySelector('aside'); if (sc && !sc._accpl) { sc._accpl = true; sc.addEventListener('scroll', () => { const o = document.querySelector('.accsel.open'); if (o) { state.accOpen = false; o.classList.remove('open'); } }, { passive: true }); } }
    setTimeout(() => { const close = e => { if (!w.isConnected) { document.removeEventListener('click', close, true); return; } if (!w.contains(e.target)) { state.accOpen = false; w.classList.remove('open'); } }; document.addEventListener('click', close, true); }, 0);
    return w;
  };
  // ------------------------------------------------ Perfil: la sección de complementos del personaje
  window.accPanel = function (owner = 'aria') {
    const box = el('div', 'pjgrp accpanel'); const L = list(owner).slice(); const PK = window.accPick;
    if (PK) { // modo «elegir»: se marcan uno o varios y «Añadir» vuelve al paso a paso
      const bar = el('div', 'accpickbar'); const bk = el('button', 'btn backbtn', '← Volver sin elegir'); bk.onclick = () => { window.accPick = null; PK.cancel && PK.cancel(); }; bar.appendChild(bk);
      const ad = el('button', 'btn acc', PK.sel.length ? `＋ Añadir a ${PK.label} (${PK.sel.length})` : `＋ Añadir a ${PK.label}`); ad.disabled = !PK.sel.length; ad.onclick = () => { const ids = PK.sel.slice(); window.accPick = null; PK.done(ids); }; bar.appendChild(ad);
      bar.appendChild(el('small', 'pjnote', 'Marca los complementos que quieras y pulsa «Añadir».')); box.appendChild(bar);
      const g = el('div', 'acccards pick'); L.forEach(c => { const t = tipoOf(c.tipo); const fijo = c.regla === 'siempre'; const on = PK.sel.includes(c.id); const d = el('div', 'acccard' + (on ? ' picked' : '') + (fijo ? ' fijo' : ''));
        const pic = c.thumb || c.cover || c.img; d.appendChild(el('div', 'accimg', pic ? `<img src="${pic}" alt="">` : `<span>${t.emo}</span>`)); const inf = el('div', 'accinf'); inf.appendChild(el('b', '', c.nombre)); inf.appendChild(el('small', '', fijo ? 'ya lo lleva siempre' : `${t.es} · ${asRef(c) ? '📷 con su imagen' : '✍️ descrito'}`)); d.appendChild(inf); if (on) d.appendChild(el('i', 'accck', '✓'));
        if (!fijo) d.onclick = () => { PK.sel = on ? PK.sel.filter(z => z !== c.id) : PK.sel.concat([c.id]); renderProfile(); }; g.appendChild(d); });
      box.appendChild(g); return box;
    }
    const hd = el('div', 'acchead left'); hd.appendChild(el('div', '', `<b>Complementos</b><small>Lo que lleva siempre y sus objetos propios. En Crear imagen se ponen solos. Arrastra una tarjeta a otro grupo para cambiar cuándo sale.</small>`));
    const add = el('button', 'btn acc', '＋ Añadir complemento'); add.onclick = () => openEditor(owner, null);
    const srcs = [['aria', (C.perfil && C.perfil.name) || 'Aria', C.perfil && C.perfil.avatar]].concat(((window.PJ && PJ.list) || []).map(q => [q.id, q.nombre, q.avatar])).filter(([id]) => id !== owner && list(id).length);
    if (owner !== 'aria' && srcs.length) { const bb = el('div', 'accheadbtns'); bb.appendChild(add); const im = el('button', 'btn pinkline', '⇩ Importar de otro personaje'); im.onclick = () => importar(owner, srcs); bb.appendChild(im); hd.appendChild(bb); } else hd.appendChild(add);
    { const nSin = L.filter(c => !(c.thumb || c.cover || c.img)).length; const fijaA = owner === 'aria' && typeof WEBM === 'function' && WEBM(); if (nSin && !fijaA) { const pb = el('button', 'btn pinkline', `🖼 Portadas desde su ficha (${nSin})`); pb.title = 'Busca en su ficha los complementos que solo están descritos y les pone de portada su recorte. Usa una lectura de foto.'; pb.onclick = () => { pb.disabled = true; pb.textContent = 'Buscando…'; portadas(owner).finally(() => { if (pb.isConnected) renderProfile(); }); }; (hd.querySelector('.accheadbtns') || hd).appendChild(pb); } }
    box.appendChild(hd);
    Object.values(PEND).filter(E => E.owner === owner && (E.job || E.nuevas.length) && E.idx == null).forEach(E => { const d = el('div', 'accpend', `${E.job ? '<span class="spin"></span>' : '🧩'}<b>${E.job ? 'Generando la ficha de producto de' : 'Ficha de producto lista, sin guardar:'} «${esc(E.c.nombre || 'complemento nuevo')}»</b><button class="btn">Abrir</button>`); d.querySelector('button').onclick = () => openEditor(owner, null); box.appendChild(d); });
    REGLAS.forEach(([rk, rn]) => {
      const idx = L.map((c, i) => [c, i]).filter(([c]) => c.regla === rk); const grid = el('div', 'acccards'); grid.dataset.regla = rk;
      const grp = el('div', 'accgrp r-' + rk); grp.appendChild(el('div', 'accsub', `${rn}<small>${rk === 'siempre' ? 'en todas sus fotos' : rk === 'escena' ? 'solo cuando la escena lo tiene' : 'no lo lleva nunca'}</small>`));
      grid.ondragover = e => { e.preventDefault(); grid.classList.add('over'); }; grid.ondragleave = () => grid.classList.remove('over');
      grid.ondrop = async e => { e.preventDefault(); grid.classList.remove('over'); const i = +e.dataTransfer.getData('text/acc'); if (isNaN(i) || !L[i] || L[i].regla === rk) return; const N = L.slice(); N[i] = Object.assign({}, L[i], { regla: rk }); if (await save(owner, N)) { toast(`«${L[i].nombre}» → ${rn}`); renderProfile(); } };

      idx.forEach(([c, i]) => {
        const t = tipoOf(c.tipo); const d = el('div', 'acccard'); d.draggable = true; d.ondragstart = e => { e.dataTransfer.setData('text/acc', String(i)); d.classList.add('drag'); }; d.ondragend = () => d.classList.remove('drag');
        const pic = c.thumb || c.cover || c.img; const busy = PEND[owner + ':' + c.id] && PEND[owner + ':' + c.id].job; d.appendChild(el('div', 'accimg' + (busy ? ' busy' : ''), (pic ? `<img src="${pic}" alt="">` : `<span>${t.emo}</span>`) + (busy ? '<i class="spin"></i>' : '')));
        const inf = el('div', 'accinf'); inf.appendChild(el('b', '', c.nombre)); inf.appendChild(el('small', '', asRef(c) ? '📷 su foto como referencia' : '✍️ descrito en el prompt')); d.appendChild(inf);
        d.onclick = () => openEditor(owner, i); d.title = `${c.nombre} · ${t.es}${c.desc ? ' · ' + c.desc : ''}\nClic para editar · arrastra para cambiar de grupo`;
        grid.appendChild(d);
      });
      { const at = el('button', 'accaddtile', `<span>＋</span><b>Añadir nuevo</b><small>${rn.toLowerCase()}</small>`); at.title = `Complemento nuevo en «${rn}»`; at.onclick = () => openEditor(owner, null, rk); grid.appendChild(at); } // cuadrado de añadir en cada grupo, con su regla ya elegida
      grp.appendChild(grid); box.appendChild(grp);   // cada grupo, en su recuadro de color
    });
    return box;
  };
  // ------------------------------------------------ importar complementos de otro personaje (se eligen haciendo clic y se copian)
  function importar(owner, srcs) {
    let from = srcs.length === 1 ? srcs[0][0] : null; const sel = new Set(); let m0 = $('#accimp'); if (m0) m0.remove(); m0 = el('div', 'fxm'); m0.id = 'accimp'; document.body.appendChild(m0); m0.onclick = e => { if (e.target === m0) m0.remove(); };
    const paint = () => { m0.innerHTML = ''; const b = el('div', 'accimpbox'); const x = el('button', 'galx', '×'); x.onclick = () => m0.remove(); b.appendChild(x);
      b.appendChild(el('div', 'fxtitle', `<small>Complementos</small><b>Importar de otro personaje</b><p>${from ? 'Pulsa los que quieras copiar (se ponen en rosa) y pulsa «Importar».' : '¿De quién?'}</p>`));
      if (!from) { const r = el('div', 'accimpsrc'); srcs.forEach(([id, n, av]) => { const c = el('button', 'pjc', `<span class="pjav">${av ? `<img src="${av}" alt="">` : `<i>${(n || '?')[0]}</i>`}</span><small>${esc(n)} · ${list(id).length}</small>`); c.onclick = () => { from = id; paint(); }; r.appendChild(c); }); b.appendChild(r); }
      else { if (srcs.length > 1) { const bk = el('button', 'lnk', '← Elegir otro personaje'); bk.onclick = () => { from = null; sel.clear(); paint(); }; b.appendChild(bk); }
        const ya = new Set(list(owner).map(c => c.nombre.toLowerCase())); const g = el('div', 'acccards pick');
        list(from).forEach(c => { const t = tipoOf(c.tipo); const had = ya.has((c.nombre || '').toLowerCase()); const on = sel.has(c.id); const d = el('div', 'acccard' + (on ? ' picked' : '') + (had ? ' fijo' : ''));
          const pic = c.thumb || c.cover || c.img; d.appendChild(el('div', 'accimg', pic ? `<img src="${pic}" alt="">` : `<span>${t.emo}</span>`)); const inf = el('div', 'accinf'); inf.appendChild(el('b', '', esc(c.nombre))); inf.appendChild(el('small', '', had ? 'ya lo tiene' : `${t.es} · ${REGLAS.find(r => r[0] === c.regla)[1].toLowerCase()}`)); d.appendChild(inf); if (on) d.appendChild(el('i', 'accck', '✓'));
          if (!had) d.onclick = () => { if (on) sel.delete(c.id); else sel.add(c.id); paint(); }; g.appendChild(d); });
        b.appendChild(g);
        const a = el('div', 'fxacts'); const go = el('button', 'btn acc', sel.size ? `⇩ Importar ${sel.size === 1 ? '1 complemento' : sel.size + ' complementos'}` : '⇩ Importar'); go.disabled = !sel.size;
        go.onclick = async () => { const ids = new Set(list(owner).map(c => c.id)); const add = list(from).filter(c => sel.has(c.id)).map(c => { const q = JSON.parse(JSON.stringify(c)); let id = q.id, k = 2; while (ids.has(id)) id = q.id + '-' + k++; ids.add(id); q.id = id; return q; });
          if (await save(owner, list(owner).concat(add))) { m0.remove(); toast(add.length === 1 ? `«${add[0].nombre}» importado` : `${add.length} complementos importados`); renderProfile(); } };
        a.appendChild(go); b.appendChild(a); }
      m0.appendChild(b); };
    paint();
  }
  // ------------------------------------------------ ficha de un complemento (editar o crear)
  const PROD = { movil: 'the camera module, lenses, flash, buttons and the frame edges', gafas: 'the frame, lenses, bridge and temples', gafassol: 'the frame, tinted lenses, bridge and temples', pendientes: 'the metal finish, clasp and exact size', collar: 'the chain, pendant and clasp', reloj: 'the dial, hands, case, crown and strap', bolso: 'the handles or strap, hardware, closure, stitching and logo', gorra: 'the crown, brim, stitching and logo' };
  const prodPrompt = c => `Create a professional PRODUCT REFERENCE SHEET of the exact product in @Image1 (${c.nombre}${c.desc ? ': ' + c.desc : ''}). One single image with a clean 2x2 grid on a plain light-gray studio background: top-left front view, top-right back view, bottom-left side view, bottom-right three-quarter view. Keep EXACTLY the same design, shape, proportions, colors, materials, finish and every detail of @Image1 (${PROD[c.tipo] || 'every visible detail'}); do not invent or change anything; the sides not visible in @Image1 must stay consistent with its real design. Soft even studio light, photoreal product photography, sharp focus, no hands, no people, no text, no labels.`;
  // cualquier foto (AVIF, HEIC que el navegador sepa abrir, PNG enorme…) → JPEG de 2000 px como mucho
  const toJpeg = src => new Promise((res, rej) => { const im = new Image(); im.onload = () => { const k = Math.min(1, 2000 / Math.max(im.naturalWidth, im.naturalHeight)); const cv = document.createElement('canvas'); cv.width = Math.round(im.naturalWidth * k); cv.height = Math.round(im.naturalHeight * k); const g = cv.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, cv.width, cv.height); g.drawImage(im, 0, 0, cv.width, cv.height); res(cv.toDataURL('image/jpeg', 0.92)); }; im.onerror = () => rej(new Error('formato de imagen no compatible')); im.src = src; });
  const readFile = file => new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = () => rej(r.error); r.readAsDataURL(file); });
  const XSVG = '<svg viewBox="0 0 10 10" width="8" height="8" aria-hidden="true"><path d="M1.5 1.5l7 7M8.5 1.5l-7 7" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>';
  // editores abiertos con una ficha de producto en marcha o sin guardar: si cierras la ventana no se pierde, al volver a abrir sigue ahí
  const PEND = {};
  function openEditor(owner, idx, regla) {
    const L = list(owner).slice(); const key = owner + ':' + (idx == null ? '' : L[idx].id);
    let E = PEND[key]; if (E && idx == null && regla && !E.job && !E.nuevas.length) { delete PEND[key]; E = null; }
    if (!E) {
      const c0 = idx == null ? { id: '', nombre: '', tipo: 'otro', regla: regla || 'escena', desc: '', modo: 'prompt', claves: [] } : Object.assign({ modo: L[idx].img ? 'foto' : 'prompt', claves: [] }, L[idx], { claves: (L[idx].claves || []).concat(L[idx].clave ? String(L[idx].clave).split('|').filter(Boolean) : []) });
      const foto0 = c0.foto || c0.cover || (c0.img && c0.img !== c0.fichaProd ? c0.img : '') || '';
      const fichas0 = (c0.fichas && c0.fichas.length ? c0.fichas : (c0.fichaProd ? [c0.fichaProd] : [])).slice();
      const asKey = v => (!v || (foto0 && v.split('?')[0] === foto0.split('?')[0])) ? '__foto__' : v;
      const cover0 = c0.portada === 'prod' ? (c0.fichaProd || '__foto__') : (!c0.portada || c0.portada === 'foto') ? '__foto__' : asKey(c0.portada);
      E = { c0, c: JSON.parse(JSON.stringify(c0)), foto: null, crop: c0.crop ? Object.assign({}, c0.crop) : null, nuevoTipo: false, fichas: fichas0, nuevas: [], job: null, desc: false, ref: asKey(c0.img), cover: cover0, view: cover0 };
    }
    Object.assign(E, { owner, idx, key, open: true });
    let m0 = $('#accm'); if (m0) m0.remove(); m0 = el('div', 'fxm'); m0.id = 'accm'; document.body.appendChild(m0);
    const forget = () => { if (!E.job && !E.nuevas.length) delete PEND[key]; else PEND[key] = E; };
    const close = () => { E.open = false; m0.remove(); clearInterval(E.tick); forget(); if (E.job) toast('La ficha del producto sigue generándose: al volver a abrir el complemento la verás'); renderProfile(); };
    m0.onclick = e => { if (e.target === m0) close(); };
    const fotoSrc = () => E.foto || E.c.foto || E.c.cover || (E.c.img && E.c.img !== E.c.fichaProd && !(E.c.fichas || []).includes(E.c.img) ? E.c.img : '') || E.c.thumbSrc || '';
    const srcOf = k => k === '__foto__' ? fotoSrc() : k;
    const coleccion = () => [['__foto__', 'Foto original']].concat(E.fichas.concat(E.nuevas).map((f, i) => [f, 'Ficha ' + (i + 1)])).filter(([k]) => srcOf(k));
    async function describe() {
      const src = fotoSrc(); if (!src || E.desc) return; E.desc = true; paint(); let r;
      try { r = await fetch('/api/describir', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: E.foto ? { data: E.foto } : { path: src.split('?')[0] }, nombre: E.c.nombre, tipo: E.c.tipo === 'otro' ? '' : tipoOf(E.c.tipo).es }) }).then(z => z.json()); } catch (e) { r = { error: String(e) }; }
      E.desc = false;
      if (r && r.ok) { E.c.desc = r.desc; if (!(E.c.nombre || '').trim() && r.nombre) { E.c.nombre = r.nombre; E.nameErr = false; } toast(r.nombre && E.c.nombre === r.nombre ? 'Nombre y descripción escritos a partir de la foto: revísalos' : 'Descripción escrita a partir de la foto: revísala'); }
      else toast('No se pudo leer la foto: ' + (r ? r.error : 'sin respuesta'));
      if (E.open) paint();
    }
    async function usePhoto(du) { // foto nueva (botón o arrastrada): se pasa a JPEG, se enseña y se lee sola (nombre y descripción si faltan)
      let jpg; try { jpg = await toJpeg(du); } catch (e) { toast('No se pudo abrir esa imagen: prueba con JPG o PNG'); return; }
      const nueva = !!fotoSrc() && !!(E.fichas.length || E.nuevas.length);
      Object.assign(E, { foto: jpg, crop: null, cropTouched: true, cover: '__foto__', view: '__foto__' }); delete E.c.thumbSrc;
      if (nueva && confirm('Foto nueva: ¿quitar de la colección las fichas de producto de la foto anterior?')) { E.fichas = []; E.nuevas = []; E.ref = '__foto__'; }
      paint(); if (!(E.c.desc || '').trim() || !(E.c.nombre || '').trim()) describe();
    }
    async function genProd() {
      const c = E.c; const src = fotoSrc(); if (!src || E.job) return; const m = MODELS.find(z => z.key === 'seedream') || curModel(); const usd = m.usd[state.quality];
      if (!confirm(`¿Generar ${E.fichas.length + E.nuevas.length ? 'otra ficha' : 'la ficha'} de producto de «${c.nombre || 'este objeto'}» con ${m.name}? (${fmtUsd(usd)})`)) return;
      E.job = { sending: true, t0: performance.now(), m }; paint(); const pt = prodPrompt(c);
      let r; try { r = await fetch('/api/generar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ item: 'ficha_producto_' + (c.id || 'nuevo'), prompt: pt, images: [E.foto ? { data: E.foto } : { path: src.split('?')[0] }], aspect: '1:1', quality: state.quality, model: m.key, meta: { name: 'Ficha de producto · ' + (c.nombre || 'complemento'), tab: 'perfil', personaje: '_complementos', hidden: true, model: m.name, ep: m.ep, prompt: pt } }) }).then(z => z.json()); } catch (e) { r = { error: String(e) }; }
      if (!r || r.error) { E.job = null; forget(); toast('No se pudo generar: ' + (r ? r.error : 'sin respuesta')); if (E.open) paint(); return; }
      const job = { rid: r.request_id, it: { id: 'prod:' + (c.id || 'nuevo'), name: 'Ficha de producto · ' + (c.nombre || 'complemento') }, tab: 'perfil', m, kind: 'image', accProd: E, t0: E.job.t0, status: 'queued', usd: r.usd != null ? Number(r.usd) : usd };
      E.job = job; PEND[key] = E; JOBS.set(job.rid, job); ensurePoller(); if (E.open) paint();
    }
    const loadImg = src => new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = rej; im.src = src; });
    async function makeThumb() { const src = srcOf(E.cover); if (!src) return null; const im = await loadImg(src); const cr = E.crop || { z: 1, x: 0.5, y: 0.5 }; const S = 480, cv = document.createElement('canvas'); cv.width = cv.height = S; const nw = im.naturalWidth, nh = im.naturalHeight, side = Math.min(nw, nh) / cr.z; cv.getContext('2d').drawImage(im, cr.x * nw - side / 2, cr.y * nh - side / 2, side, side, 0, 0, S, S); return cv.toDataURL('image/jpeg', 0.9); }
    async function guardar() {
      const c = E.c; if (!(c.nombre || '').trim()) { E.nameErr = true; paint(); const n = $('#accm .accname'); if (n) { n.scrollIntoView({ block: 'center' }); n.focus(); } toast('Falta el nombre del complemento'); return; }
      if (!(c.desc || '').trim()) c.desc = c.nombre.trim();
      if (c.modo === 'foto' && !fotoSrc() && !E.fichas.length && !E.nuevas.length) { toast('Para usar su foto como referencia, sube una foto'); return; }
      if (!c.id) c.id = c.nombre.trim().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
      delete c.clave; delete c.portada; const files = {}; if (E.foto) files[c.id] = E.foto;
      if (E.cropTouched || E.coverTouched) { try { const t = await makeThumb(); if (t) files[c.id + '__thumb'] = t; } catch (e) {} }
      if (E.crop) c.crop = Object.assign({}, E.crop); c.fichas = E.fichas.slice();
      const N = idx == null ? L.filter(z => z.id !== c.id).concat([c]) : L.map((z, k) => k === idx ? c : z);
      const body = { owner, list: N, files, copy: { [c.id]: E.nuevas.slice() }, sel: { [c.id]: { ref: E.ref, cover: E.cover } } };
      E.saving = true; paint(); let r; try { r = await fetch('/api/complementos', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(z => z.json()); } catch (e) { r = { error: String(e) }; }
      E.saving = false; if (!r || !r.ok) { toast('No se pudo guardar: ' + (r ? r.error : 'sin respuesta')); paint(); return; }
      setList(owner, r.list); delete PEND[key]; E.nuevas = []; toast(`«${c.nombre}» guardado`); E.open = false; m0.remove(); clearInterval(E.tick);
      if (E.job) { const i2 = r.list.findIndex(z => z.id === c.id); const c2 = r.list[i2] || c; PEND[owner + ':' + c.id] = E; Object.assign(E, { key: owner + ':' + c.id, idx: i2, c: JSON.parse(JSON.stringify(c2)), c0: c2, foto: null, fichas: (c2.fichas || []).slice() }); }
      renderProfile(); if (state.tab === 'crear') renderSide();
    }
    E.repaint = () => { if (E.open) paint(); };
    clearInterval(E.tick); E.tick = setInterval(() => { if (!E.open) { clearInterval(E.tick); return; } document.querySelectorAll('#accm [data-t0]').forEach(n => { n.textContent = Math.round((performance.now() - +n.dataset.t0) / 1000) + ' s'; }); }, 1000);
    function paint() {
      const keepTop = ($('#accm .accside') || {}).scrollTop || 0; // al cambiar de modo el menú no salta arriba
      m0.innerHTML = ''; const c = E.c; const t = tipoOf(c.tipo); const box = el('div', 'fxbox accbox');
      const fs = fotoSrc(); const col = coleccion(); if (!col.some(([k]) => k === E.view)) E.view = col.length ? col[0][0] : '__foto__'; if (!col.some(([k]) => k === E.cover)) E.cover = col.length ? col[0][0] : '__foto__'; if (!col.some(([k]) => k === E.ref)) E.ref = col.length ? col[col.length - 1][0] : '__foto__';
      const src = srcOf(E.view); const isCover = E.view === E.cover;
      // ---------- izquierda: colección (foto original + fichas de producto) con portada y referencia
      const media = el('div', 'fxmedia accmedia');
      if (col.length > 1 && !E.job) {
        const rows = el('div', 'accroles');
        const row = (label, sub, role) => { const r = el('div', 'accrole'); r.appendChild(el('div', 'accroleh', `<b>${label}</b><small>${sub}</small>`)); const tl = el('div', 'acctiles');
          col.forEach(([k, n]) => { const on = E[role] === k; const b = el('button', 'acctile' + (on ? ' on' : '') + (E.view === k ? ' view' : ''), `<img src="${srcOf(k)}" alt=""><span>${n}</span>${on ? '<i>✓</i>' : ''}`); b.title = role === 'cover' ? 'Usar como portada (la miniatura de la tarjeta)' : 'Usar como referencia al generar';
            b.onclick = () => { if (role === 'cover' && E.cover !== k) { E.cover = k; E.crop = { z: 1, x: 0.5, y: 0.5 }; E.coverTouched = true; } if (role === 'ref') E.ref = k; E.view = k; paint(); };
            if (k !== '__foto__') { const x = el('button', 'acctx', XSVG); x.title = 'Quitar esta ficha de la colección'; x.onclick = e => { e.stopPropagation(); if (!confirm(`¿Quitar «${n}» de la colección de este complemento?`)) return; E.fichas = E.fichas.filter(z => z !== k); E.nuevas = E.nuevas.filter(z => z !== k); paint(); }; b.appendChild(x); }
            tl.appendChild(b); });
          r.appendChild(tl); rows.appendChild(r); };
        row('Portada', 'la que se ve en su tarjeta', 'cover');
        if (c.modo === 'foto') row('Referencia al generar', 'la que se envía a la IA', 'ref');
        media.appendChild(rows);
      }
      if (src && isCover) {
        const vp = el('div', 'accvp'); const im = document.createElement('img'); im.src = src; im.draggable = false; vp.appendChild(im); vp.appendChild(el('div', 'accvpfr')); media.appendChild(vp);
        E.crop = E.crop || { z: 1, x: 0.5, y: 0.5 }; const cr = E.crop;
        const place = () => { const W = vp.clientWidth, nw = im.naturalWidth, nh = im.naturalHeight; if (!nw) return; const sc = W / Math.min(nw, nh) * cr.z; im.style.width = nw * sc + 'px'; im.style.height = nh * sc + 'px'; im.style.left = (W / 2 - cr.x * nw * sc) + 'px'; im.style.top = (W / 2 - cr.y * nh * sc) + 'px'; };
        im.onload = place; if (im.complete) setTimeout(place, 0);
        let drag = null; vp.onmousedown = e => { if (E.job) return; drag = { x: e.clientX, y: e.clientY, cx: cr.x, cy: cr.y }; e.preventDefault(); };
        window.onmousemove = e => { if (!drag) return; const sc = vp.clientWidth / Math.min(im.naturalWidth, im.naturalHeight) * cr.z; cr.x = Math.min(1, Math.max(0, drag.cx - (e.clientX - drag.x) / (im.naturalWidth * sc))); cr.y = Math.min(1, Math.max(0, drag.cy - (e.clientY - drag.y) / (im.naturalHeight * sc))); E.cropTouched = true; place(); };
        window.onmouseup = () => { drag = null; };
        const zr = document.createElement('input'); zr.type = 'range'; zr.min = 1; zr.max = 8; zr.step = 0.05; zr.value = cr.z; zr.className = 'acczoom'; zr.oninput = () => { cr.z = +zr.value; E.cropTouched = true; place(); };
        vp.onwheel = e => { if (E.job) return; e.preventDefault(); cr.z = Math.min(8, Math.max(1, cr.z * (e.deltaY < 0 ? 1.08 : 0.93))); zr.value = cr.z; E.cropTouched = true; place(); };
        const tools = el('div', 'acctools'); tools.appendChild(el('small', '', 'Portada: arrastra para encuadrar · rueda o barra para acercar')); tools.appendChild(zr); media.appendChild(tools);
      } else if (src) { const vw = el('div', 'accview'); vw.appendChild(Object.assign(document.createElement('img'), { src, alt: '' })); vw.onclick = () => lightbox(src, c.nombre || 'Complemento'); media.appendChild(vw); media.appendChild(el('small', 'accpickh', E.view === E.ref && c.modo === 'foto' ? 'Esta es la que se envía al generar' : 'Pulsa arriba para usarla como portada o como referencia')); }
      else media.appendChild(el('div', 'accnoimg', `<span>${t.emo}</span><b>Arrastra aquí una foto del objeto</b><small>o súbela con el botón · se lee sola y escribe su nombre y su descripción</small>`));
      const up = el('label', 'btn', fs ? '🖼 Cambiar la foto' : '🖼 Subir una foto'); const f = document.createElement('input'); f.type = 'file'; f.accept = 'image/*'; f.hidden = true; up.appendChild(f);
      f.onchange = async () => { const file = f.files[0]; if (file) usePhoto(await readFile(file)); }; if (!E.job) media.appendChild(up);
      // arrastrar una foto (del ordenador o de una web) a la zona negra
      media.appendChild(el('div', 'accdrop', '<b>Suelta la foto aquí</b><small>se lee sola</small>'));
      let dn = 0; media.ondragenter = e => { if (E.job) return; e.preventDefault(); dn++; media.classList.add('accover'); }; media.ondragover = e => { if (E.job) return; e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; };
      media.ondragleave = () => { dn = Math.max(0, dn - 1); if (!dn) media.classList.remove('accover'); };
      media.ondrop = async e => { e.preventDefault(); dn = 0; media.classList.remove('accover'); if (E.job) return; const dt = e.dataTransfer; const file = dt.files && [...dt.files].find(x => x.type.startsWith('image/') || /\.(heic|heif|avif)$/i.test(x.name));
        if (file) return usePhoto(await readFile(file));
        let url = dt.getData('text/uri-list') || dt.getData('text/plain') || ''; const mm = (dt.getData('text/html') || '').match(/<img[^>]+src=["']([^"']+)["']/i); if (mm) url = mm[1]; if (/^data:image\//.test(url)) return usePhoto(url); if (!/^https?:\/\//i.test(url)) return;
        toast('Descargando la imagen…'); try { const j = await fetch('/api/fetch?url=' + encodeURIComponent(url)).then(r => r.json()); if (j.error) throw new Error(j.error); usePhoto(j.data); } catch (err) { toast('No se pudo descargar: guárdala y arrástrala desde el ordenador'); } };
      // generando la ficha del producto: la zona de la izquierda entera en difuminado, como al generar una imagen
      if (E.job) { const g = el('div', 'accgen', `${fs ? `<img src="${fs}" alt="">` : ''}<div class="accgenc"><div class="bar"><i></i></div><b>${E.job.sending ? 'Enviando' : 'Generando'}</b><span>Ficha del producto · ${esc(c.nombre || 'complemento')}</span><small>${esc((E.job.m || {}).name || '')} · <i data-t0="${E.job.t0}">${Math.round((performance.now() - E.job.t0) / 1000)} s</i></small><em>Puedes cerrar esta ventana: al volver la verás aquí</em></div>`); media.appendChild(g); }
      box.appendChild(media);
      // ---------- derecha: botones arriba del todo y sus datos
      const side = el('div', 'fxside accside'); const x = el('button', 'galx', '×'); x.title = 'Cerrar sin guardar'; x.onclick = close; box.appendChild(x);
      const acts = el('div', 'fxacts accacts top'); const sv = el('button', 'btn acc', E.saving ? '⏳ Guardando…' : '✓ Guardar'); sv.disabled = !!(E.saving || (E.job && E.job.sending)); sv.onclick = guardar;
      const cn = el('button', 'btn', 'Cancelar'); cn.onclick = () => { if (!E.job) { delete PEND[key]; E.nuevas = []; } close(); }; acts.appendChild(sv); acts.appendChild(cn);
      if (idx != null) { const del = el('button', 'btn accdel', '🗑 Eliminar'); del.onclick = async () => { if (!confirm(`¿Eliminar «${E.c0.nombre}» de sus complementos?`)) return; if (await save(owner, L.filter((_, k) => k !== idx))) { delete PEND[key]; E.open = false; m0.remove(); clearInterval(E.tick); renderProfile(); } }; acts.appendChild(del); }
      side.appendChild(acts);
      const tt = el('div', 'fxtitle', `<small>${idx == null ? 'Complemento nuevo' : 'Ficha del complemento'}</small>`); side.appendChild(tt);   // el título ES el nombre: se cambia escribiendo encima
      const fld = (label, node, sub) => { const g = el('div', 'fxsec'); const h = el('h4', '', label + (sub ? `<small>${sub}</small>` : '')); g.appendChild(h); g.appendChild(node); side.appendChild(g); return g; };
      const nm = el('input', 'acctit' + (E.nameErr ? ' err' : '')); nm.value = c.nombre; nm.title = 'Clic para cambiar el nombre'; nm.placeholder = E.desc ? 'Leyendo la foto…' : 'Ponle un nombre'; nm.oninput = () => { c.nombre = nm.value; if (E.nameErr && nm.value.trim()) { E.nameErr = false; nm.classList.remove('err'); } }; tt.appendChild(nm); if (E.nameErr) tt.appendChild(el('small', 'accerr', 'Ponle un nombre para poder guardarlo'));
      // tipo (con tipos propios)
      const tw = el('div', 'stack'); { const sl = el('select', 'sel'); Object.entries(tipos()).filter(([k]) => k !== 'otro').forEach(([k, tt2]) => { const o = document.createElement('option'); o.value = k; o.textContent = `${tt2.emo} ${tt2.es}`; sl.appendChild(o); });
        [['otro', '🏷 Otro'], ['__nuevo', '＋ Crear un tipo nuevo…']].forEach(([k, n]) => { const o = document.createElement('option'); o.value = k; o.textContent = n; sl.appendChild(o); }); sl.value = E.nuevoTipo ? '__nuevo' : (tipos()[c.tipo] ? c.tipo : 'otro');
        sl.onchange = () => { if (sl.value === '__nuevo') E.nuevoTipo = true; else { c.tipo = sl.value; E.nuevoTipo = false; } paint(); }; tw.appendChild(sl); }
      if (E.nuevoTipo) { const row = el('div', 'accnew'); const ti = el('input', 'pjin'); ti.placeholder = 'Nombre del tipo nuevo · ej.: Pulsera'; const ce = el('button', 'btn acc', 'Crear'); const crear = async () => { const n = ti.value.trim(); if (!n) return; const id = 'x-' + n.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-'); const TT = (C.perfil.accTipos || []).filter(z => z.id !== id).concat([{ id, es: n, emo: '🏷' }]); const r = await fetch('/api/complementos', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ owner: 'aria', tipos: TT }) }).then(z => z.json()).catch(() => null); if (r && r.ok) { C.perfil.accTipos = TT; c.tipo = id; E.nuevoTipo = false; toast(`Tipo «${n}» creado`); paint(); } else toast('No se pudo crear el tipo'); }; ce.onclick = crear; ti.onkeydown = e => { if (e.key === 'Enter') crear(); }; row.appendChild(ti); row.appendChild(ce); tw.appendChild(row); setTimeout(() => ti.focus(), 0); }
      fld('Tipo', tw);
      { const rg = el('select', 'sel'); REGLAS.forEach(([k, n]) => { const o = document.createElement('option'); o.value = k; o.textContent = n + (k === 'siempre' ? ' · en todas sus fotos' : k === 'escena' ? ' · solo cuando la escena lo tiene' : ' · no lo lleva'); rg.appendChild(o); }); rg.value = c.regla; rg.onchange = () => { c.regla = rg.value; paint(); }; fld('Cuándo sale', rg); }
      if (c.regla === 'escena') { const kw = el('div', 'stack'); const chips = el('div', 'accreg acckws'); (c.claves || []).forEach((k, i) => { const ch = el('span', 'acckw', `<span>${esc(k)}</span><button title="Quitar">${XSVG}</button>`); ch.querySelector('button').onclick = () => { c.claves.splice(i, 1); paint(); }; chips.appendChild(ch); }); if (c.claves && c.claves.length) kw.appendChild(chips);
        const row = el('div', 'accnew'); const ki = el('input', 'pjin acckwin'); ki.placeholder = 'Ej.: selfie'; const ka = el('button', 'btn', 'Añadir'); const addK = () => { const v = ki.value.trim(); if (!v) return; c.claves = (c.claves || []).filter(z => z.toLowerCase() !== v.toLowerCase()).concat([v]); paint(); setTimeout(() => { const n = $('#accm .acckwin'); if (n) n.focus(); }, 0); }; ka.onclick = addK; ki.onkeydown = e => { if (e.key === 'Enter') addK(); }; row.appendChild(ki); row.appendChild(ka); kw.appendChild(row);
        fld('Palabras que lo activan', kw, 'si la escena las nombra, se enciende solo (además de las de su tipo)'); }
      const md = el('div', 'accmodo'); [['prompt', '✍️ Descrito en el prompt', 'Se nombra con su descripción. No gasta referencias.'], ['foto', '📷 Su foto como referencia', 'Se envía la imagen que elijas arriba a la izquierda (la foto o una ficha de producto). Gasta un hueco de referencias; si no caben, va descrito.']].forEach(([k, n, d]) => { const b = el('button', 'accm' + (c.modo === k ? ' on' : ''), `<b>${n}</b><small>${d}</small>`); b.onclick = () => { c.modo = k; paint(); }; md.appendChild(b); }); fld('Cómo se usa al generar', md);
      // descripción: siempre se guarda (también con «su foto»: es la de reserva si no caben las referencias)
      const descNode = () => { const dw = el('div', 'stack'); const ds = el('textarea', 'pjin'); ds.value = c.desc; ds.rows = 4; ds.placeholder = E.desc ? 'Leyendo la foto…' : 'Ej.: thin round silver metal-frame glasses with clear lenses'; ds.oninput = () => { c.desc = ds.value; }; dw.appendChild(ds);
        const ag = el('button', 'btn accauto', E.desc ? '⏳ Leyendo la foto…' : '✨ Generar automáticamente'); ag.disabled = E.desc || !fs; ag.title = fs ? 'Lee la foto y escribe la descripción (céntimos)' : 'Sube primero una foto'; ag.onclick = describe; const r = el('div', 'accautorow'); r.appendChild(ag); dw.appendChild(r); return dw; };
      if (c.modo !== 'foto') fld('Descripción para el prompt', descNode(), 'en inglés: forma, material, color y tamaño');
      else {
        // ficha de producto: varias vistas del objeto a partir de la foto; se guardan todas y eliges cuál se envía
        const pw = el('div', 'stack'); const m = MODELS.find(z => z.key === 'seedream') || curModel(); const nF = E.fichas.length + E.nuevas.length;
        pw.appendChild(el('small', 'pjnote', E.job ? 'Se está generando: la verás a la izquierda en cuanto termine.' : nF ? `Tienes ${nF === 1 ? 'una ficha' : nF + ' fichas'} en su colección. Arriba a la izquierda eliges la portada y la que se envía al generar. Las que no te gusten se quitan con su ×.` : 'Genera sus vistas (frente, espalda, lado y tres cuartos) a partir de la foto. Se enviará esa ficha en vez de la foto.'));
        const gb = el('button', 'btn pr' + (nF ? '' : ' acc'), E.job ? `⏳ Generando la ficha… <i data-t0="${E.job.t0}">${Math.round((performance.now() - E.job.t0) / 1000)} s</i>` : `${nF ? '↻ Generar otra ficha' : '🧩 Generar la ficha del producto'}<i>${fmtUsd(m.usd[state.quality])}</i>`); gb.disabled = !!E.job || !fs; gb.onclick = genProd;
        pw.appendChild(gb); fld('Ficha del producto', pw, 'vistas del objeto para que la IA no se invente los lados');
        const det = el('details', 'accdescdet'); det.open = !!E.descOpen; det.ontoggle = () => { E.descOpen = det.open; }; det.appendChild(el('summary', '', `<b>Descripción de reserva</b><small>${c.desc ? esc(c.desc) : 'sin escribir'}</small>`)); det.appendChild(el('p', 'pjnote', 'Se guarda también: si en una creación hay tantas referencias que su imagen no cabe, se nombra con esta descripción.')); det.appendChild(descNode()); side.appendChild(det);
      }
      box.appendChild(side); m0.appendChild(box); side.scrollTop = keepTop;
    }
    paint();
  }
  const _fin3 = window.finishJob, _fail3 = window.failJob;
  window.finishJob = function (job, st) { if (!job.accProd) return _fin3(job, st); job.end = true; const E = job.accProd; const usd = st.usd != null ? Number(st.usd) : (job.usd || 0); state.nGen++; state.spent += usd; meter();
    E.job = null; E.nuevas.push(st.file); E.ref = st.file; E.view = st.file; PEND[E.key] = E;
    if (E.open) { toast('Ficha del producto lista: ya es la que se envía al generar (puedes cambiarla arriba) · ' + fmtUsd(usd)); E.repaint(); } else { toast(`Ficha del producto de «${E.c.nombre || 'complemento nuevo'}» lista: abre el complemento para verla · ${fmtUsd(usd)}`); if (state.tab === 'perfil') renderProfile(); } };
  window.failJob = function (job, msg) { if (!job.accProd) return _fail3(job, msg); job.end = true; const E = job.accProd; E.job = null; if (!E.nuevas.length) delete PEND[E.key]; toast('No se pudo generar la ficha del producto: ' + msg); if (E.open) E.repaint(); else if (state.tab === 'perfil') renderProfile(); };
})();
