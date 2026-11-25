"""Función de coste g(n): cuánto cuesta (en minutos) recorrer cada arista.

g(n) = g(padre) + coste(padre, n)                       (apartado 3.2.A de la memoria)

Coste de una arista de TRAMO u → v (tren que va de una estación a la siguiente):
    marcha  = marcha_s × F_marcha_franja × F_marcha_clima[tipo de vía]
    parada  = parada_s(v) × F_parada_franja × F_parada_clima      (0 si v es el destino)
    coste   = (marcha + parada) / 60   → minutos

Coste de una arista de TRANSBORDO (cambio de línea dentro de la misma estación):
    coste = pasillo_min                         (caminar entre andenes)
          + intervalo_min[línea nueva] / 2      (espera media al siguiente tren)
          + saturacion_punta_min                (solo en hora punta o evento masivo)
          + penalización por minimizar transbordos   (si el usuario lo pide)
          + penalización no accesible                 (si pide ruta accesible y la estación no lo es)

Al salir del origen se suma además la espera inicial = intervalo / 2 de la línea.

Todos los parámetros están en data/factores.json (sacados del Excel del grupo).
"""

from dataclasses import dataclass

TIPOS_DIA = ("laborable", "fin_de_semana")


@dataclass
class Escenario:
    """Condiciones del viaje elegidas por el usuario en la interfaz."""
    hora: str = "08:15"                 # "HH:MM"
    dia: str = "laborable"              # "laborable" o "fin_de_semana"
    clima: str = "despejado"            # clave de factores["clima"]
    evento_masivo: bool = False
    minimizar_transbordos: bool = False
    accesible: bool = False


def minutos_del_dia(hora):
    """'08:15' → 495."""
    horas, minutos = hora.split(":")
    return int(horas) * 60 + int(minutos)


def en_horario_de_servicio(hora, factores):
    """True si a esa hora circula el metro (05:00–24:00)."""
    inicio = minutos_del_dia(factores["horario_servicio"]["inicio"])
    fin = minutos_del_dia(factores["horario_servicio"]["fin"])
    return inicio <= minutos_del_dia(hora) < fin


def franja_de(escenario, factores):
    """Devuelve la franja horaria que se aplica al escenario.

    Prioridad: evento masivo > fin de semana/festivo > franja según la hora.
    Fuera del horario de servicio (00:00–05:00) se usa 'Apertura', que es el
    primer servicio que saldría (la interfaz avisa al usuario).
    """
    por_clave = {f["clave"]: f for f in factores["franjas"]}
    if escenario.evento_masivo:
        return por_clave["evento_masivo"]
    if escenario.dia == "fin_de_semana":
        return por_clave["fin_de_semana"]
    minuto = minutos_del_dia(escenario.hora)
    for f in factores["franjas"]:
        if f["hora_inicio"] is None:
            continue
        if minutos_del_dia(f["hora_inicio"]) <= minuto < minutos_del_dia(f["hora_fin"]):
            return f
    return por_clave["apertura"]


def espera_inicial(linea, escenario, factores):
    """Minutos de espera media en el andén del origen: la mitad del intervalo."""
    return franja_de(escenario, factores)["intervalo_min"][linea] / 2


def desglose_arista(grafo, u, v, datos, escenario, destino_id):
    """Coste de ir de u a v, separado por conceptos (todo en minutos).

    Devuelve un dict con: marcha, parada, pasillo, espera, saturacion, penalizacion.
    La suma de todos los valores es el coste de la arista.
    """
    factores = datos.factores
    franja = franja_de(escenario, factores)
    clima = factores["clima"][escenario.clima]
    arista = grafo.edges[u, v]
    partes = {"marcha": 0.0, "parada": 0.0, "pasillo": 0.0, "espera": 0.0,
              "saturacion": 0.0, "penalizacion": 0.0}

    if arista["tipo_arista"] == "tramo":
        f_clima_marcha = clima[f"factor_marcha_{arista['tipo_via']}"]
        partes["marcha"] = arista["marcha_s"] * franja["factor_marcha"] * f_clima_marcha / 60
        estacion_llegada = grafo.nodes[v]["estacion_id"]
        if estacion_llegada != destino_id:
            parada_s = datos.estaciones[estacion_llegada]["parada_s"]
            partes["parada"] = parada_s * franja["factor_parada"] * clima["factor_parada"] / 60
    else:  # transbordo
        linea_nueva = grafo.nodes[v]["linea"]
        partes["pasillo"] = arista["pasillo_min"]
        partes["espera"] = franja["intervalo_min"][linea_nueva] / 2
        if franja["es_punta"]:
            partes["saturacion"] = arista["saturacion_punta_min"]
        if escenario.minimizar_transbordos:
            partes["penalizacion"] += factores["penalizacion_minimizar_transbordos_min"]
        if escenario.accesible and not datos.estaciones[arista["estacion"]]["accesible"]:
            partes["penalizacion"] += factores["penalizacion_no_accesible_min"]
    return partes


def coste_arista(grafo, u, v, datos, escenario, destino_id):
    """Coste total (minutos) de recorrer la arista u → v. Siempre ≥ 0."""
    return sum(desglose_arista(grafo, u, v, datos, escenario, destino_id).values())
