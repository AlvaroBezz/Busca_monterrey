"""Ruta más rápida en el Metro de Monterrey (líneas 1, 2 y 3) con un A* programado a mano.

Partes del archivo:
    1. Datos de la red (sacados del Excel del grupo)
    2. Grafo: un nodo por estación y línea ("cuauhtemoc@L1")
    3. g(n): minutos que cuesta cada arista según hora, día, clima y preferencias
    4. h(n): línea recta hasta el destino / 80 km/h
    5. A*
    6. calcular_ruta(): lo que usa la web (main.py)
"""

import heapq
import math

import networkx as nx

# =============================================================================
# 1. DATOS DE LA RED
# =============================================================================
# Coordenadas: L1 y L2 de Wikipedia (en), L3 de Wikidata, Simón Bolívar de Wikipedia (es).
# Tiempos, distancias y factores: hoja Metrorrey_tiempos_entre_estaciones.xlsx del grupo.

# (id, nombre, líneas, latitud, longitud)
ESTACIONES = [
    ("talleres", "Talleres", "L1", 25.75389, -100.36528),
    ("san_bernabe", "San Bernabé", "L1", 25.74833, -100.36167),
    ("unidad_modelo", "Unidad Modelo", "L1", 25.74194, -100.355),
    ("aztlan", "Aztlán", "L1", 25.73222, -100.3475),
    ("penitenciaria", "Penitenciaría", "L1", 25.72333, -100.3425),
    ("alfonso_reyes", "Alfonso Reyes", "L1", 25.71611, -100.3425),
    ("mitras", "Mitras", "L1", 25.70556, -100.3425),
    ("simon_bolivar", "Simón Bolívar", "L1", 25.69904, -100.34324),
    ("hospital", "Hospital", "L1", 25.69194, -100.34417),
    ("edison", "Edison", "L1", 25.68694, -100.33361),
    ("central", "Central", "L1", 25.68694, -100.32444),
    ("cuauhtemoc", "Cuauhtémoc", "L1 L2", 25.68611, -100.31694),
    ("del_golfo", "Del Golfo", "L1", 25.68512, -100.30663),
    ("felix_u_gomez", "Félix U. Gómez", "L1 L3", 25.68389, -100.29667),
    ("parque_fundidora", "Parque Fundidora", "L1", 25.68361, -100.28806),
    ("y_griega", "Y Griega", "L1", 25.68333, -100.27933),
    ("eloy_cavazos", "Eloy Cavazos", "L1", 25.68, -100.26417),
    ("lerdo_de_tejada", "Lerdo de Tejada", "L1", 25.67972, -100.25278),
    ("exposicion", "Exposición", "L1", 25.67944, -100.24556),
    ("sendero", "Sendero", "L2", 25.76861, -100.29278),
    ("santiago_tapia", "Santiago Tapia", "L2", 25.75926, -100.29568),
    ("san_nicolas", "San Nicolás", "L2", 25.75262, -100.29805),
    ("anahuac", "Anáhuac", "L2", 25.74028, -100.3025),
    ("universidad", "Universidad", "L2", 25.72444, -100.30833),
    ("ninos_heroes", "Niños Héroes", "L2", 25.71722, -100.31111),
    ("regina", "Regina", "L2", 25.7079, -100.3141),
    ("general_anaya", "General Anaya", "L2", 25.69694, -100.31667),
    ("alameda", "Alameda", "L2", 25.67694, -100.31833),
    ("fundadores", "Fundadores", "L2", 25.67267, -100.3197),
    ("padre_mier", "Padre Mier", "L2", 25.66888, -100.31544),
    ("general_i_zaragoza", "General I. Zaragoza", "L2 L3", 25.66778, -100.31028),
    ("hospital_metropolitano", "Hospital Metropolitano", "L3", 25.71376, -100.27359),
    ("los_angeles", "Los Ángeles", "L3", 25.70812, -100.28171),
    ("ruiz_cortines", "Ruiz Cortines", "L3", 25.70375, -100.28796),
    ("colonia_moderna", "Colonia Moderna", "L3", 25.70046, -100.2926),
    ("metalurgicos", "Metalúrgicos", "L3", 25.69102, -100.29582),
    ("colonia_obrera", "Colonia Obrera", "L3", 25.67789, -100.29766),
    ("santa_lucia", "Santa Lucía", "L3", 25.6714, -100.29855),
]

