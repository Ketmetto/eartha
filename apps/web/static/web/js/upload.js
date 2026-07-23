/* EARTHA — upload.js */

let user = Eartha.requireAuth();
if (user) {
  Eartha.renderHeader(user, 'upload');

  // ---------- photos ----------
  const drop = document.getElementById('photoDrop');
  const input = document.getElementById('photos');
  const previews = document.getElementById('photoPreviews');
  const MAX_PHOTOS = 5;
  let photos = []; // dataURLs

  const renderPreviews = () => {
    previews.innerHTML = photos
      .map(
        (src, i) => `
        <div class="ph">
          <img src="${src}" alt="Photo ${i + 1}">
          <button type="button" class="rm" data-i="${i}" aria-label="Remove photo ${i + 1}">×</button>
        </div>`
      )
      .join('');
  };

  previews.addEventListener('click', (e) => {
    const btn = e.target.closest('.rm');
    if (!btn) return;
    photos.splice(Number(btn.dataset.i), 1);
    renderPreviews();
  });

  async function addFiles(fileList) {
    const files = Array.from(fileList).filter((f) => f.type.startsWith('image/'));
    for (const file of files) {
      if (photos.length >= MAX_PHOTOS) {
        Eartha.toast('MAX 5 PHOTOS PER ITEM');
        break;
      }
      try {
        photos.push(await Eartha.compressImage(file));
      } catch {
        Eartha.toast('COULD NOT READ ONE OF THE IMAGES');
      }
    }
    renderPreviews();
  }

  drop.addEventListener('click', () => input.click());
  drop.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); }
  });
  input.addEventListener('change', () => { addFiles(input.files); input.value = ''; });

  ['dragenter', 'dragover'].forEach((ev) =>
    drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('is-over'); })
  );
  ['dragleave', 'drop'].forEach((ev) =>
    drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove('is-over'); })
  );
  drop.addEventListener('drop', (e) => addFiles(e.dataTransfer.files));

  // ---------- pickup address (asked once, saved to profile) ----------
  const addressField = document.getElementById('addressField');
  if (!user.address) addressField.hidden = false;

  // ---------- submit ----------
  document.getElementById('uploadForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const msg = document.getElementById('uploadMsg');

    if (photos.length === 0) {
      msg.textContent = 'ADD AT LEAST ONE PHOTO — IT\'S REQUIRED FOR REVIEW.';
      msg.className = 'form-msg is-error';
      return;
    }

    if (!addressField.hidden) {
      const address = document.getElementById('pickupAddress').value.trim();
      if (!address) {
        msg.textContent = 'ADD A PICKUP ADDRESS — OUR DRIVER NEEDS SOMEWHERE TO GO.';
        msg.className = 'form-msg is-error';
        return;
      }
      user = Eartha.updateUser(user.id, { address });
      addressField.hidden = true;
    }

    const sub = Eartha.addSubmission({
      userId: user.id,
      category: document.getElementById('category').value,
      condition: document.querySelector('input[name="condition"]:checked').value,
      photos,
      description: document.getElementById('description').value.trim(),
    });

    if (!sub) return; // storage error already toasted

    msg.textContent = `SUBMITTED — ${sub.num} IS NOW AWAITING REVIEW.`;
    msg.className = 'form-msg is-ok';
    photos = [];
    renderPreviews();
    e.target.reset();
    renderSubs();
    Eartha.toast(`${sub.num} SUBMITTED FOR REVIEW`);
  });

  // ---------- my submissions feed ----------
  const STATUS_NOTES = {
    pending: 'AWAITING REVIEW',
    accepted: 'APPROVED — PICKUP BEING ARRANGED',
    rejected: '',
    dispatched: 'DRIVER ON THE WAY',
    collected: 'COLLECTED — POINTS BEING ASSIGNED',
    completed: '',
  };

  function renderSubs() {
    const list = Eartha.submissions().filter((s) => s.userId === user.id).sort((a, b) => b.createdAt - a.createdAt);
    const el = document.getElementById('subList');

    if (list.length === 0) {
      el.innerHTML = '<div class="empty">NOTHING YET — YOUR FIRST DONATION STARTS ON THE LEFT.</div>';
      return;
    }

    el.innerHTML = list
      .map((s) => {
        const note =
          s.status === 'rejected'
            ? `REASON: ${Eartha.esc(s.rejectReason || '—')}`
            : s.status === 'completed'
            ? `+${s.points} POINTS AWARDED`
            : STATUS_NOTES[s.status];
        const photo = s.photos[0]
          ? `<img class="thumb-64" src="${s.photos[0]}" alt="">`
          : `<div class="thumb-64"></div>`;
        return `
        <div class="card">
          <div class="card-row">
            ${photo}
            <div style="flex:1;min-width:160px;">
              <p class="batch-tag">${s.num} · ${Eartha.fmtDate(s.createdAt)}</p>
              <p style="font-weight:700;text-transform:uppercase;letter-spacing:var(--track-wide);font-size:12px;margin-top:2px;">
                ${Eartha.esc(s.category)} · ${Eartha.esc(s.condition)}
              </p>
              <p class="muted" style="font-size:11px;margin-top:4px;">${note}</p>
            </div>
            ${Eartha.badge(s.status)}
          </div>
        </div>`;
      })
      .join('');
  }

  // next batch number preview (count so far + 1, display only)
  document.getElementById('nextBatch').textContent =
    'NEXT BATCH — N. ' + String(Eartha.submissions().length + 1).padStart(4, '0');

  renderSubs();
}
