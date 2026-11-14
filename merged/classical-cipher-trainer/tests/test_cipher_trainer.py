"""python3 -I tests/test_cipher_trainer.py : known-plaintext round trips for every cipher (stdlib unittest)."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import cipher_trainer as C

PLAIN = ("THEOLDLIGHTHOUSEKEEPERCLIMBEDTHESPIRALSTAIRSEVERYEVENINGCARRYINGALAMPANDAFLASKOFTEABECAUSETHESTORMHADBEENGROWINGALLWEEKANDTHESHIPSWOULDNEEDTHEBEAMLONGBEFOREMIDNIGHT"
         "HEKNEWEACHSTEPBYTHESOUNDITMADEUNDERHISBOOTSANDHECOUNTEDTHEMOUTOFHABITUNTILHEREACHEDTHEIRONDOORATTHETOP")
SUBKEY = "QWERTYUIOPASDFGHJKLZXCVBNM"


class T(unittest.TestCase):
    def rt(self, cipher, key):
        ct = C.encrypt(cipher, PLAIN, key); self.assertNotEqual(ct, PLAIN)
        r = C.break_cipher(cipher, ct); self.assertEqual(r["plaintext"], PLAIN, cipher); return r

    def test_caesar(self): self.assertEqual(self.rt("caesar", "11")["key"], "11")
    def test_atbash(self): self.rt("atbash", "")
    def test_vigenere(self): self.assertEqual(self.rt("vigenere", "BEACON")["key"], "BEACON")
    def test_substitution(self):
        r = self.rt("substitution", SUBKEY)   # key letters for plaintext letters that never occur (e.g. Q, Z) are unconstrained, so compare the ones that do
        for ch in set(PLAIN): self.assertEqual(r["key"][ord(ch) - 65], SUBKEY[ord(ch) - 65])
    def test_columnar(self): self.rt("columnar", "ZEBRAS")
    def test_auto_picks_the_cipher(self):
        for c, k in (("caesar", "4"), ("vigenere", "LAMP"), ("columnar", "KEYWORD")):
            r = C.break_cipher("auto", C.encrypt(c, PLAIN, k)); self.assertEqual(r["plaintext"], PLAIN); self.assertEqual(r["cipher"], "auto:" + c)
    def test_known_vectors(self):
        self.assertEqual(C.encrypt("caesar", "attack at dawn", "3"), "DWWDFNDWGDZQ")
        self.assertEqual(C.encrypt("atbash", "attack"), "ZGGZXP")
        self.assertEqual(C.encrypt("vigenere", "attack at dawn", "LEMON"), "LXFOPVEFRNHR")
        self.assertEqual(C.encrypt("columnar", "WEAREDISCOVERED", "ZEBRAS"), "EVACDESERODEWIR")   # worked by hand: rows WEARED/ISCOVE/RED, columns read in key-letter order A,B,E,R,S,Z
        self.assertEqual(C.encrypt("substitution", "abc", SUBKEY), "QWE")
    def test_errors(self):
        with self.assertRaises(ValueError): C.break_cipher("caesar", "ab")
        with self.assertRaises(ValueError): C.encrypt("substitution", "abc", "ABC")


if __name__ == "__main__":
    unittest.main(verbosity=1)
