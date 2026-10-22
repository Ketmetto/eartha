/* EARTHA — shop.js */

const products = JSON.parse(document.getElementById('shop-products').textContent);
const byId = Object.fromEntries(products.map((p) => [p.id, p]));
const money = (n) => '$' + Number(n).toFixed(2);

// ---------- tabs ----------
// #men / #women / #kids deep-links straight to a section; otherwise open
// the first one that actually has something in it.
const tabs = document.querySelectorAll('.tab[data-section]');
const panels = document.querySelectorAll('.tab-panel[data-section]');
function showSection(key) {
  tabs.forEach((t) => {
    const on = t.dataset.section === key;
    t.classList.toggle('is-active', on);
    t.setAttribute('aria-selected', on);
  });
  panels.forEach((p) => p.classList.toggle('is-active', p.dataset.section === key));
}
tabs.forEach((t) => t.addEventListener('click', () => {
  showSection(t.dataset.section);
  history.replaceState(null, '', '#' + t.dataset.section);
}));
const fromHash = location.hash.slice(1);
const firstStocked = (products[0] || {}).section;
showSection([...tabs].some((t) => t.dataset.section === fromHash) ? fromHash : firstStocked);

// ---------- basket (this browser only) ----------
// { productId: quantity }. Reconciled against the live product list on
// every load, so a sold-out or unpublished piece silently drops out and
// quantities never exceed current stock. The server re-checks anyway.
const BASKET_KEY = 'eartha.basket';
let basket = {};
try { basket = JSON.parse(localStorage.getItem(BASKET_KEY)) || {}; } catch { basket = {}; }
for (const id of Object.keys(basket)) {
  if (!byId[id]) delete basket[id];
  else basket[id] = Math.min(basket[id], byId[id].stock);
}
const saveBasket = () => {
  try { localStorage.setItem(BASKET_KEY, JSON.stringify(basket)); } catch { /* private mode — basket just won't persist */ }
};

const fab = document.getElementById('basketFab');
const basketOverlay = document.getElementById('basketOverlay');
const linesEl = document.getElementById('basketLines');

function basketCount() {
  return Object.values(basket).reduce((a, b) => a + b, 0);
}

function renderBasket() {
  const count = basketCount();
  document.getElementById('basketCount').textContent = count;
  fab.hidden = count === 0;
  const ids = Object.keys(basket);
  linesEl.innerHTML = ids.length
    ? ids.map((id) => {
      const p = byId[id];
      return `
        <div class="basket-line">
          <img src="${Eartha.esc(p.images[0])}" alt="">
          <div style="flex:1;min-width:0;">
            <p class="product-name">${Eartha.esc(p.name)}</p>
            <p class="product-meta">${money(p.price)}${p.size ? ' · SIZE ' + Eartha.esc(p.size) : ''}</p>
            <div class="qty-row">
              <button type="button" class="qty-btn" data-dec="${id}" aria-label="One fewer">−</button>
              <span>${basket[id]}</span>
              <button type="button" class="qty-btn" data-inc="${id}" aria-label="One more" ${basket[id] >= p.stock ? 'disabled' : ''}>+</button>
              <button type="button" class="link-underline basket-remove" data-rm="${id}">REMOVE</button>
            </div>
          </div>
          <p class="product-price">${money(p.price * basket[id])}</p>
        </div>`;
    }).join('')
    : '<div class="empty">YOUR BASKET IS EMPTY.</div>';
  const total = ids.reduce((sum, id) => sum + byId[id].price * basket[id], 0);
  document.getElementById('basketTotal').textContent = money(total);
}

linesEl.addEventListener('click', (e) => {
  const t = e.target.closest('button');
  if (!t) return;
  if (t.dataset.inc) basket[t.dataset.inc] = Math.min(basket[t.dataset.inc] + 1, byId[t.dataset.inc].stock);
  if (t.dataset.dec) basket[t.dataset.dec] -= 1;
  if (t.dataset.rm) basket[t.dataset.rm] = 0;
  for (const id of Object.keys(basket)) if (basket[id] <= 0) delete basket[id];
  saveBasket();
  renderBasket();
});

