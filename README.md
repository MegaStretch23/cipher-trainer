# cipher-trainer

Break classical ciphers and **see every step**. Give it a ciphertext and it works out the cipher, the key and the plaintext, and with `--explain` it prints the reasoning a codebreaker would write on paper: the letter-frequency table, the index of coincidence, the Kasiski repeats, the key-length estimate, chi-squared per column, and the hill climb for substitution ciphers.

- Ciphers: **Caesar, Atbash, Vigenere, simple substitution, rail fence, columnar transposition**.
- Python 3.9+, **standard library only**. Nothing to install to run it, no network access, no data downloads (the English model is built from a text embedded in the source).
- Made for learning and for puzzles (CTF warm-ups, escape rooms, geocaches, history). These ciphers are not secure; do not use them to protect anything.

## Quickstart

```bash
git clone https://github.com/MegaStretch23/cipher-trainer.git
cd cipher-trainer

# make a practice ciphertext
python -m cipher_trainer encrypt vigenere -k LEMON -f examples/plain-2.txt > mystery.txt

# break it and show every step
python -m cipher_trainer break vigenere -f mystery.txt --explain

# do not know the cipher? let it try all six and pick the most English-looking result
python -m cipher_trainer break auto -f mystery.txt

# just the statistics (frequencies, IC, chi-squared, Kasiski), no solving
python -m cipher_trainer analyze -f mystery.txt
```

`pip install .` also gives a `cipher-trainer` command. Text comes from `--text "..."`, `--file F` or stdin. `--json` prints the result as JSON, `--seed N` changes the seed of the substitution / wide-columnar searches (default 1, runs are reproducible).

`encrypt` / `decrypt` take `-k`: a number (Caesar, rail fence rails), a word (Vigenere, columnar), 26 letters (substitution, plain A..Z maps to those letters), or column numbers such as `3,1,2` (columnar: the order the columns are read off).

## How each break works

| cipher | what the tool does |
|---|---|
| Caesar | decrypts with all 26 shifts and ranks them by chi-squared against English letter frequencies |
| Atbash | no key: one mirrored alphabet, confirmed by chi-squared and trigram score |
| Vigenere | index of coincidence of the text, Kasiski repeats and factor votes, average column IC for each key length, then each shortlisted length is solved column by column (chi-squared) and the decrypted text is scored; the smallest length that scores near the best wins |
| substitution | frequency-rank first guess, then hill climbing on letter swaps scored by English trigrams, with a cooling schedule so it can leave dead ends, several restarts, and a final polish that also rewards common words |
| rail fence | tries 2 to 12 rails, scores each decryption |
| columnar | widths 2 to 10: all column orders up to width 7, a seeded hill climb on column swaps and moves for 8 to 10 |

The English scorer is a smoothed trigram model trained on a short embedded text plus a common-word bonus. It ranks candidates well on a few hundred letters; it is not a language detector, and the verdict line (`reads as English` / `possibly English` / `not English`) says so when the best result still looks wrong.

## Real sample output

Every file below is in `examples/` and was produced by `sh examples/regenerate.sh` with this exact code. The plaintexts are three short invented messages (`examples/plain-*.txt`).

### Vigenere, key LEMON (`examples/vigenere-explain.txt`)

```text
Vigenere: a repeating keyword picks a different Caesar shift for each position. Plan: (1) find the key length, (2) solve each column as a Caesar.
step 1a  index of coincidence of the whole text = 0.0415 (English 0.0667, random 0.0385): low means several alphabets
step 1b  Kasiski: 5 repeated 3-letter distances; examples XTS at distance 55, EZR at distance 85, ELQ at distance 100, HUP at distance 95, LQB at distance 51
         Kasiski factor votes (key length: votes): 5: 4, 17: 2, 11: 1, 2: 1, 4: 1
step 1c  average IC of the columns if the key length were L (English-like columns are near 0.066):
         ... (other lengths trimmed here, all in the file)
         L= 4  IC 0.0460  ##################
         L= 5  IC 0.0629  #########################
         L= 6  IC 0.0452  ##################
         L= 7  IC 0.0400  ################
step 1d  shortlist (IC near the best, IC >= 0.055 or a top Kasiski vote, at least 6 letters per column): [5, 10, 11, 15, 17, 20]
         try L= 5: key LEMON  English score -1.889
         try L=10: key LEMONLEMON  English score -1.889
         try L=11: key HDNNDVVASKA  English score -4.052
         try L=15: key LEMOWLEMONLEWDN  English score -2.570
         try L=17: key LMBWPNNBOOIEENJSS  English score -3.821
         try L=20: key LEMZNHMNOMLEMOALSMON  English score -3.033
         key length = 5 (smallest length within 0.03 of the best score -1.889)
step 2   the 5 columns, each solved as a Caesar cipher with chi-squared:
         column 1 (37 letters): best shift 11 = 'L' chi2    16.7 (next best 110.9)
         column 2 (37 letters): best shift  4 = 'E' chi2    22.4 (next best 93.2)
         column 3 (36 letters): best shift 12 = 'M' chi2    16.6 (next best 105.7)
         column 4 (36 letters): best shift 14 = 'O' chi2    15.1 (next best 88.8)
         column 5 (36 letters): best shift 13 = 'N' chi2    32.7 (next best 75.0)
key = LEMON

cipher:    vigenere
key:       LEMON
score:     -1.889  (reads as English)
plaintext: Attack the bridge at dawn and hold it until the second company has crossed the river. Send the signal by lamp when the road is clear, and burn every paper that mentions the name of the village before you leave the camp tonight.
```

