"""
NAI-Core v22.11 - Interfaz de consola
=====================================
Menú interactivo construido con la librería `rich` (colores, tablas y paneles
dentro de la terminal). Esta capa solo muestra información y recoge datos:
toda la lógica vive en el paquete `kernel`.
"""

import random
import time

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from config import (ANIMACION_SEGUNDOS, AUTOR, CARPETA_BITACORAS, ESTRES_MAX_PROCESOS,
                    INCREMENTO_SECCION_CRITICA, NOMBRE_SISTEMA, PROCESOS_DEMO, QUANTUM,
                    RAFAGA_MAX, RAFAGA_MIN, TAMANO_MARCO_MB, TAMANO_MAX_MB, TAMANO_MIN_MB,
                    VARIABLE_GLOBAL_NOMBRE, VERSION)
from interfaz.validaciones import (ErrorValidacion, validar_entero, validar_nombre,
                                   validar_si_no)
from kernel.interbloqueo import ErrorRecurso
from kernel.memoria import MemoriaInsuficienteError
from kernel.nucleo import Kernel
from kernel.pcb import Estado
from kernel.sincronizacion import ErrorSemaforo

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
    ("2", "Terminar proceso (kill)"),
    ("3", "Tabla de procesos (PCB / TCB)"),
    ("4", "Mapa de memoria (paginación)"),
    ("5", "Planificador Round Robin"),
    ("6", "Concurrencia: semáforo binario"),
    ("7", "Interbloqueo (deadlock)"),
    ("8", "Prueba de estrés"),
    ("9", "Bitácora del kernel"),
    ("10", "Reiniciar sistema"),
]


def color_pid(pid: int) -> str:
    return COLORES[(pid - 1) % len(COLORES)]


def etiqueta_pid(pid: int) -> Text:
    return Text(f" P{pid} ", style=f"bold black on {color_pid(pid)}")


# --- Utilidades de entrada ----------------------------------------------------
def pausa() -> None:
    consola.input("\n[dim]Presione Enter para continuar...[/]")


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


def validador_pid(kernel: Kernel, permitidos: list[int]):
    """Crea un validador que solo acepta PIDs de la lista `permitidos`."""
    def validar(texto: str) -> int:
        pid = validar_entero(texto, "El PID", 1, 9_999_999)
        if pid not in kernel.procesos:
            raise ErrorValidacion(f"No existe un proceso con PID {pid}.")
        if pid not in permitidos:
            raise ErrorValidacion(f"El PID {pid} no es válido para esta operación "
                                  f"(estado: {kernel.procesos[pid].estado.value}).")
        return pid
    return validar


def submenu(opciones: list[tuple[str, str]]) -> str:
    tabla = Table.grid(padding=(0, 2))
    tabla.add_column()
    for clave, texto in opciones:
        estilo = "bold red" if clave == "0" else "bold cyan"
        tabla.add_row(f"[{estilo}][{clave}][/] {texto}")
    consola.print(Panel(tabla, border_style="cyan", padding=(0, 2)))
    return consola.input("[bold cyan]›[/] Opción: ").strip()


def opcion_invalida(opcion: str) -> None:
    consola.print(f"  [bold red]✗[/] '{opcion}' no es una opción válida.")
    pausa()


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
    estado.append("    Listos: ", style="bold")
    estado.append(str(len(kernel.procesos_listos())), style="green")
    estado.append("   Bloqueados: ", style="bold")
    estado.append(str(len(kernel.procesos_bloqueados())), style="yellow")
    estado.append("    Reloj: ", style="bold")
    estado.append(f"t = {kernel.reloj}")
    estado.append("    Quantum: ", style="bold")
    estado.append(str(QUANTUM))
    partes = [
        Align.center(Text(LOGO, style="bold cyan")),
        Align.center(Text(f"Simulador de Funciones del Kernel · v{VERSION}", style="italic")),
        Text(""),
        Align.center(estado),
    ]
    ciclo = kernel.recursos.detectar()
    if ciclo:
        partes.append(Align.center(Text(
            f"⚠ DEADLOCK ACTIVO entre PIDs {', '.join(map(str, ciclo))} · "
            f"resuélvalo en la opción 7", style="bold white on red")))
    return Panel(Group(*partes), border_style="red" if ciclo else "cyan", padding=(1, 2))


