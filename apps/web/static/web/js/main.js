/* ============================================================
   EARTHA — main.js
   What-we-accept marquee · Newsletter
   ============================================================ */

// ---------- What we accept: infinite marquee ----------
// A native CSS animation (see .accept-marquee.is-marquee in app.css) does
// the actual scrolling — smoother and more reliable than driving it by
// hand every frame from JS. This just measures one group's real rendered
// width once, clones enough copies to comfortably cover the viewport
// twice over, and hands that exact pixel value to the CSS animation as
// the translate distance. Because every copy is identical and adjacent,
// translating by exactly one group's width always lands the next copy
// precisely where the previous one started — regardless of how many
// copies exist. (translateX(-50%) on a doubled track was the original
// approach; it requires two independently-laid-out flex groups to land
// on the exact same subpixel width, which clamp()-based card widths don't
// reliably do — that drift was the blank gap at the seam.)
const marquee = document.getElementById('acceptMarquee');
const track = marquee && marquee.querySelector('.accept-track');
const group = marquee && marquee.querySelector('.accept-group');

if (track && group) {
  const groupWidth = group.getBoundingClientRect().width;

  const copiesNeeded = Math.max(2, Math.ceil((marquee.clientWidth * 2) / groupWidth) + 1);
  for (let i = 1; i < copiesNeeded; i++) {
    const clone = group.cloneNode(true);
    clone.setAttribute('aria-hidden', 'true'); // screen readers read the cards once
    track.appendChild(clone);
  }

  if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const SPEED_PX_PER_S = 43; // matches the original design's pace
    track.style.setProperty('--marquee-distance', `${groupWidth}px`);
    track.style.animationDuration = `${groupWidth / SPEED_PX_PER_S}s`;
    marquee.classList.add('is-marquee');
  }
}

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
