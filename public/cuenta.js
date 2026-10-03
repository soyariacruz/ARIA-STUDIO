/* ARIA STUDIO · tu cuenta (v134).
   Solo actúa en la versión web: el puerto 3000 en desarrollo (aria-studio-web/web_dev.py) o cualquier dominio que no sea este ordenador.
   Sin sesión se ve la portada con «Entrar con Google». Con sesión comprueba que tu correo está en la lista de miembros, baja el catálogo
   (privado, de Supabase) y solo entonces carga la app; arriba a la derecha queda tu perfil con «Cerrar sesión».
   En local (el puente, :8767) no hace nada: ahí no hay cuentas y la app se carga con sus etiquetas de siempre. */
(function () {
  const LOCAL = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
  const WEB = !LOCAL || location.port === '3000';
  const CU = window.CUENTA = { web: WEB, user: null, sb: null, interno: false };
  if (!WEB) return;

  // Las dos son públicas por diseño (van en el navegador). Lo que protege los datos son las reglas de Supabase.
  const SB_URL = 'https://uhscbgidrloskdjbevkn.supabase.co';
  const SB_KEY = 'sb_publishable_GSO5Vqhr7Dg93egtKk_I2w_E_uScoNG';
  const APP = ['app.js', 'feedback.js', 'personajes.js', 'complementos.js', 'fichas.js', 'fichas360.js'];   // en este orden, después del catálogo
  const root = document.documentElement;
  try { if (localStorage.getItem('am_theme') !== 'light') root.classList.add('dark'); } catch (e) { root.classList.add('dark'); }
  root.classList.add('gate');   // hasta que la app esté cargada con tu sesión, no se ve

  const css = document.createElement('style');
  css.textContent = `
html.gate body>*:not(#gate){visibility:hidden!important}
#gate{position:fixed;inset:0;z-index:99999;background:var(--bg);display:none;align-items:center;justify-content:center;padding:16px;overflow:auto}
html.gate #gate{display:flex}
#gate .gcard{width:100%;max-width:400px;background:var(--panel);border:1px solid var(--line);border-radius:24px;padding:44px 34px 36px;text-align:center;display:flex;flex-direction:column;gap:20px;box-shadow:0 24px 60px rgba(0,0,0,.18)}
#gate h1{font-family:var(--serif);font-weight:500;font-size:32px;letter-spacing:.06em;color:var(--ink)}
#gate h1 i{font-style:normal;color:var(--acc);margin-left:.3em}
#gate p{color:var(--mut);font-size:14px;line-height:1.55}
#gate button{font-family:inherit;font-size:15px;font-weight:700;border-radius:999px;padding:14px 20px;cursor:pointer;border:1px solid var(--line);background:var(--bg);color:var(--ink);transition:transform .1s,filter .15s}
#gate .gin{border-color:var(--acc);background:var(--acc);color:#fff}
#gate button:hover{filter:brightness(1.07)}
#gate button:active{transform:scale(.98)}
#gate button:disabled{opacity:.55;cursor:default}
#gate .gerr{color:#e0566a;font-size:13px}
#gate [hidden]{display:none!important}
#console,#btnConsole{display:none!important}
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
  gate.innerHTML = '<div class="gcard"><h1>ARIA<i>STUDIO</i></h1>' +
    '<p id="gateMsg"></p>' +
    '<button class="gin" id="gateIn" hidden>Entrar con Google</button>' +
    '<button id="gateOut" hidden>Cerrar sesión</button>' +
    '<p class="gerr" id="gateErr" hidden></p></div>';
  document.body.prepend(gate);
  const G = (id) => gate.querySelector('#' + id);
  // La portada tiene cuatro caras: esperando, entrar, abriendo el estudio y «sin acceso».
  function cara(msg, o = {}) {
    G('gateMsg').textContent = msg || ''; G('gateMsg').hidden = !msg;
    G('gateIn').hidden = !o.entrar; G('gateIn').disabled = false;
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
  const tag = (src) => new Promise((ok, ko) => { const s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = () => ko(new Error('no carga ' + src)); document.body.appendChild(s); });
  // ---------- la sesión viaja al servidor: cabecera en /api y cookie para las imágenes propias (<img> no manda cabeceras) ----------
  function sesion(session) {
    CU.token = (session && session.access_token) || '';
    const seguro = location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = 'aria_token=' + (CU.token ? encodeURIComponent(CU.token) + '; Max-Age=3600' : '; Max-Age=0') + '; Path=/; SameSite=Lax' + seguro;
  }
  const SERVIDOR_URL = LOCAL ? '' : 'https://aria-studio.onrender.com';   // el servidor de las cuentas (generar, personajes, creaciones). En desarrollo (localhost:3000) lo pone web_dev.py
  const fetch0 = window.fetch.bind(window);
  window.fetch = (input, init) => {
    if (CU.token && typeof input === 'string' && input.startsWith('/api/')) {   // /api va directo al servidor (sin tope de tamaño ni de tiempo), con la sesión en la cabecera
      init = Object.assign({}, init); init.headers = new Headers(init.headers || {}); init.headers.set('Authorization', 'Bearer ' + CU.token);
      input = SERVIDOR_URL + input;
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
      await catalogo(); for (const s of APP) await tag(s);
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
      console.warn('[cuenta] sin lista de miembros (desarrollo): se entra igualmente', e); m = { interno: true };
    }
    if (!m) return cara(`La cuenta ${u.email} todavía no tiene acceso. ARIA STUDIO está abierto solo a miembros de la comunidad.`, { salir: true });
    CU.interno = !!m.interno;
    try { await CU.arrancar(); }
    catch (e) { console.error('[cuenta]', e); dentro = null; return cara('', { salir: true, error: 'No se ha podido abrir el estudio. Recarga la página.' }); }
    root.classList.remove('gate'); mountBtn();
  }
  function fuera() { CU.user = null; dentro = null; cara('Crea imágenes y vídeos con tus propios personajes de IA.', { entrar: true }); }

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
