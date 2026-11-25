"""Pruebas de h(n): valores básicos, admisibilidad y consistencia."""

import itertools

import pytest

from metro.coste import Escenario, coste_arista
from metro.datos import cargar_datos
from metro.grafo import construir_grafo
from metro.heuristica import haversine_km, heuristica

datos = cargar_datos()
grafo = construir_grafo(datos)

HORAS = ["05:30", "08:00", "11:00", "14:00", "18:00", "21:00", "23:00"]
CLIMAS = list(datos.factores["clima"])


def escenarios_de_prueba():
    """Todas las franjas (horas + fin de semana + evento) × todos los climas."""
    for hora, clima in itertools.product(HORAS, CLIMAS):
        yield Escenario(hora=hora, clima=clima)
    for clima in CLIMAS:
        yield Escenario(dia="fin_de_semana", clima=clima)
        yield Escenario(evento_masivo=True, clima=clima)


def test_haversine_conocida():
    # Cuauhtémoc → Félix U. Gómez: unos 2,1 km en línea recta
    c, f = datos.estaciones["cuauhtemoc"], datos.estaciones["felix_u_gomez"]
    assert haversine_km(c["lat"], c["lon"], f["lat"], f["lon"]) == pytest.approx(2.03, abs=0.1)


def test_h_cero_en_destino_y_no_negativa():
    for destino in datos.estaciones:
        assert heuristica(datos, destino, destino) == 0
        for est in datos.estaciones:
            assert heuristica(datos, est, destino) >= 0


def test_consistencia_en_todas_las_aristas():
    """h(u) ≤ coste(u, v) + h(v) en ambos sentidos, para todo destino y escenario."""
    fallos = []
    for escenario in escenarios_de_prueba():
        for destino in datos.estaciones:
            for u, v in grafo.edges():
                for a, b in ((u, v), (v, u)):
                    h_a = heuristica(datos, grafo.nodes[a]["estacion_id"], destino)
                    h_b = heuristica(datos, grafo.nodes[b]["estacion_id"], destino)
                    c = coste_arista(grafo, a, b, datos, escenario, destino)
                    if h_a > c + h_b + 1e-9:
                        fallos.append((a, b, destino, escenario))
    assert not fallos, f"{len(fallos)} aristas no cumplen la consistencia, p. ej. {fallos[:3]}"


def test_tramo_nunca_mas_rapido_que_vmax():
    """El tiempo de marcha de cada tramo es ≥ la línea recta a 80 km/h (base de la admisibilidad)."""
    v = datos.factores["v_max_kmh"]
    for t in datos.tramos:
        a, b = datos.estaciones[t["desde"]], datos.estaciones[t["hasta"]]
        minimo_s = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) / v * 3600
        assert t["marcha_s"] >= minimo_s, f"{t['desde']}→{t['hasta']}"
