const $ = id => document.getElementById(id);
let places = [];
let events = [];
let chosenEvent = null;
let textDestination = null;

fetch('/api/places').then(r => r.json()).then(data => {
  places = data;
  for (const place of places) {
    const option = document.createElement('option');
    option.value = place.name;
    $('place-list').append(option);
  }
}).catch(() => { $('calendar-status').textContent = 'Could not load campus place suggestions.'; });

const formatTime = iso => new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/New_York', weekday: 'short', month: 'short', day: 'numeric',
  hour: 'numeric', minute: '2-digit', timeZoneName: 'short'
}).format(new Date(iso));

function selectEvent(event) {
  chosenEvent = event;
  $('destination').value = event.place_name || event.location || '';
  $('calendar-status').textContent = `Selected ${event.summary} on ${formatTime(event.start)}. Check or edit the destination.`;
  $('destination').focus();
  renderEvents();
  interpretRequest();
}

function mentionedPlace(text) {
  const lower = text.toLowerCase();
  for (const place of places) {
    if ([place.name, ...place.aliases].some(alias => lower.includes(alias.toLowerCase()))) return place;
  }
  return null;
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
$('use-text').addEventListener('click', () => {
  $('destination').value = textDestination.name;
  chosenEvent = null;
  $('request-conflict').hidden = true;
  renderEvents();
  $('destination').focus();
});
$('use-class').addEventListener('click', () => {
  $('destination').value = chosenEvent.place_name || chosenEvent.location;
  $('request-conflict').hidden = true;
  textDestination = null;
  $('destination').focus();
});

function renderEvents() {
  const container = $('events');
  container.replaceChildren();
  if (!events.length) { container.textContent = 'No upcoming events in the next 30 days.'; return; }
  for (const event of events) {
    const article = document.createElement('article'); article.className = 'event';
    const head = document.createElement('div'); head.className = 'event-head';
    const content = document.createElement('div');
    const title = document.createElement('h3'); title.textContent = event.summary;
    const detail = document.createElement('p');
    detail.textContent = `${formatTime(event.start)} · ${event.location || 'No location supplied'}`;
    const tag = document.createElement('span'); tag.className = event.place_name ? 'tag ok' : 'tag';
    tag.textContent = event.place_name ? `Matched: ${event.place_name}` : event.missing_location ? 'No destination' : 'Building not matched';
    content.append(title, detail, tag);
    const button = document.createElement('button'); button.type = 'button';
    button.textContent = chosenEvent?.id === event.id ? 'Selected' : 'Use as destination';
    button.setAttribute('aria-label', `Use ${event.summary} at ${formatTime(event.start)} as destination`);
    button.addEventListener('click', () => selectEvent(event));
    head.append(content, button); article.append(head); container.append(article);
  }
}

$('import-calendar').addEventListener('click', async () => {
  const file = $('calendar-file').files[0];
  if (!file) { $('calendar-status').textContent = 'Choose an .ics file first.'; return; }
  if (!file.name.toLowerCase().endsWith('.ics')) { $('calendar-status').textContent = 'Choose a file ending in .ics.'; return; }
  $('calendar-status').textContent = 'Reading calendar…';
  try {
    const response = await fetch('/api/calendar/import', { method: 'POST', headers: {'Content-Type': 'text/calendar'}, body: file });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Calendar import failed.');
    events = data.events; chosenEvent = null;
    const next = events.find(event => event.id === data.next_event_id);
    if (next) {
      selectEvent(next);
      $('calendar-status').textContent = `Imported ${events.length} upcoming events. Next matched class: ${next.summary}, ${formatTime(next.start)}. ${data.duplicates_removed} duplicate occurrence(s) removed.`;
    } else {
      $('calendar-status').textContent = `Imported ${events.length} upcoming events. No upcoming event has a matched campus location. Select an event and correct its destination if needed.`;
      renderEvents();
    }
  } catch (error) { $('calendar-status').textContent = error.message; }
});

$('review-trip').addEventListener('click', () => {
  const origin = $('origin').value.trim(); const destination = $('destination').value.trim();
  const result = $('trip-result'); result.classList.remove('error');
  if (!$('request-conflict').hidden) {
    result.textContent = 'Choose which destination to use above.';
    result.classList.add('error'); return;
  }
  if (/\bmy next class\b/i.test($('request').value) && !chosenEvent && !destination) {
    result.textContent = 'Import a schedule with a matched class or enter a destination manually.';
    result.classList.add('error'); return;
  }
  if (!origin || !destination) {
    result.textContent = 'Enter both your current location and a destination.';
    result.classList.add('error'); return;
  }
  result.textContent = `Trip preview: ${origin} → ${destination}. No verified route available yet. Path accessibility${$('step-free').checked ? ', step-free access' : ''}${$('grades').checked ? ', and grades' : ''} cannot be confirmed until reviewed campus path data is added.`;
});
