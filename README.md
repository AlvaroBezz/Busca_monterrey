# Metrorrey · Ruta óptima con A*

Práctica de búsqueda de Inteligencia Artificial (ETSIINF, UPM, curso 2026-27, grupo 205).

Aplicación web en Python que calcula y muestra el trayecto óptimo entre dos estaciones
del Metro de Monterrey (Metrorrey), líneas 1, 2 y 3, con un **algoritmo A\* programado por
nosotros**. El coste tiene en cuenta la franja horaria, la meteorología, los transbordos,
los eventos masivos y la accesibilidad.

![Colores de línea](https://img.shields.io/badge/L1-amarilla-F2C200) ![](https://img.shields.io/badge/L2-verde-2E9E44) ![](https://img.shields.io/badge/L3-roja-D7262E)

## Requisitos

- Python 3.10 o superior
- Conexión a internet para ver el fondo del mapa (teselas de OpenStreetMap/CARTO)

## Instalación y ejecución

```bash
git clone https://github.com/AlvaroBezz/Busca_monterrey.git
cd Busca_monterrey
pip install -r requirements.txt
python main.py
```

Se abre en el navegador en **http://localhost:8080**.

### Cómo se usa

1. Elige origen y destino en el panel (o haz clic en dos estaciones del mapa).
2. Ajusta la hora, el día, la meteorología y las opciones (evento masivo, minimizar
   transbordos, ruta accesible).
3. Pulsa **Calcular ruta**: verás el tiempo total, la hora de llegada, el itinerario,
   el desglose del tiempo y la ruta resaltada en el mapa.
4. Abre **¿Cómo lo ha calculado A\*?** para ver la traza paso a paso (g, h, f) y la
   comparación con Dijkstra. El botón **Ver animación** marca en el mapa los nodos
   en el orden en que A\* los expande.

## Pruebas

```bash
pytest
```

Comprueban, entre otras cosas, que:
- la red tiene 38 estaciones, 41 nodos y 41 aristas y es conexa;
- la heurística es **consistente** en todas las aristas, para todos los destinos,
  franjas horarias y climas;
- nuestro A\* da el **mismo coste que Dijkstra de NetworkX** en los 38 × 37 pares de
  estaciones y en 4 escenarios distintos, y nunca expande más nodos.

## Estructura del proyecto

```
Busca_monterrey/
├── main.py                  arranca la web (NiceGUI)
├── requirements.txt
├── data/
│   ├── estaciones.json      38 estaciones con coordenadas, líneas y accesibilidad
│   ├── tramos.json          38 tramos con distancia, tiempo de marcha y tipo de vía
│   ├── factores.json        parámetros de g(n) y h(n): franjas, clima, transbordos
│   └── fuentes/             Excel original de tiempos del grupo
├── scripts/excel_a_json.py  convierte el Excel en los JSON anteriores
├── metro/
│   ├── datos.py             carga los JSON
│   ├── grafo.py             grafo NetworkX (un nodo por estación y línea)
│   ├── coste.py             g(n): coste de cada arista según el escenario
│   ├── heuristica.py        h(n): distancia haversine / 80 km/h
│   ├── astar.py             A* propio con traza
│   └── ruta.py              calcular_ruta(): lo que usa la interfaz
├── interfaz/                página, panel, mapa (ui.leaflet), resultado y estilos
├── tests/                   pruebas con pytest
├── legacy/grafo_inicial.py  primer grafo de Ramón (historia del proyecto)
└── docs/
    ├── uso_ia.md            registro obligatorio del uso de IA
    ├── para_memoria.md      tablas y ejemplos listos para la memoria
    └── capturas/            capturas para la memoria
```

Si se cambia el Excel, se regeneran los datos con `python scripts/excel_a_json.py`.

## Modelo en una línea

- **g(n)** = g(padre) + (marcha × F_marcha_franja × F_marcha_clima + parada × F_parada_franja × F_parada_clima) / 60
  en los tramos, y pasillo + intervalo/2 + saturación en punta (+ penalizaciones) en los transbordos.
- **h(n)** = distancia en línea recta hasta el destino / 80 km/h. Es admisible y consistente.

El detalle, con un ejemplo numérico, está en [docs/para_memoria.md](docs/para_memoria.md).

## Fuentes de datos

- Tiempos y distancias: hoja de cálculo del grupo `data/fuentes/Metrorrey_tiempos_entre_estaciones.xlsx`
  (elaborada con ayuda de IA; ver `docs/uso_ia.md`).
- Coordenadas L1 y L2: Wikipedia, *List of Metrorrey stations*.
- Coordenadas L3: Wikidata (propiedad P625 de cada estación). Simón Bolívar: Wikipedia en español
  (la lista en inglés le pone por error las coordenadas de Mitras).
- Accesibilidad de L1 y L2: ABC Noticias, 18/10/2023.
- Mapa: © OpenStreetMap contributors, © CARTO.

## Autores

Almudena Hernán Ortega (coordinadora), Álvaro Bezos Arellano, Ander Gajate García,
Francisco de Borja Elizaga Royo, Ramón Andreu Oliete y Mario López Delgado.

## Uso de inteligencia artificial

Parte del código y de la documentación se ha generado con ayuda de herramientas de IA.
Todo uso está declarado en [docs/uso_ia.md](docs/uso_ia.md), tal como exige la asignatura.
