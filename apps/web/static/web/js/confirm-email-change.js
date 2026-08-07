/* EARTHA — confirm-email-change.js */

const msg = document.getElementById('confirmMsg');
const loginLink = document.getElementById('confirmLoginLink');
const params = new URLSearchParams(location.search);
const uid = params.get('uid');
const token = params.get('token');

(async () => {
  if (!uid || !token) {
    msg.textContent = 'MISSING CONFIRMATION PARAMETERS.';
    msg.className = 'form-msg is-error';
    loginLink.hidden = false;
    return;
  }

  const res = await Eartha.confirmEmailChange(uid, token);
  if (res.error) {
    msg.textContent = res.error.toUpperCase();
    msg.className = 'form-msg is-error';
  } else {
    msg.textContent = res.detail.toUpperCase();
    msg.className = 'form-msg is-ok';
  }
  loginLink.hidden = false;
})();
