"""Pruebas del A* propio: siempre da el mismo coste que Dijkstra de NetworkX."""

import networkx as nx
import pytest

from metro.astar import FIN, INICIO, a_estrella, construir_problema
from metro.coste import Escenario
from metro.datos import cargar_datos
from metro.grafo import construir_grafo
from metro.ruta import calcular_ruta

datos = cargar_datos()
grafo = construir_grafo(datos)

ESCENARIOS = [
    Escenario(),                                                     # punta mañana, despejado
    Escenario(hora="11:00", clima="lluvia_intensa"),
    Escenario(hora="18:00", minimizar_transbordos=True, accesible=True),
    Escenario(dia="fin_de_semana", clima="inundacion", evento_masivo=True),
]


@pytest.mark.parametrize("escenario", ESCENARIOS)
def test_astar_igual_que_dijkstra_en_todos_los_pares(escenario):
    for origen in datos.estaciones:
        for destino in datos.estaciones:
            if origen == destino:
                continue
            problema = construir_problema(grafo, datos, origen, destino, escenario)
            mio = a_estrella(problema)
            sin_h = a_estrella(problema, usar_heuristica=False)
            referencia = nx.dijkstra_path_length(problema, INICIO, FIN, weight="peso")
            assert mio.encontrado
            assert mio.coste_total_min == pytest.approx(referencia, abs=1e-6)
            assert sin_h.coste_total_min == pytest.approx(referencia, abs=1e-6)
            assert mio.nodos_expandidos <= sin_h.nodos_expandidos


def nombres(ruta):
    return [p["estacion"] for p in ruta["pasos"]]


def test_misma_linea_sin_transbordo():
    r = calcular_ruta("sendero", "universidad")
    assert r["num_transbordos"] == 0
    assert nombres(r) == ["sendero", "santiago_tapia", "san_nicolas", "anahuac", "universidad"]
    assert r["distancia_km"] == pytest.approx(5.794, abs=0.01)


def test_un_transbordo_por_cuauhtemoc():
    r = calcular_ruta("talleres", "sendero")
    assert r["num_transbordos"] == 1
    assert any(p["estacion"] == "cuauhtemoc" and p["accion"] == "transbordo" for p in r["pasos"])


def test_l1_a_l3_pasa_por_felix_u_gomez():
    r = calcular_ruta("mitras", "hospital_metropolitano")
    assert r["num_transbordos"] == 1
    assert any(p["estacion"] == "felix_u_gomez" and p["accion"] == "transbordo" for p in r["pasos"])


def test_minimizar_transbordos_suma_penalizacion():
    normal = calcular_ruta("mitras", "hospital_metropolitano")
    penalizada = calcular_ruta("mitras", "hospital_metropolitano", minimizar_transbordos=True)
    assert penalizada["desglose"]["penalizaciones"] == 10
    assert penalizada["coste_astar_min"] > normal["coste_astar_min"]


def test_origen_igual_a_destino():
    r = calcular_ruta("central", "central")
    assert r["ok"] is False


def test_estacion_de_transbordo_como_origen():
    r = calcular_ruta("cuauhtemoc", "exposicion")
    assert r["num_transbordos"] == 0
    assert r["pasos"][0]["linea"] == "L1"


def test_lluvia_y_punta_tardan_mas():
    base = calcular_ruta("mitras", "hospital_metropolitano", hora="11:00")
    malo = calcular_ruta("mitras", "hospital_metropolitano", hora="08:00", clima="lluvia_intensa")
    assert malo["tiempo_total_min"] > base["tiempo_total_min"]


def test_fuera_de_horario_avisa():
    r = calcular_ruta("talleres", "exposicion", hora="02:00")
    assert any("horario" in a for a in r["avisos"])