# (línea, desde, hasta, metros, segundos de marcha, tipo de vía), en el orden de cada línea
TRAMOS = [
    ("L1", "talleres", "san_bernabe", 762, 62, "elevado"),
    ("L1", "san_bernabe", "unidad_modelo", 1037, 76, "elevado"),
    ("L1", "unidad_modelo", "aztlan", 1400, 95, "elevado"),
    ("L1", "aztlan", "penitenciaria", 1179, 84, "elevado"),
    ("L1", "penitenciaria", "alfonso_reyes", 854, 67, "elevado"),
    ("L1", "alfonso_reyes", "mitras", 628, 55, "elevado"),
    ("L1", "mitras", "simon_bolivar", 620, 55, "elevado"),
    ("L1", "simon_bolivar", "hospital", 1621, 106, "elevado"),
    ("L1", "hospital", "edison", 1271, 88, "elevado"),
    ("L1", "edison", "central", 977, 73, "elevado"),
    ("L1", "central", "cuauhtemoc", 805, 64, "elevado"),
    ("L1", "cuauhtemoc", "del_golfo", 1105, 80, "elevado"),
    ("L1", "del_golfo", "felix_u_gomez", 1072, 78, "elevado"),
    ("L1", "felix_u_gomez", "parque_fundidora", 918, 70, "elevado"),
    ("L1", "parque_fundidora", "y_griega", 931, 71, "elevado"),
    ("L1", "y_griega", "eloy_cavazos", 1663, 108, "elevado"),
    ("L1", "eloy_cavazos", "lerdo_de_tejada", 1215, 85, "elevado"),
    ("L1", "lerdo_de_tejada", "exposicion", 770, 63, "elevado"),
    ("L2", "sendero", "santiago_tapia", 1214, 85, "elevado"),
    ("L2", "santiago_tapia", "san_nicolas", 872, 68, "elevado"),
    ("L2", "san_nicolas", "anahuac", 1622, 106, "elevado"),
    ("L2", "anahuac", "universidad", 2086, 130, "elevado"),
    ("L2", "universidad", "ninos_heroes", 955, 72, "elevado"),
    ("L2", "ninos_heroes", "regina", 1213, 85, "subterraneo"),
    ("L2", "regina", "general_anaya", 1400, 95, "subterraneo"),
    ("L2", "general_anaya", "cuauhtemoc", 1354, 93, "subterraneo"),
    ("L2", "cuauhtemoc", "alameda", 1157, 82, "subterraneo"),
    ("L2", "alameda", "fundadores", 556, 52, "subterraneo"),
    ("L2", "fundadores", "padre_mier", 674, 58, "subterraneo"),
    ("L2", "padre_mier", "general_i_zaragoza", 597, 54, "subterraneo"),
    ("L3", "hospital_metropolitano", "los_angeles", 884, 68, "elevado"),
    ("L3", "los_angeles", "ruiz_cortines", 862, 67, "elevado"),
    ("L3", "ruiz_cortines", "colonia_moderna", 1008, 75, "elevado"),
    ("L3", "colonia_moderna", "metalurgicos", 1037, 76, "elevado"),
    ("L3", "metalurgicos", "felix_u_gomez", 1533, 102, "elevado"),
    ("L3", "felix_u_gomez", "colonia_obrera", 617, 55, "elevado"),
    ("L3", "colonia_obrera", "santa_lucia", 616, 55, "elevado"),
    ("L3", "santa_lucia", "general_i_zaragoza", 943, 71, "subterraneo"),
]

V_MAX = 80                       # km/h, velocidad máxima de los trenes (para h)
PARADA_S = 20                    # segundos parado en una estación normal
PARADA_TRANSBORDO_S = 35         # ... y en una de transbordo
HORA_APERTURA, HORA_CIERRE = "05:00", "24:00"

# Franjas: nombre, inicio, fin, factor de marcha, factor de parada, intervalo L1/L2/L3 (min), punta
FRANJAS = [
    ("Apertura", "05:00", "06:30", 1.00, 0.90, (6, 7, 8), False),
    ("Punta mañana", "06:30", "09:30", 1.05, 1.75, (4, 5, 6), True),
    ("Valle mañana", "09:30", "13:00", 1.00, 1.00, (7, 7, 7.5), False),
    ("Mediodía / salida escolar", "13:00", "16:30", 1.02, 1.30, (5, 6, 7.5), False),
    ("Punta tarde", "16:30", "20:00", 1.06, 1.80, (4, 5, 6), True),
    ("Noche", "20:00", "22:00", 1.00, 1.10, (6, 7, 8), False),
    ("Cierre", "22:00", "24:00", 1.00, 0.90, (8, 9, 10), False),
]
FIN_DE_SEMANA = ("Sábado/domingo/festivo", None, None, 1.00, 1.10, (7, 8, 9), False)
EVENTO = ("Evento masivo (Fundidora, Arena, estadios)", None, None, 1.10, 2.50, (4, 5, 6), True)

