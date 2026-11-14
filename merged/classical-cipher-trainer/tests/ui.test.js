// run: node tests/ui.test.js -- every element id app.js uses exists in index.html; page code has no network API and no external resource
const assert = require('assert'), fs = require('fs'), path = require('path');
const R = (f) => fs.readFileSync(path.join(__dirname, '..', f), 'utf8');
const html = R('index.html'), app = R('app.js'), core = R('core.js');
const ids = new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]));
const used = [...app.matchAll(/\$\("([^"]+)"\)/g)].map(m => m[1]);
used.forEach(i => assert(ids.has(i), 'index.html has no #' + i));
[...html.matchAll(/(?:src|href)="([^"#:]+)"/g)].forEach(m => assert(fs.existsSync(path.join(__dirname, '..', m[1])), 'missing ' + m[1]));
assert(!/(?:src|href)="(https?:)?\/\//.test(html), 'external resource');
assert(!/\b(fetch|XMLHttpRequest|sendBeacon|WebSocket|EventSource|importScripts)\b/.test(app + core.replace(/require\(/g, '')), 'network api');
// the page works end to end against a stub DOM
const els = {}; global.window = global; global.document = { getElementById: (i) => els[i] || (els[i] = { value: '', textContent: '', hidden: false, style: {}, className: '', addEventListener(ev, fn) { this['on' + ev] = fn; } }) };
require('../data.js'); require('../core.js'); global.setTimeout = (f) => f();
els.ct = { value: '', style: {}, addEventListener() {} }; els.maxlen = { value: '16' }; els.maxwidth = { value: '8' }; els.cipher = { value: 'caesar' };
require('../app.js');
els.ct.value = 'WKLVLVDWHVWRIWKHFDHVDUFLSKHUEUHDNHU'; els.go.onclick();
assert(/plaintext: THISISATESTOFTHECAESARCIPHERBREAKER/.test(els.result.textContent), els.result.textContent); assert(els.trace.textContent.includes('Step 2'));
els.ecipher = { value: 'caesar' }; els.pt = { value: 'attack at dawn' }; els.ekey = { value: '3' }; els.enc.onclick(); assert.strictEqual(els.encout.textContent, 'DWWDFNDWGDZQ');
console.log('ui tests passed');
