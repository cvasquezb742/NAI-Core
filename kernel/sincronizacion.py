"""
NAI-Core v22.11 - Concurrencia y sincronización
===============================================
Escenario: varios procesos de un servidor de juego suman XP a un marcador
global compartido. Ese marcador es la SECCIÓN CRÍTICA: si dos procesos lo
leen y lo escriben al mismo tiempo, una de las sumas se pierde (condición de
carrera).

Para evitarlo se usa un SEMÁFORO BINARIO:
- S = 1 -> la sección crítica está libre.
- S = 0 -> la sección crítica está ocupada.
- wait(P):   si S = 1, el proceso entra y S pasa a 0. Si S = 0, el proceso se
             BLOQUEA y va a la cola de espera del semáforo.
- signal(P): el proceso sale. Si hay alguien en la cola, se le entrega el
             paso directamente (se desbloquea); si no, S vuelve a 1.
"""

from collections import deque
from dataclasses import dataclass

from config import INCREMENTO_SECCION_CRITICA


class ErrorSemaforo(Exception):
    """Operación inválida sobre el semáforo (el mensaje se muestra al usuario)."""


class SemaforoBinario:
    def __init__(self) -> None:
        self.valor = 1                         # 1 = libre, 0 = ocupado
        self.dueno: int | None = None          # PID dentro de la sección crítica
        self.cola_espera: deque[int] = deque() # PIDs bloqueados esperando entrar

    def wait(self, pid: int) -> bool:
        """Intenta entrar. Devuelve True si entró, False si quedó en espera."""
        if pid == self.dueno:
            raise ErrorSemaforo(f"PID {pid} ya está dentro de la sección crítica.")
        if pid in self.cola_espera:
            raise ErrorSemaforo(f"PID {pid} ya está en la cola de espera del semáforo.")
        if self.valor == 1:
            self.valor = 0
            self.dueno = pid
            return True
        self.cola_espera.append(pid)
        return False

    def signal(self, pid: int) -> int | None:
        """Sale de la sección crítica. Devuelve el PID despertado, si lo hay."""
        if pid != self.dueno:
            raise ErrorSemaforo(
                f"PID {pid} no puede hacer signal(): no está dentro de la sección crítica.")
        if self.cola_espera:
            # El paso se entrega directamente al siguiente; S se mantiene en 0.
            self.dueno = self.cola_espera.popleft()
            return self.dueno
        self.valor = 1
        self.dueno = None
        return None

    def retirar(self, pid: int) -> int | None:
        """Saca a un proceso que termina, esté dentro o esperando."""
        if pid in self.cola_espera:
            self.cola_espera.remove(pid)
            return None
        if pid == self.dueno:
            return self.signal(pid)
        return None


@dataclass
class PasoCarrera:
    """Una instrucción ejecutada durante la demostración de carrera."""

    paso: int
    pid: int
    instruccion: str
    local: int | None        # Copia local del marcador que tiene el proceso
    global_: int             # Valor real del marcador compartido
    detalle: str


