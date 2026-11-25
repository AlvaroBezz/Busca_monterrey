# Memoria y uso de IA

Dos partes: el material listo para copiar en la memoria y el registro obligatorio de uso de IA.

## Parte 1. Material para la memoria

Datos sacados del código tal como está en este repositorio (cifras obtenidas ejecutando
`metro.py`). Si se cambian los parámetros (`FACTORES`, sección 7 de `metro.py`), hay que volver a
calcularlas.

### 3.1 Gestión topológica de los transbordos

Cada estación se representa con un nodo por línea (`estacion@linea`). Las tres estaciones de
transbordo (Cuauhtémoc, General I. Zaragoza y Félix U. Gómez) tienen por tanto dos nodos,
unidos por una arista de transbordo. El grafo tiene **41 nodos** (38 estaciones + 3
desdoblamientos) y **41 aristas** (38 tramos + 3 transbordos).

Para que A\* pueda empezar o terminar en una estación de transbordo sin elegir de antemano la
línea, se añaden dos nodos virtuales: INICIO (unido a los nodos de la estación origen con
coste = espera media del tren de esa línea) y FIN (al que se llega desde los nodos de la
estación destino con coste 0).

### 3.1 Recopilación y estructuración de datos

- Distancias y tiempos de marcha de los 38 tramos: hoja de cálculo del grupo
  (`Metrorrey_tiempos_entre_estaciones.xlsx`, hoja «Tramos (base)»).
- Factores por franja horaria y meteorología: misma hoja, pestaña «Parámetros».
- Coordenadas: Wikipedia «List of Metrorrey stations» (L1 y L2), Wikidata P625 (L3) y
  Wikipedia en español (Simón Bolívar, porque la lista en inglés repite las de Mitras).
- Formato: tres tablas dentro de `metro.py` (sección 7: `ESTACIONES`, `TRAMOS`, `FACTORES`),
  convertidas desde el Excel con un script que comprobaba que hay 38 estaciones, 38 tramos y
  que cada línea es una cadena continua (el script sigue en el historial de git).
- Las distancias de la L3 tienen confianza baja (±20 %) según la propia hoja.

### 3.2.A Función de coste g(n): tabla de parámetros

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

#### Ejemplo numérico: Talleres → San Bernabé, punta de mañana con lluvia intensa (destino Hospital Metropolitano)

- Tramo elevado, marcha 62 s, parada en San Bernabé 20 s.
- Marcha: 62 × 1,05 (punta) × 1,15 (lluvia, elevado) = 74,87 s
- Parada: 20 × 1,75 (punta) × 1,30 (lluvia) = 45,50 s
- coste = (74,87 + 45,50) / 60 = **2,01 min** (en condiciones normales serían 1,37 min).
- g(San Bernabé) = g(Talleres) + 2,01, donde g(Talleres) = 2,00 min de espera inicial (intervalo L1 en punta = 4 min, /2).

### 3.2.B Heurística h(n)

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
La prueba `test_metro.py` lo verifica en las 82 aristas dirigidas × 38 destinos ×
90 escenarios (todas las franjas × todos los climas), y comprueba que ningún tramo del Excel
tiene un tiempo de marcha menor que la línea recta a 80 km/h.

### 4.4 Casos de prueba (cifras reales de la app)

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

### 7.1 Librerías

| Librería | Uso |
|---|---|
| Python 3.10+ | Lenguaje |
| NetworkX | Estructura del grafo (el A\* es propio; NetworkX solo se usa en las pruebas para comparar con su Dijkstra) |
| NiceGUI | Interfaz web en Python (panel, tarjetas, tabla de la traza) |
| Leaflet + OpenStreetMap/CARTO (vía `ui.leaflet` de NiceGUI) | Mapa con las líneas y la ruta |
| openpyxl | Leer el Excel para generar los JSON |
| pytest | Pruebas automáticas |
| Git y GitHub | Control de versiones |

Matplotlib ya no se usa (solo lo usaba el primer prototipo del grafo, que sigue en el historial de git).

---

## Parte 2. Registro de uso de herramientas de IA

La asignatura exige declarar todo uso de IA (apartado 8 de la memoria). No declararlo supone
un 0 para todo el grupo. Cada entrada sigue el formato de la tabla del apartado 8. Los
campos «Qué se aceptó y qué se descartó» y «Cómo se revisó» los completa el grupo después de
revisar el código.

---

### 25/11/2026 · Primera versión completa de la aplicación · Herramienta: Claude Code (asistente de programación de Anthropic)

- **Tarea concreta**: generar la primera versión de la aplicación a partir del plan por fases
  del grupo (`plan/prompt_claude_code_completo.md`, fases 1 a 5) y de la memoria en Google
  Docs: conversión del Excel a JSON, grafo con NetworkX, funciones g(n) y h(n), A\* propio,
  interfaz web con NiceGUI y mapa Leaflet, pruebas, README y material para la memoria.