def menu_principal() -> Table:
    tabla = Table.grid(padding=(0, 4))
    tabla.add_column()
    tabla.add_column()
    mitad = (len(OPCIONES) + 1) // 2
    for izq, der in zip(OPCIONES[:mitad], OPCIONES[mitad:]):
        tabla.add_row(f"[bold cyan][{izq[0]}][/] {izq[1]}",
                      f"[bold cyan][{der[0]}][/] {der[1]}")
    tabla.add_row("", "[bold red][0][/] Salir")
    return tabla


def tabla_procesos(kernel: Kernel, solo_activos: bool = False) -> Table:
    tabla = Table(title="Tabla de procesos", header_style="bold cyan", expand=True)
    for columna in ("PID", "Nombre", "Estado", "Memoria", "Marcos",
                    "Ráfaga total", "Restante", "Llegada"):
        tabla.add_column(columna, justify="center")
    procesos = kernel.procesos_activos() if solo_activos else kernel.procesos.values()
    for p in procesos:
        estado = p.estado.value + (" (abortado)" if p.abortado else "")
        tabla.add_row(
            f"[{color_pid(p.pid)}]{p.pid}[/]",
            p.nombre,
            f"[{COLOR_ESTADO[p.estado]}]{estado}[/]",
            f"{p.tamano_mb} MB",
            str(p.marcos_asignados),
            str(p.rafaga_total),
            str(p.rafaga_restante),
            f"t = {p.tiempo_llegada}",
        )
    return tabla


def cola_listos(kernel: Kernel) -> Text:
    texto = Text("Cola de listos  ", style="bold")
    cola = kernel.planificador.cola_listos
    if not cola:
        texto.append("(vacía)", style="dim")
    for i, pid in enumerate(cola):
        if i:
            texto.append(" → ", style="dim")
        texto.append_text(etiqueta_pid(pid))
        texto.append(f" {kernel.procesos[pid].rafaga_restante}", style="dim")
    bloqueados = kernel.procesos_bloqueados()
    if bloqueados:
        texto.append("\nBloqueados      ", style="bold yellow")
        for i, p in enumerate(bloqueados):
            if i:
                texto.append("  ")
            texto.append_text(etiqueta_pid(p.pid))
    return texto


def describir_liberacion(resultado) -> list[str]:
    lineas = [f"Marcos de memoria liberados: {resultado.marcos_liberados} "
              f"({resultado.marcos_liberados * TAMANO_MARCO_MB} MB)"]
    for recurso, nuevo in resultado.recursos:
        destino = f"asignado a PID {nuevo}, que se desbloquea" if nuevo else "queda libre"
        lineas.append(f"{recurso} liberado → {destino}")
    if resultado.despertado_semaforo:
        lineas.append(f"Semáforo liberado → PID {resultado.despertado_semaforo} entra "
                      f"a la sección crítica")
    return lineas


# --- 1. Crear proceso ---------------------------------------------------------
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
            f"[bold]{error}[/]\n\nEl proceso fue rechazado y no se creó su PCB.\n"
            f"[dim]Puede liberar memoria con la opción 2 (kill).[/]",
            title="[bold red]OUT OF MEMORY[/]", border_style="red"))
    else:
        paginas = ", ".join(f"P{i}→M{m}" for i, m in enumerate(pcb.tabla_paginas))
        consola.print(Panel(
            f"PID [bold]{pcb.pid}[/] · '{pcb.nombre}' · {pcb.tamano_mb} MB · "
            f"ráfaga {pcb.rafaga_total}\n"
            f"Estado: NUEVO → [green]LISTO[/] (al final de la cola de listos)\n"
            f"Tabla de páginas: {paginas}",
            title="[bold green]Proceso creado[/]", border_style="green"))
    pausa()


