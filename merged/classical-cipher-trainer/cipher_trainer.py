#!/usr/bin/env python3
"""classical-cipher-trainer: break classical ciphers and print every cryptanalysis step. Standard library only (needs data.json next to this file).

  python3 -I cipher_trainer.py break caesar "WKLV LV D WHVW"
  python3 -I cipher_trainer.py break auto -f message.txt
  python3 -I cipher_trainer.py encrypt vigenere --key LEMON "attack at dawn"

Ciphers: caesar, atbash, vigenere (Kasiski + index of coincidence for the key length, then chi-squared per column), substitution (hill climb scored by English
quadgrams), columnar (column-order hill climb scored by quadgrams), auto (tries them by letter statistics and keeps the best-scoring plaintext).
Text is reduced to the letters A-Z. Breaking is statistical: short ciphertexts can come out wrong, and the trace shows the scores so you can judge.
The same algorithms run in core.js (the browser page); tests/parity.test.js checks both print the same trace."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

A = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
D = json.loads(Path(__file__).with_name("data.json").read_text(encoding="utf-8"))
FREQ, FLOOR = D["freq"], D["floor"]
T = [FLOOR] * 456976
for _q, _s in D["quad"].items():
    T[((ord(_q[0]) - 65) * 26 + ord(_q[1]) - 65) * 676 + (ord(_q[2]) - 65) * 26 + ord(_q[3]) - 65] = _s
EN_ORDER = [i for i in sorted(range(26), key=lambda i: (-FREQ[i], i))]
SEARCH_CAP = 600


def norm(text: str) -> list[int]:
    return [ord(c) - 65 for c in text.upper() if "A" <= c <= "Z"]


def txt(p) -> str:
    return "".join(A[i] for i in p)


class Rng:
    """32-bit LCG, same constants and steps as core.js, so both break the same text the same way."""
    def __init__(self, seed: int = 12345): self.s = seed

    def nxt(self, n: int) -> int:
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.s >> 16) % n


def qscore(p) -> int:
    t = T; tot = 0
    for i in range(len(p) - 3):
        tot += t[((p[i] * 26 + p[i + 1]) * 26 + p[i + 2]) * 26 + p[i + 3]]
    return tot


def mean(p) -> str:
    return "%.2f" % (qscore(p) / max(1, len(p) - 3) / 100)


def counts(p) -> list[int]:
    c = [0] * 26
    for x in p: c[x] += 1
    return c


def chi2(c, n) -> float:
    s = 0.0
    for k in range(26):
        e = n * FREQ[k]; d = c[k] - e; s += d * d / e
    return s


def ic(c, n) -> float:
    if n < 2: return 0.0
    return sum(x * (x - 1) for x in c) / (n * (n - 1))


def freq_line(c, n) -> str:
    top = sorted(range(26), key=lambda k: (-c[k], k))[:6]
    return ", ".join("%s %s%%" % (A[k], "%.1f" % (100 * c[k] / n)) for k in top)


EN_LINE = ", ".join("%s %s%%" % (A[k], "%.1f" % (100 * FREQ[k])) for k in EN_ORDER[:6])


def res(cipher, key, pt, steps):
    return {"cipher": cipher, "key": key, "plaintext": txt(pt), "quadgram_mean": mean(pt), "steps": steps}


def b_caesar(p):
    n = len(p); c = counts(p); st = ["Step 1: count the letters (%d letters)." % n, "  ciphertext most common: " + freq_line(c, n), "  English most common:    " + EN_LINE,
        "Step 2: try all 26 shifts; chi-squared against English letter frequencies (lower = more English-like)."]
    rows = []
    for s in range(26):
        sh = [0] * 26
        for k in range(26): sh[(k - s) % 26] = c[k]
        rows.append((chi2(sh, n), s))
    rows.sort()
    for x, s in rows[:5]: st.append("  shift %2d (%s -> A): chi2 = %s" % (s, A[s], "%.2f" % x))
    s = rows[0][1]; pt = [(x - s) % 26 for x in p]
    st.append("Step 3: lowest chi-squared is shift %d (key letter %s). Plaintext quadgram score: %s per quadgram (log10; closer to 0 is more English-like, a quadgram the table has never seen counts %s)." % (s, A[s], mean(pt), "%.2f" % (FLOOR / 100)))
    return res("caesar", str(s), pt, st)


def b_atbash(p):
    n = len(p); c = counts(p); pt = [25 - x for x in p]
    st = ["Step 1: count the letters (%d letters)." % n, "  ciphertext most common: " + freq_line(c, n), "  English most common:    " + EN_LINE,
          "Step 2: Atbash has no key: it maps A<->Z, B<->Y, and so on. Reverse the alphabet.",
          "Step 3: quadgram score per quadgram (log10): ciphertext as given %s, after Atbash %s." % (mean(p), mean(pt))]
    return res("atbash", "", pt, st)


def kasiski(p, maxlen):
    seen = {}; votes = [0] * (maxlen + 1); pairs = 0
    for i in range(len(p) - 2):
        g = (p[i], p[i + 1], p[i + 2])
        if g in seen:
            d = i - seen[g]; pairs += 1
            for f in range(2, maxlen + 1):
                if d % f == 0: votes[f] += 1
        seen[g] = i
    return votes, pairs


def b_vigenere(p, maxlen=16):
    n = len(p); maxlen = max(1, min(maxlen, n // 2)); st = ["Step 1: Kasiski. Distances between repeated trigrams share a factor with the key length."]
    votes, pairs = kasiski(p, maxlen)
    top = sorted(range(2, maxlen + 1), key=lambda f: (-votes[f], f))[:5]
    st.append("  %d repeated-trigram distances; factor votes: %s" % (pairs, ", ".join("%d: %d" % (f, votes[f]) for f in top if votes[f]) or "none"))
    st.append("Step 2: index of coincidence per key length (English ~0.067, random ~0.038); the columns of the right length are each one Caesar shift.")
    avg = []
    for L in range(1, maxlen + 1):
        tot = 0.0
        for j in range(L):
            col = p[j::L]; tot += ic(counts(col), len(col))
        avg.append(tot / L)
    for i in range(0, maxlen, 6): st.append("  " + "  ".join("L=%d %s" % (L, "%.4f" % avg[L - 1]) for L in range(i + 1, min(i + 7, maxlen + 1))))
    best = max(avg); L = next(l for l in range(1, maxlen + 1) if avg[l - 1] >= 0.9 * best)
    kt = top[0] if votes[top[0]] else 0
    note = "Kasiski found no repeats." if not kt else "Kasiski's top factor is %d (%s %d)." % (kt, "divides" if L % kt == 0 else "does not divide", L)
    st.append("Step 3: best IC %s; the shortest length within 90%% of it is %d. %s" % ("%.4f" % best, L, note))
    st.append("Step 4: for each of the %d columns, try the 26 shifts and keep the lowest chi-squared." % L)
    key = []
    for j in range(L):
        col = p[j::L]; c = counts(col); m = len(col); rows = []
        for s in range(26):
            sh = [0] * 26
            for k in range(26): sh[(k - s) % 26] = c[k]
            rows.append((chi2(sh, m), s))
        rows.sort(); key.append(rows[0][1])
        st.append("  column %d (%d letters): shift %s chi2 %s, runner-up %s chi2 %s" % (j + 1, m, A[rows[0][1]], "%.2f" % rows[0][0], A[rows[1][1]], "%.2f" % rows[1][0]))
    pt = [(x - key[i % L]) % 26 for i, x in enumerate(p)]
    kw = txt(key)
    st.append("Step 5: key %s. Plaintext quadgram score: %s per quadgram." % (kw, mean(pt)))
    return res("vigenere", kw, pt, st)


def b_substitution(p, restarts=10):
    n = len(p); c = counts(p); rng = Rng(); q = p[:SEARCH_CAP]
    st = ["Step 1: count the letters (%d letters); index of coincidence %s (a one-to-one substitution keeps English's ~0.067)." % (n, "%.4f" % ic(c, n)), "  ciphertext most common: " + freq_line(c, n), "  English most common:    " + EN_LINE]
    cl = sorted(range(26), key=lambda k: (-c[k], k)); m = [0] * 26
    for r, k in enumerate(cl): m[k] = EN_ORDER[r]
    st.append("Step 2: start by matching letters by frequency rank (cipher %s -> plain %s ...)." % (txt(cl[:5]), txt(EN_ORDER[:5])))

    def ev(mm): return qscore([mm[x] for x in q])

    def climb(mm):
        cur = ev(mm); imp = True
        while imp:
            imp = False
            for i in range(26):
                for j in range(i + 1, 26):
                    mm[i], mm[j] = mm[j], mm[i]; s = ev(mm)
                    if s > cur: cur = s; imp = True
                    else: mm[i], mm[j] = mm[j], mm[i]
        return cur
    st.append("Step 3: hill climb. Swap two plaintext letters in the key; keep the swap when the English quadgram score goes up; %d restarts from the best key so far, each with 4 random swaps." % restarts)
    best = m[:]; bs = climb(best); st.append("  start: score %d" % bs)
    for r in range(1, restarts + 1):
        t = best[:]
        for _ in range(4):
            i = rng.nxt(26); j = rng.nxt(26); t[i], t[j] = t[j], t[i]
        s = climb(t)
        if s > bs: bs = s; best = t
        st.append("  restart %d: score %d (best %d)" % (r, s, bs))
    pt = [best[x] for x in p]; enc = [0] * 26
    for k in range(26): enc[best[k]] = k
    key = txt(enc)
    st.append("Step 4: cipher alphabet (plain A..Z -> cipher): %s. Plaintext quadgram score: %s per quadgram." % (key, mean(pt)))
    return res("substitution", key, pt, st)


def col_decrypt(p, perm):
    w = len(perm); n = len(p); ln = [n // w + (1 if c < n % w else 0) for c in range(w)]; cols = [None] * w; pos = 0
    for k in range(w):
        c = perm[k]; cols[c] = p[pos:pos + ln[c]]; pos += ln[c]
    out = []
    for r in range((n + w - 1) // w):
        for c in range(w):
            if r < ln[c]: out.append(cols[c][r])
    return out


def col_encrypt(p, perm):
    w = len(perm); out = []
    for c in perm: out.extend(p[c::w])
    return out


def perm_word(perm):
    w = [0] * len(perm)
    for k, c in enumerate(perm): w[c] = k
    return txt(w)


def b_columnar(p, maxw=8):
    n = len(p); maxw = max(2, min(maxw, n // 2)); rng = Rng(); q = p[:SEARCH_CAP]
    st = ["Step 1: letter counts (%d letters). Index of coincidence %s: close to English's ~0.067 means the letters are only rearranged." % (n, "%.4f" % ic(counts(p), n)),
          "Step 2: for each width 2..%d, search the column order (swap two columns, keep it when the quadgram score goes up, several restarts)." % maxw]
    best = None
    for w in range(2, maxw + 1):
        wb = None; ws = None
        for r in range(2 + 4 * w):
            perm = list(range(w))
            if r:
                for i in range(w - 1, 0, -1):
                    j = rng.nxt(i + 1); perm[i], perm[j] = perm[j], perm[i]
            cur = qscore(col_decrypt(q, perm)); imp = True
            while imp:
                imp = False
                for i in range(w):
                    for j in range(i + 1, w):
                        perm[i], perm[j] = perm[j], perm[i]; s = qscore(col_decrypt(q, perm))
                        if s > cur: cur = s; imp = True
                        else: perm[i], perm[j] = perm[j], perm[i]
            if ws is None or cur > ws: ws = cur; wb = perm[:]
        st.append("  width %d: best score %d, column order %s" % (w, ws, "-".join(str(x + 1) for x in wb)))
        if best is None or ws > best[0]: best = (ws, w, wb)
    _, w, perm = best; pt = col_decrypt(p, perm)
    st.append("Step 3: width %d scores highest (the smallest width wins ties). Columns are read in order %s; equivalent key word %s. Plaintext quadgram score: %s per quadgram." % (w, "-".join(str(x + 1) for x in perm), perm_word(perm), mean(pt)))
    return res("columnar", perm_word(perm), pt, st)


def b_auto(p, **kw):
    n = len(p); i = ic(counts(p), n)
    st = ["Auto: index of coincidence of the whole text is %s (English ~0.067, polyalphabetic ~0.04-0.05)." % ("%.4f" % i)]
    runs = [b_caesar(p), b_atbash(p)]
    runs += [b_columnar(p, kw.get("maxw", 8)), b_substitution(p)] if i >= 0.055 else [b_vigenere(p, kw.get("maxlen", 16))]
    for r in runs: st += ["", "== Trying %s ==" % r["cipher"]] + r["steps"]
    best = runs[0]
    for r in runs[1:]:
        if qscore(txt_to(r["plaintext"])) > qscore(txt_to(best["plaintext"])): best = r
    st += ["", "Auto: best quadgram score per quadgram: " + ", ".join("%s %s" % (r["cipher"], r["quadgram_mean"]) for r in runs) + ". Winner: %s." % best["cipher"]]
    return {"cipher": "auto:" + best["cipher"], "key": best["key"], "plaintext": best["plaintext"], "quadgram_mean": best["quadgram_mean"], "steps": st}


def txt_to(s): return [ord(c) - 65 for c in s]


def break_cipher(cipher, text, maxlen=16, maxwidth=8):
    p = norm(text)
    if len(p) < 4: raise ValueError("need at least 4 letters")
    if cipher == "caesar": return b_caesar(p)
    if cipher == "atbash": return b_atbash(p)
    if cipher == "vigenere": return b_vigenere(p, maxlen)
    if cipher == "substitution": return b_substitution(p)
    if cipher == "columnar": return b_columnar(p, maxwidth)
    if cipher == "auto": return b_auto(p, maxlen=maxlen, maxw=maxwidth)
    raise ValueError("unknown cipher " + cipher)


def encrypt(cipher, text, key=""):
    p = norm(text)
    if cipher == "caesar": return txt((x + int(key)) % 26 for x in p)
    if cipher == "atbash": return txt(25 - x for x in p)
    if cipher == "vigenere":
        k = norm(key)
        if not k: raise ValueError("vigenere needs --key LETTERS")
        return txt((x + k[i % len(k)]) % 26 for i, x in enumerate(p))
    if cipher == "substitution":
        k = norm(key)
        if sorted(k) != list(range(26)): raise ValueError("substitution key must be a 26-letter permutation (plain A..Z -> cipher letters)")
        return txt(k[x] for x in p)
    if cipher == "columnar":
        k = [ord(c) - 65 for c in key.upper() if "A" <= c <= "Z"]
        if len(k) < 2: raise ValueError("columnar needs a key word of 2+ letters")
        perm = sorted(range(len(k)), key=lambda i: (k[i], i))
        return txt(col_encrypt(p, perm))
    raise ValueError("unknown cipher " + cipher)


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser(prog="cipher_trainer.py", description="Break classical ciphers and show every step.")
    b = argparse.ArgumentParser(prog="cipher_trainer.py break"); b.add_argument("cipher", choices=["auto", "caesar", "atbash", "vigenere", "substitution", "columnar"])
    e = argparse.ArgumentParser(prog="cipher_trainer.py encrypt"); e.add_argument("cipher", choices=["caesar", "atbash", "vigenere", "substitution", "columnar"]); e.add_argument("--key", default="")
    for x in (b, e): x.add_argument("text", nargs="?"); x.add_argument("-f", "--file", help="read the text from a file (default: the text argument, else stdin)")
    b.add_argument("--json", action="store_true"); b.add_argument("--quiet", action="store_true", help="print only cipher, key and plaintext")
    b.add_argument("--maxlen", type=int, default=16, help="longest Vigenere key length to test"); b.add_argument("--maxwidth", type=int, default=8, help="widest columnar transposition to test")
    if not argv or argv[0] not in ("break", "encrypt"):
        ap.add_argument("command", choices=["break", "encrypt"]); ap.parse_args(argv or ["-h"]); return 2   # prints usage / error
    a = (b if argv[0] == "break" else e).parse_intermixed_args(argv[1:]); a.cmd = argv[0]
    text = Path(a.file).read_text(encoding="utf-8") if a.file else a.text if a.text is not None else sys.stdin.read()
    try:
        if a.cmd == "encrypt": print(encrypt(a.cipher, text, a.key)); return 0
        r = break_cipher(a.cipher, text, a.maxlen, a.maxwidth)
    except ValueError as ex:
        print("error:", ex, file=sys.stderr); return 2
    if a.json: print(json.dumps(r, indent=1)); return 0
    if not a.quiet: print("\n".join(r["steps"]) + "\n")
    print("cipher:    " + r["cipher"]); print("key:       " + (r["key"] or "(none)")); print("plaintext: " + r["plaintext"]); return 0


if __name__ == "__main__":
    sys.exit(main())
