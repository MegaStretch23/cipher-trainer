import json
from cipher_trainer import ciphers as C
from cipher_trainer.cli import main
from cipher_trainer.corpus import SAMPLES

PT = SAMPLES["scandal"]


def test_encrypt_cli(capsys):
    assert main(["encrypt", "Hello, World!", "--cipher", "caesar", "--key", "3"]) == 0
    assert capsys.readouterr().out.strip() == "Khoor, Zruog!"


def test_encrypt_cli_missing_key(capsys):
    assert main(["encrypt", "abc", "--cipher", "vigenere"]) == 2


def test_solve_cli_prints_numbered_steps(capsys):
    assert main(["solve", C.caesar_encrypt(PT, 6)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("1. Identify the cipher family") and "\n2. Attack: caesar" in out
    assert "CIPHER: caesar   KEY: 6" in out and "PLAINTEXT: To Sherlock Holmes" in out


def test_solve_cli_json(capsys):
    assert main(["solve", "--json", C.vigenere_encrypt(PT, "CIPHER")]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["best"]["cipher"] == "vigenere" and d["best"]["key"] == "CIPHER"


def test_solve_cli_file_and_forced_cipher(tmp_path, capsys):
    f = tmp_path / "ct.txt"; f.write_text(C.atbash(PT))
    assert main(["solve", "-f", str(f), "--cipher", "atbash"]) == 0
    assert "PLAINTEXT: To Sherlock Holmes" in capsys.readouterr().out


def test_analyze_cli(capsys):
    assert main(["analyze", C.vigenere_encrypt(PT, "LEMON")]) == 0
    assert "polyalphabetic" in capsys.readouterr().out
