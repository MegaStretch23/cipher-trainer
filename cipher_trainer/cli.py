"""trainer: encrypt, analyse and break classical ciphers with a numbered explanation."""
from __future__ import annotations
import argparse, json, sys
from . import attacks, ciphers
from .stats import ic, letters, per_char


def _read(a) -> str:
    if a.file:
        return open(a.file, encoding="utf-8").read()
    if a.text == "-" or a.text is None:
        return sys.stdin.read()
    return a.text


def cmd_encrypt(a) -> int:
    try:
        print(ciphers.encrypt(a.cipher, _read(a), a.key))
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr); return 2
    return 0


def cmd_analyze(a) -> int:
    t = _read(a)
    head, order = attacks.identify(t)
    print(f"1. {head.title}")
    for line in head.lines:
        print(f"   {line}")
    print(f"   Model score of the text as given: {per_char(t):.3f} per char (English ~ -1.1, random ~ -2.7)")
    return 0


def cmd_solve(a) -> int:
    t = _read(a)
    try:
        best, steps, tried = attacks.solve(t, a.cipher)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr); return 2
    if a.json:
        print(json.dumps({"best": best.as_dict(), "trainer": [{"title": s.title, "lines": s.lines} for s in steps]}, indent=2))
        return 0 if best.accepted else 1
    for n, s in enumerate(steps, 1):
        print(f"{n}. {s.title}")
        for line in s.lines:
            for sub in line.split("\n"):
                print(f"   {sub}")
    print()
    print(f"CIPHER: {best.cipher}   KEY: {best.key}   SCORE: {best.quality:.3f}/char   {'ACCEPTED' if best.accepted else 'LOW CONFIDENCE'}")
    print(f"PLAINTEXT: {best.plaintext}")
    return 0 if best.accepted else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="trainer", description="Break classical ciphers step by step. Ciphers: " + ", ".join(ciphers.CIPHERS))
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn, hlp in (("solve", cmd_solve, "identify and break a ciphertext, printing numbered steps"),
                          ("analyze", cmd_analyze, "only the identification step (IC, frequencies, family)"),
                          ("encrypt", cmd_encrypt, "encrypt text (to make practice ciphertexts)")):
        p = sub.add_parser(name, help=hlp)
        p.add_argument("text", nargs="?", help="the text, or '-' / nothing for stdin")
        p.add_argument("-f", "--file", help="read the text from a file")
        if name == "solve":
            p.add_argument("--cipher", default="auto", choices=["auto"] + ciphers.CIPHERS, help="skip identification and force one attack")
            p.add_argument("--json", action="store_true")
        if name == "encrypt":
            p.add_argument("--cipher", required=True, choices=ciphers.CIPHERS)
            p.add_argument("--key", help="caesar 3 | affine 5,8 | vigenere LEMON | substitution <26 letters> | railfence 3 | columnar ZEBRAS")
        p.set_defaults(fn=fn)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
