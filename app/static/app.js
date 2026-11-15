const $ = id => document.getElementById(id);
let places = [];
let destinations = [];
let chosenEvent = null;
let textDestination = null;
let stops = [];
let tripRevision = 0;
let interpretRevision = 0;

function clearTripPreview() {
  tripRevision += 1;
  $('trip-result').textContent = 'Review your itinerary to update the preview and travel links.';
  $('trip-result').classList.remove('error');
  $('route-details').replaceChildren();
  $('route-details').hidden = true;
  $('transit-legs').replaceChildren();
  $('transit-legs').hidden = true;
}

fetch('/api/places').then(response => response.json()).then(data => {
  places = data;
  for (const place of places) {
    const option = document.createElement('option');
    option.value = place.name;
    $('place-list').append(option);
  }
  $('place-count').textContent = `${places.length} searchable locations from the UMass January 2026 map index and calendar aliases.`;
  $('place-count').removeAttribute('aria-busy');
}).catch(() => { $('place-count').textContent = 'Could not load campus place suggestions. You can still type a location.'; $('place-count').removeAttribute('aria-busy'); });

const formatTime = iso => new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/New_York', weekday: 'short', month: 'short', day: 'numeric',
  hour: 'numeric', minute: '2-digit', timeZoneName: 'short'
}).format(new Date(iso));

function renderStops() {
  const list = $('stops');
  list.replaceChildren();
  if (!stops.length) {
    const empty = document.createElement('li'); empty.className = 'empty-stops';
    empty.textContent = 'No extra stops yet. Add one above to build a longer itinerary.';
    list.append(empty);
    return;
  }
  stops.forEach((name, index) => {
    const row = document.createElement('li'); row.className = 'stop-row glass-card';
    const label = document.createElement('span'); label.textContent = `${index + 1}. ${name}`;
    const actions = document.createElement('span'); actions.className = 'stop-actions';
    for (const [word, offset] of [['Up', -1], ['Down', 1]]) {
      const button = document.createElement('button'); button.type = 'button';
      button.textContent = word; button.disabled = index + offset < 0 || index + offset >= stops.length;
      button.setAttribute('aria-label', `Move ${name} ${word.toLowerCase()}`);
      button.addEventListener('click', () => {
        [stops[index], stops[index + offset]] = [stops[index + offset], stops[index]];
        renderStops(); clearTripPreview(); $('stop-status').textContent = `${name} moved ${word.toLowerCase()}.`;
      });
      actions.append(button);
    }
    const remove = document.createElement('button'); remove.type = 'button';
    remove.textContent = 'Remove'; remove.setAttribute('aria-label', `Remove ${name}`);
    remove.addEventListener('click', () => {
      stops.splice(index, 1); renderStops(); clearTripPreview(); $('stop-status').textContent = `${name} removed.`;
      $('add-stop').focus();
    });
    actions.append(remove); row.append(label, actions); list.append(row);
  });
  window.CampusEffects?.initGlassCards();
}

function addStop() {
  const name = $('stop-input').value.trim();
  if (!name) { $('stop-status').textContent = 'Enter a stop before adding it.'; return; }
  if (stops.length >= 12) { $('stop-status').textContent = 'Use up to 12 stops in one itinerary.'; return; }
  stops.push(name); $('stop-input').value = ''; renderStops(); clearTripPreview();
  $('stop-status').textContent = `${name} added as stop ${stops.length}.`;
  $('stop-input').focus();
}
$('add-stop').addEventListener('click', addStop);
$('stop-input').addEventListener('keydown', event => {
  if (event.key === 'Enter') { event.preventDefault(); addStop(); }
});

function selectEvent(group) {
  chosenEvent = group;
  $('destination').value = group.place_name || group.location || '';
  $('calendar-status').textContent = `Selected ${group.next_summary} on ${formatTime(group.next_start)}. Check or edit the destination.`;
  $('destination').focus();
  renderEvents();
  interpretRequest();
  clearTripPreview();
}

function mentionedPlace(text) {
  const lower = text.toLowerCase();
  const candidates = places.flatMap(place => [place.name, ...place.aliases].map(alias => ({place, alias})));
  candidates.sort((a, b) => b.alias.length - a.alias.length);
  return candidates.find(item => lower.includes(item.alias.toLowerCase()))?.place || null;
}

