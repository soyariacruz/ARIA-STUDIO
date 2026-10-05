/* ARIA STUDIO · tu cuenta (v134).
   Solo actúa en la versión web: el puerto 3000 en desarrollo (aria-studio-web/web_dev.py) o cualquier dominio que no sea este ordenador.
   Sin sesión se ve la portada con «Entrar con Google». Con sesión comprueba que tu correo está en la lista de miembros, baja el catálogo
   (privado, de Supabase) y solo entonces carga la app; arriba a la derecha queda tu perfil con «Cerrar sesión».
   En local (el puente, :8767) no hace nada: ahí no hay cuentas y la app se carga con sus etiquetas de siempre. */
(function () {
  const LOCAL = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
  const WEB = !LOCAL || location.port === '3000';
  const CU = window.CUENTA = { web: WEB, user: null, sb: null, interno: false, ariaMia: false };
  if (!WEB) return;

  // Las dos son públicas por diseño (van en el navegador). Lo que protege los datos son las reglas de Supabase.
  const SB_URL = 'https://uhscbgidrloskdjbevkn.supabase.co';
  const SB_KEY = 'sb_publishable_GSO5Vqhr7Dg93egtKk_I2w_E_uScoNG';
  const DUENOS = ['mix1994max@gmail.com'];   // la cuenta de Max: para ella Aria Cruz es SU personaje (va primero y se puede editar). Para las demás, Aria es un personaje fijo
  const APP = ['app.js', 'feedback.js', 'personajes.js', 'complementos.js', 'fichas.js', 'fichas360.js'];   // en este orden, después del catálogo
  const root = document.documentElement;
  try { if (localStorage.getItem('am_theme') !== 'light') root.classList.add('dark'); } catch (e) { root.classList.add('dark'); }
  root.classList.add('gate');   // hasta que la app esté cargada con tu sesión, no se ve

  const css = document.createElement('style');
  css.textContent = `
html.gate body>*:not(#gate){visibility:hidden!important}
#gate{position:fixed;inset:0;z-index:99999;background:var(--bg);display:none;align-items:center;justify-content:center;padding:16px;overflow:auto}
html.gate #gate{display:flex}
#gate .gwrap{display:flex;align-items:center;justify-content:center;gap:44px;width:100%;max-width:1040px}
#gate .gfotos{display:none;gap:14px;align-items:center;flex:1;min-width:0;justify-content:flex-end}
#gate.entrar .gfotos{display:flex}
#gate .gfotos img{width:30%;max-width:200px;aspect-ratio:3/4;object-fit:cover;border-radius:20px;box-shadow:0 0 0 4px #fff,0 0 0 5px #cfa966,0 22px 50px rgba(0,0,0,.35);background:var(--panel)}
#gate .gfotos img:nth-child(2){transform:translateY(-26px) scale(1.06)}
#gate .gpts{display:none;list-style:none;margin:0;padding:0;text-align:left;flex-direction:column;gap:12px}
#gate.entrar .gpts{display:flex}
#gate .gpts li{font-size:13px;line-height:1.45;color:var(--mut);padding-left:26px;position:relative}
#gate .gpts li::before{content:'✓';position:absolute;left:0;top:0;width:18px;height:18px;border-radius:50%;background:var(--acc);color:#fff;font-size:11px;font-weight:800;line-height:18px;text-align:center}
#gate .gpts b{display:block;color:var(--ink);font-size:14px}
#gate .gnota{font-size:11.5px;color:var(--mut);opacity:.8}
@media (max-width:900px){#gate .gfotos{display:none!important}}
#gate .gcard{width:100%;max-width:400px;flex:none;background:var(--panel);border:1px solid var(--line);border-radius:24px;padding:44px 34px 36px;text-align:center;display:flex;flex-direction:column;gap:20px;box-shadow:0 24px 60px rgba(0,0,0,.18)}
#gate h1{font-family:var(--serif);font-weight:500;font-size:32px;letter-spacing:.06em;color:var(--ink)}
#gate h1 i{font-style:normal;color:var(--acc);margin-left:.3em}
#gate p{color:var(--mut);font-size:14px;line-height:1.55}
#gate.entrar #gateMsg{white-space:nowrap;font-size:13.5px}
#gate .gnota a{color:inherit;text-decoration:underline;text-underline-offset:2px}
#gate .gnota a:hover{color:var(--acc)}
#gate button{font-family:inherit;font-size:15px;font-weight:700;border-radius:999px;padding:14px 20px;cursor:pointer;border:1px solid var(--line);background:var(--bg);color:var(--ink);transition:transform .1s,filter .15s}
#gate .gin{border-color:var(--acc);background:var(--acc);color:#fff}
#gate button:hover{filter:brightness(1.07)}
#gate button:active{transform:scale(.98)}
#gate button:disabled{opacity:.55;cursor:default}
#gate .gerr{color:#e0566a;font-size:13px}
#gate [hidden]{display:none!important}
#console,#btnConsole{display:none!important}
#fbw{bottom:22px!important}
.vercomo{bottom:32px!important}
html.sinapi #livedot,html.sinapi .meter{display:none!important}
.webnote{font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut);border:1px solid var(--line);border-radius:999px;padding:6px 10px;white-space:nowrap}
.cuentabtn{width:30px;height:30px;border-radius:50%;border:1px solid var(--line);background:var(--panel);color:var(--ink);cursor:pointer;padding:0;overflow:hidden;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;flex:none}
.cuentabtn:hover,.cuentabtn.on{border-color:var(--acc);box-shadow:0 0 0 2px rgba(232,68,127,.25)}
.cuentabtn img,.cuentamenu .cav img{width:100%;height:100%;object-fit:cover;display:block}
.cuentamenu{position:fixed;z-index:9000;min-width:240px;max-width:300px;background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:0 18px 44px rgba(0,0,0,.28);display:flex;flex-direction:column;align-items:center;gap:6px;text-align:center}
.cuentamenu .cav{width:56px;height:56px;border-radius:50%;overflow:hidden;border:2px solid var(--acc);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:20px;margin-bottom:6px}
.cuentamenu b{font-size:14px}
.cuentamenu small{font-size:12px;color:var(--mut);word-break:break-all}
.cuentamenu button{margin-top:12px;width:100%;font-family:inherit;font-size:13px;font-weight:700;border-radius:10px;padding:10px 12px;cursor:pointer;border:1px solid var(--line);background:var(--bg);color:var(--ink)}
.cuentamenu button:hover{border-color:var(--acc);color:var(--acc)}
`;
  document.head.appendChild(css);

  const gate = document.createElement('div');
  gate.id = 'gate';
  gate.innerHTML = '<div class="gwrap"><div class="gfotos"><img src="/assets/biblio/p269-5.jpg" alt=""><img src="/assets/biblio/p269-6.jpg" alt=""><img src="/assets/biblio/p269-8.jpg" alt=""></div>' +
    '<div class="gcard"><h1>ARIA<i>STUDIO</i></h1>' +
    '<p id="gateMsg"></p>' +
    '<ul class="gpts"><li><b>Tu personaje, siempre el mismo</b>Crea su ficha una vez y sale igual en todas sus fotos.</li><li><b>Recrea cualquier foto con él</b>Elige una de la Fototeca o arrastra la tuya.</li><li><b>Empiezas con saldo regalo</b>Tus primeras imágenes van por nuestra cuenta. Después, desde 3 céntimos por imagen y sin suscripción.</li></ul>' +
    '<button class="gin" id="gateIn" hidden>Entrar con Google</button>' +
    '<button id="gateOut" hidden>Cerrar sesión</button>' +
    '<p class="gerr" id="gateErr" hidden></p><p class="gnota" id="gateNota" hidden>Acceso por invitación · <a href="https://www.skool.com/influencer-ai/about" target="_blank" rel="noopener">comunidad de Aria Cruz</a></p></div></div>';
  document.body.prepend(gate);
  const G = (id) => gate.querySelector('#' + id);
  // La portada tiene cuatro caras: esperando, entrar, abriendo el estudio y «sin acceso».
  function cara(msg, o = {}) {
    G('gateMsg').textContent = msg || ''; G('gateMsg').hidden = !msg;
    G('gateIn').hidden = !o.entrar; G('gateIn').disabled = false; gate.classList.toggle('entrar', !!o.entrar); G('gateNota').hidden = !o.entrar;
    G('gateOut').hidden = !o.salir;
    G('gateErr').textContent = o.error || ''; G('gateErr').hidden = !o.error;
    root.classList.add('gate');
  }
  cara('');
  async function salir() { try { await CU.sb.auth.signOut(); } catch (x) {} location.reload(); }   // recargar: no queda nada de esta cuenta en la página
  G('gateOut').onclick = (ev) => { ev.target.disabled = true; salir(); };

  const info = (u) => { const m = u.user_metadata || {}; return { name: m.full_name || m.name || (u.email || '').split('@')[0], email: u.email || '', pic: m.avatar_url || m.picture || '' }; };
  function avatar(box, d) {   // su foto de Google; si no carga, su inicial
    box.textContent = '';
    const ini = () => { box.textContent = (d.name || d.email || '?').trim().charAt(0).toUpperCase(); };
    if (!d.pic) return ini();
    const im = document.createElement('img'); im.alt = ''; im.referrerPolicy = 'no-referrer'; im.onerror = ini; im.src = d.pic; box.appendChild(im);
  }

  let menu = null;
  function closeMenu() { if (menu) { menu.remove(); menu = null; } const b = document.getElementById('cuentaBtn'); if (b) b.classList.remove('on'); }
  function openMenu(btn) {
    if (menu) return closeMenu();
    const d = info(CU.user), r = btn.getBoundingClientRect();
    menu = document.createElement('div'); menu.className = 'cuentamenu';
    const av = document.createElement('div'); av.className = 'cav'; avatar(av, d);
    const n = document.createElement('b'); n.textContent = d.name;
    const e = document.createElement('small'); e.textContent = d.email;
    const out = document.createElement('button'); out.textContent = 'Cerrar sesión';
    out.onclick = () => { out.disabled = true; out.textContent = 'Cerrando…'; salir(); };
    menu.append(av, n, e, out);
    menu.style.top = (r.bottom + 8) + 'px'; menu.style.right = Math.max(8, innerWidth - r.right) + 'px';
    menu.onclick = (ev) => ev.stopPropagation();
    document.body.appendChild(menu); btn.classList.add('on');
  }
  document.addEventListener('click', closeMenu);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeMenu(); });
  window.addEventListener('resize', closeMenu);

  function mountBtn() {
    const right = document.querySelector('header .right'); if (!right || !CU.user) return;
    let b = document.getElementById('cuentaBtn');
    if (!b) {
      b = document.createElement('button'); b.id = 'cuentaBtn'; b.className = 'cuentabtn'; b.title = 'Tu cuenta';
      b.onclick = (e) => { e.stopPropagation(); openMenu(b); };
      right.appendChild(b);
    }
    avatar(b, info(CU.user));
  }

  // ---------- cargar la app (solo con sesión) ----------
  // ---------- la sesión viaja al servidor: cabecera en /api y cookie para las imágenes propias (<img> no manda cabeceras) ----------
  function sesion(session) {
    CU.token = (session && session.access_token) || '';
    const seguro = location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = 'aria_token=' + (CU.token ? encodeURIComponent(CU.token) + '; Max-Age=3600' : '; Max-Age=0') + '; Path=/; SameSite=Lax' + seguro;
  }
  const SERVIDOR_URL = LOCAL ? '' : 'https://aria-studio.onrender.com';   // el servidor de las cuentas (generar, personajes, creaciones). En desarrollo (localhost:3000) lo pone web_dev.py
  const fetch0 = window.fetch.bind(window);
  // Si el servidor no contesta (se está reiniciando tras una actualización, o un corte de red), las LECTURAS se reintentan solas
  // durante un minuto con un aviso a la vista. Antes la app lo tomaba por «no tienes nada» y enseñaba la cuenta vacía.
  let avisoEl = null;
  function aviso(on) {
    if (!on) { if (avisoEl) { avisoEl.remove(); avisoEl = null; } return; }
    if (avisoEl) return;
    avisoEl = document.createElement('div'); avisoEl.textContent = 'Conectando con el servidor… tus datos están a salvo';
    avisoEl.style.cssText = 'position:fixed;top:10px;left:50%;transform:translateX(-50%);z-index:100000;background:var(--acc);color:#fff;font:600 12.5px var(--sans);padding:9px 16px;border-radius:999px;box-shadow:0 8px 24px rgba(0,0,0,.3)';
    document.body.appendChild(avisoEl);
  }
  let renovando = null;
  function renueva() {   // una sola renovación a la vez, aunque fallen varias peticiones juntas
    if (!renovando) renovando = (async () => { try { const { data, error } = await CU.sb.auth.refreshSession(); if (error || !data || !data.session) return false; sesion(data.session); return true; } catch (e) { return false; } })().finally(() => { setTimeout(() => { renovando = null; }, 3000); });
    return renovando;
  }
  function caducada() { dentro = null; cara('Tu sesión ha caducado. Vuelve a entrar y sigues donde estabas.', { entrar: true }); }
  async function conReintento(input, init) {
    const lectura = !init.method || init.method === 'GET';
    const esperas = lectura ? [2000, 4000, 8000, 12000, 16000, 20000] : [];
    for (let i = 0; ; i++) {
      try {
        let r = await (CU._fetch0 || fetch0)(input, init);
        if (r.status === 401 && CU.sb && CU.user) {   // la sesión se quedó vieja (portátil dormido, pestaña horas abierta)
          if (await renueva()) { init.headers.set('Authorization', 'Bearer ' + CU.token); r = await (CU._fetch0 || fetch0)(input, init); }
          if (r.status === 401) { aviso(false); caducada(); return r; }
        }
        if (!(lectura && [502, 503, 504].includes(r.status)) || i >= esperas.length) { aviso(false); return r; }
      } catch (e) { if (i >= esperas.length) { aviso(false); throw e; } }
      aviso(true); await new Promise((ok) => setTimeout(ok, esperas[i]));
    }
  }
  window.fetch = (input, init) => {
    if (CU.token && typeof input === 'string' && input.startsWith('/api/')) {   // /api va directo al servidor (sin tope de tamaño ni de tiempo), con la sesión en la cabecera
      init = Object.assign({}, init); init.headers = new Headers(init.headers || {}); init.headers.set('Authorization', 'Bearer ' + CU.token); if (CU.verMiembro) init.headers.set('X-Ver-Como', 'miembro');
      return conReintento(SERVIDOR_URL + input, init);
    }
    return fetch0(input, init);
  };
  async function catalogo() {   // el catálogo lleva los prompts: solo lo reciben los miembros con sesión
    try {   // con servidor propio: el catálogo común más lo tuyo (tu perfil, tus prendas, tus favoritas)
      const r = await fetch('/api/catalogo');
      if (r.ok && /json/.test(r.headers.get('content-type') || '')) { window.CATALOG = await r.json(); if (window.CATALOG && window.CATALOG.biblio) return; }
    } catch (e) {}
    let txt;
    try { const { data, error } = await CU.sb.storage.from('catalogo').download('catalog.js'); if (error) throw error; txt = await data.text(); }
    catch (e) { if (!LOCAL) throw e; const r = await fetch('/catalog.js'); if (!r.ok) throw e; txt = await r.text(); }   // en desarrollo vale el del puente
    const s = document.createElement('script'); s.textContent = txt; document.body.appendChild(s);
    if (!window.CATALOG) throw new Error('catálogo vacío');
  }
  function sinApi() {   // la web todavía no tiene servidor propio para generar: se ve la biblioteca, sin los avisos del puente local
    root.classList.add('sinapi');
    const right = document.querySelector('header .right'); if (!right || document.getElementById('webNote')) return;
    const n = document.createElement('span'); n.id = 'webNote'; n.className = 'webnote'; n.textContent = 'Biblioteca · generar llega muy pronto';
    right.prepend(n);
    // la Filmoteca (vídeos, 9 GB) aún no está subida: en el menú queda como «pronto»
    const bn = window.buildNav; if (typeof bn !== 'function') return;
    const pronto = () => document.querySelectorAll('#nav button').forEach((b) => {
      if (!/Filmoteca/i.test(b.textContent) || b.classList.contains('soon')) return;
      b.classList.add('soon'); b.insertAdjacentHTML('beforeend', '<i>pronto</i>'); b.title = 'Filmoteca: llega a la web muy pronto';
      b.onclick = () => { if (window.toast) toast('La Filmoteca llega a la web muy pronto'); };
    });
    window.buildNav = function () { bn.apply(this, arguments); pronto(); };
    pronto();
  }
  let arrancado = null;
  CU.arrancar = function () {
    if (arrancado) return arrancado;
    // la app se apunta a DOMContentLoaded, que aquí ya ha pasado: se le llama al momento
    const add = document.addEventListener.bind(document);
    document.addEventListener = (t, fn, o) => (t === 'DOMContentLoaded') ? void setTimeout(() => fn.call(document, new Event('DOMContentLoaded')), 0) : add(t, fn, o);
    arrancado = (async () => {
      // Primero se bajan TODOS los ficheros y luego se ejecutan seguidos, sin pausas entre uno y otro, como en local:
      // la app arranca 50 ms después de cargarse y para entonces los módulos (fichas, personajes…) ya tienen que estar puestos.
      const [, textos] = await Promise.all([catalogo(), Promise.all(APP.map((s) => fetch0(s).then((r) => { if (!r.ok) throw new Error('no carga ' + s); return r.text(); })))]);
      APP.forEach((s, i) => { const e = document.createElement('script'); e.textContent = textos[i] + '\n//# sourceURL=' + location.origin + '/' + s; document.body.appendChild(e); });
      fetch('/api/ping').then((r) => (r.ok ? r.json() : null)).then((j) => { if (!(j && j.ok)) sinApi(); }).catch(sinApi);
    })();
    arrancado.catch(() => { arrancado = null; });
    return arrancado;
  };

  let dentro = null;   // id de la cuenta con la que ya se ha entrado (el aviso de sesión llega varias veces)
  async function entrar(session) {
    const u = session.user; if (dentro === u.id) return; dentro = u.id;
    CU.user = u;
    cara('Abriendo tu estudio…');
    let m;
    try { const { data, error } = await CU.sb.from('miembros').select('email,interno').maybeSingle(); if (error) throw error; m = data; }
    catch (e) {
      if (!LOCAL) { dentro = null; return cara('', { salir: true, error: 'No se ha podido comprobar tu acceso. Recarga la página.' }); }
      console.warn('[cuenta] sin lista de miembros (desarrollo): se entra igualmente', e); m = { interno: true, dev: true };
    }
    if (!m) return cara(`La cuenta ${u.email} todavía no tiene acceso. ARIA STUDIO está abierto solo a miembros de la comunidad.`, { salir: true });
    CU.interno = !!m.interno;
    CU.ariaMia = DUENOS.includes((u.email || '').toLowerCase()) || (!!m.interno && !m.dev);
    CU.equipo = CU.ariaMia;   // 👁 el equipo puede ver la web como un miembro normal (se recuerda en este navegador)
    try { CU.verMiembro = CU.equipo && localStorage.getItem('am_vermiembro') === '1'; } catch (e) { CU.verMiembro = false; }
    if (CU.verMiembro) { CU.interno = false; CU.ariaMia = false; }   // Aria de equipo: Max y las cuentas internas la editan (solo para pintar: quien manda es el servidor)
    // Lo que la app recuerda en el navegador (la combinación a medias, el personaje elegido, el modelo…) es de UNA cuenta:
    // si en este navegador entra otra, empieza limpia (antes heredaba lo último de la anterior).
    try {
      if (localStorage.getItem('am_cuenta') !== u.id) {
        Object.keys(localStorage).filter((k) => k.startsWith('am_') && k !== 'am_theme').forEach((k) => localStorage.removeItem(k));
        localStorage.setItem('am_cuenta', u.id);
      }
    } catch (e) {}
    try { await CU.arrancar(); }
    catch (e) { console.error('[cuenta]', e); dentro = null; return cara('', { salir: true, error: 'No se ha podido abrir el estudio. Recarga la página.' }); }
    root.classList.remove('gate'); mountBtn();
  }
  function fuera() { CU.user = null; dentro = null; cara('Crea imágenes y vídeos con tu personaje de IA', { entrar: true }); }

  const lib = document.createElement('script');
  lib.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2';
  lib.onerror = () => cara('', { error: 'No se ha podido conectar. Revisa tu conexión y recarga la página.' });
  lib.onload = () => {
    const sb = CU.sb = window.supabase.createClient(SB_URL, SB_KEY, { auth: { flowType: 'pkce' } });
    const q = new URLSearchParams(location.search), qerr = q.get('error_description');
    if (qerr) history.replaceState(null, '', location.pathname);
    G('gateIn').onclick = async (ev) => {
      G('gateErr').hidden = true; ev.target.disabled = true;
      const { error } = await sb.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: location.origin } });
      if (error) cara(G('gateMsg').textContent, { entrar: true, error: error.message });
    };
    // dentro de este aviso no se puede esperar a Supabase (se bloquea): se sale de él con setTimeout
    const paint = (session) => setTimeout(() => { if (session && session.user) entrar(session); else if (!dentro) { fuera(); if (qerr) cara(G('gateMsg').textContent, { entrar: true, error: qerr }); } }, 0);
    sb.auth.onAuthStateChange((ev, session) => { sesion(session); if (ev === 'SIGNED_OUT') { dentro = null; return fuera(); } paint(session); });   // también al renovarse la sesión (cada hora)
    sb.auth.getSession().then(({ data }) => { sesion(data.session); paint(data.session); }).catch(() => fuera());
  };
  document.head.appendChild(lib);
})();