# Clima: nombre, factor de marcha en vía elevada, en subterránea, factor de parada, riesgo de cierre
CLIMAS = {
    "despejado": ("Despejado", 1.00, 1.00, 1.00, "Nula"),
    "lluvia_ligera": ("Lluvia ligera", 1.05, 1.00, 1.15, "Baja"),
    "lluvia_intensa": ("Lluvia intensa", 1.15, 1.02, 1.30, "Media"),
    "tormenta": ("Tormenta eléctrica", 1.30, 1.05, 1.35, "Alta"),
    "granizo": ("Granizo", 1.40, 1.05, 1.30, "Alta"),
    "inundacion": ("Inundación / huracán", 1.60, 2.00, 1.50, "Muy alta"),
    "calor_extremo": ("Calor extremo", 1.04, 1.00, 1.05, "Baja"),
    "helada": ("Frío extremo / helada", 1.15, 1.02, 1.10, "Media"),
    "niebla": ("Niebla densa", 1.10, 1.00, 1.00, "Baja"),
    "viento_fuerte": ("Viento fuerte", 1.10, 1.00, 1.00, "Media"),
}

# Transbordos: minutos andando entre andenes y minutos extra en hora punta
TRANSBORDOS = {"cuauhtemoc": (4, 5), "general_i_zaragoza": (3, 5), "felix_u_gomez": (3, 2)}
PENALIZACION_TRANSBORDO = 10     # si el usuario quiere cambiar de línea lo menos posible
PENALIZACION_NO_ACCESIBLE = 15   # si pide ruta accesible y la estación no lo es

COLORES_LINEA = {"L1": "#F2C200", "L2": "#2E9E44", "L3": "#D7262E"}
NOMBRES_LINEA = {"L1": "Línea 1 (amarilla)", "L2": "Línea 2 (verde)", "L3": "Línea 3 (roja)"}

# Líneas 4 y 6: en construcción (nov. 2026). Solo se dibujan en el mapa, NO se usan en el cálculo.
# Posiciones aproximadas de OpenStreetMap; de la L4 solo está el tramo del centro.
LINEAS_EN_OBRAS = [
    ("Línea 4", "#7C3AED", [
        ("Obispado / Torre Rise", 25.6707, -100.34711), ("Fuerza Civil", 25.66857, -100.33914),
        ("Serafín Peña", 25.66697, -100.33028), ("Pino Suárez", 25.6656, -100.32221),
        ("Puente del Papa", 25.66436, -100.31542), ("Macroplaza", 25.6632, -100.30911),
        ("Barrio Antiguo", 25.66583, -100.30333)]),
    ("Línea 6", "#EA580C", [
        ("Parque Fundidora", 25.67422, -100.29013), ("Y Griega", 25.68278, -100.27992),
        ("Churubusco", 25.68613, -100.2672), ("Lindavista", 25.68858, -100.25863),
        ("Libertad", 25.69116, -100.24959), ("Bonifacio Salinas", 25.69366, -100.24061),
        ("San Rafael", 25.69636, -100.23127), ("La Victoria", 25.70407, -100.2248),
        ("La Talaverna", 25.7101, -100.22175), ("La Fe", 25.72002, -100.21644),
        ("Isidro Sepúlveda", 25.73716, -100.20756), ("El Milagro", 25.74565, -100.20273),
        ("Concordia", 25.75198, -100.19934), ("Apodaca", 25.77435, -100.18775),
        ("Arco Vial", 25.78043, -100.17462)]),
]

# Diccionario id -> datos de la estación, más cómodo de usar
estaciones = {}
for id_, nombre, lineas, lat, lon in ESTACIONES:
    lineas = lineas.split()
    estaciones[id_] = {"id": id_, "nombre": nombre, "lineas": lineas, "lat": lat, "lon": lon,
                       "transbordo": len(lineas) > 1,
                       # Solo la L3 es accesible; un transbordo cuenta como accesible si lo son todas sus líneas
                       "accesible": lineas == ["L3"]}


