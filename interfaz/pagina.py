"""Página principal: cabecera, buscador + resultado a la izquierda y mapa a la derecha."""

from nicegui import ui

from interfaz.estilos import CSS
from interfaz.mapa import MapaMetro
from interfaz.panel import PanelViaje
from interfaz.resultado import mostrar_bienvenida, mostrar_resultado
from metro.ruta import calcular_ruta


@ui.page("/")
def pagina_principal():
    ui.add_css(CSS)
    ui.colors(primary="#0F172A", secondary="#2E9E44", accent="#F2C200")
    ui.query(".nicegui-content").classes("p-0 gap-0")

    # --- Cabecera
    with ui.element("header").classes("cabecera w-full text-white"):
        with ui.row().classes("w-full items-center justify-between no-wrap px-6 py-4").style("max-width:1600px;margin:0 auto"):
            with ui.row().classes("items-center gap-3 no-wrap"):
                with ui.element("div").classes("rounded-2xl bg-white/10 p-2"):
                    ui.icon("subway", size="2rem")
                with ui.column().classes("gap-0"):
                    ui.label("Metrorrey").classes("text-2xl font-extrabold leading-none")
                    ui.label("Encuentra la ruta más rápida en metro").classes("text-sm opacity-75")
            with ui.row().classes("gap-2 solo-escritorio"):
                for texto, color in (("Línea 1", "#F2C200"), ("Línea 2", "#2E9E44"), ("Línea 3", "#D7262E")):
                    with ui.element("span").classes("insignia"):
                        ui.element("span").classes("punto").style(f"background:{color}")
                        ui.label(texto)
        ui.element("div").classes("franja-lineas w-full")

    # --- Cuerpo: columna izquierda (buscador + resultado) y mapa
    with ui.element("div").classes("cuerpo"):
        with ui.element("div").classes("columna-izq"):
            panel = PanelViaje(al_calcular=lambda: calcular())
            zona_resultado = ui.column().classes("w-full gap-4")
        with ui.card().classes("tarjeta tarjeta-mapa"):
            mapa = MapaMetro(al_elegir_estacion=panel.elegir_desde_mapa)

    ui.label("Propuesta de aplicación · Grupo 205, ETSI Informáticos (UPM) · Tiempos estimados") \
        .classes("w-full text-center text-xs text-slate-400 pb-4")

    def elegir_ruta_popular(origen, destino):
        panel.poner_viaje(origen, destino)
        calcular()

    def calcular():
        r = calcular_ruta(**panel.parametros())
        zona_resultado.clear()
        with zona_resultado:
            mostrar_resultado(r)
        if r["ok"]:
            mapa.mostrar_ruta(r)
        else:
            mapa.quitar_resaltado()

    with zona_resultado:
        mostrar_bienvenida(elegir_ruta_popular)

    # Cuando el navegador ya ha creado el mapa, ajustamos su tamaño (evita que salga gris)
    ui.timer(0.3, mapa.preparar, once=True)