- **Motivo del uso**: apoyo para la implementación de la interfaz y la estructura del
  proyecto (tarea de Mario), dejando un código que los seis miembros puedan revisar,
  entender y defender.
- **Prompt utilizado** (mensaje literal de Mario):
  > «esta hecho, empieza a programar ahi y dime que cambios has hecho, ten en cuenta lo que
  > llevamos puesto en la memoria para diseñar la web sabes, que ya hemos ido poniendo cosas»

  Junto con las instrucciones del plan por fases del grupo (bloque 0 de contexto y fases 1–5),
  que se adjuntan en la carpeta `plan/` del proyecto.
- **Salida obtenida**:
  - `scripts/excel_a_json.py` → `data/estaciones.json`, `data/tramos.json`, `data/factores.json`.
  - `metro/datos.py`, `metro/grafo.py` (41 nodos, 41 aristas), `metro/coste.py` (g),
    `metro/heuristica.py` (h = haversine / 80 km/h), `metro/astar.py` (A\* con heapq, lista
    cerrada, reconstrucción del camino y traza), `metro/ruta.py` (`calcular_ruta()`).
  - `interfaz/` (página, panel, mapa, resultado, estilos) y `main.py`.
  - `tests/` (21 pruebas: tamaño y conexidad del grafo, consistencia de h en todas las
    aristas y escenarios, A\* = Dijkstra en los 1.406 pares × 4 escenarios, casos concretos).
  - `README.md`, `docs/para_memoria.md` y este fichero.
  - Se movió `hola bezos.py` (Ramón) a `legacy/grafo_inicial.py` y el README inicial a
    `docs/notas_iniciales.txt`, conservando su historia en git.
- **Datos buscados por la IA**: las coordenadas de la L3 (no están en la lista de Wikipedia
  en inglés) se tomaron de Wikidata (propiedad P625 de cada estación) y la de Simón Bolívar
  del artículo de Wikipedia en español, consultados el 25/11/2026. **Hay que comprobarlas**
  en Google Maps antes de la entrega.
- **Decisiones tomadas por la IA que el grupo debe revisar**:
  - Niños Héroes (L2) y Santa Lucía (L3) quedan entre un tramo elevado y uno subterráneo:
    se marcan como `"tipo_dudoso": true`. No afecta al cálculo (el clima se aplica por tramo).
  - Una estación de transbordo se considera accesible solo si lo son todas sus líneas, así que
    las tres de transbordo cuentan como no accesibles.
  - Las penalizaciones (minimizar transbordos, accesibilidad) cuentan en el coste de A\* pero
    no en el tiempo de viaje que se muestra, porque no son tiempo real.
  - Fuera del horario de servicio se calcula con la franja de «Apertura» y se avisa.
- **Qué se aceptó y qué se descartó/modificó**: *(a rellenar por el grupo tras revisar)*
- **Cómo se revisó y validó**: se ejecutó `pytest` (21 pruebas en verde) y se probó la web
  en un navegador (cálculo de rutas, clic en el mapa, animación de A\*, vista móvil).
  *(El grupo debe añadir su propia revisión: lectura línea a línea de `astar.py`, `coste.py`
  y `heuristica.py` por quien los vaya a defender, y comprobación de las coordenadas.)*

---

### Otros usos de IA que hay que declarar en la memoria

- Hoja `Metrorrey_tiempos_entre_estaciones.xlsx`: elaborada con ayuda de IA (Gemini u otra).
  Hay que indicar los prompts, qué cifras se aceptaron y cómo se comprobaron.
- Plantilla de la memoria, si se generó con IA.
- Claude (claude.ai): planificación del trabajo, reparto de tareas, estructura del repositorio
  y propuestas de texto para la memoria.

---

### 25/11/2026 · Versión para el público y despliegue · Herramienta: Claude Code (asistente de programación de Anthropic)

- **Tarea concreta**: rediseñar la interfaz pensando en un ciudadano o un alcalde que evalúa la
  propuesta (sin explicaciones técnicas en pantalla), arreglar el mapa que no se veía y
  preparar una forma sencilla de compartir la web.
- **Prompt utilizado** (mensaje literal de Mario):
  > «Ya lo veo, esta genial, pero varios cambios. Lo van a corregir como si fuese un alcalde
  > viendo una propuesta de web, asi que no lo hagas orientado a la teoria o las directrices de
  > la practica, quita lo del A* no expliques nada de eso. Intenta meter el mapa que ahora mismo
  > no sale. Que la interfaz sea mas para el publico, que este mas chula. Dime como puedo
  > pasarselo a mis compañeros para que lo abran y lo vean desde su ordenador y que no sea muy
  > lioso»
- **Salida obtenida**: nuevo diseño de `interfaz/` (cabecera, buscador, viajes populares,
  itinerario por pasos con horas, desglose del tiempo en lenguaje sencillo, leyenda del mapa);
  se quitan de la pantalla la traza de A\*, la comparación con Dijkstra y la animación (el
  algoritmo y las pruebas siguen igual); el mapa usa ahora CSS propio para su tamaño y un
  fondo de calles de CARTO/OpenStreetMap; `main.py` acepta el puerto de un servidor;
  `render.yaml` e `iniciar_windows.bat` para compartirla; README con los pasos.
