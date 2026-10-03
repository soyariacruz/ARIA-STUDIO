/* ARIA STUDIO · tu cuenta (v133).
   Solo actúa en la versión web: el puerto 3000 en desarrollo (aria-studio-web/web_dev.py) o cualquier dominio que no sea este ordenador.
   Sin sesión se ve la portada con «Entrar con Google»; con sesión, la app y arriba a la derecha tu perfil con «Cerrar sesión».
   En local (el puente, :8767) no hace nada: ahí no hay cuentas. */
(function () {
  const LOCAL = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
  const WEB = !LOCAL || location.port === '3000';
  const CU = window.CUENTA = { web: WEB, user: null, sb: null };
  if (!WEB) return;

  // Las dos son públicas por diseño (van en el navegador). Lo que protege los datos son las reglas de Supabase.
  const SB_URL = 'https://uhscbgidrloskdjbevkn.supabase.co';
  const SB_KEY = 'sb_publishable_GSO5Vqhr7Dg93egtKk_I2w_E_uScoNG';
  const root = document.documentElement;
  try { if (localStorage.getItem('am_theme') !== 'light') root.classList.add('dark'); } catch (e) { root.classList.add('dark'); }
  root.classList.add('gate');   // hasta saber si hay sesión, la app no se ve

  const css = document.createElement('style');
  css.textContent = `
html.gate body>*:not(#gate){visibility:hidden!important}
#gate{position:fixed;inset:0;z-index:99999;background:var(--bg);display:none;align-items:center;justify-content:center;padding:16px;overflow:auto}
html.gate #gate{display:flex}
#gate .gcard{width:100%;max-width:400px;background:var(--panel);border:1px solid var(--line);border-radius:24px;padding:44px 34px 36px;text-align:center;display:flex;flex-direction:column;gap:20px;box-shadow:0 24px 60px rgba(0,0,0,.18)}
#gate h1{font-family:var(--serif);font-weight:500;font-size:32px;letter-spacing:.06em;color:var(--ink)}
#gate h1 i{font-style:normal;color:var(--acc);margin-left:.3em}
#gate p{color:var(--mut);font-size:14px;line-height:1.55}
#gate .gin{font-family:inherit;font-size:15px;font-weight:700;border-radius:999px;padding:14px 20px;cursor:pointer;border:1px solid var(--acc);background:var(--acc);color:#fff;transition:transform .1s,filter .15s}
#gate .gin:hover{filter:brightness(1.07)}
#gate .gin:active{transform:scale(.98)}
#gate .gin:disabled{opacity:.55;cursor:default}
#gate .gerr{color:#e0566a;font-size:13px}
#gate.wait .gbody{visibility:hidden}
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
  gate.id = 'gate'; gate.className = 'wait';
  gate.innerHTML = '<div class="gcard"><h1>ARIA<i>STUDIO</i></h1><div class="gbody" style="display:flex;flex-direction:column;gap:20px">' +
    '<p>Crea imágenes y vídeos con tus propios personajes de IA.</p>' +
    '<button class="gin" id="gateIn">Entrar con Google</button>' +
    '<p class="gerr" id="gateErr" hidden></p></div></div>';
  document.body.prepend(gate);
  const fail = (m) => { const e = gate.querySelector('#gateErr'); e.textContent = m || ''; e.hidden = !m; };

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
    out.onclick = async () => { out.disabled = true; out.textContent = 'Cerrando…'; try { await CU.sb.auth.signOut(); } catch (x) {} location.reload(); };   // recargar: no queda nada de esta cuenta en la página
    menu.append(av, n, e, out);
    menu.style.top = (r.bottom + 8) + 'px'; menu.style.right = Math.max(8, innerWidth - r.right) + 'px';
    menu.onclick = (ev) => ev.stopPropagation();
    document.body.appendChild(menu); btn.classList.add('on');
  }
  document.addEventListener('click', closeMenu);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeMenu(); });
  window.addEventListener('resize', closeMenu);

  function mountBtn() {
    let b = document.getElementById('cuentaBtn');
    if (!CU.user) { if (b) b.remove(); return closeMenu(); }
    const right = document.querySelector('header .right'); if (!right) return;
    if (!b) {
      b = document.createElement('button'); b.id = 'cuentaBtn'; b.className = 'cuentabtn'; b.title = 'Tu cuenta';
      b.onclick = (e) => { e.stopPropagation(); openMenu(b); };
      right.appendChild(b);
    }
    avatar(b, info(CU.user));
  }

  function paint(session) {
    CU.user = (session && session.user) || null;
    gate.classList.remove('wait');
    root.classList.toggle('gate', !CU.user);
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mountBtn, { once: true }); else mountBtn();
  }

  const lib = document.createElement('script');
  lib.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2';
  lib.onerror = () => { gate.classList.remove('wait'); gate.querySelector('#gateIn').disabled = true; fail('No se ha podido conectar. Revisa tu conexión y recarga la página.'); };
  lib.onload = () => {
    const sb = CU.sb = window.supabase.createClient(SB_URL, SB_KEY, { auth: { flowType: 'pkce' } });
    const q = new URLSearchParams(location.search);
    if (q.get('error_description')) { fail(q.get('error_description')); history.replaceState(null, '', location.pathname); }
    gate.querySelector('#gateIn').onclick = async (ev) => {
      fail(''); ev.target.disabled = true;
      const { error } = await sb.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: location.origin } });
      if (error) { fail(error.message); ev.target.disabled = false; }
    };
    sb.auth.onAuthStateChange((_ev, session) => paint(session));
    sb.auth.getSession().then(({ data }) => paint(data.session)).catch(() => paint(null));
  };
  document.head.appendChild(lib);
})();
