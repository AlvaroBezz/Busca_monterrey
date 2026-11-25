"""calcular_ruta(): el único punto de unión entre el algoritmo y la interfaz.

Recibe lo que el usuario elige en pantalla y devuelve un diccionario con todo lo
necesario para pintar el resultado: tiempo, itinerario, desglose, traza de A*...
"""

from functools import lru_cache

from metro.astar import FIN, INICIO, a_estrella, construir_problema
from metro.coste import Escenario, en_horario_de_servicio, franja_de, minutos_del_dia
from metro.datos import COLORES_LINEA, cargar_datos
from metro.grafo import construir_grafo


@lru_cache(maxsize=1)
def grafo_red():
    """El grafo se construye una sola vez al arrancar."""
    return construir_grafo(cargar_datos())


def _direccion(datos, linea, desde_id, hacia_id):
    """Nombre de la cabecera hacia la que avanza el tren (sentido de la marcha)."""
    orden = datos.orden_linea(linea)
    cabecera = orden[-1] if orden.index(hacia_id) > orden.index(desde_id) else orden[0]
    return datos.estaciones[cabecera]["nombre"]


def _hora_mas(hora, minutos):
    """'08:15' + 23.4 min → '08:38' (da la vuelta a medianoche)."""
    total = (minutos_del_dia(hora) + round(minutos)) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def _segmentos(datos, grafo, nodos, minutos):
    """Agrupa el camino en trayectos dentro de una misma línea (para el itinerario)."""
    segmentos = []
    for i, nodo in enumerate(nodos):
        linea = grafo.nodes[nodo]["linea"]
        estacion = grafo.nodes[nodo]["estacion_id"]
        if not segmentos or segmentos[-1]["linea"] != linea:
            segmentos.append({"linea": linea, "color": COLORES_LINEA[linea],
                              "estaciones": [], "minuto_inicio": minutos[i]})
        segmentos[-1]["estaciones"].append(estacion)
        segmentos[-1]["minuto_fin"] = minutos[i]
    for s in segmentos:
        s["desde"] = s["estaciones"][0]
        s["hasta"] = s["estaciones"][-1]
        s["num_paradas"] = len(s["estaciones"]) - 1
        s["direccion"] = (_direccion(datos, s["linea"], s["desde"], s["hasta"])
                          if s["num_paradas"] > 0 else "")
    # Un segmento de una sola estación es un transbordo en el origen o destino: se quita
    return [s for s in segmentos if s["num_paradas"] > 0] or segmentos[:1]


