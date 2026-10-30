"""
NAI-Core v22.11 - Interbloqueo (Deadlock)
=========================================
El sistema tiene dos recursos exclusivos (no apropiativos): R1 y R2. Solo un
proceso puede retener cada uno y nadie se los puede quitar a la fuerza.

Un deadlock aparece cuando se cumplen las cuatro condiciones de Coffman:
exclusión mutua, retención y espera, no apropiación y ESPERA CIRCULAR.
NAI-Core fuerza la espera circular clásica:

    Proceso A retiene R1 y solicita R2
    Proceso B retiene R2 y solicita R1

Detección: se construye el grafo de espera ("PID x espera a PID y") y se busca
un ciclo. Si existe, hay deadlock.

Resolución: el usuario aborta uno de los procesos del ciclo (como "Finalizar
tarea" en el Administrador de tareas). Sus recursos se liberan, se entregan
al proceso que los esperaba y el ciclo se rompe.
"""

from dataclasses import dataclass


class ErrorRecurso(Exception):
    """Operación inválida sobre los recursos (el mensaje se muestra al usuario)."""


@dataclass
class Recurso:
    nombre: str
    descripcion: str
    dueno: int | None = None


class AdministradorRecursos:
    def __init__(self, kernel) -> None:
        self.kernel = kernel
        self.recursos = {
            "R1": Recurso("R1", "Recurso 1"),
            "R2": Recurso("R2", "Recurso 2"),
        }
        # Solicitudes pendientes en orden de llegada: PID -> recurso que espera
        self.esperando: dict[int, str] = {}

    # --- Asignación ----------------------------------------------------------
    def solicitar(self, pid: int, rid: str) -> bool:
        """Devuelve True si el recurso se asignó, False si el proceso quedó esperando."""
        recurso = self.recursos[rid]
        if recurso.dueno == pid:
            raise ErrorRecurso(f"PID {pid} ya retiene {rid}.")
        if pid in self.esperando:
            raise ErrorRecurso(f"PID {pid} ya está esperando {self.esperando[pid]}.")
        # Los recursos son no apropiativos: si está ocupado, NO se le quita
        # al dueño. El que pide queda BLOQUEADO esperando mientras conserva lo
        # que ya tenía ("retención y espera", una condición de Coffman).
        if recurso.dueno is None:
            recurso.dueno = pid
            self.kernel.log("DEADLOCK", f"PID {pid} solicita {rid}: asignado.")
            return True
        self.esperando[pid] = rid
        self.kernel.log("DEADLOCK", f"PID {pid} solicita {rid}: ocupado por PID "
                                    f"{recurso.dueno}, debe esperar.")
        self.kernel.bloquear(pid, f"esperando {rid}, retenido por PID {recurso.dueno}")
        return False

    def liberar_proceso(self, pid: int) -> list[tuple[str, int | None]]:
        """
        Libera todo lo que retiene un proceso que termina. Cada recurso liberado
        se entrega al primer proceso que lo esperaba. Devuelve [(recurso, nuevo_dueño)].
        """
        self.esperando.pop(pid, None)
        cambios = []
        for recurso in self.recursos.values():
            if recurso.dueno == pid:
                recurso.dueno = None
                nuevo = self._entregar_al_siguiente(recurso)
                cambios.append((recurso.nombre, nuevo))
        return cambios

    def _entregar_al_siguiente(self, recurso: Recurso) -> int | None:
        # El recurso liberado se entrega al primero que lo pidió (FIFO) y ese
        # proceso se desbloquea; así nadie se queda esperando para siempre.
        for pid, rid in list(self.esperando.items()):
            if rid == recurso.nombre:
                del self.esperando[pid]
                recurso.dueno = pid
                self.kernel.log("DEADLOCK", f"{recurso.nombre} liberado y asignado a PID {pid}.")
                self.kernel.desbloquear(pid, f"obtuvo {recurso.nombre}")
                return pid
        self.kernel.log("DEADLOCK", f"{recurso.nombre} liberado; queda disponible.")
        return None

    # --- Consultas -----------------------------------------------------------
    def recursos_de(self, pid: int) -> list[str]:
        return [r.nombre for r in self.recursos.values() if r.dueno == pid]

    def esperando_por(self, rid: str) -> list[int]:
        return [pid for pid, r in self.esperando.items() if r == rid]

    def grafo_espera(self) -> dict[int, int]:
        """Grafo de espera: PID que espera -> PID que retiene lo que espera."""
        return {pid: self.recursos[rid].dueno for pid, rid in self.esperando.items()
                if self.recursos[rid].dueno is not None}

    def detectar(self) -> list[int]:
        """
        Busca un ciclo en el grafo de espera. Cada proceso espera a lo sumo a
        otro, así que basta con seguir las flechas desde cada nodo: si se vuelve
        a un nodo del camino actual, ese tramo es el ciclo (deadlock).
        """
        grafo = self.grafo_espera()
        for inicio in grafo:
            camino = []
            actual = inicio
            while actual is not None and actual not in camino:
                camino.append(actual)
                actual = grafo.get(actual)
            # Si el recorrido vuelve a un proceso del camino, se cerró un
            # ciclo: cada uno espera al siguiente y ninguno puede avanzar.
            if actual is not None:
                return camino[camino.index(actual):]
        return []

    # --- Simulación del bloqueo mutuo ----------------------------------------
    def forzar_interbloqueo(self):
        """
        Crea Proceso A y Proceso B y provoca la espera circular:
        A toma R1, B toma R2, A pide R2 (espera) y B pide R1 (espera).
        Devuelve (pcb_a, pcb_b). Puede lanzar MemoriaInsuficienteError.
        """
        if any(r.dueno is not None for r in self.recursos.values()) or self.esperando:
            raise ErrorRecurso("R1 o R2 ya están en uso. Resuelva el interbloqueo actual "
                               "o termine esos procesos antes de forzar otro.")
        k = self.kernel
        a = k.crear_proceso("Proceso_A", 8, 6)
        try:
            b = k.crear_proceso("Proceso_B", 8, 6)
        except Exception:
            # Si B no cabe en memoria se deshace la creación de A, para no
            # dejar un proceso suelto que nunca participará en el deadlock.
            k.terminar_proceso(a.pid, "no hubo memoria para Proceso_B", abortado=True)
            raise
        # El orden importa: primero cada uno toma UN recurso y después pide el
        # del otro. Si A pidiera R1 y R2 seguidos antes que B, no habría ciclo.
        # Pedir siempre los recursos en el mismo orden (R1 antes que R2) es,
        # justamente, la forma de prevenir este interbloqueo.
        k.log("DEADLOCK", "Forzando espera circular entre Proceso_A y Proceso_B.")
        self.solicitar(a.pid, "R1")
        self.solicitar(b.pid, "R2")
        self.solicitar(a.pid, "R2")
        self.solicitar(b.pid, "R1")
        ciclo = self.detectar()
        if ciclo:
            k.log("DEADLOCK", f"¡DEADLOCK DETECTADO! Ciclo de espera entre PIDs {ciclo}.")
        return a, b
