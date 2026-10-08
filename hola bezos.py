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
    ("Padre Mier", "General I. Zaragoza", 2)
]

tramos_linea_roja = [
    ("Hospital Metropolitano", "Los Ángeles", 2),
    ("Los Ángeles", "Ruiz Cortines", 2),
    ("Ruiz Cortines", "Col. Moderna", 2),
    ("Col. Moderna", "Metalúrgicos", 2),
    ("Metalúrgicos", "Félix U. Gómez", 2),
    ("Félix U. Gómez", "Col Obrera", 2),
    ("Col Obrera", "Santa Lucía", 2),
    ("Santa Lucía", "Gral A. Zaragoza", 2)
]

for origen, destino, tiempo in tramos_linea_verde + tramos_linea_roja:
    G.add_edge(origen, destino, weight = tiempo)

#for origen, destino, tiempo in tramos_linea_roja:
    #G.add_edge(origen, destino, weight = tiempo)

nx.draw(G, with_labels=True)
plt.show()