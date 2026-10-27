"""Pruebas de robustez de las entradas (preparación para la prueba de estrés)."""

import unittest

from interfaz.validaciones import (ErrorValidacion, validar_entero, validar_nombre,
                                   validar_si_no)


class PruebasValidaciones(unittest.TestCase):
    def test_enteros_validos(self):
        self.assertEqual(validar_entero("10", "X", 1, 100), 10)
        self.assertEqual(validar_entero("  7 ", "X", 1, 100), 7)
        self.assertEqual(validar_entero("+5", "X", 1, 100), 5)

    def test_enteros_invalidos(self):
        for entrada in ["", "   ", "abc", "3.5", "2,5", "-4", "0", "101",
                        "99999999999999", "1e3", "10MB", "@#!", "١٢"]:
            with self.subTest(entrada=entrada):
                with self.assertRaises(ErrorValidacion):
                    validar_entero(entrada, "X", 1, 100)

    def test_nombres(self):
        self.assertEqual(validar_nombre(" chrome "), "chrome")
        self.assertEqual(validar_nombre("Año_2023"), "Año_2023")
        for entrada in ["", "con espacio", "a" * 16, "drop;table", "<script>"]:
            with self.subTest(entrada=entrada):
                with self.assertRaises(ErrorValidacion):
                    validar_nombre(entrada)

    def test_si_no(self):
        self.assertTrue(validar_si_no("S"))
        self.assertFalse(validar_si_no("no"))
        with self.assertRaises(ErrorValidacion):
            validar_si_no("tal vez")


if __name__ == "__main__":
    unittest.main()
