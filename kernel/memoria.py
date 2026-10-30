"""
NAI-Core v22.11 - Administrador de memoria (Paginación simple)
=============================================================
La RAM física de 100 MB se divide en marcos de tamaño fijo (4 MB -> 25
marcos). Cada proceso se divide en páginas del mismo tamaño y cada página
se coloca en cualquier marco libre, aunque los marcos no estén contiguos.

Ventajas frente a la asignación contigua:
- No existe fragmentación externa: cualquier marco libre sirve.
- Solo hay fragmentación interna en la última página de cada proceso.

Si no hay suficientes marcos libres, el proceso se rechaza de inmediato con
el error Out of Memory (MemoriaInsuficienteError).
"""

import math


class MemoriaInsuficienteError(Exception):
    """Error de desbordamiento de memoria (Out of Memory)."""

    def __init__(self, tamano_mb: int, marcos_requeridos: int, marcos_libres: int,
                 tamano_marco_mb: int) -> None:
        self.tamano_mb = tamano_mb
        self.marcos_requeridos = marcos_requeridos
        self.marcos_libres = marcos_libres
        self.mb_libres = marcos_libres * tamano_marco_mb
        super().__init__(
            f"Out of Memory: el proceso de {tamano_mb} MB necesita "
            f"{marcos_requeridos} marcos y solo hay {marcos_libres} libres "
            f"({self.mb_libres} MB)."
        )


class AdministradorMemoria:
    """Gestiona la tabla de marcos de la RAM física simulada."""

    def __init__(self, total_marcos: int, tamano_marco_mb: int) -> None:
        self.total_marcos = total_marcos
        self.tamano_marco_mb = tamano_marco_mb
        # Tabla de marcos: cada posición guarda el PID dueño o None si está libre.
        self.marcos: list[int | None] = [None] * total_marcos
        # Tamaño real solicitado por cada proceso (para calcular fragmentación).
        self._tamanos: dict[int, int] = {}

    # --- Consultas -----------------------------------------------------------
    def marcos_necesarios(self, tamano_mb: int) -> int:
        """Páginas que ocupa un proceso: se redondea hacia arriba."""
        # Hacia arriba porque una página no se puede partir: 10 MB necesitan
        # 3 marcos (12 MB). Los 2 MB que sobran en la última página son la
        # fragmentación interna.
        return math.ceil(tamano_mb / self.tamano_marco_mb)

    def marcos_libres(self) -> int:
        return self.marcos.count(None)

    def marcos_usados(self) -> int:
        return self.total_marcos - self.marcos_libres()

    def mb_usados(self) -> int:
        return self.marcos_usados() * self.tamano_marco_mb

    def mb_totales(self) -> int:
        return self.total_marcos * self.tamano_marco_mb

    def fragmentacion_interna(self, pid: int) -> int:
        """MB desperdiciados dentro de la última página de un proceso."""
        if pid not in self._tamanos:
            return 0
        asignado = self.marcos_necesarios(self._tamanos[pid]) * self.tamano_marco_mb
        return asignado - self._tamanos[pid]

    def fragmentacion_interna_total(self) -> int:
        return sum(self.fragmentacion_interna(pid) for pid in self._tamanos)

    # --- Operaciones ---------------------------------------------------------
    def asignar(self, pid: int, tamano_mb: int) -> list[int]:
        """
        Reserva marcos para un proceso y devuelve su tabla de páginas
        (lista donde el índice es la página y el valor es el marco físico).
        Lanza MemoriaInsuficienteError si no hay espacio.
        """
        # Se valida ANTES de tocar la tabla de marcos: o el proceso entra
        # completo o no entra. Nunca queda con solo una parte de sus páginas.
        requeridos = self.marcos_necesarios(tamano_mb)
        libres = self.marcos_libres()
        if requeridos > libres:
            raise MemoriaInsuficienteError(tamano_mb, requeridos, libres,
                                           self.tamano_marco_mb)

        # Se toma cualquier marco libre recorriendo la RAM en orden. Como es
        # paginación, no importa que los marcos queden separados: la tabla de
        # páginas recuerda en qué marco quedó cada página del proceso.
        tabla_paginas = []
        for marco, dueno in enumerate(self.marcos):
            if dueno is None:
                self.marcos[marco] = pid
                tabla_paginas.append(marco)
                if len(tabla_paginas) == requeridos:
                    break
        self._tamanos[pid] = tamano_mb
        return tabla_paginas

    def liberar(self, pid: int) -> int:
        """Libera todos los marcos de un proceso y devuelve cuántos liberó."""
        # Basta con marcar como libres los marcos de este PID. No hace falta
        # compactar la memoria: con paginación no hay fragmentación externa.
        liberados = 0
        for marco, dueno in enumerate(self.marcos):
            if dueno == pid:
                self.marcos[marco] = None
                liberados += 1
        self._tamanos.pop(pid, None)
        return liberados
