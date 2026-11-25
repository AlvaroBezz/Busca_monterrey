"""Todo el cálculo de rutas del Metro de Monterrey en un solo archivo.

Secciones, en el orden en que se usan:
    1. DATOS       cómo se guardan los datos de la red (los valores están en la sección 7)
    2. GRAFO       red de Metrorrey con NetworkX (un nodo por estación y línea)
    3. COSTE g(n)  minutos que cuesta cada arista según hora, día, clima...
    4. HEURÍSTICA h(n)  línea recta hasta el destino / 80 km/h
    5. A*          algoritmo programado a mano (sin nx.astar_path)
    6. RUTA        calcular_ruta() y calcular_ruta_llegando_a(): lo que usa la web
    7. DATOS DE LA RED  estaciones, tramos y parámetros sacados del Excel del grupo

La interfaz (main.py) solo llama a calcular_ruta(), calcular_ruta_llegando_a() y cargar_datos().
"""

import heapq
import itertools
import math
from dataclasses import dataclass, field
from functools import lru_cache

import networkx as nx


# ========================================================================================
# 1. DATOS
# ========================================================================================
# Estructura de los datos de la red. Los valores (estaciones, tramos, factores) están al final, en la sección 7.


# Colores oficiales de las líneas (se usan en el mapa y en la interfaz)
COLORES_LINEA = {"L1": "#F2C200", "L2": "#2E9E44", "L3": "#D7262E"}
NOMBRES_LINEA = {"L1": "Línea 1 (amarilla)", "L2": "Línea 2 (verde)", "L3": "Línea 3 (roja)"}


@dataclass
class DatosMetro:
    """Todo lo que sabemos de la red.

    estaciones: diccionario id → datos de la estación (nombre, lat, lon, líneas...)
    tramos:     lista de tramos entre estaciones consecutivas, en el orden de cada línea
    factores:   parámetros de g(n) y h(n) (franjas horarias, clima, transbordos...)
    """
    estaciones: dict
    tramos: list
    factores: dict

    def orden_linea(self, linea):
        """Lista de ids de estación de una línea, de una cabecera a la otra."""
        tramos_linea = [t for t in self.tramos if t["linea"] == linea]
        orden = [tramos_linea[0]["desde"]]
        for t in tramos_linea:
            orden.append(t["hasta"])
        return orden


def lineas_en_obras():
    """Líneas 4 y 6, que a noviembre de 2026 siguen en construcción.

    Solo se dibujan en el mapa con aviso: NO entran en el grafo ni en el cálculo de rutas.
    Las posiciones de sus estaciones son aproximadas (OpenStreetMap); ver la sección 7.
    """
    return LINEAS_EN_OBRAS


@lru_cache(maxsize=1)
def cargar_datos():
    """Prepara los datos de la sección 7 una sola vez y devuelve un DatosMetro."""
    estaciones = {e["id"]: e for e in ESTACIONES}
    return DatosMetro(
        estaciones=estaciones,
        tramos=TRAMOS,
        factores=FACTORES,
    )


# ========================================================================================
# 2. GRAFO
# ========================================================================================
# Construcción del grafo de la red de Metrorrey con NetworkX.
#
# Decisión de diseño (apartado 3.1 de la memoria): cada estación se representa con
# UN NODO POR LÍNEA, con id "estacion@linea" (por ejemplo "cuauhtemoc@L1").
# - Las estaciones normales tienen un único nodo (p. ej. "talleres@L1").
# - Las tres estaciones de transbordo tienen dos nodos, unidos por una arista de
#   transbordo. Así cambiar de línea es una arista más con su propio coste.
#
# Resultado: 38 estaciones + 3 desdoblamientos = 41 nodos;
# 38 aristas de tramo + 3 de transbordo = 41 aristas.
# NetworkX solo guarda la estructura: el A* está programado a mano en la sección 5.

def id_nodo(estacion_id, linea):
    """'cuauhtemoc', 'L1' → 'cuauhtemoc@L1'."""
    return f"{estacion_id}@{linea}"


def construir_grafo(datos):
    """Devuelve un nx.Graph (no dirigido) con estaciones, tramos y transbordos."""
    grafo = nx.Graph()

    # 1) Nodos: uno por cada (estación, línea)
    for est in datos.estaciones.values():
        for linea in est["lineas"]:
            grafo.add_node(
                id_nodo(est["id"], linea),
                estacion_id=est["id"],
                nombre=est["nombre"],
                linea=linea,
                lat=est["lat"],
                lon=est["lon"],
                tipo=est["tipo_por_linea"][linea],
                accesible=est["accesible"],
            )

    # 2) Aristas de tramo: estaciones consecutivas de la misma línea
    for t in datos.tramos:
        grafo.add_edge(
            id_nodo(t["desde"], t["linea"]),
            id_nodo(t["hasta"], t["linea"]),
            tipo_arista="tramo",
            linea=t["linea"],
            marcha_s=t["marcha_s"],
            distancia_m=t["distancia_m"],
            tipo_via=t["tipo"],
        )

    # 3) Aristas de transbordo: unen los nodos de una misma estación en líneas distintas
    for est in datos.estaciones.values():
        if len(est["lineas"]) > 1:
            linea_a, linea_b = est["lineas"]
            datos_transbordo = datos.factores["transbordos"][est["id"]]
            grafo.add_edge(
                id_nodo(est["id"], linea_a),
                id_nodo(est["id"], linea_b),
                tipo_arista="transbordo",
                estacion=est["id"],
                pasillo_min=datos_transbordo["pasillo_min"],
                saturacion_punta_min=datos_transbordo["saturacion_punta_min"],
            )
    return grafo


def nodos_de_estacion(grafo, estacion_id):
    """Todos los nodos de una estación (dos si es de transbordo, uno si no)."""
    return [n for n, d in grafo.nodes(data=True) if d["estacion_id"] == estacion_id]


