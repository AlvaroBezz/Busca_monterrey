# Pruebas de metro.py. Se ejecutan con: pytest

import itertools

import networkx as nx
import pytest

import metro
from metro import calcular_ruta, estaciones, grafo

ESCENARIOS = [
    dict(hora="08:15"),
    dict(hora="11:00", clima="lluvia_intensa"),
    dict(hora="18:00", minimizar_transbordos=True, accesible=True),
    dict(hora="12:00", dia="fin_de_semana", clima="inundacion", evento_masivo=True),
]


def hacer_viaje(origen, destino, hora="08:15", dia="laborable", clima="despejado",
                evento_masivo=False, minimizar_transbordos=False, accesible=False):
    return {"origen": origen, "destino": destino, "franja": metro.franja_de(hora, dia, evento_masivo),
            "clima": clima, "menos_transbordos": minimizar_transbordos, "accesible": accesible}


# ---------- grafo

def test_tamano_del_grafo():
    assert len(estaciones) == 38
    assert grafo.number_of_nodes() == 41
    assert grafo.number_of_edges() == 41
    assert nx.is_connected(grafo)


def test_transbordos():
    assert sorted(e for e in estaciones if estaciones[e]["transbordo"]) == \
        ["cuauhtemoc", "felix_u_gomez", "general_i_zaragoza"]


def test_cabeceras():
    assert metro.orden_linea("L1")[0] == "talleres" and metro.orden_linea("L1")[-1] == "exposicion"
    assert metro.orden_linea("L2")[0] == "sendero" and metro.orden_linea("L2")[-1] == "general_i_zaragoza"
    assert len(metro.orden_linea("L3")) == 9


def test_lineas_en_obras_no_entran_en_el_grafo():
    assert [l[0] for l in metro.LINEAS_EN_OBRAS] == ["Línea 4", "Línea 6"]
    assert {grafo.nodes[n]["linea"] for n in grafo} == {"L1", "L2", "L3"}


# ---------- heurística

def test_haversine():
    # Madrid - Barcelona: unos 504 km en línea recta
    assert metro.haversine_km(40.4168, -3.7038, 41.3874, 2.1686) == pytest.approx(504, abs=3)


@pytest.mark.parametrize("esc", ESCENARIOS + [dict(hora="21:00", clima="granizo")])
def test_h_consistente_en_todas_las_aristas(esc):
    # h(u) <= coste(u, v) + h(v) para todas las aristas y todos los destinos
    for destino in estaciones:
        viaje = hacer_viaje("talleres", destino, **esc)
        for u, v in itertools.chain(grafo.edges, ((v, u) for u, v in grafo.edges)):
            assert metro.h(u, viaje) <= metro.coste(u, v, viaje) + metro.h(v, viaje) + 1e-9


def test_ningun_tramo_mas_rapido_que_vmax():
    for _, desde, hasta, metros, segundos, _ in metro.TRAMOS:
        a, b = estaciones[desde], estaciones[hasta]
        assert segundos / 60 >= metro.haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) / metro.V_MAX * 60


# ---------- A*

@pytest.mark.parametrize("esc", ESCENARIOS)
def test_astar_igual_que_dijkstra(esc):
    # comparamos con el Dijkstra de NetworkX en los 38 x 37 pares de estaciones
    for origen, destino in itertools.permutations(estaciones, 2):
        viaje = hacer_viaje(origen, destino, **esc)
        dirigido = nx.DiGraph()
        pendientes, vistos = ["INICIO"], {"INICIO"}
        while pendientes:
            u = pendientes.pop()
            for v in metro.vecinos(u, viaje):
                dirigido.add_edge(u, v, peso=metro.coste(u, v, viaje))
                if v not in vistos and v != "FIN":
                    vistos.add(v)
                    pendientes.append(v)
        referencia = nx.dijkstra_path_length(dirigido, "INICIO", "FIN", weight="peso")
        _, coste, expandidos = metro.a_estrella(viaje)
        _, coste_sin_h, expandidos_sin_h = metro.a_estrella(viaje, usar_h=False)
        assert coste == pytest.approx(referencia) and coste_sin_h == pytest.approx(referencia)
        assert expandidos <= expandidos_sin_h


def paradas(r):
    return [p["estacion"] for p in r["pasos"]]


def test_misma_linea():
    r = calcular_ruta("sendero", "universidad")
    assert r["num_transbordos"] == 0
    assert paradas(r) == ["sendero", "santiago_tapia", "san_nicolas", "anahuac", "universidad"]
    assert r["distancia_km"] == pytest.approx(5.794, abs=0.01)


def test_transbordo_en_cuauhtemoc():
    r = calcular_ruta("talleres", "sendero")
    assert r["num_transbordos"] == 1
    assert {"estacion": "cuauhtemoc", "accion": "transbordo"}.items() <= \
        next(p for p in r["pasos"] if p["estacion"] == "cuauhtemoc").items()


def test_l1_a_l3_por_felix_u_gomez():
    r = calcular_ruta("mitras", "hospital_metropolitano")
    assert r["num_transbordos"] == 1
    assert any(p["estacion"] == "felix_u_gomez" and p["accion"] == "transbordo" for p in r["pasos"])


def test_penalizacion_de_transbordos():
    normal = calcular_ruta("mitras", "hospital_metropolitano")
    penalizada = calcular_ruta("mitras", "hospital_metropolitano", minimizar_transbordos=True)
    assert penalizada["desglose"]["penalizaciones"] == 10
    assert penalizada["coste_astar_min"] > normal["coste_astar_min"]


def test_origen_igual_a_destino():
    assert calcular_ruta("central", "central")["ok"] is False


def test_salir_de_una_estacion_de_transbordo():
    r = calcular_ruta("cuauhtemoc", "exposicion")
    assert r["num_transbordos"] == 0 and r["pasos"][0]["linea"] == "L1"


def test_lluvia_y_punta_tardan_mas():
    normal = calcular_ruta("mitras", "hospital_metropolitano", hora="11:00")
    malo = calcular_ruta("mitras", "hospital_metropolitano", hora="08:00", clima="lluvia_intensa")
    assert malo["tiempo_total_min"] > normal["tiempo_total_min"]


def test_fuera_de_horario_avisa():
    r = calcular_ruta("talleres", "exposicion", hora="02:30")
    assert any("cerrado" in a for a in r["avisos"])


def test_llegar_a_una_hora():
    r = metro.calcular_ruta_llegando_a("talleres", "hospital_metropolitano", "09:00")
    assert r["modo"] == "llegada"
    assert abs(metro.minutos(r["hora_llegada"]) - metro.minutos("09:00")) <= 1
