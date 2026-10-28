# NAI-Core v22.11

**Simulador de Funciones del Kernel de un Sistema Operativo**, desarrollado en Python con una interfaz de línea de comandos (CLI).

Proyecto final del curso **Sistemas Operativos I**, Universidad Mariano Gálvez de Guatemala.

- **Autor:** Christofer Josue Vasquez Baltazar
- **Video demostrativo:** _(enlace de YouTube pendiente)_

---

## Descripción

NAI-Core modela el comportamiento lógico de un núcleo de sistema operativo sin interactuar con el hardware real. Cada componente se representa con estructuras de datos que imitan las de un kernel:

| Módulo | Qué simula | Archivo |
|---|---|---|
| Gestión de procesos | PCB (PID, estado, tamaño, ráfaga total y restante) y TCB (contador de programa y registros) | `kernel/pcb.py` |
| Gestión de memoria | RAM de 100 MB con **paginación simple** (25 marcos de 4 MB) y rechazo por *Out of Memory* | `kernel/memoria.py` |
| Planificación | Round Robin con quantum fijo **q = 3**, cambio de contexto simulado, diagrama de Gantt y métricas (CT, TAT, WT, % CPU) | `kernel/planificador.py` |
| Concurrencia | Semáforo binario con `wait()` / `signal()` y cola de espera sobre un marcador global de XP compartido; demostración de condición de carrera sin y con semáforo | `kernel/sincronizacion.py` |
| Interbloqueo | Recursos R1 y R2, espera circular forzada, detección del ciclo en el grafo de espera y aborto de un proceso | `kernel/interbloqueo.py` |
| Terminación | Kill de cualquier proceso: libera memoria, semáforo y recursos, y despierta a quien los esperaba | `kernel/nucleo.py` |
| Bitácora | Registro de eventos del kernel exportable a `.txt` | `kernel/bitacora.py` |

## Requisitos

- Python 3.10 o superior
- Librería [`rich`](https://github.com/Textualize/rich) (colores y tablas en la terminal)
- Terminal con soporte Unicode (Windows Terminal, terminal de VS Code, PowerShell 7, etc.)

## Instalación

```bash
git clone https://github.com/cvasquezb742/NAI-Core.git
cd NAI-Core
python -m venv .venv
```

Activar el entorno virtual:

```bash
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Uso

```bash
python main.py
```

Menú principal:

```
[1] Crear proceso                    [6] Concurrencia: semáforo binario
[2] Terminar proceso (kill)          [7] Interbloqueo (deadlock)
[3] Tabla de procesos (PCB / TCB)    [8] Prueba de estrés
[4] Mapa de memoria (paginación)     [9] Bitácora del kernel
[5] Planificador Round Robin         [10] Reiniciar sistema
                                     [0] Salir
```

## Configuración

Todos los parámetros del sistema están en `config.py`. El simulador se ejecuta de forma local y **no utiliza conexiones de red, puertos ni claves de API**.

| Parámetro | Valor | Descripción |
|---|---|---|
| `RAM_TOTAL_MB` | 100 | Memoria física simulada |
| `TAMANO_MARCO_MB` | 4 | Tamaño de marco / página |
| `TOTAL_MARCOS` | 25 | Marcos disponibles |
| `QUANTUM` | 3 | Unidades de tiempo por turno (Round Robin) |
| `INCREMENTO_SECCION_CRITICA` | 10 | XP que suma cada proceso al marcador compartido |

## Estructura del proyecto

```
NAI-Core/
├── main.py                 Punto de entrada
├── config.py               Parámetros del sistema
├── kernel/                 Núcleo simulado
│   ├── nucleo.py           Kernel: tabla de procesos, reloj y llamadas al sistema
│   ├── pcb.py              PCB, TCB y estados del proceso
│   ├── memoria.py          Paginación simple y Out of Memory
│   ├── planificador.py     Round Robin, Gantt y métricas
│   ├── sincronizacion.py   Semáforo binario y demo de condición de carrera
│   ├── interbloqueo.py     Recursos R1/R2, detección y resolución de deadlock
│   └── bitacora.py         Registro de eventos
├── interfaz/               Capa de presentación
│   ├── menu.py             Menú interactivo
│   └── validaciones.py     Validación de entradas
└── tests/                  Pruebas automáticas
```

## Pruebas

```bash
python -m unittest discover -s tests -t .
```

Las 30 pruebas cubren memoria, validaciones, Round Robin, kill, semáforo y deadlock. La prueba `test_coincide_con_calculo_manual_tarea_12` verifica que el planificador reproduce el cálculo manual de Round Robin (q = 3; ráfagas 8, 4 y 2 → CT = 14, 12, 8 y WT = 6, 8, 6).

## Declaración de autoría

Este proyecto fue desarrollado por Christofer Josue Vasquez Baltazar como trabajo final del curso Sistemas Operativos I.
