# Web de la práctica (NiceGUI). Se arranca con: python main.py  ->  http://localhost:8080
# Todo el cálculo de rutas está en metro.py.

import os
from datetime import datetime, timedelta, timezone

from nicegui import ui

import metro
from metro import COLORES_LINEA, NOMBRES_LINEA, estaciones

CENTRO = (25.712, -100.305)
ZOOM = 13
EMOJI_LINEA = {"L1": "🟡", "L2": "🟢", "L3": "🔴"}
EMOJI_CLIMA = {"despejado": "☀️", "lluvia_ligera": "🌦️", "lluvia_intensa": "🌧️", "tormenta": "⛈️",
               "granizo": "🧊", "inundacion": "🌊", "calor_extremo": "🔥", "helada": "❄️",
               "niebla": "🌫️", "viento_fuerte": "💨"}
VIAJES_POPULARES = [
    ("talleres", "exposicion", "De punta a punta de la Línea 1"),
    ("sendero", "parque_fundidora", "Al Parque Fundidora"),
    ("universidad", "hospital_metropolitano", "Al Hospital Metropolitano"),
    ("san_bernabe", "general_i_zaragoza", "Al centro (Macroplaza)"),
]
# Fondos del mapa sin clave. Las licencias piden citarlos, por eso queda un crédito pequeñito.
ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/"
FONDOS = {
    "normal": (["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], "© OpenStreetMap"),
    "satelite": ([ESRI + "World_Imagery/MapServer/tile/{z}/{y}/{x}",
                  ESRI + "Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"],
                 "© Esri, Maxar, Earthstar Geographics"),
}

CSS = """
body { background: #EEF2F7; font-family: 'Inter', 'Segoe UI', system-ui, sans-serif; }
.cabecera { background: linear-gradient(120deg, #0F172A, #1E293B 55%, #334155); }
.franja { height: 5px; background: linear-gradient(90deg, #F2C200 0 33.3%, #2E9E44 33.3% 66.6%, #D7262E 66.6%); }
.tarjeta { border-radius: 20px; box-shadow: 0 10px 30px rgba(15,23,42,.08); }
.boton { background: linear-gradient(90deg, #0F172A, #334155) !important; color: white !important;
         border-radius: 14px !important; font-weight: 700; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px;
        font-size: .8rem; font-weight: 600; background: rgba(255,255,255,.12); color: white; }
.punto { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.paso { position: relative; padding: 0 0 16px 30px; }
.paso::before { content: ''; position: absolute; left: 9px; top: 22px; bottom: 0; width: 6px;
                border-radius: 4px; background: var(--color, #CBD5E1); }
.paso:last-child::before { display: none; }
.icono-paso { position: absolute; left: 0; top: 0; width: 24px; height: 24px; border-radius: 50%;
              display: flex; align-items: center; justify-content: center; color: white; }
.popular { border-radius: 14px; cursor: pointer; } .popular:hover { background: #F1F5F9; }
.cuerpo { display: flex; gap: 16px; align-items: flex-start; max-width: 1600px; margin: 0 auto;
          padding: 16px; width: 100%; box-sizing: border-box; }
.izquierda { width: 440px; flex-shrink: 0; display: flex; flex-direction: column; gap: 16px; }
.caja-mapa { flex: 1; min-width: 0; height: calc(100vh - 122px); min-height: 480px; position: sticky;
             top: 16px; padding: 0 !important; overflow: hidden; }
.mapa { width: 100%; height: 100%; }
.leyenda { position: absolute; top: 14px; right: 14px; z-index: 1000; background: rgba(255,255,255,.95);
           border-radius: 14px; padding: 10px 14px; box-shadow: 0 6px 20px rgba(15,23,42,.15); }
.selector-fondo { position: absolute; left: 14px; bottom: 14px; z-index: 1000; border-radius: 999px;
                  box-shadow: 0 6px 20px rgba(15,23,42,.2); }
.credito { position: absolute; right: 6px; bottom: 3px; z-index: 1000; font-size: 9px; color: #475569;
           background: rgba(255,255,255,.6); padding: 0 4px; border-radius: 4px; }
@media (max-width: 1023px) {
  .cuerpo { flex-direction: column; align-items: stretch; }
  .izquierda { width: 100%; }
  .caja-mapa { position: relative; top: 0; height: 70vh; }
  .solo-pc { display: none !important; }
}
"""


def hora_monterrey():
    # Monterrey está en UTC-6 todo el año (en México ya no hay cambio de hora)
    return datetime.now(timezone(timedelta(hours=-6))).strftime("%H:%M")


def opciones_estaciones():
    opciones = {}
    for linea in ("L1", "L2", "L3"):
        for e in metro.orden_linea(linea):
            if e not in opciones:
                emojis = "".join(EMOJI_LINEA[l] for l in estaciones[e]["lineas"])
                extra = " (Arena Monterrey)" if e == "parque_fundidora" else ""
                opciones[e] = f"{emojis}  {estaciones[e]['nombre']}{extra}"
    return opciones


@ui.page("/")
def pagina():
    ui.add_css(CSS)
    ui.colors(primary="#0F172A")
    ui.query(".nicegui-content").classes("p-0 gap-0")

    # ---------- cabecera
    with ui.element("header").classes("cabecera w-full text-white"):
        with ui.row().classes("w-full items-center justify-between no-wrap px-6 py-4") \
                .style("max-width:1600px;margin:0 auto"):
            with ui.row().classes("items-center gap-3 no-wrap"):
                ui.icon("subway", size="2rem").classes("rounded-2xl bg-white/10 p-2")
                with ui.column().classes("gap-0"):
                    ui.label("Metrorrey").classes("text-2xl font-extrabold leading-none")
                    ui.label("Encuentra la ruta más rápida en metro").classes("text-sm opacity-75")
            with ui.row().classes("gap-2 solo-pc"):
                for linea, color in COLORES_LINEA.items():
                    with ui.element("span").classes("chip"):
                        ui.element("span").classes("punto").style(f"background:{color}")
                        ui.label(linea.replace("L", "Línea "))
        ui.element("div").classes("franja w-full")

    with ui.element("div").classes("cuerpo"):
        # ---------- buscador
        with ui.element("div").classes("izquierda"):
            with ui.card().classes("tarjeta w-full gap-4 p-5"):
                ui.label("¿A dónde vas?").classes("text-2xl font-extrabold")
                ui.label("Elige las estaciones o tócalas en el mapa.").classes("text-sm text-slate-500 -mt-4")
                opciones = opciones_estaciones()
                with ui.row().classes("w-full items-center no-wrap gap-2"):
                    with ui.column().classes("grow gap-2"):
                        origen = ui.select(opciones, label="Desde", with_input=True, value="talleres") \
                            .props("outlined rounded dense").classes("w-full")
                        origen.add_slot("prepend", '<q-icon name="trip_origin" color="green-7" />')
                        destino = ui.select(opciones, label="Hasta", with_input=True,
                                            value="hospital_metropolitano") \
                            .props("outlined rounded dense").classes("w-full")
                        destino.add_slot("prepend", '<q-icon name="place" color="red-7" />')
                    ui.button(icon="swap_vert", on_click=lambda: intercambiar()) \
                        .props("round unelevated color=grey-2 text-color=grey-9")
                estilo_toggle = "spread rounded unelevated no-caps dense toggle-color=grey-9 color=grey-2 text-color=grey-9"
                modo = ui.toggle({"salida": "Salir a las", "llegada": "Llegar a las"}, value="salida") \
                    .props(estilo_toggle).classes("w-full")
                with ui.row().classes("w-full no-wrap gap-2 items-center"):
                    hora = ui.input("Hora (si la dejas vacía, ahora mismo)", value=hora_monterrey()) \
                        .props("type=time outlined rounded dense clearable").classes("grow")
                    ui.button("Ahora", on_click=lambda: hora.set_value(hora_monterrey())) \
                        .props("flat dense no-caps color=grey-8")
                dia = ui.toggle({"laborable": "Entre semana", "fin_de_semana": "Fin de semana / festivo"},
                                value="laborable").props(estilo_toggle).classes("w-full")
                clima = ui.select({k: f"{EMOJI_CLIMA[k]}  {c[0]}" for k, c in metro.CLIMAS.items()},
                                  value="despejado", label="¿Qué tiempo hace?") \
                    .props("outlined rounded dense").classes("w-full")
                with ui.column().classes("gap-0"):
                    evento = ui.switch("Hay un evento (concierto, partido, feria…)").props("color=amber-8")
                    menos_transbordos = ui.switch("Prefiero cambiar de línea lo menos posible").props("color=green-8")
                    accesible = ui.switch("Necesito ruta accesible ♿").props("color=blue-8")
                ui.button("Buscar ruta", icon="directions_subway", on_click=lambda: buscar()) \
                    .props("unelevated size=lg no-caps").classes("w-full boton")
            zona_resultado = ui.column().classes("w-full gap-4")

        # ---------- mapa
        with ui.card().classes("tarjeta caja-mapa"):
            mapa = ui.leaflet(center=CENTRO, zoom=ZOOM, options={"attributionControl": False}).classes("mapa")
            for capa in list(mapa.layers):        # quitamos el fondo que trae NiceGUI por defecto
                mapa.remove_layer(capa)
            ui.toggle({"normal": "Mapa", "satelite": "Satélite"}, value="normal",
                      on_change=lambda e: poner_fondo(e.value)) \
                .props("rounded unelevated no-caps dense toggle-color=grey-9 color=white text-color=grey-9") \
                .classes("selector-fondo")
            credito = ui.label().classes("credito")
            with ui.element("div").classes("leyenda"):
                ui.label("Red de Metrorrey").classes("text-xs font-bold text-gray-500 uppercase mb-1")
                for linea, color in COLORES_LINEA.items():
                    with ui.row().classes("items-center gap-2 no-wrap"):
                        ui.element("span").style(f"width:22px;height:6px;border-radius:4px;background:{color}")
                        ui.label(NOMBRES_LINEA[linea]).classes("text-sm")
                with ui.row().classes("items-center gap-2 no-wrap"):
                    ui.element("span").style("width:12px;height:12px;border-radius:50%;border:3px solid #1F2937;margin:0 5px")
                    ui.label("Transbordo").classes("text-sm")
                for nombre, color, _ in metro.LINEAS_EN_OBRAS:
                    with ui.row().classes("items-center gap-2 no-wrap"):
                        ui.element("span").style(f"width:22px;border-top:4px dashed {color}")
                        ui.label(f"{nombre} · en obras").classes("text-sm text-gray-500")

    ui.label("Propuesta de aplicación · Grupo 205, ETSI Informáticos (UPM) · Tiempos estimados") \
        .classes("w-full text-center text-xs text-slate-400 pb-4")

    # ---------- funciones del mapa
    capas = {"fondo": [], "red": [], "ruta": []}
    tooltips = []      # (capa, texto): se ponen cuando el mapa ya existe en el navegador

    def borrar(tipo):
        for capa in capas[tipo]:
            mapa.remove_layer(capa)
        capas[tipo] = []

    def poner_fondo(clave):
        urls, texto = FONDOS[clave]
        with mapa:
            borrar("fondo")
            capas["fondo"] = [mapa.tile_layer(url_template=u, options={"maxZoom": 19}) for u in urls]
        credito.set_text(texto)

    def circulo(lat, lon, opciones):
        return mapa.generic_layer(name="circleMarker", args=[(lat, lon), {"fillColor": "white", "fillOpacity": 1, **opciones}])

    def dibujar_red(atenuada=False):
        with mapa:
            borrar("red")
            for linea, color in COLORES_LINEA.items():
                puntos = [(estaciones[e]["lat"], estaciones[e]["lon"]) for e in metro.orden_linea(linea)]
                capas["red"].append(mapa.generic_layer(name="polyline", args=[puntos, {
                    "color": color, "weight": 7, "opacity": 0.35 if atenuada else 0.95}]))
            for e in estaciones.values():
                grande = e["transbordo"]
                capa = circulo(e["lat"], e["lon"], {"radius": 8 if grande else 5, "weight": 3 if grande else 2,
                                                    "color": "#1F2937" if grande else COLORES_LINEA[e["lineas"][0]],
                                                    "opacity": 0.5 if atenuada else 1})
                capas["red"].append(capa)
                tooltips.append((capa, f"<b>{e['nombre']}</b><br>{' · '.join(e['lineas'])}"))

    def dibujar_obras():
        # Líneas 4 y 6 en discontinua: están en obras y no se usan para calcular rutas
        with mapa:
            for nombre, color, paradas in metro.LINEAS_EN_OBRAS:
                puntos = [(lat, lon) for _, lat, lon in paradas]
                mapa.generic_layer(name="polyline", args=[puntos, {"color": color, "weight": 5,
                                                                   "opacity": 0.75, "dashArray": "10 10"}])
                for parada, lat, lon in paradas:
                    capa = circulo(lat, lon, {"radius": 4, "color": color, "weight": 2, "opacity": 0.8})
                    tooltips.append((capa, f"<b>{parada}</b><br>{nombre}<br><i>En obras, fuera de servicio</i>"))

    def poner_tooltips():
        for capa, texto in tooltips:
            capa.run_method("bindTooltip", texto)
        tooltips.clear()

    async def al_cargar_mapa():
        await mapa.initialized()
        mapa.run_map_method("invalidateSize")     # sin esto a veces sale gris
        poner_tooltips()

    def dibujar_ruta(r):
        borrar("ruta")
        dibujar_red(atenuada=True)
        poner_tooltips()
        colores = {"subir": "#16A34A", "bajar": "#DC2626", "transbordo": "#1F2937"}
        with mapa:
            for seg in r["segmentos"]:
                puntos = [(estaciones[e]["lat"], estaciones[e]["lon"]) for e in seg["estaciones"]]
                for color, grosor in (("#0F172A", 15), (seg["color"], 9)):   # borde oscuro + color
                    capas["ruta"].append(mapa.generic_layer(name="polyline", args=[puntos, {
                        "color": color, "weight": grosor, "opacity": 1}]))
            for p in r["pasos"]:
                if p["accion"] != "pasar":
                    capa = circulo(p["lat"], p["lon"], {"radius": 11, "color": "white", "weight": 3,
                                                        "fillColor": colores[p["accion"]]})
                    capa.run_method("bindTooltip", p["nombre"], {"permanent": True, "direction": "top",
                                                                 "offset": [0, -10]})
                    capas["ruta"].append(capa)
        lats = [p["lat"] for p in r["pasos"]]
        lons = [p["lon"] for p in r["pasos"]]
        mapa.run_map_method("fitBounds", [[min(lats), min(lons)], [max(lats), max(lons)]], {"padding": [70, 70]})

    def quitar_ruta():
        borrar("ruta")
        dibujar_red()
        poner_tooltips()
        mapa.set_center(CENTRO)
        mapa.set_zoom(ZOOM)

    clic_es_origen = [True]

    def clic_en_mapa(evento):
        # elegimos la estación más cercana al clic, si está a menos de 400 m
        lat, lon = evento.args["latlng"]["lat"], evento.args["latlng"]["lng"]
        e = min(estaciones.values(), key=lambda e: metro.haversine_km(lat, lon, e["lat"], e["lon"]))
        if metro.haversine_km(lat, lon, e["lat"], e["lon"]) > 0.4:
            return
        if clic_es_origen[0]:
            origen.value = e["id"]
            ui.notify(f"Origen: {e['nombre']}", position="top", type="positive", timeout=1500)
        else:
            destino.value = e["id"]
            ui.notify(f"Destino: {e['nombre']}", position="top", type="info", timeout=1500)
        clic_es_origen[0] = not clic_es_origen[0]

    # ---------- funciones del buscador y del resultado
    def intercambiar():
        origen.value, destino.value = destino.value, origen.value

    def buscar():
        opciones = dict(dia=dia.value, clima=clima.value, evento_masivo=evento.value,
                        minimizar_transbordos=menos_transbordos.value, accesible=accesible.value)
        h = hora.value or hora_monterrey()
        if modo.value == "llegada":
            r = metro.calcular_ruta_llegando_a(origen.value, destino.value, h, **opciones)
        else:
            r = metro.calcular_ruta(origen.value, destino.value, hora=h, **opciones)
        zona_resultado.clear()
        with zona_resultado:
            mostrar_resultado(r)
        if r["ok"]:
            dibujar_ruta(r)
        else:
            quitar_ruta()

    def viaje_popular(o, d):
        origen.value, destino.value = o, d
        buscar()

    def mostrar_bienvenida():
        km = sum(t[3] for t in metro.TRAMOS) / 1000
        with ui.card().classes("tarjeta w-full p-5 gap-3"):
            with ui.row().classes("w-full justify-around text-center"):
                for cifra, texto in (("3", "líneas"), (str(len(estaciones)), "estaciones"), (f"{km:.0f} km", "de vía")):
                    with ui.column().classes("items-center gap-0"):
                        ui.label(cifra).classes("text-3xl font-extrabold")
                        ui.label(texto).classes("text-xs uppercase text-slate-500")
            with ui.row().classes("w-full no-wrap gap-2 rounded-xl bg-slate-50 border p-3"):
                ui.icon("construction").classes("text-orange-600 text-lg")
                ui.label("Las Líneas 4 y 6 están en obras y temporalmente fuera de servicio. Las verás en "
                         "el mapa en discontinua, pero todavía no se usan para calcular viajes.").classes("text-sm")
            ui.separator()
            ui.label("Viajes populares").classes("font-bold")
            for o, d, titulo in VIAJES_POPULARES:
                with ui.row().classes("popular w-full items-center no-wrap gap-3 p-2") \
                        .on("click", lambda o=o, d=d: viaje_popular(o, d)):
                    ui.icon("near_me").classes("text-slate-400")
                    with ui.column().classes("gap-0 grow"):
                        ui.label(titulo).classes("text-sm font-semibold")
                        ui.label(f"{estaciones[o]['nombre']} → {estaciones[d]['nombre']}").classes("text-xs text-slate-500")
                    ui.icon("chevron_right").classes("text-slate-400")

    def mostrar_resultado(r):
        if not r["ok"]:
            with ui.card().classes("tarjeta w-full p-5"):
                ui.label(r["motivo"]).classes("font-medium")
            return
        llegada = r["modo"] == "llegada"
        with ui.card().classes("tarjeta w-full p-0 gap-0 overflow-hidden"):
            # cabecera oscura con los minutos y la hora
            with ui.column().classes("cabecera w-full p-5 gap-2 text-white"):
                ui.label(f"{r['origen']}  →  {r['destino']}").classes("text-sm opacity-80")
                with ui.row().classes("w-full items-end justify-between"):
                    with ui.row().classes("items-baseline gap-1"):
                        ui.label(f"{r['tiempo_total_min']:.0f}").classes("text-5xl font-extrabold")
                        ui.label("min").classes("text-xl opacity-80")
                    with ui.column().classes("items-end gap-0"):
                        ui.label("Sal a las" if llegada else "Llegas a las").classes("text-xs opacity-70")
                        ui.label(r["hora_salida"] if llegada else r["hora_llegada"]).classes("text-3xl font-bold")
                t = r["num_transbordos"]
                with ui.row().classes("gap-2"):
                    for texto, icono in (("Sin transbordos" if t == 0 else f"{t} transbordo{'s' * (t > 1)}", "sync_alt"),
                                         (f"{r['distancia_km']:.1f} km", "straighten"),
                                         (f"Llegada {r['hora_llegada']}" if llegada else f"Salida {r['hora_salida']}", "schedule")):
                        with ui.element("span").classes("chip"):
                            ui.icon(icono)
                            ui.label(texto)

            with ui.column().classes("w-full p-5 gap-4"):
                for aviso in r["avisos"]:
                    with ui.row().classes("w-full no-wrap gap-2 rounded-xl bg-amber-50 border border-amber-200 p-3"):
                        ui.icon("warning_amber").classes("text-amber-600 text-lg")
                        ui.label(aviso).classes("text-sm text-amber-900")

                # pasos del viaje
                with ui.column().classes("w-full gap-0"):
                    for i, seg in enumerate(r["segmentos"]):
                        mostrar_segmento(r, i, seg)
                    with ui.element("div").classes("paso"):
                        with ui.element("div").classes("icono-paso").style("background:#DC2626"):
                            ui.icon("flag").classes("text-sm")
                        ui.label(f"Llegas a {r['destino']}").classes("font-bold")
                        ui.label(f"Hacia las {r['hora_llegada']}").classes("text-sm text-slate-500")

                # en qué se va el tiempo
                ui.label("¿En qué se va el tiempo?").classes("font-bold")
                partes = [("En el tren", r["desglose"]["en_tren"], "#2563EB"),
                          ("Esperando el tren", r["desglose"]["esperas"], "#F59E0B"),
                          ("Cambiando de línea", r["desglose"]["transbordos"], "#DB2777")]
                total = sum(p[1] for p in partes) or 1
                with ui.element("div").classes("w-full flex rounded-lg overflow-hidden").style("height:12px"):
                    for _, mins, color in partes:
                        ui.element("div").style(f"width:{100 * mins / total}%;background:{color}")
                with ui.row().classes("gap-x-5 gap-y-1"):
                    for nombre, mins, color in partes:
                        if mins > 0:
                            with ui.row().classes("items-center gap-1 no-wrap"):
                                ui.element("span").classes("punto").style(f"background:{color}")
                                ui.label(f"{nombre} · {mins:.0f} min").classes("text-xs text-slate-600")
                ui.label(f"Calculado para: {r['franja'].lower()}, {r['clima'].lower()}.").classes("text-xs text-slate-400")

    def mostrar_segmento(r, i, seg):
        color = COLORES_LINEA[seg["linea"]]
        with ui.element("div").classes("paso").style(f"--color:{color}"):
            with ui.element("div").classes("icono-paso").style(f"background:{color if i == 0 else '#1F2937'}"):
                ui.icon("directions_subway" if i == 0 else "sync_alt").classes("text-sm")
            desde = estaciones[seg["desde"]]["nombre"]
            with ui.row().classes("w-full justify-between no-wrap"):
                ui.label(f"Sube en {desde}" if i == 0 else f"Cambia de línea en {desde}").classes("font-bold")
                ui.label(metro.hora_mas(r["hora_salida"], seg["minuto_inicio"])).classes("text-sm text-slate-500")
            with ui.row().classes("items-center gap-2 mt-1"):
                ui.label(NOMBRES_LINEA[seg["linea"]]).style(
                    f"background:{color};color:{'#1F2937' if seg['linea'] == 'L1' else 'white'};"
                    "padding:2px 10px;border-radius:999px;font-weight:700;font-size:.8rem")
                ui.label(f"dirección {seg['direccion']}").classes("text-sm text-slate-600")
            n = seg["num_paradas"]
            mins = seg["minuto_fin"] - seg["minuto_inicio"]
            resumen = f"{n} parada{'s' * (n != 1)} · {mins:.0f} min · bájate en {estaciones[seg['hasta']]['nombre']}"
            intermedias = [estaciones[e]["nombre"] for e in seg["estaciones"][1:-1]]
            if intermedias:
                with ui.expansion(resumen).props("dense header-class='px-0 text-slate-600'").classes("w-full text-sm"):
                    ui.label("Pasas por: " + " · ".join(intermedias)).classes("text-xs text-slate-500")
            else:
                ui.label(resumen).classes("text-sm text-slate-600 mt-1")

    # ---------- arranque de la página
    poner_fondo("normal")
    dibujar_obras()
    dibujar_red()
    mapa.on("map-click", clic_en_mapa)
    with zona_resultado:
        mostrar_bienvenida()
    ui.timer(0.3, al_cargar_mapa, once=True)


if __name__ in {"__main__", "__mp_main__"}:
    en_servidor = "PORT" in os.environ      # en Render el puerto llega en PORT
    ui.run(title="Metrorrey · Ruta más rápida", favicon="🚇", language="es", reload=False,
           host="0.0.0.0" if en_servidor else "127.0.0.1", port=int(os.environ.get("PORT", 8080)),
           show=not en_servidor)
