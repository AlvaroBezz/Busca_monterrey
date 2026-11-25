"""Construcción del grafo de la red de Metrorrey con NetworkX.

Decisión de diseño (apartado 3.1 de la memoria): cada estación se representa con
UN NODO POR LÍNEA, con id "estacion@linea" (por ejemplo "cuauhtemoc@L1").
- Las estaciones normales tienen un único nodo (p. ej. "talleres@L1").
- Las tres estaciones de transbordo tienen dos nodos, unidos por una arista de
  transbordo. Así cambiar de línea es una arista más con su propio coste.

Resultado: 38 estaciones + 3 desdoblamientos = 41 nodos;
38 aristas de tramo + 3 de transbordo = 41 aristas.
NetworkX solo guarda la estructura: el A* está programado a mano en metro/astar.py.
"""

import networkx as nx


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