// ---------- overlays ----------
let lastFocus = null;
function openOverlay(el) {
  lastFocus = document.activeElement;
  el.hidden = false;
  document.body.classList.add('no-scroll');
  el.querySelector('.shop-close').focus();
}
function closeOverlay(el) {
  el.hidden = true;
  document.body.classList.remove('no-scroll');
  if (lastFocus) lastFocus.focus();
}
document.querySelectorAll('.shop-overlay').forEach((ov) => {
  ov.addEventListener('click', (e) => {
    if (e.target === ov || e.target.closest('[data-close]')) closeOverlay(ov);
  });
});
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape') return;
  document.querySelectorAll('.shop-overlay:not([hidden])').forEach(closeOverlay);
});
fab.addEventListener('click', () => openOverlay(basketOverlay));

// ---------- product detail ----------
const productOverlay = document.getElementById('productOverlay');
const pdImg = document.getElementById('pdImg');
const pdQty = document.getElementById('pdQty');
let current = null;

document.querySelectorAll('.product-card').forEach((card) => {
  card.addEventListener('click', () => {
    const p = byId[card.dataset.product];
    if (!p) return;
    current = p;
    pdImg.src = p.images[0];
    pdImg.alt = p.name;
    document.getElementById('pdThumbs').innerHTML = p.images.length > 1
      ? p.images.map((src, i) => `<button type="button" data-src="${Eartha.esc(src)}" aria-label="Photo ${i + 1}"><img src="${Eartha.esc(src)}" alt=""></button>`).join('')
      : '';
    document.getElementById('pdName').textContent = p.name;
    document.getElementById('pdPrice').textContent = money(p.price);
    document.getElementById('pdMeta').textContent = p.size ? 'SIZE ' + p.size : '';
    document.getElementById('pdDesc').textContent = p.description;
    // one-off pieces (stock 1) don't need a quantity picker
    document.getElementById('pdQtyField').hidden = p.stock <= 1;
    pdQty.max = p.stock;
    pdQty.value = 1;
    openOverlay(productOverlay);
  });
});

document.getElementById('pdThumbs').addEventListener('click', (e) => {
  const b = e.target.closest('button[data-src]');
  if (b) pdImg.src = b.dataset.src;
});

document.getElementById('pdAdd').addEventListener('click', () => {
  const want = Math.max(1, Math.floor(Number(pdQty.value) || 1));
  const have = basket[current.id] || 0;
  const next = Math.min(have + want, current.stock);
  if (next === have) {
    Eartha.toast(current.stock === 1 ? 'ALREADY IN YOUR BASKET — IT\'S A ONE-OFF PIECE' : 'NO MORE IN STOCK');
    return;
  }
  basket[current.id] = next;
  saveBasket();
  renderBasket();
  closeOverlay(productOverlay);
  Eartha.toast('ADDED TO BASKET');
});

// ---------- checkout ----------
const form = document.getElementById('checkoutForm');
const msg = document.getElementById('checkoutMsg');
const val = (id) => document.getElementById(id).value.trim();

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const ids = Object.keys(basket);
  if (!ids.length) {
    msg.textContent = 'YOUR BASKET IS EMPTY.';
    msg.className = 'form-msg is-error';
    return;
  }
  const email = val('oEmail');
  if (!val('oName') || !val('oPhone') || !val('oCity') || !val('oAddress') ||
      (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))) {
    msg.textContent = 'FILL IN YOUR NAME, PHONE, CITY AND ADDRESS' + (email ? ', AND CHECK YOUR EMAIL' : '') + '.';
    msg.className = 'form-msg is-error';
    return;
  }

  const btn = form.querySelector('button[type="submit"]');
  btn.disabled = true;
  msg.textContent = 'PLACING YOUR ORDER...';
  msg.className = 'form-msg';
  const res = await Eartha.submitShopOrder({
    full_name: val('oName'),
    phone: val('oPhone'),
    email,
    city: val('oCity'),
    address: val('oAddress'),
    building: val('oBuilding'),
    floor_unit: val('oFloor'),
    notes: val('oNotes'),
    items: ids.map((id) => ({ product: id, quantity: basket[id] })),
    website: val('oWebsite'),
    form_token: form.dataset.formToken,
  });
  btn.disabled = false;

  if (res.error) {
    msg.textContent = res.error.toUpperCase();
    msg.className = 'form-msg is-error';
    return;
  }
  basket = {};
  saveBasket();
  form.reset();
  linesEl.innerHTML = `<div class="empty">THANK YOU — ORDER ${Eartha.esc(res.order)} IS PLACED.<br>WE'LL CALL YOU TO CONFIRM DELIVERY.</div>`;
  document.getElementById('basketTotal').textContent = money(0);
  document.getElementById('basketCount').textContent = 0;
  msg.textContent = '';
});

renderBasket();
