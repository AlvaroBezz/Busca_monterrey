import networkx as nx
import matplotlib.pyplot as plt

#esto es un comentario para comprobar q funciona git, te tocaré ramon

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
    ()
]

for origen, destino, tiempo in tramos_linea_verde:
    G.add_edge(origen, destino, weight = tiempo)

nx.draw(G, with_labels=True)
plt.show()