# --- 2. Terminar proceso (kill) -------------------------------------------------
def pantalla_kill(kernel: Kernel) -> None:
    titulo("Terminar proceso (kill)")
    activos = kernel.procesos_activos()
    if not activos:
        consola.print("  [yellow]No hay procesos activos para terminar.[/]")
        pausa()
        return
    consola.print(tabla_procesos(kernel, solo_activos=True))
    consola.print("[dim]  Equivale a 'Finalizar tarea' en el Administrador de tareas: "
                  "el proceso muere a la fuerza y libera todo lo que tenía.[/]\n")
    pid = pedir("PID del proceso a terminar (Enter para cancelar)",
                validador_pid(kernel, [p.pid for p in activos]))
    if pid is None:
        return
    nombre = kernel.procesos[pid].nombre
    if not pedir(f"¿Confirma terminar PID {pid} '{nombre}'? (s/n)", validar_si_no):
        return
    resultado = kernel.terminar_proceso(pid, "terminado por el usuario (kill)", abortado=True)
    consola.print(Panel("\n".join(describir_liberacion(resultado)),
                        title=f"[bold green]PID {pid} '{nombre}' terminado[/]",
                        border_style="green"))
    pausa()


# --- 3. Tabla de procesos ---------------------------------------------------------
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
    recursos = kernel.recursos.recursos_de(pid)
    pcb.add_row("Recursos retenidos", ", ".join(recursos) or "—")

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
    consola.print(Panel(tcb, title="[bold]TCB · hilo principal[/]", border_style=color))


def pantalla_tabla_procesos(kernel: Kernel) -> None:
    titulo("Tabla de procesos (PCB / TCB)")
    if not kernel.procesos:
        consola.print("  [yellow]No hay procesos creados todavía.[/]")
        pausa()
        return
    consola.print(tabla_procesos(kernel))
    pid = pedir("PID para ver su PCB y TCB (Enter para volver)",
                validador_pid(kernel, list(kernel.procesos)))
    if pid is not None:
        detalle_pcb(kernel, pid)
        pausa()


# --- 4. Mapa de memoria -----------------------------------------------------------
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


# --- 5. Round Robin ---------------------------------------------------------------
def linea_segmento(segmento) -> Text:
    linea = Text(f"  t = {segmento.inicio:>3} → {segmento.fin:<3} ")
    linea.append_text(etiqueta_pid(segmento.pid))
    linea.append(f" {segmento.nombre} ejecutó {segmento.duracion} u.t.  ")
    if segmento.terminado:
        linea.append(f"✓ terminó (CT = {segmento.fin}) y liberó su memoria", style="green")
    else:
        linea.append(f"↺ cambio de contexto · restante {segmento.restante} · "
                     f"vuelve al final de la cola", style="yellow")
    return linea


def diagrama_gantt(segmentos, ancho_max: int) -> Group:
    """Dibuja el diagrama de Gantt en filas que caben en la pantalla."""
    filas = []
    actual = []
    ancho = 1
    for s in segmentos:
        w = max(5, s.duracion * 3)
        if actual and ancho + w + 1 > ancho_max:
            filas.append(actual)
            actual, ancho = [], 1
        actual.append((s, w))
        ancho += w + 1
    if actual:
        filas.append(actual)

    lineas = []
    for fila in filas:
        barra = Text("│")
        total = 1 + sum(w + 1 for _, w in fila)
        tiempos = [" "] * (total + 4)

        def escribir(pos, valor):
            for i, c in enumerate(str(valor)):
                tiempos[pos + i] = c

        pos = 0
        escribir(pos, fila[0][0].inicio)
        for s, w in fila:
            barra.append(f"P{s.pid}".center(w), style=f"bold black on {color_pid(s.pid)}")
            barra.append("│")
            pos += w + 1
            escribir(pos, s.fin)
        lineas += [barra, Text("".join(tiempos).rstrip(), style="dim"), Text("")]
    return Group(*lineas)


