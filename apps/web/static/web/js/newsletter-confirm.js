/* EARTHA — newsletter-confirm.js */

const msg = document.getElementById('confirmMsg');
const homeLink = document.getElementById('confirmHomeLink');
const token = new URLSearchParams(location.search).get('token');

(async () => {
  if (!token) {
    msg.textContent = 'MISSING CONFIRMATION PARAMETERS.';
    msg.className = 'form-msg is-error';
    homeLink.hidden = false;
    return;
  }

  const res = await Eartha.confirmNewsletter(token);
  if (res.error) {
    msg.textContent = res.error.toUpperCase();
    msg.className = 'form-msg is-error';
  } else {
    msg.textContent = res.detail.toUpperCase();
    msg.className = 'form-msg is-ok';
  }
  homeLink.hidden = false;
})();
