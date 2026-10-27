"""
NAI-Core v22.11 - Simulador de Funciones del Kernel de un Sistema Operativo
===========================================================================
Proyecto final de Sistemas Operativos I - Universidad Mariano Gálvez de Guatemala.
Autor: Christofer Josue Vasquez Baltazar

Ejecutar con:  python main.py
"""

from interfaz.menu import consola, ejecutar


def main() -> None:
    try:
        ejecutar()
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C o cierre de la entrada: salir sin mostrar un error técnico.
        consola.print("\n[cyan]NAI-Core se cerró de forma segura.[/]")


if __name__ == "__main__":
    main()
