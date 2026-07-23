/* EARTHA — dashboard.js
   Admin homepage: aggregate stats + a quick read on what needs attention.
*/

const admin = Eartha.requireAdmin();
if (admin) {
  Eartha.renderHeader(admin, 'dashboard');
  document.getElementById('helloLine').textContent = `HELLO, ${admin.name.toUpperCase()}`;

  const subs = Eartha.submissions();
  const pending = subs.filter((s) => s.status === 'pending').length;
  const inProgress = subs.filter((s) => ['accepted', 'dispatched', 'collected'].includes(s.status)).length;
  const unread = Eartha.messages().filter((m) => !m.read).length;
  const completed = subs.filter((s) => s.status === 'completed');
  const totalPoints = completed.reduce((sum, s) => sum + (s.points || 0), 0);
  const donors = Eartha.users().filter((u) => !u.isAdmin).length;
  const liveBenefits = Eartha.benefits().filter((b) => b.active).length;

  // ---------- needs attention ----------
  const attention = [
    { label: 'NEEDS REVIEW', count: pending },
    { label: 'IN PROGRESS', count: inProgress },
    { label: 'UNREAD MESSAGES', count: unread },
  ];
  document.getElementById('attentionGrid').innerHTML = attention
    .map(
      (a) => `
      <a class="card" href="/queue/" style="display:block;margin-top:0;">
        <p class="eyebrow muted">${a.label}</p>
        <p style="font-size:32px;font-weight:700;margin-top:10px;">${a.count}</p>
        <p class="link-underline" style="margin-top:16px;">GO TO QUEUE</p>
      </a>`
    )
    .join('');

  // ---------- stat band ----------
  document.getElementById('statCompleted').dataset.count = completed.length;
  document.getElementById('statPoints').dataset.count = totalPoints;
  document.getElementById('statDonors').dataset.count = donors;
  document.getElementById('statBenefits').dataset.count = liveBenefits;

  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const counters = document.querySelectorAll('[data-count]');
  const animate = (el) => {
    const target = Number(el.dataset.count);
    if (reduced) { el.textContent = target.toLocaleString(); return; }
    const start = performance.now();
    const dur = 1200;
    const tick = (t) => {
      const p = Math.min(1, (t - start) / dur);
      el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3))).toLocaleString();
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) { animate(e.target); io.unobserve(e.target); }
    });
  }, { threshold: 0.4 });
  counters.forEach((c) => io.observe(c));

  // ---------- recent activity ----------
  const userById = (id) => Eartha.users().find((u) => u.id === id) || { name: 'Unknown' };
  const recent = [...subs].sort((a, b) => b.updatedAt - a.updatedAt).slice(0, 6);
  document.getElementById('recentList').innerHTML = recent.length
    ? recent
        .map(
          (s) => `
        <div class="card">
          <div class="card-row">
            <div style="flex:1;min-width:180px;">
              <p class="batch-tag">${s.num} · ${Eartha.fmtDate(s.updatedAt)} · FROM ${Eartha.esc(userById(s.userId).name.toUpperCase())}</p>
              <p style="font-weight:700;text-transform:uppercase;letter-spacing:var(--track-wide);font-size:12px;margin-top:2px;">
                ${Eartha.esc(s.category)} · ${Eartha.esc(s.condition)}
              </p>
            </div>
            ${Eartha.badge(s.status)}
          </div>
        </div>`
        )
        .join('')
    : '<div class="empty">NOTHING HAS COME THROUGH YET.</div>';
}