def mostrar_gantt_y_metricas(kernel: Kernel) -> None:
    planificador = kernel.planificador
    if not planificador.historial:
        consola.print("  [yellow]Todavía no se ha ejecutado ningún quantum.[/]")
        return
    consola.print(Panel(diagrama_gantt(planificador.historial, consola.width - 8),
                        title=f"Diagrama de Gantt · Round Robin (q = {QUANTUM})",
                        border_style="cyan"))
    m = planificador.metricas()
    if m.filas:
        tabla = Table(title="Métricas por proceso terminado", header_style="bold cyan",
                      expand=True)
        for columna in ("PID", "Nombre", "Llegada AT", "Ráfaga BT",
                        "Final CT", "Retorno TAT (CT−AT)", "Espera WT (TAT−BT)"):
            tabla.add_column(columna, justify="center")
        for f in m.filas:
            tabla.add_row(f"[{color_pid(f.pid)}]{f.pid}[/]", f.nombre, str(f.llegada),
                          str(f.rafaga), str(f.finalizacion), str(f.retorno), str(f.espera))
        tabla.add_row("", "[bold]Promedio[/]", "", "", "",
                      f"[bold]{m.promedio_retorno:.2f}[/]", f"[bold]{m.promedio_espera:.2f}[/]")
        consola.print(tabla)
    resumen = Table.grid(padding=(0, 2))
    resumen.add_column(style="bold")
    resumen.add_column()
    resumen.add_row("Utilización de CPU", f"{m.utilizacion_cpu:.1f} %")
    resumen.add_row("Productividad", f"{m.productividad:.3f} procesos por unidad de tiempo")
    resumen.add_row("Cambios de contexto", str(m.cambios_contexto))
    resumen.add_row("Procesos terminados", str(len(m.filas)))
    consola.print(Panel(resumen, title="Rendimiento", border_style="cyan"))


def pantalla_round_robin(kernel: Kernel) -> None:
    planificador = kernel.planificador
    while True:
        titulo(f"Planificador Round Robin · quantum q = {QUANTUM}")
        consola.print(Panel(cola_listos(kernel), border_style="cyan"))
        opcion = submenu([("1", "Ejecutar un quantum (paso a paso)"),
                          ("2", "Ejecutar hasta vaciar la cola de listos"),
                          ("3", "Ver diagrama de Gantt y métricas"),
                          ("0", "Volver")])
        if opcion in ("0", ""):
            return
        if opcion == "1":
            segmento = planificador.ejecutar_quantum()
            if segmento is None:
                consola.print("  [yellow]La cola de listos está vacía.[/]")
            else:
                consola.print(linea_segmento(segmento))
            pausa()
        elif opcion == "2":
            if not planificador.hay_listos():
                consola.print("  [yellow]La cola de listos está vacía.[/]")
            else:
                consola.print()
                while (segmento := planificador.ejecutar_quantum()) is not None:
                    consola.print(linea_segmento(segmento))
                    time.sleep(ANIMACION_SEGUNDOS)
                consola.print()
                mostrar_gantt_y_metricas(kernel)
            if kernel.procesos_bloqueados():
                consola.print("  [yellow]Hay procesos BLOQUEADOS: no pueden usar la CPU "
                              "hasta que se les libere lo que esperan.[/]")
            pausa()
        elif opcion == "3":
            mostrar_gantt_y_metricas(kernel)
            pausa()
        else:
            opcion_invalida(opcion)


# --- 6. Semáforo binario ----------------------------------------------------------
def estado_semaforo(kernel: Kernel) -> Table:
    concurrencia = kernel.concurrencia
    semaforo = concurrencia.semaforo
    tabla = Table.grid(padding=(0, 2))
    tabla.add_column(style="bold")
    tabla.add_column()
    tabla.add_row(VARIABLE_GLOBAL_NOMBRE, f"[bold]{concurrencia.variable_global}[/] XP")
    if semaforo.dueno is None:
        tabla.add_row("Semáforo", "[green]S = 1 · sección crítica libre[/]")
    else:
        tabla.add_row("Semáforo", f"[red]S = 0 · ocupada por PID {semaforo.dueno}[/]")
    cola = " → ".join(f"P{pid}" for pid in semaforo.cola_espera) or "(vacía)"
    tabla.add_row("Cola de espera", cola)
    return tabla


