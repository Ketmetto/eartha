/* ============================================================
   EARTHA — main.js
   What-we-accept marquee · Newsletter
   ============================================================ */

// ---------- What we accept: infinite, swipeable marquee ----------
// The strip scrolls itself left by exactly one group width, so the group is
// duplicated here to fill the gap it leaves behind — the loop point is then
// invisible. Duplicating in JS keeps the cards written once in the HTML.
// A single clone only covers that gap if the visible strip is narrower than
// one group — on wide viewports (group width is fixed once cards hit their
// max clamp() size) a lone clone runs out of cards before the wrap point,
// showing blank space. So clone enough copies to always keep at least one
// full group's worth of cards ahead of whatever's on screen.
//
// The travel is applied as scrollLeft rather than a transform, which means the
// element stays a real horizontal scroller: a touch swipe or trackpad flick
// moves it natively, and the loop simply carries on from the new position.
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
  // seconds to travel one group — with six cards this is the ~43px/s the strip
  // has always run at, and it stays honest if cards are added or removed
  const SECONDS_PER_GROUP = 58;
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
    // Exact equality, not a pixel-distance tolerance: a slow frame (main-
    // thread jank) can make a single write bigger than any fixed
    // tolerance, misreading it as a user scroll and pausing the animation
    // for RESUME_DELAY. `applied` is read back from el.scrollLeft right
    // after every write, so it always matches our latest write exactly,
    // however large — that's what distinguishes "we moved this" from "the
    // user did," not proximity.
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
    // gesture — only primary-mouse/touch pointers reliably get a matching
    // pointerup routed back here; a right-click's context menu can
    // swallow or misdirect it, leaving `held` stuck true and the marquee
    // frozen for the rest of the page's life.
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