function interpretRequest() {
  const value = $('request').value.trim();
  const parts = value.match(/\bfrom\s+(.+?)\s+to\s+(.+)/i);
  const originPlace = parts && mentionedPlace(parts[1]);
  textDestination = parts && !/\bmy next class\b/i.test(parts[2]) ? mentionedPlace(parts[2]) : null;
  if (originPlace && !$('origin').value.trim()) $('origin').value = originPlace.name;
  if (/\bwithout stairs\b|\bstep.free\b/i.test(value)) $('step-free').checked = true;
  const conflict = $('request-conflict');
  if (textDestination && chosenEvent && chosenEvent.place_id !== textDestination.id) {
    $('conflict-message').textContent = `Your text names ${textDestination.name}, while the selected class is at ${chosenEvent.place_name || chosenEvent.location}. Which destination should be used?`;
    conflict.hidden = false;
  } else {
    conflict.hidden = true;
    if (textDestination) $('destination').value = textDestination.name;
    else if (/\bmy next class\b/i.test(value) && chosenEvent) $('destination').value = chosenEvent.place_name || chosenEvent.location;
  }
}

$('request').addEventListener('change', interpretRequest);
$('request').addEventListener('input', () => { interpretRevision += 1; });
$('use-local-ai').addEventListener('change', () => {
  interpretRevision += 1;
  $('interpret-status').textContent = $('use-local-ai').checked ?
    'Local Ollama is on. Select Interpret text to request suggestions.' :
    'Basic text matching is ready. Ollama is off.';
});
$('interpret-request').addEventListener('click', async () => {
  const text = $('request').value.trim();
  if (!text) { $('interpret-status').textContent = 'Enter a trip request first.'; return; }
  if (!$('use-local-ai').checked) {
    interpretRequest();
    $('interpret-status').textContent = 'Basic text matching applied. Check the place fields and preferences.';
    return;
  }
  const revision = ++interpretRevision;
  $('interpret-request').disabled = true;
  $('interpret-status').textContent = 'Asking local Ollama for place and preference suggestions…';
  try {
    const response = await fetch('/api/interpret', {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text, use_local_ai: true})});
    if (!response.ok) throw new Error('Local interpretation unavailable.');
    const data = await response.json();
    if (revision !== interpretRevision) return;
    if (data.status !== 'ai' || !data.suggestion) throw new Error('Local interpretation unavailable.');
    const suggestion = data.suggestion;
    const origin = places.find(place => place.id === suggestion.origin_id);
    const destination = places.find(place => place.id === suggestion.destination_id);
    if (origin && !$('origin').value.trim()) $('origin').value = origin.name;
    if (suggestion.step_free) $('step-free').checked = true;
    if (suggestion.avoid_steep) $('grades').checked = true;
    textDestination = destination || null;
    if (destination && chosenEvent && chosenEvent.place_id !== destination.id) {
      $('conflict-message').textContent = `Local text interpretation suggests ${destination.name}, while the selected class is at ${chosenEvent.place_name || chosenEvent.location}. Which destination should be used?`;
      $('request-conflict').hidden = false;
    } else {
      $('request-conflict').hidden = true;
      if (destination) $('destination').value = destination.name;
      else if (suggestion.next_class && chosenEvent) $('destination').value = chosenEvent.place_name || chosenEvent.location;
    }
    clearTripPreview();
    $('interpret-status').textContent = suggestion.next_class && !chosenEvent ?
      'Local suggestions applied; import or select a class for “my next class.” Check the fields.' :
      'Local suggestions applied. Check the place fields and preferences before reviewing the itinerary.';
  } catch (error) {
    if (revision !== interpretRevision) return;
    interpretRequest();
    $('interpret-status').textContent = 'Ollama was unavailable or returned an invalid suggestion. Basic text matching was applied; check the fields.';
  } finally { $('interpret-request').disabled = false; }
});
$('use-text').addEventListener('click', () => {
  $('destination').value = textDestination.name;
  chosenEvent = null; $('request-conflict').hidden = true; renderEvents(); clearTripPreview(); $('destination').focus();
});
$('use-class').addEventListener('click', () => {
  $('destination').value = chosenEvent.place_name || chosenEvent.location;
  $('request-conflict').hidden = true; textDestination = null; clearTripPreview(); $('destination').focus();
});

