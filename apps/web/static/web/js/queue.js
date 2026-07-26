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

  const ACTION_STATUSES = ['pending', 'accepted', 'dispatched', 'collected'];
  const DONE_STATUSES = ['completed', 'rejected'];

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
        return `
          <div style="display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap;">
            <div class="field" style="margin:0;min-width:220px;">
              <label for="driver-${s.id}">DRIVER NAME</label>
              <input type="text" id="driver-${s.id}" placeholder="e.g. Karim H.">
            </div>
            <button class="btn btn-sm" data-act="dispatch" data-id="${s.id}" ${noAddress ? 'disabled title="User has no pickup address"' : ''}>DISPATCH</button>
          </div>`;
      }

      case 'dispatched':
        return `<button class="btn btn-sm" data-act="collect" data-id="${s.id}">MARK COLLECTED</button>`;

      case 'collected':
        return `<button class="btn btn-sm" data-act="complete" data-id="${s.id}">CONFIRM &amp; CLOSE OUT</button>`;

      case 'completed': {
        // Points were awarded at acceptance, not here — the table below
        // matches apps.points.rules.suggested_points exactly, so this is
        // the real amount, not a guess.
        const pts = Eartha.POINTS_CRITERIA[s.condition] ?? 0;
        return `<p class="muted" style="font-size:11px;">+${pts} PTS AWARDED AT ACCEPTANCE · ${Eartha.fmtDate(s.updatedAt)}</p>`;
      }

      case 'rejected':
        return `<p class="muted" style="font-size:11px;">REASON: ${Eartha.esc(s.rejectReason || '—')}</p>`;
    }
    return '';
  }

  function card(s) {
    const addressLine =
      ['accepted', 'dispatched'].includes(s.status)
        ? `<p class="muted" style="font-size:11px;margin-top:4px;">PICKUP: ${s.pickupAddress ? Eartha.esc(s.pickupAddress) : '<span style="color:var(--bad);">NO ADDRESS ON PROFILE</span>'}</p>`
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

  async function render() {
    let subs;
    try {
      subs = await Eartha.fetchAdminSubmissions();
    } catch (err) {
      listEl.innerHTML = `<div class="empty">${Eartha.esc(err.message || 'COULD NOT LOAD THE QUEUE.')}</div>`;
      return;
    }

    const action = subs.filter((s) => ACTION_STATUSES.includes(s.status));
    const done = subs.filter((s) => DONE_STATUSES.includes(s.status));

    document.getElementById('fCountAction').textContent = action.length ? `(${action.length})` : '';
    document.getElementById('fCountDone').textContent = done.length ? `(${done.length})` : '';
    document.getElementById('queueSummary').textContent =
      `${action.length} NEED${action.length === 1 ? 'S' : ''} ACTION · ${subs.length} TOTAL`;

    const view = filter === 'action' ? action : filter === 'done' ? done : subs;

    listEl.innerHTML = view.length
      ? view.map(card).join('')
      : `<div class="empty">${filter === 'action' ? 'QUEUE IS CLEAR — NOTHING NEEDS YOU RIGHT NOW.' : 'NOTHING HERE YET.'}</div>`;
  }

  // filters
  document.getElementById('queueFilters').addEventListener('click', (e) => {
    const btn = e.target.closest('.filter-btn');
    if (!btn) return;
    filter = btn.dataset.f;
    document.querySelectorAll('#queueFilters .filter-btn').forEach((b) =>
      b.classList.toggle('is-active', b === btn)
    );
    render();
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
        const driverName = document.getElementById('driver-' + id).value.trim();
        if (!driverName) { Eartha.toast('ENTER A DRIVER NAME'); return; }
        await Eartha.dispatchItem(id, driverName);
        Eartha.toast(`DISPATCHED TO ${driverName.toUpperCase()}`);
      } else if (act === 'collect') {
        await Eartha.collectItem(id);
        Eartha.toast('MARKED COLLECTED');
      } else if (act === 'complete') {
        await Eartha.completeItem(id);
        Eartha.toast('CLOSED OUT');
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

  render();
  renderBenefits();
  renderInbox();
}
