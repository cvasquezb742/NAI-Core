"""Pruebas del planificador Round Robin y de la terminación de procesos (kill)."""

import unittest

from kernel.nucleo import Kernel
from kernel.pcb import Estado


def ejecutar_todo(kernel):
    while kernel.planificador.ejecutar_quantum():
        pass


class PruebasRoundRobin(unittest.TestCase):
    def test_coincide_con_calculo_manual_tarea_12(self):
        # Ejercicio 1 de la Tarea 12: q = 3, P1 = 8, P2 = 4, P3 = 2, llegada en 0.
        # Resultado a mano: CT = 14, 12, 8 y WT = 6, 8, 6.
        kernel = Kernel()
        for nombre, rafaga in [("P1", 8), ("P2", 4), ("P3", 2)]:
            kernel.crear_proceso(nombre, 4, rafaga)
        ejecutar_todo(kernel)

        gantt = [(s.pid, s.inicio, s.fin) for s in kernel.planificador.historial]
        self.assertEqual(gantt, [(1, 0, 3), (2, 3, 6), (3, 6, 8),
                                 (1, 8, 11), (2, 11, 12), (1, 12, 14)])
        metricas = kernel.planificador.metricas()
        self.assertEqual([f.finalizacion for f in metricas.filas], [14, 12, 8])
        self.assertEqual([f.espera for f in metricas.filas], [6, 8, 6])
        self.assertAlmostEqual(metricas.promedio_retorno, 34 / 3)
        self.assertAlmostEqual(metricas.promedio_espera, 20 / 3)
        self.assertEqual(metricas.utilizacion_cpu, 100.0)

    def test_cambio_de_contexto_guarda_el_tcb(self):
        kernel = Kernel()
        pcb = kernel.crear_proceso("largo", 4, 7)
        segmento = kernel.planificador.ejecutar_quantum()
        self.assertFalse(segmento.terminado)
        self.assertEqual(pcb.rafaga_restante, 4)
        self.assertEqual(pcb.tcb.contador_programa, 3)
        self.assertEqual(pcb.cambios_contexto, 1)
        self.assertEqual(list(kernel.planificador.cola_listos), [1])

    def test_proceso_que_llega_despues(self):
        kernel = Kernel()
        kernel.crear_proceso("a", 4, 5)
        kernel.planificador.ejecutar_quantum()          # t = 0 -> 3
        tardio = kernel.crear_proceso("b", 4, 2)        # llega en t = 3
        self.assertEqual(tardio.tiempo_llegada, 3)
        ejecutar_todo(kernel)
        fila_b = [f for f in kernel.planificador.metricas().filas if f.pid == 2][0]
        self.assertEqual((fila_b.finalizacion, fila_b.retorno, fila_b.espera), (7, 4, 2))

    def test_al_terminar_se_libera_la_memoria(self):
        kernel = Kernel()
        kernel.crear_proceso("a", 40, 2)
        ejecutar_todo(kernel)
        self.assertEqual(kernel.memoria.marcos_libres(), 25)
        self.assertEqual(kernel.procesos[1].estado, Estado.TERMINADO)


class PruebasKill(unittest.TestCase):
    def test_kill_libera_memoria_y_sale_de_la_cola(self):
        kernel = Kernel()
        kernel.crear_proceso("a", 40, 5)
        kernel.crear_proceso("b", 8, 5)
        resultado = kernel.terminar_proceso(1, "kill", abortado=True)
        self.assertEqual(resultado.marcos_liberados, 10)
        self.assertEqual(list(kernel.planificador.cola_listos), [2])
        self.assertTrue(kernel.procesos[1].abortado)

    def test_kill_permite_crear_un_proceso_antes_rechazado(self):
        kernel = Kernel()
        kernel.crear_proceso("lleno", 100, 5)
        with self.assertRaises(Exception):
            kernel.crear_proceso("nuevo", 20, 3)
        kernel.terminar_proceso(1, "kill", abortado=True)
        self.assertEqual(kernel.crear_proceso("nuevo", 20, 3).estado, Estado.LISTO)

    def test_abortados_no_cuentan_en_metricas(self):
        kernel = Kernel()
        kernel.crear_proceso("a", 4, 5)
        kernel.terminar_proceso(1, "kill", abortado=True)
        self.assertEqual(kernel.planificador.metricas().filas, [])

    def test_reiniciar_conserva_la_bitacora(self):
        kernel = Kernel()
        kernel.crear_proceso("a", 4, 5)
        eventos = len(kernel.bitacora.eventos)
        kernel.reiniciar()
        self.assertEqual(kernel.procesos, {})
        self.assertEqual(kernel.memoria.marcos_libres(), 25)
        self.assertGreater(len(kernel.bitacora.eventos), eventos)


if __name__ == "__main__":
    unittest.main()
