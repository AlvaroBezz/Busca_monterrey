"""Función heurística h(n): estimación optimista del tiempo que falta hasta el destino.

    h(n) = distancia_haversine(n, destino) / V_max          (en minutos)

con V_max = 80 km/h (velocidad máxima de los trenes de Metrorrey; data/factores.json).

¿Por qué es ADMISIBLE (h(n) ≤ h*(n), nunca sobreestima)?
    1. La vía nunca es más corta que la línea recta entre dos puntos, así que la
       distancia que de verdad recorre el tren es ≥ la distancia haversine.
    2. El tren nunca va más rápido que V_max, así que tarda como mínimo
       distancia / V_max en recorrerla.
    3. Todo lo demás que suma g(n) (paradas, esperas, transbordos, penalizaciones)
       es ≥ 0, y los factores de marcha por franja y clima son todos ≥ 1.
    Por tanto el coste real que falta siempre es ≥ h(n).

¿Por qué es CONSISTENTE (h(u) ≤ coste(u, v) + h(v) para toda arista u → v)?
    Por la desigualdad triangular: d(u, destino) ≤ d(u, v) + d(v, destino).
    Dividiendo entre V_max: h(u) ≤ d(u, v)/V_max + h(v) ≤ coste(u, v) + h(v),
    porque el tren tarda al menos d(u, v)/V_max en ir de u a v.
    En un transbordo u y v están en la misma estación: d(u, v) = 0 y h(u) = h(v).
    Que la heurística sea consistente garantiza que A* no tiene que reabrir nodos
    ya cerrados y que el primer camino que llega al destino es el óptimo.

Las pruebas (tests/test_heuristica.py) comprueban la consistencia en TODAS las
aristas, para todos los destinos, franjas horarias y climas.
"""

import math

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