function renderEvents() {
  const container = $('events'); container.replaceChildren();
  if (!destinations.length) {
    const empty = document.createElement('p'); empty.className = 'empty-state';
    empty.textContent = 'No upcoming class destinations in the next 30 days. Try another .ics file or enter a destination above.';
    container.append(empty); return;
  }
  for (const group of destinations) {
    const article = document.createElement('article'); article.className = 'event glass-card';
    const head = document.createElement('div'); head.className = 'event-head';
    const content = document.createElement('div');
    const title = document.createElement('h3');
    title.textContent = group.place_name || group.location || 'Location not supplied';
    const detail = document.createElement('p');
    detail.textContent = `Next: ${group.next_summary} · ${formatTime(group.next_start)}`;
    const classes = document.createElement('p');
    classes.textContent = group.summaries.length > 1 ? `Classes: ${group.summaries.join(', ')}` : '';
    const tag = document.createElement('span'); tag.className = group.place_name ? 'tag ok' : 'tag';
    tag.textContent = group.place_name ? `${group.occurrence_count} meeting${group.occurrence_count === 1 ? '' : 's'} grouped` :
      group.missing_location ? 'No location supplied' : 'Building not matched';
    content.append(title, detail);
    if (group.summaries.length > 1) content.append(classes);
    content.append(tag);
    const button = document.createElement('button'); button.type = 'button';
    button.textContent = chosenEvent?.id === group.id ? 'Selected' : 'Use destination';
    button.setAttribute('aria-label', `Use ${title.textContent} as destination`);
    button.addEventListener('click', () => selectEvent(group));
    head.append(content, button); article.append(head); container.append(article);
  }
  window.CampusEffects?.initGlassCards();
}

$('import-calendar').addEventListener('click', async () => {
  const file = $('calendar-file').files[0];
  if (!file) { $('calendar-status').textContent = 'Choose an .ics file first.'; return; }
  if (!file.name.toLowerCase().endsWith('.ics')) { $('calendar-status').textContent = 'Choose a file ending in .ics.'; return; }
  $('calendar-status').textContent = 'Reading calendar…';
  $('calendar-status').setAttribute('aria-busy', 'true');
  $('import-calendar').disabled = true;
  try {
    const response = await fetch('/api/calendar/import', { method: 'POST', headers: {'Content-Type': 'text/calendar'}, body: file });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Calendar import failed.');
    destinations = data.destinations; chosenEvent = null;
    const next = destinations.find(group => group.event_id === data.next_event_id);
    if (next) {
      selectEvent(next);
      $('calendar-status').textContent = `Imported ${data.events.length} upcoming meetings, grouped into ${destinations.length} destination ${destinations.length === 1 ? 'card' : 'cards'}. Next matched class: ${next.next_summary}, ${formatTime(next.next_start)}.`;
    } else {
      $('calendar-status').textContent = `Imported ${data.events.length} upcoming meetings, grouped into ${destinations.length} cards. No upcoming class has a matched campus location; select and correct a destination if needed.`;
      renderEvents();
    }
  } catch (error) { $('calendar-status').textContent = error.message; }
  finally { $('import-calendar').disabled = false; $('calendar-status').removeAttribute('aria-busy'); }
});

$('travel-mode').addEventListener('change', () => {
  $('transit-guidance').hidden = $('travel-mode').value === 'walk';
  clearTripPreview();
});

for (const id of ['origin', 'destination', 'request']) {
  $(id).addEventListener('input', clearTripPreview);
}
for (const id of ['step-free', 'grades']) {
  $(id).addEventListener('change', clearTripPreview);
}

function placeQuery(name) {
  return places.some(place => place.name === name) ? `${name}, UMass Amherst, MA` : name;
}

function showTransitLegs(itinerary) {
  const panel = $('transit-legs'); panel.replaceChildren();
  const heading = document.createElement('h3'); heading.textContent = 'Plan each bus leg';
  const intro = document.createElement('p');
  intro.textContent = 'These links open Google Maps with each leg filled in. Check its place matches, current service, and walking portions. Opening a link shares that leg’s place names with Google.';
  const list = document.createElement('ol');
  for (let index = 0; index < itinerary.length - 1; index++) {
    const from = itinerary[index], to = itinerary[index + 1];
    const url = new URL('https://www.google.com/maps/dir/');
    url.searchParams.set('api', '1');
    url.searchParams.set('origin', placeQuery(from));
    url.searchParams.set('destination', placeQuery(to));
    url.searchParams.set('travelmode', 'transit');
    const row = document.createElement('li');
    const label = document.createElement('span'); label.textContent = `${from} → ${to}`;
    const link = document.createElement('a'); link.href = url.toString();
    link.target = '_blank'; link.rel = 'noopener noreferrer';
    link.textContent = 'Open transit directions';
    link.setAttribute('aria-label', `Open transit directions for leg ${index + 1}: ${from} to ${to}`);
    row.append(label, link); list.append(row);
  }
  panel.append(heading, intro, list); panel.hidden = false;
}

