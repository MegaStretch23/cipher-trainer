"""Cryptanalysis solvers. Every solver returns a Result whose `steps` explain, in order, what was
measured and why the next move was made. Standard library only."""
from __future__ import annotations
import itertools, random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from . import ciphers as C
from .stats import ALPHA, ENGLISH_FREQ, ENGLISH_ORDER, chi2, ic, letters, per_char, score

ACCEPT = -1.45        # per-character model score at or above which a decrypt is accepted as English
MAX_TVD = 0.25        # letter-frequency distance from English allowed in an accepted decrypt (short true English reaches ~0.16)
HIGH = -1.30          # "confident" band, reported to the user


@dataclass
class Step:
    title: str
    lines: list[str] = field(default_factory=list)


@dataclass
class Result:
    cipher: str
    key: str
    plaintext: str            # display form (case and punctuation kept where the cipher keeps them)
    quality: float            # per-character model score of the letters
    steps: list[Step] = field(default_factory=list)
    underdetermined: bool = False     # more free key parameters than the text can pin down (e.g. substitution under 100 letters)

    @property
    def accepted(self) -> bool:
        # the model score alone can be gamed by repetitive pseudo-text, so the letter distribution must also look like English
        return not self.underdetermined and self.quality >= ACCEPT and tvd(self.plaintext) <= MAX_TVD

    def as_dict(self) -> dict:
        return {"cipher": self.cipher, "key": self.key, "plaintext": self.plaintext, "quality": round(self.quality, 3),
                "accepted": self.accepted, "steps": [{"title": s.title, "lines": s.lines} for s in self.steps]}


def _fmt(x: float) -> str:
    return f"{x:.3f}"


def _preview(s: str, n: int = 60) -> str:
    return s[:n] + ("..." if len(s) > n else "")


# ---------------------------------------------------------------- measurements ----------------
def frequency_table(text: str, top: int = 8) -> Step:
    t = letters(text)
    c = Counter(t)
    n = len(t)
    rows = [f"{a}: {c[a]:3d} ({100 * c[a] / n:4.1f}%)" for a, _ in c.most_common(top)]
    exp = ", ".join(f"{a} {ENGLISH_FREQ[a]:.1f}%" for a in ENGLISH_ORDER[:top])
    return Step("Frequency analysis", [f"{n} letters. Most common ciphertext letters: " + "; ".join(rows),
                                       f"English is led by: {exp}"])


def tvd(text: str) -> float:
    """Total-variation distance between the letter distribution and English (0 = identical)."""
    t = letters(text)
    c = Counter(t)
    return sum(abs(c.get(a, 0) / len(t) - ENGLISH_FREQ[a] / 100) for a in ALPHA) / 2


def friedman_length(t: str) -> float | None:
    n = len(t)
    d = (n - 1) * ic(t) - 0.0385 * n + 0.0658
    return 0.0273 * n / d if d > 0 else None


def kasiski(t: str, size: int = 3) -> tuple[list[tuple[str, list[int]]], Counter]:
    pos = defaultdict(list)
    for i in range(len(t) - size + 1):
        pos[t[i:i + size]].append(i)
    reps, fac = [], Counter()
    for g, p in pos.items():
        if len(p) < 2:
            continue
        dists = [b - a for a, b in zip(p, p[1:])]
        reps.append((g, dists))
        for d in dists:
            for f in range(2, 21):
                if d % f == 0:
                    fac[f] += 1
    reps.sort(key=lambda r: -len(r[1]))
    return reps, fac


# ---------------------------------------------------------------- shift family ----------------
def solve_caesar(text: str) -> Result:
    t = letters(text)
    rows = sorted(((chi2(C.caesar_decrypt(t, s)), s) for s in range(26)))
    best = rows[0][1]
    steps = [frequency_table(text),
             Step("Chi-squared scoring of all 26 shifts",
                  ["For each shift, decrypt and measure the chi-squared distance of the letter counts from English (lower is better):"]
                  + [f"shift {s:2d} -> chi2 {x:8.1f}   {_preview(C.caesar_decrypt(t, s), 28)}" for x, s in rows[:4]]
                  + [f"Shift {best} is {rows[1][0] / max(rows[0][0], 1e-9):.1f}x better than the runner-up."])]
    pt = C.caesar_decrypt(text, best)
    steps.append(Step("Result", [f"Caesar shift {best} (each letter moved {best} places forward by the encryptor; key letter {ALPHA[best]})."]))
    return Result("caesar", str(best), pt, per_char(pt), steps)


def solve_atbash(text: str) -> Result:
    pt = C.atbash(text)
    return Result("atbash", "-", pt, per_char(pt), [Step("Atbash", ["Atbash has no key: A<->Z, B<->Y, ... Applying it once to the ciphertext gives: " + _preview(pt)])])


