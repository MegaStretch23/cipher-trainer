"""Encrypt / decrypt for seven classical ciphers. All functions work on letters; case and
punctuation are kept by the substitution-type ciphers (caesar, vigenere, atbash, affine,
substitution) and dropped by the transposition ciphers (rail fence, columnar)."""
from __future__ import annotations
from math import gcd
from .stats import ALPHA, letters

AFFINE_A = [a for a in range(1, 26, 2) if a != 13]   # the 12 multipliers coprime with 26


def _shift_map(text: str, fn) -> str:
    out = []
    for ch in text:
        if "A" <= ch <= "Z":
            out.append(chr(65 + fn(ord(ch) - 65)))
        elif "a" <= ch <= "z":
            out.append(chr(97 + fn(ord(ch) - 97)))
        else:
            out.append(ch)
    return "".join(out)


# ---- Caesar -------------------------------------------------------------------------------
def caesar_encrypt(text: str, shift: int) -> str:
    return _shift_map(text, lambda x: (x + shift) % 26)


def caesar_decrypt(text: str, shift: int) -> str:
    return caesar_encrypt(text, -shift)


# ---- Atbash -------------------------------------------------------------------------------
def atbash(text: str) -> str:
    return _shift_map(text, lambda x: 25 - x)


# ---- Affine -------------------------------------------------------------------------------
def affine_encrypt(text: str, a: int, b: int) -> str:
    if gcd(a, 26) != 1:
        raise ValueError(f"affine a={a} must be coprime with 26 (one of {AFFINE_A + [1]})")
    return _shift_map(text, lambda x: (a * x + b) % 26)


def affine_decrypt(text: str, a: int, b: int) -> str:
    if gcd(a, 26) != 1:
        raise ValueError(f"affine a={a} must be coprime with 26")
    inv = pow(a, -1, 26)
    return _shift_map(text, lambda x: (inv * (x - b)) % 26)


# ---- Vigenere -----------------------------------------------------------------------------
def _key_shifts(key: str) -> list[int]:
    k = [ord(c) - 65 for c in key.upper() if "A" <= c <= "Z"]
    if not k:
        raise ValueError("vigenere key needs at least one letter")
    return k


def vigenere_encrypt(text: str, key: str, sign: int = 1) -> str:
    k, i, out = _key_shifts(key), 0, []
    for ch in text:
        if ch.isalpha() and ch.isascii():
            base = 65 if ch.isupper() else 97
            out.append(chr(base + (ord(ch) - base + sign * k[i % len(k)]) % 26))
            i += 1
        else:
            out.append(ch)
    return "".join(out)


def vigenere_decrypt(text: str, key: str) -> str:
    return vigenere_encrypt(text, key, -1)


# ---- Monoalphabetic substitution ---------------------------------------------------------------
def _check_alphabet(key: str) -> str:
    key = key.upper()
    if sorted(key) != list(ALPHA):
        raise ValueError("substitution key must be a permutation of the 26 letters (plain A..Z -> key)")
    return key


def substitution_encrypt(text: str, key: str) -> str:
    key = _check_alphabet(key)
    return _shift_map(text, lambda x: ord(key[x]) - 65)


def substitution_decrypt(text: str, key: str) -> str:
    key = _check_alphabet(key)
    inv = {ord(c) - 65: i for i, c in enumerate(key)}
    return _shift_map(text, lambda x: inv[x])


# ---- Rail fence ---------------------------------------------------------------------------
def _rail_pattern(n: int, rails: int) -> list[int]:
    if rails < 2:
        raise ValueError("rail fence needs at least 2 rails")
    cycle = list(range(rails)) + list(range(rails - 2, 0, -1))
    return [cycle[i % len(cycle)] for i in range(n)]


def railfence_encrypt(text: str, rails: int) -> str:
    t = letters(text)
    pat = _rail_pattern(len(t), rails)
    return "".join(t[i] for r in range(rails) for i in range(len(t)) if pat[i] == r)


def railfence_decrypt(text: str, rails: int) -> str:
    t = letters(text)
    pat = _rail_pattern(len(t), rails)
    order = [i for r in range(rails) for i in range(len(t)) if pat[i] == r]
    out = [""] * len(t)
    for pos, ch in zip(order, t):
        out[pos] = ch
    return "".join(out)


# ---- Columnar transposition ---------------------------------------------------------------
def key_order(key: str) -> list[int]:
    """Column read order for a keyword: the column with the alphabetically first letter is read first (ties left to right)."""
    k = [c for c in key.upper() if "A" <= c <= "Z"]
    if len(k) < 2:
        raise ValueError("columnar key needs at least 2 letters")
    return sorted(range(len(k)), key=lambda i: (k[i], i))


def columnar_encrypt(text: str, key: str) -> str:
    t, order = letters(text), key_order(key)
    w = len(order)
    return "".join(t[c::w] for c in order)


def columnar_decrypt_order(text: str, order: list[int]) -> str:
    """Invert columnar_encrypt given the column read order (works for ragged last rows)."""
    t, w = letters(text), len(order)
    n = len(t)
    full, extra = divmod(n, w)
    cols: dict[int, str] = {}
    pos = 0
    for c in order:
        ln = full + (1 if c < extra else 0)
        cols[c] = t[pos:pos + ln]
        pos += ln
    return "".join(cols[c][r] for r in range(full + 1) for c in range(w) if r < len(cols[c]))


def columnar_decrypt(text: str, key: str) -> str:
    return columnar_decrypt_order(text, key_order(key))


CIPHERS = ["caesar", "atbash", "affine", "vigenere", "substitution", "railfence", "columnar"]


def encrypt(cipher: str, text: str, key: str | None) -> str:
    """Dispatch used by the CLI. Key formats: caesar 3 | affine 5,8 | vigenere LEMON | substitution <26 letters> | railfence 3 | columnar ZEBRAS | atbash (none)."""
    if cipher == "atbash":
        return atbash(text)
    if key is None:
        raise ValueError(f"{cipher} needs --key")
    if cipher == "caesar":
        return caesar_encrypt(text, int(key))
    if cipher == "affine":
        a, b = (int(x) for x in key.split(","))
        return affine_encrypt(text, a, b)
    if cipher == "vigenere":
        return vigenere_encrypt(text, key)
    if cipher == "substitution":
        return substitution_encrypt(text, key)
    if cipher == "railfence":
        return railfence_encrypt(text, int(key))
    if cipher == "columnar":
        return columnar_encrypt(text, key)
    raise ValueError(f"unknown cipher {cipher!r}; choose from {CIPHERS}")
