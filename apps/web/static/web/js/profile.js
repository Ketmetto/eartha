/* EARTHA — profile.js */

let user = Eartha.requireAuth();
if (user && user.isAdmin) location.href = '/dashboard/';
if (user && !user.isAdmin) {
  Eartha.renderHeader(user, 'profile');

  document.getElementById('helloLine').textContent = `HELLO, ${user.name.toUpperCase()}`;

  // ---------- balance ----------
  function renderBalance() {
    user = Eartha.currentUser();
    const pts = user.points || 0;
    document.getElementById('ptsBig').textContent = pts + ' PTS';

    // progress toward the cheapest benefit you can't afford yet
    const targets = Eartha.benefits()
      .filter((b) => b.active)
      .map((b) => b.pointsRequired)
      .sort((a, b) => a - b);
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
  const subs = Eartha.submissions().filter((s) => s.userId === user.id).sort((a, b) => b.createdAt - a.createdAt);
  const subsBody = document.getElementById('subsBody');
  document.getElementById('subsEmpty').hidden = subs.length > 0;
  subsBody.innerHTML = subs
    .map(
      (s) => `
      <tr>
        <td>${s.num}</td>
        <td>${Eartha.fmtDate(s.createdAt)}</td>
        <td style="text-transform:uppercase;">${Eartha.esc(s.category)} · ${Eartha.esc(s.condition)}</td>
        <td>${Eartha.badge(s.status)}${s.status === 'rejected' && s.rejectReason ? `<div class="muted" style="font-size:10px;margin-top:4px;">${Eartha.esc(s.rejectReason)}</div>` : ''}</td>
        <td>${s.status === 'completed' ? '+' + s.points : '—'}</td>
      </tr>`
    )
    .join('');

  // ---------- redemption history ----------
  const reds = Eartha.redemptions().filter((r) => r.userId === user.id);
  const redsBody = document.getElementById('redsBody');
  document.getElementById('redsEmpty').hidden = reds.length > 0;
  redsBody.innerHTML = reds
    .map(
      (r) => `
      <tr>
        <td>${Eartha.fmtDate(r.date)}</td>
        <td style="text-transform:uppercase;">${Eartha.esc(r.brand)}</td>
        <td>${r.discount}% OFF</td>
        <td style="font-weight:700;">${r.code}</td>
        <td>−${r.points}</td>
      </tr>`
    )
    .join('');

  // ---------- settings ----------
  document.getElementById('setName').value = user.name;
  document.getElementById('setEmail').value = user.email;
  document.getElementById('setAddress').value = user.address || '';
  document.getElementById('setNotify').checked = user.notify !== false;

  document.getElementById('settingsForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const msg = document.getElementById('settingsMsg');
    const name = document.getElementById('setName').value.trim();
    const email = document.getElementById('setEmail').value.trim().toLowerCase();
    const address = document.getElementById('setAddress').value.trim();
    const password = document.getElementById('setPassword').value;
    const notify = document.getElementById('setNotify').checked;

    if (!name) { msg.textContent = 'NAME CAN\'T BE EMPTY.'; msg.className = 'form-msg is-error'; return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { msg.textContent = 'ENTER A VALID EMAIL ADDRESS.'; msg.className = 'form-msg is-error'; return; }
    if (Eartha.users().some((u) => u.email === email && u.id !== user.id)) {
      msg.textContent = 'THIS EMAIL IS USED BY ANOTHER ACCOUNT.'; msg.className = 'form-msg is-error'; return;
    }
    if (password && password.length < 8) {
      msg.textContent = 'NEW PASSWORD MUST BE AT LEAST 8 CHARACTERS.'; msg.className = 'form-msg is-error'; return;
    }

    const patch = { name, email, address, notify };
    if (password) patch.password = password;
    user = Eartha.updateUser(user.id, patch);

    document.getElementById('setPassword').value = '';
    document.getElementById('helloLine').textContent = `HELLO, ${user.name.toUpperCase()}`;
    msg.textContent = 'SAVED.';
    msg.className = 'form-msg is-ok';
  });

  renderBalance();
}
