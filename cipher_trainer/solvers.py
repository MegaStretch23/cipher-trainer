"""Solvers. Each one returns a dict {cipher, key, plaintext, score, steps} where `steps` is the list of lines the --explain mode prints.
Nothing here is random except the substitution / long-columnar hill climbs, which use random.Random(seed) so a run is reproducible."""
from __future__ import annotations
import itertools
import math
import random
import re
from collections import Counter

from . import ciphers as C
from .english import ALPHA, FREQ, IC_ENGLISH, IC_RANDOM, chi_squared, clean, counts, english_score, ic, trigram_score

ENGLISH_ORDER = "ETAOINSHRDLCUMWFGYPBVKJXQZ"


# ---------------------------------------------------------------- shared analysis
def freq_lines(text: str, top: int = 8) -> list:
    c = counts(text)
    n = sum(c.values())
    lines = [f"letter frequencies ({n} letters), top {top} vs English:"]
    for l, v in c.most_common(top):
        pct = 100.0 * v / n
        lines.append(f"  {l}  {v:4d}  {pct:5.1f}%  {'#' * int(round(pct * 2))}   (English {l}: {FREQ[l]:.1f}%)")
    return lines


def kasiski(text: str, max_len: int = 20, min_gram: int = 3) -> dict:
    """Distances between repeats of the same 3+-letter group; every factor 2..max_len of each distance gets one vote."""
    t = clean(text)
    seen: dict = {}
    dists = []
    for i in range(len(t) - min_gram + 1):
        seen.setdefault(t[i:i + min_gram], []).append(i)
    for k, pos in seen.items():
        for a, b in zip(pos, pos[1:]):
            dists.append((k, b - a))
    d3 = dists
    votes: Counter = Counter()
    for _, d in d3:
        for f in range(2, max_len + 1):
            if d % f == 0:
                votes[f] += 1
    return {"repeats": d3, "votes": votes}


def kasiski_lines(text: str, max_len: int = 20) -> tuple:
    k = kasiski(text, max_len)
    lines = []
    if not k["repeats"]:
        lines.append("Kasiski: no repeated 3-letter group found (text too short or key too long); rely on the IC table below")
        return lines, k
    ex = k["repeats"][:5]
    lines.append(f"Kasiski: {len(k['repeats'])} repeated 3-letter distances; examples " + ", ".join(f"{g} at distance {d}" for g, d in ex))
    top = k["votes"].most_common(5)
    lines.append("Kasiski factor votes (key length: votes): " + ", ".join(f"{f}: {v}" for f, v in top))
    return lines, k


