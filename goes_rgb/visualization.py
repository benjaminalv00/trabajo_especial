# goes_rgb/visualization.py
import matplotlib.pyplot as plt

def plot_radiance(radiancia, titulo="Radiancia", cmap="gray"):
    plt.figure(figsize=(8, 6))
    plt.imshow(radiancia, cmap=cmap)
    plt.title(titulo)
    plt.axis("off")
    plt.colorbar(label="Radiancia")
    plt.show()

