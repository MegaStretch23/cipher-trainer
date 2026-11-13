#!/usr/bin/env bash
# Rebuilds every transcript in this folder from the public-domain samples in cipher_trainer/corpus.py.
# Usage: cd <repo root> && bash examples/regenerate.sh
set -euo pipefail
cd "$(dirname "$0")/.."
T="python3 -m cipher_trainer"
sample() { python3 -c "from cipher_trainer.corpus import SAMPLES; print(SAMPLES['$1'])"; }
run() {  # name sample cipher key
  sample "$2" > "examples/plain-$2.txt"
  $T encrypt -f "examples/plain-$2.txt" --cipher "$3" ${4:+--key "$4"} > "examples/$1.ciphertext.txt"
  { echo "\$ trainer encrypt -f examples/plain-$2.txt --cipher $3 ${4:+--key $4}"; echo "\$ trainer solve -f examples/$1.ciphertext.txt"; echo; $T solve -f "examples/$1.ciphertext.txt" || true; } > "examples/$1.transcript.txt"
}
run caesar scandal caesar 11
run vigenere oz vigenere CIPHER
run railfence emma railfence 4
run substitution treasure substitution QWERTYUIOPASDFGHJKLZXCVBNM
run substitution-near-miss emma substitution QWERTYUIOPASDFGHJKLZXCVBNM
python3 -c "
import random, sys
from cipher_trainer.stats import ALPHA
g = random.Random(0); print(''.join(g.choice(ALPHA) for _ in range(150)))" > examples/random.ciphertext.txt
{ echo "\$ trainer solve -f examples/random.ciphertext.txt   # 150 random letters, not a cipher"; echo; $T solve -f examples/random.ciphertext.txt || true; } > examples/random.transcript.txt