def ic_by_length(text: str, max_len: int = 20) -> dict:
    t = clean(text)
    out = {}
    for L in range(1, min(max_len, max(1, len(t) // 3)) + 1):
        cols = [t[i::L] for i in range(L)]
        out[L] = sum(ic(c) for c in cols) / L
    return out


def analyze(text: str) -> dict:
    t = clean(text)
    steps = [f"input: {len(t)} letters"]
    steps += freq_lines(t)
    i = ic(t)
    steps.append(f"index of coincidence = {i:.4f}  (English ~{IC_ENGLISH}, random letters ~{IC_RANDOM:.4f})")
    chi = chi_squared(t)
    steps.append(f"chi-squared of letter counts vs English = {chi:.1f}  (about 25-60 = English-like letter counts for a few hundred letters; hundreds = not)")
    if i >= 0.058:
        steps.append("high IC: one fixed letter mapping (Caesar / Atbash / simple substitution) or a transposition (rail fence / columnar)")
        steps.append("  -> if chi-squared is also LOW the letters are English letters in a new ORDER (transposition); if chi-squared is high they were REPLACED (substitution)")
    elif i <= 0.047:
        steps.append("low IC: several alphabets are in use (Vigenere-like) or the text is too short to judge")
    else:
        steps.append("middle IC: a short Vigenere key, or a very short text")
    ks, _ = kasiski_lines(t)
    steps += ks
    return {"cipher": "analysis", "key": None, "plaintext": None, "score": None, "steps": steps, "ic": i, "chi2": chi}


# ---------------------------------------------------------------- restore formatting
def _restore(original: str, new_letters: str) -> str:
    """Put solved letters back into the original's spacing / punctuation / case when the cipher is letter-for-letter."""
    out, i = [], 0
    for ch in original:
        if ch.isalpha() and ch.isascii():
            r = new_letters[i]; i += 1
            out.append(r.lower() if ch.islower() else r)
        else:
            out.append(ch)
    return "".join(out)


# ---------------------------------------------------------------- Caesar
def break_caesar(text: str, **_) -> dict:
    t = clean(text)
    steps = ["Caesar: every letter moved by the same shift k (0-25). There are only 26 keys, so we test all of them with chi-squared."]
    steps += freq_lines(t, 5)
    steps.append("for each shift k we decrypt and compute chi-squared against English letter frequencies (lower = better):")
    rows = []
    for k in range(26):
        p = C.caesar(t, k, True)
        rows.append((chi_squared(p), k, p))
    rows.sort()
    for chi, k, p in rows[:4]:
        steps.append(f"  shift {k:2d}  chi2 {chi:8.1f}  {p[:40]}")
    chi, k, _ = rows[0]
    steps.append(f"best shift = {k} (letter {ALPHA[k]}), the runner-up chi2 is {rows[1][0]:.1f}, so the margin is {rows[1][0] / max(chi, 1e-9):.1f}x")
    plain = _restore(text, C.caesar(t, k, True))
    return {"cipher": "caesar", "key": k, "plaintext": plain, "score": english_score(plain), "steps": steps}


# ---------------------------------------------------------------- Atbash
def break_atbash(text: str, **_) -> dict:
    t = clean(text)
    steps = ["Atbash: A<->Z, B<->Y, ... a fixed substitution with NO key, so there is exactly one candidate."]
    steps += freq_lines(t, 5)
    p = C.atbash(t)
    steps.append(f"chi-squared as is: {chi_squared(t):.1f}; after mirroring the alphabet: {chi_squared(p):.1f}")
    steps.append(f"trigram score as is: {trigram_score(t):.2f}; mirrored: {trigram_score(p):.2f} (higher = more English)")
    plain = _restore(text, p)
    return {"cipher": "atbash", "key": None, "plaintext": plain, "score": english_score(plain), "steps": steps}


# ---------------------------------------------------------------- Vigenere
def break_vigenere(text: str, max_key: int = 20, **_) -> dict:
    t = clean(text)
    steps = ["Vigenere: a repeating keyword picks a different Caesar shift for each position. Plan: (1) find the key length, (2) solve each column as a Caesar."]
    steps.append(f"step 1a  index of coincidence of the whole text = {ic(t):.4f} (English {IC_ENGLISH}, random {IC_RANDOM:.4f}): low means several alphabets")
    ks, kas = kasiski_lines(t, max_key)
    steps += ["step 1b  " + ks[0]] + ["         " + x for x in ks[1:]]
    table = ic_by_length(t, max_key)
    steps.append("step 1c  average IC of the columns if the key length were L (English-like columns are near 0.066):")
    best = max(table.values())
    for L, v in table.items():
        steps.append(f"         L={L:2d}  IC {v:.4f}  {'#' * int(round(v * 400))}")
    # IC and Kasiski shortlist the lengths; short texts make the IC of long keys noisy (7-letter columns), so every shortlisted
    # length is also tried end to end and judged by how English the decrypted text looks.
    def solve_cols(L):
        k = []
        for i in range(L):
            col = t[i::L]
            sc = sorted((chi_squared(C.caesar(col, sh, True)), sh) for sh in range(26))
            k.append((ALPHA[sc[0][1]], sc[0][0], sc[1][0], len(col)))
        return k
    short = [L for L, v in table.items() if v >= best - 0.012 or v >= 0.055 or (kas["votes"] and L in dict(kas["votes"].most_common(3)))]
    short = [L for L in short if len(t) // L >= 6] or [min(table, key=lambda x: -table[x])]
    steps.append(f"step 1d  shortlist (IC near the best, IC >= 0.055 or a top Kasiski vote, at least 6 letters per column): {short}")
    scored = []
    for L in short:
        kk = "".join(x[0] for x in solve_cols(L))
        sc = english_score(C.vigenere(t, kk, True))
        scored.append((sc, L, kk))
        steps.append(f"         try L={L:2d}: key {kk}  English score {sc:6.3f}")
    top = max(scored)[0]
    sc0, L, kk = min([x for x in scored if x[0] >= top - 0.03], key=lambda x: x[1])
    steps.append(f"         key length = {L} (smallest length within 0.03 of the best score {top:.3f})")
    key = []
    steps.append(f"step 2   the {L} columns, each solved as a Caesar cipher with chi-squared:")
    for i, (ch, c1, c2, n) in enumerate(solve_cols(L)):
        key.append(ch)
        steps.append(f"         column {i + 1} ({n} letters): best shift {ord(ch) - 65:2d} = '{ch}' chi2 {c1:7.1f} (next best {c2:.1f})")
    key = "".join(key)
    # reduce a repeated key such as KEYKEY to KEY
    for d in range(1, len(key)):
        if len(key) % d == 0 and key[:d] * (len(key) // d) == key:
            steps.append(f"         key {key} is {key[:d]} repeated; shortest form {key[:d]}"); key = key[:d]; break
    steps.append(f"key = {key}")
    plain = C.vigenere(text, key, True)
    return {"cipher": "vigenere", "key": key, "plaintext": plain, "score": english_score(plain), "steps": steps}


# ---------------------------------------------------------------- substitution
def _apply(table: str, t: str) -> str:
    """table[i] = plaintext letter for ciphertext letter ALPHA[i]"""
    m = str.maketrans(ALPHA, table)
    return t.translate(m)


def break_substitution(text: str, seed: int = 1, restarts: int = 6, **_) -> dict:
    t = clean(text)
    steps = ["Simple substitution: one fixed mapping of the 26 letters (26! keys, too many to try), so we climb: start from a guess, swap two letters, keep the swap if the English score rises."]
    steps += freq_lines(t, 8)
    order = [l for l, _ in counts(t).most_common()] + [l for l in ALPHA if l not in counts(t)]
    init = [""] * 26
    for cl, pl in zip(order, ENGLISH_ORDER):
        init[ord(cl) - 65] = pl
    start = "".join(init)
    steps.append("step 1  rank ciphertext letters by frequency and line them up with English order ETAOINSHRDLCUMWFGYPBVKJXQZ:")
    steps.append("        " + " ".join(f"{c}->{p}" for c, p in zip(order[:10], ENGLISH_ORDER)))
    steps.append(f"        score of that first guess: {trigram_score(_apply(start, t)):.3f}   {_apply(start, t)[:40]}")
    rng = random.Random(seed)
    best_tab, best_sc = start, trigram_score(_apply(start, t))
    steps.append(f"step 2  hill climb with a cooling schedule: propose a swap of two table entries, keep it if the trigram score rises, and keep a worse one with probability exp(drop/T) while T cools "
                 f"(escapes dead ends); {restarts} restarts (seed {seed}; the first starts from the frequency guess, the others from shuffles), each finished by plain greedy swaps")
    iters = 8000
    for r in range(restarts):
        tab = list(start) if r == 0 else rng.sample(ALPHA, 26)
        t0 = 0.02 if r == 0 else 0.08
        cur = trigram_score(_apply("".join(tab), t))
        for k in range(iters):
            temp = t0 * (0.002 / t0) ** (k / iters)
            i, j = rng.sample(range(26), 2)
            tab[i], tab[j] = tab[j], tab[i]
            sc = trigram_score(_apply("".join(tab), t))
            if sc >= cur or rng.random() < math.exp((sc - cur) / temp):
                cur = sc
            else:
                tab[i], tab[j] = tab[j], tab[i]
        improved, passes = True, 0
        while improved and passes < 40:
            improved = False
            passes += 1
            for i in range(25):
                for j in range(i + 1, 26):
                    tab[i], tab[j] = tab[j], tab[i]
                    sc = trigram_score(_apply("".join(tab), t))
                    if sc > cur + 1e-12:
                        cur = sc; improved = True
                    else:
                        tab[i], tab[j] = tab[j], tab[i]
        steps.append(f"        restart {r + 1}: score {cur:.3f}  {_apply(''.join(tab), t)[:40]}")
        if cur > best_sc:
            best_sc, best_tab = cur, "".join(tab)
    # final polish: same swap search, but judged by the full English score (trigrams + common-word coverage)
    tab = list(best_tab)
    cur = english_score(_apply("".join(tab), t))
    improved = True
    while improved:
        improved = False
        for i in range(25):
            for j in range(i + 1, 26):
                tab[i], tab[j] = tab[j], tab[i]
                sc = english_score(_apply("".join(tab), t))
                if sc > cur + 1e-12:
                    cur, improved = sc, True
                else:
                    tab[i], tab[j] = tab[j], tab[i]
    if "".join(tab) != best_tab:
        steps.append(f"step 2b polish with trigram + common-word score: swapped to {''.join(tab)}")
        best_tab = "".join(tab); best_sc = trigram_score(_apply(best_tab, t))
    plain_letters = _apply(best_tab, t)
    key = "".join(ALPHA[best_tab.index(p)] if p in best_tab else "?" for p in ALPHA)   # key[i] = cipher letter for plain letter i
    steps.append(f"step 3  best score {best_sc:.3f}; plaintext letter for each cipher letter A..Z: {best_tab}")
    steps.append(f"key (plain A..Z -> cipher letters) = {key}")
    plain = _restore(text, plain_letters)
    return {"cipher": "substitution", "key": key, "plaintext": plain, "score": english_score(plain), "steps": steps}


# ---------------------------------------------------------------- rail fence
def break_railfence(text: str, max_rails: int = 12, **_) -> dict:
    t = clean(text)
    steps = ["Rail fence: the letters are written in a zigzag over R rails and read rail by rail. The letters are only reordered, so the letter counts stay English."]
    steps.append(f"step 1  IC {ic(t):.4f} and chi-squared {chi_squared(t):.1f} look like English letters in the wrong order: a transposition")
    steps.append("step 2  try R = 2.. and score each decryption with trigram log-probability (higher = more English):")
    rows = []
    for R in range(2, min(max_rails, max(2, len(t) - 1)) + 1):
        p = C.railfence(t, R, True)
        rows.append((trigram_score(p), R, p))
    for s, R, p in rows:
        steps.append(f"        rails {R:2d}  score {s:6.3f}  {p[:40]}")
    s, R, p = max(rows)
    steps.append(f"best = {R} rails")
    return {"cipher": "railfence", "key": R, "plaintext": p, "score": english_score(p), "steps": steps}


# ---------------------------------------------------------------- columnar
def break_columnar(text: str, max_width: int = 10, seed: int = 1, **_) -> dict:
    t = clean(text)
    steps = ["Columnar transposition: the plaintext is written in rows under a keyword; the columns are read off in the keyword's alphabetical order. Letter counts stay English."]
    steps.append(f"step 1  IC {ic(t):.4f} and chi-squared {chi_squared(t):.1f}: English letters in the wrong order")
    steps.append("step 2  for each width W: widths up to 7 try all W! column orders; wider ones hill-climb on column swaps and moves (seeded). Score = trigram log-probability:")
    rng = random.Random(seed)
    results = []
    for W in range(2, min(max_width, max(2, len(t) // 2)) + 1):
        if W <= 7:
            best = max(((trigram_score(C.columnar(t, list(p), True)), list(p)) for p in itertools.permutations(range(W))), key=lambda x: x[0])
            mode = "all orders"
        else:
            best = (-99.0, None)
            for r in range(12):
                o = list(range(W)); rng.shuffle(o)
                cur = trigram_score(C.columnar(t, o, True))
                imp = True
                while imp:
                    imp = False
                    for i in range(W):
                        for j in range(W):
                            if i == j:
                                continue
                            for mv in ("swap", "move"):
                                if mv == "swap" and i > j:
                                    continue
                                c = list(o)
                                if mv == "swap":
                                    c[i], c[j] = c[j], c[i]
                                else:
                                    c.insert(j, c.pop(i))
                                sc = trigram_score(C.columnar(t, c, True))
                                if sc > cur + 1e-12:
                                    cur, o, imp = sc, c, True
                if cur > best[0]:
                    best = (cur, list(o))
            mode = "hill climb"
        s, o = best
        results.append((s, W, o))
        steps.append(f"        width {W:2d} ({mode:10s}) best score {s:6.3f}  {C.columnar(t, o, True)[:36]}")
    # prefer the smallest width unless a larger one is clearly better
    top = max(results)
    near = [r for r in results if r[0] >= top[0] - 0.03]
    s, W, o = min(near, key=lambda r: r[1])
    steps.append(f"best = width {W}, read order of columns (1-based) {[x + 1 for x in o]}")
    kw_note = ",".join(str(x + 1) for x in o)
    steps.append(f"key = {kw_note}  (column numbers in the order they were read off the grid)")
    return {"cipher": "columnar", "key": kw_note, "plaintext": C.columnar(t, o, True), "score": english_score(C.columnar(t, o, True)), "steps": steps}


SOLVERS = {"caesar": break_caesar, "atbash": break_atbash, "vigenere": break_vigenere, "substitution": break_substitution,
           "railfence": break_railfence, "columnar": break_columnar}


def verdict(score: float) -> str:
    if score >= -2.6: return "reads as English"
    if score >= -3.0: return "possibly English (short or noisy text)"
    return "not English: wrong cipher or too little text"


def solve(text: str, cipher: str = "auto", **kw) -> dict:
    if cipher != "auto":
        if cipher not in SOLVERS:
            raise ValueError(f"unknown cipher {cipher!r}; choose one of {', '.join(SOLVERS)} or auto")
        r = SOLVERS[cipher](text, **kw)
        r["verdict"] = verdict(r["score"])
        return r
    a = analyze(text)
    steps = ["AUTO: diagnose first, then run every solver and keep the most English-looking result."] + a["steps"]
    steps.append("trying every cipher; final score = trigram log-probability + small common-word bonus (higher is better):")
    found = []
    for name, fn in SOLVERS.items():
        try:
            r = fn(text, **kw)
        except ValueError as e:
            steps.append(f"  {name:12s} skipped: {e}"); continue
        found.append(r)
        steps.append(f"  {name:12s} score {r['score']:6.3f}  key {r['key']}  {clean(r['plaintext'])[:36]}")
    best = max(found, key=lambda r: r["score"])
    steps.append(f"winner: {best['cipher']} ({verdict(best['score'])})")
    return {**best, "steps": steps + ["", "--- the winning solver's own steps ---"] + best["steps"], "verdict": verdict(best["score"])}
