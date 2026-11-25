# Metrorrey · Ruta óptima con A*

Práctica de búsqueda de Inteligencia Artificial (ETSIINF, UPM, curso 2026-27, grupo 205).

Aplicación web en Python que calcula y muestra el trayecto óptimo entre dos estaciones
del Metro de Monterrey (Metrorrey), líneas 1, 2 y 3 (la 4 y la 6, en obras, aparecen en el mapa), con un **algoritmo A\* programado por
nosotros**. El coste tiene en cuenta la franja horaria, la meteorología, los transbordos,
los eventos masivos y la accesibilidad.

![Colores de línea](https://img.shields.io/badge/L1-amarilla-F2C200) ![](https://img.shields.io/badge/L2-verde-2E9E44) ![](https://img.shields.io/badge/L3-roja-D7262E)

## Verla sin instalar nada (enlace)

La app está pensada para publicarse gratis en [Render](https://render.com):

1. Entra en https://render.com y regístrate con tu cuenta de GitHub.
2. **New +** → **Web Service** → pestaña **Public Git Repository** → pega
   `https://github.com/AlvaroBezz/Busca_monterrey` → **Connect**.
3. Rellena: **Branch** `main` (o la rama que queráis enseñar), **Language** Python 3,
   **Build Command** `pip install -r requirements.txt`, **Start Command** `python main.py`,
   **Instance Type** Free → **Deploy Web Service**.
4. En 2–3 minutos Render da un enlace `https://….onrender.com` que se puede compartir.

En el plan gratuito, si nadie la usa durante 15 minutos se duerme, y la primera visita tarda
alrededor de un minuto en despertarla.

## Abrirla en tu ordenador

Necesitas Python 3.10 o superior (en Windows, desde python.org marcando "Add Python to PATH").

- **Windows**: descarga el proyecto (botón verde *Code* → *Download ZIP*), descomprímelo y haz
  doble clic en `iniciar_windows.bat`. Se abre sola en el navegador.
- **Cualquier sistema**:

```bash
git clone https://github.com/AlvaroBezz/Busca_monterrey.git
cd Busca_monterrey
pip install -r requirements.txt
python main.py
```

Se abre en **http://localhost:8080**. Hace falta internet para el fondo del mapa.

### Cómo se usa

1. Elige estación de salida y de llegada (o tócalas en el mapa), o pulsa un viaje popular.
2. Indica la hora, el día, el tiempo que hace y tus preferencias (evento, menos transbordos,
   ruta accesible).
3. Pulsa **Buscar ruta**: verás cuánto tardas, a qué hora llegas, dónde subir y dónde cambiar
   de línea, y la ruta dibujada en el mapa.

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
├── main.py            la web (NiceGUI): estilos, mapa, buscador, resultado y arranque
├── metro.py           el cálculo: datos, grafo, g(n), h(n), A* y calcular_ruta()
├── test_metro.py      pruebas con pytest
├── excel_a_json.py    convierte el Excel del grupo en los JSON de data/
├── data/
│   ├── estaciones.json      38 estaciones con coordenadas, líneas y accesibilidad
│   ├── tramos.json          38 tramos con distancia, tiempo de marcha y tipo de vía
│   ├── factores.json        parámetros de g(n) y h(n): franjas, clima, transbordos
│   ├── lineas_en_obras.json Líneas 4 y 6 (solo para el mapa, posiciones aproximadas)
│   └── fuentes/             Excel original de tiempos del grupo
├── legacy/grafo_inicial.py  primer grafo de Ramón (historia del proyecto)
└── docs/                    uso de IA, material para la memoria y capturas
```

Cada archivo de código está dividido en secciones numeradas, con una explicación al
principio de cada una. Quien vaya a defender el A\* solo tiene que leer `metro.py`.

Si se cambia el Excel, se regeneran los datos con `python excel_a_json.py`.

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
- Líneas 4 y 6 (en construcción, solo en el mapa): posiciones aproximadas de OpenStreetMap,
  consultadas el 25/11/2026. No se usan para calcular rutas hasta que abran.
- Mapa: © OpenStreetMap contributors, © CARTO.

## Autores

Almudena Hernán Ortega (coordinadora), Álvaro Bezos Arellano, Ander Gajate García,
Francisco de Borja Elizaga Royo, Ramón Andreu Oliete y Mario López Delgado.

## Uso de inteligencia artificial

Parte del código y de la documentación se ha generado con ayuda de herramientas de IA.
Todo uso está declarado en [docs/uso_ia.md](docs/uso_ia.md), tal como exige la asignatura.