- **Qué se aceptó y qué se descartó/modificó**: *(a rellenar por el grupo)*
- **Cómo se revisó y validó**: 21 pruebas de `pytest` en verde; la web se probó en navegador
  de escritorio y móvil con NiceGUI 3.19 y 4.1.

---

### 25/11/2026 · Hora de llegada y revisión de las líneas 4 y 6 · Herramienta: Claude Code (asistente de programación de Anthropic)

- **Prompt utilizado** (mensaje literal de Mario): «Otros dos cambios: Los requisitos son hacer al
  menos 3 líneas, pero nos dijo el profesor que podemos hacer las que queramos, como si hacemos
  todas (nos dará más nota) asi que mete todas. A parte de poder poner el sellector de hora de
  salida pon uno de hora de llegada tambien, y si no pones nada por default deberia de poner la
  hora actual. Y lo de compartirlo no seria mejor en vercel, estoy muy acostumbrado a esa
  paltaforma la verdad»
- **Salida obtenida**: `calcular_ruta_llegando_a()` en `metro/ruta.py` (estima la salida y la
  ajusta hasta que la llegada cuadra) con su prueba; selector «Salir a las / Llegar a las» en la
  interfaz, que usa la hora actual de Monterrey si se deja vacío.
- **Líneas 4 y 6**: la IA buscó su estado (Wikipedia, MVS Noticias 20/10/2026, Quadratín
  02/11/2026, Los Tubos 03/11/2026). A 25/11/2026 siguen en construcción, sin estaciones abiertas
  confirmadas ni coordenadas o tiempos oficiales, y la Línea 5 está cancelada. El grupo decidió
  calcular solo con las líneas en servicio (L1, L2 y L3) y avisar en el mapa de que la 4 y la 6
  están en construcción.
- **Qué se aceptó y qué se descartó/modificó**: *(a rellenar por el grupo)*
- **Cómo se revisó y validó**: 22 pruebas de `pytest` en verde; prueba en navegador del modo
  «Llegar a las» y de la hora vacía.

---

### 25/11/2026 · Líneas 4 y 6 en obras y código en menos archivos · Herramienta: Claude Code (asistente de programación de Anthropic)

- **Prompts utilizados** (mensajes literales de Mario):
  > «corrigo, metemos la 4 y 6 tambien pero con aviso que estan en obras o temporalmente fuera
  > de servicio o lo que sea»

  > «hay muchisimos archivos de codigo distintos, es un lio, haz muchos menos archivos y todo
  > mas compactado, que luego es un lio para comprobar todo, si puedes, sino puedes nada,
  > prioriza que siga funcionando la aplicacion»
- **Salida obtenida**:
  - `data/lineas_en_obras.json`: estaciones de la Línea 4 (7, solo el tramo con nombre en OSM)
    y de la Línea 6 (15, de Parque Fundidora a Arco Vial). **Posiciones aproximadas** sacadas
    por la IA de OpenStreetMap (consulta Overpass del 25/11/2026). Se dibujan en el mapa en
    discontinua con el aviso «en obras / temporalmente fuera de servicio» y **no** se usan para
    calcular rutas.
  - El código pasa de 15 archivos a 4: `metro.py` (antes `metro/datos.py`, `grafo.py`,
    `coste.py`, `heuristica.py`, `astar.py`, `ruta.py`), `main.py` (antes `interfaz/*` y
    `main.py`), `test_metro.py` (antes `tests/*`) y `excel_a_json.py` (antes en `scripts/`).
    El contenido de las funciones no cambia; solo se juntan en secciones numeradas.
- **Qué se aceptó y qué se descartó/modificó**: *(a rellenar por el grupo)*
- **Cómo se revisó y validó**: 23 pruebas de `pytest` en verde (se añade una que comprueba
  que las líneas 4 y 6 no entran en el grafo); prueba en navegador de escritorio y móvil.
  *(El grupo debe comprobar en Google Maps las posiciones de las líneas 4 y 6.)*
- **Limpieza del repositorio** (mensaje de Mario: «pero mete el codigo actualizado en github y
  quita la mierda que sobre»): se quitan el primer prototipo del grafo
  (`legacy/grafo_inicial.py`), las notas iniciales y la carpeta vacía de capturas. Siguen en el
  historial de git.
- **Archivos al mínimo** (mensaje de Mario: «claro, que quede lo mas limpio posible y aparezcan
  los minimos archivos posibles»): los datos pasan de `data/*.json` a la sección 7 de
  `metro.py`; el Excel queda en la raíz; se quitan `excel_a_json.py`, `render.yaml`,
  `iniciar_windows.bat` y la carpeta `docs/` (su contenido está en este archivo). Lo quitado
  sigue en el historial de git. 23 pruebas en verde y la web comprobada en el navegador.
