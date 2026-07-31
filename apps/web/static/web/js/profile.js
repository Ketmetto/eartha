/* EARTHA — profile.js */

let user = Eartha.requireAuth();
if (user && user.isAdmin) location.href = '/dashboard/';
if (user && !user.isAdmin) {
  Eartha.renderHeader(user, 'profile');

  document.getElementById('helloLine').textContent = `HELLO, ${user.name.toUpperCase()}`;

  // ---------- pickup address autocomplete ----------
  // Set together when a real autocomplete suggestion is picked; cleared on
  // further manual typing so a stale structured address never gets sent
  // for text the user has since edited by hand.
  let addressParts = null;
  const addressInput = document.getElementById('setAddress');
  const mapsKey = JSON.parse(document.getElementById('google-maps-key').textContent);
  EarthaAddressAutocomplete(addressInput, mapsKey, document.getElementById('pickupMap'), (parts) => { addressParts = parts; });
  addressInput.addEventListener('input', () => { addressParts = null; });

  // ---------- balance ----------
  async function renderBalance() {
    let pts = 0;
    try { pts = await Eartha.fetchBalance(); } catch { /* leave at 0 */ }
    document.getElementById('ptsBig').textContent = pts + ' PTS';

    // progress toward the cheapest benefit you can't afford yet
    let benefits = [];
    try { benefits = await Eartha.fetchActiveBenefits(); } catch { /* leave empty */ }
    const targets = benefits.map((b) => b.pointsRequired).sort((a, b) => a - b);
    const next = targets.find((t) => t > pts);
    const bar = document.getElementById('ptsBar');
    const hint = document.getElementById('ptsHint');

    if (next) {
      bar.style.width = Math.min(100, Math.round((pts / next) * 100)) + '%';
      hint.textContent = `${next - pts} PTS TO YOUR NEXT REWARD (${next} PTS)`;
    } else if (targets.length) {
      bar.style.width = '100%';
      hint.textContent = 'YOU CAN REDEEM EVERY BENEFIT ON THE BOARD.';
    } else {
      bar.style.width = '0%';
      hint.textContent = '';
    }
  }

  // ---------- tabs ----------
  document.querySelectorAll('.tabs .tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tabs .tab').forEach((t) => t.classList.toggle('is-active', t === tab));
      document.querySelectorAll('.tab-panel').forEach((p) =>
        p.classList.toggle('is-active', p.id === 'panel-' + tab.dataset.panel)
      );
    });
  });

  // ---------- submission history ----------
  // Points are awarded by an admin at their discretion, any time from
  // dispatch onward — not derivable from status/condition alone (an admin
  // may award more, less, or 0). awardedPoints comes straight from the
  // ledger via the API; null means not yet awarded, see apps.points.services.
  async function renderSubs() {
    const subsBody = document.getElementById('subsBody');
    let subs = [];
    try {
      subs = await Eartha.fetchMySubmissions();
    } catch (err) {
      Eartha.toast(err.message || 'COULD NOT LOAD YOUR SUBMISSIONS.');
    }
    document.getElementById('subsEmpty').hidden = subs.length > 0;
    subsBody.innerHTML = subs
      .map(
        (s) => `
        <tr>
          <td>${s.num}</td>
          <td>${Eartha.fmtDate(s.createdAt)}</td>
          <td style="text-transform:uppercase;">${Eartha.esc(s.category)} · ${Eartha.esc(s.condition)}</td>
          <td>${Eartha.badge(s.status)}${s.status === 'rejected' && s.rejectReason ? `<div class="muted" style="font-size:10px;margin-top:4px;">${Eartha.esc(s.rejectReason)}</div>` : ''}</td>
          <td>${s.awardedPoints != null ? '+' + s.awardedPoints : '—'}</td>
        </tr>`
      )
      .join('');
  }

  // ---------- redemption history ----------
  async function renderReds() {
    const redsBody = document.getElementById('redsBody');
    let reds = [];
    try {
      reds = await Eartha.fetchMyRedemptions();
    } catch (err) {
      Eartha.toast(err.message || 'COULD NOT LOAD YOUR REDEMPTIONS.');
    }
    document.getElementById('redsEmpty').hidden = reds.length > 0;
    redsBody.innerHTML = reds
      .map(
        (r) => `
        <tr>
          <td>${Eartha.fmtDate(r.date)}</td>
          <td style="text-transform:uppercase;">${Eartha.esc(r.brand)}</td>
          <td>${r.discount}% OFF</td>
          <td style="font-weight:700;">${Eartha.esc(r.code)}</td>
          <td>−${r.points}</td>
        </tr>`
      )
      .join('');
  }

  // ---------- settings ----------
  async function loadSettings() {
    try {
      const [me, address, prefs] = await Promise.all([
        Eartha.fetchMe(),
        Eartha.fetchAddress(),
        Eartha.fetchNotificationPrefs(),
      ]);
      document.getElementById('setName').value = [me.first_name, me.last_name].filter(Boolean).join(' ');
      document.getElementById('setEmail').value = me.email;
      document.getElementById('setAddress').value = address.line1 || '';
      document.getElementById('setNotify').checked = prefs.email_enabled;
    } catch (err) {
      Eartha.toast(err.message || 'COULD NOT LOAD YOUR SETTINGS.');
    }
  }

  document.getElementById('settingsForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const msg = document.getElementById('settingsMsg');
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const name = document.getElementById('setName').value.trim();
    const email = document.getElementById('setEmail').value.trim().toLowerCase();
    const typedAddress = addressInput.value.trim();
    // addressParts (city/country/postal_code) only exists if a real
    // autocomplete suggestion was picked — otherwise fall back to the
    // plain typed line, same as before this integration existed.
    const address = addressParts ? { ...addressParts, line1: addressParts.line1 || typedAddress } : typedAddress;
    const currentPassword = document.getElementById('setCurrentPassword').value;
    const newPassword = document.getElementById('setPassword').value;
    const notify = document.getElementById('setNotify').checked;

    if (!name) { msg.textContent = 'NAME CAN\'T BE EMPTY.'; msg.className = 'form-msg is-error'; return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { msg.textContent = 'ENTER A VALID EMAIL ADDRESS.'; msg.className = 'form-msg is-error'; return; }
    if (newPassword && newPassword.length < 8) {
      msg.textContent = 'NEW PASSWORD MUST BE AT LEAST 8 CHARACTERS.'; msg.className = 'form-msg is-error'; return;
    }
    if (newPassword && !currentPassword) {
      msg.textContent = 'ENTER YOUR CURRENT PASSWORD TO SET A NEW ONE.'; msg.className = 'form-msg is-error'; return;
    }

    submitBtn.disabled = true;
    try {
      user = await Eartha.updateMe({ name, email });
      await Eartha.updateAddress(address);
      await Eartha.updateNotificationPrefs({ email_enabled: notify });
      if (newPassword) {
        await Eartha.changePassword(currentPassword, newPassword, newPassword);
      }

      document.getElementById('setPassword').value = '';
      document.getElementById('setCurrentPassword').value = '';
      document.getElementById('helloLine').textContent = `HELLO, ${user.name.toUpperCase()}`;
      msg.textContent = 'SAVED.';
      msg.className = 'form-msg is-ok';
    } catch (err) {
      msg.textContent = err.message || 'SOMETHING WENT WRONG.';
      msg.className = 'form-msg is-error';
    } finally {
      submitBtn.disabled = false;
    }
  });

  renderBalance();
  renderSubs();
  renderReds();
  loadSettings();
}
