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
  EarthaAddressAutocomplete(
    addressInput, mapsKey, document.getElementById('pickupMap'),
    (parts) => { addressParts = parts; }, document.getElementById('setLocate')
  );
  addressInput.addEventListener('input', () => { addressParts = null; });
  const buildingInput = document.getElementById('setBuilding');
  const floorUnitInput = document.getElementById('setFloorUnit');
  const instructionsInput = document.getElementById('setInstructions');

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
  // collection onward — not derivable from status/condition alone (an admin
  // may award more, less, or 0). awardedPoints comes straight from the
  // ledger via the API; null means not yet awarded, see apps.points.services.
  // Paginated + infinite scroll — a long-time user's history can outgrow
  // one response (same pattern as the admin queue's done tab).
  let subsItems = [];
  let subsNextPage = 1;
  let subsHasMore = true;
  let subsLoading = false;

  async function loadMoreSubs() {
    if (subsLoading || !subsHasMore) return;
    subsLoading = true;
    try {
      const { items, hasMore } = await Eartha.fetchMySubmissions(subsNextPage, subsItems.length);
      subsItems = subsItems.concat(items);
      subsHasMore = hasMore;
      subsNextPage += 1;
    } finally {
      subsLoading = false;
    }
  }

  function wireSubsSentinel() {
    const sentinel = document.getElementById('subsSentinel');
    if (!sentinel) return;
    const io = new IntersectionObserver((entries) => {
      if (!entries[0].isIntersecting) return;
      io.disconnect();
      loadMoreSubs().then(renderSubsList);
    }, { rootMargin: '600px' });
    io.observe(sentinel);
  }

  function renderSubsList() {
    const subsBody = document.getElementById('subsBody');
    document.getElementById('subsEmpty').hidden = subsItems.length > 0;
    const rows = subsItems
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
    const sentinel = subsHasMore
      ? '<tr id="subsSentinel"><td colspan="5" class="muted" style="text-align:center;font-size:11px;">LOADING MORE…</td></tr>'
      : '';
    subsBody.innerHTML = rows + sentinel;
    if (subsHasMore) wireSubsSentinel();
  }

  async function renderSubs() {
    subsItems = [];
    subsNextPage = 1;
    subsHasMore = true;
    try {
      await loadMoreSubs();
    } catch (err) {
      Eartha.toast(err.message || 'COULD NOT LOAD YOUR SUBMISSIONS.');
    }
    renderSubsList();
  }

  // ---------- redemption history ----------
  let redsItems = [];
  let redsNextPage = 1;
  let redsHasMore = true;
  let redsLoading = false;

  async function loadMoreReds() {
    if (redsLoading || !redsHasMore) return;
    redsLoading = true;
    try {
      const { items, hasMore } = await Eartha.fetchMyRedemptions(redsNextPage);
      redsItems = redsItems.concat(items);
      redsHasMore = hasMore;
      redsNextPage += 1;
    } finally {
      redsLoading = false;
    }
  }

  function wireRedsSentinel() {
    const sentinel = document.getElementById('redsSentinel');
    if (!sentinel) return;
    const io = new IntersectionObserver((entries) => {
      if (!entries[0].isIntersecting) return;
      io.disconnect();
      loadMoreReds().then(renderRedsList);
    }, { rootMargin: '600px' });
    io.observe(sentinel);
  }

  function renderRedsList() {
    const redsBody = document.getElementById('redsBody');
    document.getElementById('redsEmpty').hidden = redsItems.length > 0;
    const rows = redsItems
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
    const sentinel = redsHasMore
      ? '<tr id="redsSentinel"><td colspan="5" class="muted" style="text-align:center;font-size:11px;">LOADING MORE…</td></tr>'
      : '';
    redsBody.innerHTML = rows + sentinel;
    if (redsHasMore) wireRedsSentinel();
  }

  async function renderReds() {
    redsItems = [];
    redsNextPage = 1;
    redsHasMore = true;
    try {
      await loadMoreReds();
    } catch (err) {
      Eartha.toast(err.message || 'COULD NOT LOAD YOUR REDEMPTIONS.');
    }
    renderRedsList();
  }

  // ---------- settings ----------
  function showEmailHint(pendingEmail) {
    const hint = document.getElementById('setEmailHint');
    if (pendingEmail) {
      hint.textContent = `CONFIRMATION SENT TO ${pendingEmail.toUpperCase()} — CHANGE APPLIES ONCE YOU CLICK THE LINK.`;
      hint.hidden = false;
    } else {
      hint.hidden = true;
    }
  }

  async function loadSettings() {
    try {
      const [me, address, prefs] = await Promise.all([
        Eartha.fetchMe(),
        Eartha.fetchAddress(),
        Eartha.fetchNotificationPrefs(),
      ]);
      document.getElementById('setName').value = [me.first_name, me.last_name].filter(Boolean).join(' ');
      document.getElementById('setEmail').value = me.email;
      document.getElementById('setPhone').value = me.phone || '';
      document.getElementById('setAddress').value = address.line1 || '';
      buildingInput.value = address.building || '';
      floorUnitInput.value = address.floor_unit || '';
      instructionsInput.value = address.instructions || '';
      document.getElementById('setNotify').checked = prefs.email_enabled;
      showEmailHint(me.pending_email);
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
    const phone = document.getElementById('setPhone').value.trim();
    const typedAddress = addressInput.value.trim();
    // addressParts (city/country/postal_code) only exists if a real
    // autocomplete suggestion was picked — otherwise fall back to the
    // plain typed line, same as before this integration existed.
    // building/floor_unit/instructions are independent manual fields, not
    // something Places Autocomplete resolves, so they're merged in either way.
    const address = {
      ...(addressParts || {}),
      line1: (addressParts && addressParts.line1) || typedAddress,
      building: buildingInput.value.trim(),
      floor_unit: floorUnitInput.value.trim(),
      instructions: instructionsInput.value.trim(),
    };
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
      user = await Eartha.updateMe({ name, email, phone });
      await Eartha.updateAddress(address);
      await Eartha.updateNotificationPrefs({ email_enabled: notify });
      if (newPassword) {
        await Eartha.changePassword(currentPassword, newPassword, newPassword);
      }

      document.getElementById('setPassword').value = '';
      document.getElementById('setCurrentPassword').value = '';
      document.getElementById('helloLine').textContent = `HELLO, ${user.name.toUpperCase()}`;
      // A changed email doesn't take effect immediately — see
      // apps.users.services.request_email_change — so the field reverts
      // to the still-current address rather than showing the unconfirmed one.
      document.getElementById('setEmail').value = user.email;
      showEmailHint(user.pendingEmail);
      msg.textContent = user.pendingEmail
        ? `SAVED — CHECK ${user.pendingEmail.toUpperCase()} TO CONFIRM YOUR NEW EMAIL.`
        : 'SAVED.';
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
