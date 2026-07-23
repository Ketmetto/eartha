/* ============================================================
   EARTHA — store.js
   Data layer · auth · seed data · shared UI helpers
   All state in localStorage under the "eartha:" namespace.
   ============================================================ */

const Eartha = (() => {
  const NS = 'eartha:';
  const KEYS = {
    users: NS + 'users',
    session: NS + 'session',
    profile: NS + 'profile',
    submissions: NS + 'submissions',
    drivers: NS + 'drivers',
    benefits: NS + 'benefits',
    benefitsVersion: NS + 'benefitsVersion',
    redemptions: NS + 'redemptions',
    messages: NS + 'messages',
    counter: NS + 'counter',
  };

  // ---------- storage primitives ----------
  const read = (key, fallback) => {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch {
      return fallback;
    }
  };

  const write = (key, value) => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (e) {
      console.error('Storage write failed', e);
      toast('STORAGE FULL — TRY FEWER / SMALLER PHOTOS');
      return false;
    }
  };

  const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 7);

  // Running batch number — the N. 0001 motif
  const nextBatchNum = () => {
    const n = read(KEYS.counter, 0) + 1;
    write(KEYS.counter, n);
    return 'N. ' + String(n).padStart(4, '0');
  };

  // ---------- seed ----------
  const POINTS_CRITERIA = {
    'like new': 100,
    'good': 70,
    'worn': 40,
    'damaged': 15,
  };

  // current partner catalog — bump BENEFITS_VERSION whenever this list
  // changes so returning visitors' stale localStorage picks up the update
  const BENEFITS_VERSION = 2;
  const defaultBenefits = () => [
    { id: uid(), brand: 'ByEartha', discount: 20, pointsRequired: 180, category: 'fashion', active: true, order: 0, image: '/static/web/images/image-1.png' },
    { id: uid(), brand: 'BRIO Bags', discount: 15, pointsRequired: 140, category: 'fashion', active: true, order: 1, image: '/static/web/images/image-4.png' },
    { id: uid(), brand: 'Alexandra Hakim', discount: 25, pointsRequired: 260, category: 'fashion', active: true, order: 2, image: '/static/web/images/image-7.png' },
    { id: uid(), brand: 'Warshe Sociale', discount: 15, pointsRequired: 120, category: 'food', active: true, order: 3, image: '/static/web/images/image-11.jpg' },
    { id: uid(), brand: "Neam's", discount: 20, pointsRequired: 160, category: 'beauty', active: true, order: 4, image: '/static/web/images/image-13.jpg' },
    { id: uid(), brand: 'Vivid Dreams', discount: 10, pointsRequired: 90, category: 'beauty', active: true, order: 5, image: '/static/web/images/image-3.png' },
    { id: uid(), brand: 'Walkaway', discount: 30, pointsRequired: 300, category: 'lifestyle', active: true, order: 6, image: '/static/web/images/image-9.jpg' },
    { id: uid(), brand: "Nada's Candles", discount: 15, pointsRequired: 130, category: 'lifestyle', active: true, order: 7, image: '/static/web/images/image-5.png' },
  ];

  // refreshes just the benefits catalog for visitors with existing
  // localStorage, without touching their users/points/submissions
  function syncBenefits() {
    if (read(KEYS.benefitsVersion, 0) >= BENEFITS_VERSION) return;
    write(KEYS.benefits, defaultBenefits());
    write(KEYS.benefitsVersion, BENEFITS_VERSION);
  }

  function seed() {
    if (read(KEYS.users, null)) {
      syncBenefits();
      return;
    }

    const adminId = uid();
    const demoId = uid();

    write(KEYS.users, [
      {
        id: adminId,
        name: 'Eartha Admin',
        email: 'admin@eartha.co',
        password: 'admin123',
        address: '',
        points: 0,
        isAdmin: true,
        createdAt: Date.now(),
      },
      {
        id: demoId,
        name: 'Demo User',
        email: 'demo@eartha.co',
        password: 'demo1234',
        address: 'Hamra Street, Beirut',
        points: 240,
        isAdmin: false,
        createdAt: Date.now(),
      },
    ]);

    write(KEYS.drivers, [
      { id: uid(), name: 'Karim H.', phone: '+961 70 000 001' },
      { id: uid(), name: 'Layla S.', phone: '+961 71 000 002' },
      { id: uid(), name: 'Omar T.', phone: '+961 76 000 003' },
    ]);

    write(KEYS.counter, 2);
    write(KEYS.submissions, [
      {
        id: uid(),
        num: 'N. 0001',
        userId: demoId,
        category: 'clothing',
        condition: 'good',
        photos: [],
        description: 'Beige linen shirt, barely worn.',
        status: 'completed',
        rejectReason: '',
        driverId: null,
        driverName: 'Karim H.',
        points: 70,
        createdAt: Date.now() - 86400000 * 12,
        updatedAt: Date.now() - 86400000 * 9,
      },
      {
        id: uid(),
        num: 'N. 0002',
        userId: demoId,
        category: 'clothing',
        condition: 'like new',
        photos: [],
        description: 'Grey knit sweater.',
        status: 'pending',
        rejectReason: '',
        driverId: null,
        driverName: '',
        points: 0,
        createdAt: Date.now() - 86400000 * 1,
        updatedAt: Date.now() - 86400000 * 1,
      },
    ]);

    write(KEYS.benefits, defaultBenefits());
    write(KEYS.benefitsVersion, BENEFITS_VERSION);

    write(KEYS.redemptions, [
      {
        id: uid(),
        userId: demoId,
        brand: 'BRIO Bags',
        discount: 15,
        points: 140,
        code: 'EARTHA-BB140',
        date: Date.now() - 86400000 * 5,
      },
    ]);

    write(KEYS.messages, []);
  }

  // ---------- auth ----------
  // Real accounts, backed by the Django API (JWT). The mock users() array
  // below still powers pages that aren't wired to the backend yet
  // (dashboard/queue stats, profile editing) — currentUser() no longer
  // reads from it.
  const users = () => read(KEYS.users, []);
  const saveUsers = (list) => write(KEYS.users, list);

  const AUTH_API = '/api/v1/auth';

  const session = () => read(KEYS.session, null); // { access, refresh }

  const currentUser = () => read(KEYS.profile, null);

  function extractErrorMessage(data) {
    if (!data) return null;
    if (typeof data.detail === 'string') return data.detail;
    const firstKey = Object.keys(data)[0];
    const val = firstKey && data[firstKey];
    if (Array.isArray(val)) return val[0];
    if (typeof val === 'string') return val;
    return null;
  }

  function getCookie(name) {
    const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : null;
  }

  async function authRequest(path, { method = 'GET', body, token } = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    // Django's CSRF middleware enforces this on session-authenticated
    // requests (e.g. if this browser also has an active admin/browsable-API
    // session) — harmless to send even when no session cookie exists.
    if (method !== 'GET') {
      const csrfToken = getCookie('csrftoken');
      if (csrfToken) headers['X-CSRFToken'] = csrfToken;
    }
    const res = await fetch(AUTH_API + path, {
      method,
      headers,
      credentials: 'same-origin',
      body: body ? JSON.stringify(body) : undefined,
    });
    let data = null;
    try { data = await res.json(); } catch { /* empty body */ }
    if (!res.ok) {
      throw new Error(extractErrorMessage(data) || `REQUEST FAILED (${res.status}).`);
    }
    return data;
  }

  function profileFromApiUser(apiUser) {
    const name = [apiUser.first_name, apiUser.last_name].filter(Boolean).join(' ').trim() || apiUser.email;
    return {
      id: apiUser.id,
      name,
      email: apiUser.email,
      isAdmin: !!apiUser.is_staff,
      points: 0,
    };
  }

  async function register({ name, email, password, passwordConfirm, agreeToTerms }) {
    email = email.trim().toLowerCase();
    try {
      await authRequest('/register/', {
        method: 'POST',
        body: {
          email,
          full_name: name.trim(),
          password,
          password_confirm: passwordConfirm,
          agree_to_terms: agreeToTerms,
        },
      });
    } catch (e) {
      return { error: e.message.toUpperCase() };
    }
    // registration doesn't return tokens — log the new account straight in
    return login(email, password);
  }

  async function establishSession(tokens) {
    write(KEYS.session, tokens);
    const apiUser = await authRequest('/me/', { token: tokens.access });
    const profile = profileFromApiUser(apiUser);
    write(KEYS.profile, profile);
    return profile;
  }

  async function login(email, password) {
    email = email.trim().toLowerCase();
    let tokens;
    try {
      tokens = await authRequest('/login/', { method: 'POST', body: { email, password } });
    } catch (e) {
      return { error: e.message.toUpperCase() };
    }
    return { user: await establishSession(tokens) };
  }

  // body: { id_token, display_name } from the Firebase sign-in SDK
  // (covers both Google and Apple — Firebase issues one token shape).
  async function socialLogin(body) {
    let tokens;
    try {
      tokens = await authRequest('/social/firebase/', { method: 'POST', body });
    } catch (e) {
      return { error: e.message.toUpperCase() };
    }
    return { user: await establishSession(tokens) };
  }

  function logout() {
    localStorage.removeItem(KEYS.session);
    localStorage.removeItem(KEYS.profile);
    location.href = '/login/';
  }

  function updateUser(id, patch) {
    const list = users().map((u) => (u.id === id ? { ...u, ...patch } : u));
    saveUsers(list);
    return list.find((u) => u.id === id);
  }

  // page guards
  function requireAuth() {
    const u = currentUser();
    if (!u) { location.href = '/login/'; return null; }
    return u;
  }

  function requireAdmin() {
    const u = currentUser();
    if (!u) { location.href = '/login/'; return null; }
    if (!u.isAdmin) { location.href = '/upload/'; return null; }
    return u;
  }

  // ---------- submissions ----------
  const submissions = () => read(KEYS.submissions, []);
  const saveSubmissions = (list) => write(KEYS.submissions, list);

  function addSubmission({ userId, category, condition, photos, description }) {
    const sub = {
      id: uid(),
      num: nextBatchNum(),
      userId,
      category,
      condition,
      photos,
      description,
      status: 'pending',
      rejectReason: '',
      driverId: null,
      driverName: '',
      points: 0,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    const ok = saveSubmissions([sub, ...submissions()]);
    return ok ? sub : null;
  }

  function updateSubmission(id, patch) {
    const list = submissions().map((s) =>
      s.id === id ? { ...s, ...patch, updatedAt: Date.now() } : s
    );
    saveSubmissions(list);
    return list.find((s) => s.id === id);
  }

  // lifecycle: pending → accepted → dispatched → collected → completed | rejected
  const acceptSubmission = (id) => updateSubmission(id, { status: 'accepted' });
  const rejectSubmission = (id, reason) => updateSubmission(id, { status: 'rejected', rejectReason: reason });
  const dispatchSubmission = (id, driver) =>
    updateSubmission(id, { status: 'dispatched', driverId: driver.id, driverName: driver.name });
  const collectSubmission = (id) => updateSubmission(id, { status: 'collected' });

  function completeSubmission(id, points) {
    const sub = updateSubmission(id, { status: 'completed', points });
    const user = users().find((u) => u.id === sub.userId);
    if (user) updateUser(user.id, { points: (user.points || 0) + points });
    return sub;
  }

  // ---------- drivers ----------
  const drivers = () => read(KEYS.drivers, []);

  // ---------- benefits ----------
  const benefits = () => read(KEYS.benefits, []).sort((a, b) => a.order - b.order);
  const saveBenefits = (list) => write(KEYS.benefits, list);

  function addBenefit({ brand, discount, pointsRequired, category, image }) {
    const list = benefits();
    const b = {
      id: uid(),
      brand: brand.trim(),
      discount: Number(discount),
      pointsRequired: Number(pointsRequired),
      category,
      image: image || '',
      active: true,
      order: list.length,
    };
    saveBenefits([...list, b]);
    return b;
  }

  function updateBenefit(id, patch) {
    saveBenefits(benefits().map((b) => (b.id === id ? { ...b, ...patch } : b)));
  }

  function removeBenefit(id) {
    saveBenefits(benefits().filter((b) => b.id !== id).map((b, i) => ({ ...b, order: i })));
  }

  function reorderBenefits(orderedIds) {
    const list = benefits();
    const byId = Object.fromEntries(list.map((b) => [b.id, b]));
    const seen = new Set(orderedIds);
    const reordered = orderedIds.filter((id) => byId[id]).map((id) => byId[id]);
    const rest = list.filter((b) => !seen.has(b.id)); // keep items outside the current view
    saveBenefits([...reordered, ...rest].map((b, i) => ({ ...b, order: i })));
  }

  // ---------- redemptions ----------
  const redemptions = () => read(KEYS.redemptions, []);

  function redeemBenefit(user, benefit) {
    if ((user.points || 0) < benefit.pointsRequired) return { error: 'NOT ENOUGH POINTS YET.' };
    const code =
      'EARTHA-' +
      benefit.brand.split(/\s+/).map((w) => w[0]).join('').toUpperCase().slice(0, 3) +
      benefit.pointsRequired;
    const entry = {
      id: uid(),
      userId: user.id,
      brand: benefit.brand,
      discount: benefit.discount,
      points: benefit.pointsRequired,
      code,
      date: Date.now(),
    };
    write(KEYS.redemptions, [entry, ...redemptions()]);
    updateUser(user.id, { points: user.points - benefit.pointsRequired });
    return { entry };
  }

  // ---------- contact messages ----------
  const messages = () => read(KEYS.messages, []);
  function addMessage({ name, email, subject, body }) {
    write(KEYS.messages, [
      { id: uid(), name, email, subject, body, date: Date.now(), read: false },
      ...messages(),
    ]);
  }
  const markMessageRead = (id) =>
    write(KEYS.messages, messages().map((m) => (m.id === id ? { ...m, read: true } : m)));

  // ---------- image compression (keeps localStorage sane) ----------
  function compressImage(file, maxDim = 480, quality = 0.7) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const img = new Image();
        img.onload = () => {
          const scale = Math.min(1, maxDim / Math.max(img.width, img.height));
          const canvas = document.createElement('canvas');
          canvas.width = Math.round(img.width * scale);
          canvas.height = Math.round(img.height * scale);
          canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
          resolve(canvas.toDataURL('image/jpeg', quality));
        };
        img.onerror = reject;
        img.src = reader.result;
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  // ---------- UI helpers ----------
  let toastTimer;
  function toast(text) {
    let el = document.querySelector('.toast');
    if (!el) {
      el = document.createElement('div');
      el.className = 'toast';
      document.body.appendChild(el);
    }
    el.textContent = text;
    requestAnimationFrame(() => el.classList.add('is-visible'));
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('is-visible'), 3200);
  }

  const fmtDate = (ts) =>
    new Date(ts).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase();

  const esc = (s) =>
    String(s ?? '').replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
    );

  const badge = (status) =>
    `<span class="badge badge-${status}">${status.toUpperCase()}</span>`;

  const MENU_TOGGLE_HTML = `
    <button class="menu-toggle" id="menuToggle" aria-expanded="false" aria-controls="appNav" aria-label="Toggle menu">
      <span class="menu-toggle-bars" aria-hidden="true"></span>
    </button>
  `;

  // wires the hamburger toggle: click to open/close, Escape and outside-click to close
  function initMenuToggle(header) {
    const toggle = document.getElementById('menuToggle');
    if (!toggle) return;
    const close = () => {
      header.classList.remove('is-menu-open');
      toggle.setAttribute('aria-expanded', 'false');
    };
    toggle.addEventListener('click', () => {
      const isOpen = header.classList.toggle('is-menu-open');
      toggle.setAttribute('aria-expanded', String(isOpen));
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') close();
    });
    document.addEventListener('click', (e) => {
      if (header.classList.contains('is-menu-open') && !header.contains(e.target)) close();
    });
    header.querySelectorAll('.app-nav a').forEach((a) => a.addEventListener('click', close));
  }

  // renders the shared header into #appHeader — public nav when logged out, app nav when logged in
  function renderHeader(user, current) {
    const el = document.getElementById('appHeader');
    if (!el) return;
    if (!user) {
      el.innerHTML = `
        <a href="/" class="logo"><img src="/static/web/images/logo-dark.svg" alt="EARTHA"></a>
        ${MENU_TOGGLE_HTML}
        <nav class="app-nav" id="appNav" aria-label="Public">
          <a href="/about/" class="${current === 'about' ? 'is-current' : ''}">ABOUT US</a>
          <a href="/contact/" class="${current === 'contact' ? 'is-current' : ''}">CONTACT</a>
          <a href="/login/" class="${current === 'login' ? 'is-current' : ''}">SIGN IN</a>
        </nav>
      `;
      initMenuToggle(el);
      return;
    }
    const adminLink = user.isAdmin
      ? `<a href="/queue/" class="${current === 'queue' ? 'is-current' : ''}">QUEUE</a>`
      : '';
    const profileLink = user.isAdmin
      ? ''
      : `<a href="/profile/" class="${current === 'profile' ? 'is-current' : ''}">PROFILE (<strong id="headerPts">${user.points || 0}</strong> PTS)</a>`;
    const logoHref = user.isAdmin ? '/dashboard/' : '/';
    el.innerHTML = `
      <a href="${logoHref}" class="logo"><img src="/static/web/images/logo-dark.svg" alt="EARTHA"></a>
      ${MENU_TOGGLE_HTML}
      <nav class="app-nav" id="appNav" aria-label="App">
        <a href="/upload/" class="${current === 'upload' ? 'is-current' : ''}">UPLOAD</a>
        <a href="/benefits/" class="${current === 'benefits' ? 'is-current' : ''}">BENEFITS</a>
        ${profileLink}
        ${adminLink}
        <button class="logout-btn" id="logoutBtn">LOGOUT</button>
      </nav>
    `;
    document.getElementById('logoutBtn').addEventListener('click', logout);
    initMenuToggle(el);
  }

  const refreshHeaderPts = () => {
    const u = currentUser();
    const el = document.getElementById('headerPts');
    if (u && el) el.textContent = u.points || 0;
  };

  // ---------- motion: page fade-in + scroll reveal ----------
  // tags the recurring structural blocks (page sections, page headers, the
  // auth split-view) so every page gets the same subtle motion without
  // hand-marking each HTML file. Footer is excluded — it sits at the very
  // bottom of the document so the reveal never reads as a real transition.
  const REVEAL_SELECTOR = 'main > section, .page-head, .auth-visual, .auth-panel';

  function initMotion() {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => document.body.classList.add('is-loaded'));
    });

    const targets = document.querySelectorAll(REVEAL_SELECTOR);
    if (!targets.length) return;
    targets.forEach((el) => el.classList.add('reveal'));

    if (!('IntersectionObserver' in window)) {
      targets.forEach((el) => el.classList.add('is-visible'));
      return;
    }

    // toggles on every crossing (not just once) so the reveal replays
    // whenever a section re-enters the viewport, scrolling either direction
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        entry.target.classList.toggle('is-visible', entry.isIntersecting);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -60px 0px' });

    targets.forEach((el) => io.observe(el));
  }

  document.addEventListener('DOMContentLoaded', initMotion);

  seed();

  return {
    POINTS_CRITERIA,
    currentUser, register, login, socialLogin, logout, updateUser, requireAuth, requireAdmin,
    users,
    submissions, addSubmission, updateSubmission,
    acceptSubmission, rejectSubmission, dispatchSubmission, collectSubmission, completeSubmission,
    drivers,
    benefits, addBenefit, updateBenefit, removeBenefit, reorderBenefits,
    redemptions, redeemBenefit,
    messages, addMessage, markMessageRead,
    compressImage, toast, fmtDate, esc, badge, renderHeader, refreshHeaderPts,
  };
})();
