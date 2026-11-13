import pytest
from cipher_trainer import ciphers as C
from cipher_trainer.corpus import SAMPLES
from cipher_trainer.stats import letters

T = SAMPLES["oz"]
KEY = "QWERTYUIOPASDFGHJKLZXCVBNM"


def test_caesar_known_vector():
    assert C.caesar_encrypt("Hello, World!", 3) == "Khoor, Zruog!"


def test_caesar_roundtrip_keeps_case_and_punctuation():
    assert C.caesar_decrypt(C.caesar_encrypt(T, 17), 17) == T


def test_atbash_known_and_involution():
    assert C.atbash("Wizard") == "Draziw"
    assert C.atbash(C.atbash(T)) == T


def test_affine_known_vector():
    assert C.affine_encrypt("AFFINE", 5, 8) == "IHHWVC"


def test_affine_roundtrip_all_valid_a():
    for a in C.AFFINE_A + [1]:
        assert C.affine_decrypt(C.affine_encrypt(T, a, 9), a, 9) == T


def test_affine_rejects_non_coprime_a():
    with pytest.raises(ValueError):
        C.affine_encrypt("x", 13, 1)


def test_vigenere_wikipedia_vector():
    assert C.vigenere_encrypt("ATTACKATDAWN", "LEMON") == "LXFOPVEFRNHR"


def test_vigenere_roundtrip_with_punctuation():
    assert C.vigenere_decrypt(C.vigenere_encrypt(T, "Kansas"), "Kansas") == T


def test_substitution_roundtrip_and_validation():
    assert C.substitution_decrypt(C.substitution_encrypt(T, KEY), KEY) == T
    with pytest.raises(ValueError):
        C.substitution_encrypt("x", "ABC")


def test_railfence_known_vector():
    assert C.railfence_encrypt("WEAREDISCOVEREDFLEEATONCE", 3) == "WECRLTEERDSOEEFEAOCAIVDEN"


def test_railfence_roundtrip_many_rails():
    for r in range(2, 9):
        assert C.railfence_decrypt(C.railfence_encrypt(T, r), r) == letters(T)


def test_columnar_known_vector():
    assert C.columnar_encrypt("WEAREDISCOVEREDFLEEATONCE", "ZEBRAS") == "EVLNACDTESEAROFODEECWIREE"


def test_columnar_roundtrip_ragged():
    for key in ("ZEBRAS", "KEY", "SECRETWORD"):
        assert C.columnar_decrypt(C.columnar_encrypt(T, key), key) == letters(T)


def test_encrypt_dispatch_and_missing_key():
    assert C.encrypt("caesar", "abc", "1") == "bcd"
    assert C.encrypt("affine", "AFFINE", "5,8") == "IHHWVC"
    with pytest.raises(ValueError):
        C.encrypt("vigenere", "abc", None)
