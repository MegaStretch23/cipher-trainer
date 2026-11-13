import random
import pytest
from cipher_trainer import attacks as A, ciphers as C, stats
from cipher_trainer.corpus import SAMPLES, TRAINING

SC, EM, TR = SAMPLES["scandal"], SAMPLES["emma"], SAMPLES["treasure"]


def same(result, plain):
    return stats.letters(result.plaintext) == stats.letters(plain)


def test_samples_are_held_out_from_the_model():
    for text in SAMPLES.values():
        assert stats.letters(text)[:60] not in stats.letters(TRAINING)


def test_english_scores_far_above_random():
    g = random.Random(1)
    rnd = "".join(g.choice(stats.ALPHA) for _ in range(300))
    assert stats.per_char(SC) > -1.4 and stats.per_char(rnd) < -1.7


def test_ic_values():
    assert 0.060 < stats.ic(SC) < 0.075
    assert stats.ic(C.vigenere_encrypt(SC, "CIPHER")) < 0.050


def test_chi2_lowest_at_true_shift():
    ct = C.caesar_encrypt(EM, 9)
    assert min(range(26), key=lambda s: stats.chi2(C.caesar_decrypt(ct, s))) == 9


def test_caesar_solver():
    r = A.solve_caesar(C.caesar_encrypt(SC, 11))
    assert r.key == "11" and same(r, SC)


def test_atbash_solver():
    assert same(A.solve_atbash(C.atbash(SC)), SC)


def test_affine_solver():
    r = A.solve_affine(C.affine_encrypt(EM, 7, 3))
    assert r.key == "7,3" and same(r, EM)


def test_vigenere_solver_recovers_key():
    r = A.solve_vigenere(C.vigenere_encrypt(SC, "CIPHER"))
    assert r.key == "CIPHER" and same(r, SC)


def test_vigenere_steps_include_kasiski_friedman_and_ic():
    r = A.solve_vigenere(C.vigenere_encrypt(TR, "LEMON"))
    titles = [s.title for s in r.steps]
    assert {"Kasiski examination", "Friedman estimate", "Index of coincidence"} <= set(titles)


def test_kasiski_finds_the_period():
    t = stats.letters(C.vigenere_encrypt(TR, "LEMON"))
    _, fac = A.kasiski(t)
    assert fac[5] >= max(fac[f] for f in (3, 4, 7, 9, 11))


def test_railfence_solver():
    r = A.solve_railfence(C.railfence_encrypt(SC, 5))
    assert r.key == "5" and same(r, SC)


def test_columnar_solver():
    r = A.solve_columnar(C.columnar_encrypt(TR, "ZEBRA"))
    assert same(r, TR)


def test_substitution_solver_gets_nearly_every_letter():
    key = "QWERTYUIOPASDFGHJKLZXCVBNM"
    r = A.solve_substitution(C.substitution_encrypt(TR, key))
    got, want = stats.letters(r.plaintext), stats.letters(TR)
    assert len(got) == len(want) and sum(a == b for a, b in zip(got, want)) / len(want) > 0.95


def test_solve_auto_identifies_each_family():
    cases = [("caesar", C.caesar_encrypt(SC, 4)), ("vigenere", C.vigenere_encrypt(SC, "KEYWORD")),
             ("railfence", C.railfence_encrypt(SC, 3)), ("atbash", C.atbash(SC))]
    for name, ct in cases:
        best, steps, _ = A.solve(ct)
        assert best.cipher == name and best.accepted, name
        assert steps[0].title == "Identify the cipher family"


def test_solve_flags_garbage_as_low_confidence():
    g = random.Random(5)
    junk = "".join(g.choice(stats.ALPHA) for _ in range(150))
    best, steps, _ = A.solve(junk)
    assert not best.accepted and steps[-1].title == "Brute-force fallback"


def test_solve_rejects_too_short():
    with pytest.raises(ValueError):
        A.solve("ABC")


def test_solve_leaves_plaintext_alone():
    best, _, _ = A.solve(SC)
    assert best.cipher == "none"


def test_repetitive_pseudo_text_is_not_accepted():
    r = A.Result("x", "-", "RLIFELVER" * 20, -0.8)
    assert not r.accepted


def test_short_substitution_is_never_accepted():
    g = random.Random(2)
    junk = "".join(g.choice(stats.ALPHA) for _ in range(60))
    assert not A.solve_substitution(junk).accepted
