"""Panel de búsqueda: origen, destino y condiciones del viaje."""

from datetime import datetime, timedelta, timezone

from nicegui import ui

from interfaz.estilos import EMOJI_CLIMA, EMOJI_LINEA
from metro.datos import cargar_datos

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

            with ui.row().classes("w-full no-wrap gap-2 items-center"):
                self.hora = ui.input("Salida", value=hora_actual_monterrey()) \
                    .props("type=time outlined rounded dense").classes("grow")
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
            "hora": self.hora.value or hora_actual_monterrey(),
            "dia": self.dia.value,
            "clima": self.clima.value,
            "evento_masivo": self.evento.value,
            "minimizar_transbordos": self.min_transbordos.value,
            "accesible": self.accesible.value,
        }
