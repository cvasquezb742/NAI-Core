"""Pruebas del administrador de memoria y de la creación de procesos."""

import unittest

from kernel.memoria import AdministradorMemoria, MemoriaInsuficienteError
from kernel.nucleo import Kernel
from kernel.pcb import Estado


class PruebasMemoria(unittest.TestCase):
    def setUp(self):
        self.memoria = AdministradorMemoria(total_marcos=25, tamano_marco_mb=4)

    def test_paginas_se_redondean_hacia_arriba(self):
        self.assertEqual(self.memoria.marcos_necesarios(1), 1)
        self.assertEqual(self.memoria.marcos_necesarios(4), 1)
        self.assertEqual(self.memoria.marcos_necesarios(15), 4)

    def test_asignacion_devuelve_tabla_de_paginas(self):
        tabla = self.memoria.asignar(pid=1, tamano_mb=10)
        self.assertEqual(tabla, [0, 1, 2])
        self.assertEqual(self.memoria.marcos_libres(), 22)
        self.assertEqual(self.memoria.fragmentacion_interna(1), 2)

    def test_marcos_no_contiguos_se_reutilizan(self):
        self.memoria.asignar(1, 8)    # marcos 0-1
        self.memoria.asignar(2, 8)    # marcos 2-3
        self.memoria.asignar(3, 8)    # marcos 4-5
        self.memoria.liberar(2)       # deja un hueco en 2-3
        tabla = self.memoria.asignar(4, 16)
        self.assertEqual(tabla, [2, 3, 6, 7])

    def test_out_of_memory(self):
        self.memoria.asignar(1, 90)   # 23 marcos
        with self.assertRaises(MemoriaInsuficienteError):
            self.memoria.asignar(2, 12)  # necesita 3, quedan 2
        self.assertEqual(self.memoria.marcos_libres(), 2)

    def test_proceso_mayor_que_la_ram(self):
        with self.assertRaises(MemoriaInsuficienteError):
            self.memoria.asignar(1, 150)

    def test_liberar_devuelve_todos_los_marcos(self):
        self.memoria.asignar(1, 20)
        self.assertEqual(self.memoria.liberar(1), 5)
        self.assertEqual(self.memoria.marcos_libres(), 25)


class PruebasKernel(unittest.TestCase):
    def test_crear_proceso_queda_listo(self):
        kernel = Kernel()
        pcb = kernel.crear_proceso("chrome", 20, 7)
        self.assertEqual(pcb.pid, 1)
        self.assertEqual(pcb.estado, Estado.LISTO)
        self.assertEqual(pcb.rafaga_restante, 7)
        self.assertEqual(pcb.tcb.pid, 1)

    def test_rechazo_no_consume_pid(self):
        kernel = Kernel()
        with self.assertRaises(MemoriaInsuficienteError):
            kernel.crear_proceso("gigante", 500, 5)
        self.assertEqual(kernel.crear_proceso("normal", 4, 2).pid, 1)
        self.assertEqual(len(kernel.procesos), 1)

    def test_terminar_libera_memoria(self):
        kernel = Kernel()
        kernel.crear_proceso("a", 40, 3)
        kernel.terminar_proceso(1)
        self.assertEqual(kernel.procesos[1].estado, Estado.TERMINADO)
        self.assertEqual(kernel.memoria.marcos_libres(), 25)


if __name__ == "__main__":
    unittest.main()
