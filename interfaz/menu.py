"""
NAI-Core v22.11 - Interfaz de consola
=====================================
Menú interactivo construido con la librería `rich` (colores, tablas y paneles
dentro de la terminal). Esta capa solo muestra información y recoge datos:
toda la lógica vive en el paquete `kernel`.
"""

import random

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from config import (AUTOR, CARPETA_BITACORAS, ESTRES_MAX_PROCESOS, NOMBRE_SISTEMA,
                    QUANTUM, RAFAGA_MAX, RAFAGA_MIN, TAMANO_MARCO_MB, TAMANO_MAX_MB,
                    TAMANO_MIN_MB, VERSION)
from interfaz.validaciones import (ErrorValidacion, validar_entero, validar_nombre,
                                   validar_si_no)
from kernel.memoria import MemoriaInsuficienteError
from kernel.nucleo import Kernel
from kernel.pcb import Estado

consola = Console()

# Paleta de colores: cada PID tiene siempre el mismo color en tablas y mapas.
COLORES = ["cyan", "magenta", "green", "yellow", "blue", "bright_red",
           "bright_cyan", "bright_magenta", "bright_green", "orange3"]

COLOR_ESTADO = {
    Estado.NUEVO: "white",
    Estado.LISTO: "green",
    Estado.EJECUCION: "bold cyan",
    Estado.BLOQUEADO: "yellow",
    Estado.TERMINADO: "dim",
}

