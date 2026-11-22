# -*- coding: utf-8 -*-
"""
visualisation.py – Graphiques Matplotlib (front de Pareto + convergence).
"""

import numpy as np
import matplotlib.pyplot as plt


def tracer_front(F_init, solutions, k_best, fichier="front_pareto.png"):
    Fs  = np.array([f for _, f in solutions])
    fig = plt.figure(figsize=(14, 5.5))

    ax = fig.add_subplot(1, 2, 1, projection="3d")
    ax.scatter(F_init[:, 0], F_init[:, 1], F_init[:, 2],
               c="lightgray", s=12, label="Population initiale")
    ax.scatter(Fs[:, 0], Fs[:, 1], Fs[:, 2],
               c="crimson", s=30, label="Front de Pareto")
    ax.scatter(*Fs[k_best], c="blue", s=160, marker="*", label="Meilleur compromis")
    ax.set_xlabel("f1 : conflits")
    ax.set_ylabel("f2 : heures creuses")
    ax.set_zlabel("f3 : salles")
    ax.set_title("Front de Pareto en 3D")
    ax.legend(loc="upper left", fontsize=8)

    ax2 = fig.add_subplot(1, 2, 2)
    if len(np.unique(Fs[:, 0])) > 1:
        sc = ax2.scatter(Fs[:, 1], Fs[:, 2], c=Fs[:, 0], cmap="viridis_r", s=70, edgecolors="k")
        plt.colorbar(sc, ax=ax2, label="f1 : conflits (0 = valide)")
    else:
        ax2.scatter(Fs[:, 1], Fs[:, 2], c="crimson", s=70, edgecolors="k",
                    label="Solutions non dominées (f1=0)")
    ax2.scatter(Fs[k_best, 1], Fs[k_best, 2],
                c="blue", s=250, marker="*", label="Meilleur compromis")
    ax2.plot(Fs[:, 1], Fs[:, 2], color="crimson", alpha=0.4, linestyle="--")
    marge_x = max(0.1, 0.15 * np.ptp(Fs[:, 1]))
    marge_y = max(0.1, 0.15 * np.ptp(Fs[:, 2]))
    ax2.set_xlim(Fs[:, 1].min() - marge_x, Fs[:, 1].max() + marge_x)
    ax2.set_ylim(Fs[:, 2].min() - marge_y, Fs[:, 2].max() + marge_y)
    ax2.set_xlabel("f2 : heures creuses + déséquilibre")
    ax2.set_ylabel("f3 : mauvaise utilisation des salles")
    ax2.set_title("Front de Pareto : zoom (f2, f3)")
    ax2.grid(alpha=0.3)
    ax2.legend()

    plt.tight_layout()
    plt.savefig(fichier, dpi=150)
    plt.close(fig)


def tracer_evolution(hist, fichier="evolution_objectifs.png"):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    objectifs = [
        ("f1", "f1 : conflits"),
        ("f2", "f2 : heures creuses + déséquilibre"),
        ("f3", "f3 : mauvaise utilisation des salles"),
    ]
    for ax, (col, titre) in zip(axes.flat[:3], objectifs):
        ax.plot(hist["génération"], hist[col + " moyen"], label="moyenne", color="gray")
        ax.plot(hist["génération"], hist[col + " min"],   label="meilleure valeur", color="crimson")
        ax.set_title(titre)
        ax.set_xlabel("génération")
        ax.grid(alpha=0.3)
        ax.legend()
    ax = axes.flat[3]
    ax.plot(hist["génération"], hist["solutions sans conflit"],
            label="sans conflit", color="green")
    ax.plot(hist["génération"], hist["taille front 0"],
            label="taille front 0", color="purple")
    ax.set_title("Solutions valides et taille du front")
    ax.set_xlabel("génération")
    ax.grid(alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.savefig(fichier, dpi=150)
    plt.close(fig)
