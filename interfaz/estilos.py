"""Colores, iconos y CSS compartidos por toda la interfaz."""

from metro.datos import COLORES_LINEA

EMOJI_LINEA = {"L1": "🟡", "L2": "🟢", "L3": "🔴"}

# Colores del desglose del tiempo (barra apilada del resultado)
COLORES_DESGLOSE = {
    "marcha": ("#3B82F6", "En marcha"),
    "paradas": ("#8B5CF6", "Paradas"),
    "esperas": ("#F59E0B", "Esperas en andén"),
    "transbordos": ("#EC4899", "Transbordos a pie"),
}

ICONOS_ACCION = {"subir": "login", "transbordo": "sync_alt", "bajar": "logout", "pasar": "circle"}

CSS = f"""
:root {{ --l1: {COLORES_LINEA['L1']}; --l2: {COLORES_LINEA['L2']}; --l3: {COLORES_LINEA['L3']}; }}
body {{ background: #F4F6FA; }}
body.body--dark {{ background: #0F1218; }}
.tarjeta {{ border-radius: 16px; box-shadow: 0 4px 18px rgba(15, 23, 42, .08); }}
.cifra-grande {{ font-size: 2.6rem; font-weight: 800; line-height: 1; letter-spacing: -0.02em; }}
.pildora-linea {{ display: inline-block; width: 34px; height: 8px; border-radius: 8px; margin-right: 6px; }}
.segmento {{ border-left: 6px solid; padding: 4px 0 10px 14px; margin-left: 10px; position: relative; }}
.segmento::before {{ content: ''; position: absolute; left: -11px; top: 4px; width: 16px; height: 16px;
                    border-radius: 50%; background: white; border: 4px solid; border-color: inherit; }}
.barra-desglose {{ display: flex; height: 14px; border-radius: 8px; overflow: hidden; }}
.leaflet-container {{ border-radius: 16px; }}
.nicegui-leaflet {{ height: 100%; }}
"""
