/* EARTHA — login.js */

// already signed in? admins go to their dashboard, everyone else to the homepage
const existingUser = Eartha.currentUser();
if (existingUser) location.href = existingUser.isAdmin ? '/dashboard/' : '/';

// forced logout (session expired / access revoked) leaves a one-time
// reason here — show it, then clear so it doesn't reappear on a later visit
const flash = sessionStorage.getItem('eartha:flash');
if (flash) {
  sessionStorage.removeItem('eartha:flash');
  const loginMsg = document.getElementById('loginMsg');
  if (loginMsg) {
    loginMsg.textContent = flash;
    loginMsg.className = 'form-msg is-error';
  }
}

const tabLogin = document.getElementById('tabLogin');
const tabRegister = document.getElementById('tabRegister');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');

function switchTab(showLogin) {
  tabLogin.classList.toggle('is-active', showLogin);
  tabRegister.classList.toggle('is-active', !showLogin);
  tabLogin.setAttribute('aria-selected', String(showLogin));
  tabRegister.setAttribute('aria-selected', String(!showLogin));
  loginForm.hidden = !showLogin;
  registerForm.hidden = showLogin;
}

tabLogin.addEventListener('click', () => switchTab(true));
tabRegister.addEventListener('click', () => switchTab(false));

// deep link: login.html#register
if (location.hash === '#register') switchTab(false);

// ---------- sign in ----------
loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = document.getElementById('loginMsg');
  const submitBtn = loginForm.querySelector('button[type="submit"]');
  msg.textContent = '';
  submitBtn.disabled = true;
  const res = await Eartha.login(
    document.getElementById('loginEmail').value,
    document.getElementById('loginPassword').value
  );
  submitBtn.disabled = false;
  if (res.error) {
    msg.textContent = res.error;
    msg.className = 'form-msg is-error';
    return;
  }
  // redirect logic: admins go to their dashboard, everyone else lands on the homepage
  location.href = res.user.isAdmin ? '/dashboard/' : '/';
});

// ---------- register ----------
registerForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = document.getElementById('registerMsg');
  const password = document.getElementById('regPassword').value;
  const confirm = document.getElementById('regPassword2').value;

  if (password !== confirm) {
    msg.textContent = 'PASSWORDS DO NOT MATCH.';
    msg.className = 'form-msg is-error';
    return;
  }
  if (!document.getElementById('regTerms').checked) {
    msg.textContent = 'PLEASE AGREE TO THE TERMS TO CONTINUE.';
    msg.className = 'form-msg is-error';
    return;
  }

  const submitBtn = registerForm.querySelector('button[type="submit"]');
  msg.textContent = '';
  submitBtn.disabled = true;
  const res = await Eartha.register({
    name: document.getElementById('regName').value,
    email: document.getElementById('regEmail').value,
    password,
    passwordConfirm: confirm,
    agreeToTerms: true,
  });
  submitBtn.disabled = false;

  if (res.error) {
    msg.textContent = res.error;
    msg.className = 'form-msg is-error';
    return;
  }
  location.href = '/';
});

document.getElementById('forgotLink').addEventListener('click', (e) => {
  e.preventDefault();
  Eartha.toast('PASSWORD RESET COMING SOON — CONTACT US MEANWHILE');
});

// ---------- Firebase Sign-In (Google + Apple) ----------
// Same buttons drive both sign-in and sign-up — the backend creates the
// account on first social login, so there's nothing to disambiguate here.
const firebaseConfig = JSON.parse(document.getElementById('firebase-config').textContent);
const googleBtn = document.getElementById('googleSignInBtn');
const appleBtn = document.getElementById('appleSignInBtn');

if (!firebaseConfig.apiKey) {
  googleBtn.disabled = true;
  googleBtn.title = 'Google sign-in is not configured yet.';
  appleBtn.disabled = true;
  appleBtn.title = 'Apple sign-in is not configured yet.';
} else {
  firebase.initializeApp(firebaseConfig);

  async function firebaseSignIn(btn, providerName) {
    btn.disabled = true;
    try {
      const provider = providerName === 'google'
        ? new firebase.auth.GoogleAuthProvider()
        : new firebase.auth.OAuthProvider('apple.com');
      const result = await firebase.auth().signInWithPopup(provider);
      const idToken = await result.user.getIdToken();
      const res = await Eartha.socialLogin({
        id_token: idToken,
        display_name: result.user.displayName || '',
      });
      if (res.error) {
        Eartha.toast(res.error);
        return;
      }
      location.href = res.user.isAdmin ? '/dashboard/' : '/';
    } catch (err) {
      console.error('Firebase sign-in error:', err.code, err.message);
      Eartha.toast('SIGN-IN FAILED — PLEASE TRY AGAIN.');
    } finally {
      btn.disabled = false;
    }
  }

  googleBtn.addEventListener('click', () => firebaseSignIn(googleBtn, 'google'));
  appleBtn.addEventListener('click', () => firebaseSignIn(appleBtn, 'apple'));
}