class AdministradorConcurrencia:
    def __init__(self, kernel) -> None:
        self.kernel = kernel
        self.semaforo = SemaforoBinario()
        self.variable_global = 0

    # --- Operaciones del semáforo integradas con los estados del proceso -----
    def wait(self, pid: int) -> bool:
        entro = self.semaforo.wait(pid)
        if entro:
            self.kernel.log("SYNC", f"wait(): PID {pid} entra a la sección crítica (S = 0).")
        else:
            self.kernel.log("SYNC", f"wait(): sección crítica ocupada por PID "
                                    f"{self.semaforo.dueno}. PID {pid} a la cola de espera.")
            self.kernel.bloquear(pid, "esperando el semáforo")
        return entro

    def signal(self, pid: int) -> int | None:
        despertado = self.semaforo.signal(pid)
        if despertado is None:
            self.kernel.log("SYNC", f"signal(): PID {pid} sale de la sección crítica (S = 1).")
        else:
            self.kernel.log("SYNC", f"signal(): PID {pid} sale y entrega el paso a PID {despertado}.")
            self.kernel.desbloquear(despertado, "obtuvo el semáforo")
        return despertado

    def escribir_y_salir(self, pid: int) -> int | None:
        """El proceso dentro de la sección crítica suma su XP y hace signal()."""
        if pid != self.semaforo.dueno:
            raise ErrorSemaforo(f"PID {pid} no está dentro de la sección crítica.")
        self.variable_global += INCREMENTO_SECCION_CRITICA
        self.kernel.log("SYNC", f"PID {pid} suma {INCREMENTO_SECCION_CRITICA} XP. "
                                f"Marcador = {self.variable_global}.")
        return self.signal(pid)

    def liberar_proceso(self, pid: int) -> int | None:
        """Llamado por el kernel cuando un proceso termina."""
        despertado = self.semaforo.retirar(pid)
        if despertado is not None:
            self.kernel.log("SYNC", f"PID {pid} terminó dentro de la sección crítica; "
                                    f"el paso pasa a PID {despertado}.")
            self.kernel.desbloquear(despertado, "obtuvo el semáforo")
        return despertado

    # --- Demostración de condición de carrera --------------------------------
    def simular_carrera(self, pids: list[int], con_semaforo: bool) -> list[PasoCarrera]:
        """
        Cada proceso suma XP al marcador con tres instrucciones de máquina:
        LEER (copia el marcador a un registro), SUMAR (registro + XP) y
        ESCRIBIR (guarda el registro en el marcador). Con semáforo se agregan
        wait() al inicio y signal() al final.

        El planificador intercala los procesos UNA instrucción a la vez, como
        si el quantum se agotara después de cada instrucción: el peor caso
        posible para provocar una condición de carrera.
        """
        if self.semaforo.dueno is not None or self.semaforo.cola_espera:
            raise ErrorSemaforo("El semáforo está en uso. Libérelo con signal() antes de la demo.")

        programa = ["wait", "leer", "sumar", "escribir", "signal"] if con_semaforo \
            else ["leer", "sumar", "escribir"]
        modo = "CON semáforo" if con_semaforo else "SIN semáforo"
        self.variable_global = 0
        self.kernel.log("SYNC", f"Demostración de carrera {modo} con PIDs {pids}. Marcador = 0.")

        contador = {pid: 0 for pid in pids}     # Siguiente instrucción de cada proceso
        local = {pid: None for pid in pids}     # Registro local de cada proceso
        turnos = deque(pids)
        pasos: list[PasoCarrera] = []

        def registrar(pid, instruccion, detalle):
            pasos.append(PasoCarrera(len(pasos) + 1, pid, instruccion, local[pid],
                                     self.variable_global, detalle))

        while turnos:
            pid = turnos.popleft()
            instruccion = programa[contador[pid]]

            if instruccion == "wait":
                if self.wait(pid):
                    registrar(pid, "wait()", "Entra a la sección crítica (S = 0)")
                else:
                    registrar(pid, "wait()", "Ocupada: BLOQUEADO en la cola de espera")
                    continue   # No vuelve a la fila de turnos hasta que lo despierten
            elif instruccion == "leer":
                local[pid] = self.variable_global
                registrar(pid, "LEER", f"Copia el marcador ({local[pid]}) a su registro")
            elif instruccion == "sumar":
                local[pid] += INCREMENTO_SECCION_CRITICA
                registrar(pid, "SUMAR", f"Registro + {INCREMENTO_SECCION_CRITICA} = {local[pid]}")
            elif instruccion == "escribir":
                self.variable_global = local[pid]
                registrar(pid, "ESCRIBIR", f"Guarda {local[pid]} en el marcador")
            elif instruccion == "signal":
                despertado = self.signal(pid)
                if despertado is None:
                    registrar(pid, "signal()", "Sale; sección crítica libre (S = 1)")
                else:
                    registrar(pid, "signal()", f"Sale y despierta a PID {despertado}")
                    contador[despertado] += 1   # Su wait() se completa al despertar
                    turnos.append(despertado)

            contador[pid] += 1
            if contador[pid] < len(programa):
                turnos.append(pid)

        self.kernel.log("SYNC", f"Fin de la demo {modo}: marcador = {self.variable_global} "
                                f"(esperado {INCREMENTO_SECCION_CRITICA * len(pids)}).")
        return pasos
