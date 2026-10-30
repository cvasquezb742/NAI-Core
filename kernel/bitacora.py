"""
NAI-Core v22.11 - Bitácora del kernel
=====================================
Registro cronológico de todo lo que ocurre en el sistema: creación de
procesos, rechazos por memoria, cambios de contexto, operaciones del
semáforo, detección de deadlock, etc.

Se puede exportar a un archivo .txt, que sirve como evidencia ("volcado de
texto") para la bitácora de casos de prueba del documento técnico.
"""

import os
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Evento:
    hora: str          # Hora real del sistema (HH:MM:SS)
    reloj: int         # Tiempo simulado del kernel (unidades de tiempo)
    tipo: str          # Categoría: SISTEMA, PROCESO, MEMORIA, CPU, ERROR...
    mensaje: str


class Bitacora:
    """Almacena y exporta los eventos del kernel."""

    def __init__(self) -> None:
        self.eventos: list[Evento] = []

    def registrar(self, tipo: str, mensaje: str, reloj: int = 0) -> None:
        # Se guardan dos tiempos: la hora real (cuándo ocurrió en la demo) y
        # el reloj simulado del kernel (en qué unidad de tiempo del sistema).
        hora = datetime.now().strftime("%H:%M:%S")
        self.eventos.append(Evento(hora, reloj, tipo, mensaje))

    def ultimos(self, cantidad: int) -> list[Evento]:
        return self.eventos[-cantidad:]

    def exportar(self, carpeta: str) -> str:
        """Escribe la bitácora completa en un .txt y devuelve la ruta."""
        os.makedirs(carpeta, exist_ok=True)
        nombre = datetime.now().strftime("bitacora_%Y%m%d_%H%M%S.txt")
        ruta = os.path.join(carpeta, nombre)
        with open(ruta, "w", encoding="utf-8") as archivo:
            archivo.write("NAI-Core v22.11 - Bitácora del kernel\n")
            archivo.write(f"Exportada: {datetime.now():%d/%m/%Y %H:%M:%S}\n")
            archivo.write("=" * 70 + "\n")
            for e in self.eventos:
                archivo.write(f"[{e.hora}] t={e.reloj:<4} {e.tipo:<9} {e.mensaje}\n")
        return ruta
