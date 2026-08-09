/* EARTHA — address-autocomplete.js
   Progressive enhancement: binds Google Places Autocomplete to a plain
   text <input>, auto-filling the structured fields the backend stores
   (line1/city/country/postal_code/lat/lng), then drops a draggable pin
   so the user can nudge it onto their actual entrance. A no-op with no
   API key configured — the input just stays plain text.

   Uses the classic Autocomplete widget, not PlaceAutocompleteElement —
   it binds to our existing styled <input> with no Shadow DOM to fight.

   "Use my current location" is a second entry point into the same pin,
   reverse-geocoding the browser's coordinates into the same field shape.
*/
(function () {
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

  // apiKey: blank means "not configured", no-ops below. mapEl: pin-drop
  // map <div>, pass null to skip it. onSelect(parts): called with
  // {line1, city, country, postal_code, latitude, longitude} whenever the
  // address or pin changes. locateBtn: optional "use my current
  // location" button, hidden until Maps has actually loaded.
  window.EarthaAddressAutocomplete = async function (input, apiKey, mapEl, onSelect, locateBtn) {
    if (!apiKey || !input) return;
    try {
      await loadGoogleMaps(apiKey);
    } catch {
      return; // stays a plain text input
    }
    // 'geocode' (not 'address') since Lebanese addressing is often
    // informal — 'address' only matches formal street addresses.
    // componentRestrictions biases toward Lebanon regardless of origin.
    const autocomplete = new google.maps.places.Autocomplete(input, {
      fields: ['address_components', 'formatted_address', 'geometry'],
      types: ['geocode'],
      componentRestrictions: { country: 'lb' },
    });

    let map = null;
    let marker = null;
    let textParts = {};

    // toFixed(6): the backend's DecimalField(decimal_places=6) rejects
    // extra precision as a 400 rather than rounding it.
    function emit(location) {
      onSelect({
        ...textParts,
        latitude: Number(location.lat().toFixed(6)),
        longitude: Number(location.lng().toFixed(6)),
      });
    }

    function showPin(location) {
      if (!mapEl) return;
      mapEl.hidden = false;
      if (!map) {
        map = new google.maps.Map(mapEl, { center: location, zoom: 17, disableDefaultUI: true, zoomControl: true });
        marker = new google.maps.Marker({ position: location, map, draggable: true });
        marker.addListener('dragend', () => emit(marker.getPosition()));
      } else {
        map.setCenter(location);
        marker.setPosition(location);
      }
    }

    autocomplete.addListener('place_changed', () => {
      const place = autocomplete.getPlace();
      if (!place.geometry) return; // user hit Enter without picking a suggestion
      input.value = place.formatted_address || input.value;
      textParts = place.address_components ? parseAddressComponents(place.address_components) : {};
      showPin(place.geometry.location);
      emit(place.geometry.location);
    });

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
          showPin(location);
          // Reverse geocode so the text input and structured fields end
          // up holding a real address, not just a bare coordinate — the
          // pin is still dropped and usable even if this part fails.
          new google.maps.Geocoder().geocode({ location }, (results, status) => {
            if (status === 'OK' && results[0]) {
              input.value = results[0].formatted_address;
              textParts = parseAddressComponents(results[0].address_components);
            } else {
              textParts = {};
            }
            emit(location);
            reset();
          });
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
