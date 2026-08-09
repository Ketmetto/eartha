/* EARTHA — address-autocomplete.js
   Progressive enhancement: binds Google Places Autocomplete to a plain
   text <input> so picking a suggestion auto-fills the structured fields
   the backend actually stores (line1/city/country/postal_code/lat/lng)
   instead of one unstructured line, then drops a draggable pin on a small
   map so the user can nudge it onto their actual entrance — Lebanon
   addressing is often informal enough that the geocoded point alone isn't
   reliably exact. Entirely a no-op with no API key configured — the input
   just stays a plain text field.

   Uses the classic google.maps.places.Autocomplete widget (bound directly
   to an existing <input>) rather than the newer PlaceAutocompleteElement
   web component — it drops onto our existing styled <input> with no
   markup changes and no Shadow DOM styling to fight. Google still fully
   supports it; only new *features* are Element-only.

   A "use my current location" button is a second, optional entry point
   into the same pin — useful standing at the actual pickup spot, where
   typing/searching an address is slower and less exact than just sharing
   position. It reverse-geocodes the browser's coordinates back into the
   same structured fields Places Autocomplete produces, so either path
   ends up in the same shape.
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

  // input: the visible pickup-address <input>.
  // apiKey: GOOGLE_MAPS_API_KEY from the server (blank means "not
  // configured" — no-ops below, input stays plain text).
  // mapEl: a <div> to render the pin-drop confirmation map into once a
  // suggestion is picked (stays hidden until then). Pass null to skip the
  // map entirely and just get the autocomplete + structured fields.
  // onSelect(parts): called with {line1, city, country, postal_code,
  // latitude, longitude} — once when a suggestion is picked, and again
  // (same address fields, updated coordinates) every time the pin is
  // dragged to a new spot, or "use my current location" resolves.
  // locateBtn: optional "use my current location" button — stays hidden
  // (its markup default) until Maps has actually loaded.
  window.EarthaAddressAutocomplete = async function (input, apiKey, mapEl, onSelect, locateBtn) {
    if (!apiKey || !input) return;
    try {
      await loadGoogleMaps(apiKey);
    } catch {
      return; // stays a plain text input
    }
    // Eartha operates in Lebanon, where addressing is often informal
    // (buildings identified by name/landmark rather than street number) —
    // types:['address'] only matches formal street addresses and misses
    // most of those, so 'geocode' (all geocodable results, still excludes
    // pure businesses) works far better here. componentRestrictions biases
    // toward Lebanon regardless of where the request is actually made from.
    const autocomplete = new google.maps.places.Autocomplete(input, {
      fields: ['address_components', 'formatted_address', 'geometry'],
      types: ['geocode'],
      componentRestrictions: { country: 'lb' },
    });

    let map = null;
    let marker = null;
    let textParts = {};

    // Google's lat()/lng() carry far more floating-point precision than
    // the backend's DecimalField(decimal_places=6) allows (it rejects
    // excess precision as a 400, it doesn't silently round) — 6 places is
    // already ~11cm, plenty for a pickup pin.
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
