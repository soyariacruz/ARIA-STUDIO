// ARIA STUDIO · SECCIONES EN DESARROLLO + FEEDBACK (v119)
// Una función en desarrollo sale como «Próximamente · En desarrollo» con el enlace rosa «Ver igualmente».
// Al entrar se avisa de que está en desarrollo y aparece el botón flotante 💬 Feedback (escribir o dictar con el micro).
// Cada comentario va a la base «💬 Feedback de ARIA STUDIO» de Notion (ARIA STUDIO — HQ) a través del puente.
(function () {
  const VERSION = 'v119';
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
  // ---------------------------------------------------------------- botón flotante de feedback
  let SECCION = null; const F = { open: false, tipo: '💬 Comentario', voz: false, texto: '', rec: null, oyendo: false, enviando: false };
  window.feedbackSection = function (name) { SECCION = name || null; paint(); };
  window.fbContext = null; // cada módulo puede dejar aquí una función que devuelve más contexto
  function contexto() { const extra = typeof window.fbContext === 'function' ? window.fbContext() : ''; return [`versión ${VERSION}`, `pestaña ${state.tab}`, SECCION && `sección ${SECCION}`, extra, `pantalla ${innerWidth}×${innerHeight}`, `navegador ${navigator.userAgent.replace(/^Mozilla\/5\.0 /, '').slice(0, 90)}`].filter(Boolean).join(' · '); }
  function paint() {
    let w = document.getElementById('fbw'); if (!SECCION) { if (w) w.remove(); stopMic(); F.open = false; return; }
    if (!w) { w = el('div', ''); w.id = 'fbw'; document.body.appendChild(w); } w.innerHTML = '';
    if (F.open) {
      const p = el('div', 'fbpanel'); p.appendChild(el('div', 'fbhd', `<b>💬 Tu comentario</b><small>sobre ${esc(SECCION)}</small>`)); const x = el('button', 'fbx', '×'); x.title = 'Cerrar'; x.onclick = () => { F.open = false; stopMic(); paint(); }; p.appendChild(x);
      const tp = el('div', 'fbtipos'); ['🐞 Algo falla', '🧩 Falta algo', '💡 Idea', '💬 Comentario'].forEach(t => { const b = el('button', F.tipo === t ? 'on' : '', t); b.onclick = () => { F.tipo = t; paint(); }; tp.appendChild(b); }); p.appendChild(tp);
      const ta = el('textarea', 'pjin fbta'); ta.rows = 5; ta.placeholder = F.oyendo ? 'Te escucho… habla con normalidad' : 'Cuéntame qué falla, qué falta o qué mejorarías. También puedes pulsar el micro y hablar.'; ta.value = F.texto; ta.oninput = () => { F.texto = ta.value; }; p.appendChild(ta);
      const row = el('div', 'fbrow'); const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SR) { const mic = el('button', 'fbmic' + (F.oyendo ? ' on' : ''), F.oyendo ? '⏹ Parar' : '🎙 Hablar'); mic.title = F.oyendo ? 'Dejar de escuchar' : 'Dictar el comentario con el micrófono'; mic.onclick = () => F.oyendo ? stopMic() : startMic(); row.appendChild(mic); }
      else row.appendChild(el('small', 'fbnomic', 'Este navegador no deja dictar: escríbelo'));
      const send = el('button', 'btn acc', F.enviando ? 'Enviando…' : 'Enviar'); send.disabled = F.enviando || !F.texto.trim(); send.onclick = enviar; row.appendChild(send); p.appendChild(row);
      w.appendChild(p); setTimeout(() => { const t = w.querySelector('.fbta'); if (t && !F.oyendo) { t.focus(); t.setSelectionRange(t.value.length, t.value.length); } }, 0);
    }
    const btn = el('button', 'fbbtn' + (F.open ? ' on' : ''), '💬 Feedback'); btn.title = 'Esta sección está en desarrollo: cuéntame qué falla o qué falta'; btn.onclick = () => { F.open = !F.open; if (!F.open) stopMic(); paint(); }; w.appendChild(btn);
  }
  function startMic() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition; if (!SR) return; stopMic();
    const r = new SR(); r.lang = 'es-ES'; r.continuous = true; r.interimResults = true; const base = F.texto ? F.texto.replace(/\s*$/, ' ') : '';
    r.onresult = e => { let fin = '', tmp = ''; for (let i = 0; i < e.results.length; i++) { const t = e.results[i][0].transcript; if (e.results[i].isFinal) fin += t; else tmp += t; } F.texto = (base + fin + tmp).replace(/\s+/g, ' ').trimStart(); F.voz = true; const ta = document.querySelector('#fbw .fbta'); if (ta) ta.value = F.texto; const s = document.querySelector('#fbw .fbrow .btn.acc'); if (s) s.disabled = !F.texto.trim(); };
    r.onerror = e => { if (e.error === 'not-allowed') toast('Da permiso al micrófono para dictar'); stopMic(); };
    r.onend = () => { if (F.oyendo) { F.oyendo = false; F.rec = null; paint(); } };
    try { r.start(); F.rec = r; F.oyendo = true; paint(); } catch (e) { toast('No se pudo usar el micrófono'); }
  }
  function stopMic() { if (F.rec) { try { F.rec.stop(); } catch (e) {} } F.rec = null; if (F.oyendo) { F.oyendo = false; if (document.getElementById('fbw')) paint(); } }
  async function enviar() {
    stopMic(); const texto = F.texto.trim(); if (!texto) return; F.enviando = true; paint(); let r;
    try { r = await fetch('/api/feedback', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ texto, tipo: F.tipo, via: F.voz ? '🎙️ Voz' : '⌨️ Escrito', seccion: SECCION, contexto: contexto() }) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
    F.enviando = false; if (r && r.ok) { Object.assign(F, { texto: '', voz: false, tipo: '💬 Comentario', open: false }); toast(r.local ? '¡Gracias! Guardado ' : '¡Gracias! Tu comentario ha llegado'); } else toast('No se pudo enviar: ' + (r ? r.error : 'sin respuesta'));
    paint();
  }
})();
