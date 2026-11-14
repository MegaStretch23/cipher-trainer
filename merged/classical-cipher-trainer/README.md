# Classical Cipher Trainer

Break classical ciphers and read every cryptanalysis step: Caesar, Atbash, Vigenere, simple substitution and columnar transposition.
A stdlib-only Python CLI and library, plus a browser page that runs the same algorithms in JavaScript (nothing is sent anywhere; the page code makes no network calls).

It is a trainer: each break prints the letter-frequency tables, the key-length guess with its Kasiski votes and index-of-coincidence table, the chi-squared score of each shift, and the quadgram score of each hill-climb restart, so you can see why the answer came out the way it did.

## Quickstart

Python 3 (tested on 3.12), no packages to install (it needs `data.json` next to `cipher_trainer.py`).

```
python3 -I cipher_trainer.py encrypt vigenere --key BEACON "the keeper counted every step of the spiral stairs"
python3 -I cipher_trainer.py break auto -f message.txt
python3 -I cipher_trainer.py break substitution --quiet "$(cat ciphertext.txt)"
```

Saved run (this is the exact output of the command, checked against the code by `node tests/readme.test.js`):

```
$ python3 -I cipher_trainer.py break vigenere ULEMSRQIRECHOXEFSIFVYUHRQSFVVRTTITOYTXAKFFBRDNWGULENOZQFEHCEFXHGGGPVMTSNDLEFHUFVOEYFTSTJSFIMPUQBVPDHWAEXHGVNSFOWFVOXHGRNSO
Step 1: Kasiski. Distances between repeated trigrams share a factor with the key length.
  4 repeated-trigram distances; factor votes: 2: 4, 3: 3, 6: 3, 4: 2, 12: 2
Step 2: index of coincidence per key length (English ~0.067, random ~0.038); the columns of the right length are each one Caesar shift.
  L=1 0.0451  L=2 0.0492  L=3 0.0549  L=4 0.0484  L=5 0.0483  L=6 0.0642
  L=7 0.0482  L=8 0.0507  L=9 0.0545  L=10 0.0460  L=11 0.0317  L=12 0.0670
  L=13 0.0440  L=14 0.0516  L=15 0.0532  L=16 0.0342
Step 3: best IC 0.0670; the shortest length within 90% of it is 6. Kasiski's top factor is 2 (divides 6).
Step 4: for each of the 6 columns, try the 26 shifts and keep the lowest chi-squared.
  column 1 (21 letters): shift B chi2 29.60, runner-up M chi2 60.47
  column 2 (21 letters): shift E chi2 32.85, runner-up X chi2 52.13
  column 3 (20 letters): shift A chi2 16.53, runner-up M chi2 67.99
  column 4 (20 letters): shift C chi2 27.42, runner-up S chi2 55.11
  column 5 (20 letters): shift O chi2 13.82, runner-up E chi2 57.27
  column 6 (20 letters): shift N chi2 12.25, runner-up T chi2 54.05
Step 5: key BEACON. Plaintext quadgram score: -4.24 per quadgram.

cipher:    vigenere
key:       BEACON
plaintext: THEKEEPERCOUNTEDEVERYSTEPOFTHESPIRALSTAIRSANDLITTHELAMPBEFORETHESTORMREACHEDTHEROCKSSOTHESHIPSCOULDFINDTHEHARBOURINTHEDARK
```

Only the letters A-Z are used; spaces, digits and punctuation are dropped, and the plaintext comes back as capitals without spaces.

## How each cipher is broken

| cipher | method |
|---|---|
| Caesar | all 26 shifts, lowest chi-squared against English letter frequencies |
| Atbash | no key: reverse the alphabet |
| Vigenere | Kasiski (distances between repeated trigrams) and the index of coincidence per key length choose the length (the shortest within 90% of the best IC); then each column is a Caesar shift, solved by chi-squared |
| Simple substitution | start from frequency ranks, hill-climb by swapping two key letters when the English quadgram score rises, 10 restarts with 4 random swaps each (the first 600 letters are scored) |
| Columnar transposition | for each width 2..8, search the column order with the same quadgram score (swap two columns, several restarts); the highest-scoring width wins, the smallest width on a tie |
| auto | picks what to try from the index of coincidence of the whole text, runs those breakers, keeps the highest quadgram score |

The restarts use a fixed seed (a 32-bit LCG), so a run is repeatable and the Python and JavaScript versions print identical traces.
English statistics (letter frequencies and the 9,000 most common quadgrams, as integer log10 scores) were counted from six public-domain Project Gutenberg texts (#1342, #2701, #11, #1661, #84, #98) by `build_data.py`.

## What it got right in our test (one passage, one key per cipher)

`python3 -I tests/accuracy.py` on a 431-letter passage written for the test, cut to 431, 250 and 150 letters:

```
cipher (key)             | 431 letters | 250 letters | 150 letters
caesar (7)               | exact 0.0s | exact 0.0s | exact 0.0s
atbash (-)               | exact 0.0s | exact 0.0s | exact 0.0s
vigenere (LEMON)         | exact 0.0s | exact 0.0s | exact 0.0s
vigenere (CIPHERS)       | exact 0.0s | exact 0.0s | exact 0.0s
substitution (XYLKWBFZ)  | exact 1.2s | exact 0.7s | 106 of 150 letters wrong 0.5s
columnar (ZEBRAS)        | exact 1.0s | 243 of 250 letters wrong 0.5s | exact 0.3s
columnar (KEYWORD)       | exact 1.0s | exact 0.6s | exact 0.3s
```

Read this as a sample, not a benchmark. The substitution break at 150 letters did not recover the text. The columnar ZEBRAS break at 250 letters found a plaintext that scores slightly higher than the true one but is shifted by one letter (so nearly every position differs). Statistical breaks need enough text; timings are from one machine and vary.
Not covered: ciphers that keep spaces or punctuation in the key, nulls, digraph and machine ciphers (Playfair, Enigma), non-English text, and columnar variants with double transposition.

## Tests

```
python3 -I tests/test_cipher_trainer.py     # known-plaintext round trips for every cipher
node tests/core.test.js                     # the same round trips in the JavaScript port
node tests/parity.test.js                   # CLI parity: Python CLI (--json) and core.js give the same key, plaintext and full trace on fixed vectors
node tests/ui.test.js                       # page wiring against a stub DOM, no network API, no external resource
node tests/readme.test.js                   # the README transcript equals the CLI output
```

## Related

Unrelated to ciphers but also puzzle software from the same author: a paid solver for packing puzzles, [Packing Puzzle Solver Pro](https://gumroad.com/l/wmuhsu) (pentomino and custom piece sets, separate product). This project is free and MIT licensed.
