# Material para la memoria

Datos sacados del código tal como está en este repositorio (cifras obtenidas ejecutando
`metro/ruta.py`). Si se cambian los parámetros de `data/factores.json`, hay que volver a
calcularlas.

## 3.1 Gestión topológica de los transbordos

Cada estación se representa con un nodo por línea (`estacion@linea`). Las tres estaciones de
transbordo (Cuauhtémoc, General I. Zaragoza y Félix U. Gómez) tienen por tanto dos nodos,
unidos por una arista de transbordo. El grafo tiene **41 nodos** (38 estaciones + 3
desdoblamientos) y **41 aristas** (38 tramos + 3 transbordos).

Para que A\* pueda empezar o terminar en una estación de transbordo sin elegir de antemano la
línea, se añaden dos nodos virtuales: INICIO (unido a los nodos de la estación origen con
coste = espera media del tren de esa línea) y FIN (al que se llega desde los nodos de la
estación destino con coste 0).

## 3.1 Recopilación y estructuración de datos

- Distancias y tiempos de marcha de los 38 tramos: hoja de cálculo del grupo
  (`Metrorrey_tiempos_entre_estaciones.xlsx`, hoja «Tramos (base)»).
- Factores por franja horaria y meteorología: misma hoja, pestaña «Parámetros».
- Coordenadas: Wikipedia «List of Metrorrey stations» (L1 y L2), Wikidata P625 (L3) y
  Wikipedia en español (Simón Bolívar, porque la lista en inglés repite las de Mitras).
- Formato: tres ficheros JSON (`estaciones.json`, `tramos.json`, `factores.json`) generados
  por `scripts/excel_a_json.py`, que además valida que hay 38 estaciones, 38 tramos y que cada
  línea es una cadena continua.
- Las distancias de la L3 tienen confianza baja (±20 %) según la propia hoja.

## 3.2.A Función de coste g(n): tabla de parámetros

g(n) = g(padre) + coste(padre, n), en minutos.

**Arista de tramo** (u → v):

    coste = [ marcha_s × F_marcha_franja × F_marcha_clima(tipo de vía)
            + parada_s(v) × F_parada_franja × F_parada_clima ] / 60

La parada no se suma si v es el destino (el viajero se baja).

**Arista de transbordo**:

    coste = pasillo + intervalo(línea nueva)/2 + saturación (solo punta o evento)
          + 10 min si «minimizar transbordos» + 15 min si «ruta accesible» y la estación no lo es

**Salida del origen**: espera inicial = intervalo(línea)/2.

| Parámetro | Valor | Fuente |
|---|---|---|
| Tiempo de marcha por tramo | 52–130 s según el tramo | Excel del grupo (70 km/h de crucero, aceleración 0,9 m/s², frenado 0,8 m/s²) |
| Parada en estación normal | 20 s | Excel (supuesto 15–25 s) |
| Parada en estación de transbordo | 35 s | Excel (20 s + 15 s extra) |
| Pasillo de transbordo | Cuauhtémoc 4 min, Zaragoza 3 min, Félix U. Gómez 3 min | Supuesto dentro del rango 3–6 min del Excel |
| Saturación en punta | Cuauhtémoc 5, Zaragoza 5, Félix U. Gómez 2 min | El grupo encontró 3–7 min en Cuauhtémoc y Zaragoza |
| Penalización «minimizar transbordos» | 10 min por transbordo | Decisión de diseño |
| Penalización «ruta accesible» | 15 min por transbordo en estación no accesible | Decisión de diseño; L1 y L2 no son accesibles (ABC Noticias, 2023) |
| Horario de servicio | 05:00–24:00 | lineasdelmetro.com.mx |

Franjas horarias (factor marcha / factor parada / intervalo L1-L2-L3 en min):

| Franja | Horario | F marcha | F parada | Intervalos |
|---|---|---|---|---|
| Apertura | 05:00–06:30 | 1,00 | 0,90 | 6 / 7 / 8 |
| Punta mañana | 06:30–09:30 | 1,05 | 1,75 | 4 / 5 / 6 |
| Valle mañana | 09:30–13:00 | 1,00 | 1,00 | 7 / 7 / 7,5 |
| Mediodía / salida escolar | 13:00–16:30 | 1,02 | 1,30 | 5 / 6 / 7,5 |
| Punta tarde | 16:30–20:00 | 1,06 | 1,80 | 4 / 5 / 6 |
| Noche | 20:00–22:00 | 1,00 | 1,10 | 6 / 7 / 8 |
| Cierre | 22:00–24:00 | 1,00 | 0,90 | 8 / 9 / 10 |
| Fin de semana / festivo | todo el día | 1,00 | 1,10 | 7 / 8 / 9 |
| Evento masivo | ±2 h | 1,10 | 2,50 | 4 / 5 / 6 |

Meteorología (F marcha elevado / F marcha subterráneo / F parada):

