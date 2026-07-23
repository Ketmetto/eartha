/* ============================================================
   EARTHA — main.js
   What-we-accept carousel · Newsletter
   ============================================================ */

// ---------- What we accept: carousel ----------
const track = document.getElementById('acceptTrack');
const cards = Array.from(track.querySelectorAll('.accept-card'));
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');

let active = 0;
const AUTOPLAY_MS = 4000;
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
let autoplayTimer = null;

function setActive(index) {
  active = (index + cards.length) % cards.length;

  cards.forEach((c, i) => {
    c.style.opacity = i === active ? '1' : '0.45';
  });

  cards[active].scrollIntoView({
    behavior: 'smooth',
    block: 'nearest',
    inline: 'start',
  });
}

function startAutoplay() {
  if (reducedMotion) return;
  stopAutoplay();
  autoplayTimer = setInterval(() => setActive(active + 1), AUTOPLAY_MS);
}

function stopAutoplay() {
  if (autoplayTimer) clearInterval(autoplayTimer);
}

function goTo(index) {
  setActive(index);
  startAutoplay(); // manual interaction resets the timer instead of stacking
}

prevBtn.addEventListener('click', () => goTo(active - 1));
nextBtn.addEventListener('click', () => goTo(active + 1));
track.addEventListener('mouseenter', stopAutoplay);
track.addEventListener('mouseleave', startAutoplay);

// start with all cards fully visible until the carousel interacts
cards.forEach((c) => (c.style.opacity = '1'));
startAutoplay();

// ---------- Newsletter ----------
const form = document.getElementById('newsletterForm');
const msg = document.getElementById('newsletterMsg');

form.addEventListener('submit', (e) => {
  e.preventDefault();
  const email = form.email.value.trim();
  const valid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

  if (!valid) {
    msg.textContent = 'ENTER A VALID EMAIL ADDRESS.';
    return;
  }

  // Hook this up to your backend / mail provider later
  msg.textContent = 'SIGNED UP — WATCH YOUR INBOX.';
  form.reset();
});