# ========================================================================================
# 3. COSTE g(n)
# ========================================================================================
# Función de coste g(n): cuánto cuesta (en minutos) recorrer cada arista.
#
# g(n) = g(padre) + coste(padre, n)                       (apartado 3.2.A de la memoria)
#
# Coste de una arista de TRAMO u → v (tren que va de una estación a la siguiente):
#     marcha  = marcha_s × F_marcha_franja × F_marcha_clima[tipo de vía]
#     parada  = parada_s(v) × F_parada_franja × F_parada_clima      (0 si v es el destino)
#     coste   = (marcha + parada) / 60   → minutos
#
# Coste de una arista de TRANSBORDO (cambio de línea dentro de la misma estación):
#     coste = pasillo_min                         (caminar entre andenes)
#           + intervalo_min[línea nueva] / 2      (espera media al siguiente tren)
#           + saturacion_punta_min                (solo en hora punta o evento masivo)
#           + penalización por minimizar transbordos   (si el usuario lo pide)
#           + penalización no accesible                 (si pide ruta accesible y la estación no lo es)
#
# Al salir del origen se suma además la espera inicial = intervalo / 2 de la línea.
#
# Todos los parámetros están en FACTORES, sección 7 (sacados del Excel del grupo).

TIPOS_DIA = ("laborable", "fin_de_semana")


@dataclass
class Escenario:
    """Condiciones del viaje elegidas por el usuario en la interfaz."""
    hora: str = "08:15"                 # "HH:MM"
    dia: str = "laborable"              # "laborable" o "fin_de_semana"
    clima: str = "despejado"            # clave de factores["clima"]
    evento_masivo: bool = False
    minimizar_transbordos: bool = False
    accesible: bool = False


def minutos_del_dia(hora):
    """'08:15' → 495."""
    horas, minutos = hora.split(":")
    return int(horas) * 60 + int(minutos)


def en_horario_de_servicio(hora, factores):
    """True si a esa hora circula el metro (05:00–24:00)."""
    inicio = minutos_del_dia(factores["horario_servicio"]["inicio"])
    fin = minutos_del_dia(factores["horario_servicio"]["fin"])
    return inicio <= minutos_del_dia(hora) < fin


def franja_de(escenario, factores):
    """Devuelve la franja horaria que se aplica al escenario.

    Prioridad: evento masivo > fin de semana/festivo > franja según la hora.
    Fuera del horario de servicio (00:00–05:00) se usa 'Apertura', que es el
    primer servicio que saldría (la interfaz avisa al usuario).
    """
    por_clave = {f["clave"]: f for f in factores["franjas"]}
    if escenario.evento_masivo:
        return por_clave["evento_masivo"]
    if escenario.dia == "fin_de_semana":
        return por_clave["fin_de_semana"]
    minuto = minutos_del_dia(escenario.hora)
    for f in factores["franjas"]:
        if f["hora_inicio"] is None:
            continue
        if minutos_del_dia(f["hora_inicio"]) <= minuto < minutos_del_dia(f["hora_fin"]):
            return f
    return por_clave["apertura"]


def espera_inicial(linea, escenario, factores):
    """Minutos de espera media en el andén del origen: la mitad del intervalo."""
    return franja_de(escenario, factores)["intervalo_min"][linea] / 2


def desglose_arista(grafo, u, v, datos, escenario, destino_id):
    """Coste de ir de u a v, separado por conceptos (todo en minutos).

    Devuelve un dict con: marcha, parada, pasillo, espera, saturacion, penalizacion.
    La suma de todos los valores es el coste de la arista.
    """
    factores = datos.factores
    franja = franja_de(escenario, factores)
    clima = factores["clima"][escenario.clima]
    arista = grafo.edges[u, v]
    partes = {"marcha": 0.0, "parada": 0.0, "pasillo": 0.0, "espera": 0.0,
              "saturacion": 0.0, "penalizacion": 0.0}

    if arista["tipo_arista"] == "tramo":
        f_clima_marcha = clima[f"factor_marcha_{arista['tipo_via']}"]
        partes["marcha"] = arista["marcha_s"] * franja["factor_marcha"] * f_clima_marcha / 60
        estacion_llegada = grafo.nodes[v]["estacion_id"]
        if estacion_llegada != destino_id:
            parada_s = datos.estaciones[estacion_llegada]["parada_s"]
            partes["parada"] = parada_s * franja["factor_parada"] * clima["factor_parada"] / 60
    else:  # transbordo
        linea_nueva = grafo.nodes[v]["linea"]
        partes["pasillo"] = arista["pasillo_min"]
        partes["espera"] = franja["intervalo_min"][linea_nueva] / 2
        if franja["es_punta"]:
            partes["saturacion"] = arista["saturacion_punta_min"]
        if escenario.minimizar_transbordos:
            partes["penalizacion"] += factores["penalizacion_minimizar_transbordos_min"]
        if escenario.accesible and not datos.estaciones[arista["estacion"]]["accesible"]:
            partes["penalizacion"] += factores["penalizacion_no_accesible_min"]
    return partes


def coste_arista(grafo, u, v, datos, escenario, destino_id):
    """Coste total (minutos) de recorrer la arista u → v. Siempre ≥ 0."""
    return sum(desglose_arista(grafo, u, v, datos, escenario, destino_id).values())


# ========================================================================================
# 4. HEURÍSTICA h(n)
# ========================================================================================
# Función heurística h(n): estimación optimista del tiempo que falta hasta el destino.
#
#     h(n) = distancia_haversine(n, destino) / V_max          (en minutos)
#
# con V_max = 80 km/h (velocidad máxima de los trenes de Metrorrey; FACTORES en la sección 7).
#
# ¿Por qué es ADMISIBLE (h(n) ≤ h*(n), nunca sobreestima)?
#     1. La vía nunca es más corta que la línea recta entre dos puntos, así que la
#        distancia que de verdad recorre el tren es ≥ la distancia haversine.
#     2. El tren nunca va más rápido que V_max, así que tarda como mínimo
#        distancia / V_max en recorrerla.
#     3. Todo lo demás que suma g(n) (paradas, esperas, transbordos, penalizaciones)
#        es ≥ 0, y los factores de marcha por franja y clima son todos ≥ 1.
#     Por tanto el coste real que falta siempre es ≥ h(n).
#
# ¿Por qué es CONSISTENTE (h(u) ≤ coste(u, v) + h(v) para toda arista u → v)?
#     Por la desigualdad triangular: d(u, destino) ≤ d(u, v) + d(v, destino).
#     Dividiendo entre V_max: h(u) ≤ d(u, v)/V_max + h(v) ≤ coste(u, v) + h(v),
#     porque el tren tarda al menos d(u, v)/V_max en ir de u a v.
#     En un transbordo u y v están en la misma estación: d(u, v) = 0 y h(u) = h(v).
#     Que la heurística sea consistente garantiza que A* no tiene que reabrir nodos
#     ya cerrados y que el primer camino que llega al destino es el óptimo.
#
# Las pruebas (test_metro.py) comprueban la consistencia en TODAS las
# aristas, para todos los destinos, franjas horarias y climas.

