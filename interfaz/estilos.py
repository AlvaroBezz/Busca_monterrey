"""Colores, textos e iconos compartidos por toda la interfaz."""

from metro.datos import COLORES_LINEA

EMOJI_LINEA = {"L1": "🟡", "L2": "🟢", "L3": "🔴"}

EMOJI_CLIMA = {
    "despejado": "☀️", "lluvia_ligera": "🌦️", "lluvia_intensa": "🌧️", "tormenta": "⛈️",
    "granizo": "🧊", "inundacion": "🌊", "calor_extremo": "🔥", "helada": "❄️",
    "niebla": "🌫️", "viento_fuerte": "💨",
}

# Partes del tiempo de viaje, con nombres para el público
COLORES_DESGLOSE = {
    "en_tren": ("#2563EB", "En el tren"),
    "esperas": ("#F59E0B", "Esperando el tren"),
    "transbordos": ("#DB2777", "Cambiando de línea"),
}

# Viajes de ejemplo para la pantalla inicial
RUTAS_POPULARES = [
    ("talleres", "exposicion", "De punta a punta de la Línea 1"),
    ("sendero", "parque_fundidora", "Al Parque Fundidora"),
    ("universidad", "hospital_metropolitano", "Al Hospital Metropolitano"),
    ("san_bernabe", "general_i_zaragoza", "Al centro (Macroplaza)"),
]

CSS = f"""
:root {{ --l1: {COLORES_LINEA['L1']}; --l2: {COLORES_LINEA['L2']}; --l3: {COLORES_LINEA['L3']}; }}
body {{ background: #EEF2F7; font-family: 'Inter', 'Segoe UI', system-ui, sans-serif; }}
.cabecera {{ background: linear-gradient(120deg, #0F172A 0%, #1E293B 55%, #334155 100%); }}
.franja-lineas {{ height: 5px; background: linear-gradient(90deg, var(--l1) 0 33.3%, var(--l2) 33.3% 66.6%, var(--l3) 66.6% 100%); }}
.tarjeta {{ border-radius: 20px; box-shadow: 0 10px 30px rgba(15, 23, 42, .08); border: 1px solid rgba(15,23,42,.05); }}
.cifra-grande {{ font-size: 3.2rem; font-weight: 800; line-height: 1; letter-spacing: -0.03em; }}
.boton-principal {{ background: linear-gradient(90deg, #0F172A, #334155) !important; color: white !important;
                    border-radius: 14px !important; font-weight: 700; letter-spacing: .02em; }}
.insignia {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px;
             font-size: .8rem; font-weight: 600; background: rgba(255,255,255,.12); color: white; }}
.punto {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
.paso {{ position: relative; padding: 0 0 16px 30px; }}
.paso::before {{ content: ''; position: absolute; left: 9px; top: 22px; bottom: 0; width: 6px;
                 border-radius: 4px; background: var(--color-paso, #CBD5E1); }}
.paso:last-child::before {{ display: none; }}
.paso .icono-paso {{ position: absolute; left: 0; top: 0; width: 24px; height: 24px; border-radius: 50%;
                     display: flex; align-items: center; justify-content: center; color: white; font-size: 14px; }}
.barra-desglose {{ display: flex; height: 12px; border-radius: 8px; overflow: hidden; background: #E2E8F0; }}
.leyenda-mapa {{ position: absolute; top: 14px; right: 14px; z-index: 1000; background: rgba(255,255,255,.95);
                 border-radius: 14px; padding: 10px 14px; box-shadow: 0 6px 20px rgba(15,23,42,.15); }}
.ruta-popular {{ border-radius: 14px; transition: all .15s; cursor: pointer; }}
.ruta-popular:hover {{ background: #F1F5F9; transform: translateY(-1px); }}
.cuerpo {{ display: flex; gap: 16px; align-items: flex-start; max-width: 1600px; margin: 0 auto;
           padding: 16px; width: 100%; box-sizing: border-box; }}
.columna-izq {{ width: 440px; flex-shrink: 0; display: flex; flex-direction: column; gap: 16px; }}
.tarjeta-mapa {{ flex: 1 1 auto; min-width: 0; height: calc(100vh - 122px); min-height: 480px;
                 position: sticky; top: 16px; padding: 0 !important; overflow: hidden; }}
@media (max-width: 1023px) {{
  .cuerpo {{ flex-direction: column; align-items: stretch; }}
  .columna-izq {{ width: 100%; }}
  .tarjeta-mapa {{ position: relative; top: 0; height: 70vh; width: 100%; }}
  .solo-escritorio {{ display: none !important; }}
}}
.mapa-metro {{ width: 100%; height: 100%; min-height: 420px; border-radius: 20px; }}
"""
