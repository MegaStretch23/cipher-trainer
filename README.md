# cipher-trainer (branch `full-spec`)

This branch is a second implementation beside `main`: it adds the **affine** cipher, a `trainer solve` that identifies the cipher itself and prints a numbered explanation, public-domain sample passages, 39 tests and a reproducible benchmark. Everything below describes this branch.

Break classical ciphers and see **every step**: how the cipher family was identified, what was measured, and why the next attack was tried.
Python 3.10+, **standard library only**, MIT licence.

Ciphers: Caesar, Atbash, affine, Vigenere, monoalphabetic substitution, rail fence, columnar transposition. Each has an `encrypt`, so you can make your own practice ciphertexts.

Attacks (all in `cipher_trainer/attacks.py`): letter-frequency analysis, index of coincidence (IC), Kasiski repeats, Friedman key-length estimate, per-column chi-squared shift scoring, hill-climbing on a quadgram-style language model for substitution, exhaustive or swap-climbing search over column orders, and a brute-force fallback that runs every solver and keeps the best-scoring decrypt.

## Quickstart

```bash
git clone -b full-spec https://github.com/MegaStretch23/cipher-trainer && cd cipher-trainer
python3 -m cipher_trainer encrypt "Meet me at the old bridge when the clock strikes midnight." --cipher caesar --key 5
python3 -m cipher_trainer solve -f examples/caesar.ciphertext.txt
python3 -m pytest -q          # needs pytest; the package itself needs nothing
```
(`pip install .` also installs a `trainer` command with the same arguments.)

Real output, saved in `examples/caesar.transcript.txt` (the plaintext is the opening of *A Scandal in Bohemia*, public domain, shifted by 11):

```text
$ trainer encrypt -f examples/plain-scandal.txt --cipher caesar --key 11
$ trainer solve -f examples/caesar.ciphertext.txt

1. Identify the cipher family
   Letters: 393   IC: 0.0687   distance of letter frequencies from English (total variation): 0.46
   IC is English-like but the frequencies are not: each plaintext letter always maps to the same ciphertext letter -> monoalphabetic substitution (Caesar, Atbash, affine or general substitution).
   Attack order: caesar, atbash, affine, substitution
2. Attack: caesar
   model score -1.056 per char (English ~ -1.1, random ~ -2.7, accept at -1.45)
   [Frequency analysis] 393 letters. Most common ciphertext letters: P:  55 (14.0%); L:  37 ( 9.4%); E:  30 ( 7.6%); Z:  30 ( 7.6%); S:  28 ( 7.1%); Y:  28 ( 7.1%); D:  27 ( 6.9%); T:  27 ( 6.9%) | English is led by: E 12.7%, T 9.1%, A 8.2%, O 7.5%, I 7.0%, N 6.7%, S 6.3%, H 6.1%
   [Chi-squared scoring of all 26 shifts] For each shift, decrypt and measure the chi-squared distance of the letter counts from English (lower is better): | shift 11 -> chi2     19.3   TOSHERLOCKHOLMESSHEISALWAYST... | shift 17 -> chi2   1393.3   NIMBYLFIWEBIFGYMMBYCMUFQUSMN... | shift 22 -> chi2   1692.8   IDHWTGADRZWDABTHHWTXHPALPNHI... | shift 24 -> chi2   1916.9   GBFUREYBPXUBYZRFFURVFNYJNLFG... | Shift 11 is 72.3x better than the runner-up.
   Accepted: caesar.
3. Conclusion
   Caesar shift 11 (each letter moved 11 places forward by the encryptor; key letter L).
   Decrypt: To Sherlock Holmes she is always the woman. I have seldom heard him mention her under any other name...
   Confidence: high (score -1.056)

CIPHER: caesar   KEY: 11   SCORE: -1.056/char   ACCEPTED
PLAINTEXT: To Sherlock Holmes she is always the woman. I have seldom heard him mention her under any other name. In his eyes she eclipses and predominates the whole of her sex. It was not that he felt any emotion akin to love for Irene Adler. All emotions, and that one particularly, were abhorrent to his cold, precise but admirably balanced mind. He was, I take it, the most perfect reasoning and observing machine that the world has seen, but as a lover he would have placed himself in a false position.
```

Each other cipher has a saved transcript in `examples/`: `vigenere.transcript.txt` (Kasiski, Friedman, per-column IC and chi-squared), `railfence.transcript.txt`, `substitution.transcript.txt` (hill-climb sweeps), `random.transcript.txt`.

## Commands

| command | does |
|---|---|
| `trainer solve <text>` or `-f file` | identify and break; numbered explanation; exit 0 if accepted, 1 if low confidence |
| `trainer solve --cipher vigenere ...` | skip identification, force one attack |
| `trainer solve --json ...` | same result as JSON, steps included |
| `trainer analyze <text>` | only the identification step (IC, frequency distance, family) |
| `trainer encrypt <text> --cipher C --key K` | keys: caesar `3`, affine `5,8`, vigenere `LEMON`, substitution `<26 letters>`, railfence `3`, columnar `ZEBRAS`, atbash none |

## How well does it work? (measured, not promised)

`examples/benchmark.py` encrypts six public-domain passages (235 to 411 letters) with each of the seven ciphers and breaks them with `solve` (auto mode). Output saved in `examples/benchmark.txt`, run on a 4-vCPU server:

