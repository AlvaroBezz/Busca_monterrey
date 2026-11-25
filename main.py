"""La web de Metrorrey (NiceGUI). Arranca con:  python main.py  → http://localhost:8080

Secciones:
    1. ESTILOS     colores, iconos y CSS
    2. MAPA        mapa de Monterrey con las líneas, las estaciones y la ruta (ui.leaflet)
    3. BUSCADOR    origen, destino, hora, día, tiempo y preferencias
    4. RESULTADO   pantalla de bienvenida y tarjeta con el viaje
    5. PÁGINA      monta todo y llama a metro.calcular_ruta()
    6. ARRANQUE    en tu ordenador o en un servidor (Render pasa el puerto en PORT)

Todo el cálculo (grafo, g(n), h(n), A*) está en metro.py.
"""

import os
from datetime import datetime, timedelta, timezone

from nicegui import ui

from metro import (COLORES_LINEA, NOMBRES_LINEA, calcular_ruta, calcular_ruta_llegando_a,
                   cargar_datos, haversine_km, hora_mas, lineas_en_obras)


# ========================================================================================
# 1. ESTILOS
# ========================================================================================
# Colores, textos e iconos compartidos por toda la interfaz.

EMOJI_LINEA = {"L1": "🟡", "L2": "🟢", "L3": "🔴"}

EMOJI_CLIMA = {
    "despejado": "☀️", "lluvia_ligera": "🌦️", "lluvia_intensa": "🌧️", "tormenta": "⛈️",
    "granizo": "🧊", "inundacion": "🌊", "calor_extremo": "🔥", "helada": "❄️",
    "niebla": "🌫️", "viento_fuerte": "💨",
}

# Partes del tiempo de viaje, con nombres para el público
COLORES_DESGLOSE = {
    "en_tren": ("#2563EB", "En el tren"),
    "esperas": ("#F59E0B", "Esperando el tren"),
    "transbordos": ("#DB2777", "Cambiando de línea"),
}

# Viajes de ejemplo para la pantalla inicial
RUTAS_POPULARES = [
    ("talleres", "exposicion", "De punta a punta de la Línea 1"),
    ("sendero", "parque_fundidora", "Al Parque Fundidora"),
    ("universidad", "hospital_metropolitano", "Al Hospital Metropolitano"),
    ("san_bernabe", "general_i_zaragoza", "Al centro (Macroplaza)"),
]

