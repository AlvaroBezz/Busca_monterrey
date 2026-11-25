"""Tarjetas de la columna izquierda: pantalla de bienvenida y resultado del viaje."""

from nicegui import ui

from interfaz.estilos import COLORES_DESGLOSE, RUTAS_POPULARES
from metro.coste import minutos_del_dia
from metro.datos import COLORES_LINEA, NOMBRES_LINEA, cargar_datos


def _hora_mas(hora, minutos):
    total = (minutos_del_dia(hora) + round(minutos)) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def mostrar_bienvenida(al_elegir_ruta):
    """Cifras de la red y viajes de ejemplo, antes de buscar nada."""
    datos = cargar_datos()
    km = sum(t["distancia_m"] for t in datos.tramos) / 1000
    with ui.card().classes("tarjeta w-full p-5 gap-3"):
        with ui.row().classes("w-full justify-around text-center"):
            for cifra, texto in (("3", "líneas"), (str(len(datos.estaciones)), "estaciones"),
                                 (f"{km:.0f} km", "de vía")):
                with ui.column().classes("items-center gap-0"):
                    ui.label(cifra).classes("text-3xl font-extrabold text-slate-900")
                    ui.label(texto).classes("text-xs uppercase tracking-wide text-slate-500")
        ui.separator()
        ui.label("Viajes populares").classes("font-bold text-slate-800")
        for origen, destino, titulo in RUTAS_POPULARES:
            o, d = datos.estaciones[origen], datos.estaciones[destino]
            with ui.row().classes("ruta-popular w-full items-center no-wrap gap-3 p-2") \
                    .on("click", lambda o=origen, d=destino: al_elegir_ruta(o, d)):
                ui.icon("near_me").classes("text-slate-400")
                with ui.column().classes("gap-0 grow"):
                    ui.label(titulo).classes("text-sm font-semibold")
                    ui.label(f"{o['nombre']} → {d['nombre']}").classes("text-xs text-slate-500")
                ui.icon("chevron_right").classes("text-slate-400")


def mostrar_resultado(r):
    """Pinta el resultado de calcular_ruta() dentro del contenedor actual."""
    if not r["ok"]:
        with ui.card().classes("tarjeta w-full p-5"):
            with ui.row().classes("items-center gap-2 no-wrap"):
                ui.icon("info").classes("text-2xl text-blue-600")
                ui.label(r["motivo"]).classes("font-medium")
        return

    datos = cargar_datos()
    with ui.card().classes("tarjeta w-full p-0 gap-0 overflow-hidden"):
        # --- Cabecera oscura con la duración
        with ui.column().classes("cabecera w-full p-5 gap-2 text-white"):
            ui.label(f"{r['origen']}  →  {r['destino']}").classes("text-sm opacity-80")
            with ui.row().classes("w-full items-end justify-between"):
                with ui.row().classes("items-baseline gap-1"):
                    ui.label(f"{r['tiempo_total_min']:.0f}").classes("cifra-grande")
                    ui.label("min").classes("text-xl font-semibold opacity-80")
                with ui.column().classes("items-end gap-0"):
                    if r.get("modo") == "llegada":
                        ui.label("Sal a las").classes("text-xs opacity-70")
                        ui.label(r["hora_salida"]).classes("text-3xl font-bold")
                    else:
                        ui.label("Llegas a las").classes("text-xs opacity-70")
                        ui.label(r["hora_llegada"]).classes("text-3xl font-bold")
            with ui.row().classes("gap-2"):
                t = r["num_transbordos"]
                texto_t = "Sin transbordos" if t == 0 else f"{t} transbordo{'s' if t > 1 else ''}"
                for texto, icono in ((texto_t, "sync_alt"),
                                     (f"{r['distancia_km']:.1f} km", "straighten"),
                                     ((f"Llegada {r['hora_llegada']}" if r.get("modo") == "llegada"
                                       else f"Salida {r['hora_salida']}"), "schedule")):
                    with ui.element("span").classes("insignia"):
                        ui.icon(icono).classes("text-sm")
                        ui.label(texto)

        with ui.column().classes("w-full p-5 gap-4"):
            for aviso in r["avisos"]:
                with ui.row().classes("w-full items-start no-wrap gap-2 rounded-xl bg-amber-50 "
                                      "border border-amber-200 text-amber-900 p-3"):
                    ui.icon("warning_amber").classes("text-amber-600 text-lg")
                    ui.label(aviso).classes("text-sm")

            # --- Pasos del viaje
            with ui.column().classes("w-full gap-0"):
                for i, seg in enumerate(r["segmentos"]):
                    _paso_segmento(datos, r, i, seg)
                with ui.element("div").classes("paso"):
                    with ui.element("div").classes("icono-paso").style("background:#DC2626"):
                        ui.icon("flag").classes("text-sm")
                    ui.label(f"Llegas a {r['destino']}").classes("font-bold text-slate-900")
                    ui.label(f"Hacia las {r['hora_llegada']}").classes("text-sm text-slate-500")

            # --- Desglose del tiempo en palabras sencillas
            ui.label("¿En qué se va el tiempo?").classes("font-bold text-slate-800")
            partes = {"en_tren": r["desglose"]["en_tren"], "esperas": r["desglose"]["esperas"],
                      "transbordos": r["desglose"]["transbordos"]}
            total = sum(partes.values()) or 1
            with ui.element("div").classes("barra-desglose w-full"):
                for clave, (color, _) in COLORES_DESGLOSE.items():
                    if partes[clave] > 0:
                        ui.element("div").style(f"width:{100 * partes[clave] / total}%;background:{color}")
            with ui.row().classes("gap-x-5 gap-y-1"):
                for clave, (color, etiqueta) in COLORES_DESGLOSE.items():
                    if partes[clave] > 0:
                        with ui.row().classes("items-center gap-1 no-wrap"):
                            ui.element("span").classes("punto").style(f"background:{color}")
                            ui.label(f"{etiqueta} · {partes[clave]:.0f} min").classes("text-xs text-slate-600")
            ui.label(f"Calculado para: {r['franja'].lower()}, {r['clima'].lower()}.") \
                .classes("text-xs text-slate-400")


