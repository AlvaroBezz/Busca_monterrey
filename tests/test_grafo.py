"""Pruebas de los datos y del grafo de la red."""

import networkx as nx

from metro.datos import cargar_datos
from metro.grafo import construir_grafo, nodos_de_estacion

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