def orden_linea(linea):
    """Estaciones de una línea, de una cabecera a la otra."""
    tramos = [t for t in TRAMOS if t[0] == linea]
    return [tramos[0][1]] + [t[2] for t in tramos]


# =============================================================================
# 2. GRAFO
# =============================================================================
# Un nodo por estación y línea: "cuauhtemoc@L1" y "cuauhtemoc@L2" son dos nodos unidos por
# una arista de transbordo. Así cambiar de línea tiene su propio coste.
# 38 estaciones + 3 de transbordo repetidas = 41 nodos; 38 tramos + 3 transbordos = 41 aristas.
# NetworkX solo guarda el grafo: el A* está programado abajo, a mano.

grafo = nx.Graph()
for est in estaciones.values():
    for linea in est["lineas"]:
        grafo.add_node(f"{est['id']}@{linea}", estacion=est["id"], linea=linea)
for linea, desde, hasta, metros, segundos, via in TRAMOS:
    grafo.add_edge(f"{desde}@{linea}", f"{hasta}@{linea}", tipo="tramo", metros=metros,
                   segundos=segundos, via=via)
for est_id, (pasillo, saturacion) in TRANSBORDOS.items():
    a, b = estaciones[est_id]["lineas"]
    grafo.add_edge(f"{est_id}@{a}", f"{est_id}@{b}", tipo="transbordo", pasillo=pasillo,
                   saturacion=saturacion)


def estacion(nodo):
    return grafo.nodes[nodo]["estacion"]


def linea(nodo):
    return grafo.nodes[nodo]["linea"]


# =============================================================================
# 3. FUNCIÓN DE COSTE g(n)
# =============================================================================
# g(n) = g(padre) + coste de la arista padre -> n, en minutos:
#   tramo:      (marcha × F_franja × F_clima[vía] + parada(n) × F_franja × F_clima) / 60
#               (en el destino no se suma la parada)
#   transbordo: pasillo + intervalo/2 de la línea nueva + saturación (solo en punta)
#               + penalizaciones que haya pedido el usuario
#   al empezar: espera media en el andén = intervalo/2 de la línea

def minutos(hora):
    """'08:15' -> 495"""
    h, m = hora.split(":")
    return int(h) * 60 + int(m)


def hora_mas(hora, mins):
    """'08:15' + 23.4 min -> '08:38'"""
    total = (minutos(hora) + round(mins)) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def en_servicio(hora):
    return minutos(HORA_APERTURA) <= minutos(hora) < minutos(HORA_CIERRE)


def franja_de(hora, dia="laborable", evento=False):
    """Evento > fin de semana > franja por la hora. Con el metro cerrado se usa 'Apertura'."""
    if evento:
        return EVENTO
    if dia == "fin_de_semana":
        return FIN_DE_SEMANA
    for franja in FRANJAS:
        if minutos(franja[1]) <= minutos(hora) < minutos(franja[2]):
            return franja
    return FRANJAS[0]


def intervalo(franja, lin):
    return franja[5][int(lin[1]) - 1]       # "L2" -> posición 1


def partes_coste(u, v, viaje):
    """Coste de la arista u -> v separado por conceptos (minutos). La suma es el coste."""
    franja, clima = viaje["franja"], CLIMAS[viaje["clima"]]
    partes = {"marcha": 0, "parada": 0, "espera": 0, "transbordo": 0, "penalizacion": 0}
    if u == "INICIO":                                # esperar el primer tren
        partes["espera"] = intervalo(franja, linea(v)) / 2
        return partes
    if v == "FIN":                                   # ya estamos en el destino
        return partes
    arista = grafo.edges[u, v]
    if arista["tipo"] == "tramo":
        f_via = clima[1] if arista["via"] == "elevado" else clima[2]
        partes["marcha"] = arista["segundos"] * franja[3] * f_via / 60
        if estacion(v) != viaje["destino"]:
            parada = PARADA_TRANSBORDO_S if estaciones[estacion(v)]["transbordo"] else PARADA_S
            partes["parada"] = parada * franja[4] * clima[3] / 60
    else:
        partes["transbordo"] = arista["pasillo"] + (arista["saturacion"] if franja[6] else 0)
        partes["espera"] = intervalo(franja, linea(v)) / 2
        if viaje["menos_transbordos"]:
            partes["penalizacion"] += PENALIZACION_TRANSBORDO
        if viaje["accesible"] and not estaciones[estacion(v)]["accesible"]:
            partes["penalizacion"] += PENALIZACION_NO_ACCESIBLE
    return partes