| Condición | Elevado | Subterráneo | Parada |
|---|---|---|---|
| Despejado | 1,00 | 1,00 | 1,00 |
| Lluvia ligera | 1,05 | 1,00 | 1,15 |
| Lluvia intensa | 1,15 | 1,02 | 1,30 |
| Tormenta eléctrica | 1,30 | 1,05 | 1,35 |
| Granizo | 1,40 | 1,05 | 1,30 |
| Inundación / huracán | 1,60 | 2,00 | 1,50 |
| Calor extremo | 1,04 | 1,00 | 1,05 |
| Frío extremo / helada | 1,15 | 1,02 | 1,10 |
| Niebla densa | 1,10 | 1,00 | 1,00 |
| Viento fuerte | 1,10 | 1,00 | 1,00 |

Prioridad de franjas: evento masivo > fin de semana > hora del día.

### Ejemplo numérico: Talleres → San Bernabé, punta de mañana con lluvia intensa (destino Hospital Metropolitano)

- Tramo elevado, marcha 62 s, parada en San Bernabé 20 s.
- Marcha: 62 × 1,05 (punta) × 1,15 (lluvia, elevado) = 74,87 s
- Parada: 20 × 1,75 (punta) × 1,30 (lluvia) = 45,50 s
- coste = (74,87 + 45,50) / 60 = **2,01 min** (en condiciones normales serían 1,37 min).
- g(San Bernabé) = g(Talleres) + 2,01, donde g(Talleres) = 2,00 min de espera inicial (intervalo L1 en punta = 4 min, /2).

## 3.2.B Heurística h(n)

h(n) = distancia haversine(n, destino) / V_max, con **V_max = 80 km/h = 1,333 km/min**
(velocidad máxima de los trenes; el Excel usa 70 km/h de crucero, pero con la velocidad
máxima nunca se sobreestima).

Ejemplo: Talleres → Hospital Metropolitano están a 10,21 km en línea recta, luego
h(Talleres) = 10,21 / 1,333 = **7,66 min**. h(San Bernabé) = 7,22 min.

Comprobación de consistencia en esa arista: h(Talleres) = 7,66 ≤ 2,01 + 7,22 = 9,23 ✔

**Admisible**: la vía nunca es más corta que la línea recta, el tren nunca supera V_max y el
resto de componentes de g (paradas, esperas, transbordos, penalizaciones) son ≥ 0, con
factores de marcha ≥ 1.

**Consistente**: por la desigualdad triangular, h(u) ≤ d(u,v)/V_max + h(v) ≤ coste(u,v) + h(v).
En un transbordo u y v tienen las mismas coordenadas, así que h(u) = h(v).
La prueba `tests/test_heuristica.py` lo verifica en las 82 aristas dirigidas × 38 destinos ×
90 escenarios (todas las franjas × todos los climas), y comprueba que ningún tramo del Excel
tiene un tiempo de marcha menor que la línea recta a 80 km/h.

## 4.4 Casos de prueba (cifras reales de la app)

| Caso | Entrada | Ruta | Tiempo | Transbordos | Distancia | Nodos A\* / Dijkstra |
|---|---|---|---|---|---|---|
| 1. Misma línea | Sendero → Universidad, 11:00, despejado | Sendero → Santiago Tapia → San Nicolás → Anáhuac → Universidad (L2) | 11,0 min | 0 | 5,79 km | 7 / 7 |
| 2. Con transbordo | Mitras → Hospital Metropolitano, 11:00, despejado | L1 hasta Félix U. Gómez (7 paradas), L3 hasta Hospital Metropolitano (5 paradas) | 29,9 min | 1 | 12,79 km | 38 / 40 |
| 3. Escenario dinámico | Igual que el 2, 08:00 (punta) + lluvia intensa | Misma ruta | 38,2 min (+8,3) | 1 | 12,79 km | 37 / 39 |

En el caso 2, A\* elige Félix U. Gómez (un solo transbordo) frente a Cuauhtémoc + General I.
Zaragoza (dos transbordos, con sus pasillos y esperas). En el caso 3 el tiempo sube por el
factor de marcha en punta (×1,05) y lluvia en tramo elevado (×1,15), y por las paradas más
largas (×1,75 × 1,30). Si además se marca «ruta accesible», la ruta es la misma pero el coste
de A\* sube 15 min y la app avisa de que L1 no está adaptada.

Nota (útil para la defensa): A\* expande pocos nodos menos que Dijkstra en esta red porque la
heurística es muy optimista: supone 80 km/h en línea recta, mientras que el tren va de media
a unos 40 km/h contando paradas, y no cuenta esperas ni transbordos. Sigue garantizando la
ruta óptima; una h más ajustada (por ejemplo, con la velocidad media) dejaría de ser admisible.

## 7.1 Librerías

| Librería | Uso |
|---|---|
| Python 3.10+ | Lenguaje |
| NetworkX | Estructura del grafo (el A\* es propio; NetworkX solo se usa en las pruebas para comparar con su Dijkstra) |
| NiceGUI | Interfaz web en Python (panel, tarjetas, tabla de la traza) |
| Leaflet + OpenStreetMap/CARTO (vía `ui.leaflet` de NiceGUI) | Mapa con las líneas y la ruta |
| openpyxl | Leer el Excel para generar los JSON |
| pytest | Pruebas automáticas |
| Git y GitHub | Control de versiones |

Matplotlib ya no se usa (solo en `legacy/grafo_inicial.py`).
