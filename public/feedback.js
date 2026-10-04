// ARIA STUDIO · SECCIONES EN DESARROLLO + FEEDBACK (v119)
// Una función en desarrollo sale como «Próximamente · En desarrollo» con el enlace rosa «Ver igualmente».
// Al entrar se avisa de que está en desarrollo y aparece el botón flotante 💬 Feedback (escribir o dictar con el micro).
// Cada comentario va a la base «💬 Feedback de ARIA STUDIO» de Notion (ARIA STUDIO — HQ) a través del puente.
(function () {
  const VERSION = 'v188';
  // ---------------------------------------------------------------- tarjeta «en desarrollo»
  window.devGate = function (card, label, onEnter) { // card = el botón/tarjeta de la función; onEnter = lo que hacía al pulsarlo
    card.classList.add('devsoon'); card.onclick = e => { e.preventDefault(); toast('Esta sección está en desarrollo: pulsa «Ver igualmente» para entrar'); };
    const tag = el('div', 'devtags', '<em>Próximamente</em><small>En desarrollo</small>'); const go = el('button', 'devgo', 'Ver igualmente');
    go.onclick = e => { e.stopPropagation(); devIntro(label, onEnter); }; tag.appendChild(go); card.appendChild(tag); return card;
  };
  window.devIntro = devIntro; // v123: también para botones del menú (🥊 Duelos)
  function devIntro(label, onEnter) {
    let m0 = document.getElementById('devm'); if (m0) m0.remove(); m0 = el('div', 'fxm'); m0.id = 'devm'; document.body.appendChild(m0); m0.onclick = e => { if (e.target === m0) m0.remove(); };
    const b = el('div', 'devbox', `<div class="devemo">🛠</div><h3>Esta sección está en desarrollo</h3><p class="devlab">${esc(label)}</p><p>Puedes usarla, pero todavía se está construyendo. Se agradece <b>un montón</b> cualquier comentario para mejorarla: si algo falla, si echas algo en falta o si se te ocurre una idea, dímelo con el botón <b>💬 Feedback</b> de abajo a la derecha, escribiendo o con el micrófono.</p>`);
    const a = el('div', 'pjacts'); const g = el('button', 'btn acc big', 'Entrar'); g.onclick = () => { m0.remove(); onEnter(); }; const n = el('button', 'btn', 'Ahora no'); n.onclick = () => m0.remove(); a.appendChild(g); a.appendChild(n); b.appendChild(a); m0.appendChild(b);
  }
  // ---------------------------------------------------------------- botón flotante de feedback (v188: SIEMPRE a la vista, en toda la app)
  // Un círculo rosa abajo a la derecha. Al pulsarlo se despliega el panel desde ahí. La app añade sola dónde está la persona, con qué personaje y modelo,
  // qué acaba de generar y si hay algún error a la vista. Se puede escribir, dictar (si el navegador deja) o grabar una nota de voz, que se guarda para transcribirla después.
  let SECCION = null; const F = { open: false, tipo: '💬 Comentario', voz: false, texto: '', rec: null, oyendo: false, enviando: false, audio: null, seg: 0, mr: null, sinSR: false };
  window.feedbackSection = function (name) { SECCION = name || null; paint(); };
  window.fbContext = null; // cada módulo puede dejar aquí una función que devuelve más contexto
  const donde = () => SECCION || ((TABS[state.tab] || {}).label || state.tab);
  function contexto() { const extra = typeof window.fbContext === 'function' ? window.fbContext() : ''; const t = k => { try { return k(); } catch (e) { return ''; } };
    const ult = t(() => { const c = TABS.creaciones.items.find(i => !i.pending && i.src); return c ? 'última creación ' + c.src.split('/').pop().split('?')[0] + (c.meta && c.meta.model ? ' (' + c.meta.model + ')' : '') : ''; });
    return [`pestaña ${state.tab}`, SECCION && `sección ${SECCION}`, extra, t(() => 'personaje ' + CH().name), t(() => typeof extraChars === 'function' && extraChars().length ? 'con ' + extraChars().map(c => c.name).join(', ') : ''),
      t(() => LIVE ? 'modelo ' + curModel().name + ' · ' + state.quality + ' · ' + state.aspect : 'sin API conectada'), t(() => state.tab === 'crear' ? 'creación: ' + (compNames() || 'nada añadido') : ''), t(() => { const it = cur(); return it ? 'elemento ' + (it.name || it.id) : ''; }),
      t(() => { const it = cur(); return it && it._err ? 'ERROR a la vista: ' + String(it._err).slice(0, 200) : ''; }), t(() => { const n = [...JOBS.values()].filter(j => !j.end).length; return n ? n + ' generándose' : ''; }), ult,
      t(() => window.CUENTA && CUENTA.web ? 'web' + (typeof CASA !== 'undefined' && CASA ? ' · saldo regalo' : '') : 'app local'), `pantalla ${innerWidth}×${innerHeight}`, t(() => 'escala ' + (window.ESCALA || 1)), `navegador ${navigator.userAgent.replace(/^Mozilla\/5\.0 /, '').slice(0, 90)}`].filter(Boolean).join(' · '); }
  function paint() {
    let w = document.getElementById('fbw'); if (!w) { w = el('div', ''); w.id = 'fbw'; document.body.appendChild(w); } w.innerHTML = '';
    if (F.open) {
      const p = el('div', 'fbpanel'); p.appendChild(el('div', 'fbhd', `<b>💬 Cuéntanos</b><small>estás en ${esc(donde())} · eso ya lo sabemos, no hace falta que lo expliques</small>`)); const x = el('button', 'fbx', '×'); x.title = 'Cerrar'; x.onclick = () => { F.open = false; stopMic(); paint(); }; p.appendChild(x);
      const tp = el('div', 'fbtipos'); ['🐞 Algo falla', '🧩 Falta algo', '💡 Idea', '💬 Comentario'].forEach(t => { const b = el('button', F.tipo === t ? 'on' : '', t); b.onclick = () => { F.tipo = t; paint(); }; tp.appendChild(b); }); p.appendChild(tp);
      const ta = el('textarea', 'pjin fbta'); ta.rows = 5; ta.placeholder = F.oyendo ? 'Te escucho… habla con normalidad' : 'Qué ha fallado, qué echas en falta o qué mejorarías. También puedes pulsar el micro y hablar.'; ta.value = F.texto; ta.oninput = () => { F.texto = ta.value; const s = document.querySelector('#fbw .fbrow .btn.acc'); if (s) s.disabled = !puedeEnviar(); }; p.appendChild(ta);
      if (F.audio) { const an = el('div', 'fbaudio', `🎙 Nota de voz · ${F.seg} s`); const q = el('button', 'fbx2', '×'); q.title = 'Quitar la nota de voz'; q.onclick = () => { F.audio = null; F.seg = 0; paint(); }; an.appendChild(q); p.appendChild(an); }
      const row = el('div', 'fbrow'); const SR = !F.sinSR && (window.SpeechRecognition || window.webkitSpeechRecognition); const MR = window.MediaRecorder && navigator.mediaDevices && navigator.mediaDevices.getUserMedia;
      if (SR || MR) { const mic = el('button', 'fbmic' + (F.oyendo ? ' on' : ''), F.oyendo ? `⏹ Parar${F.mr ? ' · <i class="fbseg">' + F.seg + ' s</i>' : ''}` : (SR ? '🎙 Hablar' : '🎙 Grabar nota de voz')); mic.title = F.oyendo ? 'Parar' : SR ? 'Dictar el comentario con el micrófono' : 'Grabar una nota de voz (hasta 90 segundos)'; mic.onclick = () => F.oyendo ? stopMic() : (SR ? startMic() : startRec()); row.appendChild(mic); }
      else row.appendChild(el('small', 'fbnomic', 'Este navegador no deja usar el micro: escríbelo'));
      const send = el('button', 'btn acc', F.enviando ? 'Enviando…' : 'Enviar'); send.disabled = F.enviando || !puedeEnviar(); send.onclick = enviar; row.appendChild(send); p.appendChild(row);
      w.appendChild(p); setTimeout(() => { const t = w.querySelector('.fbta'); if (t && !F.oyendo) { t.focus(); t.setSelectionRange(t.value.length, t.value.length); } }, 0);
    }
    const btn = el('button', 'fbbtn' + (F.open ? ' on' : ''), F.open ? '×' : '💬'); btn.type = 'button'; btn.title = 'Feedback: cuéntanos qué falla, qué falta o qué mejorarías'; btn.setAttribute('aria-label', 'Feedback'); btn.onclick = () => { F.open = !F.open; if (!F.open) stopMic(); paint(); }; w.appendChild(btn);
  }
  const puedeEnviar = () => !!(F.texto.trim() || F.audio);
  function startMic() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition; if (!SR) return startRec(); stopMic();
    const r = new SR(); r.lang = 'es-ES'; r.continuous = true; r.interimResults = true; const base = F.texto ? F.texto.replace(/\s*$/, ' ') : '';
    r.onresult = e => { let fin = '', tmp = ''; for (let i = 0; i < e.results.length; i++) { const t = e.results[i][0].transcript; if (e.results[i].isFinal) fin += t; else tmp += t; } F.texto = (base + fin + tmp).replace(/\s+/g, ' ').trimStart(); F.voz = true; const ta = document.querySelector('#fbw .fbta'); if (ta) ta.value = F.texto; const s = document.querySelector('#fbw .fbrow .btn.acc'); if (s) s.disabled = !puedeEnviar(); };
    r.onerror = e => { if (e.error === 'not-allowed') toast('Da permiso al micrófono para dictar'); else if (e.error !== 'no-speech' && e.error !== 'aborted') { F.sinSR = true; toast('Aquí no se puede dictar: pulsa otra vez y graba una nota de voz'); } stopMic(); };
    r.onend = () => { if (F.oyendo && !F.mr) { F.oyendo = false; F.rec = null; paint(); } };
    try { r.start(); F.rec = r; F.oyendo = true; paint(); } catch (e) { F.sinSR = true; startRec(); }
  }
  async function startRec() { // nota de voz: se graba y se manda tal cual (se transcribe después)
    stopMic(); let st; try { st = await navigator.mediaDevices.getUserMedia({ audio: true }); } catch (e) { toast('Da permiso al micrófono para grabar'); return; }
    const tipo = ['audio/mp4', 'audio/webm;codecs=opus', 'audio/webm', 'audio/ogg'].find(t => { try { return MediaRecorder.isTypeSupported(t); } catch (e) { return false; } }) || '';
    let mr; try { mr = new MediaRecorder(st, tipo ? { mimeType: tipo, audioBitsPerSecond: 32000 } : undefined); } catch (e) { st.getTracks().forEach(t => t.stop()); toast('No se pudo grabar'); return; }
    const trozos = []; const t0 = Date.now(); mr.ondataavailable = e => { if (e.data && e.data.size) trozos.push(e.data); };
    mr.onstop = () => { clearInterval(F.tick); st.getTracks().forEach(t => t.stop()); const seg = Math.round((Date.now() - t0) / 1000); F.mr = null; F.oyendo = false; if (!trozos.length || seg < 1) { paint(); return; }
      const rd = new FileReader(); rd.onload = () => { F.audio = String(rd.result).replace(/^data:[^;,]*/, 'data:' + ((mr.mimeType || tipo || 'audio/webm').split(';')[0])); F.seg = seg; F.voz = true; paint(); }; rd.readAsDataURL(new Blob(trozos, { type: mr.mimeType || tipo || 'audio/webm' })); };
    mr.start(); F.mr = mr; F.oyendo = true; F.seg = 0; clearInterval(F.tick); F.tick = setInterval(() => { F.seg = Math.round((Date.now() - t0) / 1000); const n = document.querySelector('#fbw .fbseg'); if (n) n.textContent = F.seg + ' s'; if (F.seg >= 90) stopMic(); }, 500); paint();
  }
  function stopMic() { if (F.mr) { try { F.mr.stop(); } catch (e) {} return; } if (F.rec) { try { F.rec.stop(); } catch (e) {} } F.rec = null; if (F.oyendo) { F.oyendo = false; if (document.getElementById('fbw')) paint(); } }
  async function enviar() {
    if (F.mr) { stopMic(); await new Promise(r => setTimeout(r, 400)); } else stopMic(); const texto = F.texto.trim(); if (!texto && !F.audio) return; F.enviando = true; paint(); let r;
    try { r = await fetch('/api/feedback', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ texto, audio: F.audio || undefined, tipo: F.tipo, via: F.audio ? '🎙️ Nota de voz' : F.voz ? '🎙️ Voz' : '⌨️ Escrito', seccion: donde(), contexto: contexto() }) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
    F.enviando = false; if (r && r.ok) { Object.assign(F, { texto: '', voz: false, tipo: '💬 Comentario', open: false, audio: null, seg: 0 }); toast(r.local ? '¡Gracias! Guardado ' : '¡Gracias! Tu comentario ha llegado'); } else toast('No se pudo enviar: ' + (r ? r.error : 'sin respuesta'));
    paint();
  }
  const arranca = () => { if (typeof state !== 'undefined' && document.body) paint(); else setTimeout(arranca, 400); }; setTimeout(arranca, 800);
})();