def solve_affine(text: str) -> Result:
    t = letters(text)
    cands = sorted(((score(C.affine_decrypt(t, a, b)), a, b) for a in C.AFFINE_A for b in range(26)), reverse=True)
    _, a, b = cands[0]
    pt = C.affine_decrypt(text, a, b)
    steps = [frequency_table(text),
             Step("Affine key search", ["Affine is E(x) = a*x + b mod 26 with a coprime to 26 (12 choices) and b free (26), so only 312 keys exist. All were scored with the language model (log10 probability, higher is better):"]
                  + [f"a={x[1]:2d} b={x[2]:2d} -> {x[0]:8.1f}   {_preview(C.affine_decrypt(t, x[1], x[2]), 28)}" for x in cands[:4]]),
             Step("Result", [f"Affine key a={a}, b={b}."])]
    return Result("affine", f"{a},{b}", pt, per_char(pt), steps)


# ---------------------------------------------------------------- Vigenere --------------------
def _col_key(t: str, L: int) -> list[int]:
    return [min(range(26), key=lambda s: chi2(C.caesar_decrypt(t[i::L], s))) for i in range(L)]


def _dec(t: str, shifts: list[int]) -> str:
    return C.vigenere_decrypt(t, "".join(ALPHA[s] for s in shifts))