CSS = f"""
:root {{ --l1: {COLORES_LINEA['L1']}; --l2: {COLORES_LINEA['L2']}; --l3: {COLORES_LINEA['L3']}; }}
body {{ background: #EEF2F7; font-family: 'Inter', 'Segoe UI', system-ui, sans-serif; }}
.cabecera {{ background: linear-gradient(120deg, #0F172A 0%, #1E293B 55%, #334155 100%); }}
.franja-lineas {{ height: 5px; background: linear-gradient(90deg, var(--l1) 0 33.3%, var(--l2) 33.3% 66.6%, var(--l3) 66.6% 100%); }}
.tarjeta {{ border-radius: 20px; box-shadow: 0 10px 30px rgba(15, 23, 42, .08); border: 1px solid rgba(15,23,42,.05); }}
.cifra-grande {{ font-size: 3.2rem; font-weight: 800; line-height: 1; letter-spacing: -0.03em; }}
.boton-principal {{ background: linear-gradient(90deg, #0F172A, #334155) !important; color: white !important;
                    border-radius: 14px !important; font-weight: 700; letter-spacing: .02em; }}
.insignia {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px;
             font-size: .8rem; font-weight: 600; background: rgba(255,255,255,.12); color: white; }}
.punto {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
.paso {{ position: relative; padding: 0 0 16px 30px; }}
.paso::before {{ content: ''; position: absolute; left: 9px; top: 22px; bottom: 0; width: 6px;
                 border-radius: 4px; background: var(--color-paso, #CBD5E1); }}
.paso:last-child::before {{ display: none; }}
.paso .icono-paso {{ position: absolute; left: 0; top: 0; width: 24px; height: 24px; border-radius: 50%;
                     display: flex; align-items: center; justify-content: center; color: white; font-size: 14px; }}
.barra-desglose {{ display: flex; height: 12px; border-radius: 8px; overflow: hidden; background: #E2E8F0; }}
.leyenda-mapa {{ position: absolute; top: 14px; right: 14px; z-index: 1000; background: rgba(255,255,255,.95);
                 border-radius: 14px; padding: 10px 14px; box-shadow: 0 6px 20px rgba(15,23,42,.15); }}
.ruta-popular {{ border-radius: 14px; transition: all .15s; cursor: pointer; }}
.ruta-popular:hover {{ background: #F1F5F9; transform: translateY(-1px); }}
.cuerpo {{ display: flex; gap: 16px; align-items: flex-start; max-width: 1600px; margin: 0 auto;
           padding: 16px; width: 100%; box-sizing: border-box; }}
.columna-izq {{ width: 440px; flex-shrink: 0; display: flex; flex-direction: column; gap: 16px; }}
.tarjeta-mapa {{ flex: 1 1 auto; min-width: 0; height: calc(100vh - 122px); min-height: 480px;
                 position: sticky; top: 16px; padding: 0 !important; overflow: hidden; }}
@media (max-width: 1023px) {{
  .cuerpo {{ flex-direction: column; align-items: stretch; }}
  .columna-izq {{ width: 100%; }}
  .tarjeta-mapa {{ position: relative; top: 0; height: 70vh; width: 100%; }}
  .solo-escritorio {{ display: none !important; }}
}}
.selector-fondo {{ position: absolute; left: 14px; bottom: 14px; z-index: 1000;
                   box-shadow: 0 6px 20px rgba(15,23,42,.2); border-radius: 999px; }}
.credito-mapa {{ position: absolute; right: 6px; bottom: 3px; z-index: 1000; font-size: 9px;
                 color: #475569; background: rgba(255,255,255,.6); padding: 0 4px; border-radius: 4px; }}
.mapa-metro {{ width: 100%; height: 100%; min-height: 420px; border-radius: 20px; }}
"""


# ========================================================================================
# 2. MAPA
# ========================================================================================
# Mapa de Monterrey con las tres líneas, las estaciones y la ruta calculada (ui.leaflet).

CENTRO_MONTERREY = (25.712, -100.305)
ZOOM_INICIAL = 13
DISTANCIA_MAX_CLIC_KM = 0.4   # un clic elige la estación más cercana a menos de 400 m

