"""Convierte la hoja de cálculo de tiempos de Metrorrey en los JSON que usa la app.

Uso (desde la raíz del repositorio):
    python scripts/excel_a_json.py

Lee:  data/fuentes/Metrorrey_tiempos_entre_estaciones.xlsx
Crea: data/tramos.json, data/estaciones.json y data/factores.json

- Los tiempos y distancias de cada tramo salen de la hoja "Tramos (base)".
- Los factores por franja horaria y por clima salen de la hoja "Parámetros".
- Las coordenadas NO están en el Excel: se guardan en el diccionario
  COORDENADAS de este script, con la fuente de cada una.
Al final se valida la red (38 estaciones, 38 tramos, líneas continuas).
"""

import json
import sys
import unicodedata
from pathlib import Path

import openpyxl

RAIZ = Path(__file__).resolve().parent.parent
EXCEL = RAIZ / "data" / "fuentes" / "Metrorrey_tiempos_entre_estaciones.xlsx"
CARPETA_DATOS = RAIZ / "data"

# Estaciones de transbordo y líneas que se cruzan en cada una
TRANSBORDOS = {
    "cuauhtemoc": ["L1", "L2"],
    "general_i_zaragoza": ["L2", "L3"],
    "felix_u_gomez": ["L1", "L3"],
}

# --- Coordenadas (lat, lon) y su fuente -----------------------------------
FUENTE_WIKI_EN = "Wikipedia (en), 'List of Metrorrey stations', consultada 25/11/2026"
FUENTE_WIKI_ES = "Wikipedia (es), artículo de la estación, consultada 25/11/2026"
FUENTE_WIKIDATA = "Wikidata (propiedad P625), consultada 25/11/2026"

COORDENADAS = {
    # Línea 1
    "talleres": (25.75389, -100.36528, FUENTE_WIKI_EN),
    "san_bernabe": (25.74833, -100.36167, FUENTE_WIKI_EN),
    "unidad_modelo": (25.74194, -100.35500, FUENTE_WIKI_EN),
    "aztlan": (25.73222, -100.34750, FUENTE_WIKI_EN),
    "penitenciaria": (25.72333, -100.34250, FUENTE_WIKI_EN),
    "alfonso_reyes": (25.71611, -100.34250, FUENTE_WIKI_EN),
    "mitras": (25.70556, -100.34250, FUENTE_WIKI_EN),
    # En la lista de Wikipedia (en) Simón Bolívar tiene las mismas coordenadas
    # que Mitras (error de la fuente). Se usa el artículo de Wikipedia (es).
    "simon_bolivar": (25.69904, -100.34324, FUENTE_WIKI_ES),
    "hospital": (25.69194, -100.34417, FUENTE_WIKI_EN),
    "edison": (25.68694, -100.33361, FUENTE_WIKI_EN),
    "central": (25.68694, -100.32444, FUENTE_WIKI_EN),
    "cuauhtemoc": (25.68611, -100.31694, FUENTE_WIKI_EN),
    "del_golfo": (25.68512, -100.30663, FUENTE_WIKI_EN),
    "felix_u_gomez": (25.68389, -100.29667, FUENTE_WIKI_EN),
    "parque_fundidora": (25.68361, -100.28806, FUENTE_WIKI_EN),
    "y_griega": (25.68333, -100.27933, FUENTE_WIKI_EN),
    "eloy_cavazos": (25.68000, -100.26417, FUENTE_WIKI_EN),
    "lerdo_de_tejada": (25.67972, -100.25278, FUENTE_WIKI_EN),
    "exposicion": (25.67944, -100.24556, FUENTE_WIKI_EN),
    # Línea 2
    "sendero": (25.76861, -100.29278, FUENTE_WIKI_EN),
    "santiago_tapia": (25.75926, -100.29568, FUENTE_WIKI_EN),
    "san_nicolas": (25.75262, -100.29805, FUENTE_WIKI_EN),
    "anahuac": (25.74028, -100.30250, FUENTE_WIKI_EN),
    "universidad": (25.72444, -100.30833, FUENTE_WIKI_EN),
    "ninos_heroes": (25.71722, -100.31111, FUENTE_WIKI_EN),
    "regina": (25.70790, -100.31410, FUENTE_WIKI_EN),
    "general_anaya": (25.69694, -100.31667, FUENTE_WIKI_EN),
    "alameda": (25.67694, -100.31833, FUENTE_WIKI_EN),
    "fundadores": (25.67267, -100.31970, FUENTE_WIKI_EN),
    "padre_mier": (25.66888, -100.31544, FUENTE_WIKI_EN),
    "general_i_zaragoza": (25.66778, -100.31028, FUENTE_WIKI_EN),
    # Línea 3 (la lista de Wikipedia (en) no trae coordenadas de la L3)
    "hospital_metropolitano": (25.71376, -100.27359, FUENTE_WIKIDATA),
    "los_angeles": (25.70812, -100.28171, FUENTE_WIKIDATA),
    "ruiz_cortines": (25.70375, -100.28796, FUENTE_WIKIDATA),
    "colonia_moderna": (25.70046, -100.29260, FUENTE_WIKIDATA),
    "metalurgicos": (25.69102, -100.29582, FUENTE_WIKIDATA),
    "colonia_obrera": (25.67789, -100.29766, FUENTE_WIKIDATA),
    "santa_lucia": (25.67140, -100.29855, FUENTE_WIKIDATA),
}