### Simple substitution (`examples/substitution-explain.txt`)

```text
Simple substitution: one fixed mapping of the 26 letters (26! keys, too many to try), so we climb: start from a guess, swap two letters, keep the swap if the English score rises.
letter frequencies (217 letters), top 8 vs English:
  T    32   14.7%  #############################   (English T: 9.1%)
  G    22   10.1%  ####################   (English G: 2.0%)
  Z    19    8.8%  ##################   (English Z: 0.1%)
  I    17    7.8%  ################   (English I: 7.0%)
  L    15    6.9%  ##############   (English L: 4.0%)
  O    14    6.5%  #############   (English O: 7.5%)
  K    14    6.5%  #############   (English K: 0.8%)
  F    13    6.0%  ############   (English F: 2.2%)
step 1  rank ciphertext letters by frequency and line them up with English order ETAOINSHRDLCUMWFGYPBVKJXQZ:
        T->E G->T Z->A I->O L->I O->N K->S F->H R->R X->D
        score of that first guess: -3.606   NUGTDLSESELRNHFAONIAOEHGTDOLYEUTDHRAOEHT
step 2  hill climb with a cooling schedule: propose a swap of two table entries, keep it if the trigram score rises, and keep a worse one with probability exp(drop/T) while T cools (escapes dead ends); 6 restarts (seed 1; the first starts from the frequency guess, the others from shuffles), each finished by plain greedy swaps
        restart 1: score -2.125  IFYOUAREREADINGTHISTHENYOUHAVEFOUNDTHENO
        restart 2: score -2.134  IFCOUAREREADINGTHISTHENCOUHAVEFOUNDTHENO
        restart 3: score -2.134  IFCOUAREREADINGTHISTHENCOUHAVEFOUNDTHENO
        restart 4: score -2.544  IFYOUAREREADINGSTIMSTENYOUTAVEFOUNDSTENO
        restart 5: score -2.870  OCKEYILALAITOSUNDOWNDASKEYDIBACEYSTNDASE
        restart 6: score -2.128  IFYOUAREREADINGTHISTHENYOUHAVEFOUNDTHENO
step 3  best score -2.125; plaintext letter for each cipher letter A..Z: KJVMCNOPHXRSZYIQADLEGWBUFT
key (plain A..Z -> cipher letters) = QWERTYUIOBASDFGHPKLZXCVJNM

cipher:    substitution
key:       QWERTYUIOBASDFGHPKLZXCVJNM
score:     -1.627  (reads as English)
plaintext: If you are reading this then you have found the notebook behind the loose stone in the cellar. The map shows where the silver is buried, but do not dig before the first frost, because the ground near the old well is soft and the neighbors would see you from their windows.
```

A plain letter that never occurs in the message (here J, Q and X) cannot be recovered, so its key entry is filled in arbitrarily; the plaintext is unaffected.

### Columnar transposition, key ZEBRAS (`examples/columnar-explain.txt`)

