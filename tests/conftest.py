import sys
from pathlib import Path

# Asegura que los tests importen el código fuente de src/, no una copia instalada.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
