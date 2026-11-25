"""Carga de los datos de la red (los JSON generados por scripts/excel_a_json.py)."""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CARPETA_DATOS = Path(__file__).resolve().parent.parent / "data"

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


def _leer_json(nombre):
    with open(CARPETA_DATOS / nombre, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def cargar_datos():
    """Lee los tres JSON una sola vez y devuelve un DatosMetro."""
    estaciones = {e["id"]: e for e in _leer_json("estaciones.json")}
    return DatosMetro(
        estaciones=estaciones,
        tramos=_leer_json("tramos.json"),
        factores=_leer_json("factores.json"),
    )
