"""Pruebas del semáforo binario y del interbloqueo."""

import unittest

from kernel.interbloqueo import ErrorRecurso
from kernel.nucleo import Kernel
from kernel.pcb import Estado
from kernel.sincronizacion import ErrorSemaforo


def kernel_con_procesos(cantidad):
    kernel = Kernel()
    for i in range(cantidad):
        kernel.crear_proceso(f"p{i + 1}", 4, 5)
    return kernel


class PruebasSemaforo(unittest.TestCase):
    def test_carrera_sin_semaforo_pierde_actualizaciones(self):
        kernel = kernel_con_procesos(3)
        kernel.concurrencia.simular_carrera([1, 2, 3], con_semaforo=False)
        self.assertEqual(kernel.concurrencia.variable_global, 10)   # esperado 30

    def test_semaforo_evita_la_carrera(self):
        kernel = kernel_con_procesos(3)
        pasos = kernel.concurrencia.simular_carrera([1, 2, 3], con_semaforo=True)
        self.assertEqual(kernel.concurrencia.variable_global, 30)
        self.assertIn("BLOQUEADO", " ".join(p.detalle for p in pasos))
        # Al final todos vuelven a LISTO y el semáforo queda libre.
        self.assertTrue(all(p.estado == Estado.LISTO for p in kernel.procesos.values()))
        self.assertEqual(kernel.concurrencia.semaforo.valor, 1)

    def test_wait_ocupado_bloquea_y_signal_despierta(self):
        kernel = kernel_con_procesos(2)
        concurrencia = kernel.concurrencia
        self.assertTrue(concurrencia.wait(1))
        self.assertFalse(concurrencia.wait(2))
        self.assertEqual(kernel.procesos[2].estado, Estado.BLOQUEADO)
        self.assertNotIn(2, kernel.planificador.cola_listos)
        self.assertEqual(concurrencia.escribir_y_salir(1), 2)
        self.assertEqual(kernel.procesos[2].estado, Estado.LISTO)
        self.assertEqual(concurrencia.semaforo.dueno, 2)

    def test_signal_de_quien_no_esta_dentro(self):
        kernel = kernel_con_procesos(2)
        kernel.concurrencia.wait(1)
        with self.assertRaises(ErrorSemaforo):
            kernel.concurrencia.signal(2)

    def test_terminar_al_dueno_libera_el_semaforo(self):
        kernel = kernel_con_procesos(2)
        kernel.concurrencia.wait(1)
        kernel.concurrencia.wait(2)
        resultado = kernel.terminar_proceso(1, "kill", abortado=True)
        self.assertEqual(resultado.despertado_semaforo, 2)
        self.assertEqual(kernel.concurrencia.semaforo.dueno, 2)


class PruebasDeadlock(unittest.TestCase):
    def test_forzar_y_detectar(self):
        kernel = Kernel()
        a, b = kernel.recursos.forzar_interbloqueo()
        self.assertEqual(sorted(kernel.recursos.detectar()), [a.pid, b.pid])
        self.assertEqual(a.estado, Estado.BLOQUEADO)
        self.assertEqual(b.estado, Estado.BLOQUEADO)
        self.assertFalse(kernel.planificador.hay_listos())

    def test_abortar_rompe_el_ciclo(self):
        kernel = Kernel()
        a, b = kernel.recursos.forzar_interbloqueo()
        resultado = kernel.terminar_proceso(a.pid, "romper deadlock", abortado=True)
        self.assertEqual(resultado.recursos, [("R1", b.pid)])
        self.assertEqual(kernel.recursos.detectar(), [])
        self.assertEqual(b.estado, Estado.LISTO)
        self.assertEqual(kernel.recursos.recursos_de(b.pid), ["R1", "R2"])

    def test_no_se_puede_forzar_dos_veces(self):
        kernel = Kernel()
        kernel.recursos.forzar_interbloqueo()
        with self.assertRaises(ErrorRecurso):
            kernel.recursos.forzar_interbloqueo()

    def test_sin_memoria_no_quedan_procesos_a_medias(self):
        kernel = Kernel()
        kernel.crear_proceso("relleno", 88, 5)    # quedan 12 MB: cabe A pero no B
        with self.assertRaises(Exception):
            kernel.recursos.forzar_interbloqueo()
        self.assertEqual(len(kernel.procesos_activos()), 1)
        self.assertEqual(kernel.memoria.marcos_libres(), 3)


if __name__ == "__main__":
    unittest.main()
