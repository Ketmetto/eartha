/* EARTHA — upload.js */

let user = Eartha.requireAuth();
if (user) {
  Eartha.renderHeader(user, 'upload');

  // ---------- photos ----------
  const drop = document.getElementById('photoDrop');
  const input = document.getElementById('photos');
  const previews = document.getElementById('photoPreviews');
  const MAX_PHOTOS = 5;
  // { file: File, preview: dataURL } — the original File is what actually
  // gets uploaded; the compressed dataURL is only for the on-page thumbnail.
  let photos = [];

  const renderPreviews = () => {
    previews.innerHTML = photos
      .map(
        (p, i) => `
        <div class="ph">
          <img src="${p.preview}" alt="Photo ${i + 1}">
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
        photos.push({ file, preview: await Eartha.compressImage(file) });
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
  const pickupInput = document.getElementById('pickupAddress');
  Eartha.fetchAddress()
    .then((address) => { if (!address.line1) addressField.hidden = false; })
    .catch(() => { addressField.hidden = false; });

  // Set together when a real autocomplete suggestion is picked; cleared on
  // further manual typing so a stale structured address never gets sent
  // for text the user has since edited by hand.
  let addressParts = null;
  const mapsKey = JSON.parse(document.getElementById('google-maps-key').textContent);
  EarthaAddressAutocomplete(
    pickupInput, mapsKey, document.getElementById('pickupMap'),
    (parts) => { addressParts = parts; }, document.getElementById('pickupLocate')
  );
  pickupInput.addEventListener('input', () => { addressParts = null; });
  const buildingInput = document.getElementById('pickupBuilding');
  const floorUnitInput = document.getElementById('pickupFloorUnit');
  const instructionsInput = document.getElementById('pickupInstructions');

  // ---------- phone number (asked once, saved to profile) ----------
  const phoneField = document.getElementById('phoneField');
  const phoneInput = document.getElementById('uploaderPhone');
  Eartha.fetchMe()
    .then((me) => { if (!me.phone) phoneField.hidden = false; })
    .catch(() => { phoneField.hidden = false; });

  const phoneVerifyHint = document.getElementById('uploaderPhoneVerifyHint');
  const phoneVerifyLink = document.getElementById('uploaderPhoneVerify');
  phoneInput.addEventListener('input', () => {
    const url = Eartha.whatsappVerifyUrl(phoneInput.value);
    phoneVerifyHint.hidden = !url;
    if (url) phoneVerifyLink.href = url;
  });

  // ---------- submit ----------
  document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const msg = document.getElementById('uploadMsg');
    const submitBtn = e.target.querySelector('button[type="submit"]');

    if (photos.length === 0) {
      msg.textContent = 'ADD AT LEAST ONE PHOTO — IT\'S REQUIRED FOR REVIEW.';
      msg.className = 'form-msg is-error';
      return;
    }

    let addressToSave = null;
    if (!addressField.hidden) {
      const typed = pickupInput.value.trim();
      if (!typed) {
        msg.textContent = 'ADD A PICKUP ADDRESS — OUR DRIVER NEEDS SOMEWHERE TO GO.';
        msg.className = 'form-msg is-error';
        return;
      }
      // addressParts only exists if a real suggestion was picked;
      // building/floor_unit/instructions are separate manual fields
      // either way.
      addressToSave = {
        ...(addressParts || {}),
        line1: (addressParts && addressParts.line1) || typed,
        building: buildingInput.value.trim(),
        floor_unit: floorUnitInput.value.trim(),
        instructions: instructionsInput.value.trim(),
      };
    }

    let phoneToSave = null;
    if (!phoneField.hidden) {
      const typedPhone = phoneInput.value.trim();
      if (!typedPhone) {
        msg.textContent = 'ADD A PHONE NUMBER — OUR DRIVER NEEDS TO BE ABLE TO REACH YOU.';
        msg.className = 'form-msg is-error';
        return;
      }
      phoneToSave = typedPhone;
    }

    submitBtn.disabled = true;
    msg.textContent = 'UPLOADING...';
    msg.className = 'form-msg';

    try {
      if (addressToSave) {
        await Eartha.updateAddress(addressToSave);
        addressField.hidden = true;
      }
      if (phoneToSave) {
        await Eartha.updatePhone(phoneToSave);
        phoneField.hidden = true;
      }

      const sub = await Eartha.createSubmission({
        category: document.getElementById('category').value,
        condition: document.querySelector('input[name="condition"]:checked').value,
        description: document.getElementById('description').value.trim(),
        files: photos.map((p) => p.file),
      });

      msg.textContent = `SUBMITTED — ${sub.id.slice(0, 8).toUpperCase()} IS NOW AWAITING REVIEW.`;
      msg.className = 'form-msg is-ok';
      photos = [];
      renderPreviews();
      e.target.reset();
      await renderSubs();
      Eartha.toast('SUBMITTED FOR REVIEW');
    } catch (err) {
      msg.textContent = err.message || 'SOMETHING WENT WRONG — TRY AGAIN.';
      msg.className = 'form-msg is-error';
    } finally {
      submitBtn.disabled = false;
    }
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

  // This sidebar only ever shows the first page — it's a quick-glance
  // summary next to the upload form, not the full history (that's the
  // Submission History tab on the profile page, which paginates properly).
  async function renderSubs() {
    const el = document.getElementById('subList');
    let data;
    try {
      data = await Eartha.fetchMySubmissions();
    } catch (err) {
      el.innerHTML = `<div class="empty">${Eartha.esc(err.message || 'COULD NOT LOAD SUBMISSIONS.')}</div>`;
      return;
    }
    const list = data.items;

    document.getElementById('nextBatch').textContent =
      'NEXT BATCH — N. ' + String(data.count + 1).padStart(4, '0');

    if (list.length === 0) {
      el.innerHTML = '<div class="empty">NOTHING YET — YOUR FIRST DONATION STARTS ON THE LEFT.</div>';
      return;
    }

    const seeAll = data.hasMore
      ? `<a href="/profile/" class="link-underline" style="font-size:10px;display:block;margin-top:16px;">SEE FULL HISTORY IN YOUR PROFILE</a>`
      : '';

    el.innerHTML = list
      .map((s) => {
        const note =
          s.status === 'rejected'
            ? `REASON: ${Eartha.esc(s.rejectReason || '—')}`
            : STATUS_NOTES[s.status] || '';
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
      .join('') + seeAll;
  }

  renderSubs();
}
