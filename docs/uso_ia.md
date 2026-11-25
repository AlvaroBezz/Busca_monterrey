# Registro de uso de herramientas de IA

La asignatura exige declarar todo uso de IA (apartado 8 de la memoria). No declararlo supone
un 0 para todo el grupo. Cada entrada sigue el formato de la tabla del apartado 8. Los
campos «Qué se aceptó y qué se descartó» y «Cómo se revisó» los completa el grupo después de
revisar el código.

---

## 25/11/2026 · Primera versión completa de la aplicación · Herramienta: Claude Code (asistente de programación de Anthropic)

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

## Otros usos de IA que hay que declarar en la memoria

- Hoja `Metrorrey_tiempos_entre_estaciones.xlsx`: elaborada con ayuda de IA (Gemini u otra).
  Hay que indicar los prompts, qué cifras se aceptaron y cómo se comprobaron.
- Plantilla de la memoria, si se generó con IA.
- Claude (claude.ai): planificación del trabajo, reparto de tareas, estructura del repositorio
  y propuestas de texto para la memoria.