```text
Columnar transposition: the plaintext is written in rows under a keyword; the columns are read off in the keyword's alphabetical order. Letter counts stay English.
step 1  IC 0.0757 and chi-squared 31.2: English letters in the wrong order
step 2  for each width W: widths up to 7 try all W! column orders; wider ones hill-climb on column swaps and moves (seeded). Score = trigram log-probability:
        width  2 (all orders) best score -3.309  LIOUEPNTTHESYBOURITUYIWERHLEELCOPREE
        width  3 (all orders) best score -3.272  IHGUTSPKETSWHRASTUBPOUTLIAVUOEIDFEHA
        width  4 (all orders) best score -3.199  EOLINROURGEPRDNTEETHDNESEKYBRROURSRI
        width  5 (all orders) best score -3.284  ILDWTUAERCPTHNTTBTATHTAESSEUEDBEAPTU
        width  6 (all orders) best score -2.308  THELIGHTHOUSEKEEPERSENTWORDTHATTHESU
        width  7 (all orders) best score -3.247  SOFTCWILNAPPEUHEEAESPHAADHATNELEFAHD
        width  8 (hill climb) best score -3.133  ALINOEAEOOURRENSDEPRGGATHNTEDLOTHTHD
        width  9 (hill climb) best score -3.075  EWEHSTHIGERROATTUSPLREALKPETEVAOSSTW
        width 10 (hill climb) best score -3.119  LOHILLDOLVOTHUWSELANECNPRTHVTHNTDTNK
best = width 6, read order of columns (1-based) [5, 3, 2, 4, 6, 1]
key = 5,3,2,4,6,1  (column numbers in the order they were read off the grid)

cipher:    columnar
key:       5,3,2,4,6,1
score:     -2.041  (reads as English)
plaintext: THELIGHTHOUSEKEEPERSENTWORDTHATTHESUPPLYBOATWOULDARRIVEONTUESDAYIFTHEWEATHERHELDPLEASETELLTHECOOKTOPREPAREENOUGHBREADFORTWELVEMENANDASKTHEHARBORMASTERTOLEAVETHENORTHGATEUNLOCKEDUNTILTHETIDEHASTURNED
```

### Unknown cipher, `break auto` on a Caesar text (`examples/caesar-auto-explain.txt`)

```text
AUTO: diagnose first, then run every solver and keep the most English-looking result.
input: 198 letters
letter frequencies (198 letters), top 8 vs English:
  P    34   17.2%  ##################################   (English P: 1.9%)
  ...
  -> if chi-squared is also LOW the letters are English letters in a new ORDER (transposition); if chi-squared is high they were REPLACED (substitution)
Kasiski: 15 repeated 3-letter distances; examples ESP at distance 31, ESP at distance 35, ESP at distance 6, ESP at distance 18, ESP at distance 45
Kasiski factor votes (key length: votes): 3: 7, 5: 5, 2: 4, 9: 3, 15: 3
trying every cipher; final score = trigram log-probability + small common-word bonus (higher is better):
  caesar       score -2.041  key 11  THELIGHTHOUSEKEEPERSENTWORDTHATTHESU
  atbash       score -5.183  key None  VHKDGIHVHAUWKEKKZKXWKBVSAXLVHOVVHKWU
  vigenere     score -2.041  key L  THELIGHTHOUSEKEEPERSENTWORDTHATTHESU
  substitution score -2.046  key LMNOPHRSTBVWQYZAUCDEFGXIJK  THELIGHTHOUSEKEEPERSENTFORDTHATTHESU
  railfence    score -4.299  key 7  EPCLOCEEQDCCSDTPZZSWCEGPPYPPEPPLHWZE
  columnar     score -4.014  key 10,3,1,5,8,7,9,6,2,4  JSDYPSAOCEMPPEDLCAESZYYTOCPWHPLZEWLM
winner: caesar (reads as English)
```

Caesar and Vigenere (key length 1) tie here because a Caesar cipher is a one-letter Vigenere key; ties go to the simpler cipher. `examples/railfence-auto-explain.txt` is the same run on a rail fence text.

## Limits (read these)

- Short texts break less often. Under about 80 letters, substitution and wide columnar results can be wrong, and the score will say so (`possibly English` or `not English`). a Vigenere key that is a large fraction of the text length is unlikely to be found by these statistics.
- Columnar widths 8 to 10 use a hill climb, not an exhaustive search. It can end on a nearly readable text that is off by one rotation of the grid; the score shows how close it is. Widths 2 to 7 are exhaustive.
- Transposition ciphers are solved on letters only; the output is upper case without spaces. Caesar, Atbash, Vigenere and substitution keep your case, spaces and punctuation.
- The tool assumes English plaintext and the 26-letter A-Z alphabet. Digits and accented letters are passed through or dropped, not analysed.
- Variants such as autokey, Playfair, null ciphers or a keyed rail fence with an offset are not covered.

## Tests

```bash
pip install pytest
python -m pytest        # 28 tests, about 25 seconds
```

The tests cover known cipher vectors, round trips, every solver on a generated ciphertext, key recovery for three Vigenere keys, reproducibility of the seeded searches, the CLI (`--explain`, `--json`, exit codes) and the "wrong cipher is flagged" case.

## Also by the author

I also run pay-per-event data tools on Apify, for example the [SEC Form 4 insider cluster scanner](https://apify.com/johnveds15/sec-form4-insider-clusters). They are unrelated to ciphers; there is no paid version of cipher-trainer.

MIT licensed.

## Merged from classical-cipher-trainer

`classical-cipher-trainer` was the same idea built twice. Its own files are kept in [`merged/classical-cipher-trainer/`](merged/classical-cipher-trainer/) (unique parts: see that folder's README and tests); the old repo now points here: https://github.com/MegaStretch23/classical-cipher-trainer
