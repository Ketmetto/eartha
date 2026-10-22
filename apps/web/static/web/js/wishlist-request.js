/* EARTHA — wishlist-request.js */

const form = document.getElementById('wishlistForm');
const msg = document.getElementById('wishlistMsg');
const val = (id) => document.getElementById(id).value.trim();

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const organization = val('wOrg');
  const contactName = val('wName');
  const email = val('wEmail');
  const itemsNeeded = val('wItems');

  if (!organization || !contactName || !itemsNeeded || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    msg.textContent = 'FILL IN THE ORGANIZATION, CONTACT PERSON, A VALID EMAIL AND WHAT IS NEEDED.';
    msg.className = 'form-msg is-error';
    return;
  }

  const btn = form.querySelector('button[type="submit"]');
  btn.disabled = true;
  const res = await Eartha.submitWishlistRequest({
    organization,
    contact_name: contactName,
    email,
    phone: val('wPhone'),
    items_needed: itemsNeeded,
    sizes: val('wSizes'),
    quantity: val('wQty'),
    location: val('wLocation'),
    needed_by: val('wNeededBy') || null,
    website: val('wWebsite'),
    form_token: form.dataset.formToken,
  });
  btn.disabled = false;

  if (res.error) {
    msg.textContent = res.error.toUpperCase();
    msg.className = 'form-msg is-error';
    return;
  }
  form.reset();
  msg.textContent = 'REQUEST SENT — WE REVIEW EVERY REQUEST AND REPLY BY EMAIL.';
  msg.className = 'form-msg is-ok';
});
