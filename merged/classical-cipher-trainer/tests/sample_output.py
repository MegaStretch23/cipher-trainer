"""Prints the exact README quickstart transcript (run by tests/readme.test.js and used to paste into README.md)."""
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
CT = "ULEMSRQIRECHOXEFSIFVYUHRQSFVVRTTITOYTXAKFFBRDNWGULENOZQFEHCEFXHGGGPVMTSNDLEFHUFVOEYFTSTJSFIMPUQBVPDHWAEXHGVNSFOWFVOXHGRNSO"
print("$ python3 -I cipher_trainer.py break vigenere " + CT)
print(subprocess.run([sys.executable, "-I", str(ROOT / "cipher_trainer.py"), "break", "vigenere", CT], capture_output=True, text=True, check=True, cwd="/tmp").stdout.rstrip())