RADIO_TIERRA_KM = 6371.0


def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia en km sobre la superficie de la Tierra entre dos puntos (lat, lon)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * RADIO_TIERRA_KM * math.asin(math.sqrt(a))


def h_minutos(lat, lon, lat_destino, lon_destino, v_max_kmh):
    """h = distancia en línea recta / velocidad máxima, en minutos."""
    return haversine_km(lat, lon, lat_destino, lon_destino) / v_max_kmh * 60


def heuristica(datos, estacion_id, destino_id):
    """h(n) para el nodo n de la estación estacion_id (no depende de la línea)."""
    origen = datos.estaciones[estacion_id]
    destino = datos.estaciones[destino_id]
    return h_minutos(origen["lat"], origen["lon"], destino["lat"], destino["lon"],
                     datos.factores["v_max_kmh"])


# ========================================================================================
# 5. A*
# ========================================================================================
# Algoritmo A* programado a mano (sin nx.astar_path ni nx.shortest_path).
#
# Se hace en dos pasos:
#
# 1. construir_problema(): a partir del grafo de la red y del escenario del usuario
#    crea un grafo DIRIGIDO con el coste de cada arista ya calculado con g (sección 3).
#    Es dirigido porque el coste no es simétrico: al llegar a una estación se suma su
#    parada (salvo si es el destino) y en un transbordo se espera al tren de la línea
#    a la que se cambia.
#    Como una estación de transbordo tiene dos nodos, se añaden dos nodos virtuales:
#      - INICIO, unido a cada nodo de la estación origen con coste = espera inicial
#        (intervalo / 2 de esa línea);
#      - FIN, al que se llega desde cada nodo de la estación destino con coste 0.
#    Así A* busca siempre de INICIO a FIN y elige solo la línea por la que salir.
#
# 2. a_estrella(): el algoritmo clásico, con
#      abiertos  = cola de prioridad (heapq) ordenada por f = g + h
#      cerrados  = conjunto de nodos ya expandidos
#      g, padre  = diccionarios con el mejor coste conocido y de dónde venimos
#    Guarda una TRAZA con cada expansión (nodo, g, h, f, tamaño de la frontera)
#    para enseñarla en la interfaz y explicarla en la defensa.
#    Con usar_heuristica=False, h = 0 y el algoritmo es exactamente Dijkstra.

INICIO = "INICIO"
FIN = "FIN"


@dataclass
class ResultadoAEstrella:
    """Lo que devuelve a_estrella()."""
    encontrado: bool
    camino: list = field(default_factory=list)       # nodos de INICIO a FIN
    g_camino: list = field(default_factory=list)     # g de cada nodo del camino
    coste_total_min: float = 0.0
    nodos_expandidos: int = 0
    traza: list = field(default_factory=list)
    motivo: str = ""


def construir_problema(grafo, datos, origen_id, destino_id, escenario):
    """Grafo dirigido con los costes de g ya calculados para este viaje concreto.

    Cada nodo guarda 'h' (la heurística hasta el destino) y cada arista guarda
    'peso' (minutos) y 'desglose' (las partes del coste).
    """
    problema = nx.DiGraph()

    for nodo, d in grafo.nodes(data=True):
        problema.add_node(nodo, **d, h=heuristica(datos, d["estacion_id"], destino_id))

    # Las aristas de la red se recorren en los dos sentidos, cada uno con su coste
    for u, v in grafo.edges():
        for a, b in ((u, v), (v, u)):
            partes = desglose_arista(grafo, a, b, datos, escenario, destino_id)
            problema.add_edge(a, b, peso=sum(partes.values()), desglose=partes)

    # Nodos virtuales de inicio y fin
    problema.add_node(INICIO, nombre="Inicio", h=heuristica(datos, origen_id, destino_id))
    problema.add_node(FIN, nombre="Fin", h=0.0)
    for nodo in nodos_de_estacion(grafo, origen_id):
        espera = espera_inicial(grafo.nodes[nodo]["linea"], escenario, datos.factores)
        problema.add_edge(INICIO, nodo, peso=espera,
                          desglose={"espera": espera})
    for nodo in nodos_de_estacion(grafo, destino_id):
        problema.add_edge(nodo, FIN, peso=0.0, desglose={})
    return problema


def reconstruir_camino(padre, g, nodo_final):
    """Sigue los punteros 'padre' hacia atrás desde el nodo final hasta INICIO."""
    camino = [nodo_final]
    while camino[-1] in padre:
        camino.append(padre[camino[-1]])
    camino.reverse()
    return camino, [g[n] for n in camino]


def a_estrella(problema, inicio=INICIO, fin=FIN, usar_heuristica=True):
    """Busca el camino de menor coste de 'inicio' a 'fin' con A*.

    problema: nx.DiGraph con atributo 'peso' en las aristas y 'h' en los nodos.
    """
    def h(nodo):
        return problema.nodes[nodo]["h"] if usar_heuristica else 0.0

    contador = itertools.count()          # desempate estable en la cola
    abiertos = [(h(inicio), next(contador), inicio)]
    g = {inicio: 0.0}
    padre = {}
    cerrados = set()
    traza = []

    while abiertos:
        f_actual, _, actual = heapq.heappop(abiertos)
        if actual in cerrados:
            continue                      # entrada antigua de un nodo ya mejorado
        cerrados.add(actual)
        traza.append({
            "paso": len(traza) + 1,
            "nodo": actual,
            "g": g[actual],
            "h": h(actual),
            "f": g[actual] + h(actual),
            "frontera": len(abiertos),
        })

        if actual == fin:                 # objetivo: el camino ya es óptimo
            camino, g_camino = reconstruir_camino(padre, g, fin)
            return ResultadoAEstrella(True, camino, g_camino, g[fin], len(cerrados), traza)

        for vecino in problema.successors(actual):
            if vecino in cerrados:
                continue
            g_tentativo = g[actual] + problema.edges[actual, vecino]["peso"]
            if g_tentativo < g.get(vecino, float("inf")):
                g[vecino] = g_tentativo
                padre[vecino] = actual
                heapq.heappush(abiertos, (g_tentativo + h(vecino), next(contador), vecino))

    return ResultadoAEstrella(False, nodos_expandidos=len(cerrados), traza=traza,
                              motivo="No existe camino entre el origen y el destino")


