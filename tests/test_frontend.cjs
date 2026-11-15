// Exercise the actual browser filtering and selection code with a small DOM stand-in.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function element() {
  return { value: '', dataset: {}, classList: {toggle() {}}, children: [],
    append(...items) { this.children.push(...items); },
    replaceChildren(...items) { this.children = items; },
    addEventListener() {}, setAttribute() {}, showModal() {}, close() {} };
}
const elements = new Map();
const context = vm.createContext({ console, Date, Set, Error,
  document: { body: {dataset: {connected: 'false'}},
    getElementById(id) { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); },
    createElement() { return element(); } },
});
vm.runInContext(fs.readFileSync('static/app.js', 'utf8') + `
loadDemo();
if (tracks.length !== 12) throw Error('Demo should load twelve songs');
$('keyword').value = 'minecraft';
if (matches().length !== 5) throw Error('Keyword should search titles and albums');
$('artist').value = 'captain';
if (matches().length !== 2) throw Error('Artist filter should combine with keyword');
$('album').value = 'fallen';
if (matches().length !== 0) throw Error('Album should combine with both filters');
$('reset').onclick();
$('artist').value = 'C418';
$('select-all').onclick();
if (selected.size !== 2) throw Error('Select all should select matches');
$('artist').value = 'Dan Bull'; render();
if (selected.size !== 2 || !$('hidden-count').textContent.startsWith('2 selected')) throw Error('Selection must persist across filters');
$('review').onclick();
if ($('review-list').children.length !== 2) throw Error('Review should include hidden selections');
$('clear-selection').onclick();
if (selected.size) throw Error('Clear selection should work');
tracks = Array.from({length: 105}, (_, i) => ({id: 'demo-' + i, name: 'Minecraft ' + i, artists:['Artist'], album:'Album', added_at:'2026-01-01', duration_ms:1000}));
$('reset').onclick(); $('select-all').onclick();
if (selected.size !== 105) throw Error('Select all should span pages');
if ($('tracks').children.length !== 50) throw Error('Table should paginate');
`, context);
assert.ok(true);
console.log('Frontend checks passed: combined filters, hidden selections, review, and selection across pages.');