def coste(u, v, viaje):
    return sum(partes_coste(u, v, viaje).values())


# =============================================================================
# 4. HEURÍSTICA h(n)
# =============================================================================
# h(n) = distancia en línea recta (haversine) hasta el destino / V_MAX, en minutos.
# Admisible: la vía nunca es más corta que la línea recta, el tren nunca va a más de V_MAX
#   y el resto del coste (paradas, esperas, transbordos) es >= 0. Nunca sobreestima.
# Consistente: por la desigualdad triangular, h(u) <= d(u,v)/V_MAX + h(v) <= coste(u,v) + h(v).
#   En un transbordo u y v están en el mismo sitio, así que h(u) = h(v).

def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(a))


def h(nodo, viaje):
    if nodo == "FIN":
        return 0.0
    a = estaciones[viaje["origen"] if nodo == "INICIO" else estacion(nodo)]
    b = estaciones[viaje["destino"]]
    return haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) / V_MAX * 60


# =============================================================================
# 5. A*
# =============================================================================
# Se busca de un nodo INICIO a un nodo FIN, que no están en el grafo:
#   INICIO se une a los nodos de la estación de origen (dos si es de transbordo), y
#   los nodos de la estación de destino se unen a FIN con coste 0.
# Así A* elige solo por qué línea salir y en cuál llegar.

def vecinos(nodo, viaje):
    if nodo == "INICIO":
        return [n for n in grafo if estacion(n) == viaje["origen"]]
    lista = list(grafo.neighbors(nodo))
    if estacion(nodo) == viaje["destino"]:
        lista.append("FIN")
    return lista


def a_estrella(viaje, usar_h=True):
    """Devuelve (camino de INICIO a FIN, coste total, nodos expandidos). Sin h es Dijkstra."""
    def f_h(n):
        return h(n, viaje) if usar_h else 0.0

    contador = 0                              # para desempatar en la cola
    abiertos = [(f_h("INICIO"), contador, "INICIO")]
    g = {"INICIO": 0.0}
    padre = {}
    cerrados = set()
    while abiertos:
        _, _, actual = heapq.heappop(abiertos)
        if actual in cerrados:                # entrada vieja de un nodo que ya mejoramos
            continue
        cerrados.add(actual)
        if actual == "FIN":                   # con h consistente, el primero que sale es óptimo
            camino = ["FIN"]
            while camino[-1] in padre:
                camino.append(padre[camino[-1]])
            return camino[::-1], g["FIN"], len(cerrados)
        for vecino in vecinos(actual, viaje):
            if vecino in cerrados:
                continue
            nuevo_g = g[actual] + coste(actual, vecino, viaje)
            if nuevo_g < g.get(vecino, math.inf):
                g[vecino] = nuevo_g
                padre[vecino] = actual
                contador += 1
                heapq.heappush(abiertos, (nuevo_g + f_h(vecino), contador, vecino))
    return None, math.inf, len(cerrados)


# =============================================================================
# 6. CALCULAR LA RUTA (lo que usa la web)
# =============================================================================

