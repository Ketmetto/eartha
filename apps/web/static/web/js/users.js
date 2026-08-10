/* EARTHA — users.js
   Admin: every account, with submission/redemption/points stats and ban controls.
*/

const admin = Eartha.requireAdmin();
if (admin) {
  Eartha.renderHeader(admin, 'users');

  const listEl = document.getElementById('usersList');
  const searchInput = document.getElementById('usersSearch');

  let items = [];
  let nextPage = 1;
  let hasMore = true;
  let loading = false;
  let search = '';
  const open = { ban: new Set() };

  async function loadMore() {
    if (loading || !hasMore) return;
    loading = true;
    try {
      const data = await Eartha.fetchAdminUsers(nextPage, search);
      items = items.concat(data.items);
      hasMore = data.hasMore;
      nextPage += 1;
    } finally {
      loading = false;
    }
  }

  function wireSentinel() {
    const sentinel = document.getElementById('usersSentinel');
    if (!sentinel) return;
    const io = new IntersectionObserver((entries) => {
      if (!entries[0].isIntersecting) return;
      io.disconnect();
      loadMore().then(render);
    }, { rootMargin: '600px' });
    io.observe(sentinel);
  }

  function actionArea(u) {
    if (open.ban.has(u.id)) {
      return `
        <div style="width:100%;">
          <div class="field" style="margin-bottom:14px;">
            <label for="reason-${u.id}">BAN REASON (OPTIONAL, FOR YOUR OWN RECORD)</label>
            <textarea id="reason-${u.id}" placeholder="e.g. Repeated fake submissions"></textarea>
          </div>
          <div style="display:flex;gap:10px;">
            <button class="btn btn-sm" data-act="ban-confirm" data-id="${u.id}">BAN — BLOCK LOGIN</button>
            <button class="btn btn-ghost btn-sm" data-act="ban-cancel" data-id="${u.id}">CANCEL</button>
          </div>
        </div>`;
    }
    if (u.isStaff) {
      return `<p class="muted" style="font-size:11px;">ADMIN ACCOUNTS CAN'T BE BANNED HERE.</p>`;
    }
    return u.isActive
      ? `<button class="btn btn-ghost btn-sm" data-act="ban" data-id="${u.id}">BAN</button>`
      : `<button class="btn btn-sm" data-act="unban" data-id="${u.id}">UNBAN</button>`;
  }

  function card(u) {
    const statusLine = u.isActive
      ? ''
      : `<p style="font-size:11px;margin-top:4px;color:var(--bad);">BANNED${u.banReason ? ' — ' + Eartha.esc(u.banReason) : ''}</p>`;
    return `
    <div class="card" data-card="${u.id}">
      <div class="card-row">
        <div style="flex:1;min-width:220px;">
          <p class="batch-tag">${Eartha.esc(u.name.toUpperCase())} · ${Eartha.esc(u.email)}</p>
          <p class="muted" style="font-size:11px;margin-top:4px;">
            JOINED ${Eartha.fmtDate(u.joinedAt)} · ${u.submissionsCount} SUBMISSIONS · ${u.redemptionsCount} REDEMPTIONS · ${u.pointsBalance} PTS
          </p>
          ${statusLine}
        </div>
        <div style="text-align:right;">
          <span class="badge ${u.isActive ? 'badge-completed' : 'badge-rejected'}">${u.isActive ? 'ACTIVE' : 'BANNED'}</span>
        </div>
      </div>
      <div style="margin-top:16px;border-top:1px solid var(--line);padding-top:16px;">${actionArea(u)}</div>
    </div>`;
  }

  function render() {
    document.getElementById('usersSummary').textContent = `${items.length} OF ${items.length + (hasMore ? '+' : '')} USERS`;
    listEl.innerHTML = items.length
      ? items.map(card).join('') + (hasMore ? '<div id="usersSentinel" class="empty">LOADING MORE…</div>' : '')
      : '<div class="empty">NO USERS MATCH.</div>';
    if (hasMore) wireSentinel();
  }

  async function reset() {
    items = [];
    nextPage = 1;
    hasMore = true;
    open.ban.clear();
    try {
      await loadMore();
    } catch (err) {
      listEl.innerHTML = `<div class="empty">${Eartha.esc(err.message || 'COULD NOT LOAD USERS.')}</div>`;
      return;
    }
    render();
  }

  let searchTimer = null;
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      search = searchInput.value.trim();
      reset();
    }, 300);
  });

  listEl.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-act]');
    if (!btn) return;
    const act = btn.dataset.act;
    const id = btn.dataset.id;

    if (act === 'ban') {
      open.ban.add(id);
      render();
      return;
    }
    if (act === 'ban-cancel') {
      open.ban.delete(id);
      render();
      return;
    }

    try {
      if (act === 'ban-confirm') {
        const reason = document.getElementById('reason-' + id).value.trim();
        const updated = await Eartha.banUser(id, reason);
        items = items.map((u) => (u.id === updated.id ? updated : u));
        open.ban.delete(id);
        Eartha.toast('USER BANNED.');
      } else if (act === 'unban') {
        const updated = await Eartha.unbanUser(id);
        items = items.map((u) => (u.id === updated.id ? updated : u));
        Eartha.toast('USER UNBANNED.');
      }
      render();
    } catch (err) {
      Eartha.toast(err.message || 'SOMETHING WENT WRONG.');
    }
  });

  reset();
}
