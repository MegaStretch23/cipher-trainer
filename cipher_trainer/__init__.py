"""cipher-trainer: classical-cipher cryptanalysis that explains every step. Standard library only."""
from .attacks import Result, Step, identify, solve
from .ciphers import CIPHERS, encrypt

__version__ = "0.1.0"
__all__ = ["solve", "identify", "encrypt", "CIPHERS", "Result", "Step"]