def calcular_ruta(origen, destino, hora="08:15", dia="laborable", clima="despejado",
                  evento_masivo=False, minimizar_transbordos=False, accesible=False):
    franja = franja_de(hora, dia, evento_masivo)
    viaje = {"origen": origen, "destino": destino, "franja": franja, "clima": clima,
             "menos_transbordos": minimizar_transbordos, "accesible": accesible}

    avisos = []
    if not en_servicio(hora):
        avisos.append("A esa hora el metro está cerrado (abre de 05:00 a 24:00). "
                      "Te mostramos el trayecto con el primer servicio de la mañana.")
    if CLIMAS[clima][4] in ("Alta", "Muy alta"):
        avisos.append(f"{CLIMAS[clima][0]}: es posible que el servicio se suspenda en algunos "
                      "tramos. Consulta los avisos oficiales de Metrorrey antes de salir.")
    if origen == destino:
        return {"ok": False, "motivo": "El origen y el destino son la misma estación.", "avisos": avisos}

    camino, coste_total, expandidos = a_estrella(viaje)

    # Recorremos el camino sumando el tiempo real (las penalizaciones no son tiempo real,
    # solo sirven para que A* prefiera unas rutas a otras)
    desglose = {"en_tren": 0, "esperas": 0, "transbordos": 0, "penalizaciones": 0}
    tiempo, metros, minuto_de = 0.0, 0, {}
    for u, v in zip(camino, camino[1:]):
        p = partes_coste(u, v, viaje)
        desglose["en_tren"] += p["marcha"] + p["parada"]
        desglose["esperas"] += p["espera"]
        desglose["transbordos"] += p["transbordo"]
        desglose["penalizaciones"] += p["penalizacion"]
        tiempo += sum(p.values()) - p["penalizacion"]
        if v != "FIN":
            minuto_de[v] = tiempo
            if u != "INICIO" and grafo.edges[u, v]["tipo"] == "tramo":
                metros += grafo.edges[u, v]["metros"]
    nodos = camino[1:-1]

    # Pasos: qué hacer en cada estación (subir, pasar, transbordo, bajar)
    pasos = []
    for i, n in enumerate(nodos):
        if i == 0:
            accion = "subir"
        elif i == len(nodos) - 1:
            accion = "bajar"
        elif estacion(nodos[i + 1]) == estacion(n):
            accion = "transbordo"
        elif estacion(nodos[i - 1]) == estacion(n):
            continue                          # segundo nodo del transbordo, ya contado
        else:
            accion = "pasar"
        est = estaciones[estacion(n)]
        pasos.append({"estacion": est["id"], "nombre": est["nombre"], "linea": linea(n),
                      "minuto": round(minuto_de[n], 1), "accion": accion,
                      "lat": est["lat"], "lon": est["lon"]})

    # Segmentos: trozos del viaje dentro de una misma línea
    segmentos = []
    for n in nodos:
        if not segmentos or segmentos[-1]["linea"] != linea(n):
            segmentos.append({"linea": linea(n), "color": COLORES_LINEA[linea(n)],
                              "estaciones": [], "minuto_inicio": minuto_de[n]})
        segmentos[-1]["estaciones"].append(estacion(n))
        segmentos[-1]["minuto_fin"] = minuto_de[n]
    # un segmento de una sola estación es un transbordo en el origen o en el destino: fuera
    segmentos = [s for s in segmentos if len(s["estaciones"]) > 1] or segmentos[:1]
    for s in segmentos:
        s["desde"], s["hasta"] = s["estaciones"][0], s["estaciones"][-1]
        s["num_paradas"] = len(s["estaciones"]) - 1
        orden = orden_linea(s["linea"])
        hacia_el_final = orden.index(s["hasta"]) > orden.index(s["desde"])
        s["direccion"] = estaciones[orden[-1] if hacia_el_final else orden[0]]["nombre"]

    no_accesibles = [p["nombre"] for p in pasos if p["accion"] != "pasar"
                     and not estaciones[p["estacion"]]["accesible"]]
    if accesible and no_accesibles:
        avisos.append("Parte del trayecto no está adaptado para movilidad reducida: las Líneas 1 y 2 "
                      f"no tienen accesibilidad completa ({', '.join(dict.fromkeys(no_accesibles))}).")
    if minutos(hora) + tiempo >= 24 * 60 and en_servicio(hora):
        avisos.append("Cuidado: llegarías después del cierre del metro (24:00).")

    return {
        "ok": True, "modo": "salida",
        "origen": estaciones[origen]["nombre"], "destino": estaciones[destino]["nombre"],
        "tiempo_total_min": round(tiempo, 1), "coste_astar_min": round(coste_total, 2),
        "hora_salida": hora, "hora_llegada": hora_mas(hora, tiempo),
        "num_transbordos": len(segmentos) - 1, "distancia_km": round(metros / 1000, 2),
        "franja": franja[0], "clima": CLIMAS[clima][0],
        "pasos": pasos, "segmentos": segmentos, "avisos": avisos,
        "desglose": {k: round(v, 2) for k, v in desglose.items()},
        "nodos_expandidos": expandidos,
    }


def calcular_ruta_llegando_a(origen, destino, hora_llegada, **opciones):
    """Igual, pero con la hora a la que se quiere LLEGAR. Como el tiempo depende de la hora de
    salida, se prueba una salida y se corrige unas pocas veces hasta que la llegada cuadra."""
    salida = hora_mas(hora_llegada, -30)
    r = calcular_ruta(origen, destino, hora=salida, **opciones)
    for _ in range(4):
        if not r["ok"] or hora_mas(hora_llegada, -r["tiempo_total_min"]) == salida:
            break
        salida = hora_mas(hora_llegada, -r["tiempo_total_min"])
        r = calcular_ruta(origen, destino, hora=salida, **opciones)
    r["modo"] = "llegada"
    return r
