"""Tarjeta de resultado: tiempo, itinerario, desglose y explicación de A*."""

from nicegui import ui

from interfaz.estilos import COLORES_DESGLOSE
from metro.datos import NOMBRES_LINEA, cargar_datos


def mostrar_resultado(r, al_animar):
    """Pinta el resultado de calcular_ruta() dentro del contenedor actual."""
    if not r["ok"]:
        with ui.card().classes("tarjeta w-full bg-amber-50"):
            ui.label(r["motivo"]).classes("font-medium")
        return

    datos = cargar_datos()
    with ui.card().classes("tarjeta w-full gap-3"):
        # --- Cifras principales
        with ui.row().classes("w-full items-end justify-between"):
            with ui.column().classes("gap-0"):
                ui.label(f"{r['origen']} → {r['destino']}").classes("text-sm text-gray-500")
                with ui.row().classes("items-baseline gap-1"):
                    ui.label(f"{r['tiempo_total_min']:.0f}").classes("cifra-grande")
                    ui.label("min").classes("text-xl font-semibold text-gray-500")
            with ui.column().classes("items-end gap-0"):
                ui.label(f"Llegada ≈ {r['hora_llegada']}").classes("text-lg font-semibold")
                ui.label(f"Salida {r['hora_salida']}").classes("text-xs text-gray-500")
        with ui.row().classes("gap-1"):
            transbordos = r["num_transbordos"]
            ui.chip(f"{transbordos} transbordo{'s' if transbordos != 1 else ''}", icon="sync_alt").props("outline dense")
            ui.chip(f"{r['distancia_km']:.1f} km", icon="straighten").props("outline dense")
            ui.chip(r["franja"], icon="schedule").props("outline dense")
            ui.chip(r["clima"], icon="cloud").props("outline dense")

        for aviso in r["avisos"]:
            with ui.row().classes("w-full items-start no-wrap gap-2 rounded-lg bg-amber-100 text-amber-900 p-2"):
                ui.icon("warning").classes("text-amber-600")
                ui.label(aviso).classes("text-sm")

        # --- Itinerario: un bloque por cada tramo dentro de una línea
        ui.label("Itinerario").classes("font-bold mt-1")
        for i, seg in enumerate(r["segmentos"]):
            nombre_desde = datos.estaciones[seg["desde"]]["nombre"]
            nombre_hasta = datos.estaciones[seg["hasta"]]["nombre"]
            with ui.element("div").classes("segmento w-full").style(f"border-color: {seg['color']}"):
                titulo = "Sube en" if i == 0 else "Transbordo en"
                ui.label(f"{titulo} {nombre_desde}").classes("font-semibold")
                ui.label(f"{NOMBRES_LINEA[seg['linea']]} · dirección {seg['direccion']}") \
                    .classes("text-sm").style(f"color: {seg['color']}; filter: brightness(0.8)")
                intermedias = [datos.estaciones[e]["nombre"] for e in seg["estaciones"][1:-1]]
                texto = f"{seg['num_paradas']} parada{'s' if seg['num_paradas'] != 1 else ''}"
                if intermedias:
                    with ui.expansion(texto).props("dense").classes("text-sm text-gray-600 w-full"):
                        ui.label(" · ".join(intermedias)).classes("text-xs")
                else:
                    ui.label(texto).classes("text-sm text-gray-600")
                ui.label(f"min {seg['minuto_inicio']:.0f} → {seg['minuto_fin']:.0f}").classes("text-xs text-gray-400")
        with ui.row().classes("items-center gap-2 ml-1"):
            ui.icon("flag").classes("text-red-600")
            ui.label(f"Baja en {r['destino']}").classes("font-semibold")

        # --- Desglose del tiempo
        ui.label("¿En qué se va el tiempo?").classes("font-bold mt-1")
        total = sum(r["desglose"][k] for k in COLORES_DESGLOSE) or 1
        with ui.element("div").classes("barra-desglose w-full"):
            for clave, (color, _) in COLORES_DESGLOSE.items():
                ancho = 100 * r["desglose"][clave] / total
                if ancho > 0:
                    ui.element("div").style(f"width: {ancho}%; background: {color}")
        with ui.row().classes("gap-x-4 gap-y-1"):
            for clave, (color, etiqueta) in COLORES_DESGLOSE.items():
                with ui.row().classes("items-center gap-1 no-wrap"):
                    ui.element("span").style(f"width:10px;height:10px;border-radius:3px;background:{color}")
                    ui.label(f"{etiqueta}: {r['desglose'][clave]:.1f} min").classes("text-xs")
        if r["desglose"]["penalizaciones"]:
            ui.label(f"Penalizaciones de preferencia (no son tiempo real): "
                     f"+{r['desglose']['penalizaciones']:.0f} min en el coste de A*").classes("text-xs text-gray-500")

        mostrar_explicacion_astar(r, al_animar)


def mostrar_explicacion_astar(r, al_animar):
    """Expansión con la traza paso a paso de A* y la comparación con Dijkstra."""
    with ui.expansion("¿Cómo lo ha calculado A*?", icon="psychology").classes("w-full rounded-lg bg-indigo-50"):
        a, d = r["nodos_expandidos"], r["nodos_expandidos_dijkstra"]
        with ui.row().classes("gap-2"):
            ui.chip(f"A*: {a} nodos expandidos", icon="bolt").props("color=indigo text-color=white dense")
            ui.chip(f"Dijkstra: {d} nodos", icon="blur_on").props("outline dense")
        ui.markdown(
            "A* saca siempre de la frontera el nodo con menor **f(n) = g(n) + h(n)**: "
            "g es el tiempo real acumulado y h la estimación optimista "
            "(distancia en línea recta / 80 km/h). Dijkstra es lo mismo con h = 0, "
            f"así que explora a ciegas en todas direcciones. Aquí A* ha expandido {d - a} "
            "nodos menos y ha encontrado la misma ruta óptima."
            if d > a else
            "A* saca siempre de la frontera el nodo con menor **f(n) = g(n) + h(n)**. "
            "En este trayecto h no ha permitido descartar nodos respecto a Dijkstra "
            "(h = 0): las paradas y esperas hacen que h, que solo cuenta la línea recta "
            "a 80 km/h, se quede corta. El resultado sigue siendo óptimo."
        ).classes("text-sm")
        columnas = [
            {"name": "paso", "label": "Paso", "field": "paso", "align": "left"},
            {"name": "nodo", "label": "Nodo expandido", "field": "nodo", "align": "left"},
            {"name": "g", "label": "g (min)", "field": "g"},
            {"name": "h", "label": "h (min)", "field": "h"},
            {"name": "f", "label": "f = g + h", "field": "f"},
            {"name": "frontera", "label": "Abiertos", "field": "frontera"},
        ]
        filas = [{**t, "nodo": _nombre_nodo(t["nodo"]), "g": f"{t['g']:.2f}",
                  "h": f"{t['h']:.2f}", "f": f"{t['f']:.2f}"} for t in r["traza_astar"]]
        ui.table(columns=columnas, rows=filas, row_key="paso", pagination=10) \
            .props('dense flat rows-per-page-label="Filas por página"').classes("w-full text-xs")
        ui.button("Ver animación en el mapa", icon="play_arrow", on_click=al_animar) \
            .props("outline").classes("w-full")


def _nombre_nodo(nodo):
    """'cuauhtemoc@L2' → 'Cuauhtémoc (L2)'."""
    if "@" not in nodo:
        return nodo
    estacion, linea = nodo.split("@")
    return f"{cargar_datos().estaciones[estacion]['nombre']} ({linea})"
