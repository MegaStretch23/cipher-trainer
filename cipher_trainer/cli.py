"""Command line: cipher-trainer break | analyze | encrypt | decrypt."""
from __future__ import annotations
import argparse
import json
import sys

from . import ciphers as C
from .solvers import SOLVERS, analyze, solve

CIPHERS = {"caesar": C.caesar, "atbash": C.atbash, "vigenere": C.vigenere, "substitution": C.substitution,
           "railfence": C.railfence, "columnar": C.columnar}


def _text(a) -> str:
    if getattr(a, "text", None) is not None:
        return a.text
    if getattr(a, "file", None):
        with open(a.file, encoding="utf-8") as f:
            return f.read()
    return sys.stdin.read()


def _add_input(p):
    g = p.add_mutually_exclusive_group()
    g.add_argument("--text", "-t", help="the text (default: read stdin)")
    g.add_argument("--file", "-f", help="read the text from a file")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="cipher-trainer", description="Break classical ciphers and show every step. Standard library only.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("break", help="break a ciphertext")
    b.add_argument("cipher", choices=["auto", *SOLVERS], help="cipher to assume, or auto to try all")
    _add_input(b)
    b.add_argument("--explain", "-e", action="store_true", help="print every step: frequencies, IC, Kasiski, chi-squared, hill climbing")
    b.add_argument("--json", action="store_true", help="machine-readable result")
    b.add_argument("--seed", type=int, default=1, help="seed for the hill climbs (default 1)")
    a = sub.add_parser("analyze", help="frequency table, index of coincidence, chi-squared, Kasiski; no solving")
    _add_input(a)
    for name in ("encrypt", "decrypt"):
        e = sub.add_parser(name, help=f"{name} text (to make practice ciphertexts)")
        e.add_argument("cipher", choices=list(CIPHERS))
        e.add_argument("--key", "-k", default="", help="Caesar: number; Vigenere: word; substitution: 26-letter permutation; rail fence: rails; columnar: word or 3,1,2")
        _add_input(e)
    return ap


def _key(cipher: str, k: str):
    if cipher in ("caesar", "railfence"):
        return int(k)
    return k


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    try:
        if a.cmd == "analyze":
            r = analyze(_text(a))
            print("\n".join(r["steps"])); return 0
        if a.cmd in ("encrypt", "decrypt"):
            print(CIPHERS[a.cipher](_text(a).rstrip("\n"), _key(a.cipher, a.key), a.cmd == "decrypt")); return 0
        text = _text(a)
        r = solve(text, a.cipher, seed=a.seed) if a.cipher in ("auto", "substitution", "columnar") else solve(text, a.cipher)
    except (ValueError, OSError) as e:
        print(f"cipher-trainer: error: {e}", file=sys.stderr); return 2
    if a.json:
        print(json.dumps({k: r[k] for k in ("cipher", "key", "plaintext", "score", "verdict")}, indent=2)); return 0
    if a.explain:
        print("\n".join(r["steps"])); print()
    print(f"cipher:    {r['cipher']}")
    print(f"key:       {r['key'] if r['key'] is not None else '(none)'}")
    print(f"score:     {r['score']:.3f}  ({r['verdict']})")
    print(f"plaintext: {r['plaintext']}")
    return 0
