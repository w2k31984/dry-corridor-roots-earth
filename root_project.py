"""Compatibilidad: la lógica vive en el paquete `raices_profundas`.

Equivalente a: python -m raices_profundas.cli "$@"
"""
from raices_profundas.cli import main

if __name__ == "__main__":
    main()
