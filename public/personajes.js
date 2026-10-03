// ARIA STUDIO · PERSONAJES (v116)
// Mis personajes en el Perfil + creador de personajes paso a paso, basado en el Bloque 1 del curso
// «De 0 a 100 para crear tu Influencer IA». Tres formas de empezar: desde cero, desde tus fotos favoritas (la IA rellena los rasgos) o «ya tengo mi personaje».
// Al guardar: 1 · encontrar su cara en rejillas de 3×3 → 2 · sus 4 vistas (ficha 360) → 3 · su ficha de cuerpo → 4 · su ficha principal (combinada).
// Aria es fija (vive en catalog.js). Los demás se guardan en assets/personajes/<id>/personaje.json a través del puente.
(function () {
  const CUR = 'assets/personajes/_opciones/curso/';
  const pj = { list: [], sel: 'aria', wiz: null, jobs: {} };
  const WEBM = !!(window.CUENTA && CUENTA.web && !CUENTA.ariaMia);   // miembro de la web: empieza por SU personaje y Aria es un personaje fijo (se ve y se usa, no se edita). En local y en la cuenta de Max en la web, Aria es su personaje y va primero
  window.PJ = pj;

  // ---------------------------------------------------------------- opciones (es = etiqueta, en = frase del prompt)
  const O = {
    rol: [
      ['educa', '🎓', 'Educadora · tutoriales', 'an educator who explains things simply'], ['life', '☕', 'Lifestyle', 'a lifestyle creator'],
      ['moda', '👗', 'Moda y belleza', 'a fashion and beauty creator'], ['fit', '💪', 'Fitness y salud', 'a fitness and wellness creator'],
      ['game', '🎮', 'Gaming', 'a gaming creator'], ['viaje', '✈️', 'Viajes', 'a travel creator'], ['humor', '😂', 'Humor', 'a comedy creator'],
      ['tech', '🤖', 'Tecnología e IA', 'a tech and AI creator'], ['cocina', '🍳', 'Cocina', 'a food creator'], ['arte', '🎨', 'Arte y música', 'an art and music creator'],
      ['negocio', '💼', 'Negocios y finanzas', 'a business and finance creator'], ['modelo', '📷', 'Modelo', 'a model'], ['coach', '🧭', 'Coach y motivación', 'a motivational coach'],
      ['familia', '🍼', 'Familia y maternidad', 'a family and parenting creator'], ['baile', '💃', 'Baile', 'a dance creator']],
    nicho: [
      ['ia', '🤖', 'Crear con IA'], ['influia', '🧬', 'Influencers IA'], ['moda', '👗', 'Moda'], ['maquillaje', '💄', 'Maquillaje'], ['skincare', '🧴', 'Skincare'], ['pelo', '💇', 'Peinados'],
      ['fitness', '🏋️', 'Fitness'], ['yoga', '🧘', 'Yoga y bienestar'], ['nutricion', '🥗', 'Nutrición'], ['recetas', '🍝', 'Recetas'], ['viajes', '🌍', 'Viajes'], ['lujo', '💎', 'Lujo'],
      ['finanzas', '💰', 'Finanzas personales'], ['emprender', '🚀', 'Emprendimiento'], ['marketing', '📈', 'Marketing digital'], ['productividad', '⏱', 'Productividad'],
      ['gaming', '🎮', 'Videojuegos'], ['anime', '🌸', 'Anime y cómics'], ['musica', '🎧', 'Música'], ['foto', '📸', 'Fotografía'], ['deco', '🛋', 'Decoración'], ['mascotas', '🐶', 'Mascotas'],
      ['relaciones', '💞', 'Relaciones'], ['libros', '📚', 'Libros'], ['cine', '🎬', 'Cine y series'], ['coches', '🏎', 'Coches'], ['deporte', '⚽', 'Deportes'], ['idiomas', '🗣', 'Idiomas'], ['cosplay', '🦸', 'Cosplay']],
    genero: [['fem', '♀', 'Femenino', 'woman'], ['masc', '♂', 'Masculino', 'man'], ['andro', '⚥', 'Andrógino', 'androgynous person'], ['nb', '✧', 'No binario', 'non-binary person'], ['fluido', '⟡', 'Género fluido', 'gender-fluid person'], ['agenero', '○', 'Agénero', 'agender person']],
    cara: [['oval', 'svg:oval', 'Ovalada', 'an oval face'], ['redonda', 'svg:round', 'Redonda', 'a round face with soft cheeks'], ['corazon', 'svg:heart', 'Corazón', 'a heart-shaped face with a delicate chin'],
      ['angulosa', 'svg:square', 'Angulosa', 'an angular face with a defined jawline'], ['alargada', 'svg:long', 'Alargada', 'a long, slender face']],
    ojos: [['negros', 'img:ojos_negros', 'Negros', 'dark almost black'], ['marrones', 'img:ojos_marrones', 'Marrones', 'warm brown'], ['verdes', 'img:ojos_verdes', 'Verdes', 'bright green'],
      ['azules', 'img:ojos_azules', 'Azules', 'clear blue'], ['grises', 'img:ojos_grises', 'Grises', 'soft grey'], ['ambar', 'img:ojos_ambar', 'Ámbar', 'amber'],
      ['amarillos', 'img:ojos_amarillos', 'Amarillos', 'golden yellow'], ['violeta', 'img:ojos_violeta', 'Violeta', 'violet']],
    ojosForma: [['caidos', 'svg:eyeDown', 'Caídos', 'slightly downturned'], ['rasgados', 'svg:eyeCat', 'Rasgados', 'upturned, cat-like'], ['almendra', 'svg:eyeAlmond', 'Almendrados', 'almond-shaped'], ['redondos', 'svg:eyeRound', 'Redondos', 'large and round']],
    labios: [['finos', 'svg:lips1', 'Finos', 'thin lips'], ['medios', 'svg:lips2', 'Naturales', 'natural medium lips'], ['carnosos', 'svg:lips3', 'Carnosos', 'full lips'], ['muy', 'svg:lips4', 'Muy carnosos', 'very full, plump lips']],
    nariz: [['peq', 'svg:noseUp', 'Pequeña respingona', 'a small upturned nose'], ['recta', 'svg:noseStraight', 'Recta', 'a straight nose'], ['ancha', 'svg:noseWide', 'Ancha', 'a wide nose'], ['aguilena', 'svg:noseHook', 'Aguileña', 'an aquiline nose']],
    peloColor: [['negro', 'img:pelo_negro', 'Negro', 'black'], ['castano', 'img:pelo_castano', 'Castaño', 'chestnut brown'], ['rubio', 'img:pelo_rubio', 'Rubio', 'blonde'], ['pelirrojo', 'img:pelo_pelirrojo', 'Pelirrojo', 'copper red'],
      ['rosa', 'img:pelo_rosa', 'Rosa pastel', 'pastel pink'], ['azul', 'img:pelo_azul', 'Azul eléctrico', 'electric blue'], ['verde', 'img:pelo_verde', 'Verde', 'emerald green']],
    textura: [['liso', '〰️', 'Liso', 'straight'], ['ondulado', '🌊', 'Ondulado', 'wavy'], ['rizado', '➰', 'Rizado', 'curly'], ['afro', '🌀', 'Afro', 'coily, afro-textured']],
    piel: [['muyclara', 'sw:#f6dccb', 'Muy clara', 'very fair'], ['clara', 'sw:#ecc6a8', 'Clara', 'fair'], ['media', 'sw:#d6a47d', 'Media', 'medium olive'], ['morena', 'sw:#b27a50', 'Morena', 'tan'],
      ['oscura', 'sw:#7b4a2c', 'Oscura', 'dark brown'], ['ebano', 'sw:#4a2b1b', 'Ébano', 'deep ebony']],
    matiz: [['calido', 'sw:#e2a878', 'Cálido', 'warm'], ['neutro', 'sw:#d2ab8e', 'Neutro', 'neutral'], ['frio', 'sw:#e6c0bd', 'Frío', 'cool pink']],
    pielDet: [['hoyuelos', '😊', 'Hoyuelos', 'dimples'], ['tatuajes', '🖋', 'Tatuajes', 'visible tattoos', 1], ['cicatriz', '〽️', 'Cicatriz sutil', 'a subtle scar', 1],
      ['pecas', '🟤', 'Pecas', 'freckles', 0, 1], ['lunar', '•', 'Lunar', 'a small beauty mark', 0, 1], ['sonrojo', '🌸', 'Mejillas sonrojadas', 'rosy cheeks', 0, 1]],
    complexion: [['menuda', 'body:0.78,0.62,0.8,0.8', 'Menuda', 'petite and small-framed'], ['delgada', 'body:0.9,0.66,0.9,0.85', 'Delgada', 'slim'], ['atletica', 'body:1.02,0.74,0.96,0.95', 'Atlética', 'athletic and toned'],
      ['media', 'body:1,0.84,1.02,1', 'Media', 'average build'], ['curvy', 'body:0.98,0.7,1.22,1.15', 'Curvy', 'curvy hourglass figure'], ['musculosa', 'body:1.2,0.9,1,1.05', 'Musculosa', 'muscular'], ['grande', 'body:1.12,1.08,1.2,1.2', 'Grande', 'plus-size']],
    pecho: [['peq', 'bust:0.86', 'Pequeño', 'a small bust'], ['medio', 'bust:1', 'Medio', 'a medium bust'], ['grande', 'bust:1.16', 'Grande', 'a large bust'], ['muy', 'bust:1.3', 'Muy grande', 'a very large bust']],
    cadera: [['estrecha', 'hip:0.86', 'Estrecha', 'narrow hips'], ['media', 'hip:1', 'Media', 'medium hips'], ['ancha', 'hip:1.18', 'Ancha', 'wide rounded hips'], ['muy', 'hip:1.32', 'Muy marcada', 'very curvy wide hips and prominent glutes']],
    estilo: [['realista', 'img:estilo_realista', 'Realista', 'a realistic smartphone photo, natural skin texture'], ['cartoon', 'img:estilo_cartoon', 'Cartoon', 'a cartoon illustration'], ['propio', '＋', 'Su propio estilo', 'the visual style of the style reference'],
      ['anime', 'img:estilo_anime', 'Anime', 'an anime illustration'], ['3d', 'img:estilo_3d', '3D hiperrealista', 'a hyperrealistic 3D render']],
    ropa: [['casual', '👕', 'Casual', 'casual'], ['sport', '👟', 'Deportiva', 'sporty'], ['elegante', '👠', 'Elegante', 'elegant'], ['street', '🧢', 'Streetwear', 'streetwear']],
    acc: [['gafasr', '👓', 'Gafas redondas', 'round glasses'], ['gafass', '🕶', 'Gafas de sol', 'sunglasses'], ['aros', '⭕', 'Aros', 'hoop earrings'], ['collar', '📿', 'Collar', 'a delicate necklace'],
      ['gorra', '🧢', 'Gorra', 'a cap'], ['piercing', '💎', 'Piercing', 'a small nose piercing'], ['reloj', '⌚', 'Reloj', 'a wristwatch'], ['panuelo', '🧣', 'Pañuelo', 'a silk scarf']],
    pers: [['cercana', '🤗', 'Cercana', 'approachable'], ['divertida', '😄', 'Divertida', 'fun'], ['inspira', '✨', 'Inspiradora', 'inspiring'], ['ironica', '😏', 'Irónica', 'witty'],
      ['timida', '🙈', 'Tímida pero valiente', 'shy but brave'], ['energica', '⚡', 'Enérgica', 'energetic'], ['tranquila', '🌿', 'Tranquila', 'calm'], ['misteriosa', '🌙', 'Misteriosa', 'mysterious'],
      ['profesional', '💼', 'Profesional', 'professional'], ['rebelde', '🔥', 'Rebelde', 'rebellious'], ['sonadora', '☁️', 'Soñadora', 'dreamy'], ['sabia', '🦉', 'Sabia', 'wise'],
      ['romantica', '💌', 'Romántica', 'romantic'], ['aventurera', '🧗', 'Aventurera', 'adventurous'], ['elegante', '🥂', 'Elegante', 'elegant'], ['friki', '🤓', 'Friki', 'geeky']],
    voz: [['cercano', '💬', 'Cercano', 'warm and casual'], ['divertido', '🎉', 'Divertido', 'playful'], ['ironico', '😏', 'Irónico', 'ironic'], ['inspirador', '🌟', 'Inspirador', 'inspiring'], ['formal', '🎩', 'Formal', 'formal'], ['directo', '🎯', 'Directo', 'direct'],
      ['dulce', '🍯', 'Dulce', 'sweet'], ['rapido', '💨', 'Rápido y con energía', 'fast and energetic'], ['pausado', '🐢', 'Pausado', 'slow and calm'], ['picaro', '😉', 'Pícaro', 'cheeky']],
  };
  const opt = (k, id) => (O[k] || []).find(o => o[0] === id);
  const en = (k, id) => { const o = opt(k, id); return o ? o[3] : ''; };
  const es = (k, id) => { const o = opt(k, id); return o ? o[2] : ''; };
  const arr = v => Array.isArray(v) ? v : v ? [v] : [];

  // ---------------------------------------------------------------- dibujos (siluetas y formas, sin gastar en generar)
  function svg(kind) {
    const S = (inner, vb = '0 0 100 100') => `<svg viewBox="${vb}" xmlns="http://www.w3.org/2000/svg" class="pjsvg">${inner}</svg>`;
    const st = 'fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"';
    if (kind === 'oval') return S(`<ellipse cx="50" cy="52" rx="28" ry="38" ${st}/>`);
    if (kind === 'round') return S(`<circle cx="50" cy="52" r="36" ${st}/>`);
    if (kind === 'heart') return S(`<path d="M22 30 Q24 14 50 16 Q76 14 78 30 Q80 56 50 90 Q20 56 22 30Z" ${st}/>`);
    if (kind === 'square') return S(`<path d="M22 22 Q22 14 32 14 H68 Q78 14 78 22 V60 Q78 80 60 88 H40 Q22 80 22 60Z" ${st}/>`);
    if (kind === 'long') return S(`<ellipse cx="50" cy="52" rx="22" ry="42" ${st}/>`);
    if (kind.startsWith('nose')) { // perfil de la nariz: frente a la izquierda, labio abajo
      const p = { noseUp: 'M40 12 C42 34 46 48 58 60 Q64 66 56 70 Q50 72 46 70', noseStraight: 'M40 12 C44 34 50 50 62 64 Q64 70 56 71 Q50 72 46 70', noseWide: 'M40 12 C44 32 50 46 60 60 Q72 66 64 72 Q52 76 44 70', noseHook: 'M40 12 C50 26 60 40 64 58 Q64 70 54 70 Q50 71 46 69' }[kind];
      return S(`<path d="M30 8 L30 92" stroke="currentColor" stroke-width="2" opacity=".18"/><path d="${p}" ${st}/><path d="M46 70 Q44 80 50 88" ${st} opacity=".6"/>`);
    }
    if (kind.startsWith('eye')) {
      const p = { eyeAlmond: 'M10 50 Q50 20 90 50 Q50 72 10 50Z', eyeRound: 'M14 50 Q50 12 86 50 Q50 88 14 50Z', eyeCat: 'M10 58 Q46 22 92 36 Q56 70 10 58Z', eyeDown: 'M10 42 Q50 22 90 56 Q48 72 10 42Z' }[kind];
      return S(`<path d="${p}" ${st}/><circle cx="50" cy="50" r="11" fill="currentColor"/>`);
    }
    if (kind.startsWith('lips')) {
      const t = { lips1: 5, lips2: 9, lips3: 13, lips4: 17 }[kind];
      return S(`<path d="M12 50 Q30 ${40 - t} 42 ${44 - t / 3} Q50 ${48 - t / 3} 58 ${44 - t / 3} Q70 ${40 - t} 88 50 Q70 ${56 + t * 1.3} 50 ${58 + t * 1.3} Q30 ${56 + t * 1.3} 12 50Z" fill="currentColor" opacity=".85"/><path d="M12 50 Q50 54 88 50" stroke="var(--bg,#111)" stroke-width="2" fill="none"/>`);
    }
    return '';
  }
  function body(sh, wa, hi, bu) { // silueta estilizada: hombros, cintura, cadera y pecho relativos
    const cx = 50, s = x => 23 * x; const top = 34, bust = 48, waist = 62, hip = 76, leg = 128;
    const L = x => cx - x, R = x => cx + x;
    const d = `M${L(s(sh))} ${top} Q${L(s(bu) * 1.02)} ${bust} ${L(s(wa))} ${waist} Q${L(s(hi) * 1.08)} ${hip - 4} ${L(s(hi))} ${hip + 4} L${L(s(hi) * 0.62)} ${leg} L${cx - 2} ${leg} L${cx} ${hip + 10} L${cx + 2} ${leg} L${R(s(hi) * 0.62)} ${leg} L${R(s(hi))} ${hip + 4} Q${R(s(hi) * 1.08)} ${hip - 4} ${R(s(wa))} ${waist} Q${R(s(bu) * 1.02)} ${bust} ${R(s(sh))} ${top} Q${cx} ${top - 6} ${L(s(sh))} ${top}Z`;
    return `<svg viewBox="0 0 100 134" xmlns="http://www.w3.org/2000/svg" class="pjsvg"><circle cx="50" cy="18" r="11" fill="currentColor"/><path d="M46 28 h8 v6 h-8z" fill="currentColor"/><path d="${d}" fill="currentColor"/></svg>`;
  }
  function visual(code) {
    if (!code) return '';
    if (code.startsWith('img:')) return `<img src="${CUR}${code.slice(4)}.jpg" alt="" loading="lazy">`;
    if (code.startsWith('sw:')) return `<span class="pjsw" style="background:${code.slice(3)}"></span>`;
    if (code.startsWith('svg:')) return svg(code.slice(4));
    if (code.startsWith('body:')) { const [a, b, c, d] = code.slice(5).split(',').map(Number); return body(a, b, c, d); }
    if (code.startsWith('bust:')) return body(0.95, 0.66, 0.98, 0.8 + (Number(code.slice(5)) - 0.86) * 1.6);
    if (code.startsWith('hip:')) return body(0.92, 0.66, 0.8 + (Number(code.slice(4)) - 0.86) * 1.5, 0.95);
    return `<span class="pjemo">${code}</span>`;
  }

  // ---------------------------------------------------------------- datos
  async function load() { try { const r = await fetch('/api/personajes').then(x => x.json()); pj.list = r.items || []; pj.tarj = new Set(r.tarjetas || []); } catch (e) { pj.list = []; pj.tarj = new Set(); } webIni(); syncChars(); recuperar(); }
  function webIni() {   // web, al abrir: el perfil enseña su primer personaje; si no tiene ninguno, «Crear personaje» (nunca el de Aria como si fuera suyo)
    if (!WEBM || pj.webIni) return; pj.webIni = true; if (!pj.wiz) pj.sel = pj.list.length ? pj.list[0].id : 'nuevo'; }
  function webChar() {   // miembro: en Crear imagen el personaje principal es SIEMPRE uno suyo (el primero con ficha, o el que elija entre los suyos); Aria solo se añade como segunda persona. Sin personaje propio todavía, se crea con Aria
    if (!WEBM || !window.setChar) return; const p0 = pj.list.find(p => p.ficha360); if (!p0) return;
    let ch = state.char; if (ch === undefined) { try { ch = localStorage.getItem('am_charsel') || 'aria'; } catch (e) { ch = 'aria'; } }
    if (ch === 'aria' || !pj.list.some(p => p.id === ch)) setChar(p0.id, true); }
  async function recuperar() { // trabajos de personajes que se lanzaron antes de recargar: si ya están, se recogen; si no, se siguen esperando
    let r; try { r = await fetch('/api/pendientes').then(x => x.json()); } catch (e) { return; }
    for (const j of (r.jobs || [])) { const pid = j.meta.personaje, kind = j.meta.pjKind; if (!pid || !kind || !pj.list.some(p => p.id === pid) || pj.jobs[pid + ':' + kind]) continue;
      const m = MODELS.find(x => x.key === (j.item || '').split('_').pop()) || curModel(); const job = { rid: j.rid, it: { id: 'pj:' + pid + ':' + kind, name: j.meta.name || kind }, tab: 'perfil', m, kind: 'image', persona: { id: pid, kind }, t0: performance.now() - j.edad * 1000, status: 'in_progress', usd: j.usd };
      pj.jobs[pid + ':' + kind] = job; if (j.file) await onJobDone(job, { file: j.file, usd: j.usd }); else { JOBS.set(j.rid, job); ensurePoller(); } }
    if (state.tab === 'perfil') { renderProfile(); renderSide(); } startTick();
  }
  const ARIA = 'assets/personajes/_opciones/aria/';
  const vis = (key, id, code) => (pj.tarj && pj.tarj.has(key + '_' + id)) ? `<img src="${ARIA}${key}_${id}.jpg" alt="" loading="lazy">` : visual(code);
  function syncChars() { C.chars = [C.chars && C.chars[0] || { id: 'aria', name: C.perfil.name, avatar: C.perfil.avatar, ficha: C.perfil.ficha }].concat(pj.list.map(p => ({ id: p.id, name: p.nombre, avatar: p.avatar || p.retrato || p.foto || '', ficha: p.ficha360 || '' }))); webChar(); if (window.charsReady) charsReady(); if (WEBM && window.buildNav) { try { buildNav(); } catch (e) {} } }   // en la web, el círculo de «Perfil» del menú es el de su personaje
  const cur = () => pj.list.find(p => p.id === pj.sel) || null;
  const pron = g => g === 'masc' ? ['He', 'His'] : g === 'fem' ? ['She', 'Her'] : ['They', 'Their'];
  const list = (a) => a.length < 2 ? (a[0] || '') : a.slice(0, -1).join(', ') + ' and ' + a[a.length - 1];
  const isData = v => typeof v === 'string' && v.startsWith('data:');
  const colorOf = (d, k) => d[k + 'Nombre'] ? (d[k + 'Hex'] ? `${d[k + 'Nombre']} (${d[k + 'Hex']})` : d[k + 'Nombre']) : '';

  function basePrompt(d) { // la plantilla del curso (lección 1.4), en inglés para los modelos
    const [P, Pp] = pron(d.genero); const has = P === 'They' ? 'have' : 'has';
    const face = [en('cara', d.cara), en('nariz', d.nariz), en('labios', d.labios)].filter(Boolean);
    const eyes = [colorOf(d, 'ojos') || en('ojos', d.ojos), en('ojosForma', d.ojosForma)].filter(Boolean);
    const acc = arr(d.acc).map(a => en('acc', a)).concat(d.accTxt ? [d.accTxt] : []);
    const hairStyle = d.peinado ? (d.peinado.desc || d.peinado.name) : '';
    const hair = [colorOf(d, 'pelo') || en('peloColor', d.peloColor), d.peloRef ? 'exactly the hair color of the hair color reference' : ''].filter(Boolean).join(', ');
    const skin = en('piel', d.piel);
    const det = arr(d.pielDet).map(x => en('pielDet', x)).concat(d.detTxt ? [d.detTxt] : d.detImg ? ['the unique detail of the detail reference'] : []);
    const bodyP = [en('complexion', d.complexion), d.altura ? `about ${d.altura} cm tall` : '', d.genero !== 'masc' ? en('pecho', d.pecho) : '', en('cadera', d.cadera)].filter(Boolean);
    const vibe = arr(d.pers).map(x => en('pers', x)).filter(Boolean);
    const gen = d.generoTxt || en('genero', d.genero) || 'woman';
    const style = d.estilo === 'cartoon' && d.cartoon ? `a cartoon image in the ${d.cartoon.name} style` : d.estilo === 'propio' ? 'an image in exactly the visual style of the style reference' : (en('estilo', d.estilo) || 'a realistic smartphone photo');
    const out = [];
    out.push(`A regular quality phone photo of a ${d.edad || 25}-year-old ${gen}${d.nombre ? ' named ' + d.nombre : ''}.`);
    if (face.length) out.push(`${P} ${has} ${list(face)}.`);
    if (eyes.length) out.push(`${Pp} eyes are ${eyes.join(', ')}, expressive and natural.`);
    if (acc.length) out.push(`${P} always wears ${list(acc)}.`);
    if (hair || hairStyle) out.push(`${Pp} hair is ${hair || 'natural'}${hairStyle ? ', styled as: ' + hairStyle.replace(/\.$/, '') : ''}.`);
    if (skin || det.length) out.push(`${Pp} skin is ${skin || 'natural'}${det.length ? ', with ' + list(det) : ''}, natural texture with visible pores, never plastic-looking.`);
    if (bodyP.length) out.push(`Body: ${list(bodyP)}, natural confident posture.`);
    if (vibe.length) out.push(`Overall vibe: ${list(vibe)}.`);
    out.push(`The image must look like ${style}, natural lighting${d.estilo === 'realista' || !d.estilo ? ', phone-camera quality' : ''}.`);
    return out.join(' ');
  }
  const promptOf = d => d.prompt || basePrompt(d);

  // ---------------------------------------------------------------- pasos del asistente
  const STEPS = [
    { id: 'rol', t: 'Rol', h: '¿Qué papel cumple tu influencer? Marca todos los que quieras.' },
    { id: 'nicho', t: 'Nicho', h: '¿De qué habla? Marca todos los que quieras.' },
    { id: 'nombre', t: 'Nombre y usuario', h: 'Cómo se llama y cómo la encuentran en redes.' },
    { id: 'edad', t: 'Edad y género', h: 'La energía que transmite: aspiracional o cercana.' },
    { id: 'cara', t: 'Forma de la cara', h: 'Elige la que más se parezca a la que imaginas.' },
    { id: 'ojos', t: 'Ojos', h: 'Su color (o uno exacto con las barras) y su forma.' },
    { id: 'boca', t: 'Labios y nariz', h: 'Dos detalles que cambian mucho una cara.' },
    { id: 'pelocolor', t: 'Color de pelo', h: 'Un color, uno exacto con las barras o una foto de referencia.' },
    { id: 'peinado', t: 'Peinado', h: 'Elige su peinado de tu biblioteca.' },
    { id: 'piel', t: 'Tono de piel', h: 'Elige su tono.' },
    { id: 'detalles', t: 'Detalles únicos', h: 'Opcional: lo que la hace reconocible.' },
    { id: 'cuerpo', t: 'Cuerpo', h: 'Su altura y su complexión.' },
    { id: 'curvas', t: 'Pecho y cadera', h: 'Así se verá en su ficha de cuerpo.' },
    { id: 'estilo', t: 'Estilo visual', h: 'Cómo se ve: realista, cartoon o su propio estilo.' },
    { id: 'pers', t: 'Personalidad', h: 'Cómo es. Marca todas las que quieras.' },
    { id: 'voz', t: 'Cómo habla', h: 'Su forma de hablar y una frase suya.' },
    { id: 'fin', t: 'Resumen', h: 'Revisa lo elegido, su prompt base y guárdalo.' },
  ];
  const STEPS_FOTOS = [{ id: 'fotos', t: 'Tus fotos', h: 'Suelta fotos de personas que te gusten: la IA saca sus rasgos en común.' }].concat(STEPS.filter(s => ['rol', 'nicho', 'nombre', 'edad', 'fin'].includes(s.id)));
  const STEPS_TENGO = [{ id: 'tficha', t: 'Su ficha 360', h: 'Sube la ficha de tu personaje. La IA la mira y rellena sus rasgos por ti.' }, { id: 'tdatos', t: 'Sus datos', h: 'Lo justo para crear imágenes con tu personaje. Todo se puede cambiar después.' }];
  const stepsOf = w => w.mode === 'fotos' ? STEPS_FOTOS : w.mode === 'tengo' ? STEPS_TENGO : STEPS;
  const DRAFT = 'am_pj_draft';
  function newWiz(mode, data) { pj.wiz = { mode, step: 0, d: Object.assign({ edad: 25, altura: 168, genero: 'fem', rol: [], nicho: [], pers: [], voz: [], pielDet: [], inspo: [] }, data || {}) }; saveDraft(); }
  function saveDraft() { try { if (pj.wiz) localStorage.setItem(DRAFT, JSON.stringify(Object.assign({}, pj.wiz, { d: Object.assign({}, pj.wiz.d, { foto: null, ficha: null, cuerpoUp: null, _err: null }) }))); else localStorage.removeItem(DRAFT); } catch (e) { try { localStorage.setItem(DRAFT, JSON.stringify(Object.assign({}, pj.wiz, { d: Object.assign({}, pj.wiz.d, { foto: null, ficha: null, cuerpoUp: null, inspo: [], _err: null }) }))); } catch (e2) {} } }
  function loadDraft() { try { const w = JSON.parse(localStorage.getItem(DRAFT) || 'null'); if (w && w.d) return w; } catch (e) {} return null; }
  const changed = d => { d.prompt = d.promptManual ? d.prompt : null; saveDraft(); updSide(); };

  // tarjetas: multi = true (sin límite) o número máximo; hide = ocultas (se conservan para personajes antiguos)
  function cards(key, d, field, { multi = 0, cls = '', only = null } = {}) {
    const pill = O[key].every(o => o[5] || !/^(img|svg|sw|body|bust|hip):/.test(o[1])) && !(pj.tarj && O[key].some(o => pj.tarj.has(key + '_' + o[0])));
    const box = el('div', 'pjcards ' + (pill ? 'pill ' : '') + cls); const vals = () => multi ? arr(d[field]) : d[field];
    O[key].filter(o => !o[5] && (!only || only.includes(o[0]))).forEach(([id, code, label, , warn]) => {
      const on = multi ? vals().includes(id) : vals() === id;
      const c = el('button', 'pjcard' + (on ? ' on' : '') + (warn ? ' warn' : ''), `<span class="pjvis">${vis(key, id, code)}</span><b>${label}</b>${warn ? '<small class="pjwarn">No recomendado<br>problemas de consistencia</small>' : ''}`);
      c.onclick = () => {
        if (multi) { const a = vals().slice(); const k = a.indexOf(id); if (k >= 0) a.splice(k, 1); else { if (multi !== true && a.length >= multi) a.shift(); a.push(id); } d[field] = a; }
        else d[field] = d[field] === id ? null : id;
        if (field === 'ojos') { delete d.ojosHex; delete d.ojosNombre; } if (field === 'peloColor') { delete d.peloHex; delete d.peloNombre; }
        changed(d); paintWiz();
      };
      box.appendChild(c);
    });
    return box;
  }
  const grp = (title, node, sub) => { const g = el('div', 'pjgrp'); g.appendChild(el('h4', '', title + (sub ? `<small>${sub}</small>` : ''))); if (node) g.appendChild(node); return g; };
  function input(d, field, ph, { area = false, type = 'text', err = false } = {}) { const i = el(area ? 'textarea' : 'input', 'pjin' + (err ? ' err' : '')); if (!area) i.type = type; i.placeholder = ph || ''; i.value = d[field] || ''; i.oninput = () => { d[field] = i.value; if (d._err === field && i.value.trim()) { d._err = null; i.classList.remove('err'); } changed(d); }; return i; }
  function slider(d, field, min, max, fmt) { const w = el('div', 'pjsl'); const r = document.createElement('input'); r.type = 'range'; r.min = min; r.max = max; r.value = d[field] || min; const v = el('b', '', fmt(r.value)); r.oninput = () => { d[field] = +r.value; v.textContent = fmt(r.value); changed(d); }; w.appendChild(r); w.appendChild(v); return w; }
  const shrink = (du, max = 1024) => new Promise(res => { const im = new Image(); im.onload = () => { const k = Math.min(1, max / Math.max(im.naturalWidth, im.naturalHeight)); const cv = document.createElement('canvas'); cv.width = Math.round(im.naturalWidth * k); cv.height = Math.round(im.naturalHeight * k); cv.getContext('2d').drawImage(im, 0, 0, cv.width, cv.height); res(cv.toDataURL('image/jpeg', 0.9)); }; im.onerror = () => res(du); im.src = du; });
  function upZone(cls, cur_, html, onData, max, onClear, over) { // subida a tamaño grande (una ficha no se reduce a 1024 como las fotos sueltas)
    const z = el('label', cls + (cur_ ? ' has' : ''), cur_ ? `<img src="${cur_}" alt="">${over || ''}` : html);
    const f = document.createElement('input'); f.type = 'file'; f.accept = 'image/*'; f.hidden = true; z.appendChild(f);
    const read = file => { if (!file || !/^image\//.test(file.type)) { toast('Eso no es una imagen'); return; } const r = new FileReader(); r.onload = async () => onData(await shrink(r.result, max)); r.readAsDataURL(file); };
    f.onchange = () => read(f.files[0]); z.ondragover = e => { e.preventDefault(); z.classList.add('over'); }; z.ondragleave = () => z.classList.remove('over');
    z.ondrop = async e => { e.preventDefault(); z.classList.remove('over'); const fl = [...(e.dataTransfer.files || [])].find(x => x.type.startsWith('image/')); if (fl) { read(fl); return; } let url = e.dataTransfer.getData('text/uri-list') || ''; const mm = (e.dataTransfer.getData('text/html') || '').match(/<img[^>]+src=["']([^"']+)["']/i); if (mm) url = mm[1]; if (!/^https?:/.test(url)) return; try { const j = await fetch('/api/fetch?url=' + encodeURIComponent(url)).then(r => r.json()); if (j.data) onData(await shrink(j.data, max)); } catch (x) { toast('No se pudo descargar esa imagen'); } };
    if (cur_ && onClear) { const x = el('button', 'pjtx', '×'); x.title = 'Quitar'; x.onclick = e => { e.preventDefault(); e.stopPropagation(); onClear(); }; z.appendChild(x); }
    return z;
  }
  const cropData = (du, box) => new Promise(res => { const im = new Image(); im.onload = () => { const [x0, y0, x1, y1] = box; const w = Math.max(8, Math.round((x1 - x0) * im.naturalWidth)), h = Math.max(8, Math.round((y1 - y0) * im.naturalHeight)); const cv = document.createElement('canvas'); cv.width = w; cv.height = h; cv.getContext('2d').drawImage(im, Math.round(x0 * im.naturalWidth), Math.round(y0 * im.naturalHeight), w, h, 0, 0, w, h); res(cv.toDataURL('image/jpeg', 0.92)); }; im.onerror = () => res(du); im.src = du; });
  const okBox = b => Array.isArray(b) && b.length === 4 && b.every(v => typeof v === 'number' && v >= 0 && v <= 1) && b[2] - b[0] > 0.12 && b[3] - b[1] > 0.12;
  const TIPOS_ACC = ['gafas', 'gafassol', 'pendientes', 'collar', 'reloj', 'gorra', 'otro'];
  function aplicarAnalisis(d, a) { // lo que ve la IA → los mismos campos que el creador desde cero
    ['genero', 'cara', 'ojos', 'ojosForma', 'labios', 'nariz', 'peloColor', 'piel', 'complexion', 'pecho', 'cadera', 'estilo'].forEach(k => { if (a[k] && opt(k, a[k])) d[k] = a[k]; });
    if (a.edad) d.edad = Math.max(18, Math.min(70, Math.round(+a.edad) || 25)); if (a.altura) d.altura = Math.max(145, Math.min(200, Math.round(+a.altura) || 168));
    if (a.peloNombre && !a.peloColor) d.peloNombre = a.peloNombre; if (Array.isArray(a.pielDet)) d.pielDet = a.pielDet.filter(x => opt('pielDet', x));
    if (a.peinado_en) d.peinado = { id: 'suyo', name: a.peinado_es || 'Su peinado', desc: a.peinado_en };
    d.accAuto = (Array.isArray(a.accesorios) ? a.accesorios : []).filter(x => x && x.nombre && x.desc).slice(0, 4).map(x => ({ tipo: TIPOS_ACC.includes(x.tipo) ? x.tipo : 'otro', nombre: String(x.nombre).slice(0, 40), desc: String(x.desc).slice(0, 160) }));
    d.layout = a.layout === '2x2' ? '2x2' : 'otro'; d.frontal = okBox(a.frontal) ? a.frontal : null; d.analisis = a.resumen || 'Ficha analizada'; d.prompt = null;
  }
  async function analizarFicha(d) { // no genera ninguna imagen: solo lee la ficha
    if (!LIVE) { d.analisis = ''; toast('Sin conexión con la API no se puede leer la ficha: rellena sus datos a mano'); return; }
    pj.analizando = performance.now(); paintWiz(); startTick(); let r;
    try { r = await fetch('/api/pj_analizar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ images: [await shrink(d.ficha, 1600)], modo: 'ficha' }) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
    pj.analizando = 0; if (!pj.wiz || pj.wiz.d !== d || !d.ficha) return;
    if (r && r.ok) { aplicarAnalisis(d, r.d || {}); toast('Ficha leída: revisa sus datos en el paso siguiente'); } else { d.analisis = ''; toast('No se pudo leer la ficha (' + (r ? r.error : 'sin respuesta') + '): rellena sus datos a mano'); }
    saveDraft(); paintWiz(); updSide();
  }
  function drop(label, onData, cur_, sub, multi) { // zona para arrastrar o elegir una foto (también desde otra web)
    const z = el('label', 'pjdrop' + (cur_ ? ' has' : ''), cur_ ? `<img src="${cur_}" alt="">` : `<span>＋</span><b>${label}</b><small>${sub || 'Arrastra aquí o haz clic'}</small>`);
    const f = document.createElement('input'); f.type = 'file'; f.accept = 'image/*'; f.multiple = !!multi; f.hidden = true; z.appendChild(f);
    const read = file => { if (!file || !/^image\//.test(file.type)) return; const r = new FileReader(); r.onload = async () => onData(await shrink(r.result)); r.readAsDataURL(file); };
    f.onchange = () => [...f.files].forEach(read); z.ondragover = e => { e.preventDefault(); z.classList.add('over'); }; z.ondragleave = () => z.classList.remove('over');
    z.ondrop = async e => { e.preventDefault(); z.classList.remove('over'); const fs = [...(e.dataTransfer.files || [])].filter(x => x.type.startsWith('image/')); if (fs.length) { fs.forEach(read); return; } let url = e.dataTransfer.getData('text/uri-list') || ''; const mm = (e.dataTransfer.getData('text/html') || '').match(/<img[^>]+src=["']([^"']+)["']/i); if (mm) url = mm[1]; if (!/^https?:/.test(url)) return; try { const j = await fetch('/api/fetch?url=' + encodeURIComponent(url)).then(r => r.json()); if (j.data) onData(await shrink(j.data)); } catch (x) { toast('No se pudo descargar esa imagen'); } };
    return z;
  }
  // selector de color propio (tono + luz), como el del Vestidor: se guarda el nombre y el hex del color
  function colorPick(d, k, sat, def) {
    const w = el('div', 'pjcolor'); const H = d[k + 'H'] != null ? d[k + 'H'] : def[0], L = d[k + 'L'] != null ? d[k + 'L'] : def[1];
    const name = (h, l) => l < 12 ? 'negro' : l > 90 ? 'blanco' : `${hueName(h)}${l < 26 ? ' muy oscuro' : l < 40 ? ' oscuro' : l > 76 ? ' muy claro' : l > 62 ? ' claro' : ''}`;
    const dot = el('span', 'pjcdot'); const nm = el('b', 'pjcname'); const hue = document.createElement('input'); hue.type = 'range'; hue.min = 0; hue.max = 360; hue.value = H; hue.className = 'hue';
    const lum = document.createElement('input'); lum.type = 'range'; lum.min = 4; lum.max = 94; lum.value = L; lum.className = 'lum';
    const upd = () => { const hex = hslHex(+hue.value, sat, +lum.value); dot.style.background = hex; nm.textContent = name(+hue.value, +lum.value); lum.style.background = `linear-gradient(90deg,#000,${hslHex(+hue.value, sat, 50)},#fff)`; return hex; };
    const on = !!d[k + 'Hex']; const use = el('button', 'btn' + (on ? '' : ' acc'), on ? '✓ Usando este color · quitar' : 'Usar este color');
    use.onclick = () => { if (on) { delete d[k + 'Hex']; delete d[k + 'Nombre']; } else { d[k + 'Hex'] = upd(); d[k + 'Nombre'] = name(+hue.value, +lum.value); d[k + 'H'] = +hue.value; d[k + 'L'] = +lum.value; if (k === 'ojos') d.ojos = null; if (k === 'pelo') d.peloColor = null; } changed(d); paintWiz(); };
    const live = () => { upd(); if (on) { d[k + 'Hex'] = upd(); d[k + 'Nombre'] = name(+hue.value, +lum.value); d[k + 'H'] = +hue.value; d[k + 'L'] = +lum.value; changed(d); } };
    hue.oninput = live; lum.oninput = live; upd();
    const sl = el('div', 'pjcsl'); sl.appendChild(el('small', '', 'Tono')); sl.appendChild(hue); sl.appendChild(el('small', '', 'Luz')); sl.appendChild(lum);
    const row = el('div', 'pjcrow' + (on ? ' on' : '')); row.appendChild(dot); const mid = el('div', 'pjcmid'); mid.appendChild(sl); row.appendChild(mid); const rt = el('div', 'pjcright'); rt.appendChild(nm); rt.appendChild(use); row.appendChild(rt); w.appendChild(row); return w;
  }
  // recortar una imagen (para señalar un detalle concreto)
  function cropModal(src, onSave) {
    const cr = { z: 1, x: 0.5, y: 0.5 }; let m0 = $('#pjcrop'); if (m0) m0.remove(); m0 = el('div', 'fxm'); m0.id = 'pjcrop'; document.body.appendChild(m0); const close = () => m0.remove(); m0.onclick = e => { if (e.target === m0) close(); };
    const box = el('div', 'fxbox accbox avbox'); const media = el('div', 'fxmedia accmedia'); const vp = el('div', 'accvp'); const im = document.createElement('img'); im.src = src; im.draggable = false; vp.appendChild(im); vp.appendChild(el('div', 'accvpfr')); media.appendChild(vp);
    const place = () => { const W = vp.clientWidth, nw = im.naturalWidth, nh = im.naturalHeight; if (!nw) return; const sc = W / Math.min(nw, nh) * cr.z; im.style.width = nw * sc + 'px'; im.style.height = nh * sc + 'px'; im.style.left = (W / 2 - cr.x * nw * sc) + 'px'; im.style.top = (W / 2 - cr.y * nh * sc) + 'px'; };
    im.onload = place; let drag = null; vp.onmousedown = e => { drag = { x: e.clientX, y: e.clientY, cx: cr.x, cy: cr.y }; e.preventDefault(); };
    window.onmousemove = e => { if (!drag) return; const sc = vp.clientWidth / Math.min(im.naturalWidth, im.naturalHeight) * cr.z; cr.x = Math.min(1, Math.max(0, drag.cx - (e.clientX - drag.x) / (im.naturalWidth * sc))); cr.y = Math.min(1, Math.max(0, drag.cy - (e.clientY - drag.y) / (im.naturalHeight * sc))); place(); }; window.onmouseup = () => { drag = null; };
    const zr = document.createElement('input'); zr.type = 'range'; zr.min = 1; zr.max = 8; zr.step = 0.02; zr.value = 1; zr.className = 'acczoom'; zr.oninput = () => { cr.z = +zr.value; place(); }; vp.onwheel = e => { e.preventDefault(); cr.z = Math.min(8, Math.max(1, cr.z * (e.deltaY < 0 ? 1.06 : 0.94))); zr.value = cr.z; place(); };
    const tools = el('div', 'acctools'); tools.appendChild(el('small', '', 'Acerca y centra el detalle: la IA solo verá lo que quede dentro del marco')); tools.appendChild(zr); media.appendChild(tools); box.appendChild(media);
    const side = el('div', 'fxside accside'); const acts = el('div', 'fxacts accacts top'); const sv = el('button', 'btn acc', '✓ Guardar el detalle'); sv.onclick = () => { const S = 640, cv = document.createElement('canvas'); cv.width = cv.height = S; const nw = im.naturalWidth, nh = im.naturalHeight, sd = Math.min(nw, nh) / cr.z; cv.getContext('2d').drawImage(im, cr.x * nw - sd / 2, cr.y * nh - sd / 2, sd, sd, 0, 0, S, S); onSave(cv.toDataURL('image/jpeg', 0.9)); close(); };
    const cn = el('button', 'btn', 'Cancelar'); cn.onclick = close; acts.appendChild(sv); acts.appendChild(cn); side.appendChild(acts);
    side.appendChild(el('div', 'fxtitle', '<small>Detalle único</small><b>Señala el detalle</b><p>Haz zoom sobre el detalle concreto (un lunar, una marca, un piercing…) para que la IA sepa exactamente a qué te refieres.</p>'));
    box.appendChild(side); m0.appendChild(box);
  }
  // ir a una sección de la izquierda (Peinados, Cartoon) a elegir y volver al paso
  function pickFrom(tab, label, done) {
    const w = pj.wiz; const back = () => { pj.wiz = w; if (window.PJ) PJ.sel = 'aria'; window.pjScrollTop = false; setTab('perfil'); };
    if (!window.startPick) { toast('Actualiza la página'); return; }
    startPick(tab, { label, done: it => { done(it); changed(w.d); back(); }, cancel: back });
  }
  const imgOf = it => (it.files && (it.files.main || it.files.thumb)) || it.ficha || it.thumb || it.card || '';

  function otro(d, field, ph) { const i = input(d, field, ph); const g = el('div', 'pjotro'); g.appendChild(el('small', 'pjk', 'Otro')); g.appendChild(i); return g; }
  function stepBody(id, d) {
    const b = el('div', 'pjstep'); const ARIA_BIO = (C.perfil && C.perfil.bio) || 'Digital creator. ✨ Crea conmigo tu Influencer IA.';
    if (id === 'tficha') {
      const an = pj.analizando;
      const big = upZone('pjtbig', d.ficha, '<span>＋</span><b>Suelta aquí su ficha 360</b><small>la imagen con sus vistas: de frente, de perfil, tres cuartos y de espaldas<br>o haz clic para elegirla</small>',
        v => { d.ficha = v; d.analisis = null; changed(d); paintWiz(); analizarFicha(d); }, 2400, an ? null : () => { d.ficha = null; d.analisis = null; d.accAuto = []; paintWiz(); },
        an ? `<span class="pjtbusy"><i class="spin"></i><b>La IA está mirando su ficha</b><small data-t0="${an}">${Math.round((performance.now() - an) / 1000)} s</small></span>` : '');
      const mini = (field, title, sub, html) => { const g = grp(title, upZone('pjtmini', d[field], html, v => { d[field] = v; saveDraft(); paintWiz(); }, 2000, () => { d[field] = null; paintWiz(); }), sub); return g; };
      const col = el('div', 'pjtcol');
      col.appendChild(mini('cuerpoUp', 'Su cuerpo completo', 'opcional', '<span>＋</span><b>Ficha de cuerpo</b><small>si ya la tienes</small>'));
      col.appendChild(mini('foto', 'Una foto de su cara', 'opcional', '<span>＋</span><b>Foto de frente</b><small>solo si tu ficha no es de cuatro vistas</small>'));
      const row = el('div', 'pjtengo'); row.appendChild(big); row.appendChild(col); b.appendChild(row);
      b.appendChild(el('p', 'pjnote pjtnote', an ? 'Unos segundos: está sacando su edad, sus rasgos y lo que lleva siempre.' : d.analisis ? '✓ ' + esc(d.analisis) : d.ficha ? 'Ficha cargada. Sus datos los rellenas en el paso siguiente.' : 'Al soltarla, la IA lee la ficha y rellena su edad, sus rasgos y lo que lleva siempre (gafas, pendientes…). No se genera ninguna imagen.'));
    }
    if (id === 'tdatos') {
      const g = el('div', 'pjtd'); const c1 = el('div', 'pjtdcol');
      c1.appendChild(grp('Nombre', input(d, 'nombre', 'Ej.: Aria Cruz', { err: d._err === 'nombre' }), d._err === 'nombre' ? '⚠ ponle un nombre para poder guardar' : ''));
      c1.appendChild(grp('Usuario', input(d, 'usuario', '@soy_aria_cruz'), 'opcional'));
      c1.appendChild(grp('Edad aparente', slider(d, 'edad', 18, 70, v => v + ' años')));
      c1.appendChild(grp('Género', cards('genero', d, 'genero')));
      g.appendChild(c1);
      const c2 = el('div', 'pjtdcol'); c2.appendChild(el('div', 'pjtprev', d.ficha ? `<img src="${d.ficha}" alt="">` : '<i>Falta su ficha 360: vuelve al paso 1</i>'));
      const rs = [d.ojosNombre ? 'Ojos ' + d.ojosNombre : es('ojos', d.ojos) && 'Ojos ' + es('ojos', d.ojos).toLowerCase(), d.peloNombre ? 'Pelo ' + d.peloNombre : es('peloColor', d.peloColor) && 'Pelo ' + es('peloColor', d.peloColor).toLowerCase(), d.peinado && d.peinado.name, es('piel', d.piel) && 'Piel ' + es('piel', d.piel).toLowerCase(), es('complexion', d.complexion), d.altura && (d.altura / 100).toFixed(2).replace('.', ',') + ' m'].filter(Boolean);
      const ch = el('div', 'pc-chips'); if (pj.analizando) ch.appendChild(el('small', 'pjnote', '⏳ La IA sigue leyendo su ficha…')); else if (rs.length && d.analisis != null) rs.forEach(x => ch.appendChild(el('span', '', esc(x)))); else ch.appendChild(el('small', 'pjnote', 'Sin rasgos todavía: los puedes rellenar después en «Editar sus datos».'));
      c2.appendChild(grp('Así se ve', ch, 'lo que ha leído la IA en su ficha'));
      if (arr(d.accAuto).length) { const ac = el('div', 'pc-chips edchips'); d.accAuto.forEach((x, i) => { const sp = el('span', '', esc(x.nombre)); const q = el('button', 'chx', '×'); q.title = 'No lo lleva siempre'; q.onclick = () => { d.accAuto.splice(i, 1); saveDraft(); paintWiz(); }; sp.appendChild(q); ac.appendChild(sp); }); c2.appendChild(grp('Lo que lleva siempre', ac, 'se guardan como sus complementos fijos')); }
      g.appendChild(c2); b.appendChild(g);
      const ck = el('label', 'pjtck' + (d._err === 'okIA' ? ' err' : ''), '<input type="checkbox"><span>Es un personaje creado con IA o soy yo: <b>no es la imagen de otra persona real</b>.</span>'); const cb = ck.querySelector('input'); cb.checked = !!d.okIA; cb.onchange = () => { d.okIA = cb.checked; if (d.okIA && d._err === 'okIA') { d._err = null; ck.classList.remove('err'); } saveDraft(); }; b.appendChild(ck);
    }
    if (id === 'fotos') {
      const g = el('div', 'pjinspo'); arr(d.inspo).forEach((src, i) => { const c = el('div', 'pjinsp', `<img src="${src}" alt="">`); const x = el('button', 'pjx', '×'); x.onclick = () => { d.inspo.splice(i, 1); saveDraft(); paintWiz(); }; c.appendChild(x); g.appendChild(c); });
      if (arr(d.inspo).length < 8) g.appendChild(drop('Suelta aquí sus fotos', v => { d.inspo = arr(d.inspo).concat([v]).slice(0, 8); saveDraft(); paintWiz(); }, null, 'hasta 8 · del ordenador o de otra web', true));
      b.appendChild(grp('Fotos de personas que te gusten', g, 'la IA mira qué tienen en común (cara, ojos, pelo, piel, cuerpo) y rellena todos los pasos por ti'));
      const an = el('button', 'btn acc pr', pj.analizando ? '⏳ Analizando las fotos…' : d.resumen ? '↻ Volver a analizar' : '✨ Analizar las fotos'); an.disabled = pj.analizando || arr(d.inspo).length < 1;
      an.onclick = async () => { pj.analizando = true; paintWiz(); let r; try { r = await fetch('/api/pj_analizar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ images: d.inspo }) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; } pj.analizando = false;
        if (r && r.ok) { const a = r.d || {}; ['genero', 'cara', 'ojos', 'ojosForma', 'labios', 'nariz', 'peloColor', 'piel', 'complexion', 'pecho', 'cadera', 'estilo'].forEach(k => { if (a[k] && opt(k, a[k])) d[k] = a[k]; }); if (a.edad) d.edad = Math.max(18, Math.min(70, Math.round(+a.edad))); if (a.altura) d.altura = Math.max(145, Math.min(200, Math.round(+a.altura)));
          if (a.peloNombre && !a.peloColor) d.peloNombre = a.peloNombre; if (Array.isArray(a.pielDet)) d.pielDet = a.pielDet.filter(x => opt('pielDet', x)); d.resumen = a.resumen || ''; d.prompt = null; toast('Rasgos rellenados: revisa el resumen al final'); }
        else toast('No se pudo analizar: ' + (r ? r.error : 'sin respuesta')); saveDraft(); paintWiz(); updSide(); };
      const ac = el('div', 'pjacts'); ac.appendChild(an); if (d.resumen) ac.appendChild(el('span', 'pjnote', '✓ ' + esc(d.resumen))); b.appendChild(ac);
      b.appendChild(el('p', 'pjnote', 'Después solo te pregunta el rol, el nombre y la edad. Todo lo demás lo puedes revisar en el resumen, y al guardarlo empiezas a buscar su cara en rejillas de 3×3 inspiradas en estas fotos.'));
    }
    if (id === 'rol') { b.appendChild(grp('Rol', cards('rol', d, 'rol', { multi: true }), 'puedes marcar varios')); b.appendChild(otro(d, 'rolTxt', 'Ej.: presentadora de noticias de IA')); }
    if (id === 'nicho') { b.appendChild(grp('Nicho', cards('nicho', d, 'nicho', { multi: true }), 'de qué habla · puedes marcar varios')); b.appendChild(otro(d, 'nichoTxt', 'Ej.: enseña a crear influencers IA sin complicaciones')); }
    if (id === 'nombre') { const g = el('div', 'pjform'); g.appendChild(grp('Nombre', input(d, 'nombre', 'Ej.: Aria Cruz', { err: d._err === 'nombre' }), d._err === 'nombre' ? '⚠ ponle un nombre para poder guardarla' : '')); g.appendChild(grp('Usuario', input(d, 'usuario', '@soy_aria_cruz'))); g.appendChild(grp('Bio', input(d, 'bio', ARIA_BIO, { area: true }), 'la presentación de su perfil de Instagram')); b.appendChild(g); }
    if (id === 'edad') { b.appendChild(grp('Edad aparente', slider(d, 'edad', 18, 70, v => v + ' años'))); b.appendChild(grp('Género', cards('genero', d, 'genero'))); b.appendChild(otro(d, 'generoTxt', 'Escribe su género si no está')); }
    if (id === 'cara') b.appendChild(grp('Forma de la cara', cards('cara', d, 'cara', { cls: 'one' })));
    if (id === 'ojos') { b.appendChild(grp('Color', cards('ojos', d, 'ojos', { cls: 'row8' }))); b.appendChild(grp('Otro color', colorPick(d, 'ojos', 55, [120, 40]), 'el tono exacto con las barras')); b.appendChild(grp('Forma', cards('ojosForma', d, 'ojosForma', { cls: 'row4' }))); }
    if (id === 'boca') { b.appendChild(grp('Labios', cards('labios', d, 'labios', { cls: 'two zl' }))); b.appendChild(grp('Nariz', cards('nariz', d, 'nariz', { cls: 'two zn' }))); }
    if (id === 'pelocolor') {
      b.appendChild(grp('Color', cards('peloColor', d, 'peloColor', { cls: 'row7' })));
      const r = el('div', 'pjrow pjrow2'); r.appendChild(grp('Otro color', colorPick(d, 'pelo', 55, [30, 30]), 'el tono exacto con las barras'));
      const rf = el('div', 'pjrefmini'); if (d.peloRef) { const c = el('div', 'pjinsp', `<img src="${d.peloRef}" alt="">`); const x = el('button', 'pjx', '×'); x.onclick = () => { d.peloRef = null; changed(d); paintWiz(); }; c.appendChild(x); rf.appendChild(c); } else rf.appendChild(drop('Foto de referencia', v => { d.peloRef = v; changed(d); paintWiz(); }, null, 'mechas, un mechón blanco, rayas…'));
      r.appendChild(grp('¿Un color muy concreto?', rf)); b.appendChild(r);
    }
    if (id === 'peinado') b.appendChild(hairGallery(d));
    if (id === 'piel') b.appendChild(grp('Tono', cards('piel', d, 'piel', { cls: 'one' })));
    if (id === 'detalles') {
      b.appendChild(grp('Detalles únicos', cards('pielDet', d, 'pielDet', { multi: true }), 'puedes marcar varios'));
      const r = el('div', 'pjrow'); if (d.detImg) { const c = el('div', 'pjinsp big', `<img src="${d.detImg}" alt="">`); const x = el('button', 'pjx', '×'); x.onclick = () => { d.detImg = null; changed(d); paintWiz(); }; c.appendChild(x); r.appendChild(c); }
      else r.appendChild(drop('Adjunta tu imagen', v => cropModal(v, cr => { d.detImg = cr; changed(d); paintWiz(); }), null, 'después haces zoom sobre el detalle'));
      const tx = input(d, 'detTxt', 'Descríbelo (mejor en inglés) · ej.: a tiny heart-shaped mole under the left eye', { area: true }); const col = el('div', 'stack'); col.style.flex = '1'; col.appendChild(tx); r.appendChild(col);
      b.appendChild(grp('Un detalle concreto', r, 'sube una foto, señala el detalle con el zoom y descríbelo'));
    }
    if (id === 'cuerpo') { b.appendChild(grp('Altura', slider(d, 'altura', 145, 200, v => (v / 100).toFixed(2).replace('.', ',') + ' m'))); b.appendChild(grp('Complexión', cards('complexion', d, 'complexion', { cls: 'row7 body' }))); }
    if (id === 'curvas') { if (d.genero !== 'masc') b.appendChild(grp('Pecho', cards('pecho', d, 'pecho', { cls: 'two body' }))); b.appendChild(grp('Cadera y glúteos', cards('cadera', d, 'cadera', { cls: 'two body' }))); }
    if (id === 'estilo') {
      const box = el('div', 'pjcards h169'); const on = k => d.estilo === k;
      const real = el('button', 'pjcard' + (on('realista') ? ' on' : ''), `<span class="pjvis"><img src="assets/perfil/podcast.jpg" alt=""></span><b>Realista</b>`); real.onclick = () => { d.estilo = on('realista') ? null : 'realista'; changed(d); paintWiz(); }; box.appendChild(real);
      const ct = el('button', 'pjcard' + (on('cartoon') ? ' on' : ''), `<span class="pjvis"><img src="${(d.cartoon && d.cartoon.img) || 'assets/cartoon/caricature-portrait-style_t.jpg'}" alt=""></span><b>${d.cartoon ? 'Cartoon · ' + esc(d.cartoon.name) : 'Cartoon'}</b><em class="pjmore">${d.cartoon ? 'Cambiar el estilo' : 'Ver más estilos'}</em>`); ct.onclick = () => elegirCartoon(d); box.appendChild(ct);
      const pr = d.estiloRef ? el('div', 'pjcard' + (on('propio') ? ' on' : ''), `<span class="pjvis"><img src="${d.estiloRef}" alt=""></span><b>Su propio estilo</b>`) : el('div', 'pjcard pjplus', '');
      if (d.estiloRef) { pr.onclick = () => { d.estilo = on('propio') ? null : 'propio'; changed(d); paintWiz(); }; const x = el('button', 'pjx', '×'); x.onclick = e => { e.stopPropagation(); d.estiloRef = null; if (on('propio')) d.estilo = null; changed(d); paintWiz(); }; pr.appendChild(x); }
      else pr.appendChild(drop('Su propio estilo', v => { d.estiloRef = v; d.estilo = 'propio'; changed(d); paintWiz(); }, null, 'suelta una imagen con el estilo que buscas'));
      box.appendChild(pr); b.appendChild(grp('Estilo visual', box, 'realista, uno de tus estilos Cartoon o una imagen tuya'));
      b.appendChild(el('p', 'pjnote', '👓 Los accesorios que lleva siempre (gafas, pendientes, su móvil…) se añaden después, con su foto, en la pestaña «Complementos» de su perfil.'));
    }
    if (id === 'pers') { b.appendChild(grp('Personalidad', cards('pers', d, 'pers', { multi: true }), 'todas las que quieras')); b.appendChild(grp('Con tus palabras', input(d, 'persTxt', 'Si no está en los ejemplos, escríbela aquí', { area: true }))); }
    if (id === 'voz') { b.appendChild(grp('Cómo habla', cards('voz', d, 'voz', { multi: true }), 'todas las que quieras')); b.appendChild(grp('Una frase suya', input(d, 'frase', 'Ej.: «¡Chao!» al final de cada vídeo'))); }
    if (id === 'fin') {
      const acts = el('div', 'pjacts pjsavetop'); const sv = el('button', 'btn acc', pj.wiz.editId ? '✓ Guardar cambios' : '✓ Guardar y crear su imagen'); sv.onclick = () => savePersona(); acts.appendChild(sv);
      acts.appendChild(el('span', 'pjnote', pj.wiz.editId ? 'Se guardan sus datos y su prompt base.' : 'Después buscas su cara en rejillas de 3×3, eliges la definitiva y se crean sus fichas.')); b.appendChild(acts);
      const sm = el('div', 'pjcards pjsum'); const rm = (field, v) => { if (Array.isArray(d[field])) d[field] = d[field].filter(x => x !== v); else d[field] = null; changed(d); paintWiz(); };
      const put = (html, field, v) => { const c = el('div', 'pjcard on', html); const x = el('button', 'pjx', '×'); x.title = 'Quitar'; x.onclick = () => rm(field, v); c.appendChild(x); sm.appendChild(c); };
      const one = (k, v, t) => { const o = opt(k, v); if (o) put(`<span class="pjvis">${vis(k, v, o[1])}</span><b>${t ? t + ': ' : ''}${o[2]}</b>`, k, v); };
      const img = (src, t, field) => put(`<span class="pjvis"><img src="${src}" alt=""></span><b>${esc(t)}</b>`, field);
      const col = (hex, t, field) => { const c = el('div', 'pjcard on', `<span class="pjvis"><span class="pjsw" style="background:${hex}"></span></span><b>${esc(t)}</b>`); const x = el('button', 'pjx', '×'); x.onclick = () => { delete d[field + 'Hex']; delete d[field + 'Nombre']; changed(d); paintWiz(); }; c.appendChild(x); sm.appendChild(c); };
      one('genero', d.genero); one('cara', d.cara, 'Cara'); one('ojos', d.ojos, 'Ojos'); if (d.ojosHex) col(d.ojosHex, 'Ojos: ' + d.ojosNombre, 'ojos'); one('ojosForma', d.ojosForma, 'Ojos'); one('labios', d.labios, 'Labios'); one('nariz', d.nariz, 'Nariz');
      one('peloColor', d.peloColor, 'Pelo'); if (d.peloHex) col(d.peloHex, 'Pelo: ' + d.peloNombre, 'pelo'); if (d.peloRef) img(d.peloRef, 'Color de pelo de la foto', 'peloRef'); if (d.peinado) img(d.peinado.img || '', d.peinado.name, 'peinado');
      one('piel', d.piel, 'Piel'); arr(d.pielDet).forEach(x => one('pielDet', x)); if (d.detImg) img(d.detImg, 'Su detalle', 'detImg');
      one('complexion', d.complexion); if (d.genero !== 'masc') one('pecho', d.pecho, 'Pecho'); one('cadera', d.cadera, 'Cadera');
      if (d.estilo === 'cartoon' && d.cartoon) img(d.cartoon.img, 'Cartoon: ' + d.cartoon.name, 'cartoon'); else if (d.estilo === 'propio' && d.estiloRef) img(d.estiloRef, 'Su propio estilo', 'estiloRef'); else one('estilo', d.estilo);
      arr(d.rol).forEach(x => one('rol', x)); arr(d.nicho).forEach(x => one('nicho', x)); arr(d.pers).forEach(x => one('pers', x)); arr(d.voz).forEach(x => one('voz', x, 'Habla'));
      if (sm.children.length) b.appendChild(grp(d.nombre ? `Así es ${d.nombre}` : 'Lo que has elegido', sm, [d.edad && d.edad + ' años', d.altura && (d.altura / 100).toFixed(2).replace('.', ',') + ' m', d.usuario].filter(Boolean).join(' · ')));
      const ta = el('textarea', 'pjin pjprompt'); ta.value = promptOf(d); const fit = () => { ta.style.setProperty('height', 'auto', 'important'); ta.style.setProperty('height', (ta.scrollHeight + 4) + 'px', 'important'); };
      ta.oninput = () => { const auto = ta.value.trim() === basePrompt(d).trim(); d.prompt = auto ? null : ta.value; d.promptManual = !auto; saveDraft(); fit(); rs.style.display = d.promptManual ? '' : 'none'; }; setTimeout(fit, 0);
      const rs = el('span', 'lnk', '↺ volver al automático'); rs.style.display = d.promptManual ? '' : 'none'; rs.onclick = () => { d.prompt = null; d.promptManual = false; ta.value = basePrompt(d); saveDraft(); fit(); rs.style.display = 'none'; };
      const g = grp('Prompt base', ta, 'se escribe solo con lo que eliges (si quitas algo arriba, cambia solo) · puedes editarlo a mano; entonces ya no cambia hasta que pulses «volver al automático»'); g.querySelector('h4').appendChild(rs); g.classList.add('pjpromptg'); b.appendChild(g);
    }
    return b;
  }
  function hairGallery(d) {
    const all = (TABS.hair.items || []).filter(i => !i.group); const tags = [...new Set(all.flatMap(i => i.tags || []))];
    const tag = pj.hairTag || null; const L = tag ? all.filter(i => (i.tags || []).includes(tag)) : all; const per = 8; const pages = Math.max(1, Math.ceil(L.length / per)); const pg = Math.min(pj.hairPage || 0, pages - 1);
    const w = el('div', 'pjhairg'); const top = el('div', 'pjhairtop'); const ch = el('div', 'pjcards pill');
    [[null, 'Todos']].concat(tags.map(t => [t, t])).forEach(([k, n]) => { const b = el('button', 'pjcard' + (tag === k ? ' on' : ''), `<b>${esc(n)}</b>`); b.onclick = () => { pj.hairTag = k; pj.hairPage = 0; paintWiz(); }; ch.appendChild(b); }); top.appendChild(ch);
    if (d.peinado) { const c = el('div', 'pjhairsel', `<img src="${d.peinado.img || ''}" alt=""><b>✓ ${esc(d.peinado.name)}</b>`); const x = el('button', 'pjx', '×'); x.title = 'Quitar'; x.onclick = () => { d.peinado = null; changed(d); paintWiz(); }; c.appendChild(x); top.appendChild(c); }
    w.appendChild(top);
    const g = el('div', 'pjcards h169 pjhairgrid'); L.slice(pg * per, pg * per + per).forEach(it => { const on = d.peinado && d.peinado.id === it.id; const c = el('button', 'pjcard' + (on ? ' on' : ''), `<span class="pjvis"><img src="${it.files.main}" alt="" loading="lazy"></span><b>${esc(it.name)}</b>`); c.onclick = () => { d.peinado = on ? null : { id: it.id, name: it.name, desc: it.desc || '', img: it.files.main }; changed(d); paintWiz(); }; c.ondblclick = () => lightbox(it.files.main, it.name); g.appendChild(c); }); w.appendChild(g);
    const nav = el('div', 'pjhairnav'); const pv = el('button', 'btn', '‹'); pv.disabled = pg === 0; pv.onclick = () => { pj.hairPage = pg - 1; paintWiz(); }; const nx = el('button', 'btn', '›'); nx.disabled = pg >= pages - 1; nx.onclick = () => { pj.hairPage = pg + 1; paintWiz(); };
    nav.appendChild(pv); nav.appendChild(el('small', '', `${pg + 1} de ${pages} · ${L.length} peinados · doble clic para verlo en grande`)); nav.appendChild(nx); w.appendChild(nav); return w;
  }
  function elegirPeinado(d) { pickFrom('hair', 'tu personaje nuevo', it => { d.peinado = { id: it.id, name: it.name, desc: it.desc || '', img: imgOf(it) }; toast(`Peinado «${it.name}» añadido`); }); }
  function elegirCartoon(d) { pickFrom('cartoon', 'el estilo de tu personaje', it => { d.estilo = 'cartoon'; d.cartoon = { id: it.id, name: it.name, desc: it.desc || '', img: (it.files && (it.files.thumb || it.files.main)) || imgOf(it) }; toast(`Estilo «${it.name}» elegido`); }); }

  // ---------------------------------------------------------------- guardar
  async function savePersona() {
    const w = pj.wiz, d = w.d; const S = stepsOf(w);
    if (!(d.nombre || '').trim()) { d._err = 'nombre'; toast('Ponle un nombre antes de guardar'); w.step = Math.max(0, S.findIndex(s => s.id === 'nombre' || s.id === 'tdatos')); paintWiz(); updSide(); setTimeout(() => { const i = document.querySelector('.pjin.err'); if (i) { i.focus(); i.scrollIntoView({ block: 'center' }); } }, 60); return; }
    const tengo = w.mode === 'tengo' && !w.editId;
    if (tengo && !d.ficha) { toast('Falta su ficha 360'); w.step = 0; paintWiz(); updSide(); return; }
    if (tengo && !d.okIA) { d._err = 'okIA'; toast('Marca la casilla de abajo para poder guardar'); paintWiz(); return; }
    if (tengo && pj.analizando) { toast('Un momento: la IA está terminando de leer su ficha'); return; }
    const old = w.editId ? pj.list.find(p => p.id === w.editId) : null;
    const p = Object.assign({}, old || {}, d, { id: w.editId || undefined, prompt: promptOf(d), promptEditado: !!d.promptManual, modo: old ? (old.modo || w.mode) : w.mode }); ['foto', 'ficha', '_err', 'inspo', 'peloRef', 'detImg', 'estiloRef', 'cuerpoUp', 'analisis', 'accAuto', 'okIA', 'frontal', 'layout'].forEach(k => delete p[k]);
    ['foto', 'ficha360', 'retrato', 'avatar', 'vista_frente', 'vista_perfil', 'vista_tres', 'vista_espalda', 'vistasOk', 'cuerpo', 'combo', 'explora', 'inspo'].forEach(k => { if (old && old[k]) p[k] = old[k]; });
    const files = {}; if (d.foto) files.foto = d.foto; if (d.ficha) files.ficha360 = d.ficha;
    if (tengo) { if (!d.foto) files.foto = await cropData(d.ficha, d.layout === 'otro' ? (d.frontal || [0, 0, 1, 1]) : [0, 0, 0.5, 0.5]); if (d.cuerpoUp) files.cuerpo = d.cuerpoUp; } // su foto de frente = la vista frontal de su ficha
    ['peloRef', 'detImg', 'estiloRef'].forEach(k => { if (isData(d[k])) files[k] = d[k]; else if (d[k]) p[k] = d[k]; });
    arr(d.inspo).forEach((v, i) => { if (isData(v)) files['inspo_' + (i + 1)] = v; });
    let r; try { r = await fetch('/api/personaje', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ p, files }) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
    if (!r || !r.ok) { toast('No se pudo guardar: ' + (r ? r.error : 'sin respuesta')); return; }
    if (tengo && arr(d.accAuto).length) { // lo que lleva siempre pasa a ser sus complementos fijos (descritos; luego puede añadirles foto)
      const L = d.accAuto.map((x, i) => ({ id: x.tipo + '-' + Date.now().toString(36) + i, nombre: x.nombre, tipo: x.tipo, regla: 'siempre', modo: 'prompt', desc: x.desc }));
      try { const r2 = await fetch('/api/complementos', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ owner: r.p.id, list: L, files: {} }) }).then(x => x.json()); if (r2 && r2.ok) r.p.complementos = r2.list; } catch (e) {} }
    const k = pj.list.findIndex(x => x.id === r.p.id); if (k >= 0) pj.list[k] = r.p; else pj.list.push(r.p);
    syncChars(); pj.sel = r.p.id; pj.tabBy[r.p.id] = 'ficha'; pj.wiz = null; saveDraft(); toast(tengo ? `«${r.p.nombre}» ya está en ARIA STUDIO` : w.editId ? 'Cambios guardados' : `«${r.p.nombre}» guardada. Ahora, a por su cara.`); window.pjScrollTop = true; renderProfile(); renderSide();
  }
  async function persist_(p, extra) { const r = await fetch('/api/personaje', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(Object.assign({ p }, extra || {})) }).then(x => x.json()).catch(e => ({ error: String(e) })); if (r && r.ok) { const k = pj.list.findIndex(x => x.id === r.p.id); if (k >= 0) pj.list[k] = r.p; syncChars(); } return r; }

  // ---------------------------------------------------------------- crear su imagen: 3×3 → definitiva → 4 vistas → cuerpo → ficha principal
  const MKEY = 'am_model_pj'; const pjModel = () => { let k = pj.model; if (!k) { try { k = localStorage.getItem(MKEY); } catch (e) {} } return MODELS.find(x => x.key === k) || MODELS.find(x => x.key === 'seedream') || curModel(); };
  const modelFor = n => { const m = pjModel(); return n > m.refs ? (window.fitModel && fitModel(n)) || m : m; };
  const seedream = () => MODELS.find(x => x.key === 'seedream') || curModel();
  const clean = f => (f || '').split('?')[0];
  const CELL = n => { const i = n - 1, c = i % 3, r = Math.floor(i / 3); return [c / 3, r / 3, (c + 1) / 3, (r + 1) / 3]; };
  function refsExtra(p, start) { // referencias propias del usuario (color de pelo, detalle, estilo propio). Peinados y estilos de la biblioteca salen con la cara de Aria: van en texto
    const imgs = [], txt = []; let n = start;
    if (p.peloRef) { imgs.push({ path: clean(p.peloRef) }); txt.push(`Hair color exactly as in @Image${n++} (only the hair color).`); }
    if (p.detImg) { imgs.push({ path: clean(p.detImg) }); txt.push(`Unique detail exactly as in @Image${n++}${p.detTxt ? ' (' + p.detTxt + ')' : ''}.`); }
    if (p.estilo === 'propio' && p.estiloRef) { imgs.push({ path: clean(p.estiloRef) }); txt.push(`Render everything in exactly the visual style of @Image${n++} (only its style, never the person in it).`); }
    if (p.estilo === 'cartoon' && p.cartoon) txt.push(`Render everything as ${cartoonStyle(p.cartoon)}.`);
    return { imgs, txt: txt.join(' ') };
  }
  function cartoonStyle(c) { const d = c.desc || ''; const m = d.match(/into (?:an? )?(.+?)(?:,| keep)/i); const det = ((d.split(/glasses,\s*/i)[1] || '').replace(/,?\s*no logos.*$/i, '')).trim(); return `a ${m ? m[1] : c.name + ' style'}${det ? ' (' + det + ')' : ''}`; }
  const who = p => p.genero === 'masc' ? 'men' : (p.genero === 'fem' || !p.genero) ? 'women' : 'people';
  // cada celda, una cara distinta: si no se le dice, el modelo cambia el color de pelo y repite la misma chica
  const NOMBRES = { women: ['Anna', 'Chloe', 'Sofia', 'Maya', 'Lena', 'Iris', 'Nora', 'Elena', 'Zoe'], men: ['Leo', 'Adam', 'Marco', 'Noah', 'Luca', 'Ivan', 'Hugo', 'Daniel', 'Theo'], people: ['Alex', 'Sam', 'Robin', 'Kai', 'Jules', 'Noa', 'Sasha', 'Eden', 'River'] };
  const CASTING = ['softer rounder cheeks and thick straight eyebrows', 'high defined cheekbones and thin arched eyebrows', 'a slightly longer face and a straight nose bridge', 'wider-set eyes and fuller cheeks', 'a slightly stronger jaw and bold eyebrows', 'small delicate features and a narrow chin', 'a wider mouth and prominent cheekbones', 'closer-set eyes and a soft jawline', 'hooded eyelids and a gently rounded nose tip'];
  function explorePrompt(p, inspoN) {
    const ex = refsExtra(p, (inspoN || 1) + 1); const desc = (p.promptEditado ? p.prompt || '' : basePrompt(p)).replace(/ named [^.]+\./, '.');
    const head = inspoN ? `${Array.from({ length: inspoN }, (_, i) => '@Image' + (i + 1)).join(', ')} are photos the user likes, only as loose inspiration for the common look (never copy any of those faces).` : 'Use @Image1 only as a blank canvas and ignore it.';
    return `${head} Create ONE photo collage: a 3x3 grid (three columns, three rows, thin white borders) of nine studio portraits framed from the top of the head down to the chest, so the whole hairstyle and its full length are visible. It is a casting of nine DIFFERENT ${who(p)}: nine different real people who all fit this description: ${desc} Hair color and hairstyle are identical in all nine, exactly as described (including the hair length). Underneath that same hair they are nine unrelated people at a casting call, each one still fitting the description: ${CASTING.map((c, i) => `cell ${i + 1} is ${NOMBRES[who(p)][i]}, ${Math.max(18, (+p.edad || 25) + [-2, 1, 0, 2, -1, 3, 0, -2, 1][i])}, with ${c}`).join('; ')}. Their faces must be clearly different (eye spacing, eyebrow shape, nose bridge, lip shape, cheekbones, jaw): never repeat or clone a face, no two cells can look like the same person or like sisters, and each one smiles in ${{ women: 'her', men: 'his' }[who(p)] || 'their'} own way with a slightly different head tilt. Everyone wears the same plain black tank top, with no jewelry, no earrings, no glasses and no accessories unless the description asks for them. Facing the camera, natural smile, plain light-gray studio background, soft even light, identical framing and size in every cell.${p.cambios ? ' Changes the user asks for: ' + p.cambios + '.' : ''} ${ex.txt} No text, no names, no numbers, no labels.`;
  }
  async function genPj(p, kind, spec) { // lanza una generación del personaje (3×3, definitiva, vistas o cuerpo)
    if (!LIVE) { toast('Conecta primero tu API'); return; }
    const m = spec.model || modelFor(spec.images.length); const usd = m.usd[spec.quality || state.quality];
    if (!spec.noConfirm && !confirm(`${spec.ask} con ${m.name}? (${fmtUsd(usd)})`)) return;
    pj.sending = kind; renderProfile();
    const body_ = { item: 'personaje_' + p.id + '_' + kind, prompt: spec.prompt, images: spec.images, aspect: spec.aspect, quality: spec.quality || state.quality, model: m.key, meta: { name: `${spec.name} · ${p.nombre}`, tab: 'perfil', personaje: p.id, pjKind: kind, hidden: true, model: m.name, ep: m.ep, prompt: spec.prompt } };
    let r; try { r = await fetch('/api/generar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body_) }).then(x => x.json()); } catch (e) { r = { error: String(e) }; }
    pj.sending = null; if (!r || r.error) { toast('No se pudo generar: ' + (r ? r.error : 'sin respuesta')); renderProfile(); return; }
    const job = { rid: r.request_id, it: { id: 'pj:' + p.id + ':' + kind, name: body_.meta.name }, tab: 'perfil', m, kind: 'image', persona: { id: p.id, kind, extra: spec.extra }, t0: performance.now(), status: 'queued', usd: r.usd != null ? Number(r.usd) : usd };
    JOBS.set(job.rid, job); pj.jobs[p.id + ':' + kind] = job; ensurePoller(); renderProfile(); if (kind === 'explora' && pj.x3paint) pj.x3paint(); startTick();
  }
  function startTick() { clearInterval(pj.tick); pj.tick = setInterval(() => { const ns = document.querySelectorAll('#profcard [data-t0], #pjx3m [data-t0]'); if (!ns.length && !Object.keys(pj.jobs).length) { clearInterval(pj.tick); return; } ns.forEach(n => { n.textContent = Math.round((performance.now() - +n.dataset.t0) / 1000) + ' s'; }); }, 1000); }
  function explorar(p) {
    const inspo = arr(p.inspo).slice(0, 4).map(f => ({ path: clean(p[f] || f) }));
    const ex = refsExtra(p, (inspo.length || 1) + 1); const images = (inspo.length ? inspo : [{ path: 'assets/personajes/_lienzo.jpg' }]).concat(ex.imgs);
    const m = modelFor(images.length); const q = GRIDQ;
    genPj(p, 'explora', { ask: (p.explora || []).length ? '¿Regenerar la cuadrícula (9 caras nuevas)' : '¿Generar las primeras 9 caras (3×3)', name: 'Buscar su cara · 3×3', prompt: explorePrompt(p, inspo.length), images, aspect: '16:9', model: m, quality: q });
  }
  async function elegirCara(p, ri, n) { // «Es la definitiva»: se recorta esa cara de la rejilla y pasa a ser su foto
    const r = (p.explora || [])[ri]; if (!r) return; if (!confirm(`¿La nº ${n} es la definitiva? Con su cara se crean sus fichas.`)) return;
    const res = await persist_(Object.assign(p, { caraDe: { ronda: ri + 1, n } }), { crops: { foto: { path: clean(r.file), crop: CELL(n) } } });
    if (res && res.ok) { const m0 = $('#pjx3m'); if (m0) m0.remove(); toast('¡Esa es! Ahora, sus 4 vistas'); window.pjScrollTop = true; } else toast('No se pudo guardar: ' + (res ? res.error : 'sin respuesta'));
    renderProfile(); renderSide();
  }
  const bodyOf = p => [en('complexion', p.complexion), p.altura ? `about ${p.altura} cm tall` : '', p.genero !== 'masc' ? en('pecho', p.pecho) : '', en('cadera', p.cadera)].filter(Boolean).join(', ');
  const descOf = p => (p.prompt || '').replace(/ named [^.]+\./, '.');
  function cuerpoGen(p) {
    const bodyP = bodyOf(p);
    const under = p.genero === 'masc' ? 'plain white boxer briefs' : 'a plain minimalist white bra and white briefs';
    const prompt = `Create a BODY reference sheet of the person of @Image1. @Image1 is ONLY for the skin tone and the hair color: do NOT copy the body you see in it. One single wide image with THREE views side by side, framed FROM THE NECK DOWN (the top edge cuts just below the chin, no face): left front view, middle left side profile, right back view, each from the neck to the feet. IMPORTANT, the body MUST clearly be: ${bodyP || 'a natural build'} — make these proportions obvious at first glance in all three views. ${under}, matte cotton, no lace, no logos, tasteful model-agency body polaroid style. Standing straight and relaxed, barefoot. Plain neutral light-gray studio background, soft even light, photoreal, no text.`;
    genPj(p, 'cuerpo', { ask: '¿Generar su ficha de cuerpo (3 vistas del cuello a los pies)', name: 'Ficha de cuerpo', prompt, images: [{ path: clean(p.ficha360) }], aspect: '16:9', model: seedream() });
  }
  async function onJobDone(job, st) {
    job.end = true; delete pj.jobs[job.persona.id + ':' + job.persona.kind]; fetch('/api/pendientes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ claim: job.rid }) }).catch(() => {}); const usd = st.usd != null ? Number(st.usd) : (job.usd || 0); state.nGen++; state.spent += usd; meter();
    const p = pj.list.find(x => x.id === job.persona.id); if (!p) return; const k = job.persona.kind; let r;
    if (k === 'explora') { p.explora = (p.explora || []).concat([{ file: st.file, sel: [], t: Date.now() }]); pj.ver = null; r = await persist_(p); toast(`9 caras nuevas listas: elige la que más te guste · ${fmtUsd(usd)}`); if (pj.x3paint) pj.x3paint(); }
    else if (k === 'defin') { p.defCand = st.file; r = await persist_(p); toast(`Su cara en grande lista: úsala o genera otra · ${fmtUsd(usd)}`); }
    else if (k === 'cuerpo') { p.cuerpoCand = st.file; r = await persist_(p); toast(`Ficha de cuerpo lista: apruébala o genera otra · ${fmtUsd(usd)}`); }
    else { p.vistasOk = Object.assign({}, p.vistasOk, { [k]: false }); p.verVista = k; r = await persist_(p, { copy: { ['vista_' + k]: st.file } }); const nm = (VISTAS.find(v => v[0] === k) || [k, k])[1]; toast(r && r.ok ? `Vista «${nm}» de ${p.nombre} lista: apruébala o genera otra · ${fmtUsd(usd)}` : 'Se generó, pero no se pudo guardar en su ficha'); }
    if (state.tab === 'perfil') { renderProfile(); renderSide(); }
  }
  function onJobFail(job, msg) { job.end = true; delete pj.jobs[job.persona.id + ':' + job.persona.kind]; toast(`No se pudo generar: ${msg}`); if (state.tab === 'perfil') renderProfile(); }
  async function aprobarCuerpo(p) { let r = await persist_(p, { copy: { cuerpo: p.cuerpoCand } }); if (!r || !r.ok) return; const q = pj.list.find(x => x.id === p.id); delete q.cuerpoCand; await persist_(q);
    r = await fetch('/api/personaje_combo', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: p.id }) }).then(x => x.json()).catch(e => ({ error: String(e) }));
    if (r.ok) { const i = pj.list.findIndex(x => x.id === p.id); pj.list[i] = r.p; syncChars(); if (pj.forceStage) delete pj.forceStage[p.id]; toast(`Ficha principal de ${p.nombre} lista`); } else toast('No se pudo montar la ficha principal: ' + r.error); renderProfile(); renderSide(); }
  const VISTAS = [['frente', 'Frente'], ['perfil', 'Perfil'], ['tres', 'Tres cuartos'], ['espalda', 'Espalda']];
  function genPrompt(p, kind) { // el método del curso: frente → (perfil, tres cuartos y espalda a la vez); siempre con sus rasgos y su cuerpo en el texto
    const o = p.genero === 'masc' ? 'his' : p.genero === 'fem' || !p.genero ? 'her' : 'their'; const body = bodyOf(p);
    const keep = `Keep the exact visual style of @Image1 (a photo stays a photo, a cartoon stays a cartoon). Plain neutral light-gray studio background, soft even studio light, head and upper body in a vertical 2:3 frame, simple fitted black tank top, no jewelry or accessories unless described, no text, no logos.`;
    const traits = ` Respect every trait of this description: ${descOf(p)}${body ? ` IMPORTANT: ${o} body is clearly ${body}; make it obvious as far as the frame shows it.` : ''}`;
    if (kind === 'frente') return p.foto
      ? `Front view of the EXACT same person as @Image1 (identical face, eyes, nose, lips, eyebrows, hair and skin): facing the camera, looking into the lens with a big joyful toothy smile (mouth slightly open, upper and lower teeth visible, anatomically correct teeth).${traits} ${keep}`
      : `Use @Image1 only as a plain background canvas and ignore it otherwise. ${descOf(p)} Front view: facing the camera, looking into the lens with a big joyful toothy smile (upper and lower teeth visible, anatomically correct), simple black tank top, plain neutral light-gray studio background, soft even studio light, head and upper body in a vertical 2:3 frame, no text, no logos.`;
    const same = `The EXACT same person as @Image1 (identical face, eyes, hair, skin and body${p.foto ? '; @Image2 is a close-up of the same face' : ''}),`;
    if (kind === 'perfil') return `${same} now in a strict side profile view: body and head turned 90 degrees so we see ${o} left profile, looking straight ahead (not at the camera), calm neutral expression, the full length and shape of ${o} hair visible from the side.${traits} ${keep}`;
    if (kind === 'tres') return `${same} now in a three-quarter view: body turned about 45 degrees, face turned toward the camera with a big joyful toothy smile (teeth visible).${traits} ${keep}`;
    return `${same} now seen from behind at a back three-quarter angle: we see the back of ${o} head and hair, ${o} shoulders and upper back, the face almost hidden.${traits} ${keep}`;
  }
  const vfile = (p, k) => p['vista_' + k];
  const vok = (p, k) => !!(p.vistasOk && p.vistasOk[k]);
  function specVista(p, kind) { const front = clean(vfile(p, 'frente')); const foto = clean(p.foto); const nm = (VISTAS.find(v => v[0] === kind) || [kind, kind])[1];
    const images = kind === 'frente' ? [{ path: foto || 'assets/personajes/_lienzo.jpg' }] : [{ path: front }].concat(foto ? [{ path: foto }] : []);
    return { ask: `¿Generar la vista «${nm}» de ${p.nombre}`, name: nm, prompt: genPrompt(p, kind), images, aspect: '2:3' }; }
  function generate(p, kind) { if (kind !== 'frente' && !vok(p, 'frente')) { toast('Primero genera y aprueba el frente'); return; } genPj(p, kind, specVista(p, kind)); }
  async function generarTres(p) { // perfil, tres cuartos y espalda a la vez (una sola pregunta)
    const ks = ['perfil', 'tres', 'espalda'].filter(k => !vfile(p, k) && !pj.jobs[p.id + ':' + k]); if (!ks.length) return; const m = modelFor(2);
    if (!confirm(`¿Generar ${ks.length === 3 ? 'las 3 vistas' : ks.length + ' vistas'} (perfil, tres cuartos y espalda) a la vez con ${m.name}? (${fmtUsd(m.usd[state.quality] * ks.length)})`)) return;
    for (const k of ks) await genPj(p, k, Object.assign(specVista(p, k), { noConfirm: true }));
  }
  async function approve(p, k) {
    p.vistasOk = Object.assign({}, p.vistasOk, { [k]: true }); const next = VISTAS.find(v => !vok(p, v[0])); p.verVista = k;
    let r = await persist_(p);
    if (!next) { r = await fetch('/api/personaje_ficha', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: p.id }) }).then(x => x.json()).catch(e => ({ error: String(e) }));
      if (r.ok) { const i = pj.list.findIndex(x => x.id === p.id); pj.list[i] = r.p; syncChars(); pj.rebuild = null; if (pj.forceStage && pj.forceStage[p.id]) pj.forceStage[p.id] = 'cuerpo'; toast(`Ficha 360 de ${p.nombre} lista. Ahora, su ficha de cuerpo`); } else toast('No se pudo montar la ficha 360: ' + r.error); }
    else toast(k === 'frente' ? 'Frente aprobado: ahora puedes generar las otras 3 a la vez' : `Aprobada. Falta: ${VISTAS.filter(v => !vok(p, v[0])).map(v => v[1].toLowerCase()).join(', ')}`);
    renderProfile(); renderSide();
  }
  function builder(p) { // las 4 vistas en orden, cada una con aprobar / generar otra
    const m = modelFor(2); const cost = fmtUsd(m.usd[state.quality]); const box = el('div', 'pjgrp');
    box.appendChild(el('h4', '', `Ficha 360 · 4 vistas<small>se generan una a una; apruebas cada una y al final se unen en su ficha · ${m.name} · ${cost} cada una</small>`));
    const g = el('div', 'pjviews'); let prevOk = true;
    VISTAS.forEach(([k, nm], i) => {
      const f = vfile(p, k), ok = vok(p, k), job = pj.jobs[p.id + ':' + k]; const w = el('div', 'pjvw' + (ok ? ' ok' : '') + (p.verVista === k ? ' on' : ''));
      w.appendChild(el('div', 'pjvimg pjgenv', job ? `<div class="spin"></div><small data-t0="${job.t0}">0 s</small>` : f ? `<img src="${f}" alt="">` : `<i>${i + 1}</i>`));
      if (f && !job) w.querySelector('.pjvimg').onclick = () => { p.verVista = k; renderProfile(); };
      w.appendChild(el('b', '', `${i + 1} · ${nm}`));
      const a = el('div', 'pjvact');
      if (job) a.appendChild(el('small', '', 'Generando…'));
      else if (!prevOk) a.appendChild(el('small', '', 'Aprueba la anterior'));
      else if (!f) { const b = el('button', 'btn acc pr', `Generar<i>${cost}</i>`); b.disabled = !!pj.sending; b.onclick = () => generate(p, k); a.appendChild(b); }
      else if (!ok) { const y = el('button', 'btn acc', '✓ Aprobar'); y.onclick = () => approve(p, k); const n = el('button', 'btn', '↻ Otra'); n.title = `Generar otra (${cost})`; n.onclick = () => generate(p, k); a.appendChild(y); a.appendChild(n); }
      else { a.appendChild(el('small', 'okk', '✓ Aprobada')); const n = el('button', 'btn', '↻'); n.title = `Generar otra (${cost})`; n.onclick = () => generate(p, k); a.appendChild(n); }
      w.appendChild(a); g.appendChild(w); prevOk = prevOk && ok;
    });
    box.appendChild(g); return box;
  }
  async function del(p) {
    if (!confirm(`¿Borrar a ${p.nombre}? Deja de verse y se borra del todo a los 30 días.`)) return;
    const r = await fetch('/api/personaje_borrar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: p.id }) }).then(x => x.json()).catch(e => ({ error: String(e) }));
    if (!r.ok) { toast('No se pudo borrar: ' + r.error); return; } pj.list = pj.list.filter(x => x.id !== p.id); if (state.char === p.id && window.setChar) setChar('aria', true); syncChars(); pj.sel = WEBM ? (pj.list[0] ? pj.list[0].id : 'nuevo') : 'aria'; renderProfile(); renderSide(); toast(`${p.nombre} está en la papelera`);
  }

  // ---------------------------------------------------------------- pintar el Perfil
  function top() {
    const t = el('div', 'pjtop'); t.appendChild(el('small', 'pjk', 'Mis personajes'));
    const row = el('div', 'pjcircles');
    const add = (id, name, img) => { const c = el('button', 'pjc' + (!pj.wiz && pj.sel === id ? ' on' : ''), `<span class="pjav">${img ? `<img src="${img}" alt="">` : `<i>${(name || '?')[0]}</i>`}</span><small>${name}</small>`); c.onclick = () => { pj.wiz = null; if (window.FB) FB.open = false; if (window.F3) F3.open = false; saveDraft(); pj.sel = id; renderProfile(); renderSide(); };
      if (id !== 'aria') { c.draggable = true; c.title = 'Arrástralo para cambiar el orden'; c.ondragstart = e => { pj.dragId = id; e.dataTransfer.effectAllowed = 'move'; try { e.dataTransfer.setData('text/plain', id); } catch (x) {} setTimeout(() => c.classList.add('drag'), 0); }; c.ondragend = () => { pj.dragId = null; row.querySelectorAll('.pjc').forEach(x => x.classList.remove('drag', 'dropL', 'dropR')); }; }
      c.ondragover = e => { if (!pj.dragId || pj.dragId === id) return; e.preventDefault(); const r = c.getBoundingClientRect(); const left = id === 'aria' ? WEBM : e.clientX < r.left + r.width / 2; c.classList.toggle('dropL', left); c.classList.toggle('dropR', !left); };
      c.ondragleave = () => c.classList.remove('dropL', 'dropR');
      c.ondrop = e => { e.preventDefault(); const from = pj.dragId; const left = c.classList.contains('dropL'); if (!from || from === id) return; const L = pj.list.slice(); const [m] = L.splice(L.findIndex(p => p.id === from), 1); const at = id === 'aria' ? (WEBM ? L.length : 0) : L.findIndex(p => p.id === id) + (left ? 0 : 1); L.splice(at, 0, m); L.forEach((p, i) => { p.orden = i; }); pj.list = L; pj.dragId = null; syncChars(); renderProfile();
        fetch('/api/personajes_orden', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids: L.map(p => p.id) }) }).catch(() => toast('No se pudo guardar el orden')); };
      row.appendChild(c); };
    const nb = el('button', 'pjc new' + (pj.wiz || (WEBM && pj.sel === 'nuevo') ? ' on' : ''), `<span class="pjav"><i>＋</i></span><small>Crear personaje</small>`); nb.onclick = () => startWiz();
    const suyos = () => pj.list.forEach(p => add(p.id, p.nombre, p.avatar || p.retrato || p.foto));
    if (WEBM) { if (!pj.list.length) row.appendChild(nb); suyos(); add('aria', C.perfil.name, C.perfil.avatar); if (pj.list.length) row.appendChild(nb); }   // web: primero lo suyo (o «Crear»), Aria después
    else { add('aria', C.perfil.name, C.perfil.avatar); suyos(); row.appendChild(nb); }
    t.appendChild(row); return t;
  }
  function viewAria() { const P = C.perfil; const v = el('div', 'pjview two'); const col = el('div', 'pjimgcol'); const im = el('img', 'pjbig'); im.src = P.ficha; im.onclick = () => lightbox(P.ficha, 'Ficha 360 · ' + P.name); col.appendChild(im); v.appendChild(col); return v; }
  const GRIDQ = 'high'; // la cuadrícula siempre a 2K (0,09 $ en Seedream): de su celda sale su foto, y a 1K la cara queda de unos 200 px
  function modelSel(label, q) { const row = el('label', 'pjmodel'); row.appendChild(el('span', '', label || 'Modelo')); const ms = el('select', 'sel'); MODELS.forEach(x => { const o = document.createElement('option'); o.value = x.key; o.textContent = `${x.name} · ${fmtUsd(x.usd[q || (x.usd.high === x.usd.std ? 'high' : state.quality)])}`; ms.appendChild(o); }); ms.value = pjModel().key; ms.onchange = () => { pj.model = ms.value; try { localStorage.setItem(MKEY, ms.value); } catch (e) {} renderProfile(); const m0 = $('#pjx3m'); if (m0 && m0._repaint) m0._repaint(); }; row.appendChild(ms); return row; }
  function stagesBar(p, cur_) { const S = [['explorar', '1 · Su cara'], ['vistas', '2 · Sus 4 vistas'], ['cuerpo', '3 · Su cuerpo'], ['lista', '4 · Ficha principal']]; const i0 = S.findIndex(s => s[0] === cur_); const b = el('div', 'pjstages'); S.forEach(([k, n], i) => b.appendChild(el('span', i < i0 ? 'done' : i === i0 ? 'on' : '', (i < i0 ? '✓ ' : '') + n))); return b; }
  const stageOf = p => (p.combo || (p.modo === 'tengo' && p.ficha360)) ? 'lista' : p.ficha360 ? 'cuerpo' : p.foto ? 'vistas' : 'explorar';
  function editar(p) { pj.wiz = { mode: 'cero', step: STEPS.length - 1, editId: p.id, d: Object.assign({}, p, { prompt: p.promptEditado ? p.prompt : null, promptManual: !!p.promptEditado, foto: null, ficha: null, inspo: [] }) }; saveDraft(); window.pjScrollTop = true; renderProfile(); renderSide(); }
  function viewPersona(p) {
    const st = pj.forceStage && pj.forceStage[p.id] || stageOf(p); const v = el('div', 'pjgenwrap');
    const hd = el('div', 'pjghead'); hd.appendChild(el('div', 'pjname', `<b>${esc(p.nombre)}</b><small>${[p.usuario, arr(p.rol).map(r => es('rol', r)).join(', '), p.edad ? p.edad + ' años' : ''].filter(Boolean).join(' · ')}</small>`));
    const acts = el('div', 'pjgacts'); const ed = el('button', 'btn', '✎ Editar sus datos'); ed.title = 'Abre el resumen: cambias lo que quieras y vuelves aquí'; ed.onclick = () => editar(p);
    const forced = !!(pj.forceStage && pj.forceStage[p.id]);
    if (forced && stageOf(p) === 'lista') { const bk = el('button', 'btn', '← Volver a su ficha'); bk.onclick = () => { delete pj.forceStage[p.id]; window.pjScrollTop = true; renderProfile(); }; acts.appendChild(bk); }
    if (!forced && st === 'lista') { const mk = el('button', 'btn acc', '✨ Crear imagen con ' + esc((p.nombre || '').split(' ')[0])); mk.title = 'Ir a Crear imagen con este personaje elegido'; mk.onclick = () => { if (window.setChar) setChar(p.id); setTab('crear'); }; acts.appendChild(mk); }
    acts.appendChild(ed);
    const dl = el('button', 'btn', '🗑'); dl.title = 'Borrar personaje'; dl.style.color = '#e25555'; dl.onclick = () => del(p); acts.appendChild(dl); hd.appendChild(acts); v.appendChild(hd);
    if (!LIVE) { v.appendChild(el('div', 'pjapi', `<div class="pjvideo">▶<small>Vídeo de Aria: cómo conectar tus APIs (demo)</small></div><div><h3>Conecta tu API</h3><p>Para crear su imagen hace falta tu clave de WaveSpeed (o de Higgsfield). Conéctala arriba, en «Conecta tu API».</p></div>`)); return v; }
    if (st !== 'lista' || (pj.forceStage && pj.forceStage[p.id])) v.appendChild(stagesBar(p, st));
    if (st === 'explorar') v.appendChild(panelExplorar(p));
    else if (st === 'vistas') v.appendChild(panelVistas(p));
    else if (st === 'cuerpo') v.appendChild(panelCuerpo(p));
    else v.appendChild(panelLista(p));
    return v;
  }
  function x3cells(p, ri, onPick) { // las 9 casillas sobre la rejilla: se elige UNA
    const R = p.explora[ri]; const cells = el('div', 'pjx3cells'); const sel = (R.sel || [])[0];
    for (let n = 1; n <= 9; n++) { const c = el('button', 'pjx3c' + (sel === n ? ' on' : ''), `<i>${n}</i>${sel === n ? '<em>✓</em>' : ''}`); c.title = sel === n ? 'Elegida' : 'Elegir la nº ' + n; c.onclick = e => { e.stopPropagation(); R.sel = sel === n ? [] : [n]; persist_(p); onPick(); }; cells.appendChild(c); }
    return cells;
  }
  function x3actions(p, ri, repaint) { // botones: definitiva (rosa lleno), regenerar (marco rosa), algo que cambiar, cambiar sus datos, modelo
    const R = (p.explora || [])[ri]; const sel = (R && R.sel || [])[0]; const job = pj.jobs[p.id + ':explora']; const w = el('div', 'pjx3acts');
    const def = el('button', 'btn acc big', sel ? `★ La nº ${sel} es la definitiva` : '★ Es la definitiva'); def.disabled = !sel || !R; def.title = sel ? 'Se recorta esa cara y con ella se crean sus fichas' : 'Pulsa primero la cara que te guste'; def.onclick = () => elegirCara(p, ri, sel); w.appendChild(def);
    const m = modelFor((arr(p.inspo).length || 1) + refsExtra(p, 2).imgs.length); const q = GRIDQ;
    const rg = el('button', 'btn pinkline pr', job ? `⏳ Generando… <i data-t0="${job.t0}">0 s</i>` : `↻ Regenerar la cuadrícula<i>${fmtUsd(m.usd[q])}</i>`); rg.disabled = !!job || !!pj.sending; rg.onclick = () => explorar(p); w.appendChild(rg);
    w.appendChild(modelSel('Modelo para la cuadrícula', GRIDQ));
    const ct = el('textarea', 'pjin'); ct.rows = 2; ct.placeholder = 'Algo que cambiar en las próximas · ej.: pelo más corto, más pecas, cara más redonda'; ct.value = p.cambios || ''; ct.onchange = async () => { p.cambios = ct.value.trim(); await persist_(p); }; const cw = el('div', 'stack'); cw.appendChild(el('small', 'pjk', 'Algo que cambiar')); cw.appendChild(ct); w.appendChild(cw);
    const ed = el('button', 'lnk', '✎ Cambiar sus datos (ojos, pelo, cuerpo…) y volver aquí'); ed.onclick = () => { const m0 = $('#pjx3m'); if (m0) m0.remove(); editar(p); }; w.appendChild(ed);
    return w;
  }
  function openX3(p, ri) { // la rejilla a pantalla completa con el menú a la derecha
    let m0 = $('#pjx3m'); if (m0) m0.remove(); m0 = el('div', 'fxm'); m0.id = 'pjx3m'; document.body.appendChild(m0); m0.onclick = e => { if (e.target === m0) m0.remove(); };
    const paint = () => { const q = pj.list.find(x => x.id === p.id) || p; const rounds = q.explora || []; if (ri == null || !rounds[ri]) ri = rounds.length - 1; const R = rounds[ri]; const job = pj.jobs[q.id + ':explora']; m0.innerHTML = '';
      const box = el('div', 'fxbox pjx3box'); const media = el('div', 'fxmedia'); const g = el('div', 'pjx3 full' + (job ? ' gen pjgenv' : ''));
      if (R) { g.appendChild(Object.assign(document.createElement('img'), { src: R.file, alt: '' })); if (!job) g.appendChild(x3cells(q, ri, paint)); }
      if (job) g.appendChild(el('div', 'pjx3gen', `<div class="bar"><i></i></div><b>Generando 9 caras nuevas</b><small data-t0="${job.t0}">0 s</small>`)); media.appendChild(g); box.appendChild(media);
      const side = el('div', 'fxside'); const x = el('button', 'galx', '×'); x.onclick = () => m0.remove(); box.appendChild(x);
      side.appendChild(el('div', 'fxtitle', `<small>Su cara · ronda ${ri + 1} de ${rounds.length}</small><b>${esc(q.nombre)}</b><p>Pulsa la cara que más te guste. Si ninguna es ella, regenera la cuadrícula las veces que haga falta.</p>`));
      side.appendChild(x3actions(q, ri, paint));
      if (rounds.length > 1) { const h = el('div', 'pjrounds v'); rounds.forEach((r, i) => { const t = el('button', 'pjround' + (i === ri ? ' on' : ''), `<img src="${r.file}" alt=""><small>Ronda ${i + 1}${(r.sel || [])[0] ? ' · nº ' + r.sel[0] : ''}</small>`); t.onclick = () => { ri = i; paint(); }; h.appendChild(t); }); const hs = el('div', 'fxsec'); hs.appendChild(el('h4', '', 'Rondas anteriores<small>nada se pierde: puedes elegir una cara de cualquier ronda</small>')); hs.appendChild(h); side.appendChild(hs); }
      box.appendChild(side); m0.appendChild(box); };
    m0._repaint = paint; pj.x3paint = () => { if (document.getElementById('pjx3m')) { ri = null; paint(); } }; paint(); startTick();
  }
  function panelExplorar(p) {
    const box = el('div', 'pjgrp pjexp'); const rounds = p.explora || []; const job = pj.jobs[p.id + ':explora'];
    box.appendChild(el('h4', '', `Encuentra su cara<small>la IA dibuja 9 personas distintas con todo lo que elegiste. Elige la que más te guste o regenera la cuadrícula hasta encontrarla.</small>`));
    const ri = pj.ver != null && rounds[pj.ver] ? pj.ver : rounds.length - 1; const R = rounds[ri];
    if (R || job) { const g = el('div', 'pjx3' + (job ? ' gen pjgenv' : '')); if (R) g.appendChild(Object.assign(document.createElement('img'), { src: R.file, alt: '' }));
      if (job) g.appendChild(el('div', 'pjx3gen', `<div class="bar"><i></i></div><b>Generando 9 caras</b><small data-t0="${job.t0}">0 s</small>`));
      else { g.appendChild(x3cells(p, ri, () => renderProfile())); const fs = el('button', 'pjx3full', '⤢ Ver en grande'); fs.onclick = e => { e.stopPropagation(); openX3(p, ri); }; g.appendChild(fs); }
      const main = el('div', 'pjx3wrap'); main.appendChild(g); main.appendChild(x3actions(p, ri, () => renderProfile())); box.appendChild(main); }
    else { const ms = modelSel('Modelo para la cuadrícula', GRIDQ); ms.classList.add('pjmsep'); box.appendChild(ms); const a = el('div', 'pjacts'); const m = modelFor(1); const q = GRIDQ; const b = el('button', 'btn acc big pr', `🎲 Generar las primeras 9 caras<i>${fmtUsd(m.usd[q])}</i>`); b.disabled = !!pj.sending; b.onclick = () => explorar(p); a.appendChild(b); box.appendChild(a);
      if (arr(p.inspo).length) box.appendChild(el('small', 'pjnote', `Se inspirará en tus ${arr(p.inspo).length} fotos favoritas, sin copiar ninguna cara.`)); }
    if (rounds.length > 1) { const h = el('div', 'pjrounds'); rounds.forEach((r, i) => { const t = el('button', 'pjround' + (i === ri ? ' on' : ''), `<img src="${r.file}" alt=""><small>Ronda ${i + 1}${(r.sel || [])[0] ? ' · nº ' + r.sel[0] : ''}</small>`); t.onclick = () => { pj.ver = i; renderProfile(); }; h.appendChild(t); }); box.appendChild(grp('Rondas anteriores', h, 'nada se pierde: puedes volver a una y elegir una cara de ella')); }
    return box;
  }
  function panelVistas(p) { // su cara arriba y las 4 vistas debajo, sin scroll
    const box = el('div', 'pjv2'); const m = modelFor(2); const cost = fmtUsd(m.usd[state.quality]); const fOk = vok(p, 'frente'); const fJob = pj.jobs[p.id + ':frente'];
    const top = el('div', 'pjv2top'); const face = el('div', 'pjv2face', `<img src="${p.foto}" alt=""><small>Su cara</small>`); face.onclick = () => lightbox(p.foto, 'Su cara · ' + p.nombre); top.appendChild(face);
    const info = el('div', 'pjv2info'); const faltan = ['perfil', 'tres', 'espalda'].filter(k => !vfile(p, k) && !pj.jobs[p.id + ':' + k]);
    info.appendChild(el('p', '', !vfile(p, 'frente') && !fJob ? '<b>Primero, su vista de frente</b> a partir de su cara. Cuando te guste, apruébala.' : !fOk ? '<b>¿Te gusta su frente?</b> Apruébalo o genera otro.' : faltan.length ? '<b>Frente aprobado.</b> Ahora genera las otras tres a la vez.' : '<b>Aprueba las que te gusten</b> o genera otra de la que no. Al aprobar las cuatro se unen en su ficha 360.'));
    info.appendChild(modelSel('Modelo para las vistas')); const ac = el('div', 'pjacts');
    if (!vfile(p, 'frente') && !fJob) { const b = el('button', 'btn acc big pr', `Generar su frente<i>${cost}</i>`); b.disabled = !!pj.sending; b.onclick = () => generate(p, 'frente'); ac.appendChild(b); }
    else if (fOk && faltan.length) { const b = el('button', 'btn acc big pr', `Generar ${faltan.length === 3 ? 'las 3 vistas' : 'las que faltan'} a la vez<i>${fmtUsd(m.usd[state.quality] * faltan.length)}</i>`); b.disabled = !!pj.sending; b.onclick = () => generarTres(p); ac.appendChild(b); }
    info.appendChild(ac); top.appendChild(info); box.appendChild(top);
    const row = el('div', 'pjv2row'); VISTAS.forEach(([k, nm], i) => {
      const f = vfile(p, k), ok = vok(p, k), job = pj.jobs[p.id + ':' + k]; const w = el('div', 'pjv2t' + (ok ? ' ok' : ''));
      const im = el('div', 'pjv2img pjgenv', job ? `<div class="spin"></div><small data-t0="${job.t0}">0 s</small>` : f ? `<img src="${f}" alt="">` : `<i>${i + 1}</i>`); if (f && !job) im.onclick = () => lightbox(f, nm + ' · ' + p.nombre); w.appendChild(im);
      w.appendChild(el('b', '', `${nm}${ok ? ' <em>✓</em>' : ''}`)); const a = el('div', 'pjvact');
      if (job) a.appendChild(el('small', '', 'Generando…'));
      else if (k !== 'frente' && !fOk) a.appendChild(el('small', '', 'Después del frente'));
      else if (!f) { const b = el('button', 'btn pr', `Generar<i>${cost}</i>`); b.disabled = !!pj.sending; b.onclick = () => generate(p, k); a.appendChild(b); }
      else if (!ok) { const y = el('button', 'btn acc', '✓ Aprobar'); y.onclick = () => approve(p, k); const n = el('button', 'btn', '↻'); n.title = `Generar otra (${cost})`; n.onclick = () => generate(p, k); a.appendChild(y); a.appendChild(n); }
      else { const n = el('button', 'btn', '↻ Otra'); n.title = `Generar otra (${cost})`; n.onclick = () => generate(p, k); a.appendChild(n); }
      w.appendChild(a); row.appendChild(w); });
    box.appendChild(row);
    if (p.modo === 'tengo' && !p.ficha360) { const up = el('div', 'pjacts'); up.appendChild(drop('¿Ya tienes su ficha 360? Súbela', async du => { const r = await persist_(p, { files: { ficha360: du } }); toast(r && r.ok ? 'Ficha 360 guardada' : 'No se pudo guardar'); renderProfile(); renderSide(); }, null, 'y te saltas las vistas')); box.appendChild(up); }
    return box;
  }
  function panelCuerpo(p) { // su ficha 360 y su cuerpo, del mismo tamaño, y los botones debajo
    const box = el('div', 'pjc2'); const job = pj.jobs[p.id + ':cuerpo']; const m = seedream(); const body = p.cuerpoCand || p.cuerpo;
    box.appendChild(el('p', 'pjc2t', `<b>Su ficha de cuerpo:</b> frente, perfil y espalda del cuello a los pies, en ropa interior blanca y lisa, con el cuerpo que elegiste (${esc(bodyOf(p) || 'complexión natural')}). Se hace de una vez con ${m.name}, porque otros modelos rechazan la ropa interior.`));
    const g = el('div', 'pjc2g'); const a1 = el('div', 'pjc2box', `<div class="pjc2img"><img src="${p.ficha360}" alt=""></div><small>Su ficha 360</small>`); a1.querySelector('.pjc2img').onclick = () => lightbox(p.ficha360, 'Ficha 360 · ' + p.nombre); g.appendChild(a1);
    const a2 = el('div', 'pjc2box', `<div class="pjc2img pjgenv">${job ? `<div class="spin"></div><b>Generando su cuerpo</b><small data-t0="${job.t0}">0 s</small>` : body ? `<img src="${body}" alt="">` : '<i>Aún sin generar</i>'}</div><small>Su cuerpo</small>`); if (body && !job) a2.querySelector('.pjc2img').onclick = () => lightbox(body, 'Cuerpo · ' + p.nombre); g.appendChild(a2); box.appendChild(g);
    const a = el('div', 'pjacts pjc2acts');
    if (!job) { if (p.cuerpoCand) { const y = el('button', 'btn acc big', '✓ Aprobar y montar su ficha principal'); y.onclick = () => aprobarCuerpo(p); a.appendChild(y); }
      const gb = el('button', 'btn pr' + (p.cuerpoCand ? ' pinkline' : ' acc big'), `${p.cuerpoCand ? '↻ Generar otro' : 'Generar su ficha de cuerpo'}<i>${fmtUsd(m.usd[state.quality])}</i>`); gb.disabled = !!pj.sending; gb.onclick = () => cuerpoGen(p); a.appendChild(gb); }
    box.appendChild(a); return box;
  }
  function panelLista(p) { // igual que la pestaña «Fichas 360» de Aria
    const w = el('div', 'f3wrap'); const top = el('div', 'f3main'); const main = p.combo || p.ficha360;
    const big = el('div', 'f3card big combo' + (p.combo ? '' : ' solo360'), `<div class="f3img"><img src="${main}" alt=""></div><b>Ficha principal</b><small>${p.combo ? 'sus cuatro vistas y su cuerpo entero de frente y de perfil, del cuello a los pies' : 'su ficha 360: es la referencia que va en todas sus imágenes'}</small>`); big.querySelector('img').onclick = () => lightbox(main, 'Ficha principal · ' + p.nombre); top.appendChild(big);
    const col = el('div', 'f3sidecol'); const force = stg => { pj.forceStage = Object.assign({}, pj.forceStage, { [p.id]: stg }); window.pjScrollTop = true; renderProfile(); };
    const mini = (src, t, s0, stg) => { const d = el('div', 'f3card big mini', `<div class="f3img"><img src="${src}" alt=""><button class="f3edit">✎ Editar</button></div><b>${t}</b><small>${s0}</small>`); d.querySelector('img').onclick = () => lightbox(src, t + ' · ' + p.nombre); d.querySelector('.f3edit').onclick = e => { e.stopPropagation(); force(stg); }; col.appendChild(d); };
    if (p.combo) mini(p.ficha360, 'Cara de cerca', 'cuatro ángulos: frente, perfil, tres cuartos y espalda', 'vistas');
    if (p.cuerpo) mini(p.cuerpo, 'Cuerpo completo', p.combo ? 'tres ángulos: frente, perfil y espalda' : 'su ficha de cuerpo: se usa al recrear fotos', 'cuerpo');
    else { const d = el('div', 'f3card big mini pjaddb', `<div class="f3img"><span>＋</span><b>Su cuerpo completo</b><small>Opcional. Hace que al recrear una foto salga con su cuerpo y no con el de la foto.</small></div>`); const a = el('div', 'f3acts');
      const g = el('button', 'btn acc', '✨ Crearlo a partir de su ficha'); g.title = 'Genera su ficha de cuerpo usando su ficha como referencia'; g.onclick = () => force('cuerpo'); a.appendChild(g);
      const u = el('label', 'btn', 'Subir el mío'); const f = document.createElement('input'); f.type = 'file'; f.accept = 'image/*'; f.hidden = true; u.appendChild(f); f.onchange = () => { const file = f.files[0]; if (!file) return; const rd = new FileReader(); rd.onload = async () => { const r = await persist_(p, { files: { cuerpo: await shrink(rd.result, 2000) } }); toast(r && r.ok ? 'Ficha de cuerpo guardada' : 'No se pudo guardar'); renderProfile(); }; rd.readAsDataURL(file); }; a.appendChild(u);
      d.appendChild(a); col.appendChild(d); }
    top.appendChild(col); w.appendChild(top);
    const sec2 = el('div', 'f3sec'); const hd = el('div', 'f3head stacked'); hd.appendChild(el('h4', '', 'Fichas creadas<small>para usarlas en fotos y en vídeos</small>')); const nb = el('div', 'f3newbtns pjdevnew'); const b1 = el('button', 'pjbigopt', '<span>＋</span><b>Nueva ficha</b><small>Su ficha principal con otra ropa y otros objetos.</small>'); nb.appendChild(b1); b1.onclick = () => window.nfOpenFor && nfOpenFor(p.id); if (window.devGate) devGate(b1, `Fichas de ${p.nombre} · Nueva ficha`, () => window.nfOpenFor && nfOpenFor(p.id)); hd.appendChild(nb); sec2.appendChild(hd);
    { const g = el('div', 'f3grid'); const jobs = window.nfJobs ? nfJobs(p.id) : [];
      jobs.forEach(jb => g.appendChild(el('div', 'f3card wide gen', `<div class="f3img sm"><img src="${p.combo || p.ficha360}" alt=""><span class="f3busy"><i class="spin"></i>Generando · <i data-t0="${jb.t0}">${Math.round((performance.now() - jb.t0) / 1000)} s</i></span></div><b>${esc(jb.it.name)}</b><small>se guardará aquí sola al terminar</small>`)));
      arr(p.fichas).forEach(f => { const d = el('div', 'f3card wide', `<div class="f3img sm"><img src="${f.thumb || f.img}" alt=""></div><b>${esc(f.nombre)}</b><small>${[f.t, f.modelo, f.size && f.size[0] >= 1500 ? '2K' : ''].filter(Boolean).join(' · ')}</small>`); d.querySelector('.f3img').onclick = () => lightbox(f.img, f.nombre);
        const a = el('div', 'f3acts'); const dl = el('button', 'btn', '⬇'); dl.title = 'Descargar'; dl.onclick = e => { e.stopPropagation(); const x = document.createElement('a'); x.href = f.img; x.download = f.img.split('/').pop(); document.body.appendChild(x); x.click(); x.remove(); }; a.appendChild(dl);
        const rm = el('button', 'btn', '🗑'); rm.title = 'Borrar'; rm.onclick = async e => { e.stopPropagation(); if (!confirm(`¿Borrar «${f.nombre}»? Deja de verse y se borra del todo a los 30 días.`)) return; const r = await fetch('/api/personaje_fichas', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: p.id, action: 'delete', fid: f.id }) }).then(x => x.json()).catch(x => ({ error: String(x) })); if (r && r.ok) { await load(); renderProfile(); } else toast('No se pudo borrar: ' + (r ? r.error : 'sin respuesta')); }; a.appendChild(rm); d.appendChild(a); g.appendChild(d); });
      if (!g.children.length) g.appendChild(el('div', 'accempty', 'Todavía no has creado ninguna.')); sec2.appendChild(g); if (jobs.length) startTick(); }
    w.appendChild(sec2);
    if (!p.celebrado) setTimeout(() => celebrar(p), 250);
    return w;
  }
  function celebrar(p) { // al terminar: enhorabuena y a crear
    if ($('#pjcel')) return; const m0 = el('div', 'fxm'); m0.id = 'pjcel'; document.body.appendChild(m0); const short = esc((p.nombre || '').split(' ')[0]);
    const done = async go => { m0.remove(); const q = pj.list.find(x => x.id === p.id); if (q && !q.celebrado) { q.celebrado = true; await persist_(q); } if (go === 'crear') { if (window.setChar) setChar(p.id); setTab('crear'); return; } if (go === 'acc') pj.tabBy[p.id] = 'complementos'; renderProfile(); renderSide(); };
    m0.onclick = e => { if (e.target === m0) done(); };
    const b = el('div', 'pjcelbox', `<div class="pjcelemo">🎉</div><h3>¡Enhorabuena! ${esc(p.nombre)} ya está en ARIA STUDIO</h3><img src="${p.combo || p.ficha360}" alt="">`);
    const a = el('div', 'pjacts'); const g = el('button', 'btn acc big', '✨ Crear una imagen'); g.onclick = () => done('crear'); const c = el('button', 'btn big', 'Cerrar'); c.onclick = () => done(); a.appendChild(g); a.appendChild(c); b.appendChild(a); m0.appendChild(b);
  }
  function paintWiz() {
    const host = $('#profcard .pjbody'); if (!host || !pj.wiz) return; const keep = host.scrollTop; const w = pj.wiz, d = w.d; host.innerHTML = ''; const S = stepsOf(w);
    if (w.step < 0 || w.step >= S.length) w.step = 0; const stp = S[w.step];
    const hd = el('div', 'pjwhd'); hd.appendChild(el('div', '', `<small class="pjk">${w.editId ? 'Editar personaje' : w.mode === 'tengo' ? 'Ya tengo mi personaje' : w.mode === 'fotos' ? 'Desde tus favoritas' : 'Crear personaje desde cero'} · paso ${w.step + 1} de ${S.length}</small><h3>${stp.t}</h3><p>${stp.h}</p>`));
    const dots = el('div', 'pjdots'); S.forEach((s, i) => { const k = i; const b = el('button', k === w.step ? 'on' : k < w.step ? 'done' : '', ''); b.title = s.t; b.onclick = () => { w.step = k; saveDraft(); paintWiz(); updSide(); }; dots.appendChild(b); }); hd.appendChild(dots);
    if (w.editId) { const p0 = pj.list.find(x => x.id === w.editId); const bb = el('button', 'btn fxback', `← Volver a ${esc((p0 && p0.nombre) || 'su ficha')} sin guardar`); bb.onclick = () => { pj.wiz = null; saveDraft(); pj.sel = w.editId; window.pjScrollTop = true; renderProfile(); renderSide(); }; host.appendChild(bb); }
    host.appendChild(hd); host.appendChild(stepBody(stp.id, d));
    const nav = el('div', 'pjnav'); const first = w.step === 0;
    const bk = el('button', 'btn', first ? '✕ Salir' : '← Atrás'); bk.onclick = () => { if (first) { if (confirm('¿Salir del creador? El borrador se queda guardado.')) { pj.wiz = null; renderProfile(); renderSide(); } return; } w.step--; saveDraft(); paintWiz(); updSide(); host.scrollTop = 0; }; nav.appendChild(bk);
    if (stp.id === 'fin' || stp.id === 'tdatos') { const sv = el('button', 'btn acc', w.editId ? '✓ Guardar cambios' : stp.id === 'tdatos' ? '✓ Guardar mi personaje' : '✓ Guardar y crear su imagen'); sv.onclick = () => savePersona(); nav.appendChild(sv); }
    if (w.step < S.length - 1) { const nx = el('button', 'btn acc', 'Siguiente →'); nx.onclick = () => { if (stp.id === 'tficha' && !d.ficha) { toast('Sube primero su ficha 360'); return; } w.step++; saveDraft(); paintWiz(); updSide(); host.scrollTop = 0; }; nav.appendChild(nx); }
    host.appendChild(nav); host.scrollTop = keep; // elegir una tarjeta no mueve la vista
  }
  function startWiz() {
    if (WEBM) { pj.wiz = null; pj.sel = 'nuevo'; window.pjScrollTop = true; renderProfile(); renderSide(); return; }   // en la web es un estado más del perfil (se mantiene al repintar y deja vacío el panel de la izquierda)
    pj.wiz = null; renderProfile(); const h = $('#profcard .pjbody'); h.innerHTML = ''; inicio(h);
    document.querySelectorAll('#profcard .pjc').forEach(x => x.classList.toggle('on', x.classList.contains('new'))); devSection();
  }
  function inicio(h) {   // la pantalla «Crear un personaje nuevo», con sus tres caminos
    const dr = loadDraft();
    const box = el('div', 'pjstart'); box.appendChild(el('h3', '', 'Crear un personaje nuevo')); box.appendChild(el('p', '', 'Si ya tienes tu personaje del curso «De 0 a 100 para crear tu Influencer IA», súbelo y empieza a crear. Si no, pronto podrás crearlo aquí desde cero.'));
    const r = el('div', 'pjrow');
    const f = el('button', 'pjbigopt', '<span>⚡</span><b>Desde tus favoritas</b><small>Sueltas fotos de personas que te gusten y la IA rellena los rasgos. Solo te pregunta rol, nombre y edad.</small>'); f.onclick = () => { newWiz('fotos'); renderProfile(); renderSide(); };
    const a = el('button', 'pjbigopt', '<span>🧬</span><b>Empezar desde cero</b><small>Eliges rol, nombre, rostro, pelo, piel, cuerpo, estilo y personalidad.</small>'); a.onclick = () => { newWiz('cero'); renderProfile(); renderSide(); };
    const b = el('button', 'pjbigopt', '<span>📸</span><b>Ya tengo mi personaje</b><small>Subes su ficha 360, la IA rellena sus rasgos y en dos pasos está lista para crear imágenes.</small>'); b.onclick = () => { newWiz('tengo'); renderProfile(); renderSide(); };
    if (window.devGate) { devGate(f, 'Crear personaje · Desde tus favoritas', () => { newWiz('fotos'); renderProfile(); renderSide(); }); devGate(a, 'Crear personaje · Empezar desde cero', () => { newWiz('cero'); renderProfile(); renderSide(); }); }
    r.appendChild(b); r.appendChild(a); r.appendChild(f); box.appendChild(r);
    if (dr) { const c = el('button', 'btn w', `↺ Seguir con el borrador${dr.d.nombre ? ' de ' + dr.d.nombre : ''}`); c.onclick = () => { pj.wiz = dr; renderProfile(); renderSide(); }; box.appendChild(c); }
    h.appendChild(box);
  }
  function updSide() { if (state.tab === 'perfil' && pj.wiz) renderSide(); }

  const TABS_ARIA = [['ficha', '🪪', 'Fichas 360'], ['complementos', '👓', 'Complementos'], ['voz', '🎙', 'Voz', 1], ['lugares', '📍', 'Lugares', 1]]; // Poses irá al menú de la izquierda
  const TABS_PJ = TABS_ARIA; // todos los personajes con la misma interfaz que Aria (el prompt base está en el panel de la izquierda)
  const SOON = { voz: 'Su voz para los vídeos: la voz clonada, su cadencia y sus muletillas, con muestras para escuchar y elegir.', lugares: 'Sus sitios de siempre (su habitación, su cocina, su calle…) guardados como referencias, para que sus escenas sean coherentes.' };
  pj.tabBy = pj.tabBy || {};
  function tabsBar() { const p = pj.sel === 'aria' ? null : cur(); const creando = !!(p && stageOf(p) !== 'lista'); const list = pj.sel === 'aria' ? TABS_ARIA : TABS_PJ; let cur_ = pj.tabBy[pj.sel] || 'ficha'; if (creando) cur_ = 'ficha'; const bar = el('div', 'pjtabs');
    list.forEach(([k, ic, n0, soon]) => { const off = creando && k !== 'ficha'; const n = n0; const b = el('button', 'pjtab' + (k === cur_ ? ' on' : '') + (soon ? ' soon' : '') + (off ? ' off' : ''), `<span>${ic}</span><b>${n}</b>${soon ? '<i>pronto</i>' : ''}`); if (off) { b.title = 'Se activa al terminar sus fichas'; b.onclick = () => toast('Primero termina sus fichas: luego se activan sus complementos y su prompt base'); bar.appendChild(b); return; } b.onclick = () => { pj.tabBy[pj.sel] = k; if (window.FB && k !== 'ficha') FB.open = false; if (window.F3 && k !== 'ficha' && !window.accPick) F3.open = false; if (window.accPick && k !== 'complementos') window.accPick = null; renderProfile(); }; bar.appendChild(b); }); return bar; }
  function tabBody(bd) { const p = pj.sel === 'aria' ? null : cur(); const tab = p && stageOf(p) !== 'lista' ? 'ficha' : pj.tabBy[pj.sel] || 'ficha'; const list = pj.sel === 'aria' ? TABS_ARIA : TABS_PJ; const def = list.find(t => t[0] === tab) || list[0];
    if (def[3]) { const s0 = el('div', 'pjsoon', `<span>${def[1]}</span><h3>${def[2]}</h3><p>${SOON[def[0]] || ''}</p><small>Próximamente</small>`); bd.appendChild(s0); return; }
    if (tab === 'ficha' && p && window.F3 && F3.open && F3.owner === p.id && window.f3Render && f3Render(bd)) return;   // «Nueva ficha» de este personaje
    if (tab === 'ficha' && !p) { if (window.F3 && F3.owner) { F3.open = false; F3.owner = null; } if (window.f3Render && f3Render(bd)) return; if (window.fbRender && fbRender(bd)) return; if (window.f3Gallery) { bd.appendChild(f3Gallery()); return; } }
    if (tab === 'complementos' && window.accPanel) { const w = el('div', 'pjpane'); w.appendChild(accPanel(p ? p.id : 'aria')); bd.appendChild(w); return; }
    if (tab === 'prompt' && p) { const w = el('div', 'pjpane'); const g = el('div', 'pjgrp'); g.appendChild(el('h4', '', 'Prompt base<small>la plantilla de la lección 1.4 con lo que elegiste</small>')); g.appendChild(el('div', 'promptbox', esc(p.prompt || ''))); const c = el('button', 'btn', 'Copiar prompt base'); c.onclick = () => { navigator.clipboard && navigator.clipboard.writeText(p.prompt || ''); toast('Prompt base copiado'); }; g.appendChild(c); w.appendChild(g); bd.appendChild(w); return; }
    bd.appendChild(p ? viewPersona(p) : viewAria()); if (p && Object.keys(pj.jobs).length) startTick(); }
  window.renderProfile = async function () {
    const host = $('#profcard'); const keep = host.querySelector('.pjbody') && host.querySelector('.pjbody').scrollTop;
    host.innerHTML = ''; const wrap = el('div', 'pj'); wrap.appendChild(top()); const nuevo = WEBM && pj.sel === 'nuevo' && !pj.wiz; if (!pj.wiz && !nuevo) wrap.appendChild(tabsBar()); const bd = el('div', 'pjbody'); wrap.appendChild(bd); host.appendChild(wrap);
    bd.classList.toggle('solover', WEBM && pj.sel === 'aria' && !pj.wiz);   // Aria es fija para los miembros: su perfil se ve entero, sin botones de cambiar
    if (pj.wiz) paintWiz(); else if (nuevo) { inicio(bd); devSection(); } else tabBody(bd);
    if (window.pjScrollTop) { window.pjScrollTop = false; bd.scrollTop = 0; host.scrollTop = 0; } else if (keep) bd.scrollTop = keep; // al abrir un creador se empieza arriba
    devSection();
  };
  function devSection() { // el 💬 Feedback flotante solo en lo que está en desarrollo
    if (!window.feedbackSection) return; const w = pj.wiz; const p = pj.sel === 'aria' ? null : cur();
    if (w) { const S = stepsOf(w); const st = (S[w.step] || {}).t; feedbackSection(`Crear personaje · ${w.editId ? 'Editar' : w.mode === 'fotos' ? 'Desde tus favoritas' : w.mode === 'tengo' ? 'Ya tengo mi personaje' : 'Empezar desde cero'} · ${st}`); window.fbContext = () => `personaje ${w.editId || 'nuevo'} · paso ${w.step + 1}`; }
    else if (p) { const stg = { explorar: '1 · Su cara', vistas: '2 · Sus 4 vistas', cuerpo: '3 · Su cuerpo', lista: '4 · Ficha principal' }[pj.forceStage && pj.forceStage[p.id] || stageOf(p)]; feedbackSection(`Crear personaje · ${p.nombre} · ${stg}`); window.fbContext = () => `personaje ${p.id} · pestaña ${pj.tabBy[p.id] || 'ficha'}`; }
    else if (document.querySelector('#profcard .pjstart')) feedbackSection('Crear personaje · elegir cómo empezar');
    else { feedbackSection(null); window.fbContext = null; }
  }
  // panel izquierdo del Perfil: el personaje elegido con el mismo formato que Aria; con el asistente abierto, el índice de pasos y lo elegido
  window.pjPerfil = function () {
    const p = pj.sel === 'aria' ? null : cur(); if (!p) return C.perfil; const img0 = p.combo || p.ficha360 || p['vista_frente'] || p.foto || ''; const o = p.perfil || {}; const od = o.datos || {};
    const rasgos = [p.ojosNombre ? 'Ojos ' + p.ojosNombre : es('ojos', p.ojos) && 'Ojos ' + es('ojos', p.ojos).toLowerCase(), p.peloNombre ? 'Pelo ' + p.peloNombre : es('peloColor', p.peloColor) && 'Pelo ' + es('peloColor', p.peloColor).toLowerCase(), p.peinado && p.peinado.name, es('piel', p.piel) && 'Piel ' + es('piel', p.piel).toLowerCase(), es('complexion', p.complexion)].filter(Boolean);
    return { id: p.id, name: p.nombre, handle: o.handle != null ? o.handle : (p.usuario || ''), tagline: [arr(p.rol).map(r => es('rol', r)).concat(p.rolTxt ? [p.rolTxt] : []).join(', '), p.edad ? p.edad + ' años' : ''].filter(Boolean).join(' · '), bio: o.bio != null ? o.bio : (p.bio || ''), avatar: p.avatar || p.foto || '', ficha: img0, basePrompt: p.promptEditado ? p.prompt : basePrompt(p), ig: o.ig || {},
      datos: Object.assign({ edad: p.edad ? p.edad + ' años' : '', altura: p.altura ? (p.altura / 100).toFixed(2).replace('.', ',') + ' m' : '', origen: '', idiomas: '', nacida: '', rasgos, personalidad: [arr(p.pers).map(x => es('pers', x)).join(', '), p.persTxt].filter(Boolean).join('. '), voz: [arr(p.voz).map(x => es('voz', x)).join(', '), p.frase].filter(Boolean).join(' · ') }, od) };
  };
  window.pjSetPerfil = async function (id, set) { // edición desde el panel de la izquierda: se guarda en su personaje
    const p = pj.list.find(x => x.id === id); if (!p) return null; const o = p.perfil = Object.assign({ datos: {} }, p.perfil || {});
    Object.entries(set).forEach(([k, v]) => { if (k === 'basePrompt') { p.prompt = v; p.promptEditado = true; } else if (k.startsWith('datos.')) o.datos[k.slice(6)] = v; else if (k.startsWith('ig.')) (o.ig = o.ig || {})[k.slice(3)] = v; else o[k] = v; });
    const r = await persist_(p); return r && r.ok ? pjPerfil() : null;
  };
  window.pjSaveAvatar = async function (id, data, src) { const p = pj.list.find(x => x.id === id); if (!p) return null; const files = { avatar: data }; if (src && src.startsWith('data:')) files.avatarSrc = src; const r = await persist_(p, { files }); return r && r.ok; };
  window.pjWizSide = function (side) { // devuelve true si ha pintado el panel del asistente
    if (!pj.wiz) return false; const w = pj.wiz, d = w.d; const S = stepsOf(w);
    const box = el('div', 'stack pjside'); S.forEach((s, i) => { const k = i; const b = el('button', 'pjsi' + (k === w.step ? ' on' : ''), `<i>${k + 1}</i>${s.t}`); b.onclick = () => { w.step = k; saveDraft(); paintWiz(); renderSide(); }; box.appendChild(b); });
    side.appendChild(sec(w.editId ? 'Editar personaje' : 'Crear personaje', box));
    const sum = [d.nombre, d.generoTxt || es('genero', d.genero), d.edad && d.edad + ' años', d.ojosNombre ? 'ojos ' + d.ojosNombre : es('ojos', d.ojos) && 'ojos ' + es('ojos', d.ojos).toLowerCase(), d.peloNombre ? 'pelo ' + d.peloNombre : es('peloColor', d.peloColor) && 'pelo ' + es('peloColor', d.peloColor).toLowerCase(), d.peinado && d.peinado.name, es('complexion', d.complexion), d.estilo === 'cartoon' && d.cartoon ? d.cartoon.name : es('estilo', d.estilo)].filter(Boolean);
    if (sum.length) { const ch = el('div', 'pc-chips'); sum.forEach(x => ch.appendChild(el('span', '', esc(x)))); side.appendChild(sec('Lo que llevas elegido', ch)); }
    return true;
  };
  // trabajos del personaje
  const _fin = window.finishJob, _fail = window.failJob;
  window.finishJob = function (job, st) { if (job.persona) return onJobDone(job, st); return _fin(job, st); };
  window.failJob = function (job, msg) { if (job.persona) return onJobFail(job, msg); return _fail(job, msg); };
  window.pjBody = p => bodyOf(p);   // su cuerpo en palabras, para los prompts de Crear imagen
  window.pjEyes = p => en('ojos', p.ojos) || (p.ojosHex ? p.ojosHex + ' colored' : '');
  window.pjHair = p => ({ color: colorOf(p, 'pelo') || en('peloColor', p.peloColor) || '', style: p.peinado ? (p.peinado.desc || p.peinado.name || '') : '' });   // su pelo (color y peinado) para Crear imagen: al recrear una foto no se queda el pelo de la foto   // color de ojos para la frase de identidad (también el elegido con las barras)
  window.pjStart = () => startWiz();
  window.pjReload = () => load();   // releer los personajes del disco (p. ej. al terminar una ficha nueva)
  load().then(() => { if (state.tab === 'perfil') { renderProfile(); renderSide(); } });
})();
