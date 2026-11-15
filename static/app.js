'use strict';
const $ = id => document.getElementById(id);
let tracks = [], selected = new Set(), page = 0, demo = false, busy = false, loaded = false;
const pageSize = 50;
const fields = ['keyword', 'artist', 'album', 'sort'];
const normalize = value => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const matches = () => {
  const [keyword, artist, album] = fields.slice(0, 3).map(id => normalize($(id).value.trim()));
  const result = tracks.filter(t => normalize([t.name, ...t.artists, t.album].join(' ')).includes(keyword)
    && normalize(t.artists.join(' ')).includes(artist) && normalize(t.album).includes(album));
  return result.sort((a, b) => {
    switch ($('sort').value) {
      case 'name': return a.name.localeCompare(b.name);
      case 'artist': return a.artists.join(', ').localeCompare(b.artists.join(', ')) || a.name.localeCompare(b.name);
      case 'album': return a.album.localeCompare(b.album) || a.name.localeCompare(b.name);
      default: return b.added_at.localeCompare(a.added_at);
    }
  });
};
function status(message, error = false) {
  $('status').textContent = message;
  $('status').classList.toggle('error', error);
}
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
function render() {
  const filtered = matches();
  page = Math.max(0, Math.min(page, Math.ceil(filtered.length / pageSize) - 1));
  $('total').textContent = tracks.length.toLocaleString();
  $('match-count').textContent = `${filtered.length.toLocaleString()} matches`;
  $('tracks').replaceChildren();
  for (const track of filtered.slice(page * pageSize, (page + 1) * pageSize)) {
    const row = node('tr');
    row.classList.toggle('selected', selected.has(track.id));
    const checkCell = node('td'), checkbox = node('input');
    checkbox.type = 'checkbox'; checkbox.checked = selected.has(track.id); checkbox.disabled = busy;
    checkbox.setAttribute('aria-label', `Select ${track.name} by ${track.artists.join(', ')}`);
    checkbox.addEventListener('change', () => { checkbox.checked ? selected.add(track.id) : selected.delete(track.id); render(); });
    checkCell.append(checkbox); row.append(checkCell);
    const songCell = node('td'), song = node('div', undefined, 'song-cell'), cover = node('div', '♪', 'cover');
    if (track.image && track.image.startsWith('https://i.scdn.co/')) {
      const image = node('img'); image.src = track.image; image.alt = ''; image.loading = 'lazy'; cover.replaceChildren(image);
    }
    const info = node('div'), title = node('strong', track.name);
    if (track.url && track.url.startsWith('https://open.spotify.com/')) {
      const link = node('a'); link.href = track.url; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.append(title); info.append(link);
    } else info.append(title);
    info.append(node('small', track.artists.join(', '))); song.append(cover, info); songCell.append(song); row.append(songCell);
    row.append(node('td', track.album, 'album-col'));
    row.append(node('td', track.added_at ? new Date(track.added_at).toLocaleDateString() : '—', 'date-col'));
    const seconds = Math.floor(track.duration_ms / 1000);
    row.append(node('td', `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`, 'duration-col'));
    $('tracks').append(row);
  }
  $('empty').hidden = filtered.length > 0 || busy;
  $('selected-count').textContent = `${selected.size.toLocaleString()} songs selected`;
  const visibleSelected = filtered.filter(t => selected.has(t.id)).length;
  $('hidden-count').textContent = selected.size > visibleSelected ? `${selected.size - visibleSelected} selected songs are outside these filters.` : 'Your selection stays as you filter.';
  $('review').disabled = busy || !loaded || selected.size === 0;
  $('select-all').disabled = busy || !loaded || !filtered.length;
  $('clear-selection').disabled = busy || !selected.size;
  $('check-all').checked = filtered.length > 0 && filtered.every(t => selected.has(t.id));
  $('check-all').indeterminate = visibleSelected > 0 && visibleSelected < filtered.length;
  $('check-all').disabled = busy || !loaded || !filtered.length;
  $('refresh').disabled = busy;
  $('previous').disabled = busy || page === 0;
  $('next').disabled = busy || (page + 1) * pageSize >= filtered.length;
  $('page-label').textContent = filtered.length ? `Page ${page + 1} of ${Math.ceil(filtered.length / pageSize)}` : 'No results';
  fields.forEach(id => { $(id).disabled = busy; });
  $('reset').disabled = busy;
}
function updateSuggestions() {
  for (const [id, values] of [['artists', tracks.flatMap(t => t.artists)], ['albums', tracks.map(t => t.album)]]) {
    $(id).replaceChildren(...[...new Set(values)].sort().map(value => { const option = node('option'); option.value = value; return option; }));
  }
}
async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: {'Content-Type': 'application/json', 'X-CSRF-Token': document.body.dataset.csrf} });
  let data;
  try { data = await response.json(); } catch { throw new Error('Unexpected server response. Refresh the page and try again.'); }
  if (!response.ok) throw new Error(data.error + (data.retry_after ? ` Try again in ${data.retry_after} seconds.` : ''));
  return data;
}
async function loadLibrary() {
  busy = true; loaded = false; selected.clear(); tracks = []; page = 0; render();
  let offset = 0;
  try {
    do {
      status(`Loading liked songs… ${tracks.length.toLocaleString()} loaded`);
      const data = await api(`/api/tracks?offset=${offset}`);
      const known = new Set(tracks.map(t => t.id));
      tracks.push(...data.items.filter(t => !known.has(t.id)));
      offset = data.next_offset;
      render();
    } while (offset !== null);
    loaded = true; updateSuggestions();
    status(tracks.length ? 'Library ready. Filter your songs, then select the ones to let go.' : 'Your Liked Songs library is empty.');
  } catch (error) { status(`${error.message} Use Reload library to finish loading before selecting songs.`, true); }
  finally { busy = false; render(); }
}
fields.forEach(id => $(id).addEventListener('input', () => { page = 0; render(); }));
$('reset').onclick = () => { fields.slice(0, 3).forEach(id => { $(id).value = ''; }); page = 0; render(); };
$('select-all').onclick = () => { matches().forEach(t => selected.add(t.id)); render(); };
$('check-all').onchange = event => { matches().forEach(t => event.target.checked ? selected.add(t.id) : selected.delete(t.id)); render(); };
$('clear-selection').onclick = () => { selected.clear(); render(); };
$('previous').onclick = () => { page--; render(); };
$('next').onclick = () => { page++; render(); };
$('refresh').onclick = () => demo ? loadDemo() : loadLibrary();
$('review').onclick = () => {
  const chosen = tracks.filter(t => selected.has(t.id));
  $('confirm-summary').textContent = `${demo ? 'DEMO: ' : ''}You’re about to unlike ${chosen.length} songs, including selections outside the current filters.`;
  $('review-list').replaceChildren(...chosen.map(t => node('li', `${t.name} — ${t.artists.join(', ')} · ${t.album}`)));
  $('confirm-unlike').textContent = demo ? 'Unlike in demo only' : 'Unlike selected songs';
  $('confirm').showModal();
};
$('confirm-unlike').onclick = async () => {
  $('confirm').close(); busy = true; render();
  const ids = [...selected]; let removed = 0;
  try {
    for (let index = 0; index < ids.length; index += 40) {
      status(`Unliking songs… ${removed} of ${ids.length} completed`);
      const batch = ids.slice(index, index + 40);
      const result = demo ? {removed: batch} : await api('/api/unlike', {method: 'POST', body: JSON.stringify({ids: batch})});
      const done = new Set(result.removed);
      tracks = tracks.filter(t => !done.has(t.id)); done.forEach(id => selected.delete(id)); removed += done.size;
      render();
    }
    status(`${demo ? 'Demo: ' : ''}${removed} songs unliked. A little more room for you.`);
  } catch (error) { status(`${removed} songs confirmed removed. ${error.message} Remaining selections are kept; reload if a request’s outcome is uncertain.`, true); }
  finally { busy = false; updateSuggestions(); render(); }
};
function loadDemo() {
  demo = true; loaded = true; selected.clear(); page = 0;
  const examples = [
    ['Revenge', 'CaptainSparklez', 'Minecraft Songs'], ['TNT', 'CaptainSparklez', 'Minecraft Songs'],
    ['Fallen Kingdom', 'CaptainSparklez', 'Fallen Kingdom'], ['Minecraft Won’t Add Inches', 'Dan Bull', 'Gaming Anthems'],
    ['Creeper Rap', 'Dan Bull', 'Gaming Anthems'], ['Mine Diamonds', 'MCAP Steve', 'Diamond Days'],
    ['Sweden', 'C418', 'Minecraft - Volume Alpha'], ['Wet Hands', 'C418', 'Minecraft - Volume Alpha'],
    ['Dog Days Are Over', 'Florence + The Machine', 'Lungs'], ['Dreams', 'Fleetwood Mac', 'Rumours'],
    ['This Must Be the Place', 'Talking Heads', 'Speaking in Tongues'], ['Lovely Day', 'Bill Withers', 'Menagerie'],
  ];
  tracks = examples.map(([name, artist, album], i) => ({id: `demo-${i}`, name, artists:[artist], album, added_at:new Date(Date.UTC(2026, 8, 23-i)).toISOString(), duration_ms:180000 + i*7340}));
  $('welcome').hidden = true; $('library').hidden = false; $('mode-label').textContent = 'DEMO LIBRARY · NO SPOTIFY CHANGES';
  status('Demo mode. Try searching “Minecraft” or filtering by CaptainSparklez.'); updateSuggestions(); render();
}
if ($('demo')) $('demo').onclick = loadDemo;
if (document.body.dataset.connected === 'true') loadLibrary();
