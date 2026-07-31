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
    benefits: NS + 'benefits',
    benefitsVersion: NS + 'benefitsVersion',
    redemptions: NS + 'redemptions',
    messages: NS + 'messages',
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

  // ---------- seed ----------
  // Suggested default only, per condition — points are awarded at admin
  // discretion any time from dispatch onward (see queue.js's award
  // control), the admin can type a different amount. Not a guarantee.
  const POINTS_CRITERIA = {
    'like_new': 100,
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
  // below only backs benefits.js's redeem flow now — currentUser() never
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

  // uid/token come from the query string of the emailed verification link.
  async function verifyEmail(uid, token) {
    try {
      const res = await authRequest(`/verify-email/?uid=${encodeURIComponent(uid)}&token=${encodeURIComponent(token)}`);
      return { detail: res.detail };
    } catch (e) {
      return { error: e.message };
    }
  }

  // message: shown on the login page after redirect (e.g. "your access
  // changed, sign in again") — sessionStorage survives the navigation
  // without persisting once the tab closes.
  function logout(message) {
    localStorage.removeItem(KEYS.session);
    localStorage.removeItem(KEYS.profile);
    if (message) sessionStorage.setItem('eartha:flash', message);
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

  // ---------- authenticated API calls (real backend, not localStorage) ----------
  const API_ROOT = '/api/v1';

  async function refreshAccessToken() {
    const s = session();
    if (!s || !s.refresh) return null;
    try {
      const res = await fetch(AUTH_API + '/refresh/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ refresh: s.refresh }),
      });
      if (!res.ok) return null;
      const data = await res.json();
      const next = { ...s, access: data.access };
      write(KEYS.session, next);
      return next.access;
    } catch {
      return null;
    }
  }

  // isFormData: skips JSON.stringify/Content-Type so the browser can set
  // its own multipart boundary — needed for photo uploads.
  async function apiFetch(path, { method = 'GET', body, isFormData = false } = {}) {
    const s = session();
    if (!s || !s.access) throw new Error('YOU NEED TO SIGN IN AGAIN.');

    const doFetch = (token) => {
      const headers = { Authorization: `Bearer ${token}` };
      if (!isFormData) headers['Content-Type'] = 'application/json';
      if (method !== 'GET') {
        const csrfToken = getCookie('csrftoken');
        if (csrfToken) headers['X-CSRFToken'] = csrfToken;
      }
      return fetch(API_ROOT + path, {
        method,
        headers,
        credentials: 'same-origin',
        body: isFormData ? body : body ? JSON.stringify(body) : undefined,
      });
    };

    let res = await doFetch(s.access);
    if (res.status === 401) {
      const newAccess = await refreshAccessToken();
      if (!newAccess) {
        logout('SESSION EXPIRED — PLEASE SIGN IN AGAIN.');
        throw new Error('SESSION EXPIRED — PLEASE SIGN IN AGAIN.');
      }
      res = await doFetch(newAccess);
    }

    // A valid token that's now forbidden means permissions changed after
    // login (e.g. admin access was revoked) — every 403 in this API comes
    // from IsAdmin, so this can't misfire on a legitimate per-object 403.
    // Force a fresh login instead of leaving the user on a stale admin
    // page where every action would otherwise fail silently-ish.
    if (res.status === 403) {
      logout('YOUR ACCESS HAS CHANGED — PLEASE SIGN IN AGAIN.');
      throw new Error('YOUR ACCESS HAS CHANGED — PLEASE SIGN IN AGAIN.');
    }

    let data = null;
    try { data = await res.json(); } catch { /* empty body, e.g. 204 */ }
    if (!res.ok) {
      throw new Error(extractErrorMessage(data) || `REQUEST FAILED (${res.status}).`);
    }
    return data;
  }

  // num: a display-only "N. 0001" label derived from list position, since
  // the backend Item model doesn't store a sequence number.
  function mapItem(apiItem, num) {
    return {
      id: apiItem.id,
      num,
      category: apiItem.category,
      condition: apiItem.condition,
      description: apiItem.description,
      status: apiItem.status,
      rejectReason: apiItem.rejection_reason || '',
      photos: (apiItem.photos || []).map((p) => p.image),
      createdAt: new Date(apiItem.created_at).getTime(),
      // admin-only fields — present when fetched via the admin endpoints
      updatedAt: apiItem.updated_at ? new Date(apiItem.updated_at).getTime() : undefined,
      userId: apiItem.user,
      userName: apiItem.user_name,
      userEmail: apiItem.user_email,
      pickupAddress: apiItem.pickup_address,
      driverName: apiItem.driver_name,
      // null/undefined = not yet awarded; 0 is itself a valid award
      // (e.g. an item caught as misrepresented on inspection).
      awardedPoints: apiItem.awarded_points,
    };
  }

  async function fetchMySubmissions() {
    const list = await apiFetch('/submissions/');
    const total = list.length;
    return list.map((item, i) => mapItem(item, 'N. ' + String(total - i).padStart(4, '0')));
  }

  async function createSubmission({ category, condition, description, files }) {
    const form = new FormData();
    form.append('category', category);
    form.append('condition', condition);
    if (description) form.append('description', description);
    files.forEach((file) => form.append('photos', file));
    const item = await apiFetch('/submissions/', { method: 'POST', body: form, isFormData: true });
    return mapItem(item, null);
  }

  // ---------- admin: submissions pipeline ----------
  // num here is a per-list position label ("N. 0001"), oldest-first by
  // total count — purely cosmetic, doesn't attempt to match the number the
  // uploader saw (each user's own list numbers independently).
  async function fetchAdminSubmissions() {
    const list = await apiFetch('/submissions/admin/all/');
    const total = list.length;
    return list.map((item, i) => mapItem(item, 'N. ' + String(total - i).padStart(4, '0')));
  }

  async function acceptItem(id) {
    const item = await apiFetch(`/submissions/admin/${id}/decision/`, { method: 'POST', body: { action: 'accept' } });
    return mapItem(item, null);
  }

  async function rejectItem(id, reason) {
    const item = await apiFetch(`/submissions/admin/${id}/decision/`, {
      method: 'POST',
      body: { action: 'reject', rejection_reason: reason },
    });
    return mapItem(item, null);
  }

  // pickup address is derived server-side from the user's saved address —
  // admins only supply who's driving.
  async function dispatchItem(id, driverName) {
    await apiFetch(`/submissions/admin/${id}/dispatch/`, { method: 'POST', body: { driver_name: driverName } });
  }

  async function collectItem(id) {
    const item = await apiFetch(`/submissions/admin/${id}/collect/`, { method: 'POST' });
    return mapItem(item, null);
  }

  async function completeItem(id) {
    const item = await apiFetch(`/submissions/admin/${id}/complete/`, { method: 'POST' });
    return mapItem(item, null);
  }

  // Award or correct an item's points, at admin discretion — legal any
  // time from dispatched status onward. Note: points endpoints, not
  // submissions.
  async function awardItemPoints(id, points) {
    return apiFetch(`/points/admin/items/${id}/award/`, { method: 'POST', body: { points } });
  }

  // ---------- admin: benefits catalog ----------
  function mapBenefit(apiBenefit) {
    return {
      id: apiBenefit.id,
      brand: apiBenefit.brand_name,
      discount: apiBenefit.discount_percent,
      pointsRequired: apiBenefit.points_required,
      category: apiBenefit.category,
      active: apiBenefit.is_active,
      order: apiBenefit.display_priority,
      image: apiBenefit.logo,
    };
  }

  async function fetchBenefitsAdmin() {
    const list = await apiFetch('/points/admin/benefits/');
    return list.map(mapBenefit);
  }

  async function fetchActiveBenefits() {
    const list = await apiFetch('/points/benefits/');
    return list.map(mapBenefit);
  }

  // Only appended when `image` is a freshly-picked data: URL (from the
  // compressed-preview flow in benefits.js) — an existing benefit's `image`
  // is already an absolute server URL, which isn't a file to re-upload.
  async function dataUrlToBlob(dataUrl) {
    const res = await fetch(dataUrl);
    return res.blob();
  }

  async function benefitFormData({ brand, discount, pointsRequired, category, active, image }) {
    const form = new FormData();
    if (brand !== undefined) form.append('brand_name', brand);
    if (discount !== undefined) form.append('discount_percent', discount);
    if (pointsRequired !== undefined) form.append('points_required', pointsRequired);
    if (category !== undefined) form.append('category', category);
    if (active !== undefined) form.append('is_active', active);
    if (image && image.startsWith('data:')) {
      form.append('logo', await dataUrlToBlob(image), 'logo.jpg');
    }
    return form;
  }

  async function createBenefitAdmin({ brand, discount, pointsRequired, category, image }) {
    // DRF's multipart parser treats an *absent* boolean field as False (it
    // mirrors HTML checkbox semantics), not "use the model default" the way
    // JSON parsing does — so is_active must be sent explicitly here, or
    // every new benefit would silently be created hidden.
    const form = await benefitFormData({ brand, discount, pointsRequired, category, active: true, image });
    const b = await apiFetch('/points/admin/benefits/', { method: 'POST', body: form, isFormData: true });
    return mapBenefit(b);
  }

  async function updateBenefitAdmin(id, patch) {
    const form = await benefitFormData(patch);
    const b = await apiFetch(`/points/admin/benefits/${id}/`, { method: 'PATCH', body: form, isFormData: true });
    return mapBenefit(b);
  }

  async function removeBenefitAdmin(id) {
    await apiFetch(`/points/admin/benefits/${id}/`, { method: 'DELETE' });
  }

  async function reorderBenefitsAdmin(orderedIds) {
    await apiFetch('/points/admin/benefits/reorder/', { method: 'POST', body: { ids: orderedIds } });
  }

  // ---------- points: balance / redemptions ----------
  async function fetchBalance() {
    const data = await apiFetch('/points/balance/');
    return data.balance;
  }

  // Real redemption — spends points server-side and returns a unique code.
  // Named distinctly from the legacy local-only redeemBenefit(user, benefit)
  // below, which about.html's partner-logo strip still reads from.
  async function redeemBenefitApi(benefitId) {
    return apiFetch('/points/redeem/', { method: 'POST', body: { benefit: benefitId } });
  }

  async function fetchMyRedemptions() {
    const list = await apiFetch('/points/redemptions/');
    return list.map((r) => ({
      id: r.id,
      brand: r.brand_name,
      discount: r.discount_percent,
      code: r.code,
      points: r.points_spent,
      date: new Date(r.created_at).getTime(),
    }));
  }

  // ---------- admin: contact inbox ----------
  function mapMessage(m) {
    return {
      id: m.id,
      name: m.name,
      email: m.email,
      subject: m.subject,
      body: m.message,
      date: new Date(m.created_at).getTime(),
      read: m.resolved,
    };
  }

  async function fetchContactMessages() {
    const list = await apiFetch('/engagement/admin/messages/');
    return list.map(mapMessage);
  }

  async function resolveMessage(id) {
    await apiFetch(`/engagement/admin/messages/${id}/resolve/`, { method: 'POST' });
  }

  // ---------- admin: dashboard stats ----------
  async function fetchDashboardStats() {
    const data = await apiFetch('/engagement/admin/stats/');
    const total = data.recent_items.length;
    return {
      pendingCount: data.pending_count,
      inProgressCount: data.in_progress_count,
      completedCount: data.completed_count,
      unreadMessagesCount: data.unread_messages_count,
      totalPointsAwarded: data.total_points_awarded,
      donorCount: data.donor_count,
      liveBenefitsCount: data.live_benefits_count,
      recentItems: data.recent_items.map((item, i) => mapItem(item, 'N. ' + String(total - i).padStart(4, '0'))),
    };
  }

  // ---------- account: profile / address / notifications / password ----------
  async function fetchMe() {
    return apiFetch('/auth/me/');
  }

  async function updateMe({ name, email }) {
    const [first_name, ...rest] = name.trim().split(' ');
    const body = { email, first_name, last_name: rest.join(' ') };
    const apiUser = await apiFetch('/auth/me/', { method: 'PATCH', body });
    const profile = profileFromApiUser(apiUser);
    write(KEYS.profile, profile);
    return profile;
  }

  async function fetchAddress() {
    return apiFetch('/auth/me/address/');
  }

  // fields: {line1, city, country, postal_code} when Places Autocomplete
  // resolved a real suggestion, or a bare string for a manually-typed
  // address (Maps not configured, or the user didn't pick a suggestion) —
  // in which case only line1 is set and the rest stay blank, same as before
  // this integration existed.
  async function updateAddress(fields) {
    const body = typeof fields === 'string' ? { line1: fields } : fields;
    return apiFetch('/auth/me/address/', { method: 'PATCH', body });
  }

  async function fetchNotificationPrefs() {
    return apiFetch('/auth/me/notifications/');
  }

  async function updateNotificationPrefs(patch) {
    return apiFetch('/auth/me/notifications/', { method: 'PATCH', body: patch });
  }

  async function changePassword(oldPassword, newPassword, newPasswordConfirm) {
    return apiFetch('/auth/me/change-password/', {
      method: 'POST',
      body: { old_password: oldPassword, new_password: newPassword, new_password_confirm: newPasswordConfirm },
    });
  }

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
    // Not `addEventListener('click', logout)` — that would pass the click's
    // PointerEvent as logout's `message` argument, which then gets
    // stringified into sessionStorage and shown on the login page as the
    // literal text "[object PointerEvent]".
    document.getElementById('logoutBtn').addEventListener('click', () => logout());
    initMenuToggle(el);
    // user.points is a stale cached field — always correct the nav badge
    // against the real balance right after painting it.
    if (!user.isAdmin) refreshHeaderPts();
  }

  const refreshHeaderPts = async () => {
    const el = document.getElementById('headerPts');
    if (!el) return;
    try { el.textContent = await fetchBalance(); } catch { /* leave whatever's showing */ }
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
    currentUser, register, login, socialLogin, verifyEmail, logout, requireAuth, requireAdmin,
    fetchMySubmissions, createSubmission,
    fetchAdminSubmissions, acceptItem, rejectItem, dispatchItem, collectItem, completeItem, awardItemPoints,
    fetchBenefitsAdmin, fetchActiveBenefits, createBenefitAdmin, updateBenefitAdmin, removeBenefitAdmin, reorderBenefitsAdmin,
    fetchBalance, fetchMyRedemptions, redeemBenefitApi,
    fetchContactMessages, resolveMessage,
    fetchDashboardStats,
    fetchMe, updateMe, fetchAddress, updateAddress, fetchNotificationPrefs, updateNotificationPrefs, changePassword,
    benefits, addBenefit, updateBenefit, removeBenefit, reorderBenefits,
    redemptions, redeemBenefit,
    messages, addMessage, markMessageRead,
    compressImage, toast, fmtDate, esc, badge, renderHeader, refreshHeaderPts,
  };
})();
