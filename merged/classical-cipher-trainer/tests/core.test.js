// run: node tests/core.test.js  -- known-plaintext round trips for every cipher in the JavaScript port
const assert = require('assert'), C = require('../core.js');
const PLAIN = 'THEOLDLIGHTHOUSEKEEPERCLIMBEDTHESPIRALSTAIRSEVERYEVENINGCARRYINGALAMPANDAFLASKOFTEABECAUSETHESTORMHADBEENGROWINGALLWEEKANDTHESHIPSWOULDNEEDTHEBEAMLONGBEFOREMIDNIGHT' +
  'HEKNEWEACHSTEPBYTHESOUNDITMADEUNDERHISBOOTSANDHECOUNTEDTHEMOUTOFHABITUNTILHEREACHEDTHEIRONDOORATTHETOP';
const SUB = 'QWERTYUIOPASDFGHJKLZXCVBNM';
assert.strictEqual(C.encrypt('caesar', 'attack at dawn', '3'), 'DWWDFNDWGDZQ');
assert.strictEqual(C.encrypt('atbash', 'attack'), 'ZGGZXP');
assert.strictEqual(C.encrypt('vigenere', 'attack at dawn', 'LEMON'), 'LXFOPVEFRNHR');
assert.strictEqual(C.encrypt('columnar', 'WEAREDISCOVERED', 'ZEBRAS'), 'EVACDESERODEWIR');
assert.strictEqual(C.encrypt('substitution', 'abc', SUB), 'QWE');
[['caesar', '11'], ['atbash', ''], ['vigenere', 'BEACON'], ['substitution', SUB], ['columnar', 'ZEBRAS']].forEach(([c, k]) => {
  const r = C.breakCipher(c, C.encrypt(c, PLAIN, k)); assert.strictEqual(r.plaintext, PLAIN, c);
  assert(r.steps.length >= 3 && r.steps.every(s => typeof s === 'string'), c + ' trace');
  if (c === 'vigenere') assert.strictEqual(r.key, 'BEACON');
});
const a = C.breakCipher('auto', C.encrypt('caesar', PLAIN, '4')); assert.strictEqual(a.plaintext, PLAIN); assert.strictEqual(a.cipher, 'auto:caesar');
assert.throws(() => C.breakCipher('caesar', 'ab'), /at least 4/); assert.throws(() => C.encrypt('substitution', 'abc', 'ABC'), /26-letter/);
console.log('core tests passed');
