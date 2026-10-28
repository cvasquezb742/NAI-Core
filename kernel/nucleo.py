"""
NAI-Core v22.11 - Núcleo (Kernel)
=================================
Punto central del simulador. El kernel es dueño de la tabla de procesos, del
administrador de memoria, del planificador, del semáforo, de los recursos y
del reloj del sistema. La interfaz nunca modifica esas estructuras
directamente: siempre se lo pide al kernel, igual que un programa real usa
llamadas al sistema.
"""

from dataclasses import dataclass, field

from config import (NOMBRE_SISTEMA, QUANTUM, RAM_TOTAL_MB, TAMANO_MARCO_MB,
                    TOTAL_MARCOS, VERSION)
from kernel.bitacora import Bitacora
from kernel.interbloqueo import AdministradorRecursos
from kernel.memoria import AdministradorMemoria, MemoriaInsuficienteError
from kernel.pcb import PCB, Estado
from kernel.planificador import PlanificadorRR
from kernel.sincronizacion import AdministradorConcurrencia


@dataclass
class ResultadoTerminacion:
    """Resumen de lo que se liberó al terminar un proceso."""

    marcos_liberados: int
    recursos: list = field(default_factory=list)   # [(recurso, nuevo_dueño)]
    despertado_semaforo: int | None = None


class Kernel:
    def __init__(self, bitacora: Bitacora | None = None) -> None:
        self.bitacora = bitacora or Bitacora()
        self.memoria = AdministradorMemoria(TOTAL_MARCOS, TAMANO_MARCO_MB)
        self.procesos: dict[int, PCB] = {}    # Tabla de procesos: PID -> PCB
        self.reloj = 0                        # Tiempo simulado del sistema
        self._siguiente_pid = 1
        self.planificador = PlanificadorRR(self, QUANTUM)
        self.concurrencia = AdministradorConcurrencia(self)
        self.recursos = AdministradorRecursos(self)
        self.log("SISTEMA",
                 f"{NOMBRE_SISTEMA} v{VERSION} iniciado. RAM {RAM_TOTAL_MB} MB "
                 f"en {TOTAL_MARCOS} marcos de {TAMANO_MARCO_MB} MB, quantum = {QUANTUM}.")

    def log(self, tipo: str, mensaje: str) -> None:
        self.bitacora.registrar(tipo, mensaje, self.reloj)

    def reiniciar(self) -> None:
        """Vacía la memoria y la tabla de procesos conservando la bitácora."""
        self.log("SISTEMA", "Reinicio solicitado: se eliminan todos los procesos.")
        self.__init__(self.bitacora)

    # --- Creación de procesos ------------------------------------------------
    def crear_proceso(self, nombre: str, tamano_mb: int, rafaga: int) -> PCB:
        """
        Llamada al sistema para crear un proceso:
        1. Se pide memoria al administrador (paginación).
        2. Si no hay espacio, se rechaza con Out of Memory y no se crea el PCB.
        3. Si hay espacio, se crea el PCB, pasa de NUEVO a LISTO y entra al
           final de la cola de listos del planificador.
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
        self.planificador.encolar(pid)
        self.log("PROCESO", f"PID {pid} '{nombre}' creado ({tamano_mb} MB, ráfaga {rafaga}). "
                            f"NUEVO -> LISTO.")
        return pcb

    # --- Transiciones de estado ----------------------------------------------
    def bloquear(self, pid: int, motivo: str) -> None:
        """LISTO -> BLOQUEADO: el proceso sale de la cola de listos."""
        pcb = self.procesos[pid]
        pcb.estado = Estado.BLOQUEADO
        self.planificador.retirar(pid)
        self.log("PROCESO", f"PID {pid} '{pcb.nombre}' LISTO -> BLOQUEADO ({motivo}).")

    def desbloquear(self, pid: int, motivo: str) -> None:
        """BLOQUEADO -> LISTO: el proceso vuelve al final de la cola de listos."""
        pcb = self.procesos[pid]
        if pcb.estado == Estado.TERMINADO:
            return
        pcb.estado = Estado.LISTO
        self.planificador.encolar(pid)
        self.log("PROCESO", f"PID {pid} '{pcb.nombre}' BLOQUEADO -> LISTO ({motivo}).")

    def terminar_proceso(self, pid: int, motivo: str = "completó su ráfaga",
                         abortado: bool = False) -> ResultadoTerminacion:
        """
        Pasa un proceso a TERMINADO y le quita todo lo que tenía: su lugar en
        la cola de listos, el semáforo, los recursos R1/R2 y sus marcos de
        memoria. Si otro proceso esperaba algo de lo liberado, se desbloquea.
        Es lo mismo que hace "Finalizar tarea" en el Administrador de tareas.
        """
        pcb = self.procesos[pid]
        pcb.estado = Estado.TERMINADO
        pcb.abortado = abortado
        pcb.tiempo_finalizacion = self.reloj
        self.planificador.retirar(pid)
        despertado = self.concurrencia.liberar_proceso(pid)
        recursos = self.recursos.liberar_proceso(pid)
        marcos = self.memoria.liberar(pid)
        self.log("PROCESO", f"PID {pid} '{pcb.nombre}' TERMINADO ({motivo}). "
                            f"{marcos} marcos liberados.")
        return ResultadoTerminacion(marcos, recursos, despertado)

    # --- Consultas -----------------------------------------------------------
    def procesos_activos(self) -> list[PCB]:
        return [p for p in self.procesos.values() if p.estado != Estado.TERMINADO]

    def procesos_listos(self) -> list[PCB]:
        return [p for p in self.procesos.values() if p.estado == Estado.LISTO]

    def procesos_bloqueados(self) -> list[PCB]:
        return [p for p in self.procesos.values() if p.estado == Estado.BLOQUEADO]
