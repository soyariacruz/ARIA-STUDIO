/* PRUEBA DE HUMO de ARIA STUDIO (v200). No genera nada ni gasta saldo.
   Se pega en la consola de la página ya arrancada (local :8767, o la web de pruebas :3000 con una cuenta local) y devuelve la lista de fallos.
   Recorre todas las pestañas y las combinaciones típicas de Crear imagen llamando a lo mismo que pinta la app; lo que reviente, sale aquí
   y no delante de un usuario. Antes de publicar tiene que devolver `fallos: []`. */
(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms)); const fallos = []; const hecho = [];
  const paso = (n, f) => { try { const r = f(); hecho.push(n); return r; } catch (e) { fallos.push(n + ' → ' + String((e && e.stack) || e).split('\n').slice(0, 2).join(' | ').slice(0, 260)); } };
  const pinta = n => { paso(n + ' · rejilla', () => renderRail()); paso(n + ' · panel', () => renderSide()); paso(n + ' · imagen', () => paint(cur(), true)); paso(n + ' · filtros', () => renderChips()); };
  const guard = { tab: state.tab, comp: state.comp, compBy: state.compBy, extras: (state.extras || []).slice(), ch: CH().id, nsfw: state.nsfw, k: state.k };
  state.nsfw = false;
  // 1) todas las pestañas, con su lista y con la lista vacía (como al recargar antes de que llegue)
  for (const t of Object.keys(TABS)) { paso('abrir ' + t, () => setTab(t)); await w(120); pinta(t); const L = TABS[t].items; TABS[t].items = []; pinta(t + ' vacía'); TABS[t].items = L; (t === 'creaciones' || t === 'video') ? buildCreations && paso('reconstruir creaciones', () => buildCreations()) : 0; }
  // 2) Crear imagen: combinaciones
  paso('abrir crear', () => setTab('crear')); await w(150);
  const B = TABS.biblio.items.find(x => !x.group && !x.double), V = TABS.vestidor.items.find(x => !x.group && !x.pending), H = TABS.hair.items.find(x => !x.group), E = TABS.expr.items.find(x => !x.group);
  const lug = TABS.lugar && TABS.lugar.items[0];
  const plan = n => paso(n + ' · prompt', () => { const p = livePlan('crear', cur()); if (!p || !p.prompt || /undefined|\[object|NaN/.test(p.prompt)) throw new Error('prompt raro: ' + String(p && p.prompt).slice(0, 120)); crearRefs(); compSig(); compNames(); return p; });
  const chars = charList().filter(c => c.ok).map(c => c.id);
  for (const ch of chars.slice(0, 3)) {
    paso('personaje ' + ch, () => { state.extras = []; saveExtras(); setChar(ch, true); });
    for (const [n, comp] of [['vacío', {}], ['prenda+peinado+expresión', { vestidor: V, hair: H, expr: E }], ['Fototeca', { biblio: B }], ['Fototeca + prenda', { biblio: B, vestidor: V }], ['lugar', lug ? { lugar: lug } : null], ['Fototeca + lugar', lug ? { biblio: B, lugar: lug } : null]]) {
      if (!comp) continue; state.comp = Object.assign({}, comp); state.compBy = {};
      for (const modo of (comp.biblio ? ['prompt', 'swap'] : [null])) { if (comp.biblio) B.modo = modo; pinta(ch + ' · ' + n + (modo ? ' · ' + modo : '')); plan(ch + ' · ' + n + (modo ? ' · ' + modo : '')); }
      delete B.modo; }
    if (chars.length > 1) { const otro = chars.find(c => c !== ch); paso('añadir ' + otro, () => { state.comp = { biblio: B }; state.extras = [otro]; saveExtras(); }); for (const modo of ['prompt', 'swap']) { B.modo = modo; pinta(ch + '+' + otro + ' · ' + modo); plan(ch + '+' + otro + ' · ' + modo); } delete B.modo; paso('quitar principal', () => removeMain()); pinta('tras quitar al principal'); }
  }
  // 3) foto arrastrada y popups
  paso('foto arrastrada', () => { state.extras = []; saveExtras(); state.comp = { biblio: { id: 'drop-prueba', name: 'prueba', image: 'data:image/png;base64,iVBORw0KGgo=', thumb: '', drop: true, modo: 'swap' } }; }); pinta('foto arrastrada · misma foto'); plan('foto arrastrada · misma foto');
  const cr = TABS.creaciones.items.find(x => !x.pending && x.kind !== 'video' && x.meta);
  if (cr) { paso('popup de una creación', () => openGal(cr)); await w(250); paso('cerrar popup', () => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))); paso('recrear', () => recrear(cr)); await w(250); pinta('tras recrear'); plan('tras recrear'); }
  paso('imagen encogida', () => { setK(1); setK(0); });
  // 4) editor de ficha (v198): abre, pasa por todas sus piezas y cierra
  const hecha = ((window.PJ && PJ.list) || []).find(p => p.ficha360 && p.cuerpo);
  if (hecha && window.pjEdFicha) { paso('editor de ficha · abrir', () => { pjEdFicha(hecha.id, 'frente'); if (!document.getElementById('edf')) throw new Error('no se abre'); }); for (let i = 0; i < 7; i++) paso('editor de ficha · pieza ' + i, () => pjEdMueve(1)); paso('editor de ficha · cerrar', () => { pjEdCierra(); if (document.getElementById('edf')) throw new Error('no se cierra'); }); }
  // 5) Comunidad (v199): la página, sus tres apartados, la ficha de un personaje, y que se cierre al ir a otra sección
  if (window.comAbre) { try { COM.visto = true; await comAbre('dir'); if (!document.getElementById('compage') || !COM.D) throw new Error('la página no se pinta'); hecho.push('comunidad · abrir');
      for (const v of ['sol', 'msg', 'dir']) { COM.vista = v; COM.arg = null; COM.M = []; comPinta(); hecho.push('comunidad · ' + v); }
      const cc = COM.D.cuentas.find(x => x.personajes.length); if (cc) { COM.pz = { cid: cc.cid, pid: cc.personajes[0].pid }; comPinta(); if (!document.querySelector('#compage .cpdrawer')) throw new Error('no sale la ficha del personaje'); COM.pz = null; hecho.push('comunidad · ficha'); }
      comNombre(); if (!document.querySelector('#compide input')) throw new Error('la ventana del nombre de creador sale sin su campo'); document.getElementById('compide').remove(); hecho.push('comunidad · nombre');
      if (cc) { comPide(cc, cc.personajes[0]); if (!document.querySelector('#compide textarea') || !document.querySelector('#compide button')) throw new Error('la ventana de pedir colaboración sale incompleta'); document.getElementById('compide').remove(); hecho.push('comunidad · pedir'); }
      for (const v of ['dir', 'sol', 'msg']) { COM.vista = v; comPinta(); if (/[\w.+-]+@[\w-]+\.[a-z]{2,}/i.test(document.getElementById('compage').innerText)) throw new Error('aparece algo con forma de correo en ' + v); } COM.vista = 'dir'; hecho.push('comunidad · sin correos');
      setTab(guard.tab); if (COM.on || document.getElementById('compage')) throw new Error('no se cierra al cambiar de sección'); hecho.push('comunidad · cerrar');
    } catch (e) { fallos.push('comunidad → ' + String((e && e.stack) || e).split('\n').slice(0, 2).join(' | ').slice(0, 260)); if (window.comCierra) comCierra(true); } }
  // dejarlo como estaba
  paso('restaurar', () => { state.comp = guard.comp; state.compBy = guard.compBy; state.extras = guard.extras; saveExtras(); state.nsfw = guard.nsfw; setChar(guard.ch, true); setTab(guard.tab); });
  return { fallos, pasos: hecho.length, cuenta: window.CUENTA && CUENTA.web ? (WEBM() ? 'web · miembro' : 'web · dueño') : 'local', escala: window.ESCALA, ventana: innerWidth + '×' + innerHeight };
})()
