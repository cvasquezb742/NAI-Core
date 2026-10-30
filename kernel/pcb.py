"""
NAI-Core v22.11 - Bloque de Control de Proceso (PCB) y de Hilo (TCB)
====================================================================
En un sistema operativo real, el kernel no "ve" programas: ve estructuras de
datos que los describen. La más importante es el PCB (Process Control Block),
la "ficha" de cada proceso. Dentro de cada proceso hay al menos un hilo de
ejecución, descrito por su TCB (Thread Control Block).

- PCB: identidad y recursos del proceso (PID, estado, memoria, ráfagas...).
- TCB: estado de la CPU del hilo (contador de programa y registros). Es lo que
  se guarda y se restaura en cada cambio de contexto.
"""

from dataclasses import dataclass, field
from enum import Enum


class Estado(Enum):
    """Estados posibles de un proceso (modelo clásico de 5 estados)."""

    NUEVO = "Nuevo"            # Se está creando, aún sin memoria asignada
    LISTO = "Listo"            # En memoria, esperando turno de CPU
    EJECUCION = "Ejecución"    # Usando la CPU en este momento
    BLOQUEADO = "Bloqueado"    # Esperando un recurso o un semáforo
    TERMINADO = "Terminado"    # Finalizó o fue abortado; ya no tiene memoria


@dataclass
class TCB:
    """
    Thread Control Block del hilo principal de un proceso.

    Los registros son simulados: no corresponden a una CPU real, pero se
    actualizan en cada cambio de contexto para mostrar qué información debe
    preservar el sistema operativo cuando le quita la CPU a un hilo.
    """

    tid: int                       # Identificador del hilo
    pid: int                       # Proceso al que pertenece
    contador_programa: int = 0     # PC: siguiente "instrucción" a ejecutar
    registros: dict = field(default_factory=lambda: {"ACC": 0, "SP": 0xFF})

    def guardar_contexto(self, unidades_ejecutadas: int) -> None:
        """Simula el guardado de registros al salir de la CPU."""
        # Esto es lo que hace el SO en un cambio de contexto: copia el estado
        # de la CPU (PC y registros) al TCB. Cuando el hilo vuelva a tener su
        # turno, continúa exactamente desde donde se quedó.
        self.contador_programa = unidades_ejecutadas
        self.registros["ACC"] = unidades_ejecutadas * self.pid   # acumulador
        self.registros["SP"] = 0xFF - unidades_ejecutadas        # puntero de pila


@dataclass
class PCB:
    """
    Process Control Block. Contiene los campos exigidos por el enunciado
    (PID, estado, tamaño en memoria, ráfaga total y ráfaga restante) más
    información adicional que usan el planificador y el administrador de
    memoria.
    """

    pid: int
    nombre: str
    tamano_mb: int
    rafaga_total: int
    tiempo_llegada: int = 0
    estado: Estado = Estado.NUEVO
    rafaga_restante: int = field(init=False)
    tabla_paginas: list = field(default_factory=list)  # página i -> marco
    tiempo_finalizacion: int | None = None
    cambios_contexto: int = 0
    abortado: bool = False       # True si terminó por kill o para romper un deadlock
    tcb: TCB = field(init=False)

    def __post_init__(self) -> None:
        # Al crearse, al proceso le falta ejecutar toda su ráfaga.
        self.rafaga_restante = self.rafaga_total
        # Cada proceso nace con un hilo principal (TID = PID).
        self.tcb = TCB(tid=self.pid, pid=self.pid)

    @property
    def unidades_ejecutadas(self) -> int:
        return self.rafaga_total - self.rafaga_restante

    @property
    def marcos_asignados(self) -> int:
        return len(self.tabla_paginas)

    def ejecutar(self, unidades: int) -> int:
        """
        Consume hasta `unidades` de ráfaga y devuelve cuántas se usaron
        realmente (puede ser menos si el proceso termina antes del quantum).
        """
        # Se usa el mínimo entre el quantum y lo que le falta: si al proceso
        # le quedan 2 unidades y el quantum es 3, solo ocupa 2 y suelta la CPU
        # antes. Así nunca se "gasta" CPU de más.
        usadas = min(unidades, self.rafaga_restante)
        self.rafaga_restante -= usadas
        return usadas

    def guardar_contexto(self) -> None:
        """Cambio de contexto: el estado de la CPU se guarda en el TCB."""
        self.tcb.guardar_contexto(self.unidades_ejecutadas)
        self.cambios_contexto += 1
