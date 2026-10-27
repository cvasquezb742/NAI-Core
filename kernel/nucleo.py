"""
NAI-Core v22.11 - Núcleo (Kernel)
=================================
Punto central del simulador. El kernel es dueño de la tabla de procesos, del
administrador de memoria, del reloj del sistema y de la bitácora. La interfaz
nunca modifica esas estructuras directamente: siempre se lo pide al kernel,
igual que un programa real usa llamadas al sistema.
"""

from config import (NOMBRE_SISTEMA, QUANTUM, RAM_TOTAL_MB, TAMANO_MARCO_MB,
                    TOTAL_MARCOS, VERSION)
from kernel.bitacora import Bitacora
from kernel.memoria import AdministradorMemoria, MemoriaInsuficienteError
from kernel.pcb import PCB, Estado


class Kernel:
    def __init__(self) -> None:
        self.bitacora = Bitacora()
        self.memoria = AdministradorMemoria(TOTAL_MARCOS, TAMANO_MARCO_MB)
        self.procesos: dict[int, PCB] = {}    # Tabla de procesos: PID -> PCB
        self.reloj = 0                        # Tiempo simulado del sistema
        self._siguiente_pid = 1
        self.log("SISTEMA",
                 f"{NOMBRE_SISTEMA} v{VERSION} iniciado. RAM {RAM_TOTAL_MB} MB "
                 f"en {TOTAL_MARCOS} marcos de {TAMANO_MARCO_MB} MB, quantum = {QUANTUM}.")

    def log(self, tipo: str, mensaje: str) -> None:
        self.bitacora.registrar(tipo, mensaje, self.reloj)

    # --- Gestión de procesos -------------------------------------------------
    def crear_proceso(self, nombre: str, tamano_mb: int, rafaga: int) -> PCB:
        """
        Llamada al sistema para crear un proceso:
        1. Se pide memoria al administrador (paginación).
        2. Si no hay espacio, se rechaza con Out of Memory y no se crea el PCB.
        3. Si hay espacio, se crea el PCB, pasa de NUEVO a LISTO y entra a la
           tabla de procesos.
        """
        pid = self._siguiente_pid
        try:
            tabla_paginas = self.memoria.asignar(pid, tamano_mb)
        except MemoriaInsuficienteError as error:
            self.log("ERROR", f"Proceso '{nombre}' rechazado. {error}")
            raise

        # El PID solo se consume si el proceso fue aceptado.
        self._siguiente_pid += 1
        pcb = PCB(pid=pid, nombre=nombre, tamano_mb=tamano_mb,
                  rafaga_total=rafaga, tiempo_llegada=self.reloj,
                  tabla_paginas=tabla_paginas)
        self.procesos[pid] = pcb
        n = len(tabla_paginas)
        self.log("MEMORIA", f"PID {pid}: {n} página{'s' if n != 1 else ''} -> "
                            f"marco{'s' if n != 1 else ''} {tabla_paginas}.")
        pcb.estado = Estado.LISTO
        self.log("PROCESO", f"PID {pid} '{nombre}' creado ({tamano_mb} MB, ráfaga {rafaga}). "
                            f"NUEVO -> LISTO.")
        return pcb

    def terminar_proceso(self, pid: int, motivo: str = "finalizó su ráfaga") -> None:
        """Pasa un proceso a TERMINADO y devuelve sus marcos a la memoria."""
        pcb = self.procesos[pid]
        liberados = self.memoria.liberar(pid)
        pcb.estado = Estado.TERMINADO
        pcb.tiempo_finalizacion = self.reloj
        self.log("PROCESO", f"PID {pid} '{pcb.nombre}' TERMINADO ({motivo}). "
                            f"{liberados} marcos liberados.")

    def procesos_activos(self) -> list[PCB]:
        return [p for p in self.procesos.values() if p.estado != Estado.TERMINADO]

    def procesos_listos(self) -> list[PCB]:
        return [p for p in self.procesos.values() if p.estado == Estado.LISTO]
