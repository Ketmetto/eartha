/* EARTHA — verify.js (merchant voucher check/redeem page) */

const msg = document.getElementById('verifyMsg');
const details = document.getElementById('verifyDetails');
const brandEl = document.getElementById('verifyBrand');
const discountEl = document.getElementById('verifyDiscount');
const statusBadge = document.getElementById('verifyStatusBadge');
const redeemedAtEl = document.getElementById('verifyRedeemedAt');
const redeemBtn = document.getElementById('verifyRedeemBtn');

// /verify/<code>/ — code is the last non-empty path segment.
const code = location.pathname.split('/').filter(Boolean).pop();

function render(redemption) {
  details.hidden = false;
  brandEl.textContent = redemption.brand_name;
  discountEl.textContent = `${redemption.discount_percent}% OFF`;

  if (redemption.status === 'redeemed') {
    msg.textContent = '';
    statusBadge.textContent = 'ALREADY REDEEMED';
    statusBadge.className = 'badge badge-rejected';
    redeemedAtEl.textContent = redemption.redeemed_at
      ? `Redeemed ${Eartha.fmtDate(redemption.redeemed_at)}`
      : '';
    redeemBtn.hidden = true;
  } else {
    msg.textContent = '';
    statusBadge.textContent = 'VALID — NOT YET REDEEMED';
    statusBadge.className = 'badge badge-accepted';
    redeemedAtEl.textContent = '';
    redeemBtn.hidden = false;
  }
}

async function load() {
  if (!code) {
    msg.textContent = 'MISSING VOUCHER CODE.';
    msg.className = 'form-msg is-error';
    return;
  }
  const res = await Eartha.verifyRedemption(code);
  if (res.error) {
    msg.textContent = 'INVALID CODE — ' + res.error.toUpperCase();
    msg.className = 'form-msg is-error';
    return;
  }
  render(res.redemption);
}

redeemBtn.addEventListener('click', async () => {
  const ok = confirm("Mark this voucher as used? This can't be undone.");
  if (!ok) return;

  redeemBtn.disabled = true;
  const res = await Eartha.redeemVoucher(code);
  redeemBtn.disabled = false;

  if (res.error) {
    Eartha.toast(res.error);
    // Someone else may have just redeemed it (lost a race) — refresh the
    // displayed state either way so the page reflects reality.
    load();
    return;
  }
  render(res.redemption);
});

load();