function renderRouteDetails(legs) {
  const panel = $('route-details'); panel.replaceChildren();
  for (const [index, leg] of legs.entries()) {
    const card = document.createElement('article'); card.className = 'route-leg glass-card';
    const heading = document.createElement('h3'); heading.textContent = `Leg ${index + 1}: ${leg.from} → ${leg.to}`;
    const status = document.createElement('p'); status.className = 'route-leg-status';
    if (leg.status === 'verified') {
      status.textContent = `Reviewed walking path · ${Math.round(leg.distance_m)} m of measured segments`;
      const intro = document.createElement('p'); intro.className = 'route-disclaimer';
      intro.textContent = 'Schematic segment sequence. Follow current signs and check for closures; this is not live navigation.';
      card.append(heading, status, intro);
      const list = document.createElement('ol'); list.className = 'route-segments';
      for (const segment of leg.segments) {
        const row = document.createElement('li');
        const direction = document.createElement('strong');
        direction.textContent = `${segment.from} → ${segment.to}`;
        const facts = document.createElement('span');
        facts.textContent = `${segment.mode} · ${Math.round(segment.distance_m)} m · grade ${segment.grade_percent}% · ${segment.step_free_status === 'verified' ? 'step-free field review' : 'stairs or barrier present'}`;
        row.append(direction, facts);
        for (const source of segment.evidence) {
          const link = document.createElement('a'); link.href = source.url; link.target = '_blank';
          link.rel = 'noopener noreferrer'; link.textContent = `${source.title} · source ${source.source_date} · reviewed ${source.review_date}`;
          row.append(link);
        }
        list.append(row);
      }
      card.append(list);
    } else {
      status.textContent = leg.status === 'same_place' ? leg.message :
        leg.status === 'external_transit_required' ? 'Transit planning required outside this app.' :
          'No verified route available for this leg.';
      card.append(heading, status);
      if (leg.message && leg.status === 'unavailable') {
        const explanation = document.createElement('p'); explanation.className = 'route-disclaimer';
        explanation.textContent = leg.message; card.append(explanation);
      }
    }
    panel.append(card);
  }
  panel.hidden = false;
  window.CampusEffects?.initGlassCards();
}

$('review-trip').addEventListener('click', async () => {
  const origin = $('origin').value.trim(); const destination = $('destination').value.trim();
  const result = $('trip-result'); result.classList.remove('error');
  if (!$('request-conflict').hidden) {
    result.textContent = 'Choose which destination to use above.';
    result.classList.add('error'); return;
  }
  if (!origin || !destination) {
    result.textContent = 'Enter both your current location and a final destination.';
    result.classList.add('error'); return;
  }
  const itinerary = [origin, ...stops, destination];
  const revision = ++tripRevision;
  const mode = $('travel-mode').selectedOptions[0].textContent.toLowerCase();
  result.textContent = `Checking ${itinerary.length - 1} ${itinerary.length === 2 ? 'leg' : 'legs'}…`;
  $('route-details').replaceChildren(); $('route-details').hidden = true;
  if ($('travel-mode').value === 'walk') { $('transit-legs').replaceChildren(); $('transit-legs').hidden = true; }
  else showTransitLegs(itinerary);
  $('review-trip').disabled = true;
  try {
    const response = await fetch('/api/route', {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({itinerary, mode: $('travel-mode').value,
        step_free: $('step-free').checked, avoid_steep: $('grades').checked})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Route review failed.');
    if (revision !== tripRevision) return;
    const unavailable = data.legs.filter(leg => leg.status === 'unavailable').length;
    const busNote = $('travel-mode').value === 'walk' ? '' : ' Use the external links below to plan transit; bus service and walking connections are not computed here.';
    result.textContent = `Itinerary (${mode}): ${itinerary.join(' → ')}. ${data.status === 'verified' ?
      'Every leg has a reviewed walking path or starts and ends at the same place.' :
      unavailable ? `No verified route available for ${unavailable} ${unavailable === 1 ? 'leg' : 'legs'}.` :
        'No complete route is calculated in this app.'}${busNote}`;
    renderRouteDetails(data.legs);
  } catch (error) {
    if (revision !== tripRevision) return;
    result.textContent = `Could not check route data: ${error.message}`;
    result.classList.add('error');
  } finally { $('review-trip').disabled = false; }
});

renderStops();
