/* ============================================================
   EARTHA — main.js
   What-we-accept marquee · Newsletter
   ============================================================ */

// ---------- What we accept: infinite, swipeable marquee ----------
// The strip scrolls left by exactly one group width, so the group is
// duplicated here to fill the gap that leaves behind, making the loop
// point invisible — enough copies to keep a full group ahead of whatever
// is on screen, since a wide viewport can outrun a single clone.
// Travel is applied as scrollLeft, not a transform, so it stays a real
// scroller: a touch swipe or trackpad flick moves it natively.
const marquee = document.getElementById('acceptMarquee');
const group = marquee && marquee.querySelector('.accept-group');

if (group) {
  const groupWidth = group.getBoundingClientRect().width;
  const copiesNeeded = Math.max(2, Math.ceil(marquee.clientWidth / groupWidth) + 1);
  for (let i = 1; i < copiesNeeded; i++) {
    const clone = group.cloneNode(true);
    clone.setAttribute('aria-hidden', 'true'); // screen readers read the cards once
    group.parentNode.appendChild(clone);
  }
  marquee.classList.add('is-marquee');
  runAcceptMarquee(marquee, group);
}

function runAcceptMarquee(el, group) {
  // seconds to travel one group — stays honest (same px/s) if cards are
  // added or removed. Lower = faster.
  const SECONDS_PER_GROUP = 45;
  const RESUME_DELAY = 700; // just long enough for a flick's momentum to land
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');

  let pos = 0;         // our own float copy of scrollLeft, so slow frames don't round away
  let applied = 0;     // the last value we wrote, to tell our scrolls from the user's
  let held = false;    // a button or finger is down on the strip
  let resumeAt = 0;
  let last = 0;

  const groupWidth = () => group.getBoundingClientRect().width;

  // one group in, the strip is showing the clone — identical pixels, so
  // rewinding by a group is invisible and the loop never ends
  const wrap = (width) => {
    if (width <= 0) return;
    pos = ((pos % width) + width) % width; // modulo, so even a long drag lands in range
  };

  const write = () => {
    el.scrollLeft = pos;
    applied = el.scrollLeft;
  };

  const frame = (now) => {
    const dt = last ? Math.min((now - last) / 1000, 0.05) : 0; // cap after a tab-out
    last = now;

    if (!held && !reduced.matches && now >= resumeAt) {
      const width = groupWidth();
      pos += (width / SECONDS_PER_GROUP) * dt;
      wrap(width);
      write();
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);

  // the user scrolled (swipe, trackpad, keyboard) — take their position as ours
  // and keep wrapping, so swiping past the end loops instead of hitting a wall
  el.addEventListener('scroll', () => {
    // Exact equality, not a pixel-distance tolerance — a slow frame can
    // make a single write bigger than any fixed tolerance, misreading it
    // as a user scroll. `applied` always matches our latest write exactly.
    if (el.scrollLeft === applied) return; // that was our own frame
    pos = el.scrollLeft;
    const width = groupWidth();
    if (width > 0 && (pos >= width || pos < 0)) {
      wrap(width);
      write();
    } else {
      applied = el.scrollLeft;
    }
    resumeAt = performance.now() + RESUME_DELAY;
  }, { passive: true });

  // Taking hold of the strip stops it — a click, or a finger landing on it.
  // Hovering deliberately does not: the motion is the point, and passing the
  // cursor over the section shouldn't freeze it. Touch drags the scroller
  // natively from here; the move handler below is the mouse equivalent.
  let dragX = null;    // where a mouse drag started, null when there isn't one
  let startScroll = 0;

  el.addEventListener('pointerdown', (e) => {
    // A non-primary button (right-click, middle-click) isn't a hold
    // gesture — its context menu can swallow the matching pointerup,
    // leaving `held` stuck true and the marquee frozen for good.
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    held = true;
    if (e.pointerType !== 'mouse') return; // touch drags the scroller natively from here
    dragX = e.clientX;
    startScroll = el.scrollLeft;
    el.setPointerCapture(e.pointerId);
    el.classList.add('is-grabbing');
  });

  el.addEventListener('pointermove', (e) => {
    if (dragX === null) return;
    pos = startScroll - (e.clientX - dragX);
    wrap(groupWidth());
    write();
  });

  // a card photo would otherwise be picked up as a native image drag mid-swipe
  el.addEventListener('dragstart', (e) => { if (dragX !== null) e.preventDefault(); });

  // let go and it picks straight back up from where it was left — a touch flick
  // still has momentum to spend, which the scroll handler's own delay covers
  const release = () => {
    held = false;
    dragX = null;
    el.classList.remove('is-grabbing');
  };

  el.addEventListener('pointerup', release);
  el.addEventListener('pointercancel', release);
}

// ---------- Newsletter ----------
const form = document.getElementById('newsletterForm');
const msg = document.getElementById('newsletterMsg');

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const email = form.email.value.trim();
  const valid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

  if (!valid) {
    msg.textContent = 'ENTER A VALID EMAIL ADDRESS.';
    return;
  }

  const submitBtn = form.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  const res = await Eartha.subscribeToNewsletter(email);
  submitBtn.disabled = false;

  if (res.error) {
    msg.textContent = res.error.toUpperCase();
    return;
  }
  msg.textContent = "YOU'RE SUBSCRIBED — THANKS FOR JOINING.";
  form.reset();
});