def _paso_segmento(datos, r, i, seg):
    """Un bloque del itinerario: subir (o cambiar) a una línea y viajar varias paradas."""
    color = COLORES_LINEA[seg["linea"]]
    desde = datos.estaciones[seg["desde"]]["nombre"]
    hasta = datos.estaciones[seg["hasta"]]["nombre"]
    hora = _hora_mas(r["hora_salida"], seg["minuto_inicio"])
    duracion = seg["minuto_fin"] - seg["minuto_inicio"]
    with ui.element("div").classes("paso").style(f"--color-paso:{color}"):
        icono = "directions_subway" if i == 0 else "sync_alt"
        with ui.element("div").classes("icono-paso").style(f"background:{color if i == 0 else '#1F2937'}"):
            ui.icon(icono).classes("text-sm")
        titulo = f"Sube en {desde}" if i == 0 else f"Cambia de línea en {desde}"
        with ui.row().classes("w-full justify-between items-baseline no-wrap"):
            ui.label(titulo).classes("font-bold text-slate-900")
            ui.label(hora).classes("text-sm font-semibold text-slate-500")
        with ui.row().classes("items-center gap-2 mt-1"):
            texto_color = "#1F2937" if seg["linea"] == "L1" else "white"
            ui.label(NOMBRES_LINEA[seg["linea"]]).style(
                f"background:{color};color:{texto_color};padding:2px 10px;border-radius:999px;"
                "font-weight:700;font-size:.8rem")
            ui.label(f"dirección {seg['direccion']}").classes("text-sm text-slate-600")
        paradas = seg["num_paradas"]
        intermedias = [datos.estaciones[e]["nombre"] for e in seg["estaciones"][1:-1]]
        resumen = f"{paradas} parada{'s' if paradas != 1 else ''} · {duracion:.0f} min · bájate en {hasta}"
        if intermedias:
            with ui.expansion(resumen).props("dense dense-toggle header-class='px-0 text-slate-600'") \
                    .classes("w-full text-sm"):
                ui.label("Pasas por: " + " · ".join(intermedias)).classes("text-xs text-slate-500")
        else:
            ui.label(resumen).classes("text-sm text-slate-600 mt-1")
