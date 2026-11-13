import io
import json
import math
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from cipher_trainer import ciphers as C
from cipher_trainer import solvers as S
from cipher_trainer.cli import main
from cipher_trainer.english import IC_ENGLISH, chi_squared, clean, english_score, ic, trigram_score

PLAIN = ("Meet me at the old bridge at dawn and bring the papers with you. Nobody must see the message, so burn it after you have read it. "
         "We will leave the town before the rain starts and walk along the river until we reach the harbor where the ship is waiting. "
         "If anyone asks, say that you are visiting your cousin on the far side of the valley and that the weather turned bad.")
SUBKEY = "QWERTYUIOPASDFGHJKLZXCVBNM"


def same(a, b):
    return clean(a) == clean(b)


# ---- ciphers round trip
def test_caesar_roundtrip_keeps_case_and_punctuation():
    ct = C.caesar("Hello, World!", 3)
    assert ct == "Khoor, Zruog!" and C.caesar(ct, 3, True) == "Hello, World!"


def test_atbash_is_its_own_inverse():
    assert C.atbash("Wizard") == "Draziw" and C.atbash(C.atbash(PLAIN)) == PLAIN


def test_vigenere_known_vector():
    assert C.vigenere("ATTACKATDAWN", "LEMON") == "LXFOPVEFRNHR"
    assert C.vigenere("LXFOPVEFRNHR", "LEMON", True) == "ATTACKATDAWN"


def test_substitution_roundtrip_and_bad_key():
    ct = C.substitution(PLAIN, SUBKEY)
    assert C.substitution(ct, SUBKEY, True) == PLAIN
    with pytest.raises(ValueError):
        C.substitution("abc", "ABC")


def test_railfence_known_vector():
    assert C.railfence("WEAREDISCOVEREDFLEEATONCE", 3) == "WECRLTEERDSOEEFEAOCAIVDEN"
    assert C.railfence("WECRLTEERDSOEEFEAOCAIVDEN", 3, True) == "WEAREDISCOVEREDFLEEATONCE"


def test_columnar_keyword_and_numeric_keys_roundtrip():
    msg = clean(PLAIN)
    for k in ("ZEBRAS", "3,1,2", "2,1", "4,2,7,1,6,3,8,5"):
        assert C.columnar(C.columnar(msg, k), k, True) == msg


def test_columnar_known_vector():
    # ZEBRAS -> read order A(4) B(2) E(3) R(4)... wikipedia-style grid of 6 columns
    assert C.columnar("WEAREDISCOVEREDFLEEATONCE", "ZEBRAS") == "EVLNACDTESEAROFODEECWIREE"


def test_columnar_rejects_bad_key():
    with pytest.raises(ValueError):
        C.columnar("ABCDEF", "1,1,2")


# ---- statistics
def test_ic_and_chi_separate_english_from_noise():
    assert ic(PLAIN) > 0.06
    shifted = C.vigenere(PLAIN, "LEMON")
    assert ic(shifted) < 0.05
    assert chi_squared(PLAIN) < chi_squared(shifted)
    assert abs(IC_ENGLISH - 0.0667) < 1e-9


def test_english_score_orders_candidates():
    assert english_score(PLAIN) > english_score(C.caesar(PLAIN, 5)) + 1.0
    assert english_score(PLAIN) > english_score(C.columnar(PLAIN, "ZEBRAS"))
    assert trigram_score("ab") == -99.0


def test_kasiski_finds_the_key_length_factor():
    ct = C.vigenere(PLAIN, "LEMON")
    k = S.kasiski(ct)
    assert k["repeats"] and k["votes"].most_common(1)[0][0] % 5 == 0 or 5 in dict(k["votes"].most_common(3))


# ---- solvers
def test_break_caesar_every_shift():
    for k in (1, 7, 13, 25):
        r = S.solve(C.caesar(PLAIN, k), "caesar")
        assert r["key"] == k and same(r["plaintext"], PLAIN)


def test_break_atbash():
    r = S.solve(C.atbash(PLAIN), "atbash")
    assert same(r["plaintext"], PLAIN) and r["verdict"] == "reads as English"


@pytest.mark.parametrize("key", ["LEMON", "CIPHERS", "KEY"])
def test_break_vigenere_finds_key(key):
    r = S.solve(C.vigenere(PLAIN, key), "vigenere")
    assert r["key"] == key and same(r["plaintext"], PLAIN)


def test_break_vigenere_short_text():
    short = "Attack at dawn, the bridge is unguarded and the guards sleep until noon so we cross while the fog is still thick on the river bank"
    assert S.solve(C.vigenere(short, "LEMON"), "vigenere")["key"] == "LEMON"


def test_break_substitution_hill_climb():
    r = S.solve(C.substitution(PLAIN, SUBKEY), "substitution")
    assert same(r["plaintext"], PLAIN)
    assert any("hill climb" in s for s in r["steps"])


def test_break_substitution_is_reproducible():
    ct = C.substitution(PLAIN, SUBKEY)
    assert S.solve(ct, "substitution", seed=5)["key"] == S.solve(ct, "substitution", seed=5)["key"]


def test_break_railfence():
    r = S.solve(C.railfence(PLAIN, 4), "railfence")
    assert r["key"] == 4 and same(r["plaintext"], PLAIN)


def test_break_columnar_keyword_width_6():
    r = S.solve(C.columnar(PLAIN, "ZEBRAS"), "columnar")
    assert same(r["plaintext"], PLAIN)


def test_break_columnar_width_8_hill_climb():
    r = S.solve(C.columnar(PLAIN, "4,2,7,1,6,3,8,5"), "columnar")
    assert same(r["plaintext"], PLAIN)


def test_auto_identifies_each_family():
    cases = [("caesar", C.caesar(PLAIN, 11)), ("vigenere", C.vigenere(PLAIN, "LEMON")), ("railfence", C.railfence(PLAIN, 3)),
             ("substitution", C.substitution(PLAIN, SUBKEY))]
    for name, ct in cases:
        r = S.solve(ct, "auto")
        assert r["cipher"] == name and same(r["plaintext"], PLAIN), name


def test_wrong_cipher_is_flagged_not_hidden():
    r = S.solve(C.vigenere(PLAIN, "LEMON"), "caesar")
    assert r["verdict"].startswith("not English")


def test_unknown_cipher_raises():
    with pytest.raises(ValueError):
        S.solve("abc", "enigma")


# ---- CLI
def run_cli(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(argv)
    return code, buf.getvalue()


def test_cli_explain_shows_each_step():
    ct = C.vigenere(PLAIN, "LEMON")
    code, out = run_cli(["break", "vigenere", "--text", ct, "--explain"])
    assert code == 0
    for needle in ("index of coincidence", "Kasiski", "key length", "chi2", "key = LEMON", "plaintext:"):
        assert needle in out, needle


def test_cli_json_and_encrypt_decrypt():
    code, out = run_cli(["encrypt", "caesar", "-k", "5", "-t", "Hello"])
    assert code == 0 and out.strip() == "Mjqqt"
    code, out = run_cli(["break", "caesar", "--json", "--text", C.caesar(PLAIN, 9)])
    d = json.loads(out)
    assert d["key"] == 9 and d["cipher"] == "caesar"


def test_cli_analyze_and_bad_key_exit_code():
    code, out = run_cli(["analyze", "--text", C.vigenere(PLAIN, "LEMON")])
    assert code == 0 and "index of coincidence" in out and "low IC" in out
    code, _ = run_cli(["encrypt", "substitution", "-k", "ABC", "-t", "x"])
    assert code == 2
