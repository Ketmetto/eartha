/* EARTHA — benefits.js
   One page, two modes.
   Users: browse + redeem. Admins: manage the exact grid users see —
   edit in place, drag cards to reorder, add via the last tile.
   Backed by the real API (points/benefits, points/redeem, points/balance) —
   not the legacy localStorage mock in store.js.
*/

let user = Eartha.requireAuth();
if (user) {
  const isAdmin = user.isAdmin;
  Eartha.renderHeader(user, 'benefits');

  const grid = document.getElementById('benefitsGrid');
  const ptsLine = document.getElementById('ptsLine');
  const redeemDialog = document.getElementById('redeemDialog');
  const codeDialog = document.getElementById('codeDialog');

  let activeCat = 'all';
  let editingId = null;   // benefit currently in edit mode
  let adding = false;     // add tile expanded
  let pendingBenefit = null;
  let benefits = [];      // fetched from the API — see loadBenefits()
  let balance = 0;        // fetched from the API — see refreshBalance()

  const initials = (brand) =>
    brand.split(/\s+/).map((w) => w[0]).join('').toUpperCase().slice(0, 2);

  const thumbHtml = (b) =>
    b.image
      ? `<img class="benefit-thumb" src="${b.image}" alt="" loading="lazy">`
      : `<div class="benefit-thumb" aria-hidden="true">${initials(b.brand)}</div>`;

  async function loadBenefits() {
    try {
      benefits = isAdmin ? await Eartha.fetchBenefitsAdmin() : await Eartha.fetchActiveBenefits();
    } catch {
      benefits = [];
      Eartha.toast('COULD NOT LOAD BENEFITS.');
    }
  }

  async function refreshBalance() {
    if (isAdmin) return;
    try { balance = await Eartha.fetchBalance(); } catch { /* leave at last-known value */ }
  }

  function refreshPtsLine() {
    ptsLine.textContent = isAdmin
      ? 'MANAGE MODE — CHANGES GO LIVE INSTANTLY'
      : `YOUR BALANCE — ${balance} PTS`;
  }

  // ---------- card templates ----------
  const catOptions = (sel) =>
    ['fashion', 'food', 'beauty', 'lifestyle']
      .map((c) => `<option value="${c}" ${c === sel ? 'selected' : ''}>${c.toUpperCase()}</option>`)
      .join('');

  function benefitForm(b) {
    // shared by edit-in-place and the add row
    const v = b || { brand: '', discount: '', pointsRequired: '', category: activeCat !== 'all' ? activeCat : 'fashion', image: '' };
    const idAttr = b ? `data-form="${b.id}"` : 'data-form="new"';
    const thumbStyle = v.image
      ? `background:url('${v.image}') center/cover no-repeat;`
      : 'background:var(--ink);';
    return `
      <div ${idAttr} style="display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end;width:100%;">
        <div class="field" style="margin:0;">
          <label>IMAGE</label>
          <div class="benefit-image-drop" tabindex="0" role="button" aria-label="Upload benefit image" style="width:56px;height:56px;cursor:pointer;${thumbStyle}"></div>
          <input type="file" accept="image/*" class="f-image-input" hidden>
          <input type="hidden" class="f-image" value="${Eartha.esc(v.image || '')}">
        </div>
        <div class="field" style="margin:0;flex:1;min-width:160px;">
          <label>BRAND NAME</label>
          <input type="text" class="f-brand" value="${Eartha.esc(v.brand)}">
        </div>
        <div class="field" style="margin:0;width:110px;">
          <label>DISCOUNT %</label>
          <input type="number" class="f-discount" min="1" max="100" value="${v.discount}">
        </div>
        <div class="field" style="margin:0;width:110px;">
          <label>POINTS</label>
          <input type="number" class="f-points" min="1" value="${v.pointsRequired}">
        </div>
        <div class="field" style="margin:0;width:160px;">
          <label>CATEGORY</label>
          <div class="select-wrap"><select class="f-category">${catOptions(v.category)}</select></div>
        </div>
        <div style="display:flex;gap:10px;">
          <button class="btn btn-sm" data-act="${b ? 'save' : 'create'}" data-id="${b ? b.id : ''}">${b ? 'SAVE' : 'ADD BENEFIT'}</button>
          <button class="btn btn-ghost btn-sm" data-act="cancel-form">CANCEL</button>
        </div>
      </div>`;
  }

  function userCard(b) {
    const affordable = balance >= b.pointsRequired;
    return `
      <article class="benefit-row">
        ${thumbHtml(b)}
        <div class="benefit-info">
          <p class="benefit-cat">${Eartha.esc(b.category)}</p>
          <h2 class="benefit-brand">${Eartha.esc(b.brand)}</h2>
        </div>
        <p class="benefit-off">${b.discount}% OFF</p>
        <p class="benefit-pts">${b.pointsRequired} PTS</p>
        <button class="btn btn-sm" data-act="redeem" data-id="${b.id}" ${affordable ? '' : 'disabled'}>
          ${affordable ? 'REDEEM' : 'NOT ENOUGH POINTS'}
        </button>
      </article>`;
  }

  function adminCard(b) {
    if (editingId === b.id) {
      return `<article class="benefit-row benefit-row-form" data-id="${b.id}">
        <p class="eyebrow" style="font-weight:700;margin-bottom:14px;">EDIT — ${Eartha.esc(b.brand.toUpperCase())}</p>
        ${benefitForm(b)}
      </article>`;
    }
    return `
      <article class="benefit-row drag-row ${b.active ? '' : 'is-inactive'}" draggable="true" data-id="${b.id}" style="${b.active ? '' : 'opacity:0.5;'}">
        <span class="drag-handle" title="Drag to reorder" aria-hidden="true">⋮⋮</span>
        ${thumbHtml(b)}
        <div class="benefit-info">
          <p class="benefit-cat">${Eartha.esc(b.category)}${b.active ? '' : ' · HIDDEN FROM USERS'}</p>
          <h2 class="benefit-brand">${Eartha.esc(b.brand)}</h2>
        </div>
        <p class="benefit-off">${b.discount}% OFF</p>
        <p class="benefit-pts">${b.pointsRequired} PTS</p>
        <div class="benefit-actions">
          <button class="link-underline" style="font-size:10px;" data-act="edit" data-id="${b.id}">EDIT</button>
          <button class="link-underline" style="font-size:10px;" data-act="toggle" data-id="${b.id}">${b.active ? 'HIDE' : 'SHOW'}</button>
          <button class="link-underline" style="font-size:10px;" data-act="remove" data-id="${b.id}">REMOVE</button>
        </div>
      </article>`;
  }

  const addTile = () =>
    adding
      ? `<article class="benefit-row benefit-row-form"><p class="eyebrow" style="font-weight:700;margin-bottom:14px;">NEW BENEFIT</p>${benefitForm(null)}</article>`
      : `<button class="benefit-row-add" data-act="open-add">+ ADD BENEFIT</button>`;

  // ---------- render ----------
  function render() {
    // fetchActiveBenefits() only ever returns is_active=True rows server-side
    // (its serializer doesn't even include the field) — admin's fetch
    // includes everything, so only admin needs the active/inactive split.
    const list = benefits.filter((b) => activeCat === 'all' || b.category === activeCat);

    let html = list.map((b) => (isAdmin ? adminCard(b) : userCard(b))).join('');
    if (isAdmin) html += addTile();

    grid.innerHTML =
      html || '<div class="empty">NO BENEFITS IN THIS CATEGORY YET.</div>';

    if (isAdmin) wireDrag();
  }

  // ---------- filters ----------
  document.getElementById('filterRow').addEventListener('click', (e) => {
    const btn = e.target.closest('.filter-btn');
    if (!btn) return;
    activeCat = btn.dataset.cat;
    document.querySelectorAll('.filter-btn').forEach((b) => b.classList.toggle('is-active', b === btn));
    render();
  });

  // ---------- delegated actions ----------
  grid.addEventListener('click', async (e) => {
    // Checked before the [data-act] guard below — the drop zone itself
    // carries no data-act, so it would otherwise hit the early return and
    // never open the file picker on a mouse click (only Enter/Space via
    // the keydown listener would have worked).
    const imgDrop = e.target.closest('.benefit-image-drop');
    if (imgDrop) {
      imgDrop.parentElement.querySelector('.f-image-input').click();
      return;
    }

    const btn = e.target.closest('[data-act]');
    if (!btn) return;
    const act = btn.dataset.act;
    const id = btn.dataset.id;

    // ----- user -----
    if (act === 'redeem') {
      pendingBenefit = benefits.find((b) => b.id === id);
      if (!pendingBenefit) return;
      document.getElementById('redeemText').textContent =
        `${pendingBenefit.discount}% OFF AT ${pendingBenefit.brand.toUpperCase()} FOR ${pendingBenefit.pointsRequired} PTS. ` +
        `THIS WILL LEAVE YOU WITH ${balance - pendingBenefit.pointsRequired} PTS.`;
      redeemDialog.showModal();
      return;
    }

    // ----- admin -----
    if (act === 'open-add') { adding = true; editingId = null; render(); }
    if (act === 'edit') { editingId = id; adding = false; render(); }
    if (act === 'cancel-form') { editingId = null; adding = false; render(); }
    if (act === 'toggle') {
      const b = benefits.find((x) => x.id === id);
      try {
        await Eartha.updateBenefitAdmin(id, { active: !b.active });
        Eartha.toast(b.active ? 'HIDDEN FROM THE USER-FACING PAGE' : 'LIVE ON THE USER-FACING PAGE');
        await loadBenefits();
        render();
      } catch (err) {
        Eartha.toast(err.message);
      }
    }
    if (act === 'remove') {
      const b = benefits.find((x) => x.id === id);
      const ok = confirm(`Delete "${b ? b.brand : 'this benefit'}"? This can't be undone — any past redemption codes for it stay in history, but it disappears from this list permanently.`);
      if (!ok) return;
      try {
        await Eartha.removeBenefitAdmin(id);
        Eartha.toast('BENEFIT REMOVED');
        await loadBenefits();
        render();
      } catch (err) {
        Eartha.toast(err.message);
      }
    }
    if (act === 'save' || act === 'create') {
      const form = btn.closest('[data-form]');
      const brand = form.querySelector('.f-brand').value.trim();
      const discount = Number(form.querySelector('.f-discount').value);
      const pointsRequired = Number(form.querySelector('.f-points').value);
      const category = form.querySelector('.f-category').value;
      const image = form.querySelector('.f-image').value;
      if (!brand || !discount || !pointsRequired) {
        Eartha.toast('FILL IN BRAND, DISCOUNT AND POINTS');
        return;
      }
      try {
        if (act === 'save') {
          await Eartha.updateBenefitAdmin(id, { brand, discount, pointsRequired, category, image });
          Eartha.toast('SAVED — LIVE INSTANTLY');
        } else {
          await Eartha.createBenefitAdmin({ brand, discount, pointsRequired, category, image });
          Eartha.toast('BENEFIT ADDED — LIVE INSTANTLY');
        }
        editingId = null;
        adding = false;
        await loadBenefits();
        render();
      } catch (err) {
        Eartha.toast(err.message);
      }
    }
  });

  grid.addEventListener('keydown', (e) => {
    const imgDrop = e.target.closest('.benefit-image-drop');
    if (imgDrop && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      imgDrop.parentElement.querySelector('.f-image-input').click();
    }
  });

  grid.addEventListener('change', async (e) => {
    const input = e.target.closest('.f-image-input');
    if (!input || !input.files[0]) return;
    const field = input.parentElement;
    let dataUrl;
    try {
      dataUrl = await Eartha.compressImage(input.files[0], 300, 0.8);
    } catch {
      Eartha.toast('COULD NOT READ THAT IMAGE');
      return;
    }
    field.querySelector('.f-image').value = dataUrl;
    field.querySelector('.benefit-image-drop').style.background = `url('${dataUrl}') center/cover no-repeat`;
    input.value = '';
  });

  // ---------- redeem dialogs (user) ----------
  document.getElementById('redeemCancel').addEventListener('click', () => redeemDialog.close());
  document.getElementById('redeemConfirm').addEventListener('click', async () => {
    try {
      const redemption = await Eartha.redeemBenefitApi(pendingBenefit.id);
      redeemDialog.close();
      await refreshBalance();
      await loadBenefits();
      refreshPtsLine();
      Eartha.refreshHeaderPts();
      render();
      document.getElementById('codeText').textContent = redemption.code;
      Eartha.fetchRedemptionQrObjectUrl(redemption.id)
        .then((url) => { document.getElementById('codeQr').src = url; })
        .catch(() => { /* code text above is still shown even if the QR image fails to load */ });
      codeDialog.showModal();
    } catch (err) {
      redeemDialog.close();
      Eartha.toast(err.message);
    }
  });
  document.getElementById('codeClose').addEventListener('click', () => codeDialog.close());

  // ---------- drag to reorder (admin) ----------
  function wireDrag() {
    let dragging = null;
    grid.querySelectorAll('.drag-row').forEach((card) => {
      card.addEventListener('dragstart', () => { dragging = card; card.classList.add('is-dragging'); });
      card.addEventListener('dragend', async () => {
        card.classList.remove('is-dragging');
        dragging = null;
        try {
          await Eartha.reorderBenefitsAdmin([...grid.querySelectorAll('[data-id]')].map((c) => c.dataset.id));
          Eartha.toast('DISPLAY ORDER SAVED');
          await loadBenefits();
        } catch (err) {
          Eartha.toast(err.message);
        }
      });
      card.addEventListener('dragover', (e) => {
        e.preventDefault();
        if (!dragging || dragging === card) return;
        const rect = card.getBoundingClientRect();
        const after = e.clientX > rect.left + rect.width / 2;
        card.parentNode.insertBefore(dragging, after ? card.nextSibling : card);
      });
    });
  }

  (async () => {
    await Promise.all([loadBenefits(), refreshBalance()]);
    refreshPtsLine();
    render();
  })();
}