def procesos_para_demo(kernel: Kernel) -> list[int] | None:
    """Toma hasta PROCESOS_DEMO procesos LISTOS; si faltan, ofrece crearlos."""
    listos = [p.pid for p in kernel.procesos_listos()][:PROCESOS_DEMO]
    if len(listos) >= 2:
        return listos
    consola.print(f"  [yellow]Se necesitan al menos 2 procesos LISTOS para la demostración.[/]")
    if not pedir(f"¿Crear {PROCESOS_DEMO} procesos 'jugador' de 4 MB? (s/n)", validar_si_no):
        return None
    try:
        for i in range(1, PROCESOS_DEMO + 1):
            kernel.crear_proceso(f"jugador{i}", 4, 5)
    except MemoriaInsuficienteError as error:
        consola.print(f"  [bold red]✗[/] {error}")
    listos = [p.pid for p in kernel.procesos_listos()][:PROCESOS_DEMO]
    return listos if len(listos) >= 2 else None


def demo_carrera(kernel: Kernel, con_semaforo: bool) -> None:
    pids = procesos_para_demo(kernel)
    if pids is None:
        pausa()
        return
    try:
        pasos = kernel.concurrencia.simular_carrera(pids, con_semaforo)
    except ErrorSemaforo as error:
        consola.print(f"  [bold red]✗[/] {error}")
        pausa()
        return

    modo = "CON semáforo binario" if con_semaforo else "SIN semáforo"
    consola.print(f"\n  Sección crítica: [bold]{VARIABLE_GLOBAL_NOMBRE}[/] · cada proceso quiere "
                  f"sumar [bold]{INCREMENTO_SECCION_CRITICA} XP[/] · {modo}\n")
    tabla = Table(header_style="bold cyan", expand=True)
    for columna in ("#", "Proceso", "Instrucción", "Registro local", "Marcador global", "Qué pasa"):
        tabla.add_column(columna, justify="center" if columna != "Qué pasa" else "left")
    for paso in pasos:
        estilo = "yellow" if "BLOQUEADO" in paso.detalle else \
                 "cyan" if paso.instruccion in ("wait()", "signal()") else ""
        tabla.add_row(str(paso.paso), etiqueta_pid(paso.pid), paso.instruccion,
                      "—" if paso.local is None else str(paso.local),
                      str(paso.global_), paso.detalle, style=estilo)
    consola.print(tabla)

    esperado = INCREMENTO_SECCION_CRITICA * len(pids)
    obtenido = kernel.concurrencia.variable_global
    if obtenido == esperado:
        consola.print(Panel(
            f"Resultado esperado: {esperado} XP · Resultado obtenido: [bold]{obtenido} XP[/]\n"
            f"El semáforo binario garantizó la exclusión mutua: solo un proceso a la vez "
            f"entró a la sección crítica y ninguna suma se perdió.",
            title="[bold green]DATOS CONSISTENTES[/]", border_style="green"))
    else:
        consola.print(Panel(
            f"Resultado esperado: {esperado} XP · Resultado obtenido: [bold]{obtenido} XP[/]\n"
            f"Se perdieron {esperado - obtenido} XP: varios procesos leyeron el mismo valor "
            f"antes de que otro lo actualizara y se sobrescribieron entre sí.",
            title="[bold red]CONDICIÓN DE CARRERA[/]", border_style="red"))
    pausa()


