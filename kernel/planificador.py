"""
NAI-Core v22.11 - Planificador Round Robin
==========================================
Round Robin reparte la CPU por turnos de duración fija (quantum, q = 3):

1. El despachador toma el proceso que está al frente de la cola de listos.
2. El proceso usa la CPU hasta q unidades de tiempo (o menos si termina antes).
3. Si terminó, sale del sistema y libera su memoria.
4. Si no terminó, ocurre un cambio de contexto: su estado de CPU se guarda en
   el TCB y el proceso vuelve al FINAL de la cola de listos.

Así ningún proceso acapara la CPU y todos avanzan de forma equitativa.

Métricas (las mismas fórmulas usadas en clase):
- CT  (tiempo de finalización) = instante en que el proceso termina
- TAT (tiempo de retorno)      = CT - tiempo de llegada
- WT  (tiempo de espera)       = TAT - ráfaga total
"""

from collections import deque
from dataclasses import dataclass

from kernel.pcb import Estado


@dataclass
class Segmento:
    """Un turno de CPU: un bloque del diagrama de Gantt."""

    pid: int
    nombre: str
    inicio: int
    fin: int
    restante: int
    terminado: bool

    @property
    def duracion(self) -> int:
        return self.fin - self.inicio


@dataclass
class FilaMetrica:
    pid: int
    nombre: str
    llegada: int       # AT
    rafaga: int        # BT
    finalizacion: int  # CT
    retorno: int       # TAT = CT - AT
    espera: int        # WT  = TAT - BT


@dataclass
class Metricas:
    filas: list[FilaMetrica]
    promedio_retorno: float
    promedio_espera: float
    utilizacion_cpu: float     # % del tiempo en que la CPU estuvo ocupada
    productividad: float       # procesos terminados por unidad de tiempo
    cambios_contexto: int


class PlanificadorRR:
    def __init__(self, kernel, quantum: int) -> None:
        self.kernel = kernel
        self.quantum = quantum
        self.cola_listos: deque[int] = deque()   # PIDs en orden de turno
        self.historial: list[Segmento] = []      # Diagrama de Gantt completo

    # --- Cola de listos ------------------------------------------------------
    def encolar(self, pid: int) -> None:
        if pid not in self.cola_listos:
            self.cola_listos.append(pid)

    def retirar(self, pid: int) -> None:
        if pid in self.cola_listos:
            self.cola_listos.remove(pid)

    def hay_listos(self) -> bool:
        return bool(self.cola_listos)

    # --- Ejecución -----------------------------------------------------------
    def ejecutar_quantum(self) -> Segmento | None:
        """Ejecuta un turno de CPU. Devuelve None si la cola está vacía."""
        if not self.cola_listos:
            return None
        k = self.kernel
        pid = self.cola_listos.popleft()
        pcb = k.procesos[pid]

        # Despacho: LISTO -> EJECUCIÓN
        pcb.estado = Estado.EJECUCION
        inicio = k.reloj
        k.log("CPU", f"Despachador: PID {pid} '{pcb.nombre}' entra a la CPU "
                     f"(ráfaga restante {pcb.rafaga_restante}).")

        usadas = pcb.ejecutar(self.quantum)
        k.reloj += usadas
        segmento = Segmento(pid, pcb.nombre, inicio, k.reloj,
                            pcb.rafaga_restante, pcb.rafaga_restante == 0)
        self.historial.append(segmento)

        if segmento.terminado:
            # El proceso terminó dentro de su quantum: sale del sistema.
            k.terminar_proceso(pid, "completó su ráfaga")
        else:
            # Quantum agotado: cambio de contexto y regreso al final de la cola.
            pcb.guardar_contexto()
            pcb.estado = Estado.LISTO
            self.cola_listos.append(pid)
            k.log("CPU", f"Quantum agotado en t={k.reloj}. Cambio de contexto: PID {pid} "
                         f"guardado (PC={pcb.tcb.contador_programa}, restante "
                         f"{pcb.rafaga_restante}) y enviado al final de la cola.")
        return segmento

    # --- Métricas ------------------------------------------------------------
    def metricas(self) -> Metricas:
        """Calcula CT, TAT y WT de los procesos que completaron su ráfaga."""
        terminados = [p for p in self.kernel.procesos.values()
                      if p.estado == Estado.TERMINADO and not p.abortado]
        filas = []
        for p in terminados:
            retorno = p.tiempo_finalizacion - p.tiempo_llegada
            filas.append(FilaMetrica(p.pid, p.nombre, p.tiempo_llegada, p.rafaga_total,
                                     p.tiempo_finalizacion, retorno, retorno - p.rafaga_total))
        tiempo_total = self.kernel.reloj
        ocupado = sum(s.duracion for s in self.historial)
        return Metricas(
            filas=filas,
            promedio_retorno=sum(f.retorno for f in filas) / len(filas) if filas else 0.0,
            promedio_espera=sum(f.espera for f in filas) / len(filas) if filas else 0.0,
            utilizacion_cpu=ocupado / tiempo_total * 100 if tiempo_total else 0.0,
            productividad=len(filas) / tiempo_total if tiempo_total else 0.0,
            cambios_contexto=sum(p.cambios_contexto for p in self.kernel.procesos.values()),
        )
