// run: node tests/parity.test.js  -- CLI parity: the Python CLI (--json) and core.js give the SAME key, plaintext and full step trace on fixed vectors
const assert = require('assert'), cp = require('child_process'), path = require('path'), os = require('os'), C = require('../core.js');
const PLAIN = 'THEOLDLIGHTHOUSEKEEPERCLIMBEDTHESPIRALSTAIRSEVERYEVENINGCARRYINGALAMPANDAFLASKOFTEABECAUSETHESTORMHADBEENGROWINGALLWEEKANDTHESHIPSWOULDNEEDTHEBEAMLONGBEFOREMIDNIGHT';
const CLI = path.join(__dirname, '..', 'cipher_trainer.py');
const vectors = [['caesar', '7'], ['atbash', ''], ['vigenere', 'LEMON'], ['substitution', 'QWERTYUIOPASDFGHJKLZXCVBNM'], ['columnar', 'ZEBRAS']];
const py = (args) => cp.execFileSync('python3', ['-I', CLI, ...args], { encoding: 'utf8', cwd: os.tmpdir() });
vectors.forEach(([c, k]) => {
  const ct = py(['encrypt', c, '--key', k, PLAIN]).trim(); assert.strictEqual(ct, C.encrypt(c, PLAIN, k), c + ' encrypt differs');
  const p = JSON.parse(py(['break', c, '--json', ct])), j = C.breakCipher(c, ct);
  assert.deepStrictEqual(p, j, c + ': Python CLI and JS trace differ');
  console.log('parity ok', c, j.steps.length, 'trace lines');
});
const ctv = C.encrypt('vigenere', PLAIN, 'LAMP'), p = JSON.parse(py(['break', 'auto', '--json', ctv])); assert.deepStrictEqual(p, C.breakCipher('auto', ctv)); console.log('parity ok auto');
console.log('parity tests passed');