# Otros nombres con los que se conoce una estación
ALIAS = {
    "parque_fundidora": ["Arena Monterrey"],
    "general_i_zaragoza": ["Gral. I. Zaragoza", "General Ignacio Zaragoza"],
    "colonia_moderna": ["Col. Moderna"],
    "colonia_obrera": ["Col. Obrera"],
}

# Accesibilidad por línea: el director de Metrorrey admitió en 2023 que L1 y L2
# no son aptas para personas con discapacidad (abcnoticias.mx, 18/10/2023).
# La L3 es de 2021 y se considera accesible.
ACCESIBLE_POR_LINEA = {"L1": False, "L2": False, "L3": True}

# Nombres de los climas de la hoja "Parámetros" → clave corta y etiqueta
CLIMAS = {
    "Despejado": ("despejado", "Despejado", "wb_sunny"),
    "Lluvia ligera": ("lluvia_ligera", "Lluvia ligera", "grain"),
    "Lluvia intensa": ("lluvia_intensa", "Lluvia intensa", "umbrella"),
    "Tormenta": ("tormenta", "Tormenta eléctrica", "thunderstorm"),
    "Granizo": ("granizo", "Granizo", "ac_unit"),
    "Inundación": ("inundacion", "Inundación / huracán", "flood"),
    "Calor": ("calor_extremo", "Calor extremo", "local_fire_department"),
    "Frío": ("helada", "Frío extremo / helada", "severe_cold"),
    "Niebla": ("niebla", "Niebla densa", "foggy"),
    "Viento": ("viento_fuerte", "Viento fuerte", "air"),
}


def crear_id(nombre):
    """'Félix U. Gómez' → 'felix_u_gomez' (minúsculas, sin tildes ni signos)."""
    sin_tildes = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    limpio = "".join(c if c.isalnum() else " " for c in sin_tildes.lower())
    return "_".join(limpio.split())


def leer_tramos(libro):
    """Lee la hoja 'Tramos (base)' y devuelve la lista de tramos y los nombres oficiales.

    La parada en la estación de llegada NO se guarda en el tramo: en el Excel va
    asociada al sentido de ida, pero el grafo se recorre en los dos sentidos. Por eso
    cada estación tiene su propia parada (20 s, o 35 s en las de transbordo).
    """
    hoja = libro["Tramos (base)"]
    tramos = []
    nombres = {}          # id → nombre oficial (tal como aparece en el Excel)
    for fila in hoja.iter_rows(min_row=3, values_only=True):
        linea, desde, hasta = fila[0], fila[1], fila[2]
        if linea not in ("L1", "L2", "L3"):
            continue  # se saltan las filas de "Total ..." y las notas
        distancia_m, tipo, marcha_s, confianza = fila[3], fila[5], fila[6], fila[11]
        id_desde, id_hasta = crear_id(desde), crear_id(hasta)
        nombres[id_desde], nombres[id_hasta] = desde, hasta
        tramos.append({
            "linea": linea,
            "desde": id_desde,
            "hasta": id_hasta,
            "distancia_m": int(distancia_m),
            "tipo": "subterraneo" if str(tipo).lower().startswith("subter") else "elevado",
            "marcha_s": int(marcha_s),
            "confianza": "baja" if str(confianza).lower().startswith("baja") else "media",
        })
    return tramos, nombres