def pantalla_semaforo(kernel: Kernel) -> None:
    concurrencia = kernel.concurrencia
    while True:
        titulo("Concurrencia · semáforo binario")
        consola.print(Panel(estado_semaforo(kernel), title="Sección crítica",
                            border_style="cyan"))
        opcion = submenu([("1", "Demostración: condición de carrera SIN semáforo"),
                          ("2", "Demostración: la misma operación CON semáforo"),
                          ("3", "Manual: wait(PID) · pedir entrar"),
                          ("4", f"Manual: sumar {INCREMENTO_SECCION_CRITICA} XP y signal(PID)"),
                          ("0", "Volver")])
        if opcion in ("0", ""):
            return
        if opcion == "1":
            demo_carrera(kernel, con_semaforo=False)
        elif opcion == "2":
            demo_carrera(kernel, con_semaforo=True)
        elif opcion == "3":
            listos = [p.pid for p in kernel.procesos_listos()]
            if not listos:
                consola.print("  [yellow]No hay procesos LISTOS.[/]")
            else:
                pid = pedir("PID que ejecuta wait()", validador_pid(kernel, listos))
                if pid is not None:
                    try:
                        if concurrencia.wait(pid):
                            consola.print(f"  [green]✓ PID {pid} entró a la sección crítica.[/]")
                        else:
                            consola.print(f"  [yellow]⏳ Ocupada: PID {pid} queda BLOQUEADO "
                                          f"en la cola de espera.[/]")
                    except ErrorSemaforo as error:
                        consola.print(f"  [bold red]✗[/] {error}")
            pausa()
        elif opcion == "4":
            dueno = concurrencia.semaforo.dueno
            if dueno is None:
                consola.print("  [yellow]Nadie está dentro de la sección crítica.[/]")
            else:
                pid = pedir("PID que ejecuta signal()", validador_pid(kernel, [dueno]))
                if pid is not None:
                    despertado = concurrencia.escribir_y_salir(pid)
                    consola.print(f"  [green]✓ PID {pid} sumó {INCREMENTO_SECCION_CRITICA} XP "
                                  f"y salió.[/]")
                    if despertado:
                        consola.print(f"  [cyan]→ PID {despertado} se desbloquea y entra.[/]")
            pausa()
        else:
            opcion_invalida(opcion)


# --- 7. Interbloqueo ----------------------------------------------------------------
def estado_recursos(kernel: Kernel) -> Table:
    administrador = kernel.recursos
    tabla = Table(header_style="bold cyan", expand=True)
    for columna in ("Recurso", "Retenido por", "Procesos esperando"):
        tabla.add_column(columna, justify="center")
    for recurso in administrador.recursos.values():
        dueno = f"PID {recurso.dueno}" if recurso.dueno else "[green]libre[/]"
        espera = ", ".join(f"PID {p}" for p in administrador.esperando_por(recurso.nombre))
        tabla.add_row(f"{recurso.nombre} ({recurso.descripcion})", dueno, espera or "—")
    return tabla


def alerta_deadlock(kernel: Kernel, ciclo: list[int]) -> Panel:
    administrador = kernel.recursos
    lineas = Text()
    for pid in ciclo:
        rid = administrador.esperando[pid]
        dueno = administrador.recursos[rid].dueno
        retiene = ", ".join(administrador.recursos_de(pid)) or "nada"
        lineas.append_text(etiqueta_pid(pid))
        lineas.append(f" {kernel.procesos[pid].nombre} retiene {retiene} y espera {rid} ──► ")
        lineas.append_text(etiqueta_pid(dueno))
        lineas.append("\n")
    lineas.append("\nNinguno puede avanzar: cada uno espera un recurso que el otro nunca "
                  "soltará (espera circular).\n", style="bold")
    lineas.append("En un SO real habría que abrir el Administrador de tareas y usar "
                  "'Finalizar tarea' (o el basurero de la terminal). En NAI-Core el kernel "
                  "lo detecta y permite abortar solo uno de los procesos (opción 2).",
                  style="dim")
    return Panel(lineas, title="[bold red]⚠ DEADLOCK DETECTADO[/]", border_style="red")


