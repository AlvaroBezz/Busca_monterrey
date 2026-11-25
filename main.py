"""Punto de entrada de la aplicación.

En tu ordenador:
    pip install -r requirements.txt
    python main.py            → se abre http://localhost:8080

En un servidor (Render, Hugging Face...) el puerto llega en la variable PORT.
"""

import os

from nicegui import ui

import interfaz.pagina  # noqa: F401  (registra la página "/")

if __name__ in {"__main__", "__mp_main__"}:
    en_servidor = "PORT" in os.environ
    ui.run(
        title="Metrorrey · Ruta más rápida",
        host="0.0.0.0" if en_servidor else "127.0.0.1",
        port=int(os.environ.get("PORT", 8080)),
        favicon="🚇",
        reload=False,
        show=not en_servidor,      # en tu ordenador abre el navegador solo
        language="es",
    )