def leer_factores(libro):
    """Lee franjas horarias y clima de la hoja 'Parámetros'."""
    hoja = libro["Parámetros"]
    filas = [f for f in hoja.iter_rows(values_only=True)]

    def valor_parametro(texto):
        for f in filas:
            if f[0] and str(f[0]).startswith(texto):
                return f[1]
        raise KeyError(texto)

    franjas = []
    claves_franja = {
        "Apertura": ("apertura", "05:00", "06:30", False),
        "Punta mañana": ("punta_manana", "06:30", "09:30", True),
        "Valle mañana": ("valle_manana", "09:30", "13:00", False),
        "Mediodía": ("mediodia", "13:00", "16:30", False),
        "Punta tarde": ("punta_tarde", "16:30", "20:00", True),
        "Noche": ("noche", "20:00", "22:00", False),
        "Cierre": ("cierre", "22:00", "24:00", False),
        "Sábado": ("fin_de_semana", None, None, False),
        "Evento masivo": ("evento_masivo", None, None, True),
    }
    clima = {}
    for f in filas:
        nombre = str(f[0] or "")
        for prefijo, (clave, inicio, fin, es_punta) in claves_franja.items():
            if nombre.startswith(prefijo) and isinstance(f[2], (int, float)):
                franjas.append({
                    "clave": clave,
                    "nombre": nombre,
                    "hora_inicio": inicio,
                    "hora_fin": fin,
                    "factor_marcha": f[2],
                    "factor_parada": f[3],
                    "intervalo_min": {"L1": f[4], "L2": f[5], "L3": f[6]},
                    "es_punta": es_punta,
                })
        for prefijo, (clave, etiqueta, icono) in CLIMAS.items():
            if nombre.startswith(prefijo) and isinstance(f[1], (int, float)):
                clima[clave] = {
                    "nombre": etiqueta,
                    "icono": icono,
                    "factor_marcha_elevado": f[1],
                    "factor_marcha_subterraneo": f[2],
                    "factor_parada": f[3],
                    "riesgo_suspension": f[4],
                }

    return {
        "_comentario": (
            "Parámetros de g(n) y h(n). Los factores proceden de la hoja 'Parámetros' "
            "del Excel del grupo (hipótesis de partida, no publicadas por Metrorrey). "
            "Se pueden editar a mano; la app los lee al arrancar."
        ),
        "v_max_kmh": 80,
        "_v_max": (
            "Velocidad máxima real de los trenes. El Excel calibra 70 km/h de crucero, "
            "pero h(n) necesita la máxima para no sobreestimar nunca (admisible)."
        ),
        "parada_base_s": valor_parametro("Parada base"),
        "parada_transbordo_s": valor_parametro("Parada base") + valor_parametro("Tiempo extra en estación de transbordo"),
        "horario_servicio": {"inicio": "05:00", "fin": "24:00"},
        "franjas": franjas,
        "clima": clima,
        "transbordos": {
            "_comentario": (
                "pasillo_min: caminar entre andenes (supuesto dentro del rango 3-6 min del Excel). "
                "saturacion_punta_min: tiempo extra en hora punta o evento (el grupo encontró 3-7 min "
                "en Cuauhtémoc y Zaragoza)."
            ),
            "cuauhtemoc": {"pasillo_min": 4, "saturacion_punta_min": 5},
            "general_i_zaragoza": {"pasillo_min": 3, "saturacion_punta_min": 5},
            "felix_u_gomez": {"pasillo_min": 3, "saturacion_punta_min": 2},
        },
        "penalizacion_minimizar_transbordos_min": 10,
        "penalizacion_no_accesible_min": 15,
    }


