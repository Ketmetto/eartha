/* EARTHA — queue.js
   One pipeline. Each card renders its single next action inline:
   pending → accept/reject → driver name → collected → close out → done.
*/

const admin = Eartha.requireAdmin();
if (admin) {
  Eartha.renderHeader(admin, 'queue');

  const listEl = document.getElementById('queueList');

  // ---------- tabs ----------
  document.querySelectorAll('.tabs .tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tabs .tab').forEach((t) => t.classList.toggle('is-active', t === tab));
      document.querySelectorAll('.tab-panel').forEach((p) =>
        p.classList.toggle('is-active', p.id === 'panel-' + tab.dataset.panel)
      );
    });
  });

  let filter = 'action';
  // per-card UI state that survives re-renders
  const open = { reject: new Set() };

  // ---------- data ----------
  // Action items (pending -> collected) come back in one unpaginated call —
  // that list is naturally bounded by how fast the queue gets worked.
  // Done items (completed/rejected) only ever grow, so they're paginated
  // and loaded a page at a time as the user scrolls (see loadMoreDone).
  let actionItems = [];
  let doneItems = [];
  let doneNextPage = 1;
  let doneTotal = 0;
  let doneHasMore = true;
  let doneLoading = false;

  async function loadMoreDone() {
    if (doneLoading || !doneHasMore) return;
    doneLoading = true;
    try {
      const { items, hasMore, count } = await Eartha.fetchAdminSubmissionsDone(doneNextPage, doneItems.length);
      doneItems = doneItems.concat(items);
      doneHasMore = hasMore;
      doneTotal = count;
      doneNextPage += 1;
    } finally {
      doneLoading = false;
    }
  }

  // Scrolling near the bottom of the list triggers the next page — this
  // sentinel element (rendered as the last row whenever more pages exist)
  // is what the IntersectionObserver below watches for.
  function wireDoneSentinel() {
    const sentinel = document.getElementById('doneSentinel');
    if (!sentinel) return;
    const io = new IntersectionObserver((entries) => {
      if (!entries[0].isIntersecting) return;
      io.disconnect();
      loadMoreDone().then(renderList);
    }, { rootMargin: '600px' });
    io.observe(sentinel);
  }

  const NEXT_LABEL = {
    pending: 'AWAITING REVIEW',
    accepted: 'NEEDS A DRIVER',
    dispatched: 'OUT FOR PICKUP',
    collected: 'READY TO CLOSE OUT',
    completed: 'DONE',
    rejected: 'CLOSED',
  };

  function photoStrip(s) {
    return s.photos.length
      ? `<div style="display:flex;gap:6px;">${s.photos.map((p) => `<img class="thumb-64" src="${p}" alt="">`).join('')}</div>`
      : '<div class="thumb-64"></div>';
  }

  // Award/correct points — shown once an item is dispatched onward, at
  // admin discretion (never automatic on accept, since acceptance only
  // screens photos, before the item is physically received). Pre-filled
  // from the condition's suggested default, but freely editable; 0 is a
  // valid award for a misrepresented item caught on physical inspection.
  function awardControl(s) {
    const suggested = Eartha.POINTS_CRITERIA[s.condition] ?? 0;
    const already = s.awardedPoints != null;
    const label = already ? `CORRECT AWARD (CURRENTLY ${s.awardedPoints} PTS)` : 'AWARD POINTS';
    return `
      <div style="display:flex;gap:8px;align-items:flex-end;margin-top:12px;">
        <div class="field" style="margin:0;width:100px;">
          <label for="award-${s.id}">${label}</label>
          <input type="number" min="0" id="award-${s.id}" value="${already ? s.awardedPoints : suggested}">
        </div>
        <button class="btn btn-ghost btn-sm" data-act="award" data-id="${s.id}">SAVE</button>
      </div>`;
  }

  function actionArea(s) {
    // reject panel (available while pending)
    if (open.reject.has(s.id)) {
      return `
        <div style="width:100%;">
          <div class="field" style="margin-bottom:14px;">
            <label for="reason-${s.id}">REASON — SENT TO THE USER</label>
            <textarea id="reason-${s.id}" placeholder="e.g. Photos too blurry to assess condition"></textarea>
          </div>
          <div style="display:flex;gap:10px;">
            <button class="btn btn-sm" data-act="reject-confirm" data-id="${s.id}">REJECT &amp; NOTIFY</button>
            <button class="btn btn-ghost btn-sm" data-act="reject-cancel" data-id="${s.id}">CANCEL</button>
          </div>
        </div>`;
    }

    switch (s.status) {
      case 'pending':
        return `
          <div style="display:flex;gap:10px;">
            <button class="btn btn-sm" data-act="accept" data-id="${s.id}">ACCEPT</button>
            <button class="btn btn-ghost btn-sm" data-act="reject" data-id="${s.id}">REJECT</button>
          </div>`;

      case 'accepted': {
        const noAddress = !s.pickupAddress;
        const noDrivers = driversList.length === 0;
        const disabledReason = noAddress ? 'User has no pickup address' : noDrivers ? 'Add a driver first, in the DRIVERS tab' : '';
        return `
          <div style="display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap;">
            <div class="field" style="margin:0;min-width:220px;">
              <label for="driver-${s.id}">DRIVER</label>
              <div class="select-wrap">
                <select id="driver-${s.id}" ${noDrivers ? 'disabled' : ''}>
                  ${noDrivers
                    ? '<option value="">NO DRIVERS YET</option>'
                    : driversList.map((d) => `<option value="${d.id}">${Eartha.esc(d.name)}</option>`).join('')}
                </select>
              </div>
            </div>
            <button class="btn btn-sm" data-act="dispatch" data-id="${s.id}" ${noAddress || noDrivers ? `disabled title="${disabledReason}"` : ''}>DISPATCH</button>
            <button class="btn btn-ghost btn-sm" data-act="reject" data-id="${s.id}" title="Correct a mistaken accept">UNDO — REJECT</button>
          </div>`;
      }

      case 'dispatched':
        return `<button class="btn btn-sm" data-act="collect" data-id="${s.id}">MARK COLLECTED</button>${awardControl(s)}`;

      case 'collected':
        return `<button class="btn btn-sm" data-act="complete" data-id="${s.id}">CONFIRM &amp; CLOSE OUT</button>${awardControl(s)}`;

      case 'completed': {
        const readout = s.awardedPoints != null
          ? `<p class="muted" style="font-size:11px;">+${s.awardedPoints} PTS · ${Eartha.fmtDate(s.updatedAt)}</p>`
          : '';
        return `${readout}${awardControl(s)}`;
      }

      case 'rejected':
        return `
          <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
            <p class="muted" style="font-size:11px;">REASON: ${Eartha.esc(s.rejectReason || '—')}</p>
            <button class="btn btn-ghost btn-sm" data-act="accept" data-id="${s.id}" title="Correct a mistaken reject">UNDO — ACCEPT</button>
          </div>`;
    }
    return '';
  }

  function card(s) {
    const addressLine =
      ['accepted', 'dispatched'].includes(s.status)
        ? `<p class="muted" style="font-size:11px;margin-top:4px;">PICKUP: ${s.pickupAddress ? Eartha.esc(s.pickupAddress) : '<span style="color:var(--bad);">NO ADDRESS ON PROFILE</span>'}</p>`
        : '';
    // Clickable WhatsApp link once there's a real phone — same reasoning
    // as the driver's number on the dispatch step, just for the uploader
    // this time, so whoever's coordinating pickup can actually reach them.
    const phoneDigits = (s.userPhone || '').replace(/\D/g, '');
    const phoneLine =
      ['accepted', 'dispatched'].includes(s.status)
        ? `<p class="muted" style="font-size:11px;margin-top:4px;">PHONE: ${
            phoneDigits
              ? `<a href="https://wa.me/${phoneDigits}" target="_blank" rel="noopener" class="link-underline">${Eartha.esc(s.userPhone)}</a>`
              : '<span style="color:var(--bad);">NO PHONE ON PROFILE</span>'
          }</p>`
        : '';
    const driverLine = s.driverName && s.status !== 'accepted'
      ? `<p class="muted" style="font-size:11px;margin-top:4px;">DRIVER: ${Eartha.esc(s.driverName)}</p>`
      : '';
    return `
    <div class="card" data-card="${s.id}">
      <div class="card-row">
        ${photoStrip(s)}
        <div style="flex:1;min-width:200px;">
          <p class="batch-tag">${s.num} · ${Eartha.fmtDate(s.createdAt)} · FROM ${Eartha.esc((s.userName || 'UNKNOWN').toUpperCase())}</p>
          <p style="font-weight:700;text-transform:uppercase;letter-spacing:var(--track-wide);font-size:12px;margin-top:2px;">
            ${Eartha.esc(s.category)} · ${Eartha.esc(s.condition)}
          </p>
          ${s.description ? `<p class="muted" style="font-size:11px;margin-top:4px;">"${Eartha.esc(s.description)}"</p>` : ''}
          ${addressLine}
          ${phoneLine}
          ${driverLine}
        </div>
        <div style="text-align:right;">
          ${Eartha.badge(s.status)}
          <p class="muted" style="font-size:10px;letter-spacing:var(--track-wide);margin-top:6px;">${NEXT_LABEL[s.status]}</p>
        </div>
      </div>
      <div style="margin-top:16px;border-top:1px solid var(--line);padding-top:16px;">${actionArea(s)}</div>
    </div>`;
  }

  // Re-renders from whatever's already loaded in actionItems/doneItems —
  // does not re-fetch. Safe to call as often as needed (e.g. on every
  // filter switch) since it's pure DOM work.
  function renderList() {
    document.getElementById('fCountAction').textContent = actionItems.length ? `(${actionItems.length})` : '';
    document.getElementById('fCountDone').textContent = doneTotal ? `(${doneTotal})` : '';
    document.getElementById('queueSummary').textContent =
      `${actionItems.length} NEED${actionItems.length === 1 ? 'S' : ''} ACTION · ${actionItems.length + doneTotal} TOTAL`;

    const view = filter === 'action' ? actionItems : filter === 'done' ? doneItems : actionItems.concat(doneItems);
    // Only the done/all views ever have more pages to fetch — the action
    // list is loaded in full up front.
    const showSentinel = filter !== 'action' && doneHasMore;

    listEl.innerHTML = view.length
      ? view.map(card).join('') + (showSentinel ? '<div id="doneSentinel" class="empty">LOADING MORE…</div>' : '')
      : `<div class="empty">${filter === 'action' ? 'QUEUE IS CLEAR — NOTHING NEEDS YOU RIGHT NOW.' : 'NOTHING HERE YET.'}</div>`;

    if (showSentinel) wireDoneSentinel();
  }

  // Fetches the action list in full plus the first page of done, then
  // renders. Called on initial load and after every action — an action can
  // move an item between the two lists, so both need a fresh first page;
  // any additional done pages the user had scrolled to are dropped and
  // would need re-loading, a reasonable tradeoff since actions normally
  // happen from the action tab, not deep in a scrolled done list.
  async function render() {
    try {
      actionItems = await Eartha.fetchAdminSubmissions();
    } catch (err) {
      listEl.innerHTML = `<div class="empty">${Eartha.esc(err.message || 'COULD NOT LOAD THE QUEUE.')}</div>`;
      return;
    }

    doneItems = [];
    doneNextPage = 1;
    doneHasMore = true;
    doneTotal = 0;
    try {
      await loadMoreDone();
    } catch { /* done tab/badge just won't populate; action tab still works */ }

    renderList();
  }

  // filters
  document.getElementById('queueFilters').addEventListener('click', (e) => {
    const btn = e.target.closest('.filter-btn');
    if (!btn) return;
    filter = btn.dataset.f;
    document.querySelectorAll('#queueFilters .filter-btn').forEach((b) =>
      b.classList.toggle('is-active', b === btn)
    );
    renderList();
  });

  // actions — one delegated listener, whole pipeline
  listEl.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-act]');
    if (!btn) return;
    const id = btn.dataset.id;
    const act = btn.dataset.act;

    try {
      if (act === 'accept') {
        await Eartha.acceptItem(id);
        Eartha.toast('ACCEPTED — ASSIGN A DRIVER BELOW');
      } else if (act === 'reject') {
        open.reject.add(id);
      } else if (act === 'reject-cancel') {
        open.reject.delete(id);
      } else if (act === 'reject-confirm') {
        const reason = document.getElementById('reason-' + id).value.trim() || 'Did not meet acceptance criteria.';
        await Eartha.rejectItem(id, reason);
        open.reject.delete(id);
        Eartha.toast('REJECTED — USER NOTIFIED');
      } else if (act === 'dispatch') {
        const select = document.getElementById('driver-' + id);
        const driver = driversList.find((d) => d.id === (select && select.value));
        if (!driver) { Eartha.toast('SELECT A DRIVER'); return; }

        // Opened synchronously, in the same click gesture, so browsers
        // don't treat it as a blocked popup — the dispatch call below is
        // async, and by the time it resolves the gesture context is gone.
        const waWindow = window.open('', '_blank', 'noopener');
        try {
          await Eartha.dispatchItem(id, driver.name);
        } catch (err) {
          if (waWindow) waWindow.close();
          throw err;
        }
        Eartha.toast(`DISPATCHED TO ${driver.name.toUpperCase()}`);

        const phoneDigits = driver.phone.replace(/\D/g, '');
        if (waWindow) {
          if (phoneDigits) waWindow.location.href = `https://wa.me/${phoneDigits}`;
          else waWindow.close();
        }
      } else if (act === 'collect') {
        await Eartha.collectItem(id);
        Eartha.toast('MARKED COLLECTED');
      } else if (act === 'complete') {
        await Eartha.completeItem(id);
        Eartha.toast('CLOSED OUT');
      } else if (act === 'award') {
        const points = Number(document.getElementById('award-' + id).value);
        if (Number.isNaN(points) || points < 0) { Eartha.toast('ENTER A VALID POINTS AMOUNT'); return; }
        await Eartha.awardItemPoints(id, points);
        Eartha.toast('POINTS AWARDED');
      }
    } catch (err) {
      Eartha.toast(err.message || 'SOMETHING WENT WRONG.');
    }

    render();
  });

  // ============ MANAGE BENEFITS ============
  let editingId = null;
  let benefitsList = [];
  const bForm = document.getElementById('benefitForm');
  const bMsg = document.getElementById('benefitMsg');

  async function renderBenefits() {
    const body = document.getElementById('benefitsBody');
    try {
      benefitsList = await Eartha.fetchBenefitsAdmin();
    } catch (err) {
      body.innerHTML = `<tr><td colspan="7">${Eartha.esc(err.message || 'COULD NOT LOAD BENEFITS.')}</td></tr>`;
      return;
    }
    body.innerHTML = benefitsList
      .map(
        (b) => `
      <tr class="drag-row" draggable="true" data-id="${b.id}">
        <td><span class="drag-handle" aria-hidden="true">⋮⋮</span></td>
        <td style="text-transform:uppercase;font-weight:700;">${Eartha.esc(b.brand)}</td>
        <td>${b.discount}% OFF</td>
        <td>${b.pointsRequired} PTS</td>
        <td style="text-transform:uppercase;">${Eartha.esc(b.category)}</td>
        <td>${b.active ? '<span class="badge badge-completed">LIVE</span>' : '<span class="badge badge-rejected">OFF</span>'}</td>
        <td style="white-space:nowrap;">
          <button class="link-underline" style="font-size:10px;margin-right:12px;" data-edit="${b.id}">EDIT</button>
          <button class="link-underline" style="font-size:10px;margin-right:12px;" data-toggle="${b.id}">${b.active ? 'DEACTIVATE' : 'ACTIVATE'}</button>
          <button class="link-underline" style="font-size:10px;" data-remove="${b.id}">REMOVE</button>
        </td>
      </tr>`
      )
      .join('');
    wireDrag(body);
  }

  bForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const brand = document.getElementById('bBrand').value.trim();
    const discount = Number(document.getElementById('bDiscount').value);
    const pointsRequired = Number(document.getElementById('bPoints').value);
    const category = document.getElementById('bCategory').value;

    if (!brand || !discount || !pointsRequired) {
      bMsg.textContent = 'FILL IN BRAND, DISCOUNT AND POINTS.';
      bMsg.className = 'form-msg is-error';
      return;
    }

    try {
      if (editingId) {
        await Eartha.updateBenefitAdmin(editingId, { brand, discount, pointsRequired, category });
        bMsg.textContent = 'BENEFIT UPDATED — LIVE ON THE BENEFITS PAGE.';
      } else {
        await Eartha.createBenefitAdmin({ brand, discount, pointsRequired, category });
        bMsg.textContent = 'BENEFIT ADDED — LIVE ON THE BENEFITS PAGE.';
      }
      bMsg.className = 'form-msg is-ok';
      resetBenefitForm();
      await renderBenefits();
    } catch (err) {
      bMsg.textContent = err.message || 'SOMETHING WENT WRONG.';
      bMsg.className = 'form-msg is-error';
    }
  });

  function resetBenefitForm() {
    editingId = null;
    bForm.reset();
    document.getElementById('benefitFormTitle').textContent = 'ADD BENEFIT';
    document.getElementById('benefitSubmit').textContent = 'ADD BENEFIT';
    document.getElementById('benefitCancel').hidden = true;
  }

  document.getElementById('benefitCancel').addEventListener('click', resetBenefitForm);

  document.getElementById('benefitsBody').addEventListener('click', async (e) => {
    const edit = e.target.closest('[data-edit]');
    const toggle = e.target.closest('[data-toggle]');
    const remove = e.target.closest('[data-remove]');

    if (edit) {
      const b = benefitsList.find((x) => x.id === edit.dataset.edit);
      editingId = b.id;
      document.getElementById('bBrand').value = b.brand;
      document.getElementById('bDiscount').value = b.discount;
      document.getElementById('bPoints').value = b.pointsRequired;
      document.getElementById('bCategory').value = b.category;
      document.getElementById('benefitFormTitle').textContent = 'EDIT BENEFIT — ' + b.brand.toUpperCase();
      document.getElementById('benefitSubmit').textContent = 'SAVE CHANGES';
      document.getElementById('benefitCancel').hidden = false;
      bForm.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    if (toggle) {
      try {
        const b = benefitsList.find((x) => x.id === toggle.dataset.toggle);
        await Eartha.updateBenefitAdmin(b.id, { active: !b.active });
        await renderBenefits();
      } catch (err) {
        Eartha.toast(err.message || 'SOMETHING WENT WRONG.');
      }
    }
    if (remove) {
      try {
        await Eartha.removeBenefitAdmin(remove.dataset.remove);
        Eartha.toast('BENEFIT REMOVED FROM THE USER-FACING PAGE');
        await renderBenefits();
      } catch (err) {
        Eartha.toast(err.message || 'SOMETHING WENT WRONG.');
      }
    }
  });

  // drag to reorder
  function wireDrag(body) {
    let dragging = null;
    body.querySelectorAll('.drag-row').forEach((row) => {
      row.addEventListener('dragstart', () => {
        dragging = row;
        row.classList.add('is-dragging');
      });
      row.addEventListener('dragend', async () => {
        row.classList.remove('is-dragging');
        dragging = null;
        try {
          await Eartha.reorderBenefitsAdmin([...body.querySelectorAll('.drag-row')].map((r) => r.dataset.id));
          Eartha.toast('DISPLAY ORDER SAVED');
        } catch (err) {
          Eartha.toast(err.message || 'SOMETHING WENT WRONG.');
          await renderBenefits();
        }
      });
      row.addEventListener('dragover', (e) => {
        e.preventDefault();
        if (!dragging || dragging === row) return;
        const rect = row.getBoundingClientRect();
        const after = e.clientY > rect.top + rect.height / 2;
        row.parentNode.insertBefore(dragging, after ? row.nextSibling : row);
      });
    });
  }

  // ============ DRIVERS ============
  // driversList also backs the DRIVER dropdown in the pipeline's dispatch
  // step (see actionArea's 'accepted' case) — loaded once up front,
  // before the first pipeline render (see the init block at the bottom).
  let driversList = [];
  let editingDriverId = null;
  const dForm = document.getElementById('driverForm');
  const dMsg = document.getElementById('driverMsg');

  async function renderDrivers() {
    const body = document.getElementById('driversBody');
    try {
      driversList = await Eartha.fetchDriversAdmin();
    } catch (err) {
      body.innerHTML = `<tr><td colspan="3">${Eartha.esc(err.message || 'COULD NOT LOAD DRIVERS.')}</td></tr>`;
      return;
    }
    body.innerHTML = driversList.length
      ? driversList
          .map(
            (d) => `
      <tr data-id="${d.id}">
        <td style="text-transform:uppercase;font-weight:700;">${Eartha.esc(d.name)}</td>
        <td>${Eartha.esc(d.phone)}</td>
        <td style="white-space:nowrap;">
          <button class="link-underline" style="font-size:10px;margin-right:12px;" data-edit="${d.id}">EDIT</button>
          <button class="link-underline" style="font-size:10px;" data-remove="${d.id}">REMOVE</button>
        </td>
      </tr>`
          )
          .join('')
      : '<tr><td colspan="3">NO DRIVERS YET — ADD ONE ABOVE.</td></tr>';
  }

  dForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('dName').value.trim();
    const phone = document.getElementById('dPhone').value.trim();

    if (!name || !phone) {
      dMsg.textContent = 'FILL IN NAME AND PHONE NUMBER.';
      dMsg.className = 'form-msg is-error';
      return;
    }

    try {
      if (editingDriverId) {
        await Eartha.updateDriverAdmin(editingDriverId, { name, phone });
        dMsg.textContent = 'DRIVER UPDATED.';
      } else {
        await Eartha.createDriverAdmin({ name, phone });
        dMsg.textContent = 'DRIVER ADDED.';
      }
      dMsg.className = 'form-msg is-ok';
      resetDriverForm();
      await renderDrivers();
      renderList(); // dispatch dropdown on the pipeline tab needs the new roster
    } catch (err) {
      dMsg.textContent = err.message || 'SOMETHING WENT WRONG.';
      dMsg.className = 'form-msg is-error';
    }
  });

  function resetDriverForm() {
    editingDriverId = null;
    dForm.reset();
    document.getElementById('driverFormTitle').textContent = 'ADD DRIVER';
    document.getElementById('driverSubmit').textContent = 'ADD DRIVER';
    document.getElementById('driverCancel').hidden = true;
  }

  document.getElementById('driverCancel').addEventListener('click', resetDriverForm);

  document.getElementById('driversBody').addEventListener('click', async (e) => {
    const edit = e.target.closest('[data-edit]');
    const remove = e.target.closest('[data-remove]');

    if (edit) {
      const d = driversList.find((x) => x.id === edit.dataset.edit);
      editingDriverId = d.id;
      document.getElementById('dName').value = d.name;
      document.getElementById('dPhone').value = d.phone;
      document.getElementById('driverFormTitle').textContent = 'EDIT DRIVER — ' + d.name.toUpperCase();
      document.getElementById('driverSubmit').textContent = 'SAVE CHANGES';
      document.getElementById('driverCancel').hidden = false;
      dForm.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    if (remove) {
      try {
        await Eartha.removeDriverAdmin(remove.dataset.remove);
        Eartha.toast('DRIVER REMOVED');
        await renderDrivers();
        renderList();
      } catch (err) {
        Eartha.toast(err.message || 'SOMETHING WENT WRONG.');
      }
    }
  });

  // ============ INBOX ============
  async function renderInbox() {
    const el = document.getElementById('inboxList');
    let list;
    try {
      list = await Eartha.fetchContactMessages();
    } catch (err) {
      el.innerHTML = `<div class="empty">${Eartha.esc(err.message || 'COULD NOT LOAD MESSAGES.')}</div>`;
      return;
    }

    if (!list.length) {
      el.innerHTML = '<div class="empty">INBOX IS EMPTY — CONTACT FORM MESSAGES LAND HERE.</div>';
    } else {
      el.innerHTML = list
        .map(
          (m) => `
        <div class="card" style="${m.read ? 'opacity:0.65;' : ''}">
          <p class="batch-tag">${Eartha.fmtDate(m.date)} · ${Eartha.esc(m.email)}</p>
          <p style="font-weight:700;text-transform:uppercase;letter-spacing:var(--track-wide);font-size:12px;margin-top:4px;">
            ${Eartha.esc(m.subject || '(NO SUBJECT)')} — ${Eartha.esc(m.name)}
          </p>
          <p class="muted" style="font-size:12px;margin-top:8px;">${Eartha.esc(m.body)}</p>
          ${m.read ? '' : `<button class="link-underline" style="font-size:10px;margin-top:12px;" data-read="${m.id}">MARK AS READ</button>`}
        </div>`
        )
        .join('');
    }
    document.getElementById('countInbox').textContent = list.filter((m) => !m.read).length;
  }

  document.getElementById('inboxList').addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-read]');
    if (!btn) return;
    try {
      await Eartha.resolveMessage(btn.dataset.read);
      await renderInbox();
    } catch (err) {
      Eartha.toast(err.message || 'SOMETHING WENT WRONG.');
    }
  });

  // Drivers load first and are awaited — the pipeline's dispatch dropdown
  // (see actionArea's 'accepted' case) reads driversList synchronously
  // while building each card, so it needs to be populated before the
  // first pipeline render, not just eventually.
  (async () => {
    await renderDrivers();
    render();
  })();
  renderBenefits();
  renderInbox();
}