def pantalla_deadlock(kernel: Kernel) -> None:
    administrador = kernel.recursos
    while True:
        titulo("Interbloqueo (deadlock)")
        consola.print(estado_recursos(kernel))
        ciclo = administrador.detectar()
        if ciclo:
            consola.print(alerta_deadlock(kernel, ciclo))
        else:
            consola.print("  [green]✓ Sin interbloqueo: no hay ciclos en el grafo de espera.[/]")
        opcion = submenu([("1", "Forzar interbloqueo (Proceso A ↔ Proceso B)"),
                          ("2", "Abortar un proceso del ciclo (resolver)"),
                          ("0", "Volver")])
        if opcion in ("0", ""):
            return
        if opcion == "1":
            try:
                a, b = administrador.forzar_interbloqueo()
            except (ErrorRecurso, MemoriaInsuficienteError) as error:
                consola.print(f"  [bold red]✗[/] {error}")
            else:
                pasos = [f"PID {a.pid} (Proceso_A) solicita R1 → asignado",
                         f"PID {b.pid} (Proceso_B) solicita R2 → asignado",
                         f"PID {a.pid} (Proceso_A) solicita R2 → ocupado por PID {b.pid}: BLOQUEADO",
                         f"PID {b.pid} (Proceso_B) solicita R1 → ocupado por PID {a.pid}: BLOQUEADO"]
                consola.print()
                for paso in pasos:
                    consola.print(f"  • {paso}")
                    time.sleep(ANIMACION_SEGUNDOS)
            pausa()
        elif opcion == "2":
            if not ciclo:
                consola.print("  [yellow]No hay un interbloqueo que resolver.[/]")
                pausa()
                continue
            pid = pedir(f"PID a abortar ({' o '.join(map(str, ciclo))})",
                        validador_pid(kernel, ciclo))
            if pid is None:
                continue
            nombre = kernel.procesos[pid].nombre
            resultado = kernel.terminar_proceso(pid, "abortado para romper el deadlock",
                                                abortado=True)
            lineas = describir_liberacion(resultado)
            if not administrador.detectar():
                lineas.append("[bold]Ciclo roto: el sistema vuelve a avanzar.[/]")
            consola.print(Panel("\n".join(lineas),
                                title=f"[bold green]PID {pid} '{nombre}' abortado[/]",
                                border_style="green"))
            pausa()
        else:
            opcion_invalida(opcion)


# --- 8. Prueba de estrés ------------------------------------------------------------
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


# --- 9. Bitácora --------------------------------------------------------------------
def pantalla_bitacora(kernel: Kernel) -> None:
    titulo("Bitácora del kernel")
    estilos = {"ERROR": "bold red", "MEMORIA": "magenta", "PROCESO": "green",
               "SISTEMA": "cyan", "CPU": "blue", "SYNC": "yellow", "DEADLOCK": "red"}
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


# --- 10. Reiniciar ------------------------------------------------------------------
def pantalla_reiniciar(kernel: Kernel) -> None:
    titulo("Reiniciar sistema")
    consola.print("  Se eliminarán todos los procesos, la memoria quedará vacía y el reloj "
                  "volverá a t = 0. La bitácora se conserva.\n")
    if pedir("¿Confirma reiniciar NAI-Core? (s/n)", validar_si_no):
        kernel.reiniciar()
        consola.print("  [green]✓ Sistema reiniciado.[/]")
        pausa()


# --- Bucle principal ----------------------------------------------------------------
def ejecutar() -> None:
    kernel = Kernel()
    acciones = {
        "1": pantalla_crear_proceso,
        "2": pantalla_kill,
        "3": pantalla_tabla_procesos,
        "4": pantalla_memoria,
        "5": pantalla_round_robin,
        "6": pantalla_semaforo,
        "7": pantalla_deadlock,
        "8": pantalla_estres,
        "9": pantalla_bitacora,
        "10": pantalla_reiniciar,
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
                          "Elija un número del 0 al 10.")
            pausa()
        else:
            accion(kernel)