# ========================================================================================
# 6. RUTA
# ========================================================================================
# calcular_ruta(): el único punto de unión entre el algoritmo y la interfaz.
#
# Recibe lo que el usuario elige en pantalla y devuelve un diccionario con todo lo
# necesario para pintar el resultado: tiempo, itinerario, desglose, traza de A*...

@lru_cache(maxsize=1)
def grafo_red():
    """El grafo se construye una sola vez al arrancar."""
    return construir_grafo(cargar_datos())


def _direccion(datos, linea, desde_id, hacia_id):
    """Nombre de la cabecera hacia la que avanza el tren (sentido de la marcha)."""
    orden = datos.orden_linea(linea)
    cabecera = orden[-1] if orden.index(hacia_id) > orden.index(desde_id) else orden[0]
    return datos.estaciones[cabecera]["nombre"]


def hora_mas(hora, minutos):
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
    """Calcula la ruta óptima con A* entre dos estaciones (ids de ESTACIONES, sección 7)."""
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
        "hora_llegada": hora_mas(hora, tiempo),
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
    salida = hora_mas(hora_llegada, -30)          # primera suposición: media hora antes
    resultado = calcular_ruta(origen, destino, hora=salida, **opciones)
    for _ in range(4):
        if not resultado.get("ok"):
            return resultado
        nueva_salida = hora_mas(hora_llegada, -resultado["tiempo_total_min"])
        if nueva_salida == salida:
            break
        salida = nueva_salida
        resultado = calcular_ruta(origen, destino, hora=salida, **opciones)
    resultado["modo"] = "llegada"
    resultado["hora_llegada_deseada"] = hora_llegada
    return resultado


# ========================================================================================
# 7. DATOS DE LA RED
# ========================================================================================
# Sacados de la hoja de cálculo del grupo (Metrorrey_tiempos_entre_estaciones.xlsx):
# tiempos de marcha, distancias, tipo de vía y parámetros de g(n) y h(n).
# Coordenadas: L1 y L2 de Wikipedia (en), L3 de Wikidata (P625), Simón Bolívar de Wikipedia (es).
# Accesibilidad de L1 y L2: ABC Noticias, 18/10/2023. El grupo debe revisar las coordenadas.

