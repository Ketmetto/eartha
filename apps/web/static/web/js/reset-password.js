/* EARTHA — reset-password.js */

const form = document.getElementById('resetForm');
const msg = document.getElementById('resetMsg');
const loginLink = document.getElementById('resetLoginLink');
const params = new URLSearchParams(location.search);
const uid = params.get('uid');
const token = params.get('token');

if (!uid || !token) {
  form.hidden = true;
  msg.textContent = 'MISSING RESET PARAMETERS — REQUEST A NEW LINK FROM THE LOGIN PAGE.';
  msg.className = 'form-msg is-error';
  loginLink.hidden = false;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const password = document.getElementById('newPassword').value;
  const confirm = document.getElementById('newPassword2').value;

  if (password !== confirm) {
    msg.textContent = 'PASSWORDS DO NOT MATCH.';
    msg.className = 'form-msg is-error';
    return;
  }

  const submitBtn = form.querySelector('button[type="submit"]');
  msg.textContent = '';
  submitBtn.disabled = true;
  const res = await Eartha.confirmPasswordReset(uid, token, password, confirm);
  submitBtn.disabled = false;

  if (res.error) {
    msg.textContent = res.error.toUpperCase();
    msg.className = 'form-msg is-error';
    return;
  }
  msg.textContent = res.detail.toUpperCase();
  msg.className = 'form-msg is-ok';
  form.hidden = true;
  loginLink.hidden = false;
});