def _period(key: str) -> str:
    for p in range(1, len(key) + 1):
        if len(key) % p == 0 and key[:p] * (len(key) // p) == key:
            return key[:p]
    return key


def solve_vigenere(text: str) -> Result:
    t = letters(text)
    n = len(t)
    steps = [frequency_table(text), Step("Index of coincidence", [f"IC = {ic(t):.4f}. English is about 0.0667, uniformly random letters 0.0385. A value between them means several Caesar alphabets are mixed: a polyalphabetic cipher such as Vigenere."])]
    reps, fac = kasiski(t)
    if reps:
        steps.append(Step("Kasiski examination", [f"{len(reps)} repeated 3-letter groups. Distances between repeats: " + "; ".join(f"{g}: {d}" for g, d in reps[:4]),
                                                  "Key lengths dividing the most distances: " + ", ".join(f"{f} ({c})" for f, c in fac.most_common(5))]))
    else:
        steps.append(Step("Kasiski examination", ["No repeated 3-letter groups: the text is too short for Kasiski, relying on IC alone."]))
    fr = friedman_length(t)
    steps.append(Step("Friedman estimate", [f"L ~ 0.0273*n / ((n-1)*IC - 0.0385*n + 0.0658) = {fr:.1f}" if fr else "Friedman formula not defined for this IC (denominator <= 0)."]))
    maxL = max(2, min(20, n // 12))   # fewer than ~12 letters per key letter cannot determine a key; it only overfits
    col = [(sum(ic(t[i::L]) for i in range(L)) / L, L) for L in range(1, maxL + 1)]
    steps.append(Step("Average column IC per key length", ["If the key length is right, every column is a Caesar shift and its IC rises toward 0.0667:"]
                      + ["  ".join(f"L={L}:{v:.3f}" for v, L in col[:12])]))
    tops = sorted({L for _, L in sorted(col, reverse=True)[:5]} | ({round(fr)} if fr and 1 <= round(fr) <= maxL else set()))
    trials = []
    for L in tops:
        sh = _col_key(t, L)
        trials.append((per_char(_dec(t, sh)), L, sh))
    best_pc = max(x[0] for x in trials)
    pc, L, sh = min((x for x in trials if x[0] >= best_pc - 0.03), key=lambda x: x[1])
    steps.append(Step("Per-column chi-squared shifts", ["Candidate lengths tried (model score per char): " + ", ".join(f"L={x[1]}: {_fmt(x[0])}" for x in trials),
                                                         f"Smallest length within 0.03 of the best score: L={L}. Each column's shift is the one with the lowest chi-squared; key letters: " + "".join(ALPHA[s] for s in sh)]))
    changed = True
    while changed:       # polish: re-tune each key letter with the language model (helps short texts)
        changed = False
        for i in range(L):
            cur = score(_dec(t, sh))
            for s in range(26):
                if s == sh[i]:
                    continue
                tr = sh[:i] + [s] + sh[i + 1:]
                if score(_dec(t, tr)) > cur + 1e-9:
                    sh, cur, changed = tr, score(_dec(t, tr)), True
    key = _period("".join(ALPHA[s] for s in sh))
    pt = C.vigenere_decrypt(text, key)
    steps.append(Step("Result", [f"Vigenere key {key} (length {len(key)}) after language-model polish of each key letter."]))
    return Result("vigenere", key, pt, per_char(pt), steps)


# ---------------------------------------------------------------- substitution ----------------
def solve_substitution(text: str, restarts: int = 12, seed: int = 1234) -> Result:
    t = letters(text)
    rng = random.Random(seed)
    cnt = Counter(t)
    cipher_order = sorted(ALPHA, key=lambda c: (-cnt[c], c))
    init = [""] * 26
    for cl, pl in zip(cipher_order, ENGLISH_ORDER):
        init[ord(cl) - 65] = pl
    steps = [frequency_table(text), Step("Index of coincidence", [f"IC = {ic(t):.4f}: close to English, but the letters are not the ones English uses most, so one fixed alphabet was swapped for another (monoalphabetic substitution)."]),
             Step("Initial guess by frequency rank", ["Rank the ciphertext letters by count and give them English's letters in order of frequency (E T A O I N S H R ...):",
                                                       "cipher " + ALPHA + "\nplain  " + "".join(init)])]

    def dec(k: list[str]) -> str:
        return t.translate(str.maketrans(ALPHA, "".join(k)))

    def climb(k: list[str], log: bool):
        cur = score(dec(k))
        sweep = 0
        while True:
            sweep += 1
            improved = False
            for i in range(25):
                for j in range(i + 1, 26):
                    k[i], k[j] = k[j], k[i]
                    s = score(dec(k))
                    if s > cur + 1e-9:
                        cur, improved = s, True
                    else:
                        k[i], k[j] = k[j], k[i]
            if log:
                steps[-1].lines.append(f"sweep {sweep}: model score {cur:8.1f}   {_preview(dec(k), 50)}")
            if not improved:
                return k, cur

    steps.append(Step("Hill-climbing on swaps", ["Swap two plaintext letters in the key; keep the swap if the quadgram-based log-probability of the decrypt rises; repeat until a full sweep changes nothing."]))
    best_k, best_s = climb(list(init), True)
    for r in range(restarts):
        k = list(best_k)
        for _ in range(4 + r):
            i, j = rng.sample(range(26), 2)
            k[i], k[j] = k[j], k[i]
        k, s = climb(k, False)
        if s > best_s + 1e-9:
            best_k, best_s = k, s
            steps[-1].lines.append(f"restart {r + 1}: shook the key with {4 + r} random swaps, climbed again -> new best {s:.1f}")
    steps[-1].lines.append(f"Kept the best of {restarts + 1} climbs ({restarts} restarts from perturbed keys).")
    enc_key = "".join(ALPHA[best_k.index(a)] for a in ALPHA)      # plain A..Z -> cipher letter
    pt = C.substitution_decrypt(text, enc_key)
    steps.append(Step("Result", [f"Substitution key (plain A..Z -> cipher): {enc_key}"]
                      + (["Under 100 letters a 26-letter key is not determined by the text: random letters can also be fitted to look like English, so this answer is never marked accepted."] if len(t) < 100 else [])))
    return Result("substitution", enc_key, pt, per_char(pt), steps, underdetermined=len(t) < 100)


# ---------------------------------------------------------------- transposition ---------------
def solve_railfence(text: str) -> Result:
    t = letters(text)
    cands = sorted(((score(C.railfence_decrypt(t, r)), r) for r in range(2, min(len(t) - 1, 12) + 1)), reverse=True)
    r = cands[0][1]
    pt = C.railfence_decrypt(t, r)
    steps = [Step("Why a transposition", [f"Letter distribution is {tvd(t):.2f} (total-variation) from English: the letters themselves are English's, only their order is scrambled."]),
             Step("Rail fence: try every rail count", ["Rails 2..12, scoring the decrypt with the language model:"] + [f"{x[1]:2d} rails -> {x[0]:8.1f}   {_preview(C.railfence_decrypt(t, x[1]), 28)}" for x in cands[:4]]),
             Step("Result", [f"{r} rails. Spaces and punctuation are not recoverable from a transposition of letters."])]
    return Result("railfence", str(r), pt, per_char(pt), steps)


def solve_columnar(text: str) -> Result:
    t = letters(text)
    n = len(t)
    steps = [Step("Why a transposition", [f"Letter distribution is {tvd(t):.2f} (total-variation) from English: only the order is scrambled."])]
    best = (-1e18, 0, [])
    rng = random.Random(99)
    lines = ["Widths 2..7: every column order tried (at most 5040 each). Widths 8..10: random-restart swap climbing."]
    per_width = []
    for w in range(2, min(10, n // 2) + 1):
        if w <= 7:
            wb = max(((score(C.columnar_decrypt_order(t, list(o))), list(o)) for o in itertools.permutations(range(w))), key=lambda x: x[0])
        else:
            wb = (-1e18, [])
            for _ in range(8):
                o = list(range(w)); rng.shuffle(o)
                cur = score(C.columnar_decrypt_order(t, o))
                ok = True
                while ok:
                    ok = False
                    for i in range(w):
                        for j in range(w):
                            if i == j:
                                continue
                            q = o[:]; q.insert(j, q.pop(i))
                            s = score(C.columnar_decrypt_order(t, q))
                            if s > cur + 1e-9:
                                o, cur, ok = q, s, True
                if cur > wb[0]:
                    wb = (cur, o)
        per_width.append((wb[0], w))
        if wb[0] > best[0]:
            best = (wb[0], w, wb[1])
    lines += [f"width {w:2d} -> best {s:8.1f}" for s, w in sorted(per_width, reverse=True)[:4]]
    steps.append(Step("Search width and column order", lines))
    _, w, order = best
    pt = C.columnar_decrypt_order(t, order)
    # express the order as a keyword: rank of each column
    rank = [order.index(c) for c in range(w)]
    kw = "".join(ALPHA[r] for r in rank)
    steps.append(Step("Result", [f"{w} columns, read in order {[c + 1 for c in order]} (equivalent keyword {kw})."]))
    return Result("columnar", kw, pt, per_char(pt), steps)


SOLVERS = {"caesar": solve_caesar, "atbash": solve_atbash, "affine": solve_affine, "vigenere": solve_vigenere,
           "substitution": solve_substitution, "railfence": solve_railfence, "columnar": solve_columnar}


# ---------------------------------------------------------------- the trainer -----------------
def identify(text: str) -> tuple[Step, list[str]]:
    t = letters(text)
    i, d = ic(t), tvd(t)
    lines = [f"Letters: {len(t)}   IC: {i:.4f}   distance of letter frequencies from English (total variation): {d:.2f}"]
    if i >= 0.058 and d >= 0.17:
        lines.append("IC is English-like but the frequencies are not: each plaintext letter always maps to the same ciphertext letter -> monoalphabetic substitution (Caesar, Atbash, affine or general substitution).")
        order = ["caesar", "atbash", "affine", "substitution"]
    elif i >= 0.058:
        lines.append("Both IC and frequencies look English: the letters are English's own, only reordered -> transposition (rail fence or columnar).")
        order = ["railfence", "columnar"]
    elif i <= 0.050:
        lines.append("IC is well below English: letter counts are flattened by mixing several alphabets -> polyalphabetic (Vigenere family).")
        order = ["vigenere"]
    else:
        lines.append("IC sits in the grey zone (short text or mixed signals): trying every family, cheapest first.")
        order = ["caesar", "atbash", "affine", "vigenere", "railfence", "columnar", "substitution"]
    lines.append("Attack order: " + ", ".join(order))
    return Step("Identify the cipher family", lines), order


def solve(text: str, cipher: str = "auto") -> tuple[Result, list[Step], list[Result]]:
    """Returns (best result, trainer steps, every Result tried). cipher='auto' runs the identify-then-attack ladder."""
    t = letters(text)
    if len(t) < 20:
        raise ValueError(f"need at least 20 letters of ciphertext, got {len(t)}")
    if cipher != "auto":
        r = SOLVERS[cipher](text)
        return r, list(r.steps), [r]
    head, order = identify(text)
    trail: list[Step] = [head]
    tried: list[Result] = []
    already = per_char(text)
    if already >= ACCEPT:
        r = Result("none", "-", text, already, [Step("Already readable", [f"Model score {_fmt(already)} per char is English-like: nothing to break."])])
        return r, trail + r.steps, [r]
    for name in order:
        r = SOLVERS[name](text)
        tried.append(r)
        trail.append(Step(f"Attack: {name}", [f"model score {_fmt(r.quality)} per char (English ~ -1.1, random ~ -2.7, accept at {ACCEPT})"] + [f"[{s.title}] " + " | ".join(s.lines) for s in r.steps if s.title != "Result"]
                          + [f"Accepted: {name}." if r.accepted else "Rejected: not English."]))
        if r.accepted:
            trail.append(Step("Conclusion", r.steps[-1].lines + [f"Decrypt: {_preview(r.plaintext, 100)}", f"Confidence: {'high' if r.quality >= HIGH else 'medium'} (score {_fmt(r.quality)})"]))
            return r, trail, tried
    for name in SOLVERS:       # brute-force fallback: everything not yet tried
        if name not in {x.cipher for x in tried}:
            tried.append(SOLVERS[name](text))
    best = max(tried, key=lambda r: r.quality)
    trail.append(Step("Brute-force fallback", ["No attack reached the acceptance score. Ran every solver and kept the highest-scoring decrypt: " + ", ".join(f"{r.cipher} {_fmt(r.quality)}" for r in sorted(tried, key=lambda r: -r.quality)),
                                                f"Best guess: {best.cipher}, key {best.key}. LOW CONFIDENCE (score {_fmt(best.quality)}): text may be too short or use an unsupported cipher."]))
    return best, trail, tried