def calcular_ruta(origen, destino, hora="08:15", dia="laborable", clima="despejado",
                  evento_masivo=False, minimizar_transbordos=False, accesible=False):
    """Calcula la ruta óptima con A* entre dos estaciones (ids de data/estaciones.json)."""
    datos = cargar_datos()
    grafo = grafo_red()
    escenario = Escenario(hora, dia, clima, evento_masivo, minimizar_transbordos, accesible)
    franja = franja_de(escenario, datos.factores)
    clima_info = datos.factores["clima"][clima]

    avisos = []
    if not en_horario_de_servicio(hora, datos.factores):
        avisos.append("A esa hora el metro está cerrado (abre de 05:00 a 24:00). "
                      "Te mostramos el trayecto con el primer servicio de la mañana.")
    if clima_info["riesgo_suspension"] in ("Alta", "Muy alta"):
        avisos.append(f"{clima_info['nombre']}: es posible que el servicio se suspenda en algunos "
                      "tramos. Consulta los avisos oficiales de Metrorrey antes de salir.")

    if origen == destino:
        est = datos.estaciones[origen]
        return {"ok": False, "motivo": "El origen y el destino son la misma estación.",
                "origen": est["nombre"], "destino": est["nombre"], "avisos": avisos}

    problema = construir_problema(grafo, datos, origen, destino, escenario)
    resultado = a_estrella(problema)
    dijkstra = a_estrella(problema, usar_heuristica=False)
    if not resultado.encontrado:
        return {"ok": False, "motivo": resultado.motivo, "avisos": avisos}

    # Recorremos el camino sumando el tiempo REAL (sin las penalizaciones, que solo
    # sirven para que A* prefiera unas rutas a otras) y el desglose por conceptos.
    desglose = {"marcha": 0.0, "paradas": 0.0, "esperas": 0.0, "transbordos": 0.0,
                "penalizaciones": 0.0}
    distancia_m = 0
    nodos = [n for n in resultado.camino if n not in (INICIO, FIN)]
    minutos = []
    tiempo = 0.0
    camino = resultado.camino
    for a, b in zip(camino, camino[1:]):
        partes = problema.edges[a, b]["desglose"]
        desglose["marcha"] += partes.get("marcha", 0)
        desglose["paradas"] += partes.get("parada", 0)
        desglose["esperas"] += partes.get("espera", 0)
        desglose["transbordos"] += partes.get("pasillo", 0) + partes.get("saturacion", 0)
        desglose["penalizaciones"] += partes.get("penalizacion", 0)
        tiempo += sum(partes.values()) - partes.get("penalizacion", 0)
        if b != FIN:
            minutos.append(tiempo)
        if a in grafo and b in grafo and grafo.edges[a, b]["tipo_arista"] == "tramo":
            distancia_m += grafo.edges[a, b]["distancia_m"]

    # Pasos estación a estación, con la acción en cada una
    pasos = []
    for i, nodo in enumerate(nodos):
        d = grafo.nodes[nodo]
        if i == 0:
            accion = "subir"
        elif i == len(nodos) - 1:
            accion = "bajar"
        elif grafo.nodes[nodos[i + 1]]["estacion_id"] == d["estacion_id"]:
            accion = "transbordo"
        elif grafo.nodes[nodos[i - 1]]["estacion_id"] == d["estacion_id"]:
            continue  # segundo nodo del transbordo: ya se contó
        else:
            accion = "pasar"
        est = datos.estaciones[d["estacion_id"]]
        pasos.append({"estacion": est["id"], "nombre": est["nombre"], "linea": d["linea"],
                      "minuto": round(minutos[i], 1), "accion": accion,
                      "lat": est["lat"], "lon": est["lon"]})

    segmentos = _segmentos(datos, grafo, nodos, minutos)
    num_transbordos = len(segmentos) - 1

    itinerario = []
    for i, s in enumerate(segmentos):
        desde = datos.estaciones[s["desde"]]["nombre"]
        hasta = datos.estaciones[s["hasta"]]["nombre"]
        paradas = f"{s['num_paradas']} parada{'s' if s['num_paradas'] != 1 else ''}"
        if i == 0:
            texto = f"Sube a la {s['linea']} en {desde} dirección {s['direccion']}"
        else:
            texto = f"Transbordo en {desde} a la {s['linea']} dirección {s['direccion']}"
        itinerario.append(f"{texto} ({paradas} hasta {hasta})")
    itinerario.append(f"Baja en {datos.estaciones[destino]['nombre']}")

    # Avisos de accesibilidad
    no_accesibles = [p["nombre"] for p in pasos
                     if p["accion"] in ("subir", "bajar", "transbordo")
                     and not datos.estaciones[p["estacion"]]["accesible"]]
    if accesible and no_accesibles:
        avisos.append("Parte del trayecto no está adaptado para movilidad reducida: las Líneas 1 y 2 "
                      f"no tienen accesibilidad completa ({', '.join(dict.fromkeys(no_accesibles))}).")
    if minutos_del_dia(hora) + tiempo >= 24 * 60 and en_horario_de_servicio(hora, datos.factores):
        avisos.append("Cuidado: llegarías después del cierre del metro (24:00).")

    return {
        "ok": True,
        "origen": datos.estaciones[origen]["nombre"],
        "destino": datos.estaciones[destino]["nombre"],
        "tiempo_total_min": round(tiempo, 1),
        "coste_astar_min": round(resultado.coste_total_min, 2),
        "modo": "salida",
        "hora_salida": hora,
        "hora_llegada": _hora_mas(hora, tiempo),
        "num_transbordos": num_transbordos,
        "distancia_km": round(distancia_m / 1000, 2),
        "franja": franja["nombre"],
        "clima": clima_info["nombre"],
        "pasos": pasos,
        "segmentos": segmentos,
        "itinerario_texto": itinerario,
        "desglose": {**{k: round(v, 2) for k, v in desglose.items()},
                     "en_tren": round(desglose["marcha"] + desglose["paradas"], 2)},
        "camino_nodos": resultado.camino,
        "traza_astar": resultado.traza,
        "nodos_expandidos": resultado.nodos_expandidos,
        "nodos_expandidos_dijkstra": dijkstra.nodos_expandidos,
        "avisos": avisos,
    }


def calcular_ruta_llegando_a(origen, destino, hora_llegada, **opciones):
    """Como calcular_ruta(), pero el usuario dice a qué hora quiere LLEGAR.

    El tiempo de viaje depende de la hora de salida (franja horaria), así que se
    estima la salida y se ajusta unas pocas veces hasta que la llegada cuadra:
        salida = llegada deseada − duración del viaje saliendo a esa hora
    """
    salida = _hora_mas(hora_llegada, -30)          # primera suposición: media hora antes
    resultado = calcular_ruta(origen, destino, hora=salida, **opciones)
    for _ in range(4):
        if not resultado.get("ok"):
            return resultado
        nueva_salida = _hora_mas(hora_llegada, -resultado["tiempo_total_min"])
        if nueva_salida == salida:
            break
        salida = nueva_salida
        resultado = calcular_ruta(origen, destino, hora=salida, **opciones)
    resultado["modo"] = "llegada"
    resultado["hora_llegada_deseada"] = hora_llegada
    return resultado
