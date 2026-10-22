/* EARTHA — dashboard.js
   Admin homepage: aggregate stats + a quick read on what needs attention.
*/

const admin = Eartha.requireAdmin();
if (admin) {
  Eartha.renderHeader(admin, 'dashboard');
  document.getElementById('helloLine').textContent = `HELLO, ${admin.name.toUpperCase()}`;

  (async () => {
    let stats;
    try {
      stats = await Eartha.fetchDashboardStats();
    } catch (err) {
      document.getElementById('recentList').innerHTML =
        `<div class="empty">${Eartha.esc(err.message || 'COULD NOT LOAD THE DASHBOARD.')}</div>`;
      return;
    }

    // ---------- needs attention ----------
    const attention = [
      { label: 'NEEDS REVIEW', count: stats.pendingCount },
      { label: 'IN PROGRESS', count: stats.inProgressCount },
      { label: 'UNREAD MESSAGES', count: stats.unreadMessagesCount },
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
    document.getElementById('statCompleted').dataset.count = stats.completedCount;
    document.getElementById('statPoints').dataset.count = stats.totalPointsAwarded;
    document.getElementById('statDonors').dataset.count = stats.donorCount;
    document.getElementById('statBenefits').dataset.count = stats.liveBenefitsCount;

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
    document.getElementById('recentList').innerHTML = stats.recentItems.length
      ? stats.recentItems
          .map(
            (s) => `
          <div class="card">
            <div class="card-row">
              <div style="flex:1;min-width:180px;">
                <p class="batch-tag">${s.num} · ${Eartha.fmtDate(s.updatedAt)} · FROM ${Eartha.esc((s.userName || 'UNKNOWN').toUpperCase())}</p>
                <p style="font-weight:700;text-transform:uppercase;letter-spacing:var(--track-wide);font-size:12px;margin-top:2px;">
                  ${Eartha.esc(s.category)} · ${Eartha.esc(s.condition)}${Eartha.qtyLabel(s)}
                </p>
              </div>
              ${Eartha.badge(s.status)}
            </div>
          </div>`
          )
          .join('')
      : '<div class="empty">NOTHING HAS COME THROUGH YET.</div>';
  })();
}
