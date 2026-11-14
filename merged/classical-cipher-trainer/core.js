/* classical-cipher-trainer core: JavaScript port of cipher_trainer.py. Same algorithms, same integer quadgram table (data.js), same seeded LCG,
   so both print the same trace (tests/parity.test.js). No network calls: data.js is loaded as a script tag. */
(function (g) {
  "use strict";
  if (typeof CIPHER_DATA === "undefined" && typeof require !== "undefined") require("./data.js");
  var D = g.CIPHER_DATA, A = "ABCDEFGHIJKLMNOPQRSTUVWXYZ", FREQ = D.freq, FLOOR = D.floor, SEARCH_CAP = 600;
  var T = new Int16Array(456976).fill(FLOOR);
  Object.keys(D.quad).forEach(function (q) { T[(((q.charCodeAt(0) - 65) * 26 + q.charCodeAt(1) - 65) * 26 + q.charCodeAt(2) - 65) * 26 + q.charCodeAt(3) - 65] = D.quad[q]; });
  var EN_ORDER = []; for (var i0 = 0; i0 < 26; i0++) EN_ORDER.push(i0);
  EN_ORDER.sort(function (a, b) { return (FREQ[b] - FREQ[a]) || (a - b); });

  function norm(text) { var o = [], t = String(text).toUpperCase(); for (var i = 0; i < t.length; i++) { var c = t.charCodeAt(i); if (c >= 65 && c <= 90) o.push(c - 65); } return o; }
  function txt(p) { var s = ""; for (var i = 0; i < p.length; i++) s += A[p[i]]; return s; }
  function Rng() { this.s = 12345; }
  Rng.prototype.nxt = function (n) { this.s = (Math.imul(this.s, 1664525) + 1013904223) >>> 0; return (this.s >>> 16) % n; };
  function qscore(p) { var tot = 0; for (var i = 0; i < p.length - 3; i++) tot += T[((p[i] * 26 + p[i + 1]) * 26 + p[i + 2]) * 26 + p[i + 3]]; return tot; }
  function mean(p) { return (qscore(p) / Math.max(1, p.length - 3) / 100).toFixed(2); }
  function counts(p) { var c = []; for (var i = 0; i < 26; i++) c.push(0); for (var j = 0; j < p.length; j++) c[p[j]]++; return c; }
  function chi2(c, n) { var s = 0; for (var k = 0; k < 26; k++) { var e = n * FREQ[k], d = c[k] - e; s += d * d / e; } return s; }
  function ic(c, n) { if (n < 2) return 0; var s = 0; for (var k = 0; k < 26; k++) s += c[k] * (c[k] - 1); return s / (n * (n - 1)); }
  function byCount(c) { var o = []; for (var k = 0; k < 26; k++) o.push(k); return o.sort(function (a, b) { return (c[b] - c[a]) || (a - b); }); }
  function freqLine(c, n) { return byCount(c).slice(0, 6).map(function (k) { return A[k] + " " + (100 * c[k] / n).toFixed(1) + "%"; }).join(", "); }
  var EN_LINE = EN_ORDER.slice(0, 6).map(function (k) { return A[k] + " " + (100 * FREQ[k]).toFixed(1) + "%"; }).join(", ");
  function res(cipher, key, pt, steps) { return { cipher: cipher, key: key, plaintext: txt(pt), quadgram_mean: mean(pt), steps: steps }; }
  function pad(n, w) { var s = String(n); while (s.length < w) s = " " + s; return s; }
  function shiftRows(c, m) {
    var rows = [];
    for (var s = 0; s < 26; s++) { var sh = []; for (var k = 0; k < 26; k++) sh.push(0); for (var k2 = 0; k2 < 26; k2++) sh[((k2 - s) % 26 + 26) % 26] = c[k2]; rows.push([chi2(sh, m), s]); }
    return rows.sort(function (a, b) { return (a[0] - b[0]) || (a[1] - b[1]); });
  }

  function bCaesar(p) {
    var n = p.length, c = counts(p), st = ["Step 1: count the letters (" + n + " letters).", "  ciphertext most common: " + freqLine(c, n), "  English most common:    " + EN_LINE,
      "Step 2: try all 26 shifts; chi-squared against English letter frequencies (lower = more English-like)."];
    var rows = shiftRows(c, n);
    rows.slice(0, 5).forEach(function (r) { st.push("  shift " + pad(r[1], 2) + " (" + A[r[1]] + " -> A): chi2 = " + r[0].toFixed(2)); });
    var s = rows[0][1], pt = p.map(function (x) { return ((x - s) % 26 + 26) % 26; });
    st.push("Step 3: lowest chi-squared is shift " + s + " (key letter " + A[s] + "). Plaintext quadgram score: " + mean(pt) + " per quadgram (log10; closer to 0 is more English-like, a quadgram the table has never seen counts " + (FLOOR / 100).toFixed(2) + ").");
    return res("caesar", String(s), pt, st);
  }
  function bAtbash(p) {
    var n = p.length, c = counts(p), pt = p.map(function (x) { return 25 - x; });
    return res("atbash", "", pt, ["Step 1: count the letters (" + n + " letters).", "  ciphertext most common: " + freqLine(c, n), "  English most common:    " + EN_LINE,
      "Step 2: Atbash has no key: it maps A<->Z, B<->Y, and so on. Reverse the alphabet.",
      "Step 3: quadgram score per quadgram (log10): ciphertext as given " + mean(p) + ", after Atbash " + mean(pt) + "."]);
  }
  function column(p, j, L) { var o = []; for (var i = j; i < p.length; i += L) o.push(p[i]); return o; }
  function bVigenere(p, maxlen) {
    var n = p.length; maxlen = Math.max(1, Math.min(maxlen === undefined ? 16 : maxlen, Math.floor(n / 2)));
    var st = ["Step 1: Kasiski. Distances between repeated trigrams share a factor with the key length."];
    var seen = {}, votes = [], pairs = 0, f, i;
    for (f = 0; f <= maxlen; f++) votes.push(0);
    for (i = 0; i < n - 2; i++) { var key = p[i] * 676 + p[i + 1] * 26 + p[i + 2]; if (seen[key] !== undefined) { var d = i - seen[key]; pairs++; for (f = 2; f <= maxlen; f++) if (d % f === 0) votes[f]++; } seen[key] = i; }
    var cand = []; for (f = 2; f <= maxlen; f++) cand.push(f);
    var top = cand.sort(function (a, b) { return (votes[b] - votes[a]) || (a - b); }).slice(0, 5);
    st.push("  " + pairs + " repeated-trigram distances; factor votes: " + (top.filter(function (x) { return votes[x]; }).map(function (x) { return x + ": " + votes[x]; }).join(", ") || "none"));
    st.push("Step 2: index of coincidence per key length (English ~0.067, random ~0.038); the columns of the right length are each one Caesar shift.");
    var avg = [], L, j;
    for (L = 1; L <= maxlen; L++) { var tot = 0; for (j = 0; j < L; j++) { var col = column(p, j, L); tot += ic(counts(col), col.length); } avg.push(tot / L); }
    for (i = 0; i < maxlen; i += 6) { var parts = []; for (L = i + 1; L < Math.min(i + 7, maxlen + 1); L++) parts.push("L=" + L + " " + avg[L - 1].toFixed(4)); st.push("  " + parts.join("  ")); }
    var best = Math.max.apply(null, avg); L = 1; while (!(avg[L - 1] >= 0.9 * best)) L++;
    var kt = votes[top[0]] ? top[0] : 0, note = !kt ? "Kasiski found no repeats." : "Kasiski's top factor is " + kt + " (" + (L % kt === 0 ? "divides" : "does not divide") + " " + L + ").";
    st.push("Step 3: best IC " + best.toFixed(4) + "; the shortest length within 90% of it is " + L + ". " + note);
    st.push("Step 4: for each of the " + L + " columns, try the 26 shifts and keep the lowest chi-squared.");
    var ks = [];
    for (j = 0; j < L; j++) { var cl = column(p, j, L), rows = shiftRows(counts(cl), cl.length); ks.push(rows[0][1]);
      st.push("  column " + (j + 1) + " (" + cl.length + " letters): shift " + A[rows[0][1]] + " chi2 " + rows[0][0].toFixed(2) + ", runner-up " + A[rows[1][1]] + " chi2 " + rows[1][0].toFixed(2)); }
    var pt = p.map(function (x, k) { return ((x - ks[k % L]) % 26 + 26) % 26; }), kw = txt(ks);
    st.push("Step 5: key " + kw + ". Plaintext quadgram score: " + mean(pt) + " per quadgram.");
    return res("vigenere", kw, pt, st);
  }
  function bSubstitution(p) {
    var restarts = 10, n = p.length, c = counts(p), rng = new Rng(), q = p.slice(0, SEARCH_CAP);
    var st = ["Step 1: count the letters (" + n + " letters); index of coincidence " + ic(c, n).toFixed(4) + " (a one-to-one substitution keeps English's ~0.067).", "  ciphertext most common: " + freqLine(c, n), "  English most common:    " + EN_LINE];
    var cl = byCount(c), m = []; for (var k = 0; k < 26; k++) m.push(0);
    cl.forEach(function (ck, r) { m[ck] = EN_ORDER[r]; });
    st.push("Step 2: start by matching letters by frequency rank (cipher " + txt(cl.slice(0, 5)) + " -> plain " + txt(EN_ORDER.slice(0, 5)) + " ...).");
    function ev(mm) { return qscore(q.map(function (x) { return mm[x]; })); }
    function climb(mm) {
      var cur = ev(mm), imp = true;
      while (imp) { imp = false;
        for (var i = 0; i < 26; i++) for (var j = i + 1; j < 26; j++) { var t = mm[i]; mm[i] = mm[j]; mm[j] = t; var s = ev(mm); if (s > cur) { cur = s; imp = true; } else { t = mm[i]; mm[i] = mm[j]; mm[j] = t; } } }
      return cur;
    }
    st.push("Step 3: hill climb. Swap two plaintext letters in the key; keep the swap when the English quadgram score goes up; " + restarts + " restarts from the best key so far, each with 4 random swaps.");
    var best = m.slice(), bs = climb(best); st.push("  start: score " + bs);
    for (var r = 1; r <= restarts; r++) {
      var t2 = best.slice();
      for (var z = 0; z < 4; z++) { var i = rng.nxt(26), j = rng.nxt(26), tmp = t2[i]; t2[i] = t2[j]; t2[j] = tmp; }
      var s2 = climb(t2); if (s2 > bs) { bs = s2; best = t2; }
      st.push("  restart " + r + ": score " + s2 + " (best " + bs + ")");
    }
    var pt = p.map(function (x) { return best[x]; }), enc = []; for (k = 0; k < 26; k++) enc.push(0); for (k = 0; k < 26; k++) enc[best[k]] = k;
    var key = txt(enc);
    st.push("Step 4: cipher alphabet (plain A..Z -> cipher): " + key + ". Plaintext quadgram score: " + mean(pt) + " per quadgram.");
    return res("substitution", key, pt, st);
  }
  function colDecrypt(p, perm) {
    var w = perm.length, n = p.length, ln = [], cols = [], pos = 0, c, k, r;
    for (c = 0; c < w; c++) ln.push(Math.floor(n / w) + (c < n % w ? 1 : 0));
    for (k = 0; k < w; k++) { c = perm[k]; cols[c] = p.slice(pos, pos + ln[c]); pos += ln[c]; }
    var out = [], rows = Math.floor((n + w - 1) / w);
    for (r = 0; r < rows; r++) for (c = 0; c < w; c++) if (r < ln[c]) out.push(cols[c][r]);
    return out;
  }
  function colEncrypt(p, perm) { var out = [], w = perm.length; perm.forEach(function (c) { for (var i = c; i < p.length; i += w) out.push(p[i]); }); return out; }
  function permWord(perm) { var w = []; perm.forEach(function (c, k) { w[c] = k; }); return txt(w); }
  function order(perm) { return perm.map(function (x) { return x + 1; }).join("-"); }
  function bColumnar(p, maxw) {
    var n = p.length; maxw = Math.max(2, Math.min(maxw === undefined ? 8 : maxw, Math.floor(n / 2)));
    var rng = new Rng(), q = p.slice(0, SEARCH_CAP);
    var st = ["Step 1: letter counts (" + n + " letters). Index of coincidence " + ic(counts(p), n).toFixed(4) + ": close to English's ~0.067 means the letters are only rearranged.",
      "Step 2: for each width 2.." + maxw + ", search the column order (swap two columns, keep it when the quadgram score goes up, several restarts)."];
    var best = null;
    for (var w = 2; w <= maxw; w++) {
      var wb = null, ws = null;
      for (var r = 0; r < 2 + 4 * w; r++) {
        var perm = []; for (var a = 0; a < w; a++) perm.push(a);
        if (r) for (var i = w - 1; i > 0; i--) { var j = rng.nxt(i + 1), t = perm[i]; perm[i] = perm[j]; perm[j] = t; }
        var cur = qscore(colDecrypt(q, perm)), imp = true;
        while (imp) { imp = false;
          for (var x = 0; x < w; x++) for (var y = x + 1; y < w; y++) { var t2 = perm[x]; perm[x] = perm[y]; perm[y] = t2; var s = qscore(colDecrypt(q, perm)); if (s > cur) { cur = s; imp = true; } else { t2 = perm[x]; perm[x] = perm[y]; perm[y] = t2; } } }
        if (ws === null || cur > ws) { ws = cur; wb = perm.slice(); }
      }
      st.push("  width " + w + ": best score " + ws + ", column order " + order(wb));
      if (best === null || ws > best[0]) best = [ws, w, wb];
    }
    var perm2 = best[2], pt = colDecrypt(p, perm2);
    st.push("Step 3: width " + best[1] + " scores highest (the smallest width wins ties). Columns are read in order " + order(perm2) + "; equivalent key word " + permWord(perm2) + ". Plaintext quadgram score: " + mean(pt) + " per quadgram.");
    return res("columnar", permWord(perm2), pt, st);
  }
  function bAuto(p, o) {
    var n = p.length, i = ic(counts(p), n);
    var st = ["Auto: index of coincidence of the whole text is " + i.toFixed(4) + " (English ~0.067, polyalphabetic ~0.04-0.05)."];
    var runs = [bCaesar(p), bAtbash(p)];
    if (i >= 0.055) runs.push(bColumnar(p, o.maxwidth), bSubstitution(p)); else runs.push(bVigenere(p, o.maxlen));
    runs.forEach(function (r) { st.push("", "== Trying " + r.cipher + " =="); r.steps.forEach(function (l) { st.push(l); }); });
    var best = runs[0];
    runs.slice(1).forEach(function (r) { if (qscore(norm(r.plaintext)) > qscore(norm(best.plaintext))) best = r; });
    st.push("", "Auto: best quadgram score per quadgram: " + runs.map(function (r) { return r.cipher + " " + r.quadgram_mean; }).join(", ") + ". Winner: " + best.cipher + ".");
    return { cipher: "auto:" + best.cipher, key: best.key, plaintext: best.plaintext, quadgram_mean: best.quadgram_mean, steps: st };
  }
  function breakCipher(cipher, text, opts) {
    opts = opts || {}; var p = norm(text), maxlen = opts.maxlen === undefined ? 16 : opts.maxlen, maxwidth = opts.maxwidth === undefined ? 8 : opts.maxwidth;
    if (p.length < 4) throw new Error("need at least 4 letters");
    switch (cipher) {
      case "caesar": return bCaesar(p); case "atbash": return bAtbash(p); case "vigenere": return bVigenere(p, maxlen);
      case "substitution": return bSubstitution(p); case "columnar": return bColumnar(p, maxwidth); case "auto": return bAuto(p, { maxlen: maxlen, maxwidth: maxwidth });
    }
    throw new Error("unknown cipher " + cipher);
  }
  function encrypt(cipher, text, key) {
    var p = norm(text), k;
    key = key === undefined ? "" : String(key);
    if (cipher === "caesar") { var s = parseInt(key, 10); if (isNaN(s)) throw new Error("caesar needs a number key"); return txt(p.map(function (x) { return (((x + s) % 26) + 26) % 26; })); }
    if (cipher === "atbash") return txt(p.map(function (x) { return 25 - x; }));
    if (cipher === "vigenere") { k = norm(key); if (!k.length) throw new Error("vigenere needs key letters"); return txt(p.map(function (x, i) { return (x + k[i % k.length]) % 26; })); }
    if (cipher === "substitution") { k = norm(key); if (k.slice().sort(function (a, b) { return a - b; }).join() !== EN_ORDER.slice().sort(function (a, b) { return a - b; }).join()) throw new Error("substitution key must be a 26-letter permutation (plain A..Z -> cipher letters)"); return txt(p.map(function (x) { return k[x]; })); }
    if (cipher === "columnar") { k = norm(key); if (k.length < 2) throw new Error("columnar needs a key word of 2+ letters"); var idx = k.map(function (_, i) { return i; }).sort(function (a, b) { return (k[a] - k[b]) || (a - b); }); return txt(colEncrypt(p, idx)); }
    throw new Error("unknown cipher " + cipher);
  }
  g.CipherTrainer = { norm: norm, breakCipher: breakCipher, encrypt: encrypt, qscore: qscore };
  if (typeof module !== "undefined" && module.exports) module.exports = g.CipherTrainer;
})(typeof window !== "undefined" ? window : globalThis);
