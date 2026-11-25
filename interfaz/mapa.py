"""Mapa de Monterrey con las tres líneas, las estaciones y la ruta calculada (ui.leaflet)."""

from nicegui import ui

from metro.datos import COLORES_LINEA, NOMBRES_LINEA, cargar_datos
from metro.heuristica import haversine_km

CENTRO_MONTERREY = (25.712, -100.305)
ZOOM_INICIAL = 13
DISTANCIA_MAX_CLIC_KM = 0.4   # un clic elige la estación más cercana a menos de 400 m

# Mapa base de CARTO (estilo "Voyager", con calles y nombres) sobre datos de OpenStreetMap
TESELAS = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png"
ATRIBUCION = ('&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> '
              '&copy; <a href="https://carto.com/">CARTO</a>')


class MapaMetro:
    """Envuelve un ui.leaflet y sabe pintar la red y la ruta."""

    def __init__(self, al_elegir_estacion):
        """al_elegir_estacion(id_estacion) se llama cuando el usuario hace clic cerca de una estación."""
        self.datos = cargar_datos()
        self.al_elegir_estacion = al_elegir_estacion
        self.capas_red = []        # líneas y estaciones de la red
        self.capas_ruta = []       # ruta resaltada y marcadores de origen/destino

        with ui.element("div").style("position: relative; width: 100%; height: 100%"):
            self.mapa = ui.leaflet(center=CENTRO_MONTERREY, zoom=ZOOM_INICIAL,
                                   options={"zoomControl": True, "attributionControl": True}) \
                .classes("mapa-metro")
            # Sustituimos la capa de teselas por defecto por una más clara y moderna
            for capa in list(self.mapa.layers):
                self.mapa.remove_layer(capa)
            self.mapa.tile_layer(url_template=TESELAS,
                                 options={"attribution": ATRIBUCION, "maxZoom": 19,
                                          "subdomains": "abcd"})
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

        self.mapa.on("map-click", self._al_hacer_clic)
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
