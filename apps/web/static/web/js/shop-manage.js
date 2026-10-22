/* EARTHA — shop-manage.js
   Admin shop manager: ORDERS (work through new → confirmed → delivered)
   and PRODUCTS (add / edit / hide / delete, with photos).
*/

const admin = Eartha.requireAdmin();
if (admin) {
  Eartha.renderHeader(admin, 'shop-manage');

  const money = (n) => '$' + Number(n).toFixed(2);
  const SECTION_LABELS = { women: 'WOMEN', men: 'MEN', kids: 'KIDS' };

  // ---------- tabs ----------
  document.querySelectorAll('.tabs .tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tabs .tab').forEach((t) => t.classList.toggle('is-active', t === tab));
      document.querySelectorAll('.tab-panel').forEach((p) =>
        p.classList.toggle('is-active', p.id === 'panel-' + tab.dataset.panel)
      );
    });
  });

  // ================= ORDERS =================
  const ordersEl = document.getElementById('ordersList');
  let orderView = 'open';
  let orders = [];

  const STATUS_BADGE = {
    new: '<span class="badge badge-pending">NEW — CALL TO CONFIRM</span>',
    confirmed: '<span class="badge badge-accepted">CONFIRMED — TO DELIVER</span>',
    delivered: '<span class="badge badge-completed">DELIVERED</span>',
    cancelled: '<span class="badge badge-rejected">CANCELLED</span>',
  };

  function orderActions(o) {
    if (o.status === 'new') {
      return `<button class="btn btn-sm" data-status="confirmed" data-id="${o.id}">CONFIRM ORDER</button>
              <button class="btn btn-ghost btn-sm" data-status="cancelled" data-id="${o.id}">CANCEL</button>`;
    }
    if (o.status === 'confirmed') {
      return `<button class="btn btn-sm" data-status="delivered" data-id="${o.id}">MARK DELIVERED &amp; PAID</button>
              <button class="btn btn-ghost btn-sm" data-status="cancelled" data-id="${o.id}">CANCEL</button>`;
    }
    return '';
  }

  function orderCard(o) {
    const address = [o.address, o.building, o.floor_unit, o.city].filter(Boolean).map(Eartha.esc).join(', ');
    const lines = o.items
      .map((i) => `<li>${i.quantity} × ${Eartha.esc(i.product_name)} <span class="muted">— ${money(i.unit_price_usd * i.quantity)}</span></li>`)
      .join('');
    return `
    <div class="card">
      <div class="card-row" style="align-items:flex-start;">
        <div style="flex:1;min-width:220px;">
          <p class="batch-tag">ORDER ${Eartha.esc(o.number)} · ${Eartha.fmtDate(new Date(o.created_at).getTime())}</p>
          <p style="font-weight:700;text-transform:uppercase;letter-spacing:var(--track-wide);font-size:12px;margin-top:4px;">${Eartha.esc(o.full_name)}</p>
          <p style="font-size:12px;margin-top:6px;">
            <a href="tel:${Eartha.esc(o.phone)}" class="link-underline">${Eartha.esc(o.phone)}</a>
            ${o.email ? ` · <a href="mailto:${Eartha.esc(o.email)}" class="link-underline">${Eartha.esc(o.email)}</a>` : ''}
          </p>
          <p class="muted" style="font-size:12px;margin-top:6px;">DELIVER TO: ${address}</p>
          ${o.notes ? `<p class="muted" style="font-size:12px;margin-top:4px;">NOTES: "${Eartha.esc(o.notes)}"</p>` : ''}
          <ul class="order-lines">${lines}</ul>
          <p style="font-weight:700;font-size:13px;margin-top:8px;">TOTAL ${money(o.total_usd)} <span class="muted" style="font-weight:400;font-size:11px;">CASH ON DELIVERY</span></p>
        </div>
        ${STATUS_BADGE[o.status] || ''}
      </div>
      ${orderActions(o) ? `<div class="order-actions">${orderActions(o)}</div>` : ''}
    </div>`;
  }

  async function renderOrders() {
    try {
      orders = await Eartha.fetchShopOrdersAdmin(orderView);
    } catch (err) {
      ordersEl.innerHTML = `<div class="empty">${Eartha.esc(err.message || 'COULD NOT LOAD ORDERS.')}</div>`;
      return;
    }
    ordersEl.innerHTML = orders.length
      ? orders.map(orderCard).join('')
      : `<div class="empty">${orderView === 'open' ? 'NO ORDERS WAITING — NEW ONES SHOW UP HERE.' : 'NOTHING DELIVERED OR CANCELLED YET.'}</div>`;
    refreshNewCount();
  }

  async function refreshNewCount() {
    try {
      const n = await Eartha.fetchNewShopOrderCount();
      const badge = document.getElementById('countNewOrders');
      badge.textContent = n;
      badge.hidden = n === 0;
    } catch { /* badge is optional */ }
  }

  document.getElementById('orderFilters').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-view]');
    if (!btn) return;
    orderView = btn.dataset.view;
    document.querySelectorAll('#orderFilters .filter-btn').forEach((b) => b.classList.toggle('is-active', b === btn));
    renderOrders();
  });

  ordersEl.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-status]');
    if (!btn) return;
    const o = orders.find((x) => x.id === btn.dataset.id);
    const next = btn.dataset.status;
    if (next === 'cancelled' && !confirm(`Cancel order ${o.number} for ${o.full_name}? The items go back on sale.`)) return;
    if (next === 'delivered' && !confirm(`Mark order ${o.number} as delivered and paid (${money(o.total_usd)})?`)) return;
    btn.disabled = true;
    try {
      await Eartha.setShopOrderStatus(o.id, next);
      Eartha.toast(next === 'confirmed' ? 'ORDER CONFIRMED' : next === 'delivered' ? 'ORDER DELIVERED' : 'ORDER CANCELLED — ITEMS BACK ON SALE');
      await renderOrders();
      if (next === 'cancelled') renderProducts();
    } catch (err) {
      Eartha.toast(err.message || 'COULD NOT UPDATE THE ORDER.');
      btn.disabled = false;
    }
  });

  // ================= PRODUCTS =================
  const form = document.getElementById('productForm');
  const msg = document.getElementById('productMsg');
  const body = document.getElementById('productsBody');
  const drop = document.getElementById('pPhotoDrop');
  const input = document.getElementById('pPhotos');
  const previews = document.getElementById('pPhotoPreviews');
  const MAX_PHOTOS = 8;
  let products = [];
  let editingId = null;
  // newly chosen photos: { file, url } — url is an object URL for the
  // thumbnail. When editing, the product's current photos are shown
  // until new ones are chosen, which then replace them all.
  let newPhotos = [];

  function renderPreviews() {
    if (newPhotos.length) {
      previews.innerHTML = newPhotos
        .map((p, i) => `
          <div class="ph">
            <img src="${p.url}" alt="Photo ${i + 1}">
            <button type="button" class="rm" data-i="${i}" aria-label="Remove photo ${i + 1}">×</button>
          </div>`)
        .join('');
    } else if (editingId) {
      const current = products.find((p) => p.id === editingId);
      previews.innerHTML = current.images
        .map((src, i) => `<div class="ph"><img src="${Eartha.esc(src)}" alt="Current photo ${i + 1}"></div>`)
        .join('');
    } else {
      previews.innerHTML = '';
    }
    document.getElementById('pPhotoHint').textContent = editingId
      ? 'CURRENT PHOTOS SHOWN. CHOOSE NEW ONES ONLY IF YOU WANT TO REPLACE THEM ALL.'
      : 'UP TO 8 PHOTOS. THE FIRST ONE IS THE MAIN PHOTO.';
  }

  function addFiles(fileList) {
    const files = Array.from(fileList).filter((f) => f.type.startsWith('image/'));
    for (const file of files) {
      if (newPhotos.length >= MAX_PHOTOS) {
        Eartha.toast('UP TO 8 PHOTOS PER PRODUCT');
        break;
      }
      newPhotos.push({ file, url: URL.createObjectURL(file) });
    }
    renderPreviews();
  }

  previews.addEventListener('click', (e) => {
    const rm = e.target.closest('.rm');
    if (!rm) return;
    const [removed] = newPhotos.splice(Number(rm.dataset.i), 1);
    URL.revokeObjectURL(removed.url);
    renderPreviews();
  });
  drop.addEventListener('click', () => input.click());
  drop.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); }
  });
  input.addEventListener('change', () => { addFiles(input.files); input.value = ''; });
  ['dragenter', 'dragover'].forEach((ev) =>
    drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('is-over'); })
  );
  ['dragleave', 'drop'].forEach((ev) =>
    drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove('is-over'); })
  );
  drop.addEventListener('drop', (e) => addFiles(e.dataTransfer.files));

  function statusBadge(p) {
    if (!p.active) return '<span class="badge badge-rejected">HIDDEN</span>';
    if (p.stock === 0) return '<span class="badge badge-pending">SOLD OUT</span>';
    return '<span class="badge badge-completed">LIVE</span>';
  }

  async function renderProducts() {
    try {
      products = await Eartha.fetchShopProductsAdmin();
    } catch (err) {
      body.innerHTML = `<tr><td colspan="7">${Eartha.esc(err.message || 'COULD NOT LOAD PRODUCTS.')}</td></tr>`;
      return;
    }
    body.innerHTML = products.length
      ? products.map((p) => `
        <tr>
          <td><img class="thumb-64" src="${Eartha.esc(p.images[0])}" alt=""></td>
          <td style="text-transform:uppercase;font-weight:700;">${Eartha.esc(p.name)}${p.size ? `<div class="muted" style="font-weight:400;font-size:10px;margin-top:2px;">SIZE ${Eartha.esc(p.size)}</div>` : ''}</td>
          <td>${SECTION_LABELS[p.section] || ''}</td>
          <td>${money(p.price)}</td>
          <td>${p.stock}</td>
          <td>${statusBadge(p)}</td>
          <td style="white-space:nowrap;">
            <button class="link-underline" style="font-size:10px;margin-right:12px;" data-edit="${p.id}">EDIT</button>
            <button class="link-underline" style="font-size:10px;margin-right:12px;" data-toggle="${p.id}">${p.active ? 'HIDE' : 'SHOW'}</button>
            <button class="link-underline" style="font-size:10px;" data-remove="${p.id}">DELETE</button>
          </td>
        </tr>`).join('')
      : '<tr><td colspan="7" class="muted">NO PRODUCTS YET — THE SHOP SHOWS "COMING SOON" UNTIL YOU ADD ONE.</td></tr>';
  }

  function resetForm() {
    editingId = null;
    newPhotos.forEach((p) => URL.revokeObjectURL(p.url));
    newPhotos = [];
    form.reset();
    document.getElementById('pActive').checked = true;
    document.getElementById('productFormTitle').textContent = 'ADD PRODUCT';
    document.getElementById('productSubmit').textContent = 'ADD PRODUCT';
    document.getElementById('productCancel').hidden = true;
    renderPreviews();
  }
  document.getElementById('productCancel').addEventListener('click', () => {
    resetForm();
    msg.textContent = '';
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fields = {
      name: document.getElementById('pName').value.trim(),
      section: document.getElementById('pSection').value,
      price: document.getElementById('pPrice').value.trim(),
      size: document.getElementById('pSize').value.trim(),
      description: document.getElementById('pDesc').value.trim(),
      stock: document.getElementById('pStock').value.trim(),
      active: document.getElementById('pActive').checked,
    };
    const problems = [];
    if (!fields.name) problems.push('A NAME');
    if (!(Number(fields.price) > 0)) problems.push('A PRICE ABOVE $0');
    if (!(Number.isInteger(Number(fields.stock)) && Number(fields.stock) >= 0) || fields.stock === '') problems.push('HOW MANY ARE IN STOCK');
    if (!editingId && !newPhotos.length) problems.push('AT LEAST ONE PHOTO');
    if (problems.length) {
      msg.textContent = 'ADD ' + problems.join(', ') + '.';
      msg.className = 'form-msg is-error';
      return;
    }

    const submitBtn = document.getElementById('productSubmit');
    submitBtn.disabled = true;
    msg.textContent = 'SAVING...';
    msg.className = 'form-msg';
    try {
      const files = newPhotos.map((p) => p.file);
      if (editingId) await Eartha.updateShopProductAdmin(editingId, fields, files);
      else await Eartha.createShopProductAdmin(fields, files);
      Eartha.toast(editingId ? 'PRODUCT UPDATED' : 'PRODUCT ADDED');
      msg.textContent = '';
      resetForm();
      await renderProducts();
    } catch (err) {
      msg.textContent = err.message || 'SOMETHING WENT WRONG.';
      msg.className = 'form-msg is-error';
    } finally {
      submitBtn.disabled = false;
    }
  });

  body.addEventListener('click', async (e) => {
    const edit = e.target.closest('[data-edit]');
    const toggle = e.target.closest('[data-toggle]');
    const remove = e.target.closest('[data-remove]');

    if (edit) {
      const p = products.find((x) => x.id === edit.dataset.edit);
      resetForm();
      editingId = p.id;
      document.getElementById('pName').value = p.name;
      document.getElementById('pSection').value = p.section;
      document.getElementById('pPrice').value = p.price;
      document.getElementById('pSize').value = p.size;
      document.getElementById('pDesc').value = p.description;
      document.getElementById('pStock').value = p.stock;
      document.getElementById('pActive').checked = p.active;
      document.getElementById('productFormTitle').textContent = 'EDIT PRODUCT';
      document.getElementById('productSubmit').textContent = 'SAVE CHANGES';
      document.getElementById('productCancel').hidden = false;
      renderPreviews();
      form.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }

    if (toggle) {
      const p = products.find((x) => x.id === toggle.dataset.toggle);
      try {
        await Eartha.updateShopProductAdmin(p.id, { active: !p.active });
        Eartha.toast(p.active ? 'HIDDEN FROM THE SHOP' : 'SHOWING IN THE SHOP');
        await renderProducts();
      } catch (err) {
        Eartha.toast(err.message || 'COULD NOT UPDATE.');
      }
      return;
    }

    if (remove) {
      const p = products.find((x) => x.id === remove.dataset.remove);
      if (!confirm(`Delete "${p.name}"? This can't be undone. Past orders keep their record of it. To take it off the shop temporarily, use HIDE instead.`)) return;
      try {
        await Eartha.deleteShopProductAdmin(p.id);
        if (editingId === p.id) resetForm();
        Eartha.toast('PRODUCT DELETED');
        await renderProducts();
      } catch (err) {
        Eartha.toast(err.message || 'COULD NOT DELETE.');
      }
    }
  });

  renderPreviews();
  renderOrders();
  renderProducts();
}
