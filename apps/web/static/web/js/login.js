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

// ---------- forgot password ----------
const forgotForm = document.getElementById('forgotForm');
const authSwitch = document.getElementById('authSwitch');
const socialLoginBlock = document.getElementById('socialLoginBlock');

function showForgotForm(show) {
  forgotForm.hidden = !show;
  loginForm.hidden = show;
  authSwitch.hidden = show;
  socialLoginBlock.hidden = show;
  registerForm.hidden = true;
}

document.getElementById('forgotLink').addEventListener('click', (e) => {
  e.preventDefault();
  showForgotForm(true);
});

document.getElementById('backToLoginLink').addEventListener('click', (e) => {
  e.preventDefault();
  showForgotForm(false);
  switchTab(true);
});

forgotForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = document.getElementById('forgotMsg');
  const submitBtn = forgotForm.querySelector('button[type="submit"]');
  msg.textContent = '';
  submitBtn.disabled = true;
  const res = await Eartha.requestPasswordReset(document.getElementById('forgotEmail').value);
  submitBtn.disabled = false;
  if (res.error) {
    msg.textContent = res.error.toUpperCase();
    msg.className = 'form-msg is-error';
    return;
  }
  // Backend always returns the same generic message regardless of whether
  // the email matched an account — see PasswordResetRequestView, prevents
  // this form from being used to enumerate registered addresses.
  msg.textContent = res.detail.toUpperCase();
  msg.className = 'form-msg is-ok';
  forgotForm.querySelector('input').disabled = true;
  submitBtn.disabled = true;
});

// ---------- Firebase Sign-In (Google) ----------
// Apple removed — Sign in with Apple needs a paid Apple Developer Program
// membership to configure at all, not something set up here. Same button
// drives both sign-in and sign-up — the backend creates the account on
// first social login, so there's nothing to disambiguate here.
const firebaseConfig = JSON.parse(document.getElementById('firebase-config').textContent);
const googleBtn = document.getElementById('googleSignInBtn');

if (!firebaseConfig.apiKey) {
  googleBtn.disabled = true;
  googleBtn.title = 'Google sign-in is not configured yet.';
} else {
  firebase.initializeApp(firebaseConfig);

  // Inside the Android app (eartha-app, a Capacitor shell around this
  // site), Google blocks its OAuth popup in embedded WebViews. There the
  // native FirebaseAuthentication plugin shows Google's own account
  // picker and hands back a Google ID token, which signs in to the same
  // Firebase JS SDK — so everything after this point, including the
  // backend call, is identical to the browser flow.
  const cap = window.Capacitor;
  const inApp = !!(cap && cap.isNativePlatform && cap.isNativePlatform());

  async function firebaseUserFromGoogle() {
    if (!inApp) {
      return (await firebase.auth().signInWithPopup(new firebase.auth.GoogleAuthProvider())).user;
    }
    const plugin = cap.Plugins && cap.Plugins.FirebaseAuthentication;
    if (!plugin) {
      const unavailable = new Error('Native Google sign-in plugin missing');
      unavailable.code = 'app/google-unavailable';
      throw unavailable;
    }
    const native = await plugin.signInWithGoogle();
    const credential = firebase.auth.GoogleAuthProvider.credential(native.credential.idToken);
    return (await firebase.auth().signInWithCredential(credential)).user;
  }

  googleBtn.addEventListener('click', async () => {
    googleBtn.disabled = true;
    try {
      const fbUser = await firebaseUserFromGoogle();
      const idToken = await fbUser.getIdToken();
      const res = await Eartha.socialLogin({
        id_token: idToken,
        display_name: fbUser.displayName || '',
      });
      if (res.error) {
        Eartha.toast(res.error);
        return;
      }
      location.href = res.user.isAdmin ? '/dashboard/' : '/';
    } catch (err) {
      console.error('Firebase sign-in error:', err.code, err.message);
      // Backing out of Google's native account picker isn't a failure.
      if (/cancel/i.test(err.message || '')) return;
      Eartha.toast(err.code === 'app/google-unavailable'
        ? 'GOOGLE SIGN-IN NEEDS THE LATEST APP — USE YOUR EMAIL AND PASSWORD FOR NOW.'
        : 'SIGN-IN FAILED — PLEASE TRY AGAIN.');
    } finally {
      googleBtn.disabled = false;
    }
  });
}