# Letras del logotipo en estilo "ANSI Shadow"; se unen fila por fila.
_LETRAS = {
    "N": ["███╗   ██╗", "████╗  ██║", "██╔██╗ ██║", "██║╚██╗██║", "██║ ╚████║", "╚═╝  ╚═══╝"],
    "A": [" █████╗ ", "██╔══██╗", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"],
    "I": ["██╗", "██║", "██║", "██║", "██║", "╚═╝"],
    "-": ["      ", "      ", "█████╗", "╚════╝", "      ", "      "],
    "C": [" ██████╗", "██╔════╝", "██║     ", "██║     ", "╚██████╗", " ╚═════╝"],
    "O": [" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "R": ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██║  ██║", "╚═╝  ╚═╝"],
    "E": ["███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "███████╗", "╚══════╝"],
}
LOGO = "\n".join(" ".join(_LETRAS[c][fila] for c in "NAI-CORE") for fila in range(6))

OPCIONES = [
    ("1", "Crear proceso"),
    ("2", "Tabla de procesos (PCB / TCB)"),
    ("3", "Mapa de memoria (paginación)"),
    ("4", "Planificador Round Robin"),
    ("5", "Concurrencia: semáforo binario"),
    ("6", "Interbloqueo (deadlock)"),
    ("7", "Prueba de estrés"),
    ("8", "Bitácora del kernel"),
    ("0", "Salir"),
]


def color_pid(pid: int) -> str:
    return COLORES[(pid - 1) % len(COLORES)]


# --- Utilidades de entrada ----------------------------------------------------
def pausa() -> None:
    consola.input("\n[dim]Presione Enter para volver al menú...[/]")


def titulo(texto: str) -> None:
    consola.clear()
    consola.print(Panel(Text(texto, style="bold white"), border_style="cyan",
                        title=f"{NOMBRE_SISTEMA} v{VERSION}", title_align="left"))


def pedir(etiqueta: str, validador):
    """
    Pide un dato hasta que sea válido. Si el usuario deja el campo vacío,
    devuelve None para cancelar la operación.
    """
    while True:
        texto = consola.input(f"  [cyan]›[/] {etiqueta}: ")
        if not texto.strip():
            return None
        try:
            return validador(texto)
        except ErrorValidacion as error:
            consola.print(f"    [bold red]✗[/] {error}")


# --- Componentes visuales -----------------------------------------------------
def barra_ram(kernel: Kernel, ancho: int = 25) -> Text:
    memoria = kernel.memoria
    usados = memoria.marcos_usados()
    llenos = round(usados / memoria.total_marcos * ancho)
    estilo = "red" if usados / memoria.total_marcos > 0.8 else "green"
    barra = Text("█" * llenos, style=estilo)
    barra.append("░" * (ancho - llenos), style="dim")
    barra.append(f"  {memoria.mb_usados()}/{memoria.mb_totales()} MB")
    return barra


def encabezado(kernel: Kernel) -> Panel:
    estado = Text()
    estado.append("RAM ", style="bold")
    estado.append_text(barra_ram(kernel))
    estado.append("    Procesos activos: ", style="bold")
    estado.append(str(len(kernel.procesos_activos())))
    estado.append("    Reloj: ", style="bold")
    estado.append(f"t = {kernel.reloj}")
    estado.append("    Quantum: ", style="bold")
    estado.append(str(QUANTUM))
    contenido = Group(
        Align.center(Text(LOGO, style="bold cyan")),
        Align.center(Text(f"Simulador de Funciones del Kernel · v{VERSION}", style="italic")),
        Text(""),
        Align.center(estado),
    )
    return Panel(contenido, border_style="cyan", padding=(1, 2))


def menu_principal() -> Table:
    tabla = Table.grid(padding=(0, 4))
    tabla.add_column()
    tabla.add_column()
    filas = [o for o in OPCIONES if o[0] != "0"]
    mitad = (len(filas) + 1) // 2
    for izq, der in zip(filas[:mitad], filas[mitad:] + [None]):
        celda_izq = f"[bold cyan][{izq[0]}][/] {izq[1]}"
        celda_der = f"[bold cyan][{der[0]}][/] {der[1]}" if der else ""
        tabla.add_row(celda_izq, celda_der)
    tabla.add_row("", "[bold red][0][/] Salir")
    return tabla


def tabla_procesos(kernel: Kernel) -> Table:
    tabla = Table(title="Tabla de procesos", header_style="bold cyan", expand=True)
    for columna in ("PID", "Nombre", "Estado", "Memoria", "Marcos",
                    "Ráfaga total", "Restante", "Llegada"):
        tabla.add_column(columna, justify="center")
    for p in kernel.procesos.values():
        tabla.add_row(
            f"[{color_pid(p.pid)}]{p.pid}[/]",
            p.nombre,
            f"[{COLOR_ESTADO[p.estado]}]{p.estado.value}[/]",
            f"{p.tamano_mb} MB",
            str(p.marcos_asignados),
            str(p.rafaga_total),
            str(p.rafaga_restante),
            f"t = {p.tiempo_llegada}",
        )
    return tabla


# --- Pantallas ----------------------------------------------------------------
def pantalla_crear_proceso(kernel: Kernel) -> None:
    titulo("Crear proceso")
    consola.print("[dim]  Deje un campo vacío y presione Enter para cancelar.[/]\n")
    nombre = pedir("Nombre del proceso", validar_nombre)
    if nombre is None:
        return
    tamano = pedir(f"Tamaño en memoria (MB, {TAMANO_MIN_MB}-{TAMANO_MAX_MB})",
                   lambda t: validar_entero(t, "El tamaño", TAMANO_MIN_MB, TAMANO_MAX_MB))
    if tamano is None:
        return
    rafaga = pedir(f"Ráfaga de CPU ({RAFAGA_MIN}-{RAFAGA_MAX})",
                   lambda t: validar_entero(t, "La ráfaga", RAFAGA_MIN, RAFAGA_MAX))
    if rafaga is None:
        return

    try:
        pcb = kernel.crear_proceso(nombre, tamano, rafaga)
    except MemoriaInsuficienteError as error:
        consola.print(Panel(
            f"[bold]{error}[/]\n\nEl proceso fue rechazado y no se creó su PCB.",
            title="[bold red]OUT OF MEMORY[/]", border_style="red"))
    else:
        paginas = ", ".join(f"P{i}→M{m}" for i, m in enumerate(pcb.tabla_paginas))
        consola.print(Panel(
            f"PID [bold]{pcb.pid}[/] · '{pcb.nombre}' · {pcb.tamano_mb} MB · "
            f"ráfaga {pcb.rafaga_total}\n"
            f"Estado: NUEVO → [green]LISTO[/]\n"
            f"Tabla de páginas: {paginas}",
            title="[bold green]Proceso creado[/]", border_style="green"))
    pausa()


def detalle_pcb(kernel: Kernel, pid: int) -> None:
    p = kernel.procesos[pid]
    pcb = Table.grid(padding=(0, 2))
    pcb.add_column(style="bold")
    pcb.add_column()
    pcb.add_row("PID", str(p.pid))
    pcb.add_row("Nombre", p.nombre)
    pcb.add_row("Estado actual", f"[{COLOR_ESTADO[p.estado]}]{p.estado.value}[/]")
    pcb.add_row("Tamaño en memoria", f"{p.tamano_mb} MB ({p.marcos_asignados} páginas)")
    pcb.add_row("Ráfaga de CPU total", str(p.rafaga_total))
    pcb.add_row("Ráfaga de CPU restante", str(p.rafaga_restante))
    pcb.add_row("Tiempo de llegada", f"t = {p.tiempo_llegada}")
    pcb.add_row("Cambios de contexto", str(p.cambios_contexto))
    pcb.add_row("Tabla de páginas",
                ", ".join(f"P{i}→M{m}" for i, m in enumerate(p.tabla_paginas)) or "—")

    tcb = Table.grid(padding=(0, 2))
    tcb.add_column(style="bold")
    tcb.add_column()
    tcb.add_row("TID", str(p.tcb.tid))
    tcb.add_row("Proceso dueño", f"PID {p.tcb.pid}")
    tcb.add_row("Contador de programa", str(p.tcb.contador_programa))
    for registro, valor in p.tcb.registros.items():
        tcb.add_row(f"Registro {registro}", f"{valor} (0x{valor:02X})")

    color = color_pid(p.pid)
    consola.print(Panel(pcb, title=f"[bold]PCB · PID {p.pid}[/]", border_style=color))
    consola.print(Panel(tcb, title=f"[bold]TCB · hilo principal[/]", border_style=color))


def pantalla_tabla_procesos(kernel: Kernel) -> None:
    titulo("Tabla de procesos (PCB / TCB)")
    if not kernel.procesos:
        consola.print("  [yellow]No hay procesos creados todavía.[/]")
        pausa()
        return
    consola.print(tabla_procesos(kernel))
    pid = pedir("PID para ver su PCB y TCB (Enter para volver)",
                lambda t: _validar_pid(kernel, t))
    if pid is not None:
        detalle_pcb(kernel, pid)
        pausa()


def _validar_pid(kernel: Kernel, texto: str) -> int:
    pid = validar_entero(texto, "El PID", 1, 9_999_999)
    if pid not in kernel.procesos:
        raise ErrorValidacion(f"No existe un proceso con PID {pid}.")
    return pid


def pantalla_memoria(kernel: Kernel) -> None:
    titulo("Mapa de memoria · paginación simple")
    memoria = kernel.memoria

    # Cuadrícula de 5 x 5 marcos
    mapa = Table.grid(padding=(0, 1))
    por_fila = 5
    for _ in range(por_fila):
        mapa.add_column()
    celdas = []
    for marco, pid in enumerate(memoria.marcos):
        if pid is None:
            celdas.append(Text(f" M{marco:02d} libre ", style="dim on grey15"))
        else:
            celdas.append(Text(f" M{marco:02d} PID{pid:<2}", style=f"bold black on {color_pid(pid)}"))
    for i in range(0, len(celdas), por_fila):
        mapa.add_row(*celdas[i:i + por_fila])

    resumen = Table.grid(padding=(0, 2))
    resumen.add_column(style="bold")
    resumen.add_column()
    resumen.add_row("Tamaño de marco", f"{TAMANO_MARCO_MB} MB")
    resumen.add_row("Marcos usados", f"{memoria.marcos_usados()} de {memoria.total_marcos}")
    resumen.add_row("Memoria usada", f"{memoria.mb_usados()} MB")
    resumen.add_row("Memoria libre", f"{memoria.mb_totales() - memoria.mb_usados()} MB")
    resumen.add_row("Fragmentación interna", f"{memoria.fragmentacion_interna_total()} MB")
    resumen.add_row("Fragmentación externa", "0 MB (la paginación la elimina)")

    consola.print(Panel(mapa, title="RAM física (100 MB)", border_style="cyan"))
    consola.print(Panel(resumen, title="Resumen", border_style="cyan"))

    activos = kernel.procesos_activos()
    if activos:
        tablas = Table(title="Tablas de páginas", header_style="bold cyan", expand=True)
        tablas.add_column("PID", justify="center")
        tablas.add_column("Nombre")
        tablas.add_column("Página → Marco")
        tablas.add_column("Frag. interna", justify="center")
        for p in activos:
            tablas.add_row(f"[{color_pid(p.pid)}]{p.pid}[/]", p.nombre,
                           ", ".join(f"P{i}→M{m}" for i, m in enumerate(p.tabla_paginas)),
                           f"{memoria.fragmentacion_interna(p.pid)} MB")
        consola.print(tablas)
    pausa()


def pantalla_estres(kernel: Kernel) -> None:
    titulo("Prueba de estrés")
    consola.print("[dim]  Genera procesos con tamaños y ráfagas aleatorias para "
                  "verificar las validaciones de memoria.[/]\n")
    cantidad = pedir(f"Cantidad de procesos (1-{ESTRES_MAX_PROCESOS})",
                     lambda t: validar_entero(t, "La cantidad", 1, ESTRES_MAX_PROCESOS))
    if cantidad is None:
        return
    nombres = ["chrome", "spotify", "vscode", "discord", "steam", "word",
               "excel", "zoom", "obs", "git", "python", "teams"]
    resultados = Table(header_style="bold cyan", expand=True)
    for columna in ("#", "Nombre", "Tamaño", "Ráfaga", "Resultado"):
        resultados.add_column(columna, justify="center")
    aceptados = 0
    for i in range(1, cantidad + 1):
        nombre = f"{random.choice(nombres)}{i}"
        tamano = random.randint(1, 40)
        rafaga = random.randint(1, 15)
        try:
            pcb = kernel.crear_proceso(nombre, tamano, rafaga)
            resultados.add_row(str(i), nombre, f"{tamano} MB", str(rafaga),
                               f"[green]Aceptado · PID {pcb.pid}[/]")
            aceptados += 1
        except MemoriaInsuficienteError:
            resultados.add_row(str(i), nombre, f"{tamano} MB", str(rafaga),
                               "[red]Out of Memory[/]")
    consola.print(resultados)
    consola.print(f"\n  [bold]Aceptados:[/] [green]{aceptados}[/]   "
                  f"[bold]Rechazados:[/] [red]{cantidad - aceptados}[/]")
    kernel.log("SISTEMA", f"Prueba de estrés: {cantidad} procesos, {aceptados} aceptados, "
                          f"{cantidad - aceptados} rechazados.")
    pausa()


def pantalla_bitacora(kernel: Kernel) -> None:
    titulo("Bitácora del kernel")
    estilos = {"ERROR": "bold red", "MEMORIA": "magenta", "PROCESO": "green",
               "SISTEMA": "cyan", "CPU": "blue"}
    tabla = Table(header_style="bold cyan", expand=True)
    tabla.add_column("Hora", justify="center")
    tabla.add_column("Reloj", justify="center")
    tabla.add_column("Tipo", justify="center")
    tabla.add_column("Evento")
    for e in kernel.bitacora.ultimos(30):
        estilo = estilos.get(e.tipo, "white")
        tabla.add_row(e.hora, f"t = {e.reloj}", f"[{estilo}]{e.tipo}[/]", e.mensaje)
    consola.print(tabla)
    consola.print(f"[dim]  Mostrando los últimos {min(30, len(kernel.bitacora.eventos))} "
                  f"de {len(kernel.bitacora.eventos)} eventos.[/]\n")
    if pedir("¿Exportar la bitácora completa a .txt? (s/n)", validar_si_no):
        ruta = kernel.bitacora.exportar(CARPETA_BITACORAS)
        consola.print(f"  [green]✓[/] Bitácora exportada en [bold]{ruta}[/]")
        pausa()


def pantalla_en_construccion(nombre: str) -> None:
    titulo(nombre)
    consola.print("  [yellow]Este módulo se implementará en la siguiente etapa.[/]")
    pausa()


# --- Bucle principal ----------------------------------------------------------
def ejecutar() -> None:
    kernel = Kernel()
    acciones = {
        "1": lambda: pantalla_crear_proceso(kernel),
        "2": lambda: pantalla_tabla_procesos(kernel),
        "3": lambda: pantalla_memoria(kernel),
        "4": lambda: pantalla_en_construccion("Planificador Round Robin"),
        "5": lambda: pantalla_en_construccion("Concurrencia: semáforo binario"),
        "6": lambda: pantalla_en_construccion("Interbloqueo (deadlock)"),
        "7": lambda: pantalla_estres(kernel),
        "8": lambda: pantalla_bitacora(kernel),
    }
    while True:
        consola.clear()
        consola.print(encabezado(kernel))
        consola.print(Panel(menu_principal(), title="Menú principal",
                            border_style="cyan", padding=(1, 4)))
        opcion = consola.input("[bold cyan]NAI-Core ›[/] Seleccione una opción: ").strip()
        if opcion == "0":
            consola.print(f"\n[cyan]Apagando {NOMBRE_SISTEMA}... ¡Hasta pronto![/]\n"
                          f"[dim]{AUTOR}[/]")
            break
        accion = acciones.get(opcion)
        if accion is None:
            consola.print(f"  [bold red]✗[/] '{opcion}' no es una opción válida. "
                          "Elija un número del 0 al 8.")
            pausa()
        else:
            accion()
