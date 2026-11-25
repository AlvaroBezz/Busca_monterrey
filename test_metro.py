"""Pruebas de metro.py. Se ejecutan con:  pytest

1. Grafo: tamaño, conexión, transbordos y cabeceras.
2. Heurística: admisible y consistente en todas las aristas y escenarios.
3. A*: mismo coste que Dijkstra de NetworkX en todos los pares, y casos concretos.
"""

import itertools

import networkx as nx
import pytest

from metro import (FIN, INICIO, Escenario, a_estrella, calcular_ruta, calcular_ruta_llegando_a,
                   cargar_datos, construir_grafo, construir_problema, coste_arista, haversine_km,
                   heuristica, lineas_en_obras, nodos_de_estacion)


# ========================================================================================
# 1. GRAFO
# ========================================================================================
# Pruebas de los datos y del grafo de la red.

datos = cargar_datos()
grafo = construir_grafo(datos)


def test_datos_completos():
    assert len(datos.estaciones) == 38
    assert len(datos.tramos) == 38
    assert "penitenciaria" in datos.estaciones          # faltaba en el grafo inicial
    for e in datos.estaciones.values():
        assert e["lat"] is not None and e["lon"] is not None


def test_tamano_del_grafo():
    assert grafo.number_of_nodes() == 41                 # 38 estaciones + 3 desdoblamientos
    assert grafo.number_of_edges() == 41                 # 38 tramos + 3 transbordos
    transbordos = [e for e in grafo.edges(data=True) if e[2]["tipo_arista"] == "transbordo"]
    assert len(transbordos) == 3


def test_grafo_conexo():
    assert nx.is_connected(grafo)


def test_estaciones_de_transbordo():
    for est, lineas in (("cuauhtemoc", {"L1", "L2"}),
                        ("general_i_zaragoza", {"L2", "L3"}),
                        ("felix_u_gomez", {"L1", "L3"})):
        nodos = nodos_de_estacion(grafo, est)
        assert {grafo.nodes[n]["linea"] for n in nodos} == lineas


def test_cabeceras_de_las_lineas():
    assert datos.orden_linea("L1")[0] == "talleres"
    assert datos.orden_linea("L1")[-1] == "exposicion"
    assert datos.orden_linea("L2")[0] == "sendero"
    assert datos.orden_linea("L2")[-1] == "general_i_zaragoza"
    assert datos.orden_linea("L3")[0] == "hospital_metropolitano"
    assert datos.orden_linea("L3")[-1] == "general_i_zaragoza"


# ========================================================================================
# 2. HEURÍSTICA
# ========================================================================================
# Pruebas de h(n): valores básicos, admisibilidad y consistencia.

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


# ========================================================================================
# 3. A*
# ========================================================================================
# Pruebas del A* propio: siempre da el mismo coste que Dijkstra de NetworkX.

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
    assert any("cerrado" in a for a in r["avisos"])


def test_llegar_a_una_hora():
    r = calcular_ruta_llegando_a("talleres", "hospital_metropolitano", "09:00")
    assert r["modo"] == "llegada"
    # La llegada calculada cae como mucho un minuto alrededor de la hora pedida
    llegada = int(r["hora_llegada"][:2]) * 60 + int(r["hora_llegada"][3:])
    assert abs(llegada - 9 * 60) <= 1


def test_lineas_en_obras_solo_en_el_mapa():
    """Las líneas 4 y 6 se dibujan, pero no entran en el grafo de cálculo."""
    obras = {l["id"]: l for l in lineas_en_obras()}
    assert set(obras) == {"L4", "L6"}
    assert all(len(l["estaciones"]) >= 2 for l in obras.values())
    lineas_grafo = {d["linea"] for _, d in construir_grafo(cargar_datos()).nodes(data=True)}
    assert lineas_grafo == {"L1", "L2", "L3"}
