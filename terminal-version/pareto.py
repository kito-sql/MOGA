# -*- coding: utf-8 -*-
"""
pareto.py – Classement non dominé + crowding distance.
Lit DOMINANCE_CONTRAINTE et DOMINANCE_GUIDEE depuis config dynamiquement
pour refléter les changements de configure().
Intègre G-MOGA (Guided Multi-Objective Genetic Algorithm) avec cône de dominance orienté.
"""

import numpy as np
import config as C


def matrice_domination(F):
    contrainte = C.DOMINANCE_CONTRAINTE
    guidee     = getattr(C, "DOMINANCE_GUIDEE", False)

    if guidee:
        a23 = getattr(C, "TRADE_OFF_A23", 4.0)
        a32 = getattr(C, "TRADE_OFF_A32", 0.2)
        # G-MOGA : cône de dominance orienté sur les objectifs f2 et f3
        # Omega_1 = conflits (f1)
        # Omega_2 = f2 + a23 * f3 (élimine les compromis absurdes dégradant f3)
        # Omega_3 = f3 + a32 * f2 (élimine les compromis absurdes dégradant f2)
        F_eval = np.column_stack([
            F[:, 0],
            F[:, 1] + a23 * F[:, 2],
            F[:, 2] + a32 * F[:, 1]
        ])
    else:
        F_eval = F

    classique = (
        np.all(F_eval[:, None, :] <= F_eval[None, :, :], axis=2) &
        np.any(F_eval[:, None, :] <  F_eval[None, :, :], axis=2)
    )
    if not contrainte:
        return classique
    conflits = F[:, 0]
    valide   = conflits == 0
    les_deux_valides       = valide[:, None] & valide[None, :]
    valide_contre_invalide = valide[:, None] & ~valide[None, :]
    invalides              = ~valide[:, None] & ~valide[None, :]
    moins_de_conflits      = invalides & (conflits[:, None] < conflits[None, :])
    return (les_deux_valides & classique) | valide_contre_invalide | moins_de_conflits


def classement_non_domine(F):
    N   = len(F)
    dom = matrice_domination(F)
    S   = [np.where(dom[p])[0] for p in range(N)]
    n   = dom.sum(axis=0).astype(int)
    rang = np.zeros(N, dtype=int)

    fronts = [[p for p in range(N) if n[p] == 0]]
    i = 0
    while fronts[i]:
        suivant = []
        for p in fronts[i]:
            for q in S[p]:
                n[q] -= 1
                if n[q] == 0:
                    rang[q] = i + 1
                    suivant.append(q)
        i += 1
        fronts.append(suivant)
    fronts.pop()
    return fronts, rang


def crowding_distance(F, front):
    dist  = np.zeros(len(front))
    sous_F = F[front]
    for m in range(F.shape[1]):
        ordre = np.argsort(sous_F[:, m])
        dist[ordre[0]] = dist[ordre[-1]] = np.inf
        fmin, fmax = sous_F[ordre[0], m], sous_F[ordre[-1], m]
        if fmax == fmin:
            continue
        for k in range(1, len(front) - 1):
            dist[ordre[k]] += (sous_F[ordre[k+1], m] - sous_F[ordre[k-1], m]) / (fmax - fmin)
    return dist


def crowding_population(F, fronts):
    crowd = np.zeros(len(F))
    for front in fronts:
        crowd[front] = crowding_distance(F, front)
    return crowd
