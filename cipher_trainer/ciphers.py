"""Encrypt / decrypt for the six classical ciphers. Letters only are transformed; case and non-letters are kept where the
cipher works letter by letter (Caesar, Atbash, Vigenere, substitution). The two transpositions (rail fence, columnar) work
on the letters only and return upper-case text without spaces, because moving letters across word gaps makes the gaps meaningless."""
from __future__ import annotations
from .english import ALPHA, clean


def _shift_char(ch: str, k: int) -> str:
    if "A" <= ch <= "Z":
        return chr((ord(ch) - 65 + k) % 26 + 65)
    if "a" <= ch <= "z":
        return chr((ord(ch) - 97 + k) % 26 + 97)
    return ch


def caesar(text: str, key: int, decrypt: bool = False) -> str:
    k = -key if decrypt else key
    return "".join(_shift_char(c, k) for c in text)


def atbash(text: str, key=None, decrypt: bool = False) -> str:
    out = []
    for c in text:
        if "A" <= c <= "Z":
            out.append(chr(90 - (ord(c) - 65)))
        elif "a" <= c <= "z":
            out.append(chr(122 - (ord(c) - 97)))
        else:
            out.append(c)
    return "".join(out)


def vigenere(text: str, key: str, decrypt: bool = False) -> str:
    ks = [ord(c) - 65 for c in clean(key)]
    if not ks:
        raise ValueError("Vigenere key needs at least one letter")
    out, i = [], 0
    for c in text:
        if c.isalpha() and c.isascii():
            k = -ks[i % len(ks)] if decrypt else ks[i % len(ks)]
            out.append(_shift_char(c, k)); i += 1
        else:
            out.append(c)
    return "".join(out)


def check_substitution_key(key: str) -> str:
    k = clean(key)
    if len(k) != 26 or set(k) != set(ALPHA):
        raise ValueError("substitution key must be a permutation of A-Z (26 letters, each once); plain letter A maps to key[0], B to key[1], ...")
    return k


def substitution(text: str, key: str, decrypt: bool = False) -> str:
    k = check_substitution_key(key)
    table = {ALPHA[i]: k[i] for i in range(26)}
    if decrypt:
        table = {v: a for a, v in table.items()}
    out = []
    for c in text:
        if "A" <= c <= "Z":
            out.append(table[c])
        elif "a" <= c <= "z":
            out.append(table[c.upper()].lower())
        else:
            out.append(c)
    return "".join(out)


def _rail_pattern(n: int, rails: int) -> list:
    if rails < 2:
        raise ValueError("rail fence needs at least 2 rails")
    pat, r, d = [], 0, 1
    for _ in range(n):
        pat.append(r)
        if rails > 1:
            if r == 0: d = 1
            elif r == rails - 1: d = -1
            r += d
    return pat


def railfence(text: str, key: int, decrypt: bool = False) -> str:
    t = clean(text)
    pat = _rail_pattern(len(t), int(key))
    order = sorted(range(len(t)), key=lambda i: (pat[i], i))   # positions in the order they are read off the rails
    if not decrypt:
        return "".join(t[i] for i in order)
    out = [""] * len(t)
    for pos, i in enumerate(order):
        out[i] = t[pos]
    return "".join(out)


def parse_columnar_key(key) -> list:
    """A keyword (ZEBRAS) or comma-separated digits (1,3,2) -> read order: the list of column indexes (0-based) in the order they are read off."""
    if isinstance(key, (list, tuple)):
        order = [int(x) for x in key]
    elif "," in str(key) or str(key).strip().isdigit():
        order = [int(x) - 1 for x in str(key).replace(" ", "").split(",") if x != ""]
    else:
        w = clean(str(key))
        order = [i for _, i in sorted((ch, i) for i, ch in enumerate(w))]   # ties broken left to right
    if sorted(order) != list(range(len(order))) or len(order) < 2:
        raise ValueError("columnar key must be a keyword of 2+ letters or a permutation such as 3,1,2")
    return order


def columnar(text: str, key, decrypt: bool = False) -> str:
    """Write the letters in rows under the key, then read the columns in the key order."""
    order = parse_columnar_key(key)
    t = clean(text)
    w = len(order)
    n = len(t)
    full, extra = divmod(n, w)
    # column c holds full+1 letters if c < extra else full letters
    lens = [full + (1 if c < extra else 0) for c in range(w)]
    if not decrypt:
        cols = {c: t[c::w] for c in range(w)}
        return "".join(cols[c] for c in order)
    cols, pos = {}, 0
    for c in order:
        cols[c] = t[pos:pos + lens[c]]; pos += lens[c]
    return "".join(cols[c][r] for r in range(full + (1 if extra else 0)) for c in range(w) if r < len(cols[c]))
