"""Panel de la izquierda: origen, destino y condiciones del viaje."""

from datetime import datetime

from nicegui import ui

from interfaz.estilos import EMOJI_LINEA
from metro.datos import cargar_datos


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
            alias = f" / {', '.join(est['alias'])}" if est["alias"] and linea == "L1" else ""
            opciones[est_id] = f"{emojis} {est['nombre']}{alias} · {' · '.join(est['lineas'])}"
    return opciones


class PanelViaje:
    """Controles del viaje. Guarda los valores elegidos en atributos normales."""

    def __init__(self, al_calcular):
        datos = cargar_datos()
        opciones = opciones_estaciones()
        climas = {clave: c["nombre"] for clave, c in datos.factores["clima"].items()}
        self.siguiente_clic_es_origen = True

        with ui.card().classes("tarjeta w-full gap-3"):
            ui.label("Planifica tu viaje").classes("text-lg font-bold")
            with ui.row().classes("w-full items-center no-wrap gap-2"):
                with ui.column().classes("grow gap-2"):
                    self.origen = ui.select(opciones, label="Origen", with_input=True,
                                            value="talleres").classes("w-full").props("outlined dense")
                    self.destino = ui.select(opciones, label="Destino", with_input=True,
                                             value="hospital_metropolitano").classes("w-full").props("outlined dense")
                ui.button(icon="swap_vert", on_click=self.intercambiar) \
                    .props("round flat").tooltip("Intercambiar origen y destino")
            ui.label("Consejo: también puedes hacer clic en una estación del mapa "
                     "(primer clic = origen, segundo = destino).").classes("text-xs text-gray-500")

            with ui.row().classes("w-full no-wrap gap-2"):
                self.hora = ui.input("Hora de salida", value=datetime.now().strftime("%H:%M")) \
                    .props("type=time outlined dense").classes("w-1/2")
                self.dia = ui.select({"laborable": "Laborable", "fin_de_semana": "Fin de semana / festivo"},
                                     value="laborable", label="Día").props("outlined dense").classes("w-1/2")
            self.clima = ui.select(climas, value="despejado", label="Meteorología") \
                .props("outlined dense").classes("w-full")

            with ui.column().classes("gap-0"):
                self.evento = ui.switch("Evento masivo (Fundidora, Arena, estadios)")
                self.min_transbordos = ui.switch("Minimizar transbordos")
                self.accesible = ui.switch("Ruta accesible (movilidad reducida)")

            ui.button("Calcular ruta", icon="route", on_click=al_calcular) \
                .props("unelevated size=lg").classes("w-full rounded-xl")

    def intercambiar(self):
        self.origen.value, self.destino.value = self.destino.value, self.origen.value

    def elegir_desde_mapa(self, estacion_id):
        """Un clic en el mapa rellena el origen y el siguiente el destino."""
        if self.siguiente_clic_es_origen:
            self.origen.value = estacion_id
        else:
            self.destino.value = estacion_id
        self.siguiente_clic_es_origen = not self.siguiente_clic_es_origen

    def parametros(self):
        """Valores actuales del panel, con los nombres que espera calcular_ruta()."""
        return {
            "origen": self.origen.value,
            "destino": self.destino.value,
            "hora": self.hora.value or "08:15",
            "dia": self.dia.value,
            "clima": self.clima.value,
            "evento_masivo": self.evento.value,
            "minimizar_transbordos": self.min_transbordos.value,
            "accesible": self.accesible.value,
        }
