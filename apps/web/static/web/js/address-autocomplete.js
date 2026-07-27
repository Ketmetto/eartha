/* EARTHA — address-autocomplete.js
   Progressive enhancement: binds Google Places Autocomplete to a plain
   text <input> so picking a suggestion auto-fills the structured fields
   the backend actually stores (line1/city/country/postal_code/lat/lng)
   instead of one unstructured line, then drops a draggable pin on a small
   map so the user can nudge it onto their actual entrance — Lebanon
   addressing is often informal enough that the geocoded point alone isn't
   reliably exact. Entirely a no-op with no API key configured — the input
   just stays a plain text field, same as before this existed.

   Uses the classic google.maps.places.Autocomplete widget (bound directly
   to an existing <input>) rather than the newer PlaceAutocompleteElement
   web component — it drops onto our existing styled <input> with no
   markup changes and no Shadow DOM styling to fight. Google still fully
   supports it; only new *features* are Element-only.
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
  // dragged to a new spot.
  window.EarthaAddressAutocomplete = async function (input, apiKey, mapEl, onSelect) {
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

    autocomplete.addListener('place_changed', () => {
      const place = autocomplete.getPlace();
      if (!place.geometry) return; // user hit Enter without picking a suggestion
      input.value = place.formatted_address || input.value;
      textParts = place.address_components ? parseAddressComponents(place.address_components) : {};
      const location = place.geometry.location;

      if (mapEl) {
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
      emit(location);
    });
  };
})();
