"""Break every cipher on every held-out sample and print exact-match results.
Run from the repo root:  python3 examples/benchmark.py"""
import sys, time
sys.path.insert(0, ".")
from cipher_trainer import ciphers as C, attacks as A, stats
from cipher_trainer.corpus import SAMPLES

CASES = [("caesar", "11"), ("atbash", None), ("affine", "7,3"), ("vigenere", "CIPHER"),
         ("substitution", "QWERTYUIOPASDFGHJKLZXCVBNM"), ("railfence", "4"), ("columnar", "ZEBRAS")]
exact = total = 0
print(f"{'sample':13} {'letters':>7}  {'cipher':13} {'identified as':13} {'letters right':>13}  {'seconds':>7}")
for name, text in SAMPLES.items():
    want = stats.letters(text)
    for cipher, key in CASES:
        t0 = time.time()
        best, _, _ = A.solve(C.encrypt(cipher, text, key))
        got = stats.letters(best.plaintext)
        right = sum(a == b for a, b in zip(got, want)) if len(got) == len(want) else 0
        exact += got == want; total += 1
        print(f"{name:13} {len(want):7d}  {cipher:13} {best.cipher:13} {right:5d}/{len(want):<7d}  {time.time() - t0:7.1f}")
print(f"\nexact plaintext recovered: {exact} of {total}")