def construir_estaciones(tramos, nombres, factores):
    """Crea la lista de estaciones con coordenadas, tipo de andén y accesibilidad."""
    lineas_de = {}
    tipos_de = {}  # (estación, línea) → tipos de los tramos que tocan esa estación
    for t in tramos:
        for est in (t["desde"], t["hasta"]):
            lineas_de.setdefault(est, [])
            if t["linea"] not in lineas_de[est]:
                lineas_de[est].append(t["linea"])
            tipos_de.setdefault((est, t["linea"]), set()).add(t["tipo"])

    estaciones = []
    for id_est, nombre in nombres.items():
        lat, lon, fuente = COORDENADAS[id_est]
        tipo_por_linea = {}
        dudosa = False
        for linea in lineas_de[id_est]:
            tipos = tipos_de[(id_est, linea)]
            if len(tipos) == 1:
                tipo_por_linea[linea] = tipos.pop()
            else:
                # Entre un tramo elevado y uno subterráneo: es la estación donde
                # la vía baja (rampa). No sabemos si el andén está arriba o abajo.
                tipo_por_linea[linea] = "transicion"
                dudosa = True
        es_transbordo = id_est in TRANSBORDOS
        estaciones.append({
            "id": id_est,
            "nombre": nombre,
            "alias": ALIAS.get(id_est, []),
            "lineas": lineas_de[id_est],
            "lat": lat,
            "lon": lon,
            "tipo_por_linea": tipo_por_linea,
            "tipo_dudoso": dudosa,
            "transbordo": es_transbordo,
            "parada_s": factores["parada_transbordo_s"] if es_transbordo else factores["parada_base_s"],
            # Una estación es accesible solo si lo son todas sus líneas
            "accesible": all(ACCESIBLE_POR_LINEA[l] for l in lineas_de[id_est]),
            "aprox": False,
            "fuente_coordenadas": fuente,
        })
    return estaciones


def validar(estaciones, tramos):
    """Comprueba que la red está completa y bien formada. Lanza AssertionError si no."""
    ids = {e["id"] for e in estaciones}
    assert len(estaciones) == 38, f"Se esperaban 38 estaciones y hay {len(estaciones)}"
    assert len(tramos) == 38, f"Se esperaban 38 tramos y hay {len(tramos)}"
    for t in tramos:
        assert t["desde"] in ids and t["hasta"] in ids, f"Tramo con estación desconocida: {t}"
    # Cada línea debe ser una cadena: el 'hasta' de un tramo es el 'desde' del siguiente
    for linea in ("L1", "L2", "L3"):
        de_linea = [t for t in tramos if t["linea"] == linea]
        for anterior, siguiente in zip(de_linea, de_linea[1:]):
            assert anterior["hasta"] == siguiente["desde"], f"{linea} no es continua en {anterior['hasta']}"
    for e in estaciones:
        assert e["lat"] is not None and e["lon"] is not None, f"Falta coordenada de {e['id']}"


def main():
    libro = openpyxl.load_workbook(EXCEL, data_only=True)
    tramos, nombres = leer_tramos(libro)
    factores = leer_factores(libro)
    estaciones = construir_estaciones(tramos, nombres, factores)
    validar(estaciones, tramos)

    for nombre_fichero, contenido in (
        ("tramos.json", tramos),
        ("estaciones.json", estaciones),
        ("factores.json", factores),
    ):
        with open(CARPETA_DATOS / nombre_fichero, "w", encoding="utf-8") as f:
            json.dump(contenido, f, ensure_ascii=False, indent=2)

    print("Datos generados correctamente")
    for linea in ("L1", "L2", "L3"):
        n = sum(1 for t in tramos if t["linea"] == linea)
        km = sum(t["distancia_m"] for t in tramos if t["linea"] == linea) / 1000
        print(f"  {linea}: {n} tramos, {km:.3f} km")
    print(f"  Estaciones: {len(estaciones)} · Tramos: {len(tramos)}")
    print(f"  Franjas horarias: {len(factores['franjas'])} · Climas: {len(factores['clima'])}")
    dudosas = [e["nombre"] for e in estaciones if e["tipo_dudoso"]]
    if dudosas:
        print(f"  Aviso: andén elevado/subterráneo dudoso en: {', '.join(dudosas)}")


if __name__ == "__main__":
    sys.exit(main())
