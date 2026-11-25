"""Mapa de Monterrey con las tres líneas, las estaciones y la ruta calculada (ui.leaflet)."""

from nicegui import ui

from metro.datos import COLORES_LINEA, cargar_datos
from metro.heuristica import haversine_km

CENTRO_MONTERREY = (25.712, -100.305)
DISTANCIA_MAX_CLIC_KM = 0.4   # un clic elige la estación más cercana a menos de 400 m

TESELAS_CLARAS = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
ATRIBUCION = ('&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors '
              '&copy; <a href="https://carto.com/">CARTO</a>')


class MapaMetro:
    """Envuelve un ui.leaflet y sabe pintar la red, la ruta y la animación de A*."""

    def __init__(self, al_elegir_estacion):
        """al_elegir_estacion(id_estacion) se llama cuando el usuario hace clic cerca de una estación."""
        self.datos = cargar_datos()
        self.al_elegir_estacion = al_elegir_estacion
        self.capas_red = []        # líneas y estaciones de la red
        self.capas_ruta = []       # ruta resaltada y marcadores de origen/destino
        self.capas_animacion = []  # nodos expandidos durante la animación
        self.temporizador = None

        self.mapa = ui.leaflet(center=CENTRO_MONTERREY, zoom=13).classes("w-full h-full")
        self.mapa.clear_layers()   # quita las teselas por defecto para usar unas más limpias
        self.mapa.tile_layer(url_template=TESELAS_CLARAS,
                             options={"attribution": ATRIBUCION, "maxZoom": 19})
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
            opacidad = 0.3 if atenuada else 0.95
            for linea, color in COLORES_LINEA.items():
                self.capas_red.append(self.mapa.generic_layer(
                    name="polyline",
                    args=[self._coordenadas_linea(linea),
                          {"color": color, "weight": 7, "opacity": opacidad}]))
            for est in self.datos.estaciones.values():
                color = COLORES_LINEA[est["lineas"][0]]
                self.capas_red.append(self.mapa.generic_layer(
                    name="circleMarker",
                    args=[(est["lat"], est["lon"]),
                          {"radius": 8 if est["transbordo"] else 5,
                           "color": "#1F2937" if est["transbordo"] else color,
                           "weight": 3 if est["transbordo"] else 2,
                           "fillColor": "#FFFFFF", "fillOpacity": 1,
                           "opacity": 0.4 if atenuada else 1}]))
        self._poner_nombres()

    def _poner_nombres(self):
        """Muestra el nombre de cada estación al pasar el ratón (tooltip de Leaflet)."""
        estaciones = list(self.datos.estaciones.values())
        circulos = self.capas_red[len(COLORES_LINEA):]
        for est, capa in zip(estaciones, circulos):
            lineas = " · ".join(est["lineas"])
            capa.run_method("bindTooltip", f"{est['nombre']} ({lineas})")

    async def preparar(self):
        """Espera a que el mapa exista en el navegador y vuelve a poner los tooltips."""
        await self.mapa.initialized()
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
        self.parar_animacion()
        with self.mapa:
            for capa in self.capas_ruta:
                self.mapa.remove_layer(capa)
        self.capas_ruta = []

    def mostrar_ruta(self, resultado):
        """Resalta la ruta: polilínea gruesa por tramo de línea, origen, destino y zoom."""
        self.borrar_ruta()
        self.dibujar_red(atenuada=True)
        est = self.datos.estaciones
        with self.mapa:
            for seg in resultado["segmentos"]:
                puntos = [(est[e]["lat"], est[e]["lon"]) for e in seg["estaciones"]]
                # borde oscuro debajo + color de la línea encima = efecto "resaltado"
                self.capas_ruta.append(self.mapa.generic_layer(
                    name="polyline", args=[puntos, {"color": "#111827", "weight": 14, "opacity": 0.85}]))
                self.capas_ruta.append(self.mapa.generic_layer(
                    name="polyline", args=[puntos, {"color": seg["color"], "weight": 9, "opacity": 1}]))
            for paso in resultado["pasos"]:
                if paso["accion"] == "pasar":
                    continue
                colores = {"subir": "#16A34A", "bajar": "#DC2626", "transbordo": "#111827"}
                self.capas_ruta.append(self.mapa.generic_layer(
                    name="circleMarker",
                    args=[(paso["lat"], paso["lon"]),
                          {"radius": 11, "color": "#FFFFFF", "weight": 3,
                           "fillColor": colores[paso["accion"]], "fillOpacity": 1}]))
                self.capas_ruta[-1].run_method("bindTooltip", paso["nombre"],
                                               {"permanent": True, "direction": "top", "offset": [0, -10]})
        lats = [p["lat"] for p in resultado["pasos"]]
        lons = [p["lon"] for p in resultado["pasos"]]
        self.mapa.run_map_method("fitBounds", [[min(lats), min(lons)], [max(lats), max(lons)]],
                                 {"padding": [60, 60]})

    def quitar_resaltado(self):
        """Vuelve a la vista general de la red."""
        self.borrar_ruta()
        self.dibujar_red(atenuada=False)
        self.mapa.set_center(CENTRO_MONTERREY)
        self.mapa.set_zoom(13)

    # ----------------------------------------------------------- animación
    def parar_animacion(self):
        if self.temporizador:
            self.temporizador.cancel()
            self.temporizador = None
        with self.mapa:
            for capa in self.capas_animacion:
                self.mapa.remove_layer(capa)
        self.capas_animacion = []

    def animar_traza(self, traza, al_avanzar=None):
        """Colorea uno a uno los nodos que A* va expandiendo (útil para la defensa)."""
        self.parar_animacion()
        pasos = [t for t in traza if "@" in t["nodo"]]   # se saltan INICIO y FIN
        indice = {"i": 0}

        def siguiente():
            if indice["i"] >= len(pasos):
                self.temporizador.cancel()
                return
            paso = pasos[indice["i"]]
            est = self.datos.estaciones[paso["nodo"].split("@")[0]]
            with self.mapa:
                capa = self.mapa.generic_layer(
                    name="circleMarker",
                    args=[(est["lat"], est["lon"]),
                          {"radius": 14, "color": "#7C3AED", "weight": 2,
                           "fillColor": "#A78BFA", "fillOpacity": 0.55}])
                capa.run_method("bindTooltip",
                                f"Paso {paso['paso']}: {est['nombre']} · f = {paso['f']:.1f} min")
                self.capas_animacion.append(capa)
            if al_avanzar:
                al_avanzar(paso)
            indice["i"] += 1

        with self.mapa:
            self.temporizador = ui.timer(0.35, siguiente)
