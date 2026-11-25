"""Punto de entrada de la aplicación.

    pip install -r requirements.txt
    python main.py            → abre http://localhost:8080
"""

from nicegui import ui

import interfaz.pagina  # noqa: F401  (registra la página "/")

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Metrorrey A*", port=8080, favicon="🚇", reload=False)
