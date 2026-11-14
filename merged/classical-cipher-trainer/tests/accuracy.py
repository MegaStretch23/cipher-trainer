"""python3 -I tests/accuracy.py : prints the table quoted in README.md (one fixed passage, one key per cipher, three ciphertext lengths). Not a benchmark."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import cipher_trainer as C
P = C.norm("""The old lighthouse keeper climbed the spiral stairs every evening, carrying a lamp and a flask of tea, because the storm had been growing all week and the ships would need the beam long before midnight. He knew each step by the sound it made under his boots, and he counted them out of habit, one hundred and twelve in all, until he reached the iron door at the top. Outside the wind pushed against the glass, and far below the waves broke white against the rocks, but the light turned steadily and the keeper allowed himself a small smile.""")
KEYS = [("caesar", "7"), ("atbash", ""), ("vigenere", "LEMON"), ("vigenere", "CIPHERS"), ("substitution", "XYLKWBFZTGJRQAHVEMUOPDICSN"), ("columnar", "ZEBRAS"), ("columnar", "KEYWORD")]
print("cipher (key)             | %s" % " | ".join("%3d letters" % n for n in (len(P), 250, 150)))
for name, key in KEYS:
    cells = []
    for n in (len(P), 250, 150):
        want = C.txt(P[:n]); t = time.time(); r = C.break_cipher(name, C.encrypt(name, want, key))
        got = r["plaintext"]; wrong = sum(a != b for a, b in zip(got, want))
        cells.append(("exact" if got == want else "%d of %d letters wrong" % (wrong, n)) + " %.1fs" % (time.time() - t))
    print("%-24s | %s" % ("%s (%s)" % (name, key[:8] or "-"), " | ".join(cells)))
