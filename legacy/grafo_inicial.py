# =====================================================================
# VERSIÓN INICIAL DEL GRAFO (autor: Ramón Andreu Oliete)
# Primer prototipo con NetworkX, conservado como historia del proyecto.
# Se movió aquí desde "hola bezos.py". La versión actual está en metro/grafo.py,
# que añade Penitenciaría (L1), usa los nombres oficiales del Excel y pesos
# reales en minutos en lugar de 2 para todos los tramos.
# Este fichero NO lo usa la aplicación.
# =====================================================================
import networkx as nx
import matplotlib.pyplot as plt


G = nx.Graph()

tramos_linea_verde = [
    ("Sendero", "Santiago Tapia", 2),
    ("Santiago Tapia", "San Nicolás", 2),
    ("San Nicolás", "Anáhuac", 2),
    ("Anáhuac", "Universidad", 2),
    ("Universidad", "Niños Héroes", 2),
    ("Niños Héroes", "Regina", 2),
    ("Regina", "General Anaya", 2),
    ("General Anaya", "Cuauhtémoc", 2),
    ("Cuauhtémoc", "Alameda", 2),
    ("Alameda", "Fundadores", 2),
    ("Fundadores", "Padre Mier", 2),
    ("Padre Mier", "Gral I. Zaragoza", 2)
]

tramos_linea_roja = [
    ("Hospital Metropolitano", "Los Ángeles", 2),
    ("Los Ángeles", "Ruiz Cortines", 2),
    ("Ruiz Cortines", "Col. Moderna", 2),
    ("Col. Moderna", "Metalúrgicos", 2),
    ("Metalúrgicos", "Félix U. Gómez", 2),
    ("Félix U. Gómez", "Col Obrera", 2),
    ("Col Obrera", "Santa Lucía", 2),
    ("Santa Lucía", "Gral I. Zaragoza", 2),
]

tramos_linea_amarilla = [
    ("Talleres", "San Bernabé", 2),
    ("San Bernabé", "Unidad Modelo", 2),
    ("Unidad Modelo", "Aztlán", 2),
    ("Aztlán", "Alfonso Reyes", 2),
    ("Alfonso Reyes", "Mitras", 2),
    ("Mitras", "Simón Bolívar", 2),
    ("Simón Bolívar", "Hospital", 2),
    ("Hospital", "Edison", 2),
    ("Edison", "Central", 2),
    ("Central", "Cuauhtémoc", 2),
    ("Cuauhtémoc", "Del Golfo", 2),
    ("Del Golfo", "Félix U. Gómez", 2),
    ("Félix U. Gómez", "Parque Fundidora", 2),
    ("Parque Fundidora", "Y Griega", 2),
    ("Y Griega", "Eloy Cavazos", 2),
    ("Eloy Cavazos", "Lerdo de Tejada", 2),
    ("Lerdo de Tejada", "Exposición", 2),
]

for origen, destino, tiempo in tramos_linea_verde + tramos_linea_roja + tramos_linea_amarilla:
    G.add_edge(origen, destino, weight = tiempo)

#for origen, destino, tiempo in tramos_linea_roja:
    #G.add_edge(origen, destino, weight = tiempo)

nx.draw(G, with_labels=True)
plt.show()