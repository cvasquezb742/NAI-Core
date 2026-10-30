"""
NAI-Core v22.11 - Validación de entradas
========================================
Toda entrada del usuario pasa por aquí antes de llegar al kernel. El objetivo
es que ningún dato (letras, decimales, negativos, vacío, números gigantes,
símbolos) provoque un fallo del programa durante la prueba de estrés en vivo.
Cada función devuelve el valor ya convertido o lanza ErrorValidacion con un
mensaje claro para el usuario.
"""

import re

from config import NOMBRE_MAX_CARACTERES


class ErrorValidacion(Exception):
    """Entrada inválida; el mensaje se muestra tal cual al usuario."""


# Se usa [0-9] y no \d porque \d también acepta dígitos de otros alfabetos.
_PATRON_ENTERO = re.compile(r"[+-]?[0-9]+")
_PATRON_DECIMAL = re.compile(r"[+-]?[0-9]*[.,][0-9]+")
_PATRON_NOMBRE = re.compile(r"[A-Za-z0-9_\-áéíóúÁÉÍÓÚñÑ]+")


def validar_entero(texto: str, campo: str, minimo: int, maximo: int) -> int:
    """Convierte `texto` a entero dentro de [minimo, maximo]."""
    valor = texto.strip()
    if not valor:
        raise ErrorValidacion(f"{campo} no puede estar vacío.")
    # Se revisa el texto con un patrón ANTES de convertirlo con int(). Así
    # se puede decir exactamente qué estuvo mal (decimales, letras...) en vez
    # de dejar que el programa se caiga con un error de Python.
    if not _PATRON_ENTERO.fullmatch(valor):
        if _PATRON_DECIMAL.fullmatch(valor):
            raise ErrorValidacion(f"{campo} debe ser un número entero, sin decimales.")
        raise ErrorValidacion(f"'{valor}' no es un número válido para {campo}.")
    # Se descartan números absurdamente largos antes de convertirlos.
    if len(valor.lstrip("+-")) > 7:
        raise ErrorValidacion(f"{campo} debe estar entre {minimo} y {maximo}.")
    numero = int(valor)
    if not minimo <= numero <= maximo:
        raise ErrorValidacion(
            f"{campo} debe estar entre {minimo} y {maximo} (ingresó {numero}).")
    return numero


def validar_nombre(texto: str) -> str:
    """Nombre de proceso: 1 a 15 caracteres, letras, números, '_' o '-'."""
    nombre = texto.strip()
    if not nombre:
        raise ErrorValidacion("El nombre no puede estar vacío.")
    if len(nombre) > NOMBRE_MAX_CARACTERES:
        raise ErrorValidacion(
            f"El nombre admite máximo {NOMBRE_MAX_CARACTERES} caracteres.")
    if not _PATRON_NOMBRE.fullmatch(nombre):
        raise ErrorValidacion(
            "El nombre solo puede contener letras, números, '_' o '-' (sin espacios).")
    return nombre


def validar_si_no(texto: str) -> bool:
    respuesta = texto.strip().lower()
    if respuesta in ("s", "si", "sí"):
        return True
    if respuesta in ("n", "no"):
        return False
    raise ErrorValidacion("Responda 's' (sí) o 'n' (no).")
