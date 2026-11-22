# -*- coding: utf-8 -*-
"""
resultats.py – Extraction du front de Pareto, meilleur compromis, exports CSV,
et calcul des métriques de performance EMO (Espacement de Schott, Hypervolume).
"""

import numpy as np
import pandas as pd
import config as C
from pareto import classement_non_domine
from affichage import tableau_groupe

NOMS_OBJECTIFS = ["f1 conflits", "f2 heures creuses", "f3 salles"]


def calculer_espacement_schott(F_front):
    """
    Calcule la métrique d'espacement de Schott (S, 1995).
    Mesure l'uniformité de la répartition des solutions sur le front.
    S = 0 correspond à une répartition parfaitement équidistante.
    """
    if len(F_front) < 2:
        return 0.0
    F_arr = np.atleast_2d(F_front)
    # Distance de Manhattan (L1) au plus proche voisin sur le front
    diff = np.abs(F_arr[:, None, :] - F_arr[None, :, :]).sum(axis=2)
    np.fill_diagonal(diff, np.inf)
    d = np.min(diff, axis=1)
    d_mean = np.mean(d)
    s = np.sqrt(np.sum((d - d_mean) ** 2) / (len(F_arr) - 1))
    return float(s)


def calculer_hypervolume_2d(F_2d, ref_point):
    """
    Calcule l'hypervolume exact en 2D pour un ensemble de solutions minimisées
    borné par un point de référence ref_point.
    """
    if len(F_2d) == 0:
        return 0.0
    r0, r1 = ref_point[0], ref_point[1]
    # Filtrer les points dominés par le point de référence (strictement meilleurs que ref)
    valides = F_2d[(F_2d[:, 0] < r0) & (F_2d[:, 1] < r1)]
    if len(valides) == 0:
        return 0.0

    # Tri par f0 croissant puis f1 décroissant
    ordre = np.lexsort((-valides[:, 1], valides[:, 0]))
    pts = valides[ordre]

    # Filtrer les points non-dominés en 2D
    non_dom = []
    min_f1 = np.inf
    for p in pts:
        if p[1] < min_f1:
            non_dom.append(p)
            min_f1 = p[1]

    if not non_dom:
        return 0.0

    non_dom = np.array(non_dom)
    hv = 0.0
    n = len(non_dom)
    for i in range(n):
        x_start = non_dom[i, 0]
        x_end = non_dom[i + 1, 0] if i + 1 < n else r0
        height = r1 - non_dom[i, 1]
        hv += (x_end - x_start) * height
    return float(hv)


def calculer_hypervolume(F_front, ref_point=None):
    """
    Calcule l'hypervolume de l'espace objectif couvert par le front de Pareto
    et borné par ref_point (minimisation).
    Supporte les fronts 2D et 3D (par balayage de dimension).
    """
    if len(F_front) == 0:
        return 0.0
    F_arr = np.atleast_2d(F_front)
    dim = F_arr.shape[1]

    if dim == 2:
        if ref_point is None:
            ref_point = (40.0, 30.0)
        return calculer_hypervolume_2d(F_arr, ref_point)
    elif dim == 3:
        if ref_point is None:
            ref_point = (50.0, 40.0, 30.0)
        r0, r1, r2 = ref_point
        valides = F_arr[(F_arr[:, 0] < r0) & (F_arr[:, 1] < r1) & (F_arr[:, 2] < r2)]
        if len(valides) == 0:
            return 0.0
        z_vals = np.unique(valides[:, 0])
        z_vals.sort()
        hv_total = 0.0
        for i in range(len(z_vals)):
            z_curr = z_vals[i]
            z_next = z_vals[i + 1] if i + 1 < len(z_vals) else r0
            pts_2d = valides[valides[:, 0] <= z_curr, 1:3]
            hv_2d = calculer_hypervolume_2d(pts_2d, (r1, r2))
            hv_total += (z_next - z_curr) * hv_2d
        return float(hv_total)
    else:
        return 0.0


def extraire_front(pop, F):
    fronts, _ = classement_non_domine(F)
    vus, solutions = set(), []
    for i in fronts[0]:
        cle = tuple(np.round(F[i], 4))
        if cle not in vus:
            vus.add(cle)
            solutions.append((pop[i], F[i]))
    solutions.sort(key=lambda x: (x[1][0], x[1][1], x[1][2]))
    return solutions


def meilleur_compromis(solutions):
    valides    = [k for k, (_, f) in enumerate(solutions) if f[0] == 0]
    candidats  = valides if valides else list(range(len(solutions)))
    obj        = np.array([solutions[k][1] for k in candidats])
    cols       = [1, 2] if valides else [0, 1, 2]
    sous       = obj[:, cols]
    etendue    = np.where(np.ptp(sous, axis=0) == 0, 1, np.ptp(sous, axis=0))
    norm       = (sous - sous.min(axis=0)) / etendue
    return candidats[int(np.argmin(np.linalg.norm(norm, axis=1)))]


def construire_tableau_front(solutions, k_best):
    df = pd.DataFrame([f for _, f in solutions], columns=NOMS_OBJECTIFS)
    df["valide (f1=0)"] = df["f1 conflits"] == 0
    df["compromis"]     = ["<-- MEILLEUR" if k == k_best else "" for k in range(len(df))]
    return df


def construire_comparaison(F0, f_final):
    return pd.DataFrame(
        [F0[0], F0.mean(axis=0), f_final],
        index=["Emploi du temps initial (individu 0)",
               "Moyenne population initiale",
               "Meilleur compromis NSGA-II"],
        columns=NOMS_OBJECTIFS
    )


def exporter_resultats(hist, front_df, meilleur, dossier="."):
    import os
    hist.round(3).to_csv(os.path.join(dossier, "historique_generations.csv"), index=False)
    front_df.round(3).to_csv(os.path.join(dossier, "solutions_pareto.csv"), index=False)
    pd.concat(
        [tableau_groupe(meilleur, g).assign(Groupe=C.GRP_NOMS[g]) for g in range(C.N_GRP)]
    ).to_csv(os.path.join(dossier, "emploi_du_temps_final.csv"))
