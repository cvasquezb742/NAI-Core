"""
NAI-Core v22.11 - Configuración del sistema
============================================
Constantes globales del simulador. Funcionan como las "variables de entorno"
del kernel: cualquier módulo que necesite conocer el tamaño de la RAM o el
quantum las importa desde aquí, de modo que cambiar un valor en este archivo
cambia el comportamiento de todo el sistema.

El simulador no usa conexiones de red, puertos ni claves de API: todo se
ejecuta localmente sobre estructuras de datos en memoria.
"""

# --- Identidad del sistema ---------------------------------------------------
NOMBRE_SISTEMA = "NAI-Core"
VERSION = "22.11"
AUTOR = "Christofer Josue Vasquez Baltazar"

# --- Gestión de memoria (paginación simple) ----------------------------------
RAM_TOTAL_MB = 100          # Memoria física simulada (requisito del enunciado)
TAMANO_MARCO_MB = 4         # Tamaño de cada marco de página / página lógica
TOTAL_MARCOS = RAM_TOTAL_MB // TAMANO_MARCO_MB   # 100 / 4 = 25 marcos

# --- Planificación de procesos -----------------------------------------------
QUANTUM = 3                 # Unidades de tiempo por turno en Round Robin (q = 3)

# --- Límites de validación de entradas ---------------------------------------
# El tamaño máximo aceptado como "número válido" es mayor que la RAM a propósito:
# así un proceso de, por ejemplo, 150 MB llega al administrador de memoria y es
# rechazado con el error Out of Memory, tal como pide el enunciado.
TAMANO_MIN_MB = 1
TAMANO_MAX_MB = 10_000
RAFAGA_MIN = 1
RAFAGA_MAX = 100
NOMBRE_MAX_CARACTERES = 15
ESTRES_MAX_PROCESOS = 50

# --- Archivos ----------------------------------------------------------------
CARPETA_BITACORAS = "bitacoras"   # Donde se exportan los registros del kernel
