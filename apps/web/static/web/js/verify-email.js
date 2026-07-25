/* EARTHA — verify-email.js */

const msg = document.getElementById('verifyMsg');
const loginLink = document.getElementById('verifyLoginLink');
const params = new URLSearchParams(location.search);
const uid = params.get('uid');
const token = params.get('token');

(async () => {
  if (!uid || !token) {
    msg.textContent = 'MISSING VERIFICATION PARAMETERS.';
    msg.className = 'form-msg is-error';
    loginLink.hidden = false;
    return;
  }

  const res = await Eartha.verifyEmail(uid, token);
  if (res.error) {
    msg.textContent = res.error.toUpperCase();
    msg.className = 'form-msg is-error';
  } else {
    msg.textContent = res.detail.toUpperCase();
    msg.className = 'form-msg is-ok';
  }
  loginLink.hidden = false;
})();
