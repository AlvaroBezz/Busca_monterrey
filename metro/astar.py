"""Algoritmo A* programado a mano (sin nx.astar_path ni nx.shortest_path).

Se hace en dos pasos:

1. construir_problema(): a partir del grafo de la red y del escenario del usuario
   crea un grafo DIRIGIDO con el coste de cada arista ya calculado con g (coste.py).
   Es dirigido porque el coste no es simétrico: al llegar a una estación se suma su
   parada (salvo si es el destino) y en un transbordo se espera al tren de la línea
   a la que se cambia.
   Como una estación de transbordo tiene dos nodos, se añaden dos nodos virtuales:
     - INICIO, unido a cada nodo de la estación origen con coste = espera inicial
       (intervalo / 2 de esa línea);
     - FIN, al que se llega desde cada nodo de la estación destino con coste 0.
   Así A* busca siempre de INICIO a FIN y elige solo la línea por la que salir.

2. a_estrella(): el algoritmo clásico, con
     abiertos  = cola de prioridad (heapq) ordenada por f = g + h
     cerrados  = conjunto de nodos ya expandidos
     g, padre  = diccionarios con el mejor coste conocido y de dónde venimos
   Guarda una TRAZA con cada expansión (nodo, g, h, f, tamaño de la frontera)
   para enseñarla en la interfaz y explicarla en la defensa.
   Con usar_heuristica=False, h = 0 y el algoritmo es exactamente Dijkstra.
"""

import heapq
import itertools
from dataclasses import dataclass, field

import networkx as nx

from metro.coste import desglose_arista, espera_inicial
from metro.grafo import nodos_de_estacion
from metro.heuristica import heuristica

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
