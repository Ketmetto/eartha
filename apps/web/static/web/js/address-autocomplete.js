/* EARTHA — address-autocomplete.js
   Progressive enhancement: the pickup-address <input> starts as a plain
   text field. Once Google Maps loads, that *same* input gets moved to sit
   inside the map itself (not a second, separate search box) and gets the
   classic Places Autocomplete dropdown wired to it — the same live
   suggestions-while-typing the Google Maps app itself shows. Picking a
   suggestion (or geolocating, or dragging) resolves into the structured
   fields the backend stores (line1/city/country/postal_code/lat/lng).
   A no-op with no API key configured — the input just stays a plain,
   un-moved text field.

   Pin stays fixed in the center of the map; the user drags the *map*
   underneath it (same pattern Uber/Careem/DoorDash use) rather than
   dragging a small marker — a fingertip covering the exact spot you're
   trying to place a marker on is a worse experience than panning the map
   under an always-visible, always-centered pin. Every drag reverse-geocodes
   the new center, so the text input always names wherever the pin ends up
   rather than going stale next to it.

   "Use my current location" is a third entry point into the same pin,
   reverse-geocoding the browser's coordinates into the same field shape.

   The map (and the input's move into it) happens as soon as it's actually
   visible — it may start out behind a hidden tab/toggle — a ResizeObserver
   on mapEl catches that transition instead of requiring callers to know
   about map internals.
*/
(function () {
  // Beirut center — just an initial place for the map/pin to sit before
  // the user has searched, dragged, or geolocated anywhere specific.
  const DEFAULT_CENTER = { lat: 33.8938, lng: 35.5018 };
  const DEFAULT_ZOOM = 13;
  const PIN_ZOOM = 17;
  // We only ever deliver within Lebanon, so keep the map itself from
  // panning out to the rest of the world.
  const LEBANON_BOUNDS = { north: 34.75, south: 33.0, west: 35.05, east: 36.65 };

  let loaderPromise = null;

  function loadGoogleMaps(apiKey) {
    if (!loaderPromise) {
      loaderPromise = new Promise((resolve, reject) => {
        if (window.google && window.google.maps && window.google.maps.places) {
          resolve();
          return;
        }
        window.__earthaMapsReady = resolve;
        const script = document.createElement('script');
        script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&libraries=places&loading=async&callback=__earthaMapsReady`;
        script.async = true;
        script.onerror = () => reject(new Error('Failed to load Google Maps'));
        document.head.appendChild(script);
      });
    }
    return loaderPromise;
  }

  function parseAddressComponents(components) {
    const get = (type) => (components.find((c) => c.types.includes(type)) || {}).long_name || '';
    const line1 = [get('street_number'), get('route')].filter(Boolean).join(' ');
    return {
      line1,
      city: get('locality') || get('postal_town') || get('sublocality') || '',
      country: get('country'),
      postal_code: get('postal_code'),
    };
  }

  // Runs cb every time el transitions from not-laid-out to laid-out —
  // covers "visible immediately", "starts behind a hidden tab/toggle,
  // shown later", and "hidden again and later re-shown" (switching tabs,
  // or toggling map/manual mode), without the caller having to coordinate
  // with map internals.
  function onBecomingVisible(el, cb) {
    let wasVisible = el.getClientRects().length > 0;
    if (wasVisible) cb();
    const observer = new ResizeObserver(() => {
      const isVisible = el.getClientRects().length > 0;
      if (isVisible && !wasVisible) cb();
      wasVisible = isVisible;
    });
    observer.observe(el);
  }

  // apiKey: blank means "not configured", no-ops below. mapEl: map <div>,
  // pass null to skip it entirely (input then keeps its own Autocomplete
  // dropdown but never moves). onSelect(parts): called with
  // {line1, city, country, postal_code, latitude, longitude} whenever the
  // address or pin changes. locateBtn: optional "use my current
  // location" button, hidden until Maps has actually loaded.
  window.EarthaAddressAutocomplete = async function (input, apiKey, mapEl, onSelect, locateBtn) {
    if (!apiKey || !input) {
      if (mapEl) mapEl.hidden = true;
      return;
    }
    try {
      await loadGoogleMaps(apiKey);
    } catch {
      if (mapEl) mapEl.hidden = true;
      return; // stays a plain text input
    }

    let map = null;
    let textParts = {};
    let lastCenter = DEFAULT_CENTER;

    // toFixed(6): the backend's DecimalField(decimal_places=6) rejects
    // extra precision as a 400 rather than rounding it.
    function emit(location) {
      onSelect({
        ...textParts,
        latitude: Number(location.lat().toFixed(6)),
        longitude: Number(location.lng().toFixed(6)),
      });
    }

    // Reverse-geocodes so the text input and structured fields end up
    // holding a real address, not just a bare coordinate — used both for
    // "use my current location" and for whenever the user pans the pin
    // to a new spot, so the address text never goes stale next to it.
    function reverseGeocodeAndEmit(location, done) {
      new google.maps.Geocoder().geocode({ location }, (results, status) => {
        if (status === 'OK' && results[0]) {
          input.value = results[0].formatted_address;
          textParts = parseAddressComponents(results[0].address_components);
        } else {
          textParts = {};
        }
        emit(location);
        if (done) done();
      });
    }

    function recenter(location, zoom) {
      lastCenter = location;
      if (!map) return;
      map.setCenter(location);
      if (zoom) map.setZoom(zoom);
    }

    // No `types` filter — mixes in businesses/landmarks alongside plain
    // addresses (a "geocode"-only filter hides store names, which is the
    // kind of pickup-point reference people actually search for here).
    // componentRestrictions is a hard filter to Lebanon regardless of origin.
    function wireAutocomplete() {
      const autocomplete = new google.maps.places.Autocomplete(input, {
        fields: ['address_components', 'formatted_address', 'name', 'geometry'],
        componentRestrictions: { country: 'lb' },
      });
      autocomplete.addListener('place_changed', () => {
        const place = autocomplete.getPlace();
        if (!place.geometry) return; // user hit Enter without picking a suggestion
        input.value = place.formatted_address || place.name || input.value;
        textParts = place.address_components ? parseAddressComponents(place.address_components) : {};
        recenter(place.geometry.location, PIN_ZOOM);
        emit(place.geometry.location);
      });
    }

    function initMap() {
      mapEl.style.position = 'relative';

      const canvas = document.createElement('div');
      canvas.style.cssText = 'position:absolute;inset:0;';
      mapEl.appendChild(canvas);

      const pin = document.createElement('div');
      pin.className = 'map-pin-fixed';
      pin.setAttribute('aria-hidden', 'true');
      mapEl.appendChild(pin);

      // Move the real input into the map as its search box, rather than
      // building a second one — one field, one source of truth.
      const searchWrap = document.createElement('div');
      searchWrap.className = 'map-search-box';
      input.classList.add('map-search-input');
      input.placeholder = 'SEARCH AN ADDRESS…';
      searchWrap.appendChild(input);
      mapEl.appendChild(searchWrap);
      wireAutocomplete();

      map = new google.maps.Map(canvas, {
        center: lastCenter,
        zoom: DEFAULT_ZOOM,
        disableDefaultUI: true,
        zoomControl: true,
        // strictBounds: false — a hard clamp forces Maps to constrain the
        // viewport in real time on every drag frame, which is what made
        // dragging feel laggy. This still stops zooming out past Lebanon
        // and springs back if you let go entirely outside it, without
        // fighting the drag itself.
        restriction: { latLngBounds: LEBANON_BOUNDS, strictBounds: false },
      });
      map.addListener('dragend', () => {
        lastCenter = map.getCenter();
        reverseGeocodeAndEmit(lastCenter);
      });
    }

    if (mapEl) {
      onBecomingVisible(mapEl, () => {
        if (!map) {
          initMap();
        } else {
          // was already built once, then hidden (e.g. a tab switch) —
          // Maps mis-sizes tiles rendered while display:none, so nudge it.
          google.maps.event.trigger(map, 'resize');
          map.setCenter(lastCenter);
        }
      });
    } else {
      wireAutocomplete();
    }

    if (!locateBtn) return;
    locateBtn.hidden = false;

    locateBtn.addEventListener('click', () => {
      if (!navigator.geolocation) {
        Eartha.toast("YOUR BROWSER DOESN'T SUPPORT LOCATION SHARING — ENTER YOUR ADDRESS ABOVE INSTEAD.");
        return;
      }
      const originalText = locateBtn.textContent;
      locateBtn.disabled = true;
      locateBtn.textContent = 'LOCATING…';
      const reset = () => { locateBtn.disabled = false; locateBtn.textContent = originalText; };

      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const location = new google.maps.LatLng(pos.coords.latitude, pos.coords.longitude);
          recenter(location, PIN_ZOOM);
          reverseGeocodeAndEmit(location, reset);
        },
        (err) => {
          reset();
          Eartha.toast(
            err.code === err.PERMISSION_DENIED
              ? 'LOCATION ACCESS WAS DENIED — ENTER YOUR ADDRESS ABOVE INSTEAD.'
              : 'COULD NOT GET YOUR LOCATION — ENTER YOUR ADDRESS ABOVE INSTEAD.'
          );
        },
        { enableHighAccuracy: true, timeout: 10000 }
      );
    });
  };
})();