# Fondos del mapa, gratuitos y sin clave. Sus licencias piden citar la fuente: se hace con un
# crédito pequeño en una esquina del mapa (sin el pie de Leaflet).
ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services"
FONDOS = {
    "normal": {"capas": ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
               "credito": "© OpenStreetMap"},
    "satelite": {"capas": [ESRI + "/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                           ESRI + "/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"],
                 "credito": "© Esri, Maxar, Earthstar Geographics"},
}


class MapaMetro:
    """Envuelve un ui.leaflet y sabe pintar la red y la ruta."""

    def __init__(self, al_elegir_estacion):
        """al_elegir_estacion(id_estacion) se llama cuando el usuario hace clic cerca de una estación."""
        self.datos = cargar_datos()
        self.al_elegir_estacion = al_elegir_estacion
        self.capas_red = []        # líneas y estaciones de la red
        self.capas_ruta = []       # ruta resaltada y marcadores de origen/destino
        self.capas_obras = []      # líneas 4 y 6 (en construcción, solo informativas)
        self.capas_fondo = []      # teselas del fondo (normal o satélite)

        with ui.element("div").style("position: relative; width: 100%; height: 100%"):
            self.mapa = ui.leaflet(center=CENTRO_MONTERREY, zoom=ZOOM_INICIAL,
                                   options={"zoomControl": True, "attributionControl": False}) \
                .classes("mapa-metro")
            for capa in list(self.mapa.layers):      # quitamos el fondo que trae NiceGUI
                self.mapa.remove_layer(capa)
            ui.toggle({"normal": "Mapa", "satelite": "Satélite"}, value="normal",
                      on_change=lambda e: self.poner_fondo(e.value)) \
                .props("rounded unelevated no-caps dense toggle-color=grey-9 color=white "
                       "text-color=grey-9").classes("selector-fondo")
            self.credito = ui.label().classes("credito-mapa")
            self.poner_fondo("normal")
            with ui.element("div").classes("leyenda-mapa"):
                ui.label("Red de Metrorrey").classes("text-xs font-bold text-gray-500 uppercase mb-1")
                for linea, color in COLORES_LINEA.items():
                    with ui.row().classes("items-center gap-2 no-wrap"):
                        ui.element("span").style(f"width:22px;height:6px;border-radius:4px;background:{color}")
                        ui.label(NOMBRES_LINEA[linea]).classes("text-sm")
                with ui.row().classes("items-center gap-2 no-wrap mt-1"):
                    ui.element("span").style("width:12px;height:12px;border-radius:50%;border:3px solid #1F2937;"
                                             "background:white;margin:0 5px")
                    ui.label("Transbordo").classes("text-sm")
                for linea in lineas_en_obras():
                    with ui.row().classes("items-center gap-2 no-wrap"):
                        ui.element("span").style(f"width:22px;height:0;border-top:4px dashed {linea['color']}")
                        ui.label(f"{linea['id'].replace('L', 'Línea ')} · en obras").classes("text-sm text-gray-500")

        self.mapa.on("map-click", self._al_hacer_clic)
        self.dibujar_obras()
        self.dibujar_red(atenuada=False)

    # ------------------------------------------------------------------ red
    def _coordenadas_linea(self, linea):
        return [(self.datos.estaciones[e]["lat"], self.datos.estaciones[e]["lon"])
                for e in self.datos.orden_linea(linea)]

    def dibujar_red(self, atenuada):
        """Pinta las tres líneas y sus estaciones. Atenuada = más transparente (bajo una ruta)."""
        with self.mapa:
            for capa in self.capas_red:
                self.mapa.remove_layer(capa)
            self.capas_red = []
            opacidad = 0.35 if atenuada else 0.95
            for linea, color in COLORES_LINEA.items():
                self.capas_red.append(self.mapa.generic_layer(
                    name="polyline",
                    args=[self._coordenadas_linea(linea),
                          {"color": color, "weight": 7, "opacity": opacidad, "lineCap": "round"}]))
            for est in self.datos.estaciones.values():
                color = COLORES_LINEA[est["lineas"][0]]
                self.capas_red.append(self.mapa.generic_layer(
                    name="circleMarker",
                    args=[(est["lat"], est["lon"]),
                          {"radius": 8 if est["transbordo"] else 5,
                           "color": "#1F2937" if est["transbordo"] else color,
                           "weight": 3 if est["transbordo"] else 2,
                           "fillColor": "#FFFFFF", "fillOpacity": 1,
                           "opacity": 0.5 if atenuada else 1}]))
        self._poner_nombres()

    def poner_fondo(self, clave):
        """Cambia el fondo del mapa entre el callejero (OpenStreetMap) y el satélite (Esri)."""
        with self.mapa:
            for capa in self.capas_fondo:
                self.mapa.remove_layer(capa)
            self.capas_fondo = [self.mapa.tile_layer(url_template=url, options={"maxZoom": 19})
                                for url in FONDOS[clave]["capas"]]
        self.credito.set_text(FONDOS[clave]["credito"])

    def dibujar_obras(self):
        """Líneas 4 y 6 en discontinua: están en construcción y NO se usan para calcular rutas.

        Las posiciones de sus estaciones son aproximadas (OpenStreetMap, ver LINEAS_EN_OBRAS en metro.py).
        """
        with self.mapa:
            for linea in lineas_en_obras():
                puntos = [(e["lat"], e["lon"]) for e in linea["estaciones"]]
                self.capas_obras.append(self.mapa.generic_layer(
                    name="polyline",
                    args=[puntos, {"color": linea["color"], "weight": 5, "opacity": 0.75,
                                   "dashArray": "10 10", "lineCap": "butt"}]))
                for e in linea["estaciones"]:
                    capa = self.mapa.generic_layer(
                        name="circleMarker",
                        args=[(e["lat"], e["lon"]),
                              {"radius": 4, "color": linea["color"], "weight": 2,
                               "fillColor": "#FFFFFF", "fillOpacity": 1, "opacity": 0.8}])
                    self.capas_obras.append((capa, e["nombre"], linea))

    def _poner_nombres_obras(self):
        for capa in self.capas_obras:
            if isinstance(capa, tuple):
                capa, nombre, linea = capa
                capa.run_method("bindTooltip", f"<b>{nombre}</b><br>{linea['nombre']}<br>"
                                               "<i>Temporalmente fuera de servicio (en obras)</i>")

    def _poner_nombres(self):
        """Muestra el nombre de cada estación al pasar el ratón (tooltip de Leaflet)."""
        circulos = self.capas_red[len(COLORES_LINEA):]
        for est, capa in zip(self.datos.estaciones.values(), circulos):
            capa.run_method("bindTooltip", f"<b>{est['nombre']}</b><br>{' · '.join(est['lineas'])}")

    async def preparar(self):
        """Cuando el mapa ya existe en el navegador: recalcula su tamaño y pone los nombres."""
        await self.mapa.initialized()
        self.mapa.run_map_method("invalidateSize")
        self._poner_nombres()
        self._poner_nombres_obras()

    # ---------------------------------------------------------------- clics
    def _al_hacer_clic(self, evento):
        lat = evento.args["latlng"]["lat"]
        lon = evento.args["latlng"]["lng"]
        mas_cercana = min(self.datos.estaciones.values(),
                          key=lambda e: haversine_km(lat, lon, e["lat"], e["lon"]))
        if haversine_km(lat, lon, mas_cercana["lat"], mas_cercana["lon"]) <= DISTANCIA_MAX_CLIC_KM:
            self.al_elegir_estacion(mas_cercana["id"])

    # ----------------------------------------------------------------- ruta
    def borrar_ruta(self):
        with self.mapa:
            for capa in self.capas_ruta:
                self.mapa.remove_layer(capa)
        self.capas_ruta = []

    def mostrar_ruta(self, resultado):
        """Resalta la ruta: polilínea gruesa por tramo de línea, origen, destino y zoom."""
        self.borrar_ruta()
        self.dibujar_red(atenuada=True)
        est = self.datos.estaciones
        colores = {"subir": "#16A34A", "bajar": "#DC2626", "transbordo": "#1F2937"}
        with self.mapa:
            for seg in resultado["segmentos"]:
                puntos = [(est[e]["lat"], est[e]["lon"]) for e in seg["estaciones"]]
                # borde oscuro debajo + color de la línea encima = efecto "resaltado"
                self.capas_ruta.append(self.mapa.generic_layer(
                    name="polyline", args=[puntos, {"color": "#0F172A", "weight": 15, "opacity": 0.8}]))
                self.capas_ruta.append(self.mapa.generic_layer(
                    name="polyline", args=[puntos, {"color": seg["color"], "weight": 9, "opacity": 1}]))
            for paso in resultado["pasos"]:
                if paso["accion"] == "pasar":
                    continue
                capa = self.mapa.generic_layer(
                    name="circleMarker",
                    args=[(paso["lat"], paso["lon"]),
                          {"radius": 11, "color": "#FFFFFF", "weight": 3,
                           "fillColor": colores[paso["accion"]], "fillOpacity": 1}])
                capa.run_method("bindTooltip", paso["nombre"],
                                {"permanent": True, "direction": "top", "offset": [0, -10]})
                self.capas_ruta.append(capa)
        lats = [p["lat"] for p in resultado["pasos"]]
        lons = [p["lon"] for p in resultado["pasos"]]
        self.mapa.run_map_method("fitBounds", [[min(lats), min(lons)], [max(lats), max(lons)]],
                                 {"padding": [70, 70]})

    def quitar_resaltado(self):
        """Vuelve a la vista general de la red."""
        self.borrar_ruta()
        self.dibujar_red(atenuada=False)
        self.mapa.set_center(CENTRO_MONTERREY)
        self.mapa.set_zoom(ZOOM_INICIAL)


# ========================================================================================
# 3. BUSCADOR
# ========================================================================================
# Panel de búsqueda: origen, destino y condiciones del viaje.

# Monterrey está en UTC-6 todo el año (México no aplica horario de verano desde 2022)
HUSO_MONTERREY = timezone(timedelta(hours=-6))


def hora_actual_monterrey():
    return datetime.now(HUSO_MONTERREY).strftime("%H:%M")


def opciones_estaciones():
    """Diccionario id → etiqueta, ordenado por línea y en el orden real de las estaciones."""
    datos = cargar_datos()
    opciones = {}
    for linea in ("L1", "L2", "L3"):
        for est_id in datos.orden_linea(linea):
            if est_id in opciones:
                continue
            est = datos.estaciones[est_id]
            emojis = "".join(EMOJI_LINEA[l] for l in est["lineas"])
            alias = f" ({', '.join(est['alias'])})" if est["alias"] and linea == "L1" else ""
            opciones[est_id] = f"{emojis}  {est['nombre']}{alias}"
    return opciones


class PanelViaje:
    """Controles del viaje. Guarda los valores elegidos en atributos normales."""

    def __init__(self, al_calcular):
        datos = cargar_datos()
        opciones = opciones_estaciones()
        climas = {clave: f"{EMOJI_CLIMA.get(clave, '')}  {c['nombre']}"
                  for clave, c in datos.factores["clima"].items()}
        self.siguiente_clic_es_origen = True

        with ui.card().classes("tarjeta w-full gap-4 p-5"):
            with ui.column().classes("gap-0"):
                ui.label("¿A dónde vas?").classes("text-2xl font-extrabold text-slate-900")
                ui.label("Elige las estaciones o tócalas en el mapa.").classes("text-sm text-slate-500")

            with ui.row().classes("w-full items-center no-wrap gap-2"):
                with ui.column().classes("grow gap-2"):
                    self.origen = ui.select(opciones, label="Desde", with_input=True, value="talleres") \
                        .classes("w-full").props('outlined rounded dense options-dense')
                    self.origen.add_slot("prepend", '<q-icon name="trip_origin" color="green-7" />')
                    self.destino = ui.select(opciones, label="Hasta", with_input=True,
                                             value="hospital_metropolitano") \
                        .classes("w-full").props('outlined rounded dense options-dense')
                    self.destino.add_slot("prepend", '<q-icon name="place" color="red-7" />')
                ui.button(icon="swap_vert", on_click=self.intercambiar) \
                    .props("round unelevated color=grey-2 text-color=grey-9").tooltip("Intercambiar")

            self.modo = ui.toggle({"salida": "Salir a las", "llegada": "Llegar a las"}, value="salida") \
                .props("spread rounded unelevated no-caps dense toggle-color=grey-9 color=grey-2 "
                       "text-color=grey-9").classes("w-full")
            with ui.row().classes("w-full no-wrap gap-2 items-center"):
                self.hora = ui.input("Hora (si la dejas vacía, ahora mismo)", value=hora_actual_monterrey()) \
                    .props("type=time outlined rounded dense clearable").classes("grow")
                ui.button("Ahora", on_click=lambda: self.hora.set_value(hora_actual_monterrey())) \
                    .props("flat dense no-caps color=grey-8")
            self.dia = ui.toggle({"laborable": "Entre semana", "fin_de_semana": "Fin de semana / festivo"},
                                 value="laborable").props("spread rounded unelevated no-caps toggle-color=grey-9 "
                                                          "color=grey-2 text-color=grey-9").classes("w-full")
            self.clima = ui.select(climas, value="despejado", label="¿Qué tiempo hace?") \
                .props("outlined rounded dense").classes("w-full")

            with ui.column().classes("gap-0 w-full"):
                self.evento = ui.switch("Hay un evento (concierto, partido, feria…)").props("color=amber-8")
                self.min_transbordos = ui.switch("Prefiero cambiar de línea lo menos posible").props("color=green-8")
                self.accesible = ui.switch("Necesito ruta accesible ♿").props("color=blue-8")

            ui.button("Buscar ruta", icon="directions_subway", on_click=al_calcular) \
                .props("unelevated size=lg no-caps").classes("w-full boton-principal py-1")

    def intercambiar(self):
        self.origen.value, self.destino.value = self.destino.value, self.origen.value

    def poner_viaje(self, origen, destino):
        self.origen.value, self.destino.value = origen, destino

    def elegir_desde_mapa(self, estacion_id):
        """Un clic en el mapa rellena el origen y el siguiente el destino."""
        if self.siguiente_clic_es_origen:
            self.origen.value = estacion_id
            ui.notify(f"Origen: {cargar_datos().estaciones[estacion_id]['nombre']}", position="top",
                      type="positive", timeout=1500)
        else:
            self.destino.value = estacion_id
            ui.notify(f"Destino: {cargar_datos().estaciones[estacion_id]['nombre']}", position="top",
                      type="info", timeout=1500)
        self.siguiente_clic_es_origen = not self.siguiente_clic_es_origen

    def parametros(self):
        """Valores actuales del panel, con los nombres que espera calcular_ruta()."""
        return {
            "origen": self.origen.value,
            "destino": self.destino.value,
            "modo": self.modo.value,
            "hora": self.hora.value or hora_actual_monterrey(),
            "dia": self.dia.value,
            "clima": self.clima.value,
            "evento_masivo": self.evento.value,
            "minimizar_transbordos": self.min_transbordos.value,
            "accesible": self.accesible.value,
        }


# ========================================================================================
# 4. RESULTADO
# ========================================================================================
# Tarjetas de la columna izquierda: pantalla de bienvenida y resultado del viaje.

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
        with ui.row().classes("w-full items-start no-wrap gap-2 rounded-xl bg-slate-50 "
                              "border border-slate-200 text-slate-700 p-3"):
            ui.icon("construction").classes("text-orange-600 text-lg")
            ui.label("Las Líneas 4 y 6 están en obras y temporalmente fuera de servicio. Las verás en "
                     "el mapa en discontinua, pero todavía no se usan para calcular viajes.") \
                .classes("text-sm")
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
    hora = hora_mas(r["hora_salida"], seg["minuto_inicio"])
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


# ========================================================================================
# 5. PÁGINA
# ========================================================================================
# Página principal: cabecera, buscador + resultado a la izquierda y mapa a la derecha.

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
        parametros = panel.parametros()
        modo = parametros.pop("modo")
        hora = parametros.pop("hora")
        if modo == "llegada":
            r = calcular_ruta_llegando_a(hora_llegada=hora, **parametros)
        else:
            r = calcular_ruta(hora=hora, **parametros)
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


# ========================================================================================
# 6. ARRANQUE
# ========================================================================================
if __name__ in {"__main__", "__mp_main__"}:
    en_servidor = "PORT" in os.environ
    ui.run(
        title="Metrorrey · Ruta más rápida",
        host="0.0.0.0" if en_servidor else "127.0.0.1",
        port=int(os.environ.get("PORT", 8080)),
        favicon="🚇",
        reload=False,
        show=not en_servidor,      # en tu ordenador abre el navegador solo
        language="es",
    )