```text
sample        letters  cipher        identified as letters right  seconds
scandal           393  caesar        caesar          393/393          0.0
scandal           393  atbash        atbash          393/393          0.0
scandal           393  affine        affine          393/393          0.4
scandal           393  vigenere      vigenere        393/393          0.2
scandal           393  substitution  substitution    393/393          4.6
scandal           393  railfence     railfence       393/393          0.0
scandal           393  columnar      columnar        393/393          5.1
emma              341  caesar        caesar          341/341          0.0
emma              341  atbash        atbash          341/341          0.0
emma              341  affine        affine          341/341          0.2
emma              341  vigenere      vigenere        341/341          0.1
emma              341  substitution  substitution    339/341          3.5
emma              341  railfence     railfence       341/341          0.0
emma              341  columnar      columnar        341/341          4.1
expectations      267  caesar        caesar          267/267          0.0
expectations      267  atbash        atbash          267/267          0.0
expectations      267  affine        affine          267/267          0.1
expectations      267  vigenere      vigenere        267/267          0.1
expectations      267  substitution  substitution    246/267          3.4
expectations      267  railfence     railfence       267/267          0.0
expectations      267  columnar      columnar        267/267          3.8
treasure          411  caesar        caesar          411/411          0.0
treasure          411  atbash        atbash          411/411          0.0
treasure          411  affine        affine          411/411          0.4
treasure          411  vigenere      vigenere        411/411          0.2
treasure          411  substitution  substitution    411/411          5.6
treasure          411  railfence     railfence       411/411          0.0
treasure          411  columnar      columnar        411/411          5.8
janeeyre          235  caesar        caesar          235/235          0.0
janeeyre          235  atbash        atbash          235/235          0.0
janeeyre          235  affine        affine          235/235          0.1
janeeyre          235  vigenere      vigenere        235/235          0.1
janeeyre          235  substitution  substitution    223/235          3.1
janeeyre          235  railfence     railfence       235/235          0.0
janeeyre          235  columnar      columnar        235/235          2.8
oz                315  caesar        caesar          315/315          0.0
oz                315  atbash        atbash          315/315          0.0
oz                315  affine        affine          315/315          0.1
oz                315  vigenere      vigenere        315/315          0.1
oz                315  substitution  substitution    315/315          4.0
oz                315  railfence     railfence       315/315          0.0
oz                315  columnar      columnar        315/315          3.9

exact plaintext recovered: 39 of 42
```

Reading it honestly:
- **Identification was correct in all 42 runs** and 39 of 42 recovered the exact plaintext letters.
- The 3 misses are all **substitution**: the key is 26 free letters and a few hundred letters of text do not pin down rare letters. Example from `examples/substitution-near-miss.transcript.txt`, 339 of 341 letters right (`x` came out as `k`, so "existence" printed as "ekistence"):

```text
CIPHER: substitution   KEY: QWERTYUIOMBSDFGHJKLZXCVANP   SCORE: -1.021/char   ACCEPTED
PLAINTEXT: Emma Woodhouse, handsome, clever, and rich, with a comfortable home and happy disposition, seemed to unite some of the best blessings of ekistence; and had lived nearly twenty-one years in the world with very little to distress or vek her. She was the youngest of the two daughters of a most affectionate, indulgent father; and had, in consequence of her sister's marriage, been mistress of his house from a very early per...
```

- Below about 100 letters a substitution answer is **never marked accepted**: with so few letters random text can be fitted to look like English. Random letters are reported as low confidence, not forced into a "solution" (`examples/random.transcript.txt`):

```text
3. Brute-force fallback
   Best guess: substitution, key RBQVZHXEJYNSOTCMUKDPGWLFIA. LOW CONFIDENCE (score -1.717): text may be too short or use an unsupported cipher.
CIPHER: substitution   KEY: RBQVZHXEJYNSOTCMUKDPGWLFIA   SCORE: -1.717/char   LOW CONFIDENCE
```

- Seconds are wall-clock for one run in pure Python; substitution and columnar are the slow ones (a few seconds).

## Limits

- English only. The language model is built at import time from about 8,800 letters of public-domain prose (`cipher_trainer/corpus.py`); a bigger corpus would make substitution more exact. The test and benchmark passages are different texts from the training text.
- Columnar search covers widths 2 to 10 (all column orders up to width 7, random-restart swap climbing for 8 to 10). Rail fence: 2 to 12 rails, no offset. Vigenere key length up to 20 with at least 12 ciphertext letters per key letter.
- Transposition output is letters only (spaces and punctuation cannot be recovered); the substitution-type ciphers keep case and punctuation.
- Classical ciphers are not secure. This is for learning, puzzles and CTF warm-ups.

## Tests

`python3 -m pytest -q` runs 39 tests: known vectors (Wikipedia's rail fence, columnar and Vigenere examples, Caesar, affine), round trips, each solver on held-out passages, the identification ladder, garbage and too-short inputs, and the CLI.

## Also by the author (unrelated to ciphers)

Paid tools that are not part of this repo:
- Apify pay-per-event actors for structured SEC filings: [SEC Form 4 insider clusters](https://apify.com/johnveds15/sec-form4-insider-clusters), [SEC 8-K material events](https://apify.com/johnveds15/sec-8k-material-events).
- Gumroad source packs: [pdfguard, hidden prompt-injection text in PDFs (Python, local)](https://vedovino.gumroad.com/l/gvvcsh), [Doom-detector for headless Claude Code runs](https://vedovino.gumroad.com/l/mjxcmw).

## Licence

MIT, see `LICENSE`. Sample passages are public-domain excerpts.
