/* EARTHA — content.js
   Admin: replace the headline copy and key images on the public marketing
   pages (home/about/contact). Fixed set of slots — see apps.content.
*/

const admin = Eartha.requireAdmin();
if (admin) {
  Eartha.renderHeader(admin, 'content');

  const textsEl = document.getElementById('contentTexts');
  const imagesEl = document.getElementById('contentImages');
  const pending = {}; // key -> dataUrl, images staged but not yet saved

  function textCard(t) {
    return `
    <div class="card" data-text="${t.key}">
      <p class="eyebrow muted">${Eartha.esc(t.label)}</p>
      <div class="field" style="margin-top:10px;">
        <textarea data-input="${t.key}" rows="2">${Eartha.esc(t.value)}</textarea>
      </div>
      <button class="btn btn-sm" data-act="save-text" data-id="${t.key}">SAVE</button>
    </div>`;
  }

  function imageCard(i) {
    const preview = pending[i.key] || i.image;
    return `
    <div class="card" data-image="${i.key}">
      <p class="eyebrow muted">${Eartha.esc(i.label)}</p>
      <div class="benefit-image-drop" data-drop="${i.key}" tabindex="0" role="button"
           aria-label="Upload replacement image"
           style="width:100%;height:140px;margin-top:10px;cursor:pointer;${preview ? `background:url('${preview}') center/cover no-repeat;` : 'background:var(--ink);'}">
        ${preview ? '' : '<p class="muted" style="font-size:11px;padding:10px;">USING THE DEFAULT — CLICK TO REPLACE</p>'}
      </div>
      <input type="file" accept="image/*" class="f-image-input" data-input="${i.key}" hidden>
      <div style="display:flex;gap:10px;margin-top:10px;">
        <button class="btn btn-sm" data-act="save-image" data-id="${i.key}" ${pending[i.key] ? '' : 'disabled'}>SAVE</button>
        ${i.image ? `<button class="btn btn-ghost btn-sm" data-act="reset-image" data-id="${i.key}">RESET TO DEFAULT</button>` : ''}
      </div>
    </div>`;
  }

  let texts = [];
  let images = [];

  async function load() {
    try {
      [texts, images] = await Promise.all([Eartha.fetchSiteTexts(), Eartha.fetchSiteImages()]);
    } catch (err) {
      textsEl.innerHTML = `<div class="empty">${Eartha.esc(err.message || 'COULD NOT LOAD SITE CONTENT.')}</div>`;
      return;
    }
    render();
  }

  function render() {
    textsEl.innerHTML = texts.map(textCard).join('');
    imagesEl.innerHTML = images.map(imageCard).join('');
  }

  textsEl.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-act="save-text"]');
    if (!btn) return;
    const key = btn.dataset.id;
    const value = document.querySelector(`[data-input="${key}"]`).value;
    try {
      await Eartha.updateSiteText(key, value);
      texts = texts.map((t) => (t.key === key ? { ...t, value } : t));
      Eartha.toast('SAVED.');
    } catch (err) {
      Eartha.toast(err.message || 'COULD NOT SAVE.');
    }
  });

  imagesEl.addEventListener('click', (e) => {
    const drop = e.target.closest('[data-drop]');
    if (drop) {
      imagesEl.querySelector(`.f-image-input[data-input="${drop.dataset.drop}"]`).click();
    }
  });

  imagesEl.addEventListener('change', async (e) => {
    const input = e.target.closest('.f-image-input');
    if (!input || !input.files[0]) return;
    const key = input.dataset.input;
    try {
      pending[key] = await Eartha.compressImage(input.files[0], 800, 0.8);
    } catch {
      Eartha.toast('COULD NOT READ THAT IMAGE.');
      return;
    }
    input.value = '';
    render();
  });

  imagesEl.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-act]');
    if (!btn) return;
    const key = btn.dataset.id;

    if (btn.dataset.act === 'save-image') {
      if (!pending[key]) return;
      try {
        const updated = await Eartha.updateSiteImage(key, pending[key]);
        images = images.map((i) => (i.key === key ? { ...i, image: updated.image } : i));
        delete pending[key];
        Eartha.toast('SAVED — LIVE ON THE SITE NOW.');
        render();
      } catch (err) {
        Eartha.toast(err.message || 'COULD NOT SAVE.');
      }
    } else if (btn.dataset.act === 'reset-image') {
      if (!confirm('Reset this image back to the original default?')) return;
      try {
        const updated = await Eartha.clearSiteImage(key);
        images = images.map((i) => (i.key === key ? { ...i, image: updated.image } : i));
        delete pending[key];
        Eartha.toast('RESET TO DEFAULT.');
        render();
      } catch (err) {
        Eartha.toast(err.message || 'COULD NOT RESET.');
      }
    }
  });

  load();
}
