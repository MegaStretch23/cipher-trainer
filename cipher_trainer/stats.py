"""Letter statistics and a small interpolated n-gram language model (standard library only)."""
from __future__ import annotations
import math
from collections import Counter
from functools import lru_cache

ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# Standard published English letter frequencies, percent.
ENGLISH_FREQ = dict(zip(ALPHA, [8.167, 1.492, 2.782, 4.253, 12.702, 2.228, 2.015, 6.094, 6.966, 0.153, 0.772, 4.025, 2.406,
                                6.749, 7.507, 1.929, 0.095, 5.987, 6.327, 9.056, 2.758, 0.978, 2.360, 0.150, 1.974, 0.074]))
ENGLISH_ORDER = "".join(sorted(ALPHA, key=lambda c: -ENGLISH_FREQ[c]))
ENGLISH_IC = 0.0667
RANDOM_IC = 1 / 26


def letters(text: str) -> str:
    return "".join(c for c in text.upper() if "A" <= c <= "Z")


def counts(text: str) -> Counter:
    return Counter(letters(text))


def ic(text: str) -> float:
    """Index of coincidence: probability that two letters drawn without replacement match."""
    t = letters(text)
    n = len(t)
    if n < 2:
        return 0.0
    return sum(f * (f - 1) for f in Counter(t).values()) / (n * (n - 1))


def chi2(text: str) -> float:
    """Chi-squared distance of the letter counts from English. Lower = more English-like."""
    t = letters(text)
    n = len(t)
    if not n:
        return float("inf")
    c = Counter(t)
    return sum((c.get(a, 0) - n * ENGLISH_FREQ[a] / 100) ** 2 / (n * ENGLISH_FREQ[a] / 100) for a in ALPHA)


class _Model:
    def __init__(self) -> None:
        from .corpus import TRAINING
        t = letters(TRAINING)
        self.n = [Counter(t[i:i + k] for i in range(len(t) - k + 1)) for k in (1, 2, 3, 4)]
        self.total = len(t)

    def cond(self, w: str) -> float:
        """P(last letter of w | previous letters), interpolated 4/3/2/1-gram."""
        c1, c2, c3, c4 = self.n
        p = (c1[w[3]] + 0.5) / (self.total + 13)
        p2 = c2[w[2:]] / c1[w[2]] if c1[w[2]] else 0.0
        p3 = c3[w[1:]] / c2[w[1:3]] if c2[w[1:3]] else 0.0
        p4 = c4[w] / c3[w[:3]] if c3[w[:3]] else 0.0
        return 0.45 * p4 + 0.30 * p3 + 0.17 * p2 + 0.08 * p


_model: _Model | None = None


def _m() -> _Model:
    global _model
    if _model is None:
        _model = _Model()
    return _model


@lru_cache(maxsize=None)
def _win(w: str) -> float:
    return math.log10(_m().cond(w))


def score(text: str) -> float:
    """Total log10-probability of the letters of text under the model (higher = more English)."""
    t = "^^^" + (letters(text) if not text.isupper() or not text.isalpha() else text)   # '^' pads the start so the first letters use lower orders
    return sum(_win(t[i:i + 4]) for i in range(len(t) - 3))


def per_char(text: str) -> float:
    """score() divided by the number of letters. English held-out text is about -1.0 to -1.3."""
    t = letters(text)
    return score(t) / max(1, len(t))
