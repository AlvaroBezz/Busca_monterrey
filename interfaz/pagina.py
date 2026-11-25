"""Página principal: cabecera, panel + resultado a la izquierda y mapa a la derecha."""

from nicegui import ui

from interfaz.estilos import CSS
from interfaz.mapa import MapaMetro
from interfaz.panel import PanelViaje
from interfaz.resultado import mostrar_resultado
from metro.datos import COLORES_LINEA
from metro.ruta import calcular_ruta


@ui.page("/")
async def pagina_principal():
    ui.add_css(CSS)
    ui.colors(primary="#1E293B", secondary="#2E9E44", accent="#F2C200")
    modo_oscuro = ui.dark_mode()
    estado = {"resultado": None}

    # --- Cabecera
    with ui.header().classes("items-center justify-between no-wrap bg-white text-gray-900 shadow-sm px-6 py-3"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("subway", size="2rem").classes("text-gray-800")
            with ui.column().classes("gap-0"):
                ui.label("Metrorrey · Ruta óptima con A*").classes("text-lg sm:text-xl font-extrabold")
                with ui.row().classes("items-center gap-0"):
                    for color in COLORES_LINEA.values():
                        ui.element("span").classes("pildora-linea").style(f"background:{color}")
        ui.button(icon="dark_mode", on_click=modo_oscuro.toggle).props("flat round") \
            .tooltip("Modo oscuro")

    # --- Cuerpo: columna izquierda (panel + resultado) y mapa
    with ui.row().classes("w-full no-wrap gap-4 p-4 max-lg:flex-col lg:h-[calc(100vh-80px)]"):
        with ui.column().classes("gap-4 lg:overflow-y-auto shrink-0 w-full lg:w-[430px] lg:h-full pr-1"):
            panel = PanelViaje(al_calcular=lambda: calcular())
            zona_resultado = ui.column().classes("w-full gap-4")
        with ui.card().classes("tarjeta grow p-0 w-full max-lg:h-[70vh] lg:h-full"):
            mapa = MapaMetro(al_elegir_estacion=panel.elegir_desde_mapa)

    def animar():
        if estado["resultado"]:
            mapa.animar_traza(estado["resultado"]["traza_astar"])

    def calcular():
        r = calcular_ruta(**panel.parametros())
        estado["resultado"] = r
        zona_resultado.clear()
        with zona_resultado:
            mostrar_resultado(r, al_animar=animar)
        if r["ok"]:
            mapa.mostrar_ruta(r)
        else:
            mapa.quitar_resaltado()

    await mapa.preparar()