ESTACIONES = [{'id': 'talleres',
  'nombre': 'Talleres',
  'alias': [],
  'lineas': ['L1'],
  'lat': 25.75389,
  'lon': -100.36528,
  'tipo_por_linea': {'L1': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'san_bernabe',
  'nombre': 'San Bernabé',
  'alias': [],
  'lineas': ['L1'],
  'lat': 25.74833,
  'lon': -100.36167,
  'tipo_por_linea': {'L1': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'unidad_modelo',
  'nombre': 'Unidad Modelo',
  'alias': [],
  'lineas': ['L1'],
  'lat': 25.74194,
  'lon': -100.355,
  'tipo_por_linea': {'L1': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'aztlan',
  'nombre': 'Aztlán',
  'alias': [],
  'lineas': ['L1'],
  'lat': 25.73222,
  'lon': -100.3475,
  'tipo_por_linea': {'L1': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'penitenciaria',
  'nombre': 'Penitenciaría',
  'alias': [],
  'lineas': ['L1'],
  'lat': 25.72333,
  'lon': -100.3425,
  'tipo_por_linea': {'L1': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'alfonso_reyes',
  'nombre': 'Alfonso Reyes',
  'alias': [],
  'lineas': ['L1'],
  'lat': 25.71611,
  'lon': -100.3425,
  'tipo_por_linea': {'L1': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'mitras',
  'nombre': 'Mitras',
  'alias': [],
  'lineas': ['L1'],
  'lat': 25.70556,
  'lon': -100.3425,
  'tipo_por_linea': {'L1': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'simon_bolivar',
  'nombre': 'Simón Bolívar',
  'alias': [],
  'lineas': ['L1'],
  'lat': 25.69904,
  'lon': -100.34324,
  'tipo_por_linea': {'L1': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': 'Wikipedia (es), artículo de la estación, consultada 25/11/2026'},
 {'id': 'hospital',
  'nombre': 'Hospital',
  'alias': [],
  'lineas': ['L1'],
  'lat': 25.69194,
  'lon': -100.34417,
  'tipo_por_linea': {'L1': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'edison',
  'nombre': 'Edison',
  'alias': [],
  'lineas': ['L1'],
  'lat': 25.68694,
  'lon': -100.33361,
  'tipo_por_linea': {'L1': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'central',
  'nombre': 'Central',
  'alias': [],
  'lineas': ['L1'],
  'lat': 25.68694,
  'lon': -100.32444,
  'tipo_por_linea': {'L1': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'cuauhtemoc',
  'nombre': 'Cuauhtémoc',
  'alias': [],
  'lineas': ['L1', 'L2'],
  'lat': 25.68611,
  'lon': -100.31694,
  'tipo_por_linea': {'L1': 'elevado', 'L2': 'subterraneo'},
  'tipo_dudoso': False,
  'transbordo': True,
  'parada_s': 35,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'del_golfo',
  'nombre': 'Del Golfo',
  'alias': [],
  'lineas': ['L1'],
  'lat': 25.68512,
  'lon': -100.30663,
  'tipo_por_linea': {'L1': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'felix_u_gomez',
  'nombre': 'Félix U. Gómez',
  'alias': [],
  'lineas': ['L1', 'L3'],
  'lat': 25.68389,
  'lon': -100.29667,
  'tipo_por_linea': {'L1': 'elevado', 'L3': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': True,
  'parada_s': 35,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'parque_fundidora',
  'nombre': 'Parque Fundidora',
  'alias': ['Arena Monterrey'],
  'lineas': ['L1'],
  'lat': 25.68361,
  'lon': -100.28806,
  'tipo_por_linea': {'L1': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'y_griega',
  'nombre': 'Y Griega',
  'alias': [],
  'lineas': ['L1'],
  'lat': 25.68333,
  'lon': -100.27933,
  'tipo_por_linea': {'L1': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'eloy_cavazos',
  'nombre': 'Eloy Cavazos',
  'alias': [],
  'lineas': ['L1'],
  'lat': 25.68,
  'lon': -100.26417,
  'tipo_por_linea': {'L1': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'lerdo_de_tejada',
  'nombre': 'Lerdo de Tejada',
  'alias': [],
  'lineas': ['L1'],
  'lat': 25.67972,
  'lon': -100.25278,
  'tipo_por_linea': {'L1': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'exposicion',
  'nombre': 'Exposición',
  'alias': [],
  'lineas': ['L1'],
  'lat': 25.67944,
  'lon': -100.24556,
  'tipo_por_linea': {'L1': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'sendero',
  'nombre': 'Sendero',
  'alias': [],
  'lineas': ['L2'],
  'lat': 25.76861,
  'lon': -100.29278,
  'tipo_por_linea': {'L2': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'santiago_tapia',
  'nombre': 'Santiago Tapia',
  'alias': [],
  'lineas': ['L2'],
  'lat': 25.75926,
  'lon': -100.29568,
  'tipo_por_linea': {'L2': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'san_nicolas',
  'nombre': 'San Nicolás',
  'alias': [],
  'lineas': ['L2'],
  'lat': 25.75262,
  'lon': -100.29805,
  'tipo_por_linea': {'L2': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'anahuac',
  'nombre': 'Anáhuac',
  'alias': [],
  'lineas': ['L2'],
  'lat': 25.74028,
  'lon': -100.3025,
  'tipo_por_linea': {'L2': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'universidad',
  'nombre': 'Universidad',
  'alias': [],
  'lineas': ['L2'],
  'lat': 25.72444,
  'lon': -100.30833,
  'tipo_por_linea': {'L2': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'ninos_heroes',
  'nombre': 'Niños Héroes',
  'alias': [],
  'lineas': ['L2'],
  'lat': 25.71722,
  'lon': -100.31111,
  'tipo_por_linea': {'L2': 'transicion'},
  'tipo_dudoso': True,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'regina',
  'nombre': 'Regina',
  'alias': [],
  'lineas': ['L2'],
  'lat': 25.7079,
  'lon': -100.3141,
  'tipo_por_linea': {'L2': 'subterraneo'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'general_anaya',
  'nombre': 'General Anaya',
  'alias': [],
  'lineas': ['L2'],
  'lat': 25.69694,
  'lon': -100.31667,
  'tipo_por_linea': {'L2': 'subterraneo'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'alameda',
  'nombre': 'Alameda',
  'alias': [],
  'lineas': ['L2'],
  'lat': 25.67694,
  'lon': -100.31833,
  'tipo_por_linea': {'L2': 'subterraneo'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'fundadores',
  'nombre': 'Fundadores',
  'alias': [],
  'lineas': ['L2'],
  'lat': 25.67267,
  'lon': -100.3197,
  'tipo_por_linea': {'L2': 'subterraneo'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'padre_mier',
  'nombre': 'Padre Mier',
  'alias': [],
  'lineas': ['L2'],
  'lat': 25.66888,
  'lon': -100.31544,
  'tipo_por_linea': {'L2': 'subterraneo'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'general_i_zaragoza',
  'nombre': 'General I. Zaragoza',
  'alias': ['Gral. I. Zaragoza', 'General Ignacio Zaragoza'],
  'lineas': ['L2', 'L3'],
  'lat': 25.66778,
  'lon': -100.31028,
  'tipo_por_linea': {'L2': 'subterraneo', 'L3': 'subterraneo'},
  'tipo_dudoso': False,
  'transbordo': True,
  'parada_s': 35,
  'accesible': False,
  'aprox': False,
  'fuente_coordenadas': "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"},
 {'id': 'hospital_metropolitano',
  'nombre': 'Hospital Metropolitano',
  'alias': [],
  'lineas': ['L3'],
  'lat': 25.71376,
  'lon': -100.27359,
  'tipo_por_linea': {'L3': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': True,
  'aprox': False,
  'fuente_coordenadas': 'Wikidata (propiedad P625), consultada 25/11/2026'},
 {'id': 'los_angeles',
  'nombre': 'Los Ángeles',
  'alias': [],
  'lineas': ['L3'],
  'lat': 25.70812,
  'lon': -100.28171,
  'tipo_por_linea': {'L3': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': True,
  'aprox': False,
  'fuente_coordenadas': 'Wikidata (propiedad P625), consultada 25/11/2026'},
 {'id': 'ruiz_cortines',
  'nombre': 'Ruiz Cortines',
  'alias': [],
  'lineas': ['L3'],
  'lat': 25.70375,
  'lon': -100.28796,
  'tipo_por_linea': {'L3': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': True,
  'aprox': False,
  'fuente_coordenadas': 'Wikidata (propiedad P625), consultada 25/11/2026'},
 {'id': 'colonia_moderna',
  'nombre': 'Colonia Moderna',
  'alias': ['Col. Moderna'],
  'lineas': ['L3'],
  'lat': 25.70046,
  'lon': -100.2926,
  'tipo_por_linea': {'L3': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': True,
  'aprox': False,
  'fuente_coordenadas': 'Wikidata (propiedad P625), consultada 25/11/2026'},
 {'id': 'metalurgicos',
  'nombre': 'Metalúrgicos',
  'alias': [],
  'lineas': ['L3'],
  'lat': 25.69102,
  'lon': -100.29582,
  'tipo_por_linea': {'L3': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': True,
  'aprox': False,
  'fuente_coordenadas': 'Wikidata (propiedad P625), consultada 25/11/2026'},
 {'id': 'colonia_obrera',
  'nombre': 'Colonia Obrera',
  'alias': ['Col. Obrera'],
  'lineas': ['L3'],
  'lat': 25.67789,
  'lon': -100.29766,
  'tipo_por_linea': {'L3': 'elevado'},
  'tipo_dudoso': False,
  'transbordo': False,
  'parada_s': 20,
  'accesible': True,
  'aprox': False,
  'fuente_coordenadas': 'Wikidata (propiedad P625), consultada 25/11/2026'},
 {'id': 'santa_lucia',
  'nombre': 'Santa Lucía',
  'alias': [],
  'lineas': ['L3'],
  'lat': 25.6714,
  'lon': -100.29855,
  'tipo_por_linea': {'L3': 'transicion'},
  'tipo_dudoso': True,
  'transbordo': False,
  'parada_s': 20,
  'accesible': True,
  'aprox': False,
  'fuente_coordenadas': 'Wikidata (propiedad P625), consultada 25/11/2026'}]

# Tramos entre estaciones consecutivas, en el orden de cada línea (marcha_s = segundos de marcha)
TRAMOS = [
    {'linea': 'L1', 'desde': 'talleres', 'hasta': 'san_bernabe', 'distancia_m': 762, 'tipo': 'elevado', 'marcha_s': 62, 'confianza': 'media'},
    {'linea': 'L1', 'desde': 'san_bernabe', 'hasta': 'unidad_modelo', 'distancia_m': 1037, 'tipo': 'elevado', 'marcha_s': 76, 'confianza': 'media'},
    {'linea': 'L1', 'desde': 'unidad_modelo', 'hasta': 'aztlan', 'distancia_m': 1400, 'tipo': 'elevado', 'marcha_s': 95, 'confianza': 'media'},
    {'linea': 'L1', 'desde': 'aztlan', 'hasta': 'penitenciaria', 'distancia_m': 1179, 'tipo': 'elevado', 'marcha_s': 84, 'confianza': 'media'},
    {'linea': 'L1', 'desde': 'penitenciaria', 'hasta': 'alfonso_reyes', 'distancia_m': 854, 'tipo': 'elevado', 'marcha_s': 67, 'confianza': 'media'},
    {'linea': 'L1', 'desde': 'alfonso_reyes', 'hasta': 'mitras', 'distancia_m': 628, 'tipo': 'elevado', 'marcha_s': 55, 'confianza': 'media'},
    {'linea': 'L1', 'desde': 'mitras', 'hasta': 'simon_bolivar', 'distancia_m': 620, 'tipo': 'elevado', 'marcha_s': 55, 'confianza': 'media'},
    {'linea': 'L1', 'desde': 'simon_bolivar', 'hasta': 'hospital', 'distancia_m': 1621, 'tipo': 'elevado', 'marcha_s': 106, 'confianza': 'media'},
    {'linea': 'L1', 'desde': 'hospital', 'hasta': 'edison', 'distancia_m': 1271, 'tipo': 'elevado', 'marcha_s': 88, 'confianza': 'media'},
    {'linea': 'L1', 'desde': 'edison', 'hasta': 'central', 'distancia_m': 977, 'tipo': 'elevado', 'marcha_s': 73, 'confianza': 'media'},
    {'linea': 'L1', 'desde': 'central', 'hasta': 'cuauhtemoc', 'distancia_m': 805, 'tipo': 'elevado', 'marcha_s': 64, 'confianza': 'media'},
    {'linea': 'L1', 'desde': 'cuauhtemoc', 'hasta': 'del_golfo', 'distancia_m': 1105, 'tipo': 'elevado', 'marcha_s': 80, 'confianza': 'media'},
    {'linea': 'L1', 'desde': 'del_golfo', 'hasta': 'felix_u_gomez', 'distancia_m': 1072, 'tipo': 'elevado', 'marcha_s': 78, 'confianza': 'media'},
    {'linea': 'L1', 'desde': 'felix_u_gomez', 'hasta': 'parque_fundidora', 'distancia_m': 918, 'tipo': 'elevado', 'marcha_s': 70, 'confianza': 'media'},
    {'linea': 'L1', 'desde': 'parque_fundidora', 'hasta': 'y_griega', 'distancia_m': 931, 'tipo': 'elevado', 'marcha_s': 71, 'confianza': 'media'},
    {'linea': 'L1', 'desde': 'y_griega', 'hasta': 'eloy_cavazos', 'distancia_m': 1663, 'tipo': 'elevado', 'marcha_s': 108, 'confianza': 'media'},
    {'linea': 'L1', 'desde': 'eloy_cavazos', 'hasta': 'lerdo_de_tejada', 'distancia_m': 1215, 'tipo': 'elevado', 'marcha_s': 85, 'confianza': 'media'},
    {'linea': 'L1', 'desde': 'lerdo_de_tejada', 'hasta': 'exposicion', 'distancia_m': 770, 'tipo': 'elevado', 'marcha_s': 63, 'confianza': 'media'},
    {'linea': 'L2', 'desde': 'sendero', 'hasta': 'santiago_tapia', 'distancia_m': 1214, 'tipo': 'elevado', 'marcha_s': 85, 'confianza': 'media'},
    {'linea': 'L2', 'desde': 'santiago_tapia', 'hasta': 'san_nicolas', 'distancia_m': 872, 'tipo': 'elevado', 'marcha_s': 68, 'confianza': 'media'},
    {'linea': 'L2', 'desde': 'san_nicolas', 'hasta': 'anahuac', 'distancia_m': 1622, 'tipo': 'elevado', 'marcha_s': 106, 'confianza': 'media'},
    {'linea': 'L2', 'desde': 'anahuac', 'hasta': 'universidad', 'distancia_m': 2086, 'tipo': 'elevado', 'marcha_s': 130, 'confianza': 'media'},
    {'linea': 'L2', 'desde': 'universidad', 'hasta': 'ninos_heroes', 'distancia_m': 955, 'tipo': 'elevado', 'marcha_s': 72, 'confianza': 'media'},
    {'linea': 'L2', 'desde': 'ninos_heroes', 'hasta': 'regina', 'distancia_m': 1213, 'tipo': 'subterraneo', 'marcha_s': 85, 'confianza': 'media'},
    {'linea': 'L2', 'desde': 'regina', 'hasta': 'general_anaya', 'distancia_m': 1400, 'tipo': 'subterraneo', 'marcha_s': 95, 'confianza': 'media'},
    {'linea': 'L2', 'desde': 'general_anaya', 'hasta': 'cuauhtemoc', 'distancia_m': 1354, 'tipo': 'subterraneo', 'marcha_s': 93, 'confianza': 'media'},
    {'linea': 'L2', 'desde': 'cuauhtemoc', 'hasta': 'alameda', 'distancia_m': 1157, 'tipo': 'subterraneo', 'marcha_s': 82, 'confianza': 'media'},
    {'linea': 'L2', 'desde': 'alameda', 'hasta': 'fundadores', 'distancia_m': 556, 'tipo': 'subterraneo', 'marcha_s': 52, 'confianza': 'media'},
    {'linea': 'L2', 'desde': 'fundadores', 'hasta': 'padre_mier', 'distancia_m': 674, 'tipo': 'subterraneo', 'marcha_s': 58, 'confianza': 'media'},
    {'linea': 'L2', 'desde': 'padre_mier', 'hasta': 'general_i_zaragoza', 'distancia_m': 597, 'tipo': 'subterraneo', 'marcha_s': 54, 'confianza': 'media'},
    {'linea': 'L3', 'desde': 'hospital_metropolitano', 'hasta': 'los_angeles', 'distancia_m': 884, 'tipo': 'elevado', 'marcha_s': 68, 'confianza': 'baja'},
    {'linea': 'L3', 'desde': 'los_angeles', 'hasta': 'ruiz_cortines', 'distancia_m': 862, 'tipo': 'elevado', 'marcha_s': 67, 'confianza': 'baja'},
    {'linea': 'L3', 'desde': 'ruiz_cortines', 'hasta': 'colonia_moderna', 'distancia_m': 1008, 'tipo': 'elevado', 'marcha_s': 75, 'confianza': 'baja'},
    {'linea': 'L3', 'desde': 'colonia_moderna', 'hasta': 'metalurgicos', 'distancia_m': 1037, 'tipo': 'elevado', 'marcha_s': 76, 'confianza': 'baja'},
    {'linea': 'L3', 'desde': 'metalurgicos', 'hasta': 'felix_u_gomez', 'distancia_m': 1533, 'tipo': 'elevado', 'marcha_s': 102, 'confianza': 'baja'},
    {'linea': 'L3', 'desde': 'felix_u_gomez', 'hasta': 'colonia_obrera', 'distancia_m': 617, 'tipo': 'elevado', 'marcha_s': 55, 'confianza': 'baja'},
    {'linea': 'L3', 'desde': 'colonia_obrera', 'hasta': 'santa_lucia', 'distancia_m': 616, 'tipo': 'elevado', 'marcha_s': 55, 'confianza': 'baja'},
    {'linea': 'L3', 'desde': 'santa_lucia', 'hasta': 'general_i_zaragoza', 'distancia_m': 943, 'tipo': 'subterraneo', 'marcha_s': 71, 'confianza': 'baja'},
]

FACTORES = {'_comentario': "Parámetros de g(n) y h(n). Los factores proceden de la hoja 'Parámetros' del Excel del "
                'grupo (hipótesis de partida, no publicadas por Metrorrey). Se pueden editar a mano; la app '
                'los lee al arrancar.',
 'v_max_kmh': 80,
 '_v_max': 'Velocidad máxima real de los trenes. El Excel calibra 70 km/h de crucero, pero h(n) necesita la '
           'máxima para no sobreestimar nunca (admisible).',
 'parada_base_s': 20,
 'parada_transbordo_s': 35,
 'horario_servicio': {'inicio': '05:00', 'fin': '24:00'},
 'franjas': [{'clave': 'apertura',
              'nombre': 'Apertura',
              'hora_inicio': '05:00',
              'hora_fin': '06:30',
              'factor_marcha': 1,
              'factor_parada': 0.9,
              'intervalo_min': {'L1': 6, 'L2': 7, 'L3': 8},
              'es_punta': False},
             {'clave': 'punta_manana',
              'nombre': 'Punta mañana',
              'hora_inicio': '06:30',
              'hora_fin': '09:30',
              'factor_marcha': 1.05,
              'factor_parada': 1.75,
              'intervalo_min': {'L1': 4, 'L2': 5, 'L3': 6},
              'es_punta': True},
             {'clave': 'valle_manana',
              'nombre': 'Valle mañana',
              'hora_inicio': '09:30',
              'hora_fin': '13:00',
              'factor_marcha': 1,
              'factor_parada': 1,
              'intervalo_min': {'L1': 7, 'L2': 7, 'L3': 7.5},
              'es_punta': False},
             {'clave': 'mediodia',
              'nombre': 'Mediodía / salida escolar',
              'hora_inicio': '13:00',
              'hora_fin': '16:30',
              'factor_marcha': 1.02,
              'factor_parada': 1.3,
              'intervalo_min': {'L1': 5, 'L2': 6, 'L3': 7.5},
              'es_punta': False},
             {'clave': 'punta_tarde',
              'nombre': 'Punta tarde',
              'hora_inicio': '16:30',
              'hora_fin': '20:00',
              'factor_marcha': 1.06,
              'factor_parada': 1.8,
              'intervalo_min': {'L1': 4, 'L2': 5, 'L3': 6},
              'es_punta': True},
             {'clave': 'noche',
              'nombre': 'Noche',
              'hora_inicio': '20:00',
              'hora_fin': '22:00',
              'factor_marcha': 1,
              'factor_parada': 1.1,
              'intervalo_min': {'L1': 6, 'L2': 7, 'L3': 8},
              'es_punta': False},
             {'clave': 'cierre',
              'nombre': 'Cierre',
              'hora_inicio': '22:00',
              'hora_fin': '24:00',
              'factor_marcha': 1,
              'factor_parada': 0.9,
              'intervalo_min': {'L1': 8, 'L2': 9, 'L3': 10},
              'es_punta': False},
             {'clave': 'fin_de_semana',
              'nombre': 'Sábado/domingo/festivo',
              'hora_inicio': None,
              'hora_fin': None,
              'factor_marcha': 1,
              'factor_parada': 1.1,
              'intervalo_min': {'L1': 7, 'L2': 8, 'L3': 9},
              'es_punta': False},
             {'clave': 'evento_masivo',
              'nombre': 'Evento masivo (Fundidora, Arena, estadios)',
              'hora_inicio': None,
              'hora_fin': None,
              'factor_marcha': 1.1,
              'factor_parada': 2.5,
              'intervalo_min': {'L1': 4, 'L2': 5, 'L3': 6},
              'es_punta': True}],
 'clima': {'despejado': {'nombre': 'Despejado',
                         'icono': 'wb_sunny',
                         'factor_marcha_elevado': 1,
                         'factor_marcha_subterraneo': 1,
                         'factor_parada': 1,
                         'riesgo_suspension': 'Nula'},
           'lluvia_ligera': {'nombre': 'Lluvia ligera',
                             'icono': 'grain',
                             'factor_marcha_elevado': 1.05,
                             'factor_marcha_subterraneo': 1,
                             'factor_parada': 1.15,
                             'riesgo_suspension': 'Baja'},
           'lluvia_intensa': {'nombre': 'Lluvia intensa',
                              'icono': 'umbrella',
                              'factor_marcha_elevado': 1.15,
                              'factor_marcha_subterraneo': 1.02,
                              'factor_parada': 1.3,
                              'riesgo_suspension': 'Media'},
           'tormenta': {'nombre': 'Tormenta eléctrica',
                        'icono': 'thunderstorm',
                        'factor_marcha_elevado': 1.3,
                        'factor_marcha_subterraneo': 1.05,
                        'factor_parada': 1.35,
                        'riesgo_suspension': 'Alta'},
           'granizo': {'nombre': 'Granizo',
                       'icono': 'ac_unit',
                       'factor_marcha_elevado': 1.4,
                       'factor_marcha_subterraneo': 1.05,
                       'factor_parada': 1.3,
                       'riesgo_suspension': 'Alta'},
           'inundacion': {'nombre': 'Inundación / huracán',
                          'icono': 'flood',
                          'factor_marcha_elevado': 1.6,
                          'factor_marcha_subterraneo': 2,
                          'factor_parada': 1.5,
                          'riesgo_suspension': 'Muy alta'},
           'calor_extremo': {'nombre': 'Calor extremo',
                             'icono': 'local_fire_department',
                             'factor_marcha_elevado': 1.04,
                             'factor_marcha_subterraneo': 1,
                             'factor_parada': 1.05,
                             'riesgo_suspension': 'Baja'},
           'helada': {'nombre': 'Frío extremo / helada',
                      'icono': 'severe_cold',
                      'factor_marcha_elevado': 1.15,
                      'factor_marcha_subterraneo': 1.02,
                      'factor_parada': 1.1,
                      'riesgo_suspension': 'Media'},
           'niebla': {'nombre': 'Niebla densa',
                      'icono': 'foggy',
                      'factor_marcha_elevado': 1.1,
                      'factor_marcha_subterraneo': 1,
                      'factor_parada': 1,
                      'riesgo_suspension': 'Baja'},
           'viento_fuerte': {'nombre': 'Viento fuerte',
                             'icono': 'air',
                             'factor_marcha_elevado': 1.1,
                             'factor_marcha_subterraneo': 1,
                             'factor_parada': 1,
                             'riesgo_suspension': 'Media'}},
 'transbordos': {'_comentario': 'pasillo_min: caminar entre andenes (supuesto dentro del rango 3-6 min del '
                                'Excel). saturacion_punta_min: tiempo extra en hora punta o evento (el grupo '
                                'encontró 3-7 min en Cuauhtémoc y Zaragoza).',
                 'cuauhtemoc': {'pasillo_min': 4, 'saturacion_punta_min': 5},
                 'general_i_zaragoza': {'pasillo_min': 3, 'saturacion_punta_min': 5},
                 'felix_u_gomez': {'pasillo_min': 3, 'saturacion_punta_min': 2}},
 'penalizacion_minimizar_transbordos_min': 10,
 'penalizacion_no_accesible_min': 15}

# Líneas 4 y 6: EN CONSTRUCCIÓN a 25/11/2026. Solo se dibujan en el mapa, no se usan para
# calcular rutas. Posiciones APROXIMADAS de OpenStreetMap (consulta del 25/11/2026); de la
# Línea 4 solo está el tramo del centro, que es el que tiene nombres en OSM.
LINEAS_EN_OBRAS = [{'id': 'L4',
  'nombre': 'Línea 4 (en construcción)',
  'color': '#7C3AED',
  'estaciones': [{'nombre': 'Obispado / Torre Rise', 'lat': 25.6707, 'lon': -100.34711},
                 {'nombre': 'Fuerza Civil', 'lat': 25.66857, 'lon': -100.33914},
                 {'nombre': 'Serafín Peña', 'lat': 25.66697, 'lon': -100.33028},
                 {'nombre': 'Pino Suárez', 'lat': 25.6656, 'lon': -100.32221},
                 {'nombre': 'Puente del Papa', 'lat': 25.66436, 'lon': -100.31542},
                 {'nombre': 'Macroplaza', 'lat': 25.6632, 'lon': -100.30911},
                 {'nombre': 'Barrio Antiguo', 'lat': 25.66583, 'lon': -100.30333}]},
 {'id': 'L6',
  'nombre': 'Línea 6 (en construcción)',
  'color': '#EA580C',
  'estaciones': [{'nombre': 'Parque Fundidora', 'lat': 25.67422, 'lon': -100.29013},
                 {'nombre': 'Y Griega', 'lat': 25.68278, 'lon': -100.27992},
                 {'nombre': 'Churubusco', 'lat': 25.68613, 'lon': -100.2672},
                 {'nombre': 'Lindavista', 'lat': 25.68858, 'lon': -100.25863},
                 {'nombre': 'Libertad', 'lat': 25.69116, 'lon': -100.24959},
                 {'nombre': 'Bonifacio Salinas', 'lat': 25.69366, 'lon': -100.24061},
                 {'nombre': 'San Rafael', 'lat': 25.69636, 'lon': -100.23127},
                 {'nombre': 'La Victoria', 'lat': 25.70407, 'lon': -100.2248},
                 {'nombre': 'La Talaverna', 'lat': 25.7101, 'lon': -100.22175},
                 {'nombre': 'La Fe', 'lat': 25.72002, 'lon': -100.21644},
                 {'nombre': 'Isidro Sepúlveda', 'lat': 25.73716, 'lon': -100.20756},
                 {'nombre': 'El Milagro', 'lat': 25.74565, 'lon': -100.20273},
                 {'nombre': 'Concordia', 'lat': 25.75198, 'lon': -100.19934},
                 {'nombre': 'Apodaca', 'lat': 25.77435, 'lon': -100.18775},
                 {'nombre': 'Arco Vial', 'lat': 25.78043, 'lon': -100.17462}]}]
