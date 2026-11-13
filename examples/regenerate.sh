#!/bin/sh
# Rebuilds every file in this folder from the three plaintexts. Run from the repo root: sh examples/regenerate.sh
set -e
CT="python3 -m cipher_trainer"
cd "$(dirname "$0")/.."
cd examples
( cd ..
  $CT encrypt caesar -k 11 -f examples/plain-1.txt > examples/caesar.ct.txt
  $CT break auto -f examples/caesar.ct.txt --explain > examples/caesar-auto-explain.txt
  $CT encrypt vigenere -k LEMON -f examples/plain-2.txt > examples/vigenere.ct.txt
  $CT break vigenere -f examples/vigenere.ct.txt --explain > examples/vigenere-explain.txt
  $CT encrypt substitution -k QWERTYUIOPASDFGHJKLZXCVBNM -f examples/plain-3.txt > examples/substitution.ct.txt
  $CT break substitution -f examples/substitution.ct.txt --explain > examples/substitution-explain.txt
  $CT encrypt columnar -k ZEBRAS -f examples/plain-1.txt > examples/columnar.ct.txt
  $CT break columnar -f examples/columnar.ct.txt --explain > examples/columnar-explain.txt
  $CT encrypt railfence -k 4 -f examples/plain-2.txt > examples/railfence.ct.txt
  $CT break auto -f examples/railfence.ct.txt --explain > examples/railfence-auto-explain.txt )